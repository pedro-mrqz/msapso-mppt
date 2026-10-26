"""
reinforce_nn_V5.py — REINFORCE con MLP, FORMULACION CORREGIDA (V5). Nivel 1 (potencia estatica), sin GMPP en entrenamiento.

Correcciones respecto a la V4 (cada una ataca la causa probable del resultado de la V4: se optimizaba la potencia PROMEDIO de las
muestras, lo que empuja sigma a 0 y no premia al MEJOR punto, que es el que se elige al final):
  (a) reward = "max":  recompensa de GRUPO = max_k P_k (la mejor muestra de los K, potencia MEDIDA) -> objetivo J = E[max_k P(a_k)].
      reward = "gain": recompensa de GRUPO = max(0, max_k P_k - mejor punto del barrido), solo cuenta cuanto MEJORA lo ya conocido.
      reward = "mean": la de la V4 (potencia de cada muestra), para comparar.
      Gradiente de grupo:  grad J = E[ (G - b) * sum_k (a_k - mu)/sigma^2 * grad mu ]
  (b) sigma FIJA (sigma1 = None) o DECRECIENTE (de sigma0 a sigma1, lineal en las actualizaciones): no se aprende sigma, no puede colapsar.
  (c) K de entrenamiento (K_train) distinto del K de evaluacion: p. ej. 20 muestras al entrenar y 5 al evaluar.
Baselines b: "none" | "batch" (media movil de G) | "value" (V(obs) aprendida).
USO: python3 reinforce_nn_V5.py --reward max --baseline value --K-train 20 --sigma0 0.05
"""
import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch, torch.nn as nn
from pvsim_V5.array_model_V5 import SyntheticPVCurve, random_shading_mix
from pvsim_V5.static_plant_V5 import StaticPlant
from pvsim_V5.medicion_V5 import (ISC_NOM, I_MIN, I_MAX, P_NOM, grid_currents, scan, metrics_from_plant, action_to_current)

TABLE_PTS = 600


def p_table(curve):
    Ig = np.linspace(0.0, ISC_NOM, TABLE_PTS)
    return np.interp(Ig, curve.I, curve.P, right=0.0).astype(np.float32)


def build_pool(M, seed=0):
    rng = np.random.default_rng(seed)
    return np.stack([p_table(SyntheticPVCurve(random_shading_mix(rng))) for _ in range(M)])


def table_lookup(tab, I):
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
    return sigma_frac * ISC_NOM / (0.5 * (I_MAX - I_MIN))


def train(N=7, K_train=20, sigma0=0.05, sigma1=None, baseline="value", reward="max", updates=4000, B=128, lr=1e-3,
          noise_w=0.0, seed=0, pool=None, log=False):
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    pool = pool if pool is not None else build_pool(6000, seed=0)
    Iscan = grid_currents(N)
    obs_all = np.stack([table_lookup(pool, np.tile(i, (pool.shape[0], 1)))[:, 0] for i in Iscan], axis=1) / P_NOM
    pol = Policy(N); opt = torch.optim.Adam(pol.parameters(), lr=lr)
    b_run, t0, K = 0.0, time.time(), K_train
    for u in range(updates):
        frac = u / max(updates - 1, 1)
        sig = sigma0 if sigma1 is None else sigma0 + (sigma1 - sigma0) * frac
        sa = sigma_action(sig)
        idx = rng.integers(0, pool.shape[0], B)
        obs = obs_all[idx] + (rng.normal(0, noise_w, (B, N)) / P_NOM if noise_w > 0 else 0.0)
        x = torch.tensor(obs, dtype=torch.float32)
        mu = pol(x)
        a = mu[:, None].detach() + sa * torch.randn(B, K)
        I = I_MIN + 0.5 * (np.clip(a.numpy(), -1, 1) + 1.0) * (I_MAX - I_MIN)
        P = table_lookup(pool[idx], I) + (rng.normal(0, noise_w, (B, K)) if noise_w > 0 else 0.0)
        Pn = P / P_NOM                                                       # SOLO potencia medida
        scan_best = obs.max(axis=1)
        if reward == "mean":                                                 # V4: recompensa por muestra
            G = torch.tensor(Pn, dtype=torch.float32)                        # (B,K)
        elif reward == "max":
            G = torch.tensor(Pn.max(axis=1), dtype=torch.float32)            # (B,)
        elif reward == "gain":
            G = torch.tensor(np.maximum(Pn.max(axis=1) - scan_best, 0.0), dtype=torch.float32)
        else:
            raise ValueError(reward)
        if baseline == "value":
            v = pol.v(x).squeeze(-1)
            b = v.detach()[:, None] if reward == "mean" else v.detach()
        elif baseline == "batch":
            b_run = 0.95 * b_run + 0.05 * float(G.mean()); b = b_run
        else:
            b = 0.0
        adv = G - b
        adv = adv / (adv.std() + 1e-6) if baseline != "none" else adv
        score = (a - mu.detach()[:, None]) / sa ** 2                         # (B,K)
        if reward == "mean":
            loss = -(adv * score * mu[:, None]).mean()
        else:
            loss = -(adv * score.mean(dim=1) * mu).mean()                    # score de grupo (promedio de las K)
        if baseline == "value":
            tgt = G.mean(dim=1) if reward == "mean" else G
            loss = loss + ((pol.v(x).squeeze(-1) - tgt) ** 2).mean()
        opt.zero_grad(); loss.backward(); opt.step()
        if log and (u % 1000 == 0 or u == updates - 1):
            print(f"  upd {u:5d}  G medio {float(G.mean()):.4f}  sigma {sig:.3f}  ({time.time()-t0:.0f} s)", flush=True)
    return pol


def eval_policy(pol, N, K, sigma, curves, mode="stoch", noise_w=0.0, seed=11, reps=1):
    """mode 'stoch': N + K muestras gaussianas.  'mu': N + 1 en mu.  'mu+stoch': N + 1 + K."""
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


def build_pool_aug(M, seed=0, p_global=0.5, smin=0.25):
    """Banco con ATENUACION GLOBAL: con prob. p_global todas las irradiancias se multiplican por U[smin,1] (cielo nublado / suciedad general),
    lo que produce patrones de Isc baja que el generador original casi no produce. Solo curvas sinteticas."""
    rng = np.random.default_rng(seed); tabs = []
    for _ in range(M):
        irr = random_shading_mix(rng)
        if rng.random() < p_global:
            irr = irr * rng.uniform(smin, 1.0)
        tabs.append(p_table(SyntheticPVCurve(irr)))
    return np.stack(tabs)
