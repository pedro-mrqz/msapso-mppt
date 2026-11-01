# V12 (control) — MSAPSO corto + CEM frente a MLP + CEM

Pregunta: ¿el MLP de la V11 aporta algo que el propio MSAPSO no da gratis? Control justo de la V11: en vez del MLP, un MSAPSO CORTO (pocas pasadas, sin entrenamiento) ubica el pico y su Gbest siembra a CEM (μ0 = Gbest/Isc, σ0 pequeña); parada por σ < δ.

## Protocolo (igual que V10/V11; fijado antes de correr)
- **Cuadrícula en validación** (200 curvas, 3030/3031, sin ruido): pasadas del MSAPSO T0 ∈ {2, 3, 4, 5, 6}; beta ∈ {del paper (t_max = 25), comprimida a T0}; CEM: σ0 ∈ {0.03, 0.06, 0.1}, n ∈ {3, 5, 7}, k ∈ {1, 2}, α ∈ {0.7, 1}, δ ∈ {0.005, 0.01, 0.02}, t_max = 12, σ_min = 0.002.
- **Selección:** (a) *principal*: menos mediciones con pérdida ≤ 0.10 pp frente al MSAPSO completo; (b) si ninguna, **mayor exactitud con ≤ 40 mediciones** (mismo presupuesto que MLP + CEM de la V11, ≈ 37) y también con ≤ 70 (presupuesto de la V7).
- **Prueba** fresca (4040/4041 + 4 reales; ruido 0/1/2 W; 1000 curvas 7777/7778) y **dinámico** (los primeros 600 escenarios de la campaña V7). Se compara contra MSAPSO completo, V7 y MLP + CEM (modelo y configuración de la V11, sin cambios). IC95 % bootstrap pareado.
## Criterios de lectura (antes de correr)
- **MSAPSO corto + CEM iguala o supera a MLP + CEM** si su diferencia pareada de energía dinámica contra MLP + CEM tiene IC95 % que incluye 0 o es positiva, **y** su exactitud estática no es peor: entonces el MLP no aporta y se descarta por simplicidad.
- **El MLP aporta** si MLP + CEM supera a MSAPSO corto + CEM con IC95 % por encima de 0 en dinámico o en estático.
- Se reportan siempre cola de riesgo (p1, peor, % que pierde > 3 pp) y los 4 casos reales.
