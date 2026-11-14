# V17 — DecentCEM como buscador de MPPT (Frente B/C; sugerido por el profesor)

Origen: el profesor pidió (1) quitar la adaptación de sigma del CEM y (2) probar DecentCEM (Shi et al., arXiv 2212.08235) o el Cross Entropy Mixture Model (arXiv 2009.09043, sec. IV-B). Describió su versión: barrer N puntos uniformes en todo el rango de corriente; los élites caen en picos distintos; si su separación supera un umbral, cada élite pasa a ser la media de su propia distribución (un «worker») y en las siguientes iteraciones cada worker muestrea N puntos para refinar su pico. Se escribe este diseño ANTES de correr nada.

## Lectura de los papers (hecha con resumen automático de la página; las ecuaciones de EM del segundo paper no vienen escritas en él)
- **DecentCEM**: M instancias de CEM independientes, sin comunicación; N y k se reparten por igual entre instancias; cada una reajusta media y varianza por máxima verosimilitud con suavizado α y un piso de varianza (ε = 1e-3 en su estudio 1D); al final se elige la distribución de mejor valor. Prueban 100–1000 muestras.
- **CE-Mixture (sec. IV-B)**: es CE-surrogate con mezcla gaussiana; necesita un modelo sustituto barato (≈10 mil muestras sustitutas por iteración) y EM. Nosotros medimos directo en la planta y no tenemos sustituto: **no se implementa** (el paper tampoco lo mostró mejor que su CE-surrogate). Se declara como no probado.

## Métodos (`decentcem_V17.py`)
Todos usan x = I/Isc en [0, 1], una medición por `planta.run(1.0, I)`, y la corriente de operación es la de la mejor potencia medida (como en el resto del proyecto) con retroceso b.
- **Brazo A / B — versión del profesor (barrido + workers).** Barrido ascendente de N puntos uniformes en [0.10, 0.95]. Élites = los 3 de mayor potencia; se recorren de mayor a menor potencia y un élite pasa a ser worker nuevo solo si dista más de τ de los ya aceptados (si no, se funde con el mejor de su pico). Máximo 3 workers. Cada worker: T iteraciones de n muestras N(μ_w, σ²), k = 2 élites, μ ← (1−α)μ + α·media(élites), α = 0.7 (el de la V14). **A: σ fija** (lo que pidió el profesor; sin parada por σ, presupuesto fijo). **B: σ adaptada con piso** (σ ← máx((1−α)σ + α·std(élites), 0.005), como el paper).
- **Brazo C — DecentCEM del paper.** M = 3 instancias con medias iniciales 0.2, 0.5, 0.8, σ0 = 0.15, σ adaptada con piso 0.005, n = 4, k = 2, α = 0.7, T iteraciones, sin comunicación.
- Presupuesto: A/B = N + (nº de workers)·n·T (≈ 20–58 mediciones); C = 12·T.

## Rejilla (única, sin más ajuste; 68 configuraciones)
A/B: modo {σ fija, σ con piso} × N {7, 10} × σ0 {0.03, 0.05} × τ {0.15, 0.25} × (n, T) {(3, 3), (4, 4)} × b {0, 0.02} = 64. C: T {4, 6} × b {0, 0.02} = 4. Fijos y NO ajustados: k_barrido = 3, W_máx = 3, k = 2, α = 0.7, piso 0.005. Interpretaciones propias declaradas: élites del barrido = 3; fusión por τ contra el mejor ya aceptado; sin fusión posterior de workers; en C la inicialización de medias (0.2/0.5/0.8) y σ0 = 0.15 no vienen del paper.

## Protocolo y selección (los de V14–V16, fijados antes de correr)
1. **Cola estática en validación** (200 curvas, semillas 3030/3031): pérdida de exactitud final vs MSAPSO completo, por configuración, con presupuesto medio de mediciones.
2. **Regla de parada del frente (fijada antes de correr):** si NINGUNA configuración tiene p99 ≤ 5 pp en esa cola, no se corren prueba ni confirmación; se reporta el resultado y se cierra V17 como negativo. Si alguna tiene p99 ≤ 3 pp, el pool de selección son esas; si solo hay con p99 entre 3 y 5 pp, el pool son las de p99 ≤ 5 y se declara que falla el criterio (d).
3. **Energía dinámica en validación** (escenarios 600–1199): del pool, la de mayor energía. Se congela una.
4. **Prueba** (0–599) y **confirmación** (1200–2399), escenarios V7 Monte Carlo (semillas 100000 + idx); cola estática en 1000 curvas (7777/7778). Referencias, con los resultados por escenario de V16: MSAPSO completo, V7, V7 + retroceso 2 % (**plan B**), candidata V14 (MSAPSO corto + CEM, b = 0.02).

## Criterios de lectura (los de V14–V16)
(a) ventaja demostrable (IC95 % bootstrap pareado > 0) sobre la V7 en energía, en prueba y en confirmación; (b) ninguna celda del desglose con debilidad demostrable peor que −1 pp; (c) pierde > 3 pp frente al MSAPSO completo en ≤ 10 % de escenarios; (d) cola estática: pérdida media ≤ 0.5 pp y p99 ≤ 3 pp. Si falla (a) la V7 sigue como método principal; si falla (d) se declara la condición. Lectura adicional: contra el plan B (V7 + retroceso) y la candidata V14, para ubicar el resultado.

## Hipótesis que se quiere comprobar
La cola de la candidata V14 (p99 estático 13 pp, máx 23 pp aun sin retroceso) viene de elegir el pico equivocado cuando hay picos parecidos y refinar solo uno. Refinar cada pico antes de decidir debería reducirla. Si la cola no baja, la hipótesis queda refutada para este presupuesto.

## Reservas
Solo simulación; interpretaciones propias listadas arriba; 68 configuraciones (la validación sesga hacia arriba por selección, la confirmación no); sin corrección por comparaciones múltiples; papers leídos con resumen automático; CE-Mixture no probado.
