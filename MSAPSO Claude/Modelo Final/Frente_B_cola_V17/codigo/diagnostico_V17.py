"""
diagnostico_V17.py — Por que falla la candidata V14 en estatico. Conjunto de DIAGNOSTICO nuevo (semillas 8080/8081, 1000 curvas; no es S ni P).
Registra, por curva: perdida vs GMPP, mediciones, dispersion del enjambre tras las 3 pasadas, y senales observables candidatas a «detector de pico equivocado».
USO: python3 diagnostico_V17.py -> resultados_V17/diagnostico_V17.txt
"""
import numpy as np
from msapso_early_V14 import *
from campana_base_V14 import methods, NAMES
from pvsim_V14.static_plant_V14 import StaticPlant
from pvsim_V14.msapso_V14 import INIT_FRACS


def diag_curves(n=500):
    r1, r2 = np.random.default_rng(8080), np.random.default_rng(8081)
    return [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(n)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(n)]


def peaks(c, rel=0.02):
    """Maximos locales de la curva P(I) verdadera (para analisis, el controlador no lo ve)."""
    P = c.P; i = np.where((P[1:-1] > P[:-2]) & (P[1:-1] >= P[2:]) & (P[1:-1] > rel * P.max()))[0] + 1
    return c.I[i], P[i]


def bound_gap(I, P, Pbest, Isc):
    """Cota fisica: V(I) no crece con I, asi que entre dos mediciones Ia < Ib, P <= Ib * V(Ia) = Pa * Ib / Ia.
    Devuelve el mayor cociente cota / Pbest entre intervalos NO adyacentes al mejor punto (zonas donde podria esconderse un pico mayor)."""
    o = np.argsort(I); I, P = I[o], P[o]
    I = np.concatenate([I, [Isc]]); P = np.concatenate([P, [0.0]])
    ib = int(np.argmax(P)); best = 0.0
    for a in range(len(I) - 1):
        if abs(a - ib) <= 1 and abs(a + 1 - ib) <= 1: continue
        if I[a] <= 0: continue
        best = max(best, P[a] * I[a + 1] / I[a] / Pbest)
    return best


if __name__ == "__main__":
    M = methods(); cand = M[NAMES[3]]; curves = diag_curves(); rows = []
    for k, c in enumerate(curves):
        rng = np.random.default_rng(7 + 1000 * k); pl = StaticPlant(c, rng=rng)
        # repetimos el MSAPSO corto a mano para leer su dispersion
        from pvsim_V14.msapso_V14 import Swarm
        sw = Swarm(first_pass="ascending"); sw.restart(c.Isc, first=True)
        for _ in range(3): sw.sweep(pl, 1.0); sw.update(paper_beta(sw.t, t_max=3))
        disp3 = sw.dispersion(); first7 = np.array(pl.log_Pmeas[:7]); I21 = np.array(pl.log_I); P21 = np.array(pl.log_Pmeas)
        pl2 = StaticPlant(c, rng=np.random.default_rng(7 + 1000 * k)); cand(pl2, c, np.random.default_rng(7 + 1000 * k))
        Pm = np.array(pl2.log_Pmeas); sel = int(np.where(Pm == Pm.max())[0][-1]); loss = 100 * (1 - pl2.p_true(pl2.log_I[sel]) / c.P_gmpp)
        Ip, Pp = peaks(c); s = np.sort(Pp)[::-1]
        rows.append(dict(loss=loss, n=len(Pm), disp3=disp3, npk=len(Pp), ratio2=(s[1] / s[0]) if len(s) > 1 else 0.0,
                         gap7=bound_gap(np.array(sorted(INIT_FRACS)) * c.Isc, np.array(first7), first7.max(), c.Isc),
                         gap21=bound_gap(I21, P21, P21.max(), c.Isc), gapall=bound_gap(np.array(pl2.log_I), Pm, Pm.max(), c.Isc),
                         Isel=pl2.log_I[sel] / c.Isc, Ig=c.I_gmpp / c.Isc))
    L = np.array([r["loss"] for r in rows]); bad = L > 3
    out = [f"1000 curvas de diagnostico. perdida vs GMPP: media {L.mean():.2f}, p99 {np.percentile(L,99):.2f}, > 3 pp: {bad.sum()} curvas"]
    for key in ("disp3", "npk", "ratio2", "gap7", "gap21", "gapall"):
        v = np.array([r[key] for r in rows])
        out.append(f"  {key:7s}: fallos mediana {np.median(v[bad]):.3f} [min {v[bad].min():.3f}, max {v[bad].max():.3f}] | aciertos mediana {np.median(v[~bad]):.3f} p90 {np.percentile(v[~bad],90):.3f}")
        for th in np.quantile(v, [0.5, 0.7, 0.8, 0.9, 0.95]):
            fl = v > th; out.append(f"      umbral > {th:.3f}: dispara en {100*fl.mean():4.1f} % de curvas, atrapa {fl[bad].sum()}/{bad.sum()} fallos")
    out.append("\nFallos (loss, n, disp3, picos, ratio2, gap7, gap21, gapall, I_sel/Isc, I_gmpp/Isc):")
    for r in sorted([r for r in rows if r["loss"] > 3], key=lambda r: -r["loss"]):
        out.append("  " + " ".join(f"{r[k]:.3f}" if isinstance(r[k], float) else str(r[k]) for k in ("loss", "n", "disp3", "npk", "ratio2", "gap7", "gap21", "gapall", "Isel", "Ig")))
    print("\n".join(out)); open("resultados_V17/diagnostico_V17.txt", "w").write("\n".join(out))
