"""
campana_V17.py — DecentCEM en el entorno de la V14. USO: python3 campana_V17.py sel | val | test | conf | S   (ver diseno_V17.md)
 sel  -> cola estatica en validacion (200 curvas) de las 68 configuraciones + regla de parada del frente  -> resultados_V17/dc_sel_V17.json|txt
 val  -> energia dinamica en 600-1199 del pool permitido, elige y congela                              -> resultados_V17/dc_val_V17.json|txt
 test | conf -> escenarios 0-599 | 1200-2399 con la configuracion congelada                           -> resultados_V17/dc_<modo>_V17.json|txt
 S    -> 1000 curvas estaticas (7777/7778) con la configuracion congelada                             -> resultados_V17/dc_S_V17.txt
"""
import json, sys
from multiprocessing import Pool
import numpy as np
from entorno_V17 import *
from msapso_early_V17 import make_msapso_early, Rule, SyntheticPVCurve, random_shading_mix
from pvsim_V17.static_plant_V17 import StaticPlant
from decentcem_V17 import Cfg, make_decent

GRID = []   # (modo, N, sigma0, tau, n, T, b)
for modo in ("fixed", "floor"):
    for N in (7, 10):
        for s0 in (0.03, 0.05):
            for tau in (0.15, 0.25):
                for (n, T) in ((3, 3), (4, 4)):
                    for b in (0.0, 0.02): GRID.append((modo, N, s0, tau, n, T, b))
for T in (4, 6):
    for b in (0.0, 0.02): GRID.append(("paper", 0, 0.15, 0.0, 4, T, b))
key = lambda c: f"{c[0]}_N{c[1]}_s{c[2]:g}_tau{c[3]:g}_n{c[4]}_T{c[5]}_b{c[6]:g}"
def mk(c):
    if c[0] == "paper": return make_decent(Cfg(kind="paper", sigma_mode="floor", sigma0=c[2], n=c[4], T=c[5]))
    return make_decent(Cfg(kind="sweep", sigma_mode=c[0], N=c[1], sigma0=c[2], tau=c[3], n=c[4], T=c[5]))
def boot(d, B=3000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
def final_acc(fn, curves, b):
    fin, cnt = [], []
    for k, c in enumerate(curves):
        rng = np.random.default_rng(7 + 1000 * k); pl = StaticPlant(c, rng=rng); fn(pl, c, rng); Pm = np.array(pl.log_Pmeas); sel = int(np.where(Pm == Pm.max())[0][-1])
        fin.append(100.0 * pl.p_true(pl.log_I[sel] * (1 - b)) / c.P_gmpp); cnt.append(len(Pm))
    return np.array(fin), np.array(cnt)
def static_set(kind):
    if kind == "val":
        r1, r2 = np.random.default_rng(3030), np.random.default_rng(3031)
        return [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(100)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(100)]
    r1, r2 = np.random.default_rng(7777), np.random.default_rng(7778)
    return [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(500)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(500)]
def sel_task(c):
    f, n = final_acc(mk(c), static_set("val"), c[6]); return key(c), (f, n)
def dyn_task(a):
    idx, cfgs = a; meta, curves, bounds, total = make_scenario(idx); out = dict(idx=idx, regimen=meta["regimen"])
    for c in cfgs:
        e, fin, nr, ns = run_ops(mk(c), curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"], backoff=c[6]); out[key(c)] = [e, fin, nr]
    return out
def ref_task(idx):
    meta, curves, bounds, total = make_scenario(idx); e, fin, nr, ns = run_ops(make_msapso_early(Rule("disp", delta=0.02, t_min=3)), curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"], backoff=0.0)
    return e
R_ = "resultados_V17/"

if __name__ == "__main__":
    mode = sys.argv[1]; lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    if mode == "sel":
        val = static_set("val"); base, _ = final_acc(make_msapso_early(Rule("none")), val, 0.0)
        with Pool(8) as pool: R = dict(pool.map(sel_task, GRID))
        res = {}; P("COLA ESTATICA en validacion (200 curvas): perdida de exactitud final vs MSAPSO completo (pp)"); P(f"{'config':44s} | mediciones | media | p99 | maximo | p99<=3 | p99<=5")
        for c in GRID:
            f, n = R[key(c)]; d = base - f; p99 = float(np.percentile(d, 99))
            res[key(c)] = dict(media=float(d.mean()), p99=p99, max=float(d.max()), med=float(n.mean()), ok3=bool(p99 <= 3.0), ok5=bool(p99 <= 5.0))
            P(f"{key(c):44s} | {n.mean():6.1f} | {d.mean():+.3f} | {p99:5.2f} | {d.max():5.2f} | {'si' if p99 <= 3 else 'NO'} | {'si' if p99 <= 5 else 'NO'}")
        cont = any(v["ok5"] for v in res.values())
        P(f"\nRegla de parada del frente: {'se continua (hay configuraciones con p99 <= 5 pp)' if cont else 'SE DETIENE: ninguna configuracion tiene p99 <= 5 pp; no se corren prueba ni confirmacion'}")
        json.dump(dict(cfg=res, continuar=bool(cont)), open(R_ + "dc_sel_V17.json", "w")); open(R_ + "dc_sel_V17.txt", "w").write("\n".join(lines))
    elif mode == "val":
        sel = json.load(open(R_ + "dc_sel_V17.json")); assert sel["continuar"], "la regla de parada del frente se activo en sel"
        s = sel["cfg"]; ok3 = [k for k, v in s.items() if v["ok3"]]; pool_k = ok3 if ok3 else [k for k, v in s.items() if v["ok5"]]
        cf = [c for c in GRID if key(c) in pool_k]
        with Pool(8) as pool: R = pool.map(dyn_task, [(i, cf) for i in range(600, 1200)], chunksize=2)
        P(f"VALIDACION dinamica (600-1199): energia media (%) del pool ({'p99 <= 3' if ok3 else 'p99 <= 5, falla el criterio d'}; {len(cf)} configuraciones)"); P(f"{'config':44s} | energia | exactitud final | p99 estatico")
        m = {key(c): float(np.mean([r[key(c)][0] for r in R])) for c in cf}
        for k in sorted(m, key=m.get, reverse=True): P(f"{k:44s} | {m[k]:6.2f} | {np.mean([r[k][1] for r in R]):6.2f} | {s[k]['p99']:5.2f}")
        best = max(m, key=m.get); P(f"\nElegida: {best}" + ("" if ok3 else "  (ninguna con p99 <= 3: falla el criterio d)"))
        json.dump(dict(elegida=best, pool_p99_3=bool(ok3), energia=m), open(R_ + "dc_val_V17.json", "w")); open(R_ + "dc_val_V17.txt", "w").write("\n".join(lines))
    elif mode in ("test", "conf"):
        best = json.load(open(R_ + "dc_val_V17.json"))["elegida"]; c = [c for c in GRID if key(c) == best][0]
        rng_idx = range(600) if mode == "test" else range(1200, 2400)
        with Pool(8) as pool: R = pool.map(dyn_task, [(i, [c]) for i in rng_idx], chunksize=2); chk = pool.map(ref_task, list(rng_idx)[:16])
        B = json.load(open(R_ + f"ref/backoff_{'prueba' if mode == 'test' else 'confirmacion'}_V16.json"))
        E = lambda L, k: np.array([r[k][0] for r in L]); dg = E(R, best); full, v7, v7b, cand = E(B, "MSAPSO completo|0.0"), E(B, "V7 (parada)|0.0"), E(B, "V7 (parada)|0.02"), E(B, "corto + CEM (<=40)|0.02")
        assert np.allclose(v7[:16], chk), "las referencias no reproducen"
        P(f"{'PRUEBA 0-599' if mode == 'test' else 'CONFIRMACION 1200-2399'} | DecentCEM congelado: {best}")
        f = lambda t: f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"
        P(f"  V17 - MSAPSO completo:       {f(boot(dg-full))}\n  V17 - V7:                    {f(boot(dg-v7))}\n  V17 - V7 + retroceso (plan B): {f(boot(dg-v7b))}\n  V17 - candidata V14:         {f(boot(dg-cand))}\n  pierde>3pp vs MSAPSO: {100*np.mean(dg-full<-3):.0f} % | peor: {(dg-full).min():+.1f} | exactitud final media {np.mean([r[best][1] for r in R]):.2f}")
        meta = [make_scenario(r["idx"])[0] for r in R]; cells = []
        for fac in ("panel", "wait", "regimen", "ruido"):
            P(f"\n  por {fac} (V17 - V7):")
            for v in sorted({x[fac] for x in meta}, key=str):
                mkk = np.array([x[fac] == v for x in meta]); a = boot((dg - v7)[mkk]); sg = "V" if a[1] > 0 else "D" if a[2] < 0 else "~"; P(f"    {str(v):10s} n={mkk.sum():4d} | {f(a)} {sg}")
                if mkk.sum() >= 30: cells.append((fac, v, a, sg))
        P(f"\n  celdas n>=30: ventaja {sum(c[3]=='V' for c in cells)}, debilidad {sum(c[3]=='D' for c in cells)}, indeterminadas {sum(c[3]=='~' for c in cells)}")
        json.dump(R, open(R_ + f"dc_{mode}_V17.json", "w")); open(R_ + f"dc_{mode}_V17.txt", "w").write("\n".join(lines))
    elif mode == "S":
        best = json.load(open(R_ + "dc_val_V17.json"))["elegida"]; c = [c for c in GRID if key(c) == best][0]; curves = static_set("S")
        base, _ = final_acc(make_msapso_early(Rule("none")), curves, 0.0); f_, n_ = final_acc(mk(c), curves, c[6]); d = base - f_
        P(f"1000 curvas estaticas, V17 {best}: mediciones {n_.mean():.1f} | perdida media {d.mean():+.3f} | p95 {np.percentile(d,95):.2f} | p99 {np.percentile(d,99):.2f} | max {d.max():.2f} | >3 pp: {100*np.mean(d>3):.1f} %")
        open(R_ + "dc_S_V17.txt", "w").write("\n".join(lines))
