"""
refuerzo_V14.py — Cola ESTATICA de la candidata congelada (MSAPSO corto + CEM, retroceso 0.02), con los mismos conjuntos de la V7.1. USO: python3 refuerzo_V14.py S|P -> resultados_V14/refuerzo_<modo>_V14.txt|json
  S  1000 curvas frescas (semillas 7777/7778): perdida de exactitud final vs MSAPSO completo, media, p95, p99, maximo, % > 0.5 pp
  P  100 curvas por panel (semilla 5151), 4 paneles distintos
La exactitud final = potencia verdadera en la corriente elegida (mejor potencia leida) * (1 - b). b = 0 para MSAPSO completo, V7 y la candidata sin retroceso.
"""
import json, sys
from msapso_early_V14 import *
from entorno_V14 import mix_curves, panel_ctx
from pvsim_V14.static_plant_V14 import StaticPlant
from campana_base_V14 import methods, NAMES, boot

M = methods(); CAND = NAMES[3]
COLS = [("MSAPSO completo", NAMES[0], 0.0), ("V7 (parada)", NAMES[1], 0.0), ("candidata b=0", CAND, 0.0), ("candidata b=0.02", CAND, 0.02)]
def final_acc(fn, curves, b):
    fin, nm = [], []
    for k, c in enumerate(curves):
        rng = np.random.default_rng(7 + 1000 * k); pl = StaticPlant(c, rng=rng); fn(pl, c, rng)
        Pm = np.array(pl.log_Pmeas); sel = int(np.where(Pm == Pm.max())[0][-1]); fin.append(100.0 * pl.p_true(pl.log_I[sel] * (1 - b)) / c.P_gmpp); nm.append(len(Pm))
    return np.array(fin), np.array(nm)

if __name__ == "__main__":
    mode = sys.argv[1]; lines = []; out = {}
    def P(s=""): print(s, flush=True); lines.append(s)
    if mode == "S":
        r1 = np.random.default_rng(7777); r2 = np.random.default_rng(7778)
        curves = [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(500)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(500)]
        R = {c[0]: final_acc(M[c[1]], curves, c[2]) for c in COLS}; base = R["MSAPSO completo"][0]
        P("1000 curvas estaticas frescas; sin ruido. perdida = exactitud final MSAPSO completo - metodo (pp)")
        P(f"{'metodo':20s} | med. | final | perdida media [IC95 %] | p95 | p99 | maximo | % > 0.5 pp | % > 3 pp")
        for n, (f, m) in R.items():
            d = base - f; a = boot(-d)
            P(f"{n:20s} | {m.mean():4.0f} | {f.mean():6.2f} | {d.mean():+.3f} [{-a[2]:+.3f}, {-a[1]:+.3f}] | {np.percentile(d,95):.2f} | {np.percentile(d,99):.2f} | {d.max():.2f} | {100*np.mean(d>0.5):5.1f} | {100*np.mean(d>3):4.1f}")
            out[n] = dict(med=float(m.mean()), perdida=float(d.mean()), p95=float(np.percentile(d, 95)), p99=float(np.percentile(d, 99)), max=float(d.max()))
    else:
        panels = [("72 celdas, 6 sub-strings, Isc 9.5 A", 72, 9.5, 1.5, 6), ("36 celdas, 3 sub-strings, Isc 5.5 A", 36, 5.5, 1.5, 3), ("60 celdas, 4 sub-strings, Isc 11 A, A=1.3", 60, 11.0, 1.3, 4), ("96 celdas, 4 sub-strings, Isc 6.5 A, A=1.7", 96, 6.5, 1.7, 4)]
        P("ESTATICO, 100 curvas por panel (semilla 5151). perdida vs MSAPSO completo (pp): media / p99 / maximo")
        for name, ns, isc, A, nsub in panels:
            with panel_ctx(ns, isc, A):
                curves = mix_curves(np.random.default_rng(5151), 100, nsub); R = {c[0]: final_acc(M[c[1]], curves, c[2]) for c in COLS}; base = R["MSAPSO completo"][0]
                P(f"  {name:42s} | " + " | ".join(f"{n[:12]:12s} {(base-f).mean():+.3f}/{np.percentile(base-f,99):.2f}/{(base-f).max():.2f}" for n, (f, m) in list(R.items())[1:]) + f" | med. cand {R['candidata b=0.02'][1].mean():.0f}")
                out[name] = {n: dict(perdida=float((base - f).mean()), p99=float(np.percentile(base - f, 99)), max=float((base - f).max()), med=float(m.mean())) for n, (f, m) in R.items()}
    open(f"resultados_V14/refuerzo_{mode}_V14.txt", "w").write("\n".join(lines)); json.dump(out, open(f"resultados_V14/refuerzo_{mode}_V14.json", "w"), default=float)
