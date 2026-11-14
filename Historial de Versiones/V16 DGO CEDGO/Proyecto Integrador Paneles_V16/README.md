# V16 — DGO (Tang y Fong) y CEDGO (con CEM) como buscadores de MPPT — versión confirmada por el profesor
Diseño y criterios fijados antes de correr: `diseno_V16.md`. Código: `dgo_V16.py`, `campana_V16.py` (`sel`, `val`, `test`, `conf`, `S`). Resultados: `resultados_V16/dgo_*_V16.txt`; referencias de la V15 (DGBCO) en `resultados_V16/ref_V15/`.

Elegida en validación (ninguna de las 32 configuraciones pasó el filtro de cola estática): **CEDGO** (DGO con operador CEM), 8 individuos, 5 generaciones (40 mediciones), inicio aleatorio, retroceso 2 %.

| Energía (pp) | Prueba 0–599 | Confirmación 1200–2399 |
|---|---|---|
| CEDGO − MSAPSO completo | +2.09 [+1.30, +2.88] | +1.98 [+1.39, +2.54] |
| CEDGO − V7 | **−0.89 [−1.54, −0.25]** | **−0.81 [−1.32, −0.31]** |
| CEDGO − candidata V14 | −2.22 [−2.83, −1.61] | −2.41 [−2.87, −1.96] |
| CEDGO − DGBCO (V15) | −1.72 [−2.35, −1.14] | −1.66 [−2.08, −1.23] |
| Pierde > 3 pp vs MSAPSO | 23 % | 22 % |

Cola estática (1000 curvas): pérdida media 3.36 pp, p99 28.9 pp, máximo 59.2 pp, 27.6 % de curvas con pérdida > 3 pp (V7: 0.05 / 0.64 / 0.97).

## Veredicto contra los criterios
(a) Ventaja sobre la V7: **NO** (pierde, con IC que excluye 0 en prueba y en confirmación). (b) Sin celdas con debilidad < −1 pp: NO (7 y 11 celdas con debilidad demostrable; −4 a −5.5 pp con t_wait de 0.5 ms). (c) Pierde > 3 pp en ≤ 10 %: NO (22–23 %). (d) Cola estática: NO, la peor de todos los métodos probados.
Lectura: con 40–70 mediciones el DGO/CEDGO no supera a la V7 ni al MSAPSO en exactitud, y solo gana con t_wait de 5 ms y sombra muy cambiante. Con esta evidencia no hay razón para sustituir a la V7.
Reservas: interpretaciones propias de partes que el paper no precisa (número de grupos, α0, Mr, λ, Lr, TtL; no se ajustaron); se usaron las ecuaciones del DGO tal como las reproduce el paper de 2017 (CEDGO), no el original de 2016; los autores lo evaluaron en funciones de referencia con poblaciones de 30 y presupuestos de miles de evaluaciones, no con 40–70 mediciones; solo simulación; sin corrección por comparaciones múltiples.
