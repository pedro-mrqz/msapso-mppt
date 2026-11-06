"""
dinamico_V18.py — Energia DINAMICA de las variantes V18, mismo entorno y escenarios que la campana V7/V14/V17 (run_ops, semillas 100000 + idx).
USO: python3 dinamico_V18.py val|val2            -> escenarios 600-1199 (VALIDACION): val = 24 variantes V18, val2 = 16 variantes V18.1; + referencias
     python3 dinamico_V18.py test "<variante>"   -> 0-599 (PRUEBA) y 1200-2399 (CONFIRMACION): variante congelada, su control V11 y las referencias, con desglose
Retroceso: 0 para MSAPSO y V7; 0.02 para el resto (como en la V14 y la V17).
-> resultados_V18/dinamico_<modo>_V18.txt|json
"""
import os
for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[v] = "1"
import json, sys
from multiprocessing import Pool
import numpy as np
from entorno_V14 import make_scenario, run_ops
from metodos_V18 import metodo, variantes, parse, retroceso
from neuroevolucion_V18 import p_name

REFS = ["MSAPSO", "V7", "V14", "V17", "V11"]


def task(a):
    idx, names = a; meta, curves, bounds, total = make_scenario(idx); out = dict(idx=idx)
    for n in names:
        e, fin, nr, ns = run_ops(metodo(n), curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"], backoff=retroceso(n)); out[n] = [e, fin, nr, ns]
    return out


def boot(d, B_=3000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B_, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
f3 = lambda t: f"{t[0]:+.2f} [{t[1]:+.2f},{t[2]:+.2f}]"


if __name__ == "__main__":
    mode = sys.argv[1]; lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    if mode in ("val", "val2"):
        names = REFS + variantes("V18" if mode == "val" else "V18.1"); idxs = list(range(600, 1200))
    else:
        sel = sys.argv[2]; _, pc = parse(sel); ctrl = f"V11 {p_name(pc)}"
        names = REFS + ([ctrl] if ctrl != "V11 s0=0.1" else []) + [sel]; idxs = list(range(0, 600)) + list(range(1200, 2400))
    with Pool(22) as pool: R = pool.map(task, [(i, names) for i in idxs], chunksize=1)
    json.dump(R, open(f"resultados_V18/dinamico_{mode}_V18.json", "w"))
    E = lambda n, m: np.array([r[n][0] for r in R])[m]; idx = np.array([r["idx"] for r in R])
    sets = {"validacion 600-1199": np.ones(len(R), bool)} if mode.startswith("val") else {"prueba 0-599": idx < 600, "confirmacion 1200-2399": idx >= 1200, "prueba + confirmacion (1800)": idx >= 0}
    for s, m in sets.items():
        P(f"\n{s} (n = {m.sum()}): energia dinamica (pp), IC95 % bootstrap pareado")
        P(f"  {'metodo':36s} | - V7 | - V17 | - V11 | - MSAPSO | pierde>3pp vs MSAPSO | busquedas/escenario")
        for n in names[1:]:
            d7, d17, d11, dF = (E(n, m) - E(r, m) for r in ("V7", "V17", "V11", "MSAPSO")); ns = np.array([r[n][3] for r in R])[m]
            P(f"  {n:36s} | {f3(boot(d7)) if n != 'V7' else '--'} | {f3(boot(d17)) if n != 'V17' else '--'} | {f3(boot(d11)) if n != 'V11' else '--'} | {f3(boot(dF))} | {100*np.mean(dF<-3):4.1f} % | {ns.mean():.1f}")
    if not mode.startswith("val"):
        n = names[-1]; meta = [make_scenario(i)[0] for i in idx]; cells = []
        P(f"\nDESGLOSE (1800 escenarios de prueba + confirmacion): {n} - V7 (pp) [IC95 %]; V = ventaja, D = debilidad, ~ = indeterminada; y {n} - V17")
        for fac in ("panel", "wait", "regimen", "ruido", "fuente"):
            P(f"  por {fac}:")
            for v in sorted({x[fac] for x in meta}, key=str):
                mm = np.array([x[fac] == v for x in meta]); a = boot(E(n, mm) - E("V7", mm)); s = "V" if a[1] > 0 else "D" if a[2] < 0 else "~"; g = boot(E(n, mm) - E("V17", mm))
                P(f"    {str(v):10s} n={mm.sum():4d} | vs V7 {a[0]:+6.2f} [{a[1]:+6.2f},{a[2]:+6.2f}] {s} | vs V17 {g[0]:+6.2f} [{g[1]:+6.2f},{g[2]:+6.2f}]")
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
    open(f"resultados_V18/dinamico_{mode}_V18.txt", "w").write("\n".join(lines))
