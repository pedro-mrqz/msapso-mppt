"""
huella_computo_V7.py — HUELLA DE COMPUTO de la parada anticipada de la V7 frente al MSAPSO completo (7 particulas).
(1) Conteo analitico de operaciones y memoria por pasada; (2) microbenchmark en Python/numpy como referencia relativa (NO es un tiempo de microcontrolador).
USO: python3 huella_computo_V7.py -> resultados_V7/huella_computo_V7.txt
"""
import timeit
import numpy as np
from pvsim_V7.msapso_V7 import Swarm

lines = []
def P(s=""): print(s, flush=True); lines.append(s)
n = 7
P("CONTEO ANALITICO (7 particulas, por pasada):")
P("  MSAPSO completo, por pasada: 7 mediciones + comparaciones Pbest (7) + actualizacion Eq. 13 (7 x [resta, multiplicacion, suma] = 21 operaciones) + beta (1 multiplicacion y 1 suma).")
P("  Parada anticipada, extra por pasada: dispersion std(x)/Isc = media (7 sumas + 1 division) + desviaciones (7 restas, 7 multiplicaciones, 6 sumas) + raiz + division = ~30 operaciones + 1 comparacion con delta.")
P("  Memoria extra: 1 constante (delta). La dispersion se calcula con las posiciones que el algoritmo ya guarda (no hay historial ni tablas).")
P("  Efecto: ~30 operaciones adicionales por pasada frente a 7 mediciones de 5 ms (35 ms de sensado por pasada), y se ahorran ~105 mediciones (15 pasadas) por busqueda.")
sw = Swarm(first_pass="ascending"); sw.restart(8.0, first=True); sw.x = np.array([7.6, 6.4, 5.2, 4.0, 2.4, 1.2, 0.8]); sw.Gbest = 5.0
t_upd = timeit.timeit(lambda: sw.update(0.5), number=20000) / 20000 * 1e6
t_disp = timeit.timeit(lambda: sw.dispersion(), number=20000) / 20000 * 1e6
P(f"\nMICROBENCHMARK (Python/numpy, referencia relativa): actualizacion Eq. 13 = {t_upd:.1f} us por pasada; calculo de la dispersion = {t_disp:.1f} us por pasada (+{100*t_disp/t_upd:.0f} % sobre la actualizacion); ambos son despreciables frente a 7 x t_wait (35 ms a 5 ms).")
open("resultados_V7/huella_computo_V7.txt", "w").write("\n".join(lines))
