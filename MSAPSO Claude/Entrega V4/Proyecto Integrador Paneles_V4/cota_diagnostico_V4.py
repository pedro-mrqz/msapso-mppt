"""DIAGNOSTICO PRIVADO (no es un metodo ni se entrena en la V4 final): cota de cuanto margen hay.
Usa el GMPP real como etiqueta SOLO para estimar el techo de lo que cualquier modelo (RL o no) podria lograr con N potencias."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch, torch.nn as nn
from pvsim_V4.pvcurve_V4 import load_case
from pvsim_V4.array_model_V4 import SyntheticPVCurve, random_shading_mix
from pvsim_V4.static_plant_V4 import StaticPlant
from pvsim_V4.medicion_V4 import *
from baselines_nivel1_V4 import scenarios

def feats(c, N):
    pl = StaticPlant(c); I, P = scan(pl, N); return P / P_NOM, pl
def evaluate_pred(curves, predict, N, K=5, sigma=0.05, seed=3):
    out = []
    for k, c in enumerate(curves):
        rng = np.random.default_rng(seed + k)
        x, pl = feats(c, N)
        mu = predict(x)
        for _ in range(K): pl.run(1.0, float(np.clip(rng.normal(mu, sigma * ISC_NOM), I_MIN, I_MAX)))
        out.append(metrics_from_plant(pl, c))
    return {k: np.nanmean([o[k] for o in out]) for k in out[0]}
real, synth = scenarios()
rng = np.random.default_rng(0)
train = [SyntheticPVCurve(random_shading_mix(rng)) for _ in range(6000)]
for N in (7, 10, 20):
    X = np.array([feats(c, N)[0] for c in train]); y = np.array([c.I_gmpp for c in train])
    torch.manual_seed(0)
    net = nn.Sequential(nn.Linear(N, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1))
    opt = torch.optim.Adam(net.parameters(), 3e-3); Xt = torch.tensor(X, dtype=torch.float32); yt = torch.tensor(y / ISC_NOM, dtype=torch.float32)[:, None]
    for ep in range(600):
        opt.zero_grad(); loss = ((net(Xt) - yt) ** 2).mean(); loss.backward(); opt.step()
    class M:
        def predict(self, x): return net(torch.tensor(x, dtype=torch.float32)).detach().numpy().ravel() * ISC_NOM
    m = M()
    orc = lambda c: None
    print(f"\nN={N}, K=5 (mediciones = {N+5})")
    for nm, cs in (("reales", real), ("sinteticos", synth)):
        a = evaluate_pred(cs, lambda x: float(np.clip(m.predict(x[None])[0], I_MIN, I_MAX)), N)
        # oraculo: propone el GMPP exacto
        o = []
        for k, c in enumerate(cs):
            x, pl = feats(c, N); r = np.random.default_rng(k)
            for _ in range(5): pl.run(1.0, float(np.clip(r.normal(c.I_gmpp, 0.05 * ISC_NOM), I_MIN, I_MAX)))
            o.append(metrics_from_plant(pl, c))
        o = {k: np.nanmean([q[k] for q in o]) for k in o[0]}
        print(f"  {nm:10s} | modelo supervisado (cota): efi_final {a['eff_final']:.2f}  energia {a['eff_energy']:.2f} | oraculo ideal: efi_final {o['eff_final']:.2f} energia {o['eff_energy']:.2f}")
