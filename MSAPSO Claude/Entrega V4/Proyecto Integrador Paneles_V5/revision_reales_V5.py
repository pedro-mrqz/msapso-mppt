"""
revision_reales_V5.py — ¿Por que el arbol (y otros) fallan en algunos de los 4 casos reales? Diagnostico por caso y prueba de una causa probable:
DESAJUSTE DE DISTRIBUCION: el generador sintetico casi no produce patrones de Isc baja (caso 3: Isc = 3.25 A), y con el rango fijado por la Isc NOMINAL
(8.9 A) la mayoria de los puntos del barrido caen en la zona de potencia 0.
ADVERTENCIA METODOLOGICA: la idea de «atenuacion global» se propone DESPUES de ver el fallo en los reales; por eso se valida tambien en 100 sinteticos
nuevos con atenuacion global (semilla distinta) y los 4 reales dejan de ser un holdout puro. Se declara en el reporte.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from algoritmos_V5 import *
from reinforce_nn_V5 import build_pool_aug
from baselines_nivel1_V5 import scenarios, make_best_of_n, evaluate
from pvsim_V5.array_model_V5 import SyntheticPVCurve, random_shading_mix
real, synth = scenarios()
rng = np.random.default_rng(777)
synth_att = [SyntheticPVCurve(random_shading_mix(rng) * rng.uniform(0.25, 1.0)) for _ in range(100)]     # sinteticos NUEVOS con atenuacion global (semilla distinta)
pool = build_pool(10000, seed=0); pool_aug = build_pool_aug(10000, seed=0)
print("Isc de los patrones: reales", [round(c.Isc, 2) for c in real], "| banco original: % con Isc<4.5 A =", round(100 * np.mean([ (t > 0).nonzero()[0].max() * ISC_NOM / 599 < 4.5 for t in pool[:2000]]), 1),
      "| banco con atenuacion: ", round(100 * np.mean([(t > 0).nonzero()[0].max() * ISC_NOM / 599 < 4.5 for t in pool_aug[:2000]]), 1))
for N in (5, 7):
    I = grid_currents(N)
    print(f"\nN={N}: corrientes del barrido {np.round(I,2)} A")
    for i, c in enumerate(real):
        print(f"  caso {i+1}: Isc {c.Isc:.2f} A, GMPP en {c.I_gmpp:.2f} A ({c.P_gmpp:.0f} W); puntos del barrido con potencia > 0: {int(sum(c.power_at_I(x) > 1 for x in I))} de {N}")
    K = 5
    models = {}
    for nm, pl_, ob in (("arbol (banco original)", pool, make_obs_all(pool, N)), ("arbol (con atenuacion global)", pool_aug, make_obs_all(pool_aug, N))):
        models[nm] = [train_tree(N, pl_, ob, seed=s) for s in range(3)]
    print(f"  --- N={N}, K={K}: eficiencia final por caso real (y medias) ---")
    print(f"  {'metodo':32s} | caso1  caso2  caso3  caso4 | reales | sint.orig | sint.atenuados")
    row = lambda nm, per, so, sa_: print(f"  {nm:32s} | " + " ".join(f"{x:6.1f}" for x in per) + f" | {np.mean(per):6.2f} | {so:9.2f} | {sa_:9.2f}")
    ctl = make_best_of_n(N, K, 0.05)
    per = [evaluate(ctl, [c], reps=10)["eff_final"] for c in real]
    row("control simple", per, evaluate(ctl, synth)["eff_final"], evaluate(ctl, synth_att)["eff_final"])
    for nm, ms in models.items():
        per = np.mean([[eval_mu(m, N, K, 0.05, [c], "gauss", reps=10)["eff_final"] for c in real] for m in ms], axis=0)
        so = np.mean([eval_mu(m, N, K, 0.05, synth, "gauss", reps=3)["eff_final"] for m in ms]); sa_ = np.mean([eval_mu(m, N, K, 0.05, synth_att, "gauss", reps=3)["eff_final"] for m in ms])
        row(nm, per, so, sa_)
