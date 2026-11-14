"""
seleccion_V11.py — Elige en VALIDACION (criterios de diseno_V11.md) la configuracion de MLP+CEM y del control «sin modelo». USO: python3 seleccion_V11.py -> resultados_V11/seleccion_V11.json|txt
"""
import json, itertools, pickle, time
from mlp_cem_V11 import *
from msapso_early_V11 import *

if __name__ == "__main__":
    lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    val = make_sets()["val"]; b = eval_curves(make_msapso_early(Rule("none")), val); v7 = eval_curves(make_msapso_early(Rule("disp", delta=0.02, t_min=3)), val)
    P(f"MSAPSO completo: {b[2].mean():.0f} med | final {b[0].mean():.3f} || V7: {v7[2].mean():.0f} med | final {v7[0].mean():.3f}")
    cfgs = [Cfg(modo="mlp", n=n, k=k, alpha=a, sigma0=s0, delta=d) for s0, n, k, a, d in itertools.product((0.03, 0.06, 0.1, 0.15), (3, 5, 7), (1, 2), (0.7, 1.0), (0.005, 0.01, 0.02))]
    models, rows = {}, []
    for nt, hid in itertools.product((8000, 30000), ((64, 64), (128, 128))):
        t = time.time(); m = train_mlp(nt, 1111, hid); models[(nt, hid)] = m
        for c in cfgs:
            f, e, n = eval_curves(make_mlp_cem(m, c), val); rows.append(dict(modelo=[nt, list(hid)], cfg=c.__dict__, mediciones=float(n.mean()), final=float(f.mean()), p98=float(100 * np.mean(f < 98))))
        P(f"MLP datos={nt} capas={hid}: {len(cfgs)} configuraciones evaluadas ({time.time()-t:.0f} s)")
    ctrl = []
    for c in cfgs:
        cc = Cfg(**{**c.__dict__, "modo": "sin_modelo"}); f, e, n = eval_curves(make_mlp_cem(None, cc), val); ctrl.append(dict(cfg=cc.__dict__, mediciones=float(n.mean()), final=float(f.mean()), p98=float(100 * np.mean(f < 98))))
    fs = [make_mlp_cem(m, Cfg(modo="solo_mlp")) for m in models.values()]
    solo = [(k, eval_curves(make_mlp_cem(m, Cfg(modo="solo_mlp")), val)) for k, m in models.items()]
    for k, (f, e, n) in solo: P(f"solo MLP {k}: {n.mean():.0f} med | final {f.mean():.3f} | <98 %: {100*np.mean(f<98):.1f} %")
    def pick(R):
        ok = [r for r in R if b[0].mean() - r["final"] <= 0.10]
        if ok: return "principal (<=0.10 pp)", min(ok, key=lambda r: r["mediciones"])
        return "mayor exactitud con <=70 med.", max([r for r in R if r["mediciones"] <= 70], key=lambda r: r["final"])
    out = {"msapso": dict(med=float(b[2].mean()), final=float(b[0].mean())), "v7": dict(med=float(v7[2].mean()), final=float(v7[0].mean()))}
    for nombre, R in (("mlp_cem", rows), ("sin_modelo", ctrl)):
        crit, r = pick(R); out[nombre] = r; out[nombre]["criterio"] = crit
        P(f"\n{nombre}: criterio «{crit}» -> {r.get('modelo','-')} {r['cfg']} | {r['mediciones']:.1f} med | final {r['final']:.3f} | <98 %: {r['p98']:.1f} %")
    top = sorted(rows, key=lambda r: -r["final"])[:5]; P("\n5 mejores MLP+CEM por exactitud (cualquier presupuesto):")
    for r in top: P(f"  {r['modelo']} s0={r['cfg']['sigma0']} n={r['cfg']['n']} k={r['cfg']['k']} a={r['cfg']['alpha']} d={r['cfg']['delta']} | {r['mediciones']:.1f} med | {r['final']:.3f} | <98 %: {r['p98']:.1f} %")
    best = out["mlp_cem"]; key = (best["modelo"][0], tuple(best["modelo"][1])); pickle.dump(models[key], open("resultados_V11/mlp_elegido_V11.pkl", "wb"))
    json.dump(out, open("resultados_V11/seleccion_V11.json", "w"), indent=1); open("resultados_V11/seleccion_V11.txt", "w").write("\n".join(lines))
