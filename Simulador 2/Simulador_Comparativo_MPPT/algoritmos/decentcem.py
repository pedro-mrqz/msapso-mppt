"""
decentcem.py — V17: DecentCEM (Shi et al., arXiv 2212.08235) y la version del profesor (barrido uniforme + workers por pico) como buscadores de MPPT.
Mismo contrato que el MSAPSO: buscar(planta, curva, rng); cada planta.run(1.0, I) es UNA medicion. x = I / Isc en [0, 1].
 kind='sweep' (brazos A/B): barrido ascendente de N puntos uniformes en [0.10, 0.95]; elites = 3 mejores; un elite es worker nuevo si dista > tau de los ya aceptados (maximo 3);
                            cada worker hace T iteraciones de n muestras N(mu, sigma^2), k=2 elites, mu <- (1-a) mu + a media(elites). sigma_mode 'fixed' (A) o 'floor' (B: sigma <- max((1-a) sigma + a std(elites), floor)).
 kind='paper' (brazo C):    M=3 instancias independientes, medias iniciales 0.2/0.5/0.8, sigma0=0.15, sigma adaptada con piso, n por instancia, k=2, T iteraciones.
Sin parada anticipada: presupuesto fijo. La corriente de operacion la elige el entorno (mejor potencia medida) y aplica el retroceso b.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from dataclasses import dataclass
from pvsim.static_plant import set_tag


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
    elite_frac: float = 0.0    # > 0: elites por iteracion = max(1, round(elite_frac * n)) en lugar de k fijo (pedido del profesor: % de elites parametrizable)
    borde: bool = False        # True = barrido parejo de N puntos entre el BORDE alcanzable (V/I = 12 ohm) y 0.95 Isc (revision del profesor; ver borde_alcanzable)


def _measure(planta, curva, xs, t):
    order = np.argsort(xs)
    if t % 2 == 1: order = order[::-1]
    P = np.empty(len(xs))
    for j in order: P[j] = planta.run(1.0, xs[j] * curva.Isc)[0]
    return P


def _update(mu, sig, xs, P, cfg, adapt):
    k = max(1, int(round(cfg.elite_frac * len(xs)))) if cfg.elite_frac > 0 else cfg.k
    el = xs[np.argsort(P)[::-1][:k]]
    mu = (1 - cfg.alpha) * mu + cfg.alpha * float(el.mean())
    if adapt: sig = max((1 - cfg.alpha) * sig + cfg.alpha * float(el.std()), cfg.floor)
    return mu, sig


def borde_alcanzable(curva, R=12.0, x_min=0.10):
    """ORACULO (revision del profesor, nov. 2026): fraccion de Isc donde la curva cruza V/I = R, es decir, la menor corriente en la que el Boost
    con carga R puede operar en regimen permanente. Usa la curva verdadera, que un controlador real NO conoce: sirve como COTA SUPERIOR de lo que
    se ganaria repartiendo el barrido solo en la zona alcanzable. Un sondeo medido (pedir I = 0 y leer Ipv) se probo y no es confiable con
    t_wait <= 2 ms: el convertidor no llega al borde en una ventana."""
    I = np.linspace(1e-3, curva.Isc, 4000); P = np.interp(I, curva.I, curva.P, right=0.0); ok = P <= R * I * I
    xb = float(I[int(np.argmax(ok))] / curva.Isc) if ok.any() else x_min
    return max(xb, x_min)


def make_decent(cfg: Cfg):
    def buscar(planta, curva, rng):
        if cfg.kind == "paper":
            mus = np.array([0.2, 0.5, 0.8]); sg = np.full(cfg.M, cfg.sigma0)
            for t in range(cfg.T):
                for w in range(cfg.M):
                    set_tag(planta, t, w)
                    xs = np.clip(mus[w] + sg[w] * rng.normal(size=cfg.n), 0.0, 1.0)
                    P = _measure(planta, curva, xs, t + w)
                    mus[w], sg[w] = _update(mus[w], sg[w], xs, P, cfg, True)
            return
        x0 = np.linspace(borde_alcanzable(curva) if cfg.borde else 0.10, 0.95, cfg.N); P0 = np.empty(cfg.N); set_tag(planta, 0)
        for j in range(cfg.N): P0[j] = planta.run(1.0, x0[j] * curva.Isc)[0]
        workers = []
        for j in np.argsort(P0)[::-1][:cfg.k_sweep]:
            if all(abs(x0[j] - m) > cfg.tau for m in workers) and len(workers) < cfg.w_max: workers.append(float(x0[j]))
        mus = np.array(workers); sg = np.full(len(workers), cfg.sigma0)
        for t in range(cfg.T):
            for w in range(len(mus)):
                xs = np.clip(mus[w] + sg[w] * rng.normal(size=cfg.n), 0.0, 1.0)
                set_tag(planta, t + 1, w)                          # worker w, iteracion t + 1
                P = _measure(planta, curva, xs, t + w)
                mus[w], sg[w] = _update(mus[w], sg[w], xs, P, cfg, cfg.sigma_mode == "floor")
    return buscar
