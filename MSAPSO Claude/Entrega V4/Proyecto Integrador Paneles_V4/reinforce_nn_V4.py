"""
reinforce_nn_V4.py — REINFORCE con MLP (propuesta del profesor) en el NIVEL 1 (potencia estatica).

Politica: MLP(N potencias/250 W) -> mu en [-1,1] (tanh) = corriente propuesta (accion normalizada). Se muestrean K acciones
a_k ~ N(mu, sigma^2) por patron de sombra (el «muestreo de puntos aledanos» ES la politica). Recompensa r_k = potencia MEDIDA
en la corriente muestreada / 250 W. NO se usa el GMPP ni P_ceiling en el entrenamiento (solo en la evaluacion).
Gradiente (REINFORCE):  grad J = E[ (r_k - b) * (a_k - mu)/sigma^2 * grad mu ].
Baselines b:  none | mean (promedio de los OTROS K-1 muestreos del mismo patron, «leave-one-out») | value (V(obs) aprendida).
sigma fija (en fraccion de la Isc nominal): «desviacion estandar muy pequenita» (profesor).
USO:  python3 reinforce_nn_V4.py --N 7 --K 5 --sigma 0.05 --baseline mean --seed 0
"""
import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch, torch.nn as nn
from pvsim_V4.array_model_V4 import SyntheticPVCurve, random_shading_mix
from pvsim_V4.static_plant_V4 import StaticPlant
from pvsim_V4.medicion_V4 import (ISC_NOM, I_MIN, I_MAX, P_NOM, grid_currents, scan, metrics_from_plant, current_to_action, action_to_current)

TABLE_PTS = 600


def p_table(curve):
    Ig = np.linspace(0.0, ISC_NOM, TABLE_PTS)
    return np.interp(Ig, curve.I, curve.P, right=0.0).astype(np.float32)


def build_pool(M, seed=0):
    rng = np.random.default_rng(seed)
    return np.stack([p_table(SyntheticPVCurve(random_shading_mix(rng))) for _ in range(M)])


def table_lookup(tab, I):
    """tab (B,T) ; I (B,K) amperes -> potencia (B,K) por interpolacion lineal."""
    pos = np.clip(I / ISC_NOM, 0.0, 1.0) * (TABLE_PTS - 1)
    lo = np.floor(pos).astype(int); hi = np.minimum(lo + 1, TABLE_PTS - 1); fr = pos - lo
    rows = np.arange(tab.shape[0])[:, None]
    return tab[rows, lo] * (1 - fr) + tab[rows, hi] * fr


class Policy(nn.Module):
    def __init__(self, N, hidden=64):
        super().__init__()
        self.mu = nn.Sequential(nn.Linear(N, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1), nn.Tanh())
        self.v = nn.Sequential(nn.Linear(N, hidden), nn.ReLU(), nn.Linear(hidden, 1))

    def forward(self, x):
        return self.mu(x).squeeze(-1)


def sigma_action(sigma_frac):
    return sigma_frac * ISC_NOM / (0.5 * (I_MAX - I_MIN))          # sigma en unidades de la accion [-1,1]


def train(N=7, K=5, sigma=0.05, baseline="mean", updates=3000, B=128, lr=1e-3, noise_w=0.0, seed=0, pool=None, log=True, adv_norm=True, reward="abs"):
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    pool = pool if pool is not None else build_pool(6000, seed=0)
    Iscan = grid_currents(N)
    obs_all = np.stack([table_lookup(pool, np.tile(i, (pool.shape[0], 1)))[:, 0] for i in Iscan], axis=1) / P_NOM   # (M,N)
    pol = Policy(N); opt = torch.optim.Adam(pol.parameters(), lr=lr)
    sa = sigma_action(sigma); t0 = time.time(); hist = []
    for u in range(updates):
        idx = rng.integers(0, pool.shape[0], B)
        obs = obs_all[idx] + (rng.normal(0, noise_w, (B, N)) / P_NOM if noise_w > 0 else 0.0)
        x = torch.tensor(obs, dtype=torch.float32)
        mu = pol(x)                                                         # (B,)
        eps = torch.randn(B, K)
        a = mu[:, None].detach() + sa * eps                                 # (B,K) acciones muestreadas
        I = I_MIN + 0.5 * (np.clip(a.numpy(), -1, 1) + 1.0) * (I_MAX - I_MIN)
        P = table_lookup(pool[idx], I) + (rng.normal(0, noise_w, (B, K)) if noise_w > 0 else 0.0)
        if reward == "gain":                                                # mejora sobre el mejor punto del barrido (potencias MEDIDAS)
            P = P / P_NOM - obs.max(axis=1, keepdims=True)
        else:
            P = P / P_NOM                                                   # recompensa: SOLO potencia medida
        R = torch.tensor(P, dtype=torch.float32)
        if baseline == "none":
            adv = R
        elif baseline == "mean":
            adv = R - (R.sum(1, keepdim=True) - R) / (K - 1)
        else:
            v = pol.v(x).squeeze(-1); adv = R - v[:, None].detach()
        if adv_norm and baseline != "none":
            adv = adv / (adv.std() + 1e-6)
        logp_grad = (a - mu.detach()[:, None]) / sa ** 2                     # d log N / d mu (coeficiente; el gradiente pasa por mu)
        loss = -(adv * logp_grad * mu[:, None]).mean()                      # grad = adv * (a-mu)/sigma^2 * grad mu
        if baseline == "value":
            loss = loss + ((pol.v(x).squeeze(-1)[:, None] - R) ** 2).mean()
        opt.zero_grad(); loss.backward(); opt.step()
        if log and (u % 500 == 0 or u == updates - 1):
            hist.append((u, float(R.mean())))
            print(f"  upd {u:5d}  recompensa media {R.mean():.4f}  ({time.time()-t0:.0f} s)", flush=True)
    return pol, hist


def eval_policy(pol, N, K, sigma, curves, mode="stoch", noise_w=0.0, seed=11, reps=1):
    """mode 'stoch': N + K muestras gaussianas.  mode 'mu': N + 1 medicion en mu (determinista).  mode 'mu+stoch': N + 1 + K."""
    sa = sigma_action(sigma); out = []
    for k, c in enumerate(curves):
        for r in range(reps):
            rng = np.random.default_rng(seed + 1000 * k + r)
            pl = StaticPlant(c, noise_w=noise_w, rng=rng)
            _, P = scan(pl, N)
            with torch.no_grad():
                mu = float(pol(torch.tensor(P / P_NOM, dtype=torch.float32)[None])[0])
            if mode in ("mu", "mu+stoch"):
                pl.run(1.0, action_to_current(mu))
            if mode in ("stoch", "mu+stoch"):
                for _ in range(K):
                    pl.run(1.0, action_to_current(mu + sa * rng.normal()))
            out.append(metrics_from_plant(pl, c))
    return {m: float(np.nanmean([o[m] for o in out])) for m in out[0]}


if __name__ == "__main__":
    from baselines_nivel1_V4 import scenarios
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=7); ap.add_argument("--K", type=int, default=5)
    ap.add_argument("--sigma", type=float, default=0.05); ap.add_argument("--baseline", default="mean", choices=["none", "mean", "value"])
    ap.add_argument("--updates", type=int, default=3000); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--noise", type=float, default=0.0); ap.add_argument("--lr", type=float, default=1e-3)
    a = ap.parse_args()
    real, synth = scenarios()
    pol, hist = train(a.N, a.K, a.sigma, a.baseline, a.updates, lr=a.lr, noise_w=a.noise, seed=a.seed)
    for mode in ("stoch", "mu", "mu+stoch"):
        r = eval_policy(pol, a.N, a.K, a.sigma, real, mode, a.noise, reps=20 if a.noise else 5)
        s = eval_policy(pol, a.N, a.K, a.sigma, synth, mode, a.noise, reps=3)
        print(f"{mode:9s} | reales: n={r['n_meas']:.0f} fin {r['eff_final']:.2f} ener {r['eff_energy']:.2f} | sinteticos: n={s['n_meas']:.0f} fin {s['eff_final']:.2f} ener {s['eff_energy']:.2f}")
