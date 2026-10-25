# Bitácora de trabajo — Corrida V4 (proponer el máximo a partir de N potencias medidas, nivel 1)

Documento vivo: cada entrada registra QUÉ se hizo, POR QUÉ (razonamiento), cómo se VERIFICÓ, QUÉ RESULTÓ y QUÉ ARCHIVOS lo respaldan. De aquí se compila el PDF.

## Contexto y punto de partida (octubre 2026)
- La V2 (carpeta `Proyecto Integrador Paneles_V2/`) NO se modifica. Concluyó que el agente PPO que ajustaba β y el reinicio solo mejoraba +1.84 pp en sombra estática y que una regla simple sin RL lo igualaba.
- En la reunión del 21-oct-2026 el profesor propuso otro esquema: medir N potencias en N corrientes uniformes y ascendentes, y que un agente de RL con un MLP sencillo las use como observación para proponer dónde está el máximo; el muestreo de puntos aledaños es parte de policy gradients (política gaussiana con σ pequeña). Orden de algoritmos: REINFORCE con baselines, PPO, SAC y DDPG; variante con árbol de decisión dentro del RL.
- Indicaciones posteriores del profesor: no usar el GMPP real en entrenamiento (evitar fuga de datos); rango de corrientes fijado con la Isc nominal; t_wait del paper como base y preferir iteraciones al tiempo (su Colab no modela la dinámica del convertidor); medir número de mediciones y energía, priorizando mediciones; reinicio ante 5 W remuestreando los N puntos (aprender el umbral queda para después); incluir sombra gradual y ruido de medición.
- Alcance de esta corrida (V4): el NIVEL 1 (potencia estática, sin dinámica del convertidor) con N = 7 y K = 5. Quedan para la siguiente corrida: SAC, DDPG, árbol de decisión, barrido de N y K, sombra gradual, ruido en entrenamiento y el nivel dinámico.

---
## PASO 1 — Diseño: traducir las indicaciones del profesor a un problema bien definido
**Qué hice.** Escribí `diseno_V4.md` con las indicaciones del profesor, las decisiones de diseño y el estado.
Observación = N potencias medidas / 250 W (potencia nominal de hoja de datos) en N corrientes uniformes entre 0.10 y 0.95 de la Isc NOMINAL (8.9 A). Acción = corriente propuesta en ese rango. Recompensa = potencia MEDIDA en la corriente muestreada / 250 W. Episodio = N + K mediciones (K muestras por patrón); es un bandido contextual (γ = 0).
**Por qué.** (a) El profesor pidió explícitamente no usar el GMPP real en entrenamiento: la observación y la recompensa solo pueden usar potencias medidas; el GMPP se reserva para calcular eficiencias al EVALUAR. (b) Pidió fijar mínimo y máximo con la Isc nominal, no con la real del patrón (que un controlador no conoce). (c) Su Colab ignora la dinámica del convertidor, así que la métrica prioritaria es el número de mediciones.
**Decisiones propias (por confirmar con el profesor).** Normalizar por 250 W; episodios de K muestras con γ = 0; dos niveles de simulación (1: estático, 2: con convertidor); referencias sin aprendizaje; la ventana de 200 mediciones para la métrica de energía.
**Archivos.** `diseno_V4.md`.

---
## PASO 2 — Simulador V4 y «planta estática» (nivel 1)
**Qué hice.** Copié el simulador de la V2 a `pvsim_V4/` (mismos modelos del panel, convertidor y MSAPSO fiel, renombrados a `_V4`) y añadí `static_plant_V4.py` con dos plantas: `StaticPlant` (nivel 1: potencia estática P(I), sin inercia del inductor) y `DynamicPlantLogged` (nivel 2: simulador con Boost + Super-Twisting, para usarlo después). Ambas registran cada medición y admiten ruido gaussiano aditivo en la potencia leída. `medicion_V4.py` define la rejilla, la observación y las métricas.
**Por qué.** El profesor indicó que conviene contar iteraciones y no tiempo, porque el tiempo de transición depende de muchas cosas. Con la planta estática, la potencia medida al pedir I es P(I) de la curva; una corriente mayor que la Isc REAL del patrón da potencia 0 (el panel queda en cortocircuito), lo que importa porque el rango se fija con la Isc nominal y los casos 1 y 3 tienen Isc real menor (7.12 A y 3.25 A frente a 8.9 A).
**Métricas (por patrón, búsqueda en frío).** `n_meas` (mediciones gastadas), `n99` (primera medición con potencia verdadera ≥ 99 % del GMPP), `eff_final` (potencia verdadera en el punto elegido, que es la mejor potencia LEÍDA, entre el GMPP) y `eff_energy` (promedio de potencia verdadera en una ventana de 200 mediciones: la búsqueda más la permanencia en el punto elegido).
**Advertencia declarada.** `eff_energy` depende de la longitud de la ventana (200) y favorece búsquedas cortas; por eso se reportan también `eff_final` y `n_meas`.
**Archivos.** `pvsim_V4/static_plant_V4.py`, `pvsim_V4/medicion_V4.py`.

---
## PASO 3 — Entorno Gymnasium y pruebas de humo
**Qué hice.** `pvsim_V4/gym_env_V4.py`: un episodio es un patrón sintético al azar (4 sub-strings); el entorno mide N potencias ascendentes (observación) y el agente da K acciones; cada una es una corriente en [I_MIN, I_MAX] y la recompensa es la potencia medida entre 250 W. Al terminar entrega las métricas en `info['metrics']`.
**Verificación.** `probar_entorno_V4.py`: el entorno pasa `check_env` de stable-baselines3 en nivel estático y dinámico (0.5 y 5 ms). Un agente que propone el GMPP real obtiene 100 % en el nivel estático (el problema está bien planteado) y uno al azar 95.8 % (porque el mejor de los N + K puntos ya incluye el barrido).
**Nota.** En el nivel dinámico la eficiencia aún se calcula contra el GMPP teórico y debería calcularse contra P_ceiling (el Boost con R = 12 Ω no alcanza todos los puntos); queda pendiente antes de usar ese nivel.
**Archivos.** `pvsim_V4/gym_env_V4.py`, `probar_entorno_V4.py`.

---
## PASO 4 — Referencias sin aprendizaje en el nivel 1 (¿contra qué hay que ganar?)
**Qué hice.** `baselines_nivel1_V4.py` mide, con el mismo protocolo, métodos sin aprendizaje sobre los 4 casos reales y 100 patrones sintéticos NUEVOS (semilla 2026, distintos de los de entrenamiento), con ruido de 0, 1 y 2 W:
MSAPSO fiel (Fig. 6 del paper: 7 partículas, β 0.1→0.95, t_max = 25 = 175 mediciones), sembrado con la Isc real y con la Isc nominal; la regla simple de la V2 (β = 0.95, t_max = 5 = 35 mediciones); «mejor de N» (N puntos uniformes y se elige el mejor); y «mejor de N + 5 gaussianas» (los N puntos y luego K = 5 muestras N(mejor, σ²) con σ = 0.05·Isc_nom; es lo que haría la política SIN haber aprendido nada).
**Por qué.** Antes de entrenar hay que saber qué margen deja el control sin aprendizaje; si un método trivial ya iguala al RL, el RL no aporta.
**Resultado (sin ruido; sintéticos / reales).**
| Método | Mediciones | Eficiencia final | Energía (200 med.) |
|---|---|---|---|
| MSAPSO fiel (Isc real) | 175 | 99.98 / 99.99 % | 92.8 / 92.6 % |
| MSAPSO fiel (Isc nominal) | 175 | 99.97 / 99.99 % | 91.0 / 89.9 % |
| Regla simple (β = 0.95, t_max = 5) | 35 | 94.8 / 94.4 % | 93.1 / 92.5 % |
| Mejor de 7 | 7 | 93.3 / 87.1 % | 91.9 / 85.6 % |
| Mejor de 7 + 5 gaussianas | 12 | 97.2 / 93.5 % | 95.4 / 91.7 % |
| Mejor de 10 + 5 gaussianas | 15 | 98.4 / 96.5 % | 95.9 / 93.9 % |
| Mejor de 20 | 20 | 98.5 / 97.2 % | 94.3 / 92.5 % |
| Mejor de 20 + 5 gaussianas | 25 | 99.2 / 99.6 % | 94.6 / 94.4 % |
**Hallazgos.** (1) Sembrar el MSAPSO con la Isc nominal lo empeora (energía 91.0 y 89.9 % frente a 92.8 y 92.6 %), porque en los casos 1 y 3 la Isc real es menor y varias partículas caen donde casi no hay potencia: es una consecuencia de la indicación del profesor que conviene comunicarle. (2) «Mejor de 7 + 5 gaussianas» usa 12 mediciones y ya supera al MSAPSO en energía en sintéticos (95.4 contra 92.8 %), aunque pierde exactitud final (97.2 contra casi 100 %). (3) Con ruido de 1 y 2 W las cifras cambian poco en este nivel.
**Archivos.** `baselines_nivel1_V4.py`, `resultados_V4/baselines_nivel1_V4.txt|json`.

---
## PASO 5 — Cota de diagnóstico: ¿hay margen para un modelo?
**Qué hice.** `cota_diagnostico_V4.py` entrena un MLP SUPERVISADO (con el GMPP real como etiqueta) sobre 6000 curvas sintéticas, con las mismas N potencias, y evalúa con el mismo protocolo. También calcula un «oráculo» que propone exactamente el GMPP y muestrea K = 5 gaussianas alrededor.
**Por qué.** Para saber, antes de gastar entrenamiento de RL, cuánto margen existe. NO es un método de la V4: el profesor prohíbe el GMPP real en entrenamiento; es un diagnóstico del techo.
**Resultado (N = 7, K = 5, 12 mediciones).** Cota supervisada: sintéticos 98.1 % final / 96.2 % energía; reales 97.4 / 95.2 %. Con N = 10 (15 mediciones): 98.1 / 95.5 % (sintéticos); con N = 20 (25 mediciones): 99.0 / 94.3 %. Incluso el oráculo con σ = 0.05 queda en 96–99 % porque 5 muestras no siempre caen en el pico, lo que indica que σ y K también limitan el techo.
**Lectura.** Hay margen moderado: frente a la referencia sin aprendizaje (97.2 / 95.4 % en sintéticos) la cota sube ≈ 0.9 pp de exactitud y ≈ 0.8 pp de energía; frente al MSAPSO, ≈ +3.4 pp de energía con 12 mediciones en vez de 175. Ningún modelo con 12 mediciones alcanza la exactitud del MSAPSO.
**Archivos.** `cota_diagnostico_V4.py`, `resultados_V4/cota_diagnostico_V4.txt`.

---
## PASO 6 — REINFORCE con MLP (propuesta del profesor)
**Qué hice.** `reinforce_nn_V4.py`: política MLP(N → 64 → 64 → 1, tanh) que da μ (corriente propuesta normalizada); se muestrean K = 5 acciones a_k ~ N(μ, σ²) por patrón; recompensa r_k = potencia MEDIDA / 250 W; gradiente REINFORCE ∇J = E[(r_k − b)·(a_k − μ)/σ²·∇μ]. Baselines b: ninguno, «mean» (promedio de las otras K − 1 muestras del mismo patrón) y «value» (V(obs) aprendida). Lotes de 128 patrones, Adam con lr 1e-3, 4000 actualizaciones, banco de 6000 curvas sintéticas de entrenamiento (semilla 0). Sin GMPP ni P_ceiling en el entrenamiento. Evaluación en los 4 reales y 100 sintéticos nuevos, con 3 semillas, en tres modos: K muestras, solo μ (1 medición) y μ + K muestras. Malla: baseline × σ ∈ {0.02, 0.05, 0.10}·Isc_nom (`grid_reinforce_V4.py`).
**Resultado (media de 3 semillas, modo K muestras, N = 7, K = 5).**
| Baseline, σ | Reales: final / energía | Sintéticos: final / energía |
|---|---|---|
| none, 0.05 (mejor) | 97.2 / 95.1 % | 96.7 / 94.9 % |
| mean, 0.05 | 96.3 / 94.2 % | 96.8 / 95.0 % |
| value, 0.05 | 95.6 / 93.5 % | 96.7 / 94.9 % |
| none, 0.02 | 96.4 / 94.5 % | 96.1 / 94.4 % |
| none, 0.10 | 95.3 / 93.1 % | 96.9 / 94.9 % |
Evaluado solo en μ (1 medición): ≈ 94.4 % en sintéticos, apenas sobre «mejor de 7» (93.3 %).
**Variante de recompensa.** Probé premiar la mejora sobre el mejor punto del barrido (calculada con potencias medidas): no cambió nada (`prueba_reward_V4.py`).
**Lectura.** En sintéticos REINFORCE queda ligeramente por debajo de la referencia sin aprendizaje (97.2 / 95.4 %). En los 4 reales parece mejor (+3 pp) pero son solo 4 casos. La política casi no aprende dónde está el pico: su media μ equivale a «mejor de 7».
**Archivos.** `reinforce_nn_V4.py`, `grid_reinforce_V4.py`, `prueba_reward_V4.py`, `resultados_V4/reinforce_*`.

---
## PASO 7 — PPO (stable-baselines3) en el mismo entorno
**Qué hice.** `ppo_nivel1_V4.py`: PPO sobre `MPPTSampleEnvV4` con γ = 0 y λ_GAE = 0 (bandido contextual), MLP 64×64, 8 entornos, 1 millón de pasos (≈ 85 s por semilla), σ inicial pequeña (log_std_init = −2, σ = 0.135 en unidades de acción), 3 semillas. Mismos escenarios de evaluación.
**Resultado.**
| Configuración | Reales: final / energía | Sintéticos: final / energía | σ aprendida |
|---|---|---|---|
| PPO, semilla 0 | 87.9 / 86.3 % | 96.2 / 94.5 % | 0.014 |
| PPO, semilla 1 | 87.9 / 86.2 % | 95.7 / 94.1 % | 0.013 |
| PPO, semilla 2 | 89.0 / 87.4 % | 95.6 / 93.9 % | 0.013 |
| PPO + entropía 0.02 (1 sem.) | 87.8 / 86.1 % | 95.8 / 94.2 % | 0.019 |
| PPO + entropía 0.1 (1 sem.) | 95.0 / 93.1 % | 96.4 / 94.7 % | 0.034 |
**Hallazgo.** La σ colapsa a ≈ 0.013 (frente a 0.135 inicial): al maximizar la potencia promedio de las muestras, la política aprende a no explorar, con lo que las K muestras caen casi en el mismo punto y no aportan nada. Con una bonificación de entropía alta (0.1), PPO mejora mucho en los reales (88 → 95 %), lo que apunta en esa dirección. Es una hipótesis razonable, no una causa demostrada del todo.
**Archivos.** `ppo_nivel1_V4.py`, `resultados_V4/ppo_*`, `modelos_V4/`.

---
## PASO 8 — ¿Más entrenamiento cambia el resultado?
**Qué hice.** `entrenamiento_largo_V4.py`: REINFORCE (baseline «mean», σ = 0.05) con 4 mil, 20 mil y 60 mil actualizaciones y lotes de 128, 512 y 256, 3 semillas.
**Resultado (sintéticos, eficiencia final con K = 5 / solo μ).** 4 mil: 96.84 / 94.36 %; 20 mil (lote 128): 97.10 / 94.52 %; 20 mil (lote 512): 96.97 / 94.48 %; 60 mil: 97.20 / 94.76 %. Referencia sin aprendizaje: 97.22 %. Cota supervisada: 98.1 %.
**Lectura.** Con 15 veces más entrenamiento el resultado sube ≈ 0.4 pp y se IGUALA a la referencia sin aprendizaje, sin superarla; μ solo sube de 94.4 a 94.8 %. La curva se aplana, lo que apunta a que el límite está en lo que se optimiza y no en la cantidad de entrenamiento. En la V2 ocurrió algo parecido: PPO con 3 M de pasos fue peor que con 1 M.
**Archivos.** `entrenamiento_largo_V4.py`, `resultados_V4/entrenamiento_largo_V4.txt`.
