import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from reinforce_nn_V4 import train, eval_policy, build_pool
from baselines_nivel1_V4 import scenarios
real, synth = scenarios(); pool = build_pool(6000, seed=0); N, K = 7, 5
print("reward | baseline | sigma | modo | REALES fin ener | SINT fin ener (3 semillas)")
for reward in ("abs", "gain"):
    for baseline in ("mean", "none"):
        for sigma in (0.05, 0.10):
            acc = {"stoch": [], "mu": []}
            for seed in range(3):
                pol, _ = train(N, K, sigma, baseline, 4000, seed=seed, pool=pool, log=False, reward=reward)
                for m in acc:
                    r = eval_policy(pol, N, K, sigma, real, m, reps=5); s = eval_policy(pol, N, K, sigma, synth, m, reps=3)
                    acc[m].append((r["eff_final"], r["eff_energy"], s["eff_final"], s["eff_energy"]))
            for m, v in acc.items():
                mm = np.array(v).mean(0); print(f"{reward:4s} | {baseline:5s} | {sigma:4.2f} | {m:5s} | {mm[0]:6.2f} {mm[1]:6.2f} | {mm[2]:6.2f} {mm[3]:6.2f}", flush=True)
