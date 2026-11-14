"""
campana_V16.py — DGO en el entorno de la V14. USO: python3 campana_V16.py sel | val | test | conf | S   (ver diseno_V16.md)
 sel  -> cola estatica en validacion (200 curvas) de las 16 configuraciones      -> resultados_V16/dgo_sel_V16.json|txt
 val  -> energia dinamica en 600-1199, aplica el filtro y elige y congela         -> resultados_V16/dgo_val_V16.json|txt
 test | conf -> escenarios 0-599 | 1200-2399 con la configuracion congelada      -> resultados_V16/dgo_<modo>_V16.json|txt
 S    -> 1000 curvas estaticas (7777/7778) con la configuracion congelada        -> resultados_V16/dgo_S_V16.txt
"""
import json, sys, itertools
from multiprocessing import Pool
import numpy as np
from entorno_V16 import *
from msapso_early_V16 import make_msapso_early, Rule, SyntheticPVCurve, random_shading_mix
from pvsim_V16.static_plant_V16 import StaticPlant
from dgo_V16 import Cfg, make_dgo

GRID = [(v, n, G, init, b) for v in ("dgo", "cedgo") for (n, G) in ((5, 8), (8, 5), (7, 10), (10, 7)) for init in ("random", "strat") for b in (0.0, 0.02)]
key = lambda c: f"{c[0]}_n{c[1]}_G{c[2]}_{c[3]}_b{c[4]:g}"
mk = lambda c: make_dgo(Cfg(variant=c[0], n=c[1], G=c[2], init=c[3]))
def boot(d, B=3000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
def final_acc(fn, curves, b):
    fin = []
    for k, c in enumerate(curves):
        rng = np.random.default_rng(7 + 1000 * k); pl = StaticPlant(c, rng=rng); fn(pl, c, rng); Pm = np.array(pl.log_Pmeas); sel = int(np.where(Pm == Pm.max())[0][-1])
        fin.append(100.0 * pl.p_true(pl.log_I[sel] * (1 - b)) / c.P_gmpp)
    return np.array(fin)
def static_set(kind):
    if kind == "val":
        r1, r2 = np.random.default_rng(3030), np.random.default_rng(3031)
        return [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(100)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(100)]
    r1, r2 = np.random.default_rng(7777), np.random.default_rng(7778)
    return [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(500)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(500)]
def sel_task(c):
    return key(c), final_acc(mk(c), static_set("val"), c[4])
def dyn_task(a):
    idx, cfgs = a; meta, curves, bounds, total = make_scenario(idx); out = dict(idx=idx, regimen=meta["regimen"])
    for c in cfgs:
        e, fin, nr, ns = run_ops(mk(c), curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"], backoff=c[4]); out[key(c)] = [e, fin, nr]
    return out
def ref_task(a):
    idx, = a; meta, curves, bounds, total = make_scenario(idx); out = dict(idx=idx)
    for nm, fn, b in (("MSAPSO completo", make_msapso_early(Rule("none")), 0.0), ("V7 (parada)", make_msapso_early(Rule("disp", delta=0.02, t_min=3)), 0.0)):
        e, fin, nr, ns = run_ops(fn, curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"], backoff=b); out[f"{nm}|{b}"] = [e, fin, nr]
    return out

if __name__ == "__main__":
    mode = sys.argv[1]; lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    if mode == "sel":
        val = static_set("val"); base = final_acc(make_msapso_early(Rule("none")), val, 0.0)
        with Pool(8) as pool: R = dict(pool.map(sel_task, GRID))
        res = {}; P("COLA ESTATICA en validacion (200 curvas): perdida de exactitud final vs MSAPSO completo (pp)"); P(f"{'config':26s} | media | p99 | maximo | pasa filtro (p99 <= 3)")
        for c in GRID:
            d = base - R[key(c)]; ok = bool(np.percentile(d, 99) <= 3.0); res[key(c)] = dict(media=float(d.mean()), p99=float(np.percentile(d, 99)), max=float(d.max()), ok=ok)
            P(f"{key(c):26s} | {d.mean():+.3f} | {np.percentile(d,99):5.2f} | {d.max():5.2f} | {'si' if ok else 'NO'}")
        json.dump(res, open("resultados_V16/dgo_sel_V16.json", "w")); open("resultados_V16/dgo_sel_V16.txt", "w").write("\n".join(lines))
    elif mode == "val":
        sel = json.load(open("resultados_V16/dgo_sel_V16.json"))
        with Pool(8) as pool: R = pool.map(dyn_task, [(i, GRID) for i in range(600, 1200)], chunksize=2)
        P("VALIDACION dinamica (600-1199): energia media (%) por configuracion"); P(f"{'config':26s} | energia | exactitud final | pasa filtro estatico")
        m = {key(c): float(np.mean([r[key(c)][0] for r in R])) for c in GRID}
        for c in GRID: P(f"{key(c):26s} | {m[key(c)]:6.2f} | {np.mean([r[key(c)][1] for r in R]):6.2f} | {'si' if sel[key(c)]['ok'] else 'NO'}")
        ok = [k for k in m if sel[k]["ok"]]; pool_ = ok if ok else list(m); best = max(pool_, key=m.get)
        P(f"\nElegida: {best}" + ("" if ok else "  (NINGUNA pasa el filtro estatico: falla el criterio d; se reporta la de mayor energia)"))
        json.dump(dict(elegida=best, filtro_ok=bool(ok), energia=m), open("resultados_V16/dgo_val_V16.json", "w")); open("resultados_V16/dgo_val_V16.txt", "w").write("\n".join(lines))
    elif mode in ("test", "conf"):
        best = json.load(open("resultados_V16/dgo_val_V16.json"))["elegida"]; c = [c for c in GRID if key(c) == best][0]
        rng_idx = range(600) if mode == "test" else range(1200, 2400)
        with Pool(8) as pool: R = pool.map(dyn_task, [(i, [c]) for i in rng_idx], chunksize=2); RF = pool.map(ref_task, [(i,) for i in rng_idx], chunksize=2)
        B = json.load(open(f"resultados_V16/backoff_{'prueba' if mode == 'test' else 'confirmacion'}_V16.json"))
        E = lambda L, k: np.array([r[k][0] for r in L]); dg = E(R, best); full, v7, cand = E(B, "MSAPSO completo|0.0"), E(B, "V7 (parada)|0.0"), E(B, "corto + CEM (<=40)|0.02")
        assert np.allclose(full, E(RF, "MSAPSO completo|0.0")) and np.allclose(v7, E(RF, "V7 (parada)|0.0")), "las referencias no reproducen"
        P(f"{'PRUEBA 0-599' if mode == 'test' else 'CONFIRMACION 1200-2399'} | DGO congelado: {best}")
        f = lambda t: f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"
        db = E(json.load(open(f"resultados_V16/ref_V15/dgbco_{mode}_V16.json")), "n4_T10_msapso_b0.02")
        P(f"  DGO - MSAPSO completo: {f(boot(dg-full))}\n  DGO - V7:             {f(boot(dg-v7))}\n  DGO - candidata V14:  {f(boot(dg-cand))}\n  DGO - DGBCO (V15):      {f(boot(dg-db))}\n  pierde>3pp vs MSAPSO: {100*np.mean(dg-full<-3):.0f} % | peor: {(dg-full).min():+.1f} | exactitud final media {np.mean([r[best][1] for r in R]):.2f}")
        meta = [make_scenario(r["idx"])[0] for r in R]; cells = []
        for fac in ("panel", "wait", "regimen", "ruido"):
            P(f"\n  por {fac} (DGO - V7):")
            for v in sorted({x[fac] for x in meta}, key=str):
                mk = np.array([x[fac] == v for x in meta]); a = boot((dg - v7)[mk]); s = "V" if a[1] > 0 else "D" if a[2] < 0 else "~"; P(f"    {str(v):10s} n={mk.sum():4d} | {f(a)} {s}")
                if mk.sum() >= 30: cells.append((fac, v, a, s))
        P(f"\n  celdas n>=30: ventaja {sum(c[3]=='V' for c in cells)}, debilidad {sum(c[3]=='D' for c in cells)}, indeterminadas {sum(c[3]=='~' for c in cells)}")
        json.dump(R, open(f"resultados_V16/dgo_{mode}_V16.json", "w")); open(f"resultados_V16/dgo_{mode}_V16.txt", "w").write("\n".join(lines))
    elif mode == "S":
        best = json.load(open("resultados_V16/dgo_val_V16.json"))["elegida"]; c = [c for c in GRID if key(c) == best][0]; curves = static_set("S")
        base = final_acc(make_msapso_early(Rule("none")), curves, 0.0); d = base - final_acc(mk(c), curves, c[4])
        P(f"1000 curvas estaticas, DGO {best}: perdida media {d.mean():+.3f} | p95 {np.percentile(d,95):.2f} | p99 {np.percentile(d,99):.2f} | max {d.max():.2f} | >3 pp: {100*np.mean(d>3):.1f} %")
        open("resultados_V16/dgo_S_V16.txt", "w").write("\n".join(lines))
