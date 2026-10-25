import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from reinforce_nn_V4 import train, eval_policy, build_pool
from baselines_nivel1_V4 import scenarios
real, synth = scenarios(); pool = build_pool(6000, seed=0); N, K = 7, 5
print("updates | batch | sigma | modo | REALES fin ener | SINT fin ener  (media de 3 semillas)")
for upd, B, lr in ((4000, 128, 1e-3), (20000, 128, 1e-3), (20000, 512, 3e-4), (60000, 256, 3e-4)):
    for sigma in (0.05,):
        acc = []
        for seed in range(3):
            pol, _ = train(N, K, sigma, "mean", upd, B=B, lr=lr, seed=seed, pool=pool, log=False)
            r = eval_policy(pol, N, K, sigma, real, "stoch", reps=5); s = eval_policy(pol, N, K, sigma, synth, "stoch", reps=3)
            m = eval_policy(pol, N, K, sigma, synth, "mu")
            acc.append((r["eff_final"], r["eff_energy"], s["eff_final"], s["eff_energy"], m["eff_final"]))
        a = np.array(acc).mean(0)
        print(f"{upd:6d} | {B:4d} | {sigma} | stoch | {a[0]:6.2f} {a[1]:6.2f} | {a[2]:6.2f} {a[3]:6.2f} | solo mu (sint) {a[4]:.2f}", flush=True)
