"""
dinamico_V17.py — Energia DINAMICA de las variantes con verificacion, mismo entorno y escenarios de la campana V7/V14 (run_ops, semillas 100000 + idx).
USO: python3 dinamico_V17.py val|val2             -> (val2 = rejilla V17.1 intercalada) escenarios 600-1199 (VALIDACION), todas las variantes con b = 0.02
     python3 dinamico_V17.py test "<variante>"    -> 0-599 (PRUEBA) y 1200-2399 (CONFIRMACION), variante congelada, con desglose como en campana_V14
Referencias en cada escenario: MSAPSO completo (b = 0), V7 (b = 0), V14 (b = 0.02).
-> resultados_V17/dinamico_<modo>_V17.txt|json
"""
import json, sys
from multiprocessing import Pool
import numpy as np
from entorno_V14 import make_scenario, run_ops, make_msapso_early, Rule
from verificacion_V17 import GRID, GRID_I, GRID_R, VCfg, make_verificada, make_any, name

B = 0.02
FULL, V7 = make_msapso_early(Rule("none")), make_msapso_early(Rule("disp", delta=0.02, t_min=3))


def task(a):
    idx, variants = a; meta, curves, bounds, total = make_scenario(idx); out = dict(idx=idx)
    runs = [("MSAPSO", FULL, 0.0), ("V7", V7, 0.0), ("V14", make_verificada(VCfg("ninguna")), B)] + [(name(v), make_any(v), B) for v in variants]
    for n, fn, b in runs:
        e, fin, nr, ns = run_ops(fn, curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"], backoff=b); out[n] = [e, fin, nr, ns]
    return out


def boot(d, B_=3000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B_, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
f3 = lambda t: f"{t[0]:+.2f} [{t[1]:+.2f},{t[2]:+.2f}]"


if __name__ == "__main__":
    mode = sys.argv[1]; lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    if mode == "val":
        variants = GRID[1:]; idxs = list(range(600, 1200))
    elif mode == "val2":
        variants = GRID_I; idxs = list(range(600, 1200))
    elif mode == "val3":
        variants = GRID_R; idxs = list(range(600, 1200))
    else:
        variants = [v for v in GRID + GRID_I + GRID_R if name(v) == sys.argv[2]]; assert len(variants) == 1; idxs = list(range(0, 600)) + list(range(1200, 2400))
    with Pool(22) as pool: R = pool.map(task, [(i, variants) for i in idxs], chunksize=1)
    json.dump(R, open(f"resultados_V17/dinamico_{mode}_V17.json", "w"))
    E = lambda n, m: np.array([r[n][0] for r in R])[m]; idx = np.array([r["idx"] for r in R])
    sets = {"validacion 600-1199": np.ones(len(R), bool)} if mode.startswith("val") else {"prueba 0-599": idx < 600, "confirmacion 1200-2399": idx >= 1200, "prueba + confirmacion (1800)": idx >= 0}
    names = ["V14"] + [name(v) for v in variants]
    for s, m in sets.items():
        P(f"\n{s} (n = {m.sum()}): energia dinamica (pp), IC95 % bootstrap pareado")
        P(f"  {'metodo':24s} | - V7 | - V14 | - MSAPSO | pierde>3pp vs MSAPSO | busquedas/escenario")
        P(f"  {'V7 (b=0)':24s} |   --  |  --  | {f3(boot(E('V7',m)-E('MSAPSO',m)))} | {100*np.mean(E('V7',m)-E('MSAPSO',m)<-3):4.1f} % |")
        for n in names:
            d7, d14, dF = E(n, m) - E("V7", m), E(n, m) - E("V14", m), E(n, m) - E("MSAPSO", m); ns = np.array([r[n][3] for r in R])[m]
            P(f"  {n:24s} | {f3(boot(d7))} | {f3(boot(d14)) if n != 'V14' else '--':>21s} | {f3(boot(dF))} | {100*np.mean(dF<-3):4.1f} % | {ns.mean():.1f}")
    if not mode.startswith("val"):
        n = names[1]; meta = [make_scenario(i)[0] for i in idx]; cells = []
        P(f"\nDESGLOSE (1800 escenarios de prueba + confirmacion): {n} - V7 (pp) [IC95 %]; V = ventaja, D = debilidad, ~ = indeterminada; y {n} - V14")
        for fac in ("panel", "wait", "regimen", "ruido", "fuente"):
            P(f"  por {fac}:")
            for v in sorted({x[fac] for x in meta}, key=str):
                mm = np.array([x[fac] == v for x in meta]); a = boot((E(n, mm) - E("V7", mm))); s = "V" if a[1] > 0 else "D" if a[2] < 0 else "~"; g = boot(E(n, mm) - E("V14", mm))
                P(f"    {str(v):10s} n={mm.sum():4d} | vs V7 {a[0]:+6.2f} [{a[1]:+6.2f},{a[2]:+6.2f}] {s} | vs V14 {g[0]:+6.2f} [{g[1]:+6.2f},{g[2]:+6.2f}]")
                if mm.sum() >= 30: cells.append((fac, str(v), int(mm.sum()), a, s))
        P("  cruce regimen x ruido (vs V7):")
        for rg in sorted({x["regimen"] for x in meta}):
            row = []
            for nsw in (0.0, 1.0, 2.0):
                mm = np.array([x["regimen"] == rg and x["ruido"] == nsw for x in meta])
                if mm.sum() >= 30:
                    a = boot(E(n, mm) - E("V7", mm)); s = "V" if a[1] > 0 else "D" if a[2] < 0 else "~"; row.append(f"{nsw:g} W: {a[0]:+5.2f} [{a[1]:+5.2f},{a[2]:+5.2f}] {s} (n={mm.sum()})"); cells.append((f"{rg}x{nsw:g}W", "", int(mm.sum()), a, s))
                else: row.append(f"{nsw:g} W: n<30")
            P(f"    {rg:9s} | " + " | ".join(row))
        k = {s: sum(1 for c in cells if c[4] == s) for s in "VD~"}
        P(f"\nCeldas (n >= 30): ventaja {k['V']}, debilidad {k['D']}, indeterminadas {k['~']}")
        P("Debilidades: " + ("; ".join(f"{c[0]} {c[1]} {c[3][0]:+.2f} [{c[3][1]:+.2f},{c[3][2]:+.2f}]" for c in cells if c[4] == "D") or "ninguna"))
    open(f"resultados_V17/dinamico_{mode}_V17.txt", "w").write("\n".join(lines))
