# V17 — DecentCEM (versión del profesor: barrido uniforme + workers por pico) como buscador de MPPT
Diseño y criterios fijados antes de correr: `diseno_V17.md`. Código: `decentcem_V17.py`, `campana_V17.py` (`sel`, `val`, `test`, `conf`, `S`). Resultados: `resultados_V17/dc_*_V17.txt`; referencias (V16) en `resultados_V17/ref/`.

Elegida en validación (entre 6 con p99 estático ≤ 5 pp; ninguna ≤ 3): **barrido de 10 puntos, élites → workers con τ = 0.15, σ fija = 0.03, 4 muestras × 4 iteraciones, sin retroceso** (≈ 40 mediciones).

| Energía (pp) | Prueba 0–599 | Confirmación 1200–2399 |
|---|---|---|
| V17 − MSAPSO completo | +3.41 [+2.66, +4.15] | +3.13 [+2.59, +3.65] |
| V17 − V7 | **+0.43 [−0.14, +0.99]** | **+0.35 [−0.11, +0.79]** |
| V17 − V7 + retroceso 2 % (plan B) | +0.35 [−0.24, +0.90] | −0.01 [−0.46, +0.43] |
| V17 − candidata V14 | −0.90 [−1.47, −0.34] | −1.26 [−1.68, −0.82] |
| Pierde > 3 pp vs MSAPSO | 14 % | 17 % |

Cola estática (1000 curvas, 7777/7778): 40.2 mediciones, pérdida media 0.245 pp, p95 1.65, **p99 5.34**, máx 7.64, 2.3 % > 3 pp (V7: 0.05 / p99 0.64 / máx 0.97; candidata V14: 0.365 / p99 12.7 / máx 22.8).

## Veredicto contra los criterios
(a) Ventaja demostrable sobre la V7: **NO** (el IC incluye 0 en prueba y confirmación). (b) Sin debilidad demostrable < −1 pp: **NO** (t_wait 0.5 ms: −3.7 y −5.2 pp; en prueba además régimen «único»). (c) Pierde > 3 pp en ≤ 10 %: **NO** (14–17 %). (d) Cola estática: media sí (≤ 0.5), p99 **NO** (5.3 > 3).
Lectura: la hipótesis de la cola se confirma en parte (p99 estático de 12.7 a 5.3 pp y máximo de 22.8 a 7.6 pp frente a la candidata V14, con ≈ 40 mediciones), pero la energía dinámica no supera a la V7 y es menor que la de la candidata V14 (que usa retroceso). Solo gana con t_wait de 5 ms (+2.8/+3.4 pp). La V7 sigue como método principal.
σ fija superó a σ con piso en todas las configuraciones elegibles; el DecentCEM «del paper» (M fijo, 3 instancias) tuvo la peor cola (p99 ≈ 15 pp).
Reservas: el filtro estático (p99 ≤ 5, fijado antes) dejó fuera todas las variantes con retroceso 2 % (que en estático pierden más), así que «V17 + retroceso» no se evaluó dinámicamente (sería exploratorio); 68 configuraciones y sin corrección por comparaciones múltiples (6 finalistas separadas por 0.25 pp en validación); papers leídos con resumen automático; CE-Mixture no implementado (requiere modelo sustituto); solo simulación.
