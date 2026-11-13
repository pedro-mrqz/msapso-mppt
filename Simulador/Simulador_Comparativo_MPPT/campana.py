"""
campana.py — Mide los metodos del registro (metodos.py) con el MISMO codigo y los MISMOS escenarios.
USO:
  python campana.py dyn [--solo id1,id2]   energia dinamica en prueba (0-599) y confirmacion (1200-2399)  -> resultados/dyn.json
  python campana.py est [--solo id1,id2]   cola estatica en 1000 curvas (semillas 7777/7778)               -> resultados/est.json
Con --solo solo se (re)miden esos metodos y se MEZCLAN con lo que ya hay en el JSON (el resto no se toca).
Estas cifras alimentan la pestaña "Resultados" del simulador (construir_html.py). Tarda unos minutos en total (usa todos los nucleos).
"""
import os, sys, json, argparse
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
from multiprocessing import Pool
import numpy as np
from entorno import make_scenario, run_ops
from algoritmos.msapso_early import make_msapso_early, Rule, SyntheticPVCurve, random_shading_mix
from pvsim.static_plant import StaticPlant
from metodos import METODOS

R_ = "resultados/"; MET = list(METODOS)
def boot(d, B=3000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def task(a):
    idx, ms = a; meta, curves, bounds, total = make_scenario(idx); out = dict(idx=idx, regimen=meta["regimen"], wait=meta["wait"], ruido=meta["ruido"], panel=meta["panel"])
    for m in ms:
        nm, mk, b = METODOS[m]; e, fin, nr, ns = run_ops(mk(), curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"], backoff=b); out[m] = [e, fin, nr]
    return out

def static_set():
    r1, r2 = np.random.default_rng(7777), np.random.default_rng(7778)
    return [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(500)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(500)]

def final_acc(m):
    nm, mk, b = METODOS[m]; fn = mk(); fin, cnt = [], []
    for k, c in enumerate(static_set()):
        rng = np.random.default_rng(7 + 1000 * k); pl = StaticPlant(c, rng=rng); fn(pl, c, rng); Pm = np.array(pl.log_Pmeas); sel = int(np.where(Pm == Pm.max())[0][-1])
        fin.append(100.0 * pl.p_true(pl.log_I[sel] * (1 - b)) / c.P_gmpp); cnt.append(len(Pm))
    return m, (np.array(fin), np.array(cnt))

def resumen_dyn(A):
    for lab, lo, hi in (("PRUEBA 0-599", 0, 600), ("CONFIRMACION 1200-2399", 1200, 2400)):
        S = [a for a in A if lo <= a["idx"] < hi]; ms = [m for m in MET if all(m in a for a in S)]
        if "msapso" not in ms or not S: continue
        full = np.array([a["msapso"][0] for a in S]); v7 = np.array([a["v7"][0] for a in S]) if "v7" in ms else None; print(lab)
        for m in ms:
            e = np.array([a[m][0] for a in S]); d = boot(e - full); s = f"  {m:8s} vs MSAPSO {d[0]:+.2f} [{d[1]:+.2f},{d[2]:+.2f}]"
            if v7 is not None: dv = boot(e - v7); s += f" | vs V7 {dv[0]:+.2f} [{dv[1]:+.2f},{dv[2]:+.2f}]"
            print(s + f" | pierde>3pp {100*np.mean(e-full<-3):.0f} %")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("modo", choices=["dyn", "est"]); ap.add_argument("--solo", default=""); a = ap.parse_args()
    solo = [m for m in a.solo.split(",") if m] or MET
    for m in solo: assert m in METODOS, f"metodo desconocido: {m} (ver metodos.py)"
    nproc = os.cpu_count() or 4
    if a.modo == "dyn":
        idxs = list(range(600)) + list(range(1200, 2400))
        with Pool(nproc) as pool: new = pool.map(task, [(i, solo) for i in idxs], chunksize=4)
        old = {r["idx"]: r for r in json.load(open(R_ + "dyn.json"))} if (a.solo and os.path.exists(R_ + "dyn.json")) else {}
        A = []
        for r in new: o = old.get(r["idx"], {}); o.update(r); A.append(o)
        json.dump(A, open(R_ + "dyn.json", "w")); resumen_dyn(A)
    else:
        with Pool(nproc) as pool: R = dict(pool.map(final_acc, solo + ([] if "msapso" in solo else ["msapso"])))
        base = R["msapso"][0]; old = json.load(open(R_ + "est.json")) if (a.solo and os.path.exists(R_ + "est.json")) else {}
        for m in solo:
            f, n = R[m]; d = base - f
            old[m] = dict(med=float(n.mean()), media=float(d.mean()), p95=float(np.percentile(d, 95)), p99=float(np.percentile(d, 99)), max=float(d.max()), gt3=float(100 * np.mean(d > 3)))
            print(f"{m:8s} | med {n.mean():6.1f} | perdida media {d.mean():+.3f} | p95 {np.percentile(d,95):6.2f} | p99 {np.percentile(d,99):6.2f} | max {d.max():6.2f} | >3 pp {100*np.mean(d>3):5.1f} %")
        json.dump(old, open(R_ + "est.json", "w"))
