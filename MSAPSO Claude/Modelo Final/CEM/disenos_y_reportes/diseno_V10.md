# V10 — Cross-Entropy Method (CEM) puro como buscador de MPPT: diseño y criterios (escritos ANTES de correr)

Origen: reunión con el profesor Gerardo Jesús Camacho González (28-oct-2026). Pidió un examen exhaustivo de CEM (bajo qué situaciones funciona y bajo cuáles no) y del problema de varios picos.
Pregunta: ¿puede CEM reemplazar al MSAPSO (o a la V7) como buscador, con menos mediciones o más energía, sin entrenamiento?

## Método (CEM puro, sin modelo aprendido)
Sobre la corriente normalizada x = I / Isc ∈ [0, 1] se mantiene una gaussiana N(μ, σ²).
En cada iteración: (1) se muestrean n candidatos x_i ~ N(μ, σ²) recortados a [0, 1]; (2) se miden (1 medición cada uno, ordenados de menor a mayor corriente y alternando el sentido en iteraciones sucesivas, igual que el MSAPSO, para no forzar saltos grandes en el inductor);
(3) se toman los k mejores (élites) por potencia medida; (4) μ ← (1-α) μ + α media(élites), σ ← (1-α) σ + α std(élites), con piso σ ≥ σ_min.
Punto final: el de mayor potencia medida (igual que el MSAPSO). Reinicio de 5 W y asentamiento: idénticos para todos (entorno_V10.py = V7 sin cambios).
Variantes de parada: «completo» (t_max = 25 iteraciones, sin regla) y «parada» (σ < δ tras t_min = 3 iteraciones; es el análogo de la dispersión de la V7).
Diferencia con el MSAPSO: CEM no usa Gbest ni la beta del paper; la contracción la determina la dispersión de las élites. μ0 = 0.5 y σ0 se fijan (no se siembra con las 7 posiciones del paper).

## Protocolo (igual que la V7)
- **Validación** (elegir parámetros): 200 curvas (semillas 3030/3031), sin ruido. **Prueba** fresca: 4040/4041 más los 4 casos reales; con ruido 0, 1 y 2 W (parámetros NO re-ajustados).
- **Cuadrícula en validación:** n ∈ {5, 7, 10}; élites k ∈ {2, 3}; α ∈ {0.7, 1.0}; σ0 ∈ {0.2, 0.3}; σ_min ∈ {0, 0.01}; δ ∈ {0.01, 0.02, 0.03}.
- **Selección (criterio fijado antes de ver la prueba):**
  - *CEM de referencia (presupuesto completo, 25 iteraciones)*: la configuración con mayor exactitud final media: muestra el mejor desempeño posible de CEM.
  - *CEM principal*: entre las configuraciones con parada cuya exactitud final media en validación NO baja más de 0.10 pp de la del MSAPSO completo, la de MENOS mediciones.
  - Si ninguna cumple, se reporta la mejor relación y se declara que **CEM no iguala al MSAPSO en exactitud**.
- **Dinámico:** los primeros 600 escenarios de la campaña Monte Carlo de la V7 (semillas 100000 + idx, misma distribución de paneles, t_wait, regímenes de sombra y ruido), con la configuración congelada. El MSAPSO completo y la V7 se toman de los resultados ya guardados de la V7 (verificado: el entorno reproduce esos números exactamente).
- **IC95 %:** bootstrap pareado por escenario.

## Criterios de éxito (fijados antes de correr)
1. **Estático:** CEM *aporta* si, en PRUEBA, usa **menos de 70 mediciones** (las de la V7) con pérdida ≤ 0.10 pp de exactitud frente al MSAPSO completo. *Equivale* si usa ≈ 70 con pérdida similar. *No aporta* si necesita más mediciones o pierde > 0.10 pp.
2. **Varios picos:** se reporta, para cada método, el porcentaje de curvas con exactitud final < 98 % y < 95 %, y el peor caso. CEM *no* es robusto si ese porcentaje es mayor que el del MSAPSO completo.
3. **Dinámico:** CEM *aporta* si su diferencia de energía contra el MSAPSO tiene IC95 % por encima de 0 **y** no es peor que la V7; reportar por régimen de sombra y la cola de riesgo (percentiles 1 y 5, peor caso, % que pierde > 3 pp).
4. **Honestidad:** se reportan los resultados negativos y la causa. Nada se re-ajusta después de ver la prueba o la campaña.

## Qué NO se hace en este paso
Variantes para varios picos (élites por grupos, mezcla de gaussianas), MLP, DGO: se deciden después de ver estos resultados, con sus propios criterios.

## Aclaración declarada tras ver la VALIDACIÓN y ANTES de evaluar la prueba
Al ver la validación se detectaron dos fallas en la redacción del criterio (no en los datos de prueba, que aún no se han mirado):
1. «Presupuesto completo = 25 iteraciones» con n = 10 candidatos son 250 mediciones (más que las 175 del MSAPSO). La referencia justa es **la mejor configuración con ≤ 175 mediciones**; la de 250 se reporta solo como información adicional.
2. Con σ_min ≥ δ la parada nunca se activa (σ no puede bajar de δ). Esas configuraciones se excluyen de «con parada».
Además de la configuración «principal» (criterio ≤ 0.10 pp), se evalúan en la prueba: **CEM ≤ 175 mediciones** (mejor exactitud con parada y ≤ 175), **CEM ≤ 70 mediciones** (mismo presupuesto que la V7) y la referencia sin parada ≤ 175. Todo definido con la validación; la prueba no modifica ninguna elección.
