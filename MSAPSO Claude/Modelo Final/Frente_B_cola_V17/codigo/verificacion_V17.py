"""
verificacion_V17.py — V17: candidata V14 (MSAPSO de 3 pasadas + CEM) + VERIFICACION POR COTA FISICA contra el pico equivocado. Sin entrenamiento.

Idea. En un panel el voltaje nunca sube al subir la corriente (V(I) no creciente). Con dos mediciones Ia < Ib, cualquier punto del intervalo cumple
P(I) = I * V(I) <= Ib * V(Ia) = Pa * Ib / Ia. Si esa cota supera la mejor potencia medida, en ese intervalo PODRIA haber un pico mayor; si no la supera,
el intervalo queda descartado con certeza (salvo ruido). Solo usa potencias y corrientes medidas (las del propio controlador).

Metodo (despues de la busqueda corta de la V14, sin tocarla):
  repetir hasta max_probes veces:
    1. ordenar las mediciones por corriente (corriente MEDIDA del panel, Ipv) y agregar (Isc, 0) como extremo derecho;
    2. cota de cada intervalo [Ia, Ib] no pegado al mejor punto: Pa * Ib / Ia;
    3. si ninguna cota supera Pbest * (1 + tau) -> fin (busqueda verificada);
    4. medir en el punto medio del intervalo con la cota mayor; si esa medicion supera a Pbest, el CEM de la V14 refina desde ahi.
Controles (para separar el efecto de la cota):
  «alargar»: si la cota inicial supera Pbest*(1+tau), se repite la busqueda con la V7 completa (MSAPSO con parada por dispersion).
  «ciega»:  siempre mide los max_probes intervalos mas anchos, sin mirar la cota (mismo costo maximo, sin detector).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dataclasses import dataclass
from pvsim_V14.msapso_V14 import Swarm
from baselines_nivel1_V14 import paper_beta
from msapso_cem_V14 import Cfg as CfgM
from msapso_early_V14 import Rule, should_stop

CAND_CFG = CfgM(T0=3, comprimida=True, n=7, k=2, alpha=0.7, sigma0=0.03, sigma_min=0.002, delta=0.005, t_min=2, t_max=12)   # V14 congelada (seleccion_V12 «le40»)


class Rec:
    """Envoltura de la planta que guarda (corriente medida, potencia leida) de cada medicion de la busqueda."""
    def __init__(self, pl): self.pl, self.I, self.P, self.Iref = pl, [], [], []
    @property
    def Ipv(self): return self.pl.Ipv
    @property
    def curve(self): return self.pl.curve
    def run(self, d, I_ref):
        P, e = self.pl.run(d, I_ref); self.I.append(float(self.pl.Ipv)); self.P.append(float(P)); self.Iref.append(float(I_ref)); return P, e


def short_msapso(rp, Isc, cfg):
    sw = Swarm(first_pass="ascending"); sw.restart(Isc, first=True); tm = cfg.T0 if cfg.comprimida else 25
    for _ in range(cfg.T0):
        sw.sweep(rp, 1.0); sw.update(paper_beta(sw.t, t_max=tm))
    return float(np.clip(sw.Gbest / Isc, 0.0, 1.0))


def cem_refine(rp, Isc, mu, cfg, rng):
    """El refinador CEM de la V14, sin cambios."""
    sig = cfg.sigma0
    for t in range(1, cfg.t_max + 1):
        x = np.clip(mu + sig * rng.normal(size=cfg.n), 0.0, 1.0); order = np.argsort(x)
        if t % 2 == 0: order = order[::-1]
        P = np.empty(cfg.n)
        for j in order: P[j] = rp.run(1.0, x[j] * Isc)[0]
        el = x[np.argsort(P)[::-1][:cfg.k]]
        mu = (1 - cfg.alpha) * mu + cfg.alpha * el.mean(); sig = max((1 - cfg.alpha) * sig + cfg.alpha * el.std(), cfg.sigma_min)
        if t >= cfg.t_min and sig < cfg.delta: break


def intervals(I, P, Isc):
    """Intervalos entre mediciones consecutivas (por corriente) con su cota Pa*Ib/Ia; excluye los pegados al mejor punto."""
    I = np.asarray(I); P = np.asarray(P); m = I > 1e-6; I, P = I[m], P[m]
    o = np.argsort(I); I, P = I[o], P[o]
    if I[-1] < Isc: I = np.append(I, Isc); P = np.append(P, 0.0)
    ib = int(np.argmax(P)); out = []
    for a in range(len(I) - 1):
        if a == ib or a + 1 == ib or I[a + 1] - I[a] < 1e-3 * Isc: continue
        out.append((max(P[a], 0.0) * I[a + 1] / I[a], I[a], I[a + 1]))
    return out, float(P.max())


def max_bound_ratio(I, P, Isc):
    iv, Pb = intervals(I, P, Isc)
    return max((b for b, _, _ in iv), default=0.0) / max(Pb, 1e-6)


@dataclass(frozen=True)
class VCfg:
    modo: str = "cota"      # cota | alargar | ciega | ninguna
    tau: float = 0.10
    max_probes: int = 6


def make_verificada(vc: VCfg, cfg: CfgM = CAND_CFG):
    v7 = Rule("disp", delta=0.02, t_min=3)

    def buscar(planta, curva, rng):
        Isc = curva.Isc; rp = Rec(planta)
        cem_refine(rp, Isc, short_msapso(rp, Isc, cfg), cfg, rng)
        if vc.modo == "cota":
            for _ in range(vc.max_probes):
                iv, Pb = intervals(rp.I, rp.P, Isc)
                iv = [x for x in iv if x[0] > Pb * (1 + vc.tau)]
                if not iv: break
                _, a, b = max(iv); Ip = 0.5 * (a + b); P, _ = rp.run(1.0, Ip)
                if P > Pb: cem_refine(rp, Isc, float(np.clip(rp.I[-1] / Isc, 0, 1)), cfg, rng)
        elif vc.modo == "alargar":
            if max_bound_ratio(rp.I, rp.P, Isc) > 1 + vc.tau:
                sw = Swarm(first_pass="ascending"); sw.restart(Isc, first=True); hist = []
                for _ in range(25):
                    sw.sweep(rp, 1.0); hist.append(sw.Pbest); d = sw.dispersion(); sw.update(paper_beta(sw.t, t_max=25))
                    if should_stop(v7, hist, d): break
        elif vc.modo == "ciega":
            for _ in range(vc.max_probes):
                iv, Pb = intervals(rp.I, rp.P, Isc)
                if not iv: break
                _, a, b = max(iv, key=lambda x: x[2] - x[1]); P, _ = rp.run(1.0, 0.5 * (a + b))
                if P > Pb: cem_refine(rp, Isc, float(np.clip(rp.I[-1] / Isc, 0, 1)), cfg, rng)
    return buscar


GRID = [VCfg("ninguna")] + [VCfg("cota", t, k) for t in (0.02, 0.05, 0.10, 0.15, 0.20) for k in (2, 4, 8)] \
     + [VCfg("alargar", t) for t in (0.05, 0.10, 0.20)] + [VCfg("ciega", 0.0, k) for k in (2, 4)]
def name(vc):
    if isinstance(vc, ICfg): return ("ref " if vc.ref else "") + f"intercalado tau={vc.tau:g} k={vc.k} pasadas={vc.passes}" + (f" final tau={vc.tau_final:g}" if vc.tau_final else "")
    return "V14 (sin verif.)" if vc.modo == "ninguna" else f"{vc.modo} tau={vc.tau:g} k={vc.max_probes}" if vc.modo != "alargar" else f"alargar tau={vc.tau:g}"


# ---------------------------------------------------------------------------------------------------------------------------------------
# V17.1 (revision tras la validacion dinamica, ANTES de la prueba): los sondeos de la V17 son saltos grandes de corriente al final de la
# busqueda; a t_wait de 0.5-1 ms el inductor no los sigue y esas ventanas entregan poca potencia. Aqui la misma cota decide DONDE sondear,
# pero los sondeos se INTERCALAN en la escalera de la siguiente pasada del enjambre (se miden en su lugar segun el orden de la pasada),
# asi que cada sondeo es un paso pequeno entre vecinos. Un sondeo que supera a Pbest pasa a ser el Gbest (como cualquier particula);
# no es particula (no se mueve con la Eq. 13). Opcional: verificacion final (modo «cota» de la V17) con un umbral tau_final.
# ---------------------------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ICfg:
    tau: float = 0.05
    k: int = 2              # sondeos maximos por pasada
    passes: int = 2         # en cuantas pasadas (a partir de la 2.a) se intercalan sondeos
    tau_final: float = 0.0  # 0 = sin verificacion final
    k_final: int = 4
    ref: bool = False       # V17.2: la cota usa la corriente PEDIDA (igual a la medida en estatico; en dinamico no refleja el rezago del inductor)


def sweep_with_probes(sw, rp, probes):
    pts = [(float(x), True) for x in sw.x] + [(float(p), False) for p in probes]
    pts.sort(key=lambda t: t[0], reverse=(sw.direction == "descending"))
    for I, part in pts:
        P, _ = rp.run(1.0, I)
        if P >= sw.Pbest: sw.Pbest = P; sw.Gbest = rp.Ipv


def make_intercalado(ic: ICfg, cfg: CfgM = CAND_CFG):
    def buscar(planta, curva, rng):
        Isc = curva.Isc; rp = Rec(planta); sw = Swarm(first_pass="ascending"); sw.restart(Isc, first=True)
        Ib = (lambda: rp.Iref) if ic.ref else (lambda: rp.I)
        for p in range(cfg.T0):
            probes = []
            if 1 <= p <= ic.passes:
                iv, Pb = intervals(Ib(), rp.P, Isc)
                probes = [0.5 * (a + b) for _, a, b in sorted([x for x in iv if x[0] > Pb * (1 + ic.tau)], reverse=True)[:ic.k]]
            sweep_with_probes(sw, rp, probes); sw.update(paper_beta(sw.t, t_max=cfg.T0))
        cem_refine(rp, Isc, float(np.clip(sw.Gbest / Isc, 0.0, 1.0)), cfg, rng)
        if ic.tau_final:
            for _ in range(ic.k_final):
                iv, Pb = intervals(Ib(), rp.P, Isc); iv = [x for x in iv if x[0] > Pb * (1 + ic.tau_final)]
                if not iv: break
                _, a, b = max(iv); P, _ = rp.run(1.0, 0.5 * (a + b))
                if P > Pb: cem_refine(rp, Isc, float(np.clip(rp.I[-1] / Isc, 0, 1)), cfg, rng)
    return buscar


GRID_I = [ICfg(t, k, ps) for t in (0.0, 0.05, 0.10, 0.20) for k in (1, 2, 3) for ps in (1, 2)] \
       + [ICfg(t, k, 2, tf) for t in (0.05, 0.10) for k in (2, 3) for tf in (0.02, 0.05, 0.10, 0.20)]
GRID_R = [ICfg(t, 2, 2, tf, ref=True) for t in (0.05, 0.10, 0.20) for tf in (0.0, 0.02, 0.05, 0.10, 0.20)]   # V17.2


def make_any(v): return make_intercalado(v) if isinstance(v, ICfg) else make_verificada(v)
