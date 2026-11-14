"""
decentcem_V17.py — V17: DecentCEM (Shi et al., arXiv 2212.08235) y la version del profesor (barrido uniforme + workers por pico) como buscadores de MPPT.
Mismo contrato que el MSAPSO: buscar(planta, curva, rng); cada planta.run(1.0, I) es UNA medicion. x = I / Isc en [0, 1].
 kind='sweep' (brazos A/B): barrido ascendente de N puntos uniformes en [0.10, 0.95]; elites = 3 mejores; un elite es worker nuevo si dista > tau de los ya aceptados (maximo 3);
                            cada worker hace T iteraciones de n muestras N(mu, sigma^2), k=2 elites, mu <- (1-a) mu + a media(elites). sigma_mode 'fixed' (A) o 'floor' (B: sigma <- max((1-a) sigma + a std(elites), floor)).
 kind='paper' (brazo C):    M=3 instancias independientes, medias iniciales 0.2/0.5/0.8, sigma0=0.15, sigma adaptada con piso, n por instancia, k=2, T iteraciones.
Sin parada anticipada: presupuesto fijo. La corriente de operacion la elige el entorno (mejor potencia medida) y aplica el retroceso b.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class Cfg:
    kind: str = "sweep"        # sweep | paper
    sigma_mode: str = "fixed"  # fixed | floor
    N: int = 7
    sigma0: float = 0.03
    tau: float = 0.15
    n: int = 3
    T: int = 3
    k: int = 2
    alpha: float = 0.7
    floor: float = 0.005
    k_sweep: int = 3
    w_max: int = 3
    M: int = 3


def _measure(planta, curva, xs, t):
    order = np.argsort(xs)
    if t % 2 == 1: order = order[::-1]
    P = np.empty(len(xs))
    for j in order: P[j] = planta.run(1.0, xs[j] * curva.Isc)[0]
    return P


def _update(mu, sig, xs, P, cfg, adapt):
    el = xs[np.argsort(P)[::-1][:cfg.k]]
    mu = (1 - cfg.alpha) * mu + cfg.alpha * float(el.mean())
    if adapt: sig = max((1 - cfg.alpha) * sig + cfg.alpha * float(el.std()), cfg.floor)
    return mu, sig


def make_decent(cfg: Cfg):
    def buscar(planta, curva, rng):
        if cfg.kind == "paper":
            mus = np.array([0.2, 0.5, 0.8]); sg = np.full(cfg.M, cfg.sigma0)
            for t in range(cfg.T):
                for w in range(cfg.M):
                    xs = np.clip(mus[w] + sg[w] * rng.normal(size=cfg.n), 0.0, 1.0)
                    P = _measure(planta, curva, xs, t + w)
                    mus[w], sg[w] = _update(mus[w], sg[w], xs, P, cfg, True)
            return
        x0 = np.linspace(0.10, 0.95, cfg.N); P0 = np.empty(cfg.N)
        for j in range(cfg.N): P0[j] = planta.run(1.0, x0[j] * curva.Isc)[0]
        workers = []
        for j in np.argsort(P0)[::-1][:cfg.k_sweep]:
            if all(abs(x0[j] - m) > cfg.tau for m in workers) and len(workers) < cfg.w_max: workers.append(float(x0[j]))
        mus = np.array(workers); sg = np.full(len(workers), cfg.sigma0)
        for t in range(cfg.T):
            for w in range(len(mus)):
                xs = np.clip(mus[w] + sg[w] * rng.normal(size=cfg.n), 0.0, 1.0)
                P = _measure(planta, curva, xs, t + w)
                mus[w], sg[w] = _update(mus[w], sg[w], xs, P, cfg, cfg.sigma_mode == "floor")
    return buscar
