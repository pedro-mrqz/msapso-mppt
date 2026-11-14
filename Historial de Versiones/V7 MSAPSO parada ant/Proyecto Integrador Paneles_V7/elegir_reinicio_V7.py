"""
elegir_reinicio_V7.py — Elige la regla de reinicio en VALIDACION (semillas 3000+) con el CRITERIO FIJADO ANTES DE LA PRUEBA: entre las reglas de la familia cuya energia, en NINGUN grupo de escenarios
(promedio de MSAPSO completo y V7), baja mas de 0.25 pp respecto a la regla del paper (5 W), la de MAYOR mejora media de energia sobre todos los grupos. Se congela y se evalua en la PRUEBA (reinicio_prueba_V7.py).
USO: python3 elegir_reinicio_V7.py -> resultados_V7/reinicio_seleccion_V7.txt|json
"""
import json
import numpy as np
from reinicio_V7 import FULLFAM as FAMILY, FAMILY as FAM1
import sys
RONDA = int(sys.argv[1]) if len(sys.argv) > 1 else 1
N1 = len(FAM1)

import os
if os.path.exists("resultados_V7/reinicio_validacion_V7.json"): _M = json.load(open("resultados_V7/reinicio_validacion_V7.json")); R = [_M[str(i)] for i in range(len(FAMILY) if RONDA == 2 else N1)]
else: R = [json.load(open(f"resultados_V7/reinicio_val_{i}.json")) for i in range(len(FAMILY) if RONDA == 2 else N1)]
groups = list(R[0].keys()); lines = []
def P(s=""): print(s, flush=True); lines.append(s)
def en(i, g): return np.mean([R[i][g][m]["energia"] for m in R[i][g]])
def fa(i, g): return np.mean([R[i][g][m]["falsos"] for m in R[i][g]])
P("Diferencia de energia respecto a la regla del paper (5 W), promedio de MSAPSO completo y V7 (pp) | reinicios falsos por escenario entre parentesis")
P(f"{'regla':24s} | " + " | ".join(g[:22] for g in groups) + " | media | peor grupo")
rows = []
for i, r in enumerate(FAMILY[:len(R)]):
    d = [en(i, g) - en(0, g) for g in groups]; rows.append((i, float(np.mean(d)), float(min(d)))); P(f"{r.name:24s} | " + " | ".join(f"{x:+5.2f} ({fa(i, g):4.1f})" for x, g in zip(d, groups)) + f" | {np.mean(d):+.2f} | {min(d):+.2f}")
ok = [x for x in rows if x[0] != 0 and x[2] >= -0.25]; best = max(ok, key=lambda x: x[1]) if ok else None
if best:
    P(f"\nELEGIDA: {FAMILY[best[0]].name} (mejora media {best[1]:+.2f} pp; peor grupo {best[2]:+.2f} pp)"); json.dump(dict(indice=best[0], nombre=FAMILY[best[0]].name, mejora_media=best[1], peor_grupo=best[2], ronda=RONDA), open(f"resultados_V7/reinicio_seleccion_V7{'_r2' if RONDA == 2 else ''}.json", "w"), indent=1)
else: P("\nNinguna regla cumple el criterio; se mantiene la del paper.")
open(f"resultados_V7/reinicio_seleccion_V7{'_r2' if RONDA == 2 else ''}.txt", "w").write("\n".join(lines))
