"""Resume resultados_V5/comparar_N*.json: media y desv. estandar entre semillas, junto a los controles sin aprendizaje (100 sinteticos / 4 reales)."""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from baselines_nivel1_V5 import scenarios, make_best_of_n, evaluate
from control_parabolico_V5 import make_parabolic
real, synth = scenarios()
lines = []
def P(s=""): print(s); lines.append(s)
for noise in (0.0, 1.0, 2.0):
  for N in (3, 5, 7):
    f = f"resultados_V5/comparar_N{N}.json" if noise == 0 else f"resultados_V5/comparar_N{N}_ruido{noise}.json"
    if not os.path.exists(f): continue
    R = json.load(open(f))
    for K in (3, 5):
        if noise > 0 and K == 3: continue
        P(f"\n=== ruido {noise:g} W | N={N}, K={K}  ({N+K} mediciones) | SINTETICOS final/energia (+-sd semillas) | REALES final/energia ===")
        for nm, m in (("control simple (mejor de N + K gauss.)", make_best_of_n(N, K, 0.05)), ("control parabolico", make_parabolic(N, K))):
            a_ = evaluate(m, synth, noise, reps=3 if noise else 1); b_ = evaluate(m, real, noise, reps=20 if noise else 1)
            P(f"{nm:38s} | {a_['eff_final']:6.2f} / {a_['eff_energy']:6.2f}              | {b_['eff_final']:6.2f} / {b_['eff_energy']:6.2f}")
        for algo in ("reinforce", "ppo", "sac", "ddpg", "arbol"):
            for mode in ("gauss", "mu"):
                v = np.array(R.get(f"{algo}|K{K}|{mode}", []))
                if len(v) == 0: continue
                mm, sd = v.mean(0), v.std(0)
                P(f"{algo:9s} {('K muestras' if mode=='gauss' else 'solo mu'):10s}            | {mm[0]:6.2f} / {mm[1]:6.2f} (+-{sd[0]:.2f}/{sd[1]:.2f}) | {mm[2]:6.2f} / {mm[3]:6.2f}  [n={len(v)} sem.]")
open("resultados_V5/resumen_comparar_V5.txt", "w").write("\n".join(lines))
