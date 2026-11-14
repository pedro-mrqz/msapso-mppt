"""
evaluar_V11.py — PRUEBA fresca (estatico) y OPERACION dinamica (600 escenarios de la campana V7) de la configuracion CONGELADA en seleccion_V11.py.
Metodos: MSAPSO completo | V7 | MLP + CEM | sin modelo (CEM desde el mejor punto del barrido) | solo MLP. IC95 % bootstrap pareado.
USO: python3 evaluar_V11.py estatico | python3 evaluar_V11.py dinamico  -> resultados_V11/evaluar_V11_<modo>.txt|json
"""
import json, pickle, sys
from multiprocessing import Pool
from mlp_cem_V11 import *
from msapso_early_V11 import *

CH = json.load(open("resultados_V11/seleccion_V11.json")); MODEL = pickle.load(open("resultados_V11/mlp_elegido_V11.pkl", "rb"))
def methods():
    return {"MSAPSO completo (paper)": make_msapso_early(Rule("none")), "V7 (parada por dispersion)": make_msapso_early(Rule("disp", delta=0.02, t_min=3)),
            "MLP + CEM": make_mlp_cem(MODEL, Cfg(**CH["mlp_cem"]["cfg"])), "sin modelo (CEM desde el mejor punto)": make_mlp_cem(None, Cfg(**CH["sin_modelo"]["cfg"])),
            "solo MLP (8 med.)": make_mlp_cem(MODEL, Cfg(modo="solo_mlp"))}
def curves_big():
    def orig(seed, n=500):
        r = np.random.default_rng(seed); return [SyntheticPVCurve(random_shading_mix(r)) for _ in range(n)]
    def att(seed, n=500):
        r = np.random.default_rng(seed); return [SyntheticPVCurve(random_shading_mix(r) * r.uniform(0.25, 1.0)) for _ in range(n)]
    return orig(7777) + att(7778)
def job(a):
    name, which, noise = a; S = make_sets(); cs = {"prueba": S["test_orig"] + S["test_att"], "reales": S["real"], "grande": curves_big()}[which]
    f, e, n = eval_curves(methods()[name], cs, noise_w=noise, reps=(10 if which == "reales" else 1)); return a, f, e, n
def boot(d, B=4000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
def one_dyn(idx):
    from entorno_V11 import make_scenario, run_ops
    meta, curves, bounds, total = make_scenario(idx); M = methods()
    for name in ("MLP + CEM", "sin modelo (CEM desde el mejor punto)"):
        e, fin, nr, ns = run_ops(M[name], curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"]); meta[name] = dict(e=e, fin=fin, nr=nr, ns=ns)
    return meta

if __name__ == "__main__":
    lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    if sys.argv[1] == "estatico":
        res = {}; names = list(methods())
        jobs = [(n, w, z) for n in names for w, zs in (("prueba", (0.0, 1.0, 2.0)), ("reales", (0.0,)), ("grande", (0.0,))) for z in zs]
        with Pool(8) as pool:
            for a, f, e, n in pool.imap_unordered(job, jobs): res[a] = (f, e, n)
        for which, noise in [("prueba", 0.0), ("prueba", 1.0), ("prueba", 2.0), ("reales", 0.0), ("grande", 0.0)]:
            base = res[(names[0], which, noise)]; v7 = res[(names[1], which, noise)]; sm = res[(names[3], which, noise)]
            P(f"\n== {which} | ruido {noise:g} W | {len(base[0])} curvas ==")
            P(f"{'metodo':40s} | {'med.':>5s} | {'final %':>8s} | {'vs MSAPSO (pp) [IC95 %]':>26s} | {'vs V7':>7s} | {'vs sin modelo':>14s} | {'<98 %':>6s} | {'<95 %':>6s} | peor")
            for name in names:
                f, e, n = res[(name, which, noise)]; a, lo, hi = boot(f - base[0])
                P(f"{name:40s} | {n.mean():5.0f} | {f.mean():8.3f} | {a:+8.3f} [{lo:+.3f}, {hi:+.3f}] | {(f-v7[0]).mean():+7.3f} | {(f-sm[0]).mean():+14.3f} | {100*np.mean(f<98):5.1f}% | {100*np.mean(f<95):5.1f}% | {f.min():.1f}")
        json.dump({f"{k[0]}|{k[1]}|{k[2]}": dict(final=v[0].tolist(), mediciones=v[2].tolist()) for k, v in res.items()}, open("resultados_V11/evaluar_V11_estatico.json", "w"))
        open("resultados_V11/evaluar_V11_estatico.txt", "w").write("\n".join(lines))
    else:
        with Pool(8) as pool: R = pool.map(one_dyn, range(600), chunksize=4)
        ref = {json.loads(l)["idx"]: json.loads(l) for l in open("resultados_V11/campana_V7_referencia.jsonl")}
        P("OPERACION DINAMICA: 600 escenarios (primeros de la campana V7). Diferencia de energia en pp (pareada).")
        for name in ("MLP + CEM", "sin modelo (CEM desde el mejor punto)"):
            for vs, vl in (("full", "MSAPSO completo"), ("principal", "V7 principal")):
                d = np.array([r[name]["e"] - ref[r["idx"]][vs]["e"] for r in R]); a, lo, hi = boot(d)
                P(f"\n== {name} - {vl} == media {a:+.2f} [{lo:+.2f}, {hi:+.2f}] | mediana {np.median(d):+.2f} | p1/p5 {np.percentile(d,1):+.1f}/{np.percentile(d,5):+.1f} | peor {d.min():+.1f} | pierde(<-3) {100*np.mean(d<-3):.0f} %")
                if vs == "full":
                    for reg in ("unico", "estable", "moderado", "alto", "muy alto", "flicker"):
                        dd = np.array([r[name]["e"] - ref[r["idx"]]["full"]["e"] for r in R if r["regimen"] == reg]); x = boot(dd); P(f"   {reg:10s} | {len(dd):3d} | {x[0]:+.2f} [{x[1]:+.2f}, {x[2]:+.2f}]")
        d = np.array([r["MLP + CEM"]["e"] - r["sin modelo (CEM desde el mejor punto)"]["e"] for r in R]); a, lo, hi = boot(d); P(f"\nAporte del MLP (MLP+CEM - sin modelo): {a:+.2f} [{lo:+.2f}, {hi:+.2f}] pp")
        P("Exactitud al final: MSAPSO %.2f | V7 %.2f | MLP+CEM %.2f | sin modelo %.2f" % (np.mean([ref[r['idx']]['full']['fin'] for r in R]), np.mean([ref[r['idx']]['principal']['fin'] for r in R]), np.mean([r['MLP + CEM']['fin'] for r in R]), np.mean([r['sin modelo (CEM desde el mejor punto)']['fin'] for r in R])))
        P("Reinicios: MSAPSO %.1f | V7 %.1f | MLP+CEM %.1f | sin modelo %.1f" % (np.mean([ref[r['idx']]['full']['nr'] for r in R]), np.mean([ref[r['idx']]['principal']['nr'] for r in R]), np.mean([r['MLP + CEM']['nr'] for r in R]), np.mean([r['sin modelo (CEM desde el mejor punto)']['nr'] for r in R])))
        open("resultados_V11/evaluar_V11_dinamico.txt", "w").write("\n".join(lines)); open("resultados_V11/evaluar_V11_dinamico.jsonl", "w").write("\n".join(json.dumps(r) for r in R))
