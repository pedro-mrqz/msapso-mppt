# V16 — DGO (Tang y Fong 2016) y CEDGO (Tang et al., Entropy 2017) como buscadores de MPPT (Frente C; versión confirmada por el profesor)

Fuente: Tang, Fong, Dey, Wong y Mohammed, «Cross Entropy Method Based Hybridization of Dynamic Group Optimization Algorithm», Entropy 19(10):533 (2017): describe el DGO (Eqs. 4–8) y el CEDGO (Eqs. 10–12, tiempo de vida). El profesor respondió que la versión que quiere es la de Tang y Fong. No se leyó el paper original del DGO (2016): se usan las ecuaciones tal como las reproduce el de 2017. El paper evalúa funciones de referencia, no MPPT ni sombreado parcial; el simulador, la métrica y los escenarios son los nuestros.

## Implementación (`dgo_V16.py`)
Ecuaciones en el docstring. **Interpretaciones propias, declaradas antes de correr** (el paper no las precisa): 2 grupos; cabeza = mejor del grupo; Mr1 = Mr2 = 0.25; α0 = 0.1; λ = 1.5 (Mantegna); Eq. 4 y 5 en secuencia; variación de grupo (el grupo con la mejor cabeza recibe un miembro del otro); CEDGO con Mu y S por grupo (S0 = 0.1, Lr = 0.7) y tiempo de vida de 3 generaciones con reemplazo por el promedio de 3 cabezas más N(0, 0.05); sin parada anticipada (presupuesto n·G fijo); el reinicio de operación es el de 5 W de nuestro entorno. Cualquier diferencia con los autores puede cambiar el resultado, y α0, Mr, λ, Lr y S0 NO se ajustan (solo la rejilla de abajo).

## Rejilla (única, sin más ajuste)
variante {DGO, CEDGO} × (n, G) ∈ {(5, 8), (8, 5)} (≈ 40 mediciones) o {(7, 10), (10, 7)} (≈ 70) × inicialización {aleatoria (paper), estratificada} × retroceso b ∈ {0, 0.02} = 32 configuraciones.

## Protocolo y selección (los de la V15, fijados antes de correr)
1. Cola estática en validación (200 curvas, semillas 3030/3031): se excluye toda configuración con p99 de pérdida de exactitud final > 3 pp frente al MSAPSO completo (con su retroceso aplicado).
2. Energía dinámica en validación (600–1199): entre las no excluidas, la de mayor energía (si ninguna pasa, se reporta la mejor y se declara que falla el criterio d).
3. Se congela. Prueba 0–599 y confirmación 1200–2399; cola estática en 1000 curvas (7777/7778). Referencias: MSAPSO completo, V7, candidata V14 y DGBCO (V15), con resultados por escenario guardados.

## Criterios de lectura (los de la V14/V15)
(a) ventaja demostrable (IC95 % pareado > 0) sobre la V7 en energía, en prueba y en confirmación; (b) ninguna celda del desglose con debilidad demostrable peor que −1 pp; (c) pierde > 3 pp frente al MSAPSO completo en ≤ 10 % de escenarios; (d) cola estática: pérdida media ≤ 0.5 pp y p99 ≤ 3 pp. Si falla (a) la V7 sigue; si falla (d) se declara la condición.

## Reservas
Solo simulación; muchas interpretaciones propias; 32 configuraciones (la validación sesga hacia arriba por selección, la confirmación no); sin corrección por comparaciones múltiples; se leyó la descripción del DGO de un paper posterior, no el original.
