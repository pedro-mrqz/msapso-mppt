"""
fase0_msapso_V2.py — Fase 0 corregida: algoritmos de busqueda sobre las curvas P(I) ESTATICAS de los 4 casos (sin dinamica de convertidor).
Corrige la V1 en lo pedido por el profesor:
  * APSO con epsilon ~ U[0,1] (como el paper, Eq. 12 y texto bajo la ecuacion), SIN el factor extra Isc*0.05 de la V1; se muestra tambien la
    variante de la V1 (epsilon ~ U[-1,1]) para cuantificar el efecto de la discrepancia.
  * MSAPSO FIEL (7 particulas Isc*[0.95..0.1], beta 0.1->0.95, t_max=25, Gbest inmediato, Eq.13), determinista.
  * PSO de inercia lineal (LW-PSO, ref. [40] del paper): 10 particulas, t_max=50, w 0.9->0.4, alpha=beta=2 (Eq. 10), estocastico.
Variable en por unidad (x = I/Isc). Eficiencia = P(Gbest) / GMPP teorico (aqui no hay convertidor, asi que no aplica el techo alcanzable).
30 semillas por caso para los algoritmos estocasticos. Parametros no dados por el paper (alpha de APSO, beta de APSO) se declaran y se barren.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from pvsim_V2.pvcurve_V2 import load_case

FRACS = np.array([0.95, 0.8, 0.65, 0.5, 0.3, 0.15, 0.1])


def P_of(curve, x):
    return curve.power_at_I(np.clip(x, 0.0, 1.0) * curve.Isc)


def msapso_static(curve, t_max=25, bmin=0.1, bmax=0.95):
    x = np.sort(FRACS)                   # orden ascendente (el orden no importa sin dinamica, pero se respeta el barrido)
    Pbest, G = 0.0, 0.0
    hist = []
    for t in range(1, t_max + 1):
        order = np.argsort(x) if t % 2 == 1 else np.argsort(x)[::-1]
        for i in order:
            P = P_of(curve, x[i])
            if P >= Pbest: Pbest, G = P, x[i]          # Gbest inmediato
        beta = bmin + (t / t_max) * (bmax - bmin)      # Eq. 14
        x = np.clip(x + beta * (G - x), 0, 1)          # Eq. 13
        hist.append(Pbest)
    return Pbest, np.array(hist)


def apso_static(curve, rng, eps_range=(0.0, 1.0), alpha=0.1, beta=0.4, n=7, t_max=25):
    x = rng.uniform(0, 1, n)
    P = P_of(curve, x); gi = np.argmax(P); G, Pbest = x[gi], P[gi]
    hist = [Pbest]
    for t in range(t_max):
        eps = rng.uniform(eps_range[0], eps_range[1], n)
        x = np.clip((1 - beta) * x + beta * G + alpha * eps, 0, 1)         # Eq. 12
        P = P_of(curve, x); j = np.argmax(P)
        if P[j] > Pbest: Pbest, G = P[j], x[j]
        hist.append(Pbest)
    return Pbest, np.array(hist)


def pso_lw_static(curve, rng, n=10, t_max=50, wmax=0.9, wmin=0.4, a=2.0, b=2.0):
    x = rng.uniform(0, 1, n); v = np.zeros(n)
    P = P_of(curve, x); pb_x, pb_P = x.copy(), P.copy(); gi = np.argmax(P); G, Pbest = x[gi], P[gi]
    hist = [Pbest]
    for t in range(1, t_max + 1):
        w = wmax - (wmax - wmin) / t_max * t                               # Eq. 11
        v = w * v + a * rng.uniform(0, 1, n) * (pb_x - x) + b * rng.uniform(0, 1, n) * (G - x)   # Eq. 10
        x = np.clip(x + v, 0, 1)
        P = P_of(curve, x)
        imp = P > pb_P; pb_x[imp], pb_P[imp] = x[imp], P[imp]
        if pb_P.max() > Pbest: Pbest = pb_P.max(); G = pb_x[np.argmax(pb_P)]
        hist.append(Pbest)
    return Pbest, np.array(hist)


if __name__ == "__main__":
    cases = [load_case(i) for i in range(4)]
    N = 30
    rows = {}
    def summarize(name, fn):
        out = []
        for c in cases:
            effs = []
            for s in range(N):
                Pb, _ = fn(c, np.random.default_rng(s))
                effs.append(100 * Pb / c.P_gmpp)
            out.append((float(np.mean(effs)), float(np.min(effs))))
        rows[name] = out
    rows["MSAPSO fiel (determinista)"] = [(100 * msapso_static(c)[0] / c.P_gmpp,) * 2 for c in cases]
    for a in (0.05, 0.1, 0.2):
        summarize(f"APSO, ε~U[0,1] (paper), α={a}", lambda c, r, a=a: apso_static(c, r, (0.0, 1.0), alpha=a))
        summarize(f"APSO, ε~U[-1,1] (como la V1), α={a}", lambda c, r, a=a: apso_static(c, r, (-1.0, 1.0), alpha=a))
    summarize("PSO de inercia lineal (LW-PSO [40])", lambda c, r: pso_lw_static(c, r))
    lines = [f"Eficiencia % sobre el GMPP teorico, curvas P(I) estaticas, {N} semillas (media / minimo)", f"{'algoritmo':44s}" + "".join(f"{'caso '+str(i+1):>16s}" for i in range(4))]
    for k, v in rows.items():
        lines.append(f"{k:44s}" + "".join(f"{m:8.2f}/{mn:6.2f}" for m, mn in v))
    print("\n".join(lines))
    open("resultados_V2/fase0_V2.txt", "w").write("\n".join(lines)); json.dump(rows, open("resultados_V2/fase0_V2.json", "w"))
