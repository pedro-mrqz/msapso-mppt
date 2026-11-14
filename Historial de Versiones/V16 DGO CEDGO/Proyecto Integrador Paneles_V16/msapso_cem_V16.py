"""
msapso_cem_V16.py — V16: MSAPSO CORTO (T0 pasadas, sin entrenamiento) ubica el pico y CEM converge desde su Gbest. Control de la V11 (MLP + CEM).
MSAPSO: 7 particulas Isc*[.1 ... .95], Eq. 13 y alternancia del paper (beta del paper con t_max = 25 o comprimida a T0 pasadas). CEM: mu0 = Gbest/Isc, sigma0 pequena, parada sigma < delta.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dataclasses import dataclass
from pvsim_V16.msapso_V16 import Swarm
from baselines_nivel1_V16 import paper_beta


@dataclass(frozen=True)
class Cfg:
    T0: int = 4
    comprimida: bool = False
    n: int = 5
    k: int = 2
    alpha: float = 1.0
    sigma0: float = 0.06
    sigma_min: float = 0.002
    delta: float = 0.01
    t_min: int = 2
    t_max: int = 12


def make_msapso_cem(cfg: Cfg):
    def buscar(planta, curva, rng):
        sw = Swarm(first_pass="ascending"); sw.restart(curva.Isc, first=True); tm = cfg.T0 if cfg.comprimida else 25
        for _ in range(cfg.T0):
            sw.sweep(planta, 1.0); sw.update(paper_beta(sw.t, t_max=tm))
        mu, sig = float(np.clip(sw.Gbest / curva.Isc, 0.0, 1.0)), cfg.sigma0
        for t in range(1, cfg.t_max + 1):
            x = np.clip(mu + sig * rng.normal(size=cfg.n), 0.0, 1.0); order = np.argsort(x)
            if t % 2 == 0: order = order[::-1]
            P = np.empty(cfg.n)
            for j in order: P[j] = planta.run(1.0, x[j] * curva.Isc)[0]
            el = x[np.argsort(P)[::-1][:cfg.k]]
            mu = (1 - cfg.alpha) * mu + cfg.alpha * el.mean(); sig = max((1 - cfg.alpha) * sig + cfg.alpha * el.std(), cfg.sigma_min)
            if t >= cfg.t_min and sig < cfg.delta: break
    return buscar
