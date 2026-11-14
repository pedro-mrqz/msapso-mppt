"""
seleccion_regla_V7.py — Elige la regla de parada anticipada en VALIDACION (200 curvas, semillas 3030/3031, sin ruido).
CRITERIO FIJADO ANTES DE VER LA PRUEBA: entre las reglas cuya eficiencia final media NO baja mas de 0.10 pp de la del MSAPSO completo (25 pasadas), la que usa MENOS mediciones;
y, como variante mas prudente, la que no baja mas de 0.02 pp. La eleccion se congela y se evalua en la PRUEBA (evaluar_parada_V7.py). Tambien se listan los truncados fijos.
USO: python3 seleccion_regla_V7.py -> resultados_V7/seleccion_regla_V7.json|txt
"""
import json
from msapso_early_V7 import *

sets = make_sets(); lines = []
def P(s=""): print(s, flush=True); lines.append(s)
val = sets["val"]
base = eval_curves(make_msapso_early(Rule("none")), val)
P(f"MSAPSO completo (25 pasadas): {base[2].mean():.0f} mediciones | final {base[0].mean():.3f} % | energia {base[1].mean():.2f} %")
cands = []
for d in (0.005, 0.01, 0.02, 0.03, 0.05): cands.append((f"disp d={d}", Rule("disp", delta=d)))
for k in (2, 3, 4):
    for e in (0.05, 0.1, 0.25, 0.5): cands.append((f"noimp k={k} eps={e}W", Rule("noimp", k=k, eps=e)))
for k, e, d in ((3, 0.1, 0.02), (3, 0.25, 0.03), (2, 0.1, 0.01), (4, 0.05, 0.02)):
    cands.append((f"OR  k={k} eps={e}W d={d}", Rule("or", k=k, eps=e, delta=d))); cands.append((f"AND k={k} eps={e}W d={d}", Rule("and", k=k, eps=e, delta=d)))
P(f"\n{'regla':28s} | {'med.':>5s} | {'final':>7s} | {'perdida vs completo':>20s} | {'energia':>7s}")
rows = []
for name, rule in cands:
    f, e, n = eval_curves(make_msapso_early(rule), val)
    rows.append((name, rule, n.mean(), f.mean(), base[0].mean() - f.mean(), e.mean())); P(f"{name:28s} | {n.mean():5.0f} | {f.mean():7.3f} | {base[0].mean()-f.mean():+20.3f} | {e.mean():7.2f}")
P("\nTruncados fijos (referencias sin regla):")
trunc = []
for T in (6, 8, 10, 12, 14):
    f1 = eval_curves(make_msapso_early(Rule("none"), compress_T=None), val)  # placeholder para estructura
for T in (6, 8, 10, 12, 14):
    class Cut:
        pass
    def mk(T):
        def fn(plant, curve, rng):
            sw = Swarm(first_pass="ascending"); sw.restart(curve.Isc, first=True)
            for _ in range(T): sw.sweep(plant, 1.0); sw.update(paper_beta(sw.t))        # beta del paper SIN comprimir (t_max = 25), solo se corta
        return fn
    f, e, n = eval_curves(mk(T), val); trunc.append((f"truncado T={T} (beta del paper)", n.mean(), f.mean(), e.mean()))
    f2, e2, n2 = eval_curves(make_msapso_early(Rule("none"), compress_T=T), val); trunc.append((f"comprimido T={T} (beta a T pasadas)", n2.mean(), f2.mean(), e2.mean()))
for name, n, f, e in trunc: P(f"{name:38s} | {n:5.0f} | {f:7.3f} | {base[0].mean()-f:+7.3f} | {e:7.2f}")
chosen = {}
for tag, tol in (("principal (<= 0.10 pp)", 0.10), ("prudente (<= 0.02 pp)", 0.02)):
    ok = [r for r in rows if r[4] <= tol]; best = min(ok, key=lambda r: r[2]) if ok else None
    if best: chosen[tag] = dict(nombre=best[0], kind=best[1].kind, k=best[1].k, eps=best[1].eps, delta=best[1].delta, t_min=best[1].t_min, mediciones=best[2], final=best[3], perdida=best[4], energia=best[5]); P(f"\nELEGIDA {tag}: {best[0]} -> {best[2]:.0f} mediciones, final {best[3]:.3f} % (perdida {best[4]:+.3f} pp), energia {best[5]:.2f} %")
json.dump(chosen, open("resultados_V7/seleccion_regla_V7.json", "w"), indent=1); open("resultados_V7/seleccion_regla_V7.txt", "w").write("\n".join(lines))
