"""
entorno_V14.py — Entorno de evaluacion DINAMICO y generador de escenarios, copiados SIN CAMBIOS de la V7 (operacion_V7.py, refuerzo_V7.py, campana_V7.py) para que el CEM de la V14
se mida con el MISMO protocolo y los MISMOS escenarios (semillas 100000 + idx) que la campana Monte Carlo de la V7. Aqui no se carga ningun resultado de la V7.
"""
import contextlib
from msapso_early_V14 import *
import pvsim_V14.array_model_V14 as am
from pvsim_V14.static_plant_V14 import DynamicPlantLogged

THRESH, SETTLE_MAX, SEG = 5.0, 10, 300
def run_ops(search_fn, curves, bounds, wait, total, seed=0, noise_w=0.0, backoff=0.0):
    """Operacion: busqueda -> asentamiento -> park -> si |Pbest - P| >= 5 W, reinicio. curves/bounds: sombras y ventana de inicio de cada una."""
    sched = {b: c for b, c in zip(bounds, curves) if b > 0}
    pl = DynamicPlantLogged(curves[0], wait, noise_w=noise_w, rng=np.random.default_rng(seed), schedule=sched); rng = np.random.default_rng(seed + 1); nr = 0; ns = 0
    while len(pl.log_E) < total:
        n0 = len(pl.log_E); search_fn(pl, pl.curve, rng); ns += 1; n1 = len(pl.log_E)
        j = n0 + int(np.argmax(pl.log_Pmeas[n0:n1])); I_sel = pl.log_Ipv[j] * (1.0 - backoff)
        Pb, _ = pl.run(wait, I_sel)
        for _ in range(SETTLE_MAX):
            Pn, _ = pl.run(wait, I_sel); done = abs(Pn - Pb) < 1.0; Pb = Pn
            if done: break
        while len(pl.log_E) < total:
            Pm, _ = pl.run(wait, I_sel)
            if abs(Pb - Pm) >= THRESH: nr += 1; break
    E = np.array(pl.log_E[:total]); ref = 0.0; edges = list(bounds) + [total]
    for c, a, b in zip(curves, edges[:-1], edges[1:]): ref += c.P_ceiling * wait * (b - a)
    Pt = np.array(pl.log_Ptrue[:total]); last = edges[-1]; fin = Pt[last - 20:last].mean() / curves[-1].P_ceiling
    return 100 * E.sum() / ref, 100 * fin, nr, ns


def make_sequence(rng, pool, mean_len, total):
    bounds, w = [0], 0
    while True:
        w += max(15, int(rng.exponential(mean_len)))
        if w >= total: break
        bounds.append(w)
    curves = [pool[int(rng.integers(len(pool)))]]
    for _ in bounds[1:]:
        nxt = pool[int(rng.integers(len(pool)))]
        while nxt is curves[-1]: nxt = pool[int(rng.integers(len(pool)))]
        curves.append(nxt)
    return curves, bounds


def make_curves_aug(M, seed, p_global=0.5, smin=0.25):
    rng = np.random.default_rng(seed); out = []
    for _ in range(M):
        irr = random_shading_mix(rng)
        if rng.random() < p_global: irr = irr * rng.uniform(smin, 1.0)
        out.append(SyntheticPVCurve(irr))
    return out


@contextlib.contextmanager
def panel_ctx(ns, isc, A, nsub=None):
    """Cambia temporalmente los parametros del modelo de un diodo (las curvas guardan sus tablas al construirse)."""
    old = (am.NS, am.ISC_REF, am.RS, am.A_IDEAL, am.IO)
    am.NS, am.ISC_REF, am.A_IDEAL = ns, isc, A
    am.RS = 0.00497 * ns * (8.9 / isc); am.IO = 1.9164e-9 * (isc / 8.9)
    try: yield
    finally: am.NS, am.ISC_REF, am.RS, am.A_IDEAL, am.IO = old


def mix_curves(rng, n, nsub, att=True):
    out = []
    for _ in range(n):
        irr = random_shading_mix(rng, n_sub=nsub)
        if att and rng.random() < 0.5: irr = irr * rng.uniform(0.25, 1.0)
        out.append(SyntheticPVCurve(irr))
    return out


def flicker_sequence(rng, mean_len, amp, total=3000, nsub=4):
    base = random_shading_mix(rng, n_sub=nsub) * (rng.uniform(0.5, 1.0) if rng.random() < 0.5 else 1.0)
    bounds, w = [0], 0
    while True:
        w += max(15, int(rng.exponential(mean_len)))
        if w >= total: break
        bounds.append(w)
    curves = []
    for _ in bounds:
        f = 1.0 - amp * rng.uniform(0, 1, nsub) * (rng.random(nsub) < 0.5)
        curves.append(SyntheticPVCurve(base * f))
    return curves, bounds


PANELS = [("base", 60, 8.9, 1.5, 4), ("72c-6s", 72, 9.5, 1.5, 6), ("36c-3s", 36, 5.5, 1.5, 3), ("60c-11A", 60, 11.0, 1.3, 4), ("96c-6.5A", 96, 6.5, 1.7, 4)]
WAITS = [(5e-3, 0.40), (2e-3, 0.20), (1e-3, 0.20), (5e-4, 0.20)]
REGIMES = [("unico", 0.30), ("moderado", 0.15), ("alto", 0.20), ("muy alto", 0.10), ("flicker", 0.20), ("estable", 0.05)]
NOISES = [(0.0, 0.50), (1.0, 0.25), (2.0, 0.25)]
MEAN = {"moderado": 300, "alto": 100, "muy alto": 40, "estable": 1500}


def pick(rng, table):
    vals = [v for v, _ in table]; p = np.array([w for _, w in table]); return vals[int(rng.choice(len(vals), p=p / p.sum()))]


def make_scenario(idx):
    rng = np.random.default_rng(100000 + idx)
    panel = PANELS[int(rng.integers(len(PANELS)))]; wait = pick(rng, WAITS); reg = pick(rng, REGIMES); noise = pick(rng, NOISES)
    real_src = panel[0] == "base" and rng.random() < 0.30
    meta = dict(idx=idx, panel=panel[0], wait=wait, regimen=reg, ruido=noise, fuente="reales" if real_src else "sinteticos")
    real, _ = scenarios()
    with panel_ctx(panel[1], panel[2], panel[3]):
        nsub = panel[4]
        if reg == "unico":
            if real_src:
                a, b = rng.choice(4, 2, replace=False); curves = [real[a], real[b]]
            else:
                curves = mix_curves(rng, 2, nsub)
            bounds, total = [0, SEG], 2 * SEG
        elif reg == "flicker":
            amp = float(rng.choice([0.1, 0.3, 0.6])); ml = int(rng.choice([100, 40])); meta.update(amp=amp, ml=ml)
            curves, bounds = flicker_sequence(rng, ml, amp, nsub=nsub); total = 3000
        else:
            pool = real if real_src else mix_curves(rng, 30, nsub)
            curves, bounds = make_sequence(rng, pool, MEAN[reg], 3000); total = 3000
    meta["n_seg"] = len(curves)
    return meta, curves, bounds, total
