"""
neuroevolucion_V18.py — V18: la MISMA red de la V11 (MLP 8 -> h -> h -> 1, ReLU, salida lineal recortada a [0, 1]) entrenada SIN retropropagacion,
con CEM (Cross-Entropy Method) sobre los PESOS:
  1. cada peso es la media de una gaussiana (mu, sigma) independiente;
  2. se muestrean `pop` redes completas;
  3. cada red se evalua por la POTENCIA que obtiene en curvas de entrenamiento: p = P(x_pred) / P_gmpp. Objetivo = media(p) + cola * media del
     10 % peor de p (cola = 0: solo la media; cola = 1: castiga ademas los fallos graves). No se usa el error contra x*;
  4. se conservan las `elite` mejores redes y mu, sigma se mueven hacia su media y su desviacion (suavizado alpha, piso de ruido que decrece);
  5. se repite `gens` generaciones. La red final es mu.
Despliegue (igual que la V11): barrido de 7 mediciones -> la red predice x* = I/Isc -> CEM sobre la CORRIENTE refina -> retroceso 2 %
(el retroceso lo aplican run_ops / final_acc). Opcional: verificacion final por cota fisica de la V17 despues del refinado.
Datos: el mismo generador y la misma semilla que la red de la V11 (mlp_cem_V14.make_dataset(30000, 1111)), asi que la unica diferencia
entre V11 y V18 es el metodo de entrenamiento y la funcion objetivo.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dataclasses import dataclass, replace
from msapso_early_V14 import SyntheticPVCurve, random_shading_mix
from mlp_cem_V14 import features, FR
from msapso_cem_V14 import Cfg as CfgM
from verificacion_V17 import Rec, cem_refine, intervals

NX = 501                                   # rejilla de x = I/Isc para evaluar la potencia de cada prediccion
XG = np.linspace(0.0, 1.0, NX)


# ---------------------------------------------------------------- datos
def make_tables(n, seed):
    """Mismo generador que mlp_cem_V14.make_dataset(n, seed) (sin ruido): X caracteristicas (n, 8), y = x* (n,), T = P(x)/P_gmpp en XG (n, NX)."""
    r = np.random.default_rng(seed); X, y, T = [], [], []
    for _ in range(n):
        irr = random_shading_mix(r)
        if r.random() < 0.5: irr = irr * r.uniform(0.25, 1.0)
        c = SyntheticPVCurve(irr); Ps = np.interp(FR * c.Isc, c.I, c.P, right=0.0)
        X.append(features(Ps)); y.append(c.I_gmpp / c.Isc); T.append(np.interp(XG * c.Isc, c.I, c.P, right=0.0) / c.P_gmpp)
    return np.array(X, np.float32), np.array(y), np.array(T, np.float32)


def lookup(T, xh):
    """T (B, NX), xh (..., B) -> potencia relativa interpolada en xh (recortado a [0, 1])."""
    pos = np.clip(xh, 0.0, 1.0) * (NX - 1); i0 = np.minimum(pos.astype(np.int64), NX - 2); f = pos - i0
    rows = np.arange(T.shape[0])
    return T[rows, i0] * (1 - f) + T[rows, i0 + 1] * f


# ---------------------------------------------------------------- red
def shapes(h): d = [8, *h, 1]; return [(d[i], d[i + 1]) for i in range(len(d) - 1)]
def n_params(h): return sum(a * b + b for a, b in shapes(h))


def init_scale(h):
    """Desviacion inicial por parametro: escala de He (sqrt(2/fan_in)) en los pesos, 0.1 en los sesgos."""
    s = []
    for a, b in shapes(h): s += [np.sqrt(2.0 / a)] * (a * b) + [0.1] * b
    return np.array(s, np.float32)


def forward_batch(Th, X, h):
    """Th (P, D) parametros de P redes, X (B, 8) -> salidas (P, B)."""
    P = Th.shape[0]; A = np.broadcast_to(X, (P,) + X.shape); off = 0; sh = shapes(h)
    for li, (a, b) in enumerate(sh):
        W = Th[:, off:off + a * b].reshape(P, a, b); off += a * b; bb = Th[:, off:off + b]; off += b
        A = np.matmul(A, W) + bb[:, None, :]
        if li < len(sh) - 1: A = np.maximum(A, 0.0)
    return A[..., 0]


class Red:
    """MLP en numpy (ReLU, salida lineal recortada a [0, 1]). Se construye desde un vector de parametros (V18) o desde el MLPRegressor de la V11."""
    def __init__(self, Ws, bs): self.Ws, self.bs = [np.asarray(w, float) for w in Ws], [np.asarray(b, float) for b in bs]
    @classmethod
    def from_theta(cls, theta, h):
        Ws, bs, off = [], [], 0
        for a, b in shapes(h):
            Ws.append(theta[off:off + a * b].reshape(a, b)); off += a * b; bs.append(theta[off:off + b]); off += b
        return cls(Ws, bs)
    @classmethod
    def from_sklearn(cls, m): return cls(m.coefs_, m.intercepts_)
    def predict(self, X):
        A = np.atleast_2d(np.asarray(X, float))
        for i, (W, b) in enumerate(zip(self.Ws, self.bs)):
            A = A @ W + b
            if i < len(self.Ws) - 1: A = np.maximum(A, 0.0)
        return A[:, 0]


# ---------------------------------------------------------------- entrenamiento por CEM sobre los pesos
@dataclass(frozen=True)
class NECfg:
    h: tuple = (32, 32)
    cola: float = 0.0       # peso del 10 % peor en el objetivo (0 = solo la media)
    pop: int = 200          # redes por generacion
    elite: float = 0.1      # fraccion de elites
    alpha: float = 0.7      # suavizado de mu y sigma
    gens: int = 2000
    batch: int = 2000       # curvas por generacion (las mismas para todas las redes de esa generacion)
    eps0: float = 0.05      # piso de ruido inicial (fraccion de la escala inicial); decrece linealmente a 0
    seed: int = 0
    s0_ref: float = 0.0     # V18.1: > 0 -> el objetivo es la CADENA COMPLETA (barrido + red + CEM sobre la corriente con este sigma0)


def ne_name(c): return f"NE {'x'.join(map(str, c.h))} cola={c.cola:g}" + (f" ref={c.s0_ref:g}" if c.s0_ref else "")


# ---------------------------------------------------------------- V18.1: simulacion vectorizada de la cadena completa (sin ruido)
I_FR = np.rint(FR * (NX - 1)).astype(np.int64)      # el barrido cae exactamente en la rejilla (0.1, 0.15, ... 0.95)


def cadena(T, x0, s0, Z, cfg=None):
    """Resultado de la cadena completa para P redes en B curvas: mejor potencia medida / P_gmpp tras el barrido de 7 y el CEM sobre la corriente
    (mismo algoritmo que verificacion_V17.cem_refine, con parada individual). T (B, NX); x0 (P, B) predicciones; Z (B, t_max, n) normales comunes."""
    cfg = cfg or REF; a = cfg.alpha; Pn, B = x0.shape; rows = np.arange(B)[None, :, None]
    mu = np.clip(x0, 0, 1).astype(np.float32); sig = np.full_like(mu, s0); best = np.broadcast_to(T[:, I_FR].max(1), (Pn, B)).copy(); act = np.ones((Pn, B), bool)
    for t in range(cfg.t_max):
        x = np.clip(mu[..., None] + sig[..., None] * Z[None, :, t, :], 0.0, 1.0); pos = x * (NX - 1); i0 = np.minimum(pos.astype(np.int64), NX - 2); f = pos - i0
        p = T[rows, i0] * (1 - f) + T[rows, i0 + 1] * f
        best = np.where(act, np.maximum(best, p.max(-1)), best)
        el = np.take_along_axis(x, np.argsort(p, -1)[..., ::-1][..., :cfg.k], -1)
        mu = np.where(act, (1 - a) * mu + a * el.mean(-1), mu); sig = np.where(act, np.maximum((1 - a) * sig + a * el.std(-1), cfg.sigma_min), sig)
        if t + 1 >= cfg.t_min: act &= ~(sig < cfg.delta)
        if not act.any(): break
    return best


def entrenar(cfg, Xtr, Ttr, Xmon, Tmon, log_every=10):
    """Devuelve (theta = mu final, registro). Registro: generacion, objetivo medio de las elites y, para mu en el conjunto de monitoreo, la potencia
    en el punto predicho (mon, mon_p1) y el resultado de la cadena completa con refinado (mon_cadena, mon_cadena_p1; sigma0 = s0_ref o 0.1)."""
    rng = np.random.default_rng(cfg.seed); D = n_params(cfg.h); s0 = init_scale(cfg.h)
    mu = np.zeros(D, np.float32); sig = s0.copy(); ne = max(2, int(round(cfg.pop * cfg.elite))); log = []
    for g in range(cfg.gens):
        bi = rng.choice(len(Xtr), cfg.batch, replace=False)
        Th = (mu + sig * rng.standard_normal((cfg.pop, D))).astype(np.float32)
        if cfg.s0_ref: p = cadena(Ttr[bi], forward_batch(Th, Xtr[bi], cfg.h), cfg.s0_ref, rng.standard_normal((cfg.batch, REF.t_max, REF.n)).astype(np.float32))
        else: p = lookup(Ttr[bi], forward_batch(Th, Xtr[bi], cfg.h))
        F = p.mean(1)
        if cfg.cola: F = F + cfg.cola * np.sort(p, axis=1)[:, :cfg.batch // 10].mean(1)
        el = Th[np.argsort(F)[::-1][:ne]]; eps = cfg.eps0 * max(0.0, 1.0 - g / cfg.gens)
        mu = (1 - cfg.alpha) * mu + cfg.alpha * el.mean(0); sig = (1 - cfg.alpha) * sig + cfg.alpha * el.std(0) + eps * s0
        if g % log_every == 0 or g == cfg.gens - 1:
            xm = forward_batch(mu[None], Xmon, cfg.h); pm = lookup(Tmon, xm)[0]
            pc = cadena(Tmon, xm, cfg.s0_ref or 0.1, np.random.default_rng(99).standard_normal((len(Xmon), REF.t_max, REF.n)).astype(np.float32))[0]
            log.append(dict(gen=g, elite=float(np.sort(F)[::-1][:ne].mean()), mon=float(pm.mean()), mon_p1=float(np.percentile(pm, 1)),
                            mon_cadena=float(pc.mean()), mon_cadena_p1=float(np.percentile(pc, 1)), sig=float(sig.mean())))
    return mu, log


# ---------------------------------------------------------------- despliegue: barrido de 7 + red + CEM sobre la corriente (+ cota de la V17)
REF = CfgM(T0=0, n=7, k=2, alpha=0.7, sigma0=0.1, sigma_min=0.002, delta=0.005, t_min=2, t_max=12)   # refinado de la V11 congelado (seleccion_V11)


@dataclass(frozen=True)
class PCfg:
    sigma0: float = 0.1     # sigma inicial del CEM sobre la corriente (V11: 0.1)
    cota: bool = False      # verificacion final de la V17: hasta 4 sondeos donde la cota (corriente pedida) supere Pbest*1.05


def make_red_cem(red, pc: PCfg):
    cfg = replace(REF, sigma0=pc.sigma0)
    def buscar(planta, curva, rng):
        Isc = curva.Isc; rp = Rec(planta)
        Ps = np.array([rp.run(1.0, f * Isc)[0] for f in FR])                                 # barrido de 7 mediciones (ascendente)
        mu = float(np.clip(red.predict(features(Ps))[0], 0.0, 1.0))
        cem_refine(rp, Isc, mu, cfg, rng)
        if pc.cota:
            for _ in range(4):
                iv, Pb = intervals(rp.Iref, rp.P, Isc); iv = [x for x in iv if x[0] > Pb * 1.05]
                if not iv: break
                _, a, b = max(iv); P, _ = rp.run(1.0, 0.5 * (a + b))
                if P > Pb: cem_refine(rp, Isc, float(np.clip(rp.I[-1] / Isc, 0, 1)), cfg, rng)
    return buscar


def p_name(pc): return f"s0={pc.sigma0:g}" + (" +cota" if pc.cota else "")
