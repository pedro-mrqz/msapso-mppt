"""
comparar_algoritmos_V5.py — Entrena y evalua REINFORCE, PPO, SAC, DDPG y arbol (formulacion corregida) para un N dado, varias semillas.
Evalua en 100 sinteticos nuevos (reps=3) y 4 reales (reps=5), con K = 3 y 5 muestras, sigma_eval = 0.05, y tambien solo en mu.
USO: python3 comparar_algoritmos_V5.py --N 5 --seeds 0 1 2 [--steps-onpolicy 300000 --steps-offpolicy 60000]
"""
import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, torch
torch.set_num_threads(1)
from algoritmos_V5 import *
from baselines_nivel1_V5 import scenarios

ap = argparse.ArgumentParser()
ap.add_argument("--N", type=int, required=True); ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
ap.add_argument("--steps-onpolicy", type=int, default=300000); ap.add_argument("--steps-offpolicy", type=int, default=60000)
ap.add_argument("--noise", type=float, default=0.0); ap.add_argument("--algos", nargs="+", default=["reinforce", "ppo", "sac", "ddpg", "arbol"])
a = ap.parse_args()
real, synth = scenarios(); pool = build_pool(10000, seed=0); obs_all = make_obs_all(pool, a.N)
res = {}
for seed in a.seeds:
    for algo in a.algos:
        t0 = time.time()
        if algo == "reinforce":
            mus = {K: reinforce_mu(train_reinforce(a.N, K, SIGMA_EVAL, None, "value", "gain", 4000, seed=seed, pool=pool, noise_w=a.noise)) for K in (3, 5)}
        elif algo == "arbol":
            m = train_tree(a.N, pool, obs_all, seed=seed, noise_w=a.noise); mus = {3: m, 5: m}
        else:
            m = sb3_mu(train_sb3(algo, a.N, pool, obs_all, a.steps_onpolicy if algo == "ppo" else a.steps_offpolicy, seed, a.noise)); mus = {3: m, 5: m}
        for K in (3, 5):
            for mode in ("gauss", "mu"):
                s = eval_mu(mus[K], a.N, K, SIGMA_EVAL, synth, mode, reps=3, noise_w=a.noise)
                r = eval_mu(mus[K], a.N, K, SIGMA_EVAL, real, mode, reps=5, noise_w=a.noise)
                res.setdefault(f"{algo}|K{K}|{mode}", []).append([s["eff_final"], s["eff_energy"], r["eff_final"], r["eff_energy"]])
        print(f"N={a.N} seed={seed} {algo:9s} listo en {time.time()-t0:.0f} s | K=5 gauss: sint {res[f'{algo}|K5|gauss'][-1][0]:.2f}/{res[f'{algo}|K5|gauss'][-1][1]:.2f}", flush=True)
        json.dump(res, open(f"resultados_V5/comparar_N{a.N}{'_ruido'+str(a.noise) if a.noise else ''}.json", "w"), indent=1)
