# V18 — Neuroevolución: la red de la V11 entrenada con CEM sobre sus pesos, sin retropropagación

Frente B. Pregunta del equipo: ¿qué pasa si el MLP (Multi-Layer Perceptron, red neuronal de capas densas) no se entrena con retropropagación,
sino tratando cada parámetro como la media de una distribución, muestreando redes, evaluando la potencia que logran en las curvas,
quedándose con las mejores y volviendo a muestrear? Es el CEM (Cross-Entropy Method) aplicado a los **pesos** de la red, no a la corriente.

Escrito ANTES de correr el entrenamiento definitivo, la validación y la prueba. Lo único corrido antes es un piloto de tiempos y convergencia
(sección «Piloto»), que usa solo datos de entrenamiento y un conjunto de monitoreo (semilla 2222) que no es validación ni prueba.

## Punto de partida
- **V11** (MLP + CEM, Frente B, exploratoria): barrido de 7 mediciones → una red 8 → 64 → 64 → 1 entrenada **supervisada** (retropropagación,
  regresión de x* = I_gmpp/Isc, 30000 curvas, semilla 1111) predice dónde está el pico → CEM sobre la corriente refina. ≈ 37 mediciones;
  +1.37 pp de energía dinámica sobre la V7, pero −0.74 pp de exactitud estática y 11–12 % de curvas por debajo de 98 %.
  Su diseño decía que el entrenamiento supervisado es la «cota superior» de lo que ES (Evolution Strategies) o RL podrían lograr con la misma red.
  Eso es cierto para el error contra x*, pero no para la potencia: la regresión promedia entre picos parecidos, y un punto intermedio puede no tener potencia.
  Un entrenamiento sin gradiente puede optimizar directamente la potencia (y su cola), que no es diferenciable respecto a los pesos.
- **V7** (MSAPSO con parada por dispersión < 0.02): 70 mediciones, p99 estático 0.64 pp. Método principal.
- **V14** (MSAPSO de 3 pasadas + CEM sobre la corriente + retroceso 2 %): +1.54 pp sobre la V7, p99 estático 13 pp.
- **V17** (V14 + verificación por cota física): +1.79 pp sobre la V7, p99 estático ≤ 2.4 pp. Es el **listón para ES/RL** fijado en su diseño.

## Método
**Entrenamiento (CEM sobre los pesos).** Red con la misma forma y activaciones que la V11 (ReLU, salida lineal recortada a [0, 1]), mismas entradas
(7 potencias del barrido normalizadas por la mayor, y la mayor / P_nom) y **mismos datos** (`make_dataset(30000, 1111)` de la V11).
1. Cada parámetro θ_i ~ N(μ_i, σ_i²), independiente. Inicio: μ = 0, σ = escala de He (√(2/entradas)) en pesos y 0.1 en sesgos.
2. Cada generación: se muestrean 200 redes y se eligen 2000 curvas al azar de las 30000 (las mismas para las 200 redes).
3. Puntaje de una red = potencia relativa en el punto que predice, p = P(x̂)/P_gmpp, en esas curvas: **media(p) + cola · media del 10 % peor de p**.
4. Élites = las 20 mejores (10 %). μ ← 0.3 μ + 0.7 media(élites); σ ← 0.3 σ + 0.7 desv(élites) + ruido extra que decrece linealmente de 0.05·σ_inicial a 0.
5. 2000 generaciones. La red final es μ.

**Despliegue (igual que la V11).** Barrido de 7 mediciones → la red predice x̂ → CEM sobre la corriente (el de la V11: n = 7, k = 2, α = 0.7, δ = 0.005)
desde x̂ → retroceso del 2 %. Opcional: la verificación final por cota física de la V17 (hasta 4 sondeos donde la cota con corriente pedida supere Pbest·1.05).

**Rejilla (24 variantes).** Capas ∈ {16×16, 32×32, 64×64} × cola ∈ {0, 1} (6 redes) × σ0 del refinado ∈ {0.03, 0.1} × cota ∈ {no, sí}.

**Control de la pregunta principal.** La red de la V11 con exactamente el mismo despliegue que la variante elegida (mismo σ0, misma cota):
solo cambian los pesos. Si la elegida es «64×64, σ0 = 0.1, sin cota», el control es la V11 tal cual.

## Piloto (antes de escribir este diseño; solo entrenamiento y monitoreo 2222)
- Tiempo: ≈ 0.02 s por generación (16×16) y ≈ 0.08 s (64×64) con un hilo; entrenar las 6 redes tarda ≈ 5 min.
- Con 800 generaciones la red 64×64 no había convergido (potencia media en el punto predicho 0.908 contra 0.924 con 2000); se fija 2000.
- Un primer objetivo con ventana (mejor potencia a ±0.05·Isc de la predicción) se degeneró: la red aprendía a caer a 0.05 del pico, incluso
  fuera de la curva (p1 = 0). Se descartó y se sustituyó por el objetivo con cola. Sin cola, la red 16×16 llegó a 0.925 de potencia media en
  el punto predicho; la red de la V11 obtiene ≈ 0.876 en sus propios datos de entrenamiento.

## Selección (validación)
- Estático: 1000 curvas 8080/8081 (panel base) + 100 curvas por panel (semilla 6161) en los otros 4 paneles (los de la V17).
- Dinámico: escenarios 600–1199 de la campaña.
- Regla: entre las variantes con p99 ≤ 3 pp (b = 0.02) en los 5 conjuntos estáticos de validación, la de mayor energía dinámica media en 600–1199.
  Empate (< 0.1 pp): la de menos mediciones estáticas. Si **ninguna** pasa el filtro, se elige la de menor p99 máximo y se reporta que falla el criterio 1.

## Prueba (variante congelada)
- Estático: S (7777/7778, 1000 curvas), P (5151, 4 paneles), frescos 9393/9394 y paneles 5252 (los de la V17), y los 4 casos reales del paper.
  Con ruido de 1 y 2 W como reporte adicional (sin criterio).
- Dinámico: 0–599 (prueba) y 1200–2399 (confirmación). Referencias en cada escenario: MSAPSO completo, V7, V14, V17, V11 y el control.

## Criterios (fijados antes de correr)
0. **Pregunta principal (CEM sobre pesos contra retropropagación, mismo despliegue):** se reporta V18 − control en pérdida estática media, p99
   estático y energía dinámica (IC95 % bootstrap pareado). «Mejor» si la energía dinámica tiene límite inferior > 0 en prueba y confirmación y el
   p99 estático en S no empeora; «peor» si el límite superior < 0; si no, «sin diferencia demostrable».
1. **Cola estática:** p99 ≤ 3 pp (b = 0.02) en S, en cada panel de P y en los conjuntos frescos.
2. **Ganancia dinámica sobre la V7:** límite inferior del IC95 % > 0 en 0–599 y en 1200–2399.
3. Criterios (b) y (c) de la V14: ninguna celda del desglose con debilidad peor que −1 pp contra la V7; pierde > 3 pp contra el MSAPSO completo en ≤ 10 % de los escenarios.
4. **Listón ES/RL (V17):** la V18 lo supera si V18 − V17 tiene límite inferior > 0 en prueba y confirmación y cumple 1. Si V18 − V17 queda
   dentro de ±0.3 pp y cumple 1, es «equivalente con entrenamiento» (y la V17 se prefiere por no necesitar entrenamiento).

Si cumple 1–3 y supera el 4, la V18 se propone en lugar de la V17. Si no, la V17 sigue siendo la candidata en dinámico y la V7 el método principal.

## Reservas conocidas antes de correr
Solo simulación, con una reproducción propia del MSAPSO. Sin corrección por comparaciones múltiples. La red se entrena solo con el panel base
(como la V11), pero se prueba en 5 paneles. Los escenarios 600–1199 ya se usaron en la V14 y en la V17 para elegir. S y P ya se reportaron antes
(por eso se agregan los conjuntos frescos). El objetivo con cola y el número de generaciones se fijaron después del piloto (solo con datos de
entrenamiento y monitoreo).

## Revisiones tras la validación (escritas ANTES de abrir la prueba)
**Resultado de la validación V18 (`estatico_val_V18.txt`, `dinamico_val_V18.txt`).** Ninguna de las 24 variantes pasa el filtro estático
(p99 de 11 a 28 pp; la V11 da 12.6 y la V17 1.7 en el panel base). En dinámico todas quedan por debajo de la V17 (−0.6 a −3.2 pp) y ninguna
supera a la V11 con un intervalo que excluya el cero. Con la regla original se elegiría la de menor p99 máximo.
Causa medida: sin refinado, las redes CEM obtienen más potencia en el punto predicho que la V11 (0.927 contra 0.880 en monitoreo), pero su
error contra x* es el doble (0.12 contra 0.06): aprenden a caer sobre *algún* pico con buena potencia (a menudo el local, de corriente alta),
y el CEM sobre la corriente, que es local, ya no sale de él. La red de la V11 apunta a x* y deja al refinado más cerca del pico global.
El objetivo «potencia en el punto predicho» no es el que importa en el despliegue.

**V18.1 (`estatico_val2`, `dinamico_val2`).** El puntaje de cada red pasa a ser el resultado de la **cadena completa** en cada curva:
barrido de 7 → predicción → CEM sobre la corriente (el mismo del despliegue, simulado sobre la curva sin ruido) → mejor potencia medida /
P_gmpp. Los números aleatorios del refinado son los mismos para todas las redes de una generación. Como el σ0 del refinado forma parte del
objetivo, cada red se entrena con su σ0 y se despliega con ese mismo σ0. Para que el costo sea manejable: 500 curvas por generación (en vez de 2000).
Rejilla V18.1: capas ∈ {16×16, 64×64} × cola ∈ {0, 1} × σ0 ∈ {0.03, 0.1} (8 redes) × cota ∈ {no, sí} = 16 variantes.
**Selección:** la misma regla, sobre las 40 variantes (V18 y V18.1) con los mismos conjuntos de validación.

**Reserva agregada:** la validación se usó en dos rondas de diseño (V18 y V18.1), además de las de la V14 y la V17, así que sus cifras son optimistas.
Los criterios de la prueba no cambian.
