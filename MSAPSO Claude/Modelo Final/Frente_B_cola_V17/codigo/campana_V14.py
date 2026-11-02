"""
campana_V14.py — Campana completa (2400 escenarios de la campana V7) de la candidata CONGELADA: MSAPSO corto (3 pasadas) + CEM + retroceso 0.02. USO: python3 campana_V14.py
Reutiliza las corridas V13 de 0-599 (prueba) y 1200-2399 (confirmacion) y corre 600-1199 (validacion de b) para completar los 2400; desglosa por panel, t_wait, regimen, ruido y fuente.
-> resultados_V14/campana_V14.json|txt
"""
import json
from multiprocessing import Pool
import numpy as np
from entorno_V14 import make_scenario
from campana_base_V14 import task, NAMES

CAND, B = "corto + CEM (<=40)", 0.02
def boot(d, B_=3000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B_, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

if __name__ == "__main__":
    lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    need = {NAMES[0]: [0.0], NAMES[1]: [0.0], CAND: [0.0, B]}
    with Pool(8) as pool: val = pool.map(task, [(i, need) for i in range(600, 1200)], chunksize=2)
    R = json.load(open("resultados_V14/backoff_prueba_V14.json")) + val + json.load(open("resultados_V14/backoff_confirmacion_V14.json"))
    assert [r["idx"] for r in R] == list(range(2400))
    meta = [make_scenario(r["idx"])[0] for r in R]
    E = lambda n, b: np.array([r[f"{n}|{b}"][0] for r in R]); F = lambda n, b: np.array([r[f"{n}|{b}"][1] for r in R])
    full, v7, c0, cb = E(NAMES[0], 0.0), E(NAMES[1], 0.0), E(CAND, 0.0), E(CAND, B)
    idx = np.arange(2400); sets = {"prueba 0-599": idx < 600, "validacion 600-1199 (b elegido aqui)": (idx >= 600) & (idx < 1200), "confirmacion 1200-2399": idx >= 1200, "TODOS 2400": idx >= 0}
    P("CAMPANA COMPLETA V14: candidata (MSAPSO corto + CEM + retroceso 0.02) vs V7 y MSAPSO completo (energia, pp; IC95 % pareado)")
    P(f"\n{'conjunto':40s} | cand - MSAPSO | cand - V7 | V7 - MSAPSO | efecto retroceso | pierde>3pp (vs MSAPSO) cand / V7 | peor cand | peor V7")
    res = {}
    for k, m in sets.items():
        a, b_, c, d = boot((cb - full)[m]), boot((cb - v7)[m]), boot((v7 - full)[m]), boot((cb - c0)[m])
        f = lambda t: f"{t[0]:+.2f} [{t[1]:+.2f},{t[2]:+.2f}]"
        P(f"{k:40s} | {f(a)} | {f(b_)} | {f(c)} | {f(d)} | {100*np.mean((cb-full)[m]<-3):4.0f} % / {100*np.mean((v7-full)[m]<-3):4.0f} % | {(cb-full)[m].min():+.1f} | {(v7-full)[m].min():+.1f}")
        res[k] = dict(cand_vs_msapso=a, cand_vs_v7=b_)
    P(f"\nExactitud final media (todos): MSAPSO {F(NAMES[0],0.0).mean():.2f} | V7 {F(NAMES[1],0.0).mean():.2f} | candidata b=0 {F(CAND,0.0).mean():.2f} | candidata b=0.02 {F(CAND,B).mean():.2f}")
    P("\nDESGLOSE (los 2400): candidata - V7 en energia (pp) [IC95 %]; n; estado (V = ventaja, D = debilidad, ~ = indeterminada); y candidata - MSAPSO")
    cells = []
    for fac in ("panel", "wait", "regimen", "ruido", "fuente"):
        P(f"\n  por {fac}:")
        for v in sorted({x[fac] for x in meta}, key=str):
            m = np.array([x[fac] == v for x in meta]); a = boot((cb - v7)[m]); s = "V" if a[1] > 0 else "D" if a[2] < 0 else "~"; g = boot((cb - full)[m])
            P(f"    {str(v):10s} n={m.sum():4d} | vs V7 {a[0]:+6.2f} [{a[1]:+6.2f},{a[2]:+6.2f}] {s} | vs MSAPSO {g[0]:+6.2f} [{g[1]:+6.2f},{g[2]:+6.2f}]")
            if m.sum() >= 30: cells.append((fac, v, int(m.sum()), a, s))
    cross = {}
    P("\n  cruce regimen x ruido (candidata - V7):")
    for rg in sorted({x["regimen"] for x in meta}):
        row = []
        for ns in (0.0, 1.0, 2.0):
            m = np.array([x["regimen"] == rg and x["ruido"] == ns for x in meta])
            if m.sum() >= 30:
                a = boot((cb - v7)[m]); s = "V" if a[1] > 0 else "D" if a[2] < 0 else "~"; row.append(f"{ns:g} W: {a[0]:+5.2f} [{a[1]:+5.2f},{a[2]:+5.2f}] {s} (n={m.sum()})"); cells.append((f"{rg}x{ns:g}W", "", int(m.sum()), a, s))
            else: row.append(f"{ns:g} W: n<30")
        P(f"    {rg:9s} | " + " | ".join(row))
    n = {s: sum(1 for c in cells if c[4] == s) for s in "VD~"}; worstD = min([c[3][2] for c in cells if c[4] == "D"], default=None)
    P(f"\nCeldas (n>=30): ventaja {n['V']}, debilidad {n['D']}, indeterminadas {n['~']}. Peor limite superior entre debilidades: {worstD}")
    P("Debilidades: " + "; ".join(f"{c[0]} {c[1]} {c[3][0]:+.2f} [{c[3][1]:+.2f},{c[3][2]:+.2f}]" for c in cells if c[4] == "D"))
    json.dump(dict(res=res, cells=[(c[0], str(c[1]), c[2], c[3], c[4]) for c in cells]), open("resultados_V14/campana_V14.json", "w")); open("resultados_V14/campana_V14.txt", "w").write("\n".join(lines))
