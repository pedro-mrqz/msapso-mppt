# V17 — Verificación por cota física: evita que la búsqueda corta se quede en el pico equivocado

Frente B, sin entrenamiento. Mejora sobre la candidata V14 (MSAPSO de 3 pasadas + CEM + retroceso del 2 %), que ganaba energía pero tenía una cola de fallos grave en estático (p99 de 13 pp); su reporte dejaba pendiente un «respaldo contra la cola».

*(Título cambiado después de la prueba solo para hacerlo más claro; el contenido del diseño no cambió.)*

Escrito ANTES de correr validación y prueba. El único resultado visto antes de escribirlo es el diagnóstico (`resultados_V17/diagnostico_V17.txt`), hecho con un conjunto nuevo (semillas 8080/8081) que no es S ni P.

## Punto de partida
- V7 (MSAPSO con parada por dispersión < 0.02): 70 mediciones, −0.05 pp de exactitud, p99 estático 0.64 pp. Método principal.
- V14 (MSAPSO de 3 pasadas + CEM + retroceso 2 %): +1.54 pp de energía dinámica sobre la V7, pero p99 estático de 13 pp (máximo 23 pp).
- Objetivo pedido: un mecanismo que detecte cuándo la búsqueda corta se equivocó de pico y la repita o alargue. Éxito = mantener la ganancia dinámica con p99 estático ≤ 3 pp. Listón para que valga la pena seguir con ES/RL: +1.6 pp sobre la V7 con esa cola.

## Diagnóstico (1000 curvas 8080/8081)
33 curvas pierden > 3 pp. En casi todas la búsqueda corta se queda en el pico de corriente alta (≈ 0.94·Isc) y el pico global está a corriente baja (≈ 0.2–0.3·Isc), entre las partículas iniciales 0.15 y 0.3·Isc. Tras 3 pasadas con β comprimida la dispersión del enjambre es siempre ≈ 0.003, así que «más pasadas cuando la dispersión sea alta» no puede detectar nada.

## Mecanismo
El voltaje del panel no sube al subir la corriente, así que entre dos mediciones Ia < Ib la potencia está acotada por Pa·Ib/Ia (dato físico, sin modelo ni entrenamiento). Tras la búsqueda corta de la V14 (sin cambios):
1. se calcula la cota de cada intervalo entre mediciones (excepto los pegados al mejor punto);
2. si alguna supera Pbest·(1 + τ), se mide en el punto medio del intervalo con la cota mayor; si esa medición supera a Pbest, el mismo CEM de la V14 refina desde ahí;
3. se repite hasta que ninguna cota supere el umbral o se agoten k sondeos.
Rejilla: τ ∈ {0.02, 0.05, 0.10, 0.15, 0.20} × k ∈ {2, 4, 8}.
Controles: «alargar» (si la cota inicial supera el umbral, se repite la búsqueda con la V7; τ ∈ {0.05, 0.10, 0.20}) y «ciega» (k sondeos en los intervalos más anchos sin mirar la cota; k ∈ {2, 4}). El retroceso es b = 0.02, como en la V14.

## Selección (validación)
- Estático: 1000 curvas 8080/8081 (panel base) + 100 curvas por panel (semilla 6161) en los otros 4 paneles.
- Dinámico: escenarios 600–1199 de la campaña (ya usados en la V14 para elegir b).
- Regla: entre las variantes con p99 ≤ 3 pp (b = 0.02) en los 5 conjuntos estáticos de validación, se elige la de mayor energía dinámica media en 600–1199. Empate (< 0.1 pp): la de menos mediciones estáticas.

## Prueba (variante congelada)
- Estático: S (7777/7778, 1000 curvas) y P (5151, 4 paneles), los mismos de la V14, más conjuntos frescos 9393/9394 y paneles 5252. También con ruido de 1 y 2 W como reporte adicional (sin criterio).
- Dinámico: 0–599 (prueba) y 1200–2399 (confirmación).

## Criterios (fijados antes de correr)
1. **Cola estática:** p99 ≤ 3 pp en S, en cada panel de P y en los conjuntos frescos (b = 0.02). Se reporta también la pérdida media (el criterio (d) de la V14 pedía además ≤ 0.5 pp; el retroceso del 2 % cuesta por sí solo ≈ 0.5 pp en estático, se reporta aparte con b = 0).
2. **Mantiene la ganancia dinámica:** V17 − V7 con límite inferior del IC95 % > 0 en 0–599 y en 1200–2399, y V17 − V14 ≥ −0.3 pp (estimación puntual) en ambos.
3. Los criterios (b) y (c) de la V14: ninguna celda del desglose con debilidad peor que −1 pp contra la V7; pierde > 3 pp contra el MSAPSO completo en ≤ 10 % de los escenarios.
4. **Listón ES/RL:** se reporta si V17 − V7 ≥ +1.6 pp con la cola del criterio 1. Si la V17 lo alcanza sin entrenar, el listón para ES/RL pasa a ser la V17.

Si se cumplen 1–3, la V17 se propone como alternativa a la V7 en dinámico. Si falla 1, la V7 sigue siendo la recomendación.

## Reservas conocidas antes de correr
Solo simulación. Sin corrección por comparaciones múltiples. S y P ya se reportaron en la V14 (no se usaron para elegir nada aquí; por eso se agregan conjuntos frescos). Los escenarios 600–1199 se usaron dos veces para elegir (b en la V14, variante aquí).

## Revisiones tras la validación (escritas ANTES de abrir la prueba)
**Resultado de la validación V17 (`estatico_val_V17.txt`, `dinamico_val_V17.txt`).** La cota sirve en estático (τ ≤ 0.05, k ≥ 4: p99 1.2–2.3 pp en los 5 conjuntos; el control «ciega» no pasa), pero en dinámico cuesta 0.7–1.1 pp contra la V14, casi todo a t_wait de 0.5–1 ms (−2.2 y −1.9 pp; −0.03 a 5 ms). Causa medida: a 5 ms la verificación se activa en el 7 % de las búsquedas (como en estático); a 0.5–1 ms en el 42–52 %, porque la corriente medida va rezagada respecto a la pedida y deja huecos aparentes; cada sondeo es además un salto grande de corriente que el inductor no sigue. Con la regla original habría ganado «alargar τ = 0.05» (+0.84 pp sobre la V7, −0.80 contra la V14), que fallaría el criterio 2.

**V17.1 (`estatico_val2`, `dinamico_val2`).** Los sondeos que pide la cota se intercalan en la escalera de las pasadas 2 y 3 del enjambre (pasos pequeños entre vecinos; un sondeo que supera a Pbest pasa a ser Gbest). Opcional: verificación final con τ_final. Solo intercalado: −0.2 pp contra la V14 en dinámico pero p99 de 3.0–3.7 pp (no pasa). Con verificación final pasa en estático pero vuelve a costar 0.6–1.2 pp en dinámico.

**V17.2 (`estatico_val3`, `dinamico_val3`).** Igual que la V17.1, pero la cota se calcula con la corriente PEDIDA en lugar de la medida (en estático son la misma, así que la cola estática no cambia; en dinámico deja de reaccionar al rezago del inductor). Pasan el filtro estático las 4 variantes con τ ∈ {0.05, 0.1} y τ_final ∈ {0.02, 0.05}; en dinámico quedan entre −0.08 y +0.22 pp contra la V14.

**Variante congelada para la prueba (misma regla de selección):** `ref intercalado tau=0.1 k=2 pasadas=2 final tau=0.05` — V17.2: MSAPSO de 3 pasadas con hasta 2 sondeos por pasada en las pasadas 2 y 3 donde la cota supera Pbest·1.10, CEM de la V14, verificación final (hasta 4 sondeos) donde la cota supera Pbest·1.05, retroceso 2 %. Validación: p99 estático 1.64 / 2.36 / 1.84 / 2.41 / 1.73 pp; 40.4 mediciones (base); dinámico +1.86 [+1.43, +2.32] pp sobre la V7 y +0.22 [−0.11, +0.59] sobre la V14.

**Reserva agregada:** la validación se usó en tres rondas de diseño (V17, V17.1, V17.2) y en la V14 para elegir b, así que sus cifras son optimistas. Los criterios de la prueba no cambian.
