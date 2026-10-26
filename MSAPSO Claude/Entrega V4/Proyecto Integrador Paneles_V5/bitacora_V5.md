# Bitácora de trabajo — Corrida V5 (formulación corregida y comparación de algoritmos, nivel 1)

Documento vivo: cada entrada registra QUÉ se hizo, POR QUÉ (razonamiento), cómo se VERIFICÓ, QUÉ RESULTÓ y QUÉ ARCHIVOS lo respaldan. De aquí se compila el PDF.

## Contexto y punto de partida (octubre 2026)
- La V4 (carpeta `Proyecto Integrador Paneles_V4/`) no se modifica. Implementó el esquema del profesor (N potencias medidas como observación, MLP, política gaussiana, muestreo de puntos aledaños) y concluyó que, con esa formulación, REINFORCE-MLP y PPO no superaban a la referencia sin aprendizaje «mejor de 7 + 5 gaussianas»; 15 veces más entrenamiento no cambiaba el resultado.
- Causa probable identificada en la V4: la recompensa promediaba la potencia de las muestras, lo que empuja σ a cero (en PPO σ cayó a 0.013) y no premia al MEJOR punto, que es el que se elige al final.
- Esta corrida (V5) aplica tres correcciones de raíz y, como el resultado mejora, compara REINFORCE, PPO, SAC, DDPG y un árbol de decisión sobre la MISMA formulación. Sigue en el NIVEL 1 (potencia estática, sin dinámica del convertidor), sin GMPP real en entrenamiento y con el rango de corrientes fijado con la Isc nominal (8.9 A).
- Evaluación común: 100 patrones sintéticos nuevos (semilla 2026, distintos de los de entrenamiento) y los 4 casos reales; eficiencia final (punto elegido / GMPP), energía en una ventana de 200 mediciones y número de mediciones (N + K).

---
## PASO 1 — Las tres correcciones de raíz y su implementación en REINFORCE
**Qué hice.** `reinforce_nn_V5.py`: (a) recompensa de GRUPO: `max` = la mejor de las K muestras (potencia medida) o `gain` = max(0, mejor muestra − mejor punto del barrido), en lugar de la potencia media de cada muestra; el gradiente pasa a ser ∇J = E[(G − b)·Σ_k (a_k − μ)/σ²·∇μ]. (b) σ FIJA o DECRECIENTE (de σ₀ a σ₁), sin aprenderla. (c) K de entrenamiento distinto del K de evaluación (5 o 20 muestras al entrenar, 5 al evaluar). Baselines de valor (V(obs) aprendida) o de media móvil.
**Por qué.** Se ataca la causa probable de la V4: el objetivo promedio premia concentrar todas las muestras en el mismo punto; el objetivo de grupo premia que ALGUNA muestra supere lo ya conocido, que es lo que se usa al final.
**Verificación.** Solo potencias medidas en la recompensa y en la observación (sin GMPP); evaluación en patrones nuevos.
**Archivos.** `reinforce_nn_V5.py`.

---
## PASO 2 — Malla de REINFORCE corregido (N = 7, K = 5)
**Qué hice.** `grid_reinforce_V5.py`: recompensa (`mean` de la V4, `max`, `gain`) × baseline (valor, media móvil) × K de entrenamiento (5, 20) × σ (0.05 fija; decreciente 0.15 → 0.03), 3 semillas, 4000 actualizaciones. 24 configuraciones.
**Resultado.** La mejor configuración en sintéticos fue `gain`, baseline de valor, K de entrenamiento 5, σ = 0.05 fija: 97.54 % de exactitud final y 95.60 % de energía (referencia sin aprendizaje: 97.22 y 95.36 %; la V4: 96.7 y 94.9 %). La diferencia con la referencia (≈ +0.3 pp) está dentro del ruido. El punto μ solo (una medición) sube de ≈ 94.4 a ≈ 95.7 %.
**Lectura.** Con N = 7 las correcciones por sí solas mueven poco el resultado: ya queda poco margen sobre un control simple. La pregunta pasó a ser DÓNDE hay margen (Paso 3).
**Archivos.** `grid_reinforce_V5.py`, `resultados_V5/reinforce_grid_V5.txt|json`.

---
## PASO 3 — ¿Dónde hay margen? Barrido de N y K, con un control más fuerte
**Qué hice.** `margen_NK_V5.py` y `control_parabolico_V5.py`: para N ∈ {3, 4, 5, 7, 10} y K ∈ {3, 5}, comparé tres cosas sobre 100 sintéticos nuevos: el control simple («mejor de N + K gaussianas»), un control sin aprendizaje más fuerte (ajuste de una parábola a los 3 puntos vecinos del mejor del barrido y K gaussianas alrededor de su vértice) y REINFORCE corregido. También una cota supervisada de diagnóstico (MLP con el GMPP como etiqueta; NO es un método válido bajo la regla del profesor).
**Por qué.** El profesor pidió «muy pocos muestreos»; con N = 7 un control simple ya iguala, pero con N pequeño la información del barrido es escasa y un modelo podría aportar más. El control parabólico evita comparar contra un control demasiado débil.
**Resultado (final / energía en sintéticos).**
| N, K (mediciones) | Control simple | Control parabólico | REINFORCE corregido |
|---|---|---|---|
| 3, 3 (6) | 80.8 / 80.0 | 86.7 / 85.8 | 90.3 / 89.2 |
| 5, 3 (8) | 93.9 / 92.6 | 94.0 / 92.7 | 96.4 / 94.9 |
| 5, 5 (10) | 94.7 / 93.3 | 94.7 / 93.3 | 96.9 / 95.2 |
| 7, 5 (12) | 97.2 / 95.4 | 96.8 / 95.0 | 97.5 / 95.6 |
| 10, 5 (15) | 98.4 / 95.9 | 98.5 / 96.0 | 98.2 / 95.7 |
**Lectura.** El control parabólico NO mejora al simple; REINFORCE corregido gana ≈ 2–3 pp con N entre 3 y 5 y casi nada con N ≥ 7. El margen está en pocas mediciones.
**Archivos.** `margen_NK_V5.py`, `control_parabolico_V5.py`, `resultados_V5/margen_NK_V5.txt`, `resultados_V5/control_parabolico_V5.txt`.

---
## PASO 4 — Cinco algoritmos sobre la misma formulación
**Qué hice.** `algoritmos_V5.py` y `comparar_algoritmos_V5.py`, con N ∈ {3, 5, 7}, 3 semillas, K = 3 y 5, σ de evaluación = 0.05·Isc_nominal: REINFORCE corregido (recompensa `gain`, baseline de valor, σ fija); PPO, SAC y DDPG de stable-baselines3 sobre un entorno de UN paso (`pvsim_V5/bandit_env_V5.py`, recompensa `gain`, banco precalculado de 10 000 curvas), PPO con σ congelada y DDPG con ruido gaussiano de exploración; y el ÁRBOL DE DECISIÓN dentro del bucle de RL, recalculado en cada iteración: se muestrean K = 10 acciones alrededor de la propuesta actual, se mide la potencia y el árbol (profundidad 10) se reajusta con la mejor acción MEDIDA de cada patrón si mejora al barrido, con σ decreciente (0.15 → 0.04) en 15 iteraciones. Solo potencias medidas. Entrenamiento: PPO 300 mil pasos (≈ 25 s), SAC y DDPG 100 mil pasos (160–260 s), árbol ≈ 2 s.
**Evaluación.** Se mide el barrido de N puntos, el modelo propone μ y se toman K muestras N(μ, σ²); se elige la mejor leída.
**Resultado (K = 5, sin ruido; 100 sintéticos nuevos, final / energía; media de 3 semillas).**
| N (mediciones) | Control simple | Control parabólico | REINFORCE | PPO | SAC | DDPG | Árbol |
|---|---|---|---|---|---|---|---|
| 3 (8) | 83.2 / 82.2 | 88.4 / 87.4 | 93.9 / 92.6 | 93.9 / 92.6 | 95.6 / 94.4 | 95.6 / 94.5 | 95.5 / 94.3 |
| 5 (10) | 94.7 / 93.3 | 94.7 / 93.3 | 97.1 / 95.4 | 96.6 / 94.9 | 97.2 / 95.6 | 97.6 / 96.0 | 97.7 / 96.2 |
| 7 (12) | 97.2 / 95.4 | 96.8 / 95.0 | 97.6 / 95.6 | 97.1 / 95.1 | 97.4 / 95.4 | 97.5 / 95.5 | 98.5 / 96.5 |
Las desviaciones entre semillas son de 0.03 a 0.8 pp (el árbol: 0.04–0.05 con N = 5 y 7). Con K = 3 el orden es el mismo (con N = 5: control 93.9 / 92.6; árbol 96.95 / 95.5; DDPG 96.8 / 95.4).
**Lectura.** (1) Con N = 5 y 10 mediciones, DDPG y el árbol ganan ≈ 3 pp de exactitud y de energía a ambos controles. (2) Con N = 7 y 12 mediciones el árbol supera incluso al control con 15 mediciones (98.5 / 96.5 contra 98.4 / 95.9). (3) El árbol es el más barato (2 s de entrenamiento). (4) PPO y REINFORCE quedan algo por debajo de SAC, DDPG y árbol, aunque por encima de los controles con N de 3 a 5. (5) Corrijo una afirmación de la V4: la «cota supervisada» (98.1 %) no era un techo; el árbol, que solo usa potencias medidas, la supera (98.5 %).
**Resultados en los 4 casos reales (N = 5, K = 5, final / energía).** control 95.5 / 94.2; REINFORCE 97.7 / 95.8; SAC 98.7 / 97.0; DDPG 97.0 / 95.4; PPO 95.9 / 94.0; árbol 94.5 / 92.8. Con N = 7: control 93.5 / 91.7; REINFORCE 96.8 / 94.7; SAC 97.5 / 95.3; DDPG 98.5 / 96.3; árbol 97.7 / 95.5; PPO 94.0 / 91.7. Son solo 4 casos: ver el Paso 6.
**Archivos.** `algoritmos_V5.py`, `comparar_algoritmos_V5.py`, `pvsim_V5/bandit_env_V5.py`, `resumen_comparar_V5.py`, `resultados_V5/comparar_N*.json`, `resultados_V5/resumen_comparar_V5.txt`.

---
## PASO 5 — Ruido de medición (1 y 2 W)
**Qué hice.** El mismo experimento del Paso 4 (N = 5 y 7, K = 5, 3 semillas) con ruido gaussiano aditivo de 1 y 2 W en TODAS las potencias leídas (barrido y muestras), tanto en el entrenamiento como en la evaluación.
**Resultado (100 sintéticos nuevos, final / energía).**
| Ruido, N | Control simple | REINFORCE | PPO | SAC | DDPG | Árbol |
|---|---|---|---|---|---|---|
| 1 W, N = 5 | 94.6 / 93.2 | 97.0 / 95.3 | 96.6 / 95.0 | 97.1 / 95.5 | 97.5 / 95.8 | 97.2 / 95.7 |
| 1 W, N = 7 | 96.9 / 95.1 | 97.5 / 95.4 | 97.1 / 95.1 | 97.5 / 95.5 | 97.7 / 95.7 | 98.1 / 96.1 |
| 2 W, N = 5 | 94.5 / 93.1 | 97.0 / 95.3 | 96.5 / 94.9 | 97.0 / 95.4 | 97.2 / 95.5 | 96.7 / 95.1 |
| 2 W, N = 7 | 96.7 / 94.9 | 97.1 / 95.1 | 97.2 / 95.2 | 97.3 / 95.3 | 97.3 / 95.4 | 97.8 / 95.9 |
**Lectura.** (1) La ventaja sobre los controles se mantiene (+2 a +3 pp con N = 5; +0.5 a +1.4 con N = 7). (2) El orden entre métodos cambia un poco: el árbol es el mejor con N = 7, pero con 2 W y N = 5 baja a 96.7 y DDPG pasa al frente; SAC y DDPG parecen más robustos. (3) En los 4 reales, REINFORCE es consistentemente bueno (96.6–97.2) y PPO falla con N = 7 (≈ 93 %).
**Alcance.** Es ruido estático en el nivel 1; en el nivel dinámico el ruido interactúa con el umbral de 5 W de reinicio, que no se probó.
**Archivos.** `resultados_V5/comparar_N*_ruido*.json`, `resultados_V5/resumen_comparar_V5.txt`.

---
## PASO 6 — Revisión de los casos reales (¿por qué el árbol falla en algunos?)
**Qué hice.** `revision_reales_V5.py`: diagnóstico por caso real y prueba de una causa probable, el DESAJUSTE DE DISTRIBUCIÓN. El caso 3 tiene Isc = 3.25 A y, como el rango se fija con la Isc NOMINAL (8.9 A), solo 2 de los 5 o 7 puntos del barrido tienen potencia; en el banco sintético original solo el 2.1 % de los patrones tenían Isc menor a 4.5 A. Entrené el árbol con un banco con ATENUACIÓN GLOBAL (con probabilidad 0.5 todas las irradiancias se multiplican por U[0.25, 1]; el 23 % de los patrones pasan a tener Isc baja), `build_pool_aug` en `reinforce_nn_V5.py`, y lo evalué también en 100 sintéticos NUEVOS con atenuación global (semilla distinta).
**Resultado (eficiencia final, K = 5, árbol con 3 semillas).**
| | Reales (media de 4) | Sintéticos originales | Sintéticos atenuados |
|---|---|---|---|
| N = 5, control simple | 95.6 | 94.7 | 91.5 |
| N = 5, árbol (banco original) | 94.4 | 97.7 | 95.1 |
| N = 5, árbol (con atenuación) | 96.0 | 97.5 | 96.2 |
| N = 7, control simple | 95.0 | 97.2 | 95.2 |
| N = 7, árbol (banco original) | 96.8 | 98.5 | 96.7 |
| N = 7, árbol (con atenuación) | 97.0 | 98.6 | 97.2 |
Por caso (N = 5, control / árbol original / árbol con atenuación): caso 1: 99.9 / 99.9 / 99.9; caso 2: 94.9 / 92.5 / 96.3; caso 3: 89.4 / 87.4 / 89.3; caso 4: 98.2 / 97.6 / 98.5.
**Lectura.** La atenuación global corrige en parte la caída (N = 5: de 94.4 a 96.0 en reales, por encima del control) y mejora los sintéticos atenuados (95.1 → 96.2). El caso 3 sigue siendo el más débil para todos (≈ 87–92 %): con el rango fijado por la Isc nominal casi no hay puntos útiles en el barrido.
**Advertencia metodológica.** La idea de la atenuación se propuso DESPUÉS de ver el fallo en los reales, por lo que esos 4 casos dejan de ser un conjunto de prueba puro; por eso se validó también con sintéticos nuevos. Las cifras de los Pasos 4 y 5 usan el banco original.
**Archivos.** `revision_reales_V5.py`, `resultados_V5/revision_reales_V5.txt`.
