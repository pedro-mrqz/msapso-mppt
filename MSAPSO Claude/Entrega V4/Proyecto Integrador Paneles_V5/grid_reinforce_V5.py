"""Malla de la formulacion corregida (V5): reward x baseline x K_train x sigma (fija/decreciente). N=7, evaluacion con K=5.
Evalua en 4 reales y 100 sinteticos NUEVOS, 3 semillas. Referencias: 'mejor de 7 + 5 gauss.' = 97.22/95.36 (sint) y 93.5/91.7 (reales); cota supervisada 98.1/96.2."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from reinforce_nn_V5 import train, eval_policy, build_pool
from baselines_nivel1_V5 import scenarios
real, synth = scenarios(); pool = build_pool(6000, seed=0)
N, K_EVAL, UPD = int(os.environ.get("N", 7)), 5, int(os.environ.get("UPD", 4000))
cfgs = []
for reward in ("mean", "max", "gain"):
    for baseline in ("value", "batch"):
        for K in (5, 20):
            for sig in ((0.05, None), (0.15, 0.03)):
                cfgs.append((reward, baseline, K, sig))
res = {}
print(f"N={N} K_eval={K_EVAL} updates={UPD}\n{'reward':5s} {'baseline':8s} {'Ktr':3s} {'sigma':11s} | modo  | REALES fin  ener | SINT fin  ener")
for (reward, baseline, K, (s0, s1)) in cfgs:
    acc = {"stoch": [], "mu": []}
    for seed in range(3):
        pol = train(N, K, s0, s1, baseline, reward, UPD, seed=seed, pool=pool)
        s_eval = s0 if s1 is None else s1
        for m in acc:
            r = eval_policy(pol, N, K_EVAL, s_eval, real, m, reps=5); s = eval_policy(pol, N, K_EVAL, s_eval, synth, m, reps=3)
            acc[m].append((r["eff_final"], r["eff_energy"], s["eff_final"], s["eff_energy"]))
    for m, v in acc.items():
        mm = np.array(v).mean(0)
        key = f"{reward}|{baseline}|{K}|{s0}-{s1}|{m}"; res[key] = mm.tolist()
        sg = f"{s0}" if s1 is None else f"{s0}->{s1}"
        print(f"{reward:5s} {baseline:8s} {K:3d} {sg:11s} | {m:5s} | {mm[0]:6.2f} {mm[1]:6.2f} | {mm[2]:6.2f} {mm[3]:6.2f}", flush=True)
json.dump(res, open("resultados_V5/reinforce_grid_V5.json", "w"), indent=1)
