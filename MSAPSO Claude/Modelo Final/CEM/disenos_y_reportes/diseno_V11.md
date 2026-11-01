# V11 (EXPLORATORIO) — MLP ubica el pico, CEM converge: primera aproximación rápida para el Frente B

Origen: idea 4 de la reunión del 28-oct-2026 (profesor Gerardo Jesús Camacho González) y resultado de la V10 (CEM puro es mal buscador global; hipótesis: sirve como refinador local).
Objetivo: ver «por encima» si hay señal antes de que el compañero del frente B profundice. **No es el estudio completo**: el MLP se entrena SUPERVISADO (cota superior de lo que ES/RL podrían lograr con la misma red).

## Método
1. Barrido de 7 mediciones en Isc·[0.1 … 0.95] (las posiciones iniciales del MSAPSO). 2. MLP (entradas: 7 potencias normalizadas por la mayor + mayor/P_nom; salida: x* = I_gmpp/Isc) entrenado con 8000 o 30000 sombras sintéticas (semilla 1111, sin tocar validación/prueba). 3. CEM con μ0 = x*, σ0 pequeña, parada por σ < δ.
Controles: **sin modelo** (CEM desde el mejor punto del barrido; mide la aportación real del MLP) y **solo MLP** (barrido + 1 medición en x*).

## Protocolo y criterios (fijados antes de correr)
- Validación: 200 curvas (3030/3031), sin ruido. Cuadrícula: MLP (datos ∈ {8000, 30000}, capas ∈ {(64,64), (128,128)}), σ0 ∈ {0.03, 0.06, 0.1, 0.15}, n ∈ {3, 5, 7}, k ∈ {1, 2}, α ∈ {0.7, 1}, δ ∈ {0.005, 0.01, 0.02}, t_max = 12, σ_min = 0.002. Misma cuadrícula (sin MLP) para el control.
- Selección: **principal** = menos mediciones con pérdida ≤ 0.10 pp frente al MSAPSO completo; si ninguna, la de **mayor exactitud con ≤ 70 mediciones** (presupuesto de la V7).
- Prueba fresca (4040/4041 + 4 reales; ruido 0/1/2 W; 1000 curvas 7777/7778) y dinámico (primeros 600 escenarios de la campaña V7). Nada se re-ajusta después de ver la prueba.
- Éxito: (1) < 70 mediciones con pérdida ≤ 0.10 pp; (2) el MLP aporta si MLP+CEM supera a «sin modelo» con IC95 % > 0 al mismo presupuesto; (3) dinámico: IC95 % > 0 y no peor que la V7.
