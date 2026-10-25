"""Malla de REINFORCE-MLP en el nivel 1: baseline x sigma x semilla (N=7, K=5). Evalua en reales (4) y sinteticos (100) NUNCA vistos."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from reinforce_nn_V4 import train, eval_policy, build_pool
from baselines_nivel1_V4 import scenarios
real, synth = scenarios()
pool = build_pool(6000, seed=0)
N, K, UPD = int(os.environ.get("N", 7)), int(os.environ.get("K", 5)), int(os.environ.get("UPD", 4000))
rows, res = [], {}
print(f"N={N} K={K} updates={UPD}\n{'config':28s} | {'modo':9s} | REALES fin   ener | SINT fin   ener")
for baseline in ("none", "mean", "value"):
    for sigma in (0.02, 0.05, 0.10):
        acc = {m: [] for m in ("stoch", "mu", "mu+stoch")}
        for seed in range(3):
            pol, _ = train(N, K, sigma, baseline, UPD, seed=seed, pool=pool, log=False)
            for m in acc:
                r = eval_policy(pol, N, K, sigma, real, m, reps=5); s = eval_policy(pol, N, K, sigma, synth, m, reps=3)
                acc[m].append((r["eff_final"], r["eff_energy"], s["eff_final"], s["eff_energy"], s["n_meas"]))
        for m, v in acc.items():
            v = np.array(v); mm = v.mean(0); sd = v.std(0)
            res[f"{baseline}|{sigma}|{m}"] = dict(mean=mm.tolist(), sd=sd.tolist())
            print(f"{baseline+' s='+str(sigma):28s} | {m:9s} | {mm[0]:6.2f} {mm[1]:6.2f} (+-{sd[1]:.2f}) | {mm[2]:6.2f} {mm[3]:6.2f} (+-{sd[3]:.2f}) n={mm[4]:.0f}", flush=True)
json.dump(res, open(f"resultados_V4/reinforce_grid_N{N}_K{K}_V4.json", "w"), indent=1)
