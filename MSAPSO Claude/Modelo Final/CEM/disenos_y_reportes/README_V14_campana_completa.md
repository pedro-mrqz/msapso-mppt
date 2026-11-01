# V14 — Campaña completa y cola estática de «MSAPSO corto + CEM + retroceso 2 %»
Criterios fijados antes de correr: `diseno_V14.md`. Resultados: `resultados_V14/campana_V14.txt`, `refuerzo_S_V14.txt`, `refuerzo_P_V14.txt`.
Correr: `python3 campana_V14.py` (≈2 min, 8 núcleos); `python3 refuerzo_V14.py S` y `P`.

## Veredicto contra los criterios
(a) Ventaja global sobre la V7: CUMPLE. 2400 escenarios: +1.54 pp [+1.31, +1.78]; prueba +1.33, confirmación +1.60.
(b) Ninguna celda con debilidad peor que −1 pp: CUMPLE. De 37 celdas, 31 ventaja, 5 indeterminadas, 1 debilidad: t_wait = 0.5 ms (−0.67 [−1.21, −0.09]).
(c) Pierde > 3 pp en ≤ 10 %: CUMPLE (7 %; V7 8 %).
(d) Cola estática (media ≤ 0.5 pp y p99 ≤ 3 pp): NO CUMPLE. 1000 curvas: pérdida media 0.88 pp (con retroceso), p99 13.0 pp, máximo 23.0 pp; V7: 0.05 / 0.64 / 0.97. Con otros paneles el p99 llega a 6–13 pp (el panel de 36 celdas sí queda bien).
Conclusión: la candidata gana en energía dinámica en casi todo (+1.5 pp sobre la V7), pero tiene cola de fallos grave (en ≈ 3 % de curvas pierde > 3 pp en estático): MSAPSO de 3 pasadas a veces se queda en un pico equivocado y el CEM lo refina. La V7 sigue siendo la recomendación segura; la candidata requeriría un respaldo contra la cola (p. ej. verificación o más pasadas cuando la dispersión sea alta), que no se probó.
Reservas: simulación; sin corrección por comparaciones múltiples; b se eligió tras ver V12; índices 600–1199 se usaron para elegir b.
