# V14 — Campaña completa y pruebas de estrés de la candidata «MSAPSO corto + CEM + retroceso 2 %»

Candidata CONGELADA (V12/V13, nada se re-ajusta): MSAPSO de T0 = 3 pasadas (β comprimida) → CEM (n = 7, k = 2, α = 0.7, σ0 = 0.03, δ = 0.005), 39 mediciones en mediana; corriente de operación = 0.98 · I_elegida (b = 0.02, elegido en validación 600–1199 de la V13).
Referencias: MSAPSO completo (paper) y V7 (parada por dispersión < 0.02), ambos con b = 0, tomados de `campana_V7_referencia.jsonl` (el entorno reproduce la V7 exacto con b = 0).

## Qué se corre
1. **Campaña completa (C):** los 2400 escenarios de la campaña V7 (semillas 100000 + idx), que ya mezclan 5 paneles, 4 t_wait, 6 regímenes de sombra (único, moderado, alto, muy alto, flicker, estable) y ruido 0/1/2 W. Candidata con b = 0.02 y con b = 0 (aísla el retroceso). Resultados globales y DESGLOSADOS por panel, t_wait, régimen, ruido y fuente (reales/sintéticos). Los índices 600–1199 se usaron para elegir b: se reportan aparte (0–599 prueba, 1200–2399 confirmación) y el total solo como referencia.
2. **Cola estática (S):** 1000 curvas frescas (semillas 7777/7778, las de la V7.1): pérdida de exactitud final vs MSAPSO completo, media, p95, p99, máximo, % con pérdida > 0.5 pp.
3. **Otros paneles estáticos (P):** 100 curvas por panel (semilla 5151), 4 paneles, como en la V7.1.

## Criterios de lectura (fijados antes de correr)
Diferencia de energía = candidata − V7, IC95 % bootstrap pareado, por celda del desglose (celdas con ≥ 30 escenarios).
- **Ventaja demostrable** de una celda: límite inferior > 0. **Debilidad demostrable:** límite superior < 0.
- **La candidata resiste** (se puede proponer como alternativa a la V7 en dinámico) si TODAS se cumplen: (a) ventaja global demostrable sobre la V7 en 1200–2399 y en 0–599; (b) ninguna celda con debilidad demostrable peor que −1 pp; (c) % de escenarios que pierden > 3 pp contra el MSAPSO completo no mayor a 10 %; (d) cola estática: pérdida media ≤ 0.5 pp y p99 ≤ 3 pp en S y en cada panel de P.
- Si falla (b) o (d) se declara la condición de uso en que falla; si falla (a), la V7 sigue siendo la recomendación.
- Se reporta también cuántas celdas son debilidad / ventaja / indeterminadas.

## Reservas conocidas antes de correr
Solo simulación; sin corrección por comparaciones múltiples (decenas de celdas); b se decidió tras ver V12; las celdas pequeñas tienen IC amplios.
