"""
estatico_V18.py — Cola ESTATICA de las variantes V18 y de las referencias. Misma medida que estatico_V17.py: perdida de exactitud final contra el MSAPSO completo (pp).
USO: python3 estatico_V18.py val|val2            -> VALIDACION (elegir variante): 1000 curvas 8080/8081 + 100 curvas por panel (6161); val = 24 variantes V18, val2 = 16 variantes V18.1
     python3 estatico_V18.py test "<variante>"   -> PRUEBA: S (7777/7778), P (5151), frescos (9393/9394; 5252) y los 4 casos reales. RUIDO=1|2 para ruido.
-> resultados_V18/estatico_<modo>_V18.txt|json
"""
import os
for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[v] = "1"
import json, sys
from multiprocessing import Pool
import numpy as np
from estatico_V17 import build, final_acc
from baselines_nivel1_V14 import scenarios
from metodos_V18 import metodo, variantes, parse
from neuroevolucion_V18 import p_name

REFS = ["V7", "V14", "V17", "V11"]


def job(args):
    key, n, b, params, curves, noise = args
    from entorno_V14 import panel_ctx
    fn = metodo(n)
    if params:
        with panel_ctx(*params): f, m = final_acc(fn, curves, b, noise)
    else: f, m = final_acc(fn, curves, b, noise)
    return key, f, m


def run(sets, names, noise=0.0):
    jobs = []
    for s, (params, curves) in sets.items():
        jobs.append(((s, "MSAPSO", 0.0), "MSAPSO", 0.0, params, curves, noise)); jobs.append(((s, "V7", 0.0), "V7", 0.0, params, curves, noise))
        for n in [x for x in names if x != "V7"]:
            for b in ((0.02,) if n in REFS else (0.0, 0.02)): jobs.append(((s, n, b), n, b, params, curves, noise))
    with Pool(22) as p: R = {k: (f, m) for k, f, m in p.map(job, jobs, chunksize=1)}
    return R


def table(R, sets, names, P):
    out = {}
    for s in sets:
        base = R[(s, "MSAPSO", 0.0)][0]
        P(f"\n{s}: perdida vs MSAPSO completo (pp) | med. | media | p95 | p99 | max | % > 3 pp")
        rows = [("V7", 0.0)] + [(n, b) for n in names if n != "V7" for b in ((0.02,) if n in REFS else (0.0, 0.02))]
        for n, b in rows:
            f, m = R[(s, n, b)]; d = base - f; lbl = f"{n} b={b:g}"
            P(f"  {lbl:40s} | {m.mean():5.1f} | {d.mean():+.3f} | {np.percentile(d,95):5.2f} | {np.percentile(d,99):5.2f} | {d.max():5.2f} | {100*np.mean(d>3):4.1f}")
            out[f"{s}|{lbl}"] = dict(med=float(m.mean()), media=float(d.mean()), p95=float(np.percentile(d, 95)), p99=float(np.percentile(d, 99)), max=float(d.max()), gt3=float(np.mean(d > 3)), perdidas=d.round(4).tolist())
    return out


if __name__ == "__main__":
    mode = sys.argv[1]; lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    if mode in ("val", "val2"):
        sets = build((8080, 8081), 6161); names = REFS + variantes("V18" if mode == "val" else "V18.1"); noise = 0.0
    else:
        sel = sys.argv[2]; clave, pc = parse(sel); noise = float(os.environ.get("RUIDO", 0.0))
        names = REFS + [f"V11 {p_name(pc)}", sel] if f"V11 {p_name(pc)}" != "V11 s0=0.1" else REFS + [sel]
        real, _ = scenarios()
        sets = build((7777, 7778), 5151) | build((9393, 9394), 5252) | {"reales 4 (casos del paper)": (None, real)}
        mode = mode + (f"_ruido{noise:g}" if noise else "")
    P(f"ESTATICO V18 ({mode}); ruido {noise:g} W; perdida = exactitud final MSAPSO completo - metodo; V7 sin retroceso, el resto b = 0.02 (V18 tambien b = 0)")
    R = run(sets, names, noise); out = table(R, sets, names, P)
    open(f"resultados_V18/estatico_{mode}_V18.txt", "w").write("\n".join(lines)); json.dump(out, open(f"resultados_V18/estatico_{mode}_V18.json", "w"))
