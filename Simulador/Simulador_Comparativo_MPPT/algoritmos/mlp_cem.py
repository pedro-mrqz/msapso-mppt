"""
mlp_cem.py — V13 (EXPLORATORIO): un MLP UBICA el pico global y CEM CONVERGE desde ahi (idea 4 del profesor; Frente B, primera aproximacion rapida).
Pasos del metodo: (1) barrido de 7 mediciones en las posiciones iniciales del MSAPSO (Isc*[0.1 ... 0.95]); (2) el MLP recibe las 7 potencias (normalizadas por la mayor medida) y la mayor medida / P_nom y predice x* = I_gmpp / Isc;
(3) CEM con mu0 = x* y sigma0 PEQUENA refina; parada por sigma < delta. Punto final = mayor potencia medida (como siempre).
Controles: «sin modelo» (CEM desde el mejor punto del barrido) y «solo MLP» (barrido + 1 medicion en x*).
El MLP se entrena SUPERVISADO (regresion de x*), lo que da una COTA SUPERIOR de lo que Evolution Strategies / RL podrian lograr con la misma red y los mismos datos: si ni asi funciona, ES tampoco.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from dataclasses import dataclass
from sklearn.neural_network import MLPRegressor
from algoritmos.msapso_early import SyntheticPVCurve, random_shading_mix
from pvsim.medicion import P_NOM
from pvsim.msapso import INIT_FRACS

FR = np.array(sorted(INIT_FRACS))


def features(Ps):
    Ps = np.asarray(Ps, float); m = max(Ps.max(), 1e-6)
    return np.concatenate([Ps / m, [m / P_NOM]])


def make_dataset(n, seed, noise_w=0.0):
    r = np.random.default_rng(seed); X, y = [], []
    for _ in range(n):
        irr = random_shading_mix(r)
        if r.random() < 0.5: irr = irr * r.uniform(0.25, 1.0)
        c = SyntheticPVCurve(irr); Ps = np.interp(FR * c.Isc, c.I, c.P, right=0.0) + (r.normal(0, noise_w, 7) if noise_w > 0 else 0)
        X.append(features(Ps)); y.append(c.I_gmpp / c.Isc)
    return np.array(X), np.array(y)


def train_mlp(n=8000, seed=1111, hidden=(64, 64), noise_w=0.0):
    X, y = make_dataset(n, seed, noise_w)
    return MLPRegressor(hidden_layer_sizes=hidden, max_iter=600, early_stopping=True, random_state=0).fit(X, y)


@dataclass(frozen=True)
class Cfg:
    modo: str = "mlp"        # mlp | sin_modelo | solo_mlp
    n: int = 5
    k: int = 2
    alpha: float = 1.0
    sigma0: float = 0.06
    sigma_min: float = 0.002
    delta: float = 0.01
    t_min: int = 2
    t_max: int = 12


def make_mlp_cem(model, cfg: Cfg):
    def buscar(planta, curva, rng):
        Ps = np.array([planta.run(1.0, f * curva.Isc)[0] for f in FR])          # barrido de 7 mediciones (ascendente)
        if cfg.modo == "sin_modelo": mu = FR[int(np.argmax(Ps))]
        else: mu = float(np.clip(model.predict(features(Ps)[None])[0], 0.0, 1.0))
        if cfg.modo == "solo_mlp":
            planta.run(1.0, mu * curva.Isc); return
        sig = cfg.sigma0
        for t in range(1, cfg.t_max + 1):
            x = np.clip(mu + sig * rng.normal(size=cfg.n), 0.0, 1.0); order = np.argsort(x)
            if t % 2 == 0: order = order[::-1]
            P = np.empty(cfg.n)
            for j in order: P[j] = planta.run(1.0, x[j] * curva.Isc)[0]
            el = x[np.argsort(P)[::-1][:cfg.k]]
            mu = (1 - cfg.alpha) * mu + cfg.alpha * el.mean(); sig = max((1 - cfg.alpha) * sig + cfg.alpha * el.std(), cfg.sigma_min)
            if t >= cfg.t_min and sig < cfg.delta: break
    return buscar
