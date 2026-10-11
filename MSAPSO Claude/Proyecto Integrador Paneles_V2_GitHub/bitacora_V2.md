# Bitácora de trabajo — Corrida V2 (corrección y re-validación de las Fases 0–3)

Documento vivo: cada entrada registra QUÉ se hizo, POR QUÉ (razonamiento), QUÉ RESULTÓ y QUÉ ARCHIVOS lo respaldan.
De aquí se compila el PDF final para el profesor.

## Contexto y punto de partida (2026-10-10)
- La V1 (carpeta `Proyecto Integrador Paneles/`) NO se modifica; se conserva como evidencia.
- Observaciones del profesor sobre la V1: (1) ε de APSO muestreado en [-1,1] en vez de [0,1]; (2) el "baseline" no era el MSAPSO del paper;
  (3) falta graficar β; (4) cuestionó si el controlador deslizante realmente se simuló; (5) pidió barrido escalonado alternante fiel al paper;
  (6) propuso rama REINFORCE (gradiente gaussiano) con baselines R-V(s), R-Q(a,s), Q(a,s)-V(s).
- Autocrítica propia previa (reportada al profesor): fuga de información en la observación de RL (normalización por P_gmpp y aviso de cambio de sombra),
  baseline con 5 partículas/1 ms/sin reinicio, métrica = mejor potencia encontrada (no energía entregada), una sola semilla.
- Lectura directa de las figuras 5 y 6 del paper (como imagen, no como texto): MSAPSO = 7 partículas Isc·[0.95 0.8 0.65 0.5 0.3 0.15 0.1],
  β_min=0.1, β_max=0.95, t_max=25, t_wait=0.5 ms, pasada "positiva" y pasada "negativa" alternadas, Gbest se actualiza al instante (Ppv ≥ Pbest),
  posiciones recalculadas al final de cada pasada (Eq.13), y reinicio si |Pbest−Ppv| ≥ 5 W medido tras t_max con el convertidor fijo en Gbest.

## Decisiones declaradas para los puntos que el profesor no pudo aclarar (fin de semana)
| Duda | Decisión | Cobertura |
|---|---|---|
| Dirección de la 1.ª pasada | Menor→mayor corriente (dicho por el profesor), luego mayor→menor, alternando | Variante con orden literal de la Fig. 6 como sensibilidad |
| ¿Eq.12 (ε) o Eq.13? | Eq.13 determinista (el paper dice que MSAPSO elimina la aleatoriedad) | APSO aparte con ε∈[0,1] |
| Reinicio | Solo tras t_max, umbral absoluto 5 W (Fig. 6) | Variante "detección temprana" (cada pasada) y "sin reinicio" |
| t_wait 0.5 ms vs 5 ms | Probar el barrido fiel a 0.5 ms; re-sintonizar el controlador solo si no asienta | Reportar ambos tiempos |
| Tiempo de espera del agente RL | Fijo e igual para todos en la comparación principal | Ablación aparte |
| REINFORCE | Forma del profesor (principal) y forma de libro (control); corrientes en por unidad (÷Isc) | Malla en etapas |


---
## PASO 1 — Simulador V2 (mismo modelo físico, núcleo compilado) y validación contra la V1
**Qué hice.** Reescribí el modelo dinámico PV+Boost+Super-Twisting (`pvsim_V2/converter_V2.py`) con integración RK4 de paso fijo compilada con numba
(la V1 usaba `scipy.solve_ivp`). Añadí a las curvas (`pvcurve_V2.py`, `array_model_V2.py`) el atributo `P_ceiling` (potencia máxima alcanzable con la carga R=12 Ω)
y guardé las tablas I(V) listas para el núcleo compilado.
**Por qué.** (a) Con los tiempos fieles al paper (7 partículas × 0.5 ms por pasada, 25 pasadas, miles de episodios) la V1 era inviable (~2.8 ms de cómputo por ms simulado).
(b) El profesor cuestionó si el controlador deslizante se simuló de verdad: aquí la ley u = u_eq + u_st con integrador z sigue siendo la del paper (ecs. 4–7); solo cambió el integrador numérico.
(c) `P_ceiling`: en la V1 medí contra el GMPP teórico aunque fuera físicamente inalcanzable con un Boost y R=12 Ω (Caso 3), lo que castigaba a cualquier método por algo imposible.
**Cómo lo verifiqué** (`validar_simulador_V2.py`):
- Convergencia en dt: con dt = 1e-5 s el error en P_final es 0.0001 % respecto a dt = 1e-6 s.
- Equivalencia con la V1 (escalera de 7 corrientes × 3, ventanas de 0.5 ms y 5 ms, 4 casos): diferencia máxima en potencia ≤ 0.003 %, en energía 0.000 %.
- Velocidad: V1 = 2.81 ms de cómputo por ms simulado; V2 = 0.025 ms → **aceleración ≈ 113×** (1 s simulado ≈ 25 ms de cómputo).
**Resultado.** Simulador V2 validado; todo lo que sigue usa dt = 1e-5 s.
**Archivos.** `pvsim_V2/converter_V2.py`, `pvsim_V2/pvcurve_V2.py`, `pvsim_V2/array_model_V2.py`, `validar_simulador_V2.py`.

---
## PASO 2 — MSAPSO fiel a la Fig. 6 y primera compuerta de validación
**Qué hice.** Implementé `pvsim_V2/msapso_V2.py`: 7 partículas Isc·[0.95 … 0.1], β de 0.1 a 0.95 (Eq. 14), t_max = 25, barrido alternante (la 1.ª pasada de menor a mayor,
como indicó el profesor), Gbest actualizado al instante con la regla Ppv ≥ Pbest, posiciones recalculadas al final de cada pasada (Eq. 13 determinista), «park» en Gbest tras
t_max y reinicio si |Pbest − Ppv| ≥ 5 W. Un «paso» de tiempo = una pasada = 7 ventanas de t_wait; el mantenimiento (park) dura lo mismo, para que la energía de todos los métodos
se compare en la misma base.
**Corrección de fidelidad detectada en el camino.** Primero guardé como Gbest la corriente del *inductor*; en la Fig. 6 el paper guarda `Gbest = Ipv` y mide `Ppv = Vpv·Ipv`, y su Eq. 1
define Ipv como la corriente de salida del *módulo*. En mi modelo (que incluye el capacitor de entrada Ce) ambas difieren en los transitorios, y entonces Pbest y Gbest no eran el mismo punto
de la curva → reinicios espurios. Corregido: Ipv = I_panel(Vpv) (sensor en los terminales del panel).
**Resultado (casos estáticos, 1 s, MSAPSO fiel, t_wait = 0.5 ms).** Potencia final 100 / 100 / 100 / 97.5 % del techo alcanzable (casos 1–4); energía entregada 99.6 / 99.7 / 99.7 / 97.2 %;
la 1.ª búsqueda termina en 87.5 ms = 25 × 7 × 0.5 ms (cuadra con los 0.12 s de la Tabla 3 del paper). Con 5 ms: 100 % en los 4 casos.
**Archivos.** `pvsim_V2/msapso_V2.py`, `evaluar_baselines_V2.py`, `resultados_V2/baselines_V2.txt|json`.

---
## PASO 3 — Ablación, diagnóstico de la dinámica del convertidor y decisión del régimen de tiempo
**Hipótesis que probé y que resultó FALSA.** Pensé que el barrido alternante era lo que hacía viable t_wait = 0.5 ms. Ablación a 0.5 ms (potencia final % / reinicios):
alternar o no apenas cambia nada (100/100/100/97.2); lo decisivo fue guardar Gbest como la corriente *medida* (la V1 guardaba la corriente *comandada*): sin eso, 78.7 / 99.3 / 70.6 / 93.8 con reinicios espurios.
**Diagnóstico del Caso «2→1» (transición que fallaba).** Inspeccionando ventana por ventana: a 0.5 ms la corriente del inductor se mueve solo ~0.6 A hacia abajo y ~0.3 A hacia arriba por ventana;
el convertidor no alcanza a seguir la referencia y la potencia medida refleja el punto donde el convertidor *va*, no el candidato aplicado. El algoritmo actúa como un «escáner de trayectoria».
**¿Re-sintonizar el controlador ayuda?** (`resintonia_controlador_V2.py`). Con las ganancias del paper (λ=0.1, Υ=0.01): −0.59 A / +0.33 A por 0.5 ms. Con 10× las ganancias el convertidor ya satura en su
límite físico (−1.00 A / +1.75 A; límite teórico −0.95 / +1.50 A con L = 10 mH, Vpv ≈ 30 V, Vo ≈ 49 V); con 100× y 1000× no mejora. Conclusión: re-sintonizar solo da 2–3× y no alcanza; el límite es el inductor.
**Transiciones (12 pares ordenados, MSAPSO fiel) vs t_wait:** pares con potencia final ≥ 99 %: 8/12 (0.5 ms), 8/12 (1 ms), 9/12 (2 ms), **12/12 (5 ms)**; eficiencia de energía 95.1 → 96.4 %.
**Decisión declarada.** Régimen PRINCIPAL: t_wait = 5 ms (el convertidor sigue la referencia; todas las mediciones son honestas). Régimen SECUNDARIO: t_wait = 0.5 ms (valor literal del paper). Ambos con las ganancias del paper.
Pregunta para el profesor (no bloquea): ¿su convertidor simulado asienta en 0.5 ms? Con L = 10 mH el nuestro no puede por límite físico de pendiente de corriente.
**Otros hallazgos del mismo barrido de variantes** (`evaluar_baselines_V2.py`):
- «Reinicio temprano» (comparar el máximo de cada pasada contra Pbest) NO sirve como baseline más fuerte: se dispara en casi cada pasada (95 reinicios/s) porque en una pasada con partículas dispersas el máximo puede quedar ≥5 W por debajo de Pbest legítimamente. Se descarta y se reporta así.
- «Sin reinicio»: 53 % de energía en las transiciones frente a 95 % con la regla del paper → el reinicio es lo que sostiene el desempeño ante cambios de sombra.
- El «baseline de la V1» reconstruido en el simulador V2 (5 partículas, β 0.1→0.9, sin reinicio, orden fijo, Gbest = referencia, 1 ms) entrega solo 55–85 % de la energía: confirma que era un baseline débil (la V1 lo evaluaba con «mejor potencia encontrada», métrica que no penaliza eso).

---
## PASO 4 — Entorno de RL V2, arnés común de evaluación y primera prueba de PPO
**Qué hice.**
- `pvsim_V2/passrunner_V2.py`: la mecánica de UNA pasada (7 ventanas, barrido alternante, Gbest inmediato, Eq. 13) en una sola clase usada tanto por el entorno de RL como por los
  controladores que se evalúan → lo que aprende el agente y lo que se mide son idénticos.
- `pvsim_V2/gym_env_V2.py` (Gymnasium; `check_env` OK): acción = [β ∈ 0.05–0.95, reinicio sí/no]; el tiempo de espera NO lo decide el agente (fijo, igual para todos los métodos);
  episodios de 130 pasadas con búsqueda inicial, un cambio abrupto de sombra (80 % de los episodios, entre las pasadas 20 y 70) y re-búsqueda.
- **Observación sin información privilegiada** (8 señales: P_max y P_media de la última pasada, Pbest, caída relativa respecto a Pbest, dispersión de partículas, pasadas desde el reinicio,
  β previo, ΔPbest). Se eliminó la normalización por GMPP real y el aviso directo de cambio de sombra que tenía la V1.
- **Recompensa = energía entregada en la pasada / energía ideal** (usa P_ceiling solo aquí, en entrenamiento). Premia lo que importa y castiga explorar de más; reemplaza la métrica «mejor potencia encontrada» de la V1.
- Sombras de entrenamiento más exigentes (`random_shading_mix`: mezcla de sub-strings soleados y sombreados). Los 4 casos reales y sus pares NO se usan para entrenar (holdout).
- `pvsim_V2/harness_V2.py` + `evaluar_rl_V2.py`: mismos escenarios y métrica para todos los métodos: 4 casos estáticos; 12 pares ordenados de casos reales (holdout);
  100 pares de curvas sintéticas nuevas (semilla fija) para generalización. Segmentos de 62 pasadas.
**Por qué.** Responde a: «baseline injusto», «features que filtran información», «métrica que no mide la energía entregada» y «una sola semilla» (se entrenarán 3).
**Velocidad.** ≈1,000 pasos/s por entorno a t_wait = 5 ms y ≈8,000 a 0.5 ms → 1 M de pasos de PPO ≈ 8 min (la V1 tardaba ~3.3 h por 300 k). Por eso el entrenamiento se corre aquí, sin necesidad de VS Code.
**Primer resultado (modelo de prueba, 1 semilla, 200 k pasos, t_wait = 5 ms; energía % / potencia final % / reinicios):**
| Método | 4 casos estáticos | 12 transiciones reales | 100 sintéticas nuevas |
|---|---|---|---|
| MSAPSO fiel (paper) | 97.26 / 100.0 / 0 | 96.41 / 100.0 / 1.00 | 96.04 / 99.23 / 0.95 |
| MSAPSO sin reinicio | 97.26 / 100.0 / 0 | 56.58 / 56.54 / 0 | 60.76 / 60.66 / 0 |
| PPO (prueba 200 k) | 99.35 / 99.93 / 0 | 96.54 / 98.00 / 0.67 | 93.14 / 94.35 / 0.65 |
**Lectura.** Con un baseline justo el panorama cambia por completo respecto a la V1: el agente gana en energía en casos estáticos (converge más rápido), EMPATA en las transiciones reales y queda
POR DEBAJO en sombras sintéticas nuevas (modelo todavía subentrenado). La «mejora enorme» de la V1 venía del baseline débil y de la información filtrada, no del aprendizaje.
**Siguiente.** Entrenamientos formales (3 semillas × 2 regímenes de tiempo + ablación de señales), un control sin RL con el calendario de β optimizado, y la rama REINFORCE.
**Archivos.** `pvsim_V2/passrunner_V2.py`, `pvsim_V2/gym_env_V2.py`, `pvsim_V2/harness_V2.py`, `train_V2.py`, `evaluar_rl_V2.py`, `lanzar_entrenamientos_V2.sh`, `resultados_V2/eval_prueba.json`.

---
## PASO 5 — Rama REINFORCE (propuesta del profesor): implementación y malla en etapas
**Qué hice.** `pvsim_V2/reinforce_V2.py`: cada pasada se muestrean K = 7 corrientes candidatas de N(μ, σ²) (en por unidad: corriente/Isc, así σ = 0.3/0.5/0.8 son fracciones de Isc), se prueban en
ESCALERA (pasada ascendente, luego descendente, Gbest inmediato) y se actualiza μ con el gradiente del log de la gaussiana, (b − μ)/σ². «Park» y regla de reinicio de 5 W idénticos al MSAPSO fiel,
de modo que solo cambia la regla de actualización. Formas: **B** (la del profesor: lr·W·(Gbest − μ)/σ², con W = recompensa asociada a Gbest; baseline none | V) y **A** (estimador REINFORCE de libro,
suma sobre muestras; baselines none | R−V | R−Q̂(a) | Q̂(a)−V con Q̂ = regresión kernel gaussiana). Recompensa R = P/P_norm, con P_norm = 250 W (nominal) o la mejor potencia vista. Tasas: fija (0.1/0.01/0.001),
acelerada (Eq. 14), 1/t.
**Por qué estas decisiones.** (1) Por unidad: con σ en amperios, 0.5 A significaría cosas muy distintas con Isc de 3.2 A que con 8.9 A. (2) Paso efectivo c = lr·W/σ² (estabilidad: converge si 0 < c < 2). (3) Se agregó la forma A
como control, porque la forma B del profesor es en la práctica SAPSO con paso escalado por W/σ².
**Malla en etapas** (`reinforce_grid_V2.py`): etapa 1 = 180 configuraciones puntuadas con sombras sintéticas de entrenamiento (semilla 7; 30 pares × 2 repeticiones); etapa 2 = la mejor de cada
(forma, baseline) y la mejor de cada tasa (forma B) evaluadas en los conjuntos de prueba con 5 repeticiones. **Resultado** (energía % / potencia final %), t_wait = 5 ms, MSAPSO fiel como referencia
(97.26/100, 96.41/100, 96.04/99.23 en estáticos/pares reales/sintéticos):
| Configuración elegida | 4 estáticos | 12 pares reales | 100 sintéticos |
|---|---|---|---|
| B, sin baseline (lr acelerada, σ 0.3, R nominal) | 87.65 / 96.9 | 85.58 / 95.6 | 83.88 / 95.4 |
| B, baseline V (lr 0.001, σ 0.3) | 87.07 / 98.7 | 84.25 / 98.2 | 84.16 / 93.3 |
| A, sin baseline (lr 0.1, σ 0.3) | 88.29 / 98.5 | 85.89 / 96.6 | 86.58 / 96.5 |
| A, R−V (lr acelerada, σ 0.3, R nominal) | 87.61 / 100.0 | 87.65 / 99.6 | 88.71 / 98.0 |
| A, R−Q̂ (acelerada, σ 0.3) | 85.78 / 95.2 | 85.72 / 98.3 | 87.66 / 97.4 |
| A, Q̂−V (1/t, σ 0.3) | 87.64 / 95.0 | 87.75 / 98.2 | 86.56 / 96.4 |
**Lectura.** Todas las variantes convergen (potencia final 93–100 %) pero ENTREGAN MENOS ENERGÍA (84–89 %) que el MSAPSO (96–97 %): con σ fija, los candidatos siguen dispersos alrededor de μ durante toda la búsqueda,
mientras que MSAPSO contrae el enjambre y por eso desperdicia menos. En los seis casos la mejor σ fue la MENOR de las propuestas (0.3), señal de que un σ más pequeño o decreciente podría ayudar (extensión no pedida por el profesor,
se prueba aparte y se reporta como tal). Entre baselines no hay diferencias grandes y consistentes (A-R−V es la mejor en pares reales y sintéticos); la tasa acelerada con σ = 0.3 tiene c = lr/σ² hasta ≈ 10.5 > 2 (inestable por
construcción) y aun así es elegida: el recorte de μ a [0.02, 1] limita el daño.
**Archivos.** `pvsim_V2/reinforce_V2.py`, `reinforce_grid_V2.py`, `resultados_V2/reinforce_grid_V2.json`.

---
## PASO 6 — Primer PPO formal (semilla 0) y qué aprendió el agente
**Qué hice.** Entrené PPO (stable-baselines3, hiperparámetros por defecto, red 64×64) 1,000,000 pasos, 4 entornos paralelos, t_wait = 5 ms (950 s de cómputo con la máquina cargada). Evaluación con el arnés común
(`evaluar_rl_V2.py`; energía % / potencia final %): estáticos 99.32 / 99.90 · pares reales 98.26 / 99.94 · sintéticos 96.57 / 98.53, frente al MSAPSO fiel 97.26 / 100 · 96.41 / 100 · 96.04 / 99.23.
→ ventaja modesta pero consistente en energía (+2.1, +1.9, +0.5 puntos), con potencia final equivalente.
**Gráfica pedida por el profesor (β vs convergencia, `fig_agente_vs_msapso_s0.png`).** Lo que hace el agente: arranca con β ≈ 0.95 → el enjambre se colapsa sobre el mejor punto de la PRIMERA pasada (la dispersión cae a ~0 en 2–3 pasadas;
el MSAPSO tarda ~12) y reinicia justo después del cambio de sombra. La «β alta primero y menor cerca del MPP» que supuso el profesor aparece solo de forma leve (un valle ≈ 0.45 hacia la pasada 4) y no tiene efecto: con el enjambre ya colapsado, β no mueve nada.
**Control sin RL (hallazgo clave, marcado POST-HOC porque lo probé después de ver al agente).** MSAPSO con β = 0.95 constante y t_max = 3–5 entrega 99.29 / 99.86 (estáticos), 98.37 / 99.91 (pares reales) y 95.7 / 97.1 (sintéticos): IGUALA al PPO en casos reales;
y «β 0.5→0.95, t_max = 8» da 98.98 · 98.03 · 97.35, superando al PPO en sintéticos. Es decir, la ventaja del agente sobre el calendario del paper se explica por un calendario más agresivo, no por aprendizaje.
**Autocrítica sobre un intento previo de control.** La primera búsqueda de un «MSAPSO optimizado» (121 configuraciones, 40 escenarios) eligió (β 0.28→0.60, t_max = 5), que mejoró en las sombras de optimización (96.22 % vs 95.04 %) pero EMPEORÓ en prueba
(93.05 % vs 97.26 % en estáticos): sobreajuste por seleccionar el mejor de muchos sobre pocos escenarios (maldición del ganador). Se repite con espacio ampliado y selección en dos etapas (optimización → validación con 150 pares nuevos).
**Archivos.** `modelos_V2/ppo_5ms_full_s0.*`, `resultados_V2/eval_main_s0.json`, `resultados_V2/fig_agente_vs_msapso_s0.png`, `optimizar_msapso_V2.py`.

---
## PASO 7 — Control sin RL con selección en dos etapas (sin mirar los conjuntos de prueba)
**Qué hice.** `optimizar_msapso_V2.py`: búsqueda aleatoria de (β_min, β_max, t_max) con 150 configuraciones, espacio ampliado (β_min hasta 0.95; t_max ∈ {3, 5, 8, 12, 18, 25}), puntuadas con 60 pares sintéticos de
OPTIMIZACIÓN (semilla 7); las 8 mejores + la del paper se re-puntúan con 150 pares de VALIDACIÓN (semilla 8) y se elige por validación. La evaluación en prueba (casos reales y sintéticas nuevas, semilla 2026) se hace una sola vez al final.
**Por qué.** Es el control honesto de «¿se explica la ganancia de RL por un mejor calendario de β?», evitando la maldición del ganador del primer intento (Paso 6).
**Resultado.** Mejor configuración (β 0.185 → 0.732, t_max = 25): validación 97.04 % vs 96.78 % del paper; prueba (energía %): 97.58 · 96.64 · 96.31 (estáticos · pares reales · sintéticos) vs 97.26 · 96.41 · 96.04 del paper → +0.3 puntos, es decir,
prácticamente la configuración del paper. **Matiz importante:** sobre sombras sintéticas un calendario agresivo no gana, pero sobre los casos reales del paper sí (reglas simples post-hoc del Paso 6). Mi primera explicación («los 7 puntos iniciales de la rejilla caen cerca del GMPP en los casos reales») resultó FALSA al medirla: el mejor punto de la rejilla inicial alcanza solo 99.7 / 85.5 / 99.5 / 91.0 % del techo alcanzable en los casos 1–4 (y 96.0 % en promedio en las curvas sintéticas, con 40 % de ellas por debajo de 95 %). En el simulador dinámico las mediciones al final de cada ventana caen sobre la trayectoria del convertidor, no solo en las corrientes comandadas, así que una sola pasada explora más de 7 puntos; es plausible que eso ayude, pero no lo investigué a fondo. Por qué un calendario agresivo favorece a los casos reales y no a los sintéticos queda como PREGUNTA ABIERTA.
**Archivos.** `optimizar_msapso_V2.py`, `resultados_V2/msapso_optimizado_5ms.json`.

---
## PASO 8 — PPO con 3 semillas y dos regímenes de tiempo (resultado principal)
**Qué hice.** Entrené PPO (hiperparámetros por defecto, red 64×64, 1 M de pasos, 4 entornos) con 3 semillas en t_wait = 5 ms (régimen principal) y 3 semillas en t_wait = 0.5 ms (literal del paper), y evalué todo con el arnés común
(`analisis_final_V2.py`: media ± desv. entre semillas y diferencia pareada por escenario con IC95 % bootstrap).
**Resultado, t_wait = 5 ms (energía %; potencia final % entre paréntesis):**
| Método | 4 estáticos | 12 pares reales | 100 sintéticos |
|---|---|---|---|
| MSAPSO fiel (paper) | 97.26 (100.0) | 96.41 (100.0) | 96.04 (99.2) |
| MSAPSO sin reinicio | 97.26 (100.0) | 56.58 (56.5) | 60.76 (60.7) |
| MSAPSO optimizado formal | 97.58 (100.0) | 96.64 (100.0) | 96.31 (99.2) |
| regla simple β = 0.95, t_max = 5 (post-hoc) | 99.29 (99.9) | 98.37 (99.9) | 95.71 (97.0) |
| regla simple β 0.5→0.95, t_max = 8 (post-hoc) | 98.98 (100.0) | 98.03 (100.0) | 97.35 (99.0) |
| **PPO (3 semillas, media ± sd)** | **99.10 ± 0.16** (99.8) | **96.84 ± 1.01** (98.2) | **95.21 ± 1.03** (97.4) |
Diferencia pareada PPO − MSAPSO fiel (puntos, IC95 %): estáticos +1.84 [+1.23, +2.42] (mejor en 4/4); pares reales +0.42 [−1.35, +1.88] (9/12); sintéticos −0.82 [−2.04, +0.34] (66/100).
PPO − regla simple β = 0.95: estáticos −0.19, pares reales −1.53 [−3.29, −0.27] (la regla simple es significativamente mejor), sintéticos −0.50.
**Hay variabilidad entre semillas:** la semilla 0 llega a 98.26 % en pares reales; las semillas 1 y 2, a 96.1 %.
**Resultado, t_wait = 0.5 ms (literal del paper):** MSAPSO fiel 97.97 · 92.01 · 86.24; PPO 96.93 ± 0.78 · 89.48 ± 2.53 · 85.03 ± 0.33 (todas las diferencias con IC que incluye 0); las reglas simples agresivas FALLAN
(92 · 71 · 76 y 97 · 68 · 80) porque el convertidor no sigue referencias que cambian tan rápido (límite de pendiente del inductor, Paso 3).
**Lectura.** Con una comparación justa, el agente de RL NO supera de forma robusta al MSAPSO del paper en las transiciones de sombra; su única ventaja demostrable es converger más rápido en sombras estáticas, y eso lo reproduce una regla trivial.
**Archivos.** `modelos_V2/ppo_*`, `analisis_final_V2.py`, `resultados_V2/final_raw_V2.json`, `resultados_V2/analisis_final_V2.txt`.

---
## PASO 9 — Extensión de REINFORCE con σ más pequeña (no pedida; reportada como extensión)
**Por qué.** En la malla del Paso 5 la mejor σ siempre fue la menor propuesta (0.3). Probé σ ∈ {0.05, 0.1, 0.2} en cuatro variantes (B-ninguno, A-ninguno, A-R−V, A-Q̂−V) con 120 configuraciones.
**Resultado** (energía % / potencia final %; estáticos · pares reales · sintéticos): B-ninguno con lr = 0.001, σ = 0.05, R normalizada por la mejor potencia: **95.55/100 · 93.85/100 · 89.94/95.6** (paso efectivo c = lr/σ² = 0.4);
A-R−V (lr 0.1, σ 0.05): 92.35 · 92.74 · 89.68; A-Q̂−V (1/t, σ 0.05): 91.90 · 93.05 · 89.84. Mejora grande respecto a σ ≥ 0.3 (≈ 88 %), pero sigue por DEBAJO del MSAPSO fiel (97.26 · 96.41 · 96.04),
sobre todo en sintéticas. Conclusión: con σ fija, REINFORCE gaussiano converge a la potencia correcta pero gasta más energía explorando; un σ decreciente (no probado) sería el siguiente paso natural.
**Archivos.** `resultados_V2/reinforce_grid_ext_V2.json`.

---
## PASO 10 — Ablación de las señales de observación (¿valen la pena todas?)
**Qué hice.** Entrené PPO (1 M de pasos, 2 semillas por variante, 5 ms) con subconjuntos de las 8 señales: completa; sin dispersión de partículas; sin «pasadas desde el reinicio»; sin las dos señales de variación de potencia (caída relativa respecto a Pbest y ΔPbest);
y una mínima con solo P_max, Pbest y caída relativa. El profesor pidió justificar «tiempo desde el último reinicio» y «dispersión de las partículas», y sospechó que el delta de potencia explica el β alto inicial.
**Por qué elegí originalmente esas señales (respuesta directa).** La dispersión resume cuánto se ha colapsado el enjambre (historial acumulado de β) y sirve para decidir si conviene re-explorar; el tiempo desde el reinicio funciona como reloj de la búsqueda; las señales de variación de potencia
son la pista para detectar un cambio de sombra. Fue intuición de diseño, sin evidencia previa; la ablación es la evidencia.
**Resultado** (energía % media de 2 semillas; estáticos · pares reales · sintéticos): completa 99.15 · 97.20 · 95.78; sin dispersión 98.73 · 96.68 · 95.19; sin t. desde reinicio 99.29 · 96.49 · **92.29**; sin caída/ΔPbest 98.78 · **95.74** · 95.10; mínima 99.24 · **94.89** · **92.55**.
**Lectura (con cautela: la desviación entre semillas de PPO es ≈ 1 punto en pares y sintéticas).** (1) En casos estáticos ninguna señal importa (≈ 99 %). (2) La **dispersión** aporta poco (−0.4 a −0.6 puntos, dentro del ruido): prescindible. (3) El **tiempo desde el reinicio** importa en sombras
sintéticas (−3.5 puntos) y no en las reales. (4) Las **señales de variación de potencia** (caída relativa y ΔPbest) importan en las transiciones (−1.5 puntos en pares reales; −2.3 en la mínima): son la señal de detección del cambio. (5) Contra la hipótesis del profesor: quitar el delta NO
afecta la convergencia rápida de los casos estáticos (98.78 vs 99.15); el β alto inicial se aprende sin él. El delta sirve para detectar el cambio, no para acelerar la convergencia.
**Archivos.** `modelos_V2/ppo_5ms_{no_disp,no_time,no_drop,minimal}_s{0,1}.*`, `resultados_V2/fig_ablacion_senales.png`.

---
## PASO 11 — ¿Más entrenamiento u otro algoritmo cierra la brecha?
**Qué hice.** (a) PPO con 3 M de pasos (2 semillas); (b) A2C 1 M de pasos y (c) SAC 300 k pasos (1 semilla cada uno), con hiperparámetros por defecto de stable-baselines3 y el mismo entorno y arnés. Respuesta a «¿qué tal les ha ido con distintos métodos de RL?».
**Resultado** (5 ms; energía % / potencia final %; estáticos · pares reales · sintéticos):
| Método | 4 estáticos | 12 pares reales | 100 sintéticos |
|---|---|---|---|
| MSAPSO fiel (referencia) | 97.26 / 100.0 | 96.41 / 100.0 | 96.04 / 99.2 |
| PPO 1 M (media de 3 semillas) | 99.10 / 99.8 | 96.84 / 98.2 | 95.21 / 97.4 |
| PPO 3 M, semilla 0 | 98.82 / 98.3 | 95.56 / 98.0 | 94.11 / 98.5 |
| PPO 3 M, semilla 1 | 98.91 / 100.0 | 96.79 / 100.0 | 93.68 / 96.8 |
| A2C 1 M | 99.00 / 98.3 | 93.43 / 97.6 | 95.98 / 98.3 |
| SAC 300 k | 98.80 / 99.9 | 96.75 / 99.9 | 95.03 / 97.5 |
**Lectura.** Triplicar el entrenamiento NO mejora (incluso la semilla 0, que con 1 M era la mejor, empeora de 98.26 a 95.56 en pares reales y hace reinicios innecesarios); A2C es peor en transiciones; SAC rinde parecido a PPO. Ningún algoritmo supera de forma robusta al MSAPSO fiel en las
transiciones, y todos coinciden en converger más rápido en sombras estáticas. Es una sola semilla para A2C y SAC: son indicios, no conclusiones.
**Archivos.** `modelos_V2/ppo_5ms_full3M_s*`, `a2c_5ms_full_s0.*`, `sac_5ms_full_s0.*`, `resultados_V2/final_raw_V2.json`.

---
## PASO 12 — Fase 0 corregida: APSO con ε ~ U[0,1], PSO de inercia lineal y MSAPSO fiel sobre las curvas estáticas
**Qué hice.** `fase0_msapso_V2.py`: sobre las curvas P(I) estáticas de los 4 casos (sin dinámica de convertidor, como la Fase 0 de la V1), corrí (a) el MSAPSO fiel (determinista); (b) APSO (Eq. 12) con **ε ~ U[0,1] como en el paper**, sin el factor Isc·0.05 que yo había añadido en la V1;
(c) APSO con ε ~ U[−1,1] (la variante de la V1) para cuantificar el efecto de la discrepancia que señaló el profesor; (d) PSO de inercia lineal (ref. [40]: 10 partículas, t_max = 50, w 0.9→0.4, α = β = 2). Variable en por unidad (I/Isc); 30 semillas por caso en los estocásticos.
α y β de APSO no vienen en el paper: α ∈ {0.05, 0.1, 0.2} (barrido declarado) y β = 0.4.
**Por qué.** Era la petición explícita del profesor («correr de nuevo APSO corrigiendo el muestreo de ε»). Se mide contra el GMPP teórico porque aquí no hay convertidor.
**Resultado** (eficiencia % sobre el GMPP; media / mínimo de 30 semillas; casos 1 · 2 · 3 · 4):
| Algoritmo | Caso 1 | Caso 2 | Caso 3 | Caso 4 |
|---|---|---|---|---|
| MSAPSO fiel (determinista) | 100.00 | 100.00 | 100.00 | 99.94 |
| APSO ε~U[0,1] (paper), α = 0.05 | 100.00 / 99.98 | 99.93 / 99.66 | 97.79 / 88.01 | 99.85 / 99.55 |
| APSO ε~U[−1,1] (V1), α = 0.05 | 99.96 / 98.71 | 100.00 / 99.99 | 99.20 / 88.11 | 99.96 / 99.94 |
| APSO ε~U[0,1] (paper), α = 0.2 | 99.92 / 99.75 | 99.48 / 97.75 | 94.74 / 87.92 | 98.87 / 86.01 |
| APSO ε~U[−1,1] (V1), α = 0.2 | 100.00 / 99.98 | 99.99 / 99.93 | 96.82 / 88.04 | 99.94 / 99.74 |
| PSO inercia lineal | 100.00 / 100.00 | 100.00 / 100.00 | 99.21 / 88.12 | 99.98 / 99.94 |
**Lectura.** (1) La corrección del profesor importa: con ε ∈ [0,1] el ruido es de un solo signo y empuja a las partículas siempre hacia corrientes mayores, por lo que APSO resulta peor y más variable que con mi ε ∈ [−1,1] (p. ej. Caso 3, α = 0.2: 94.7 % vs 96.8 %; Caso 4, mínimo 86.0 % vs 99.7 %).
Mi APSO de la V1 era, pues, más favorable a APSO de lo que implica el paper. (2) La conclusión cualitativa de la V1 se mantiene: los algoritmos estocásticos (APSO, PSO) pueden caer a ~86–88 % en su peor semilla (quedan en el pico local del Caso 3),
mientras que el MSAPSO fiel, por su siembra determinista en rejilla, no baja de 99.94 %. (3) Esta fase es sobre la curva estática: no dice nada del desempeño con dinámica real (Pasos 2–8).
**Archivos.** `fase0_msapso_V2.py`, `resultados_V2/fase0_V2.txt|json`.
