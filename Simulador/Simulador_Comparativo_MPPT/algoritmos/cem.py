"""
cem.py — V10: Cross-Entropy Method (CEM) PURO como buscador de MPPT. Mismo contrato que el MSAPSO: buscar(planta, curva, rng); cada planta.run(1.0, I) es UNA medicion.
Ver diseno_V10.md. x = I / Isc; gaussiana N(mu, sigma^2) recortada a [0, 1]; n candidatos por iteracion; k elites; actualizacion suavizada con alpha; parada por sigma < delta.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class CEMCfg:
    n: int = 7             # candidatos por iteracion
    k: int = 2             # elites
    alpha: float = 1.0     # suavizado (1 = CEM clasico)
    mu0: float = 0.5
    sigma0: float = 0.3
    sigma_min: float = 0.0
    delta: float = 0.02    # parada: sigma < delta (None = sin parada, t_max iteraciones)
    t_min: int = 3
    t_max: int = 25


def make_cem(cfg: CEMCfg):
    def buscar(planta, curva, rng):
        mu, sig = cfg.mu0, cfg.sigma0
        for t in range(1, cfg.t_max + 1):
            x = np.clip(mu + sig * rng.normal(size=cfg.n), 0.0, 1.0)
            order = np.argsort(x)
            if t % 2 == 0:
                order = order[::-1]                      # barrido alternante, como el MSAPSO
            P = np.empty(cfg.n)
            for j in order:
                P[j] = planta.run(1.0, x[j] * curva.Isc)[0]
            el = x[np.argsort(P)[::-1][:cfg.k]]
            mu = (1 - cfg.alpha) * mu + cfg.alpha * el.mean()
            sig = max((1 - cfg.alpha) * sig + cfg.alpha * el.std(), cfg.sigma_min)
            if cfg.delta is not None and t >= cfg.t_min and sig < cfg.delta:
                break
    return buscar
