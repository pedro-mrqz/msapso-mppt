"""¿Donde hay margen para un modelo? Barrido de N (puntos de barrido) y K (muestras) con tres columnas:
  control = 'mejor de N + K gaussianas' (sin aprendizaje) | cota = MLP supervisado (diagnostico; usa GMPP como etiqueta, NO es un metodo valido)
  | RL = REINFORCE corregido (reward 'gain', baseline 'value', sigma 0.05 fija, K_train = K). Evalua 100 sinteticos nuevos, sin ruido."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, torch, torch.nn as nn
from pvsim_V5.static_plant_V5 import StaticPlant
from pvsim_V5.medicion_V5 import *
from pvsim_V5.array_model_V5 import SyntheticPVCurve, random_shading_mix
from baselines_nivel1_V5 import scenarios, make_best_of_n, evaluate
from reinforce_nn_V5 import train, eval_policy, build_pool
real, synth = scenarios(); pool = build_pool(6000, seed=0)
rng = np.random.default_rng(0); train_curves = [SyntheticPVCurve(random_shading_mix(rng)) for _ in range(6000)]

def cota_model(N):
    X = np.array([np.array([StaticPlant(c).run(1.0, i)[0] for i in grid_currents(N)]) / P_NOM for c in train_curves]); y = np.array([c.I_gmpp for c in train_curves]) / ISC_NOM
    torch.manual_seed(0); net = nn.Sequential(nn.Linear(N, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)); opt = torch.optim.Adam(net.parameters(), 3e-3)
    Xt, yt = torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)[:, None]
    for _ in range(600): opt.zero_grad(); ((net(Xt) - yt) ** 2).mean().backward(); opt.step()
    return net

def eval_cota(net, N, K, curves, sigma=0.05):
    out = []
    for k, c in enumerate(curves):
        r = np.random.default_rng(3 + k); pl = StaticPlant(c); P = np.array([pl.run(1.0, i)[0] for i in grid_currents(N)])
        mu = float(net(torch.tensor(P / P_NOM, dtype=torch.float32)[None])) * ISC_NOM
        for _ in range(K): pl.run(1.0, float(np.clip(r.normal(mu, sigma * ISC_NOM), I_MIN, I_MAX)))
        out.append(metrics_from_plant(pl, c))
    return {m: np.mean([o[m] for o in out]) for m in out[0]}

print("N  K  med | control fin  ener | cota fin  ener | RL corregido fin  ener (3 sem.)   [100 sinteticos]")
for N, K in ((3, 3), (4, 3), (4, 5), (5, 3), (5, 5), (7, 3), (7, 5), (10, 5)):
    c = evaluate(make_best_of_n(N, K, 0.05), synth)
    net = cota_model(N); q = eval_cota(net, N, K, synth)
    rl = []
    for seed in range(3):
        pol = train(N, K, 0.05, None, "value", "gain", 4000, seed=seed, pool=pool)
        s = eval_policy(pol, N, K, 0.05, synth, "stoch", reps=3); rl.append((s["eff_final"], s["eff_energy"]))
    rl = np.mean(rl, 0)
    print(f"{N:2d} {K:2d} {N+K:3d} | {c['eff_final']:11.2f} {c['eff_energy']:5.2f} | {q['eff_final']:8.2f} {q['eff_energy']:5.2f} | {rl[0]:15.2f} {rl[1]:5.2f}", flush=True)
