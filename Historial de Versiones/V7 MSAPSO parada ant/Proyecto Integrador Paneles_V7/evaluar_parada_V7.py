"""
evaluar_parada_V7.py — Evaluacion de la parada anticipada en la PRUEBA FRESCA (100 originales semilla 4040 + 100 con atenuacion semilla 4041) y los 4 casos reales,
con las reglas CONGELADAS por seleccion_regla_V7.py; sin ruido y con ruido de 1 y 2 W (reglas NO re-ajustadas). IC95 % bootstrap pareados contra el MSAPSO completo.
Metodos: MSAPSO completo (175 med.) | parada principal | parada prudente | comprimido T=10 / 8 / 12 (beta del paper comprimida a T pasadas; hallado en validacion) | truncado fijo T=12.
USO: python3 evaluar_parada_V7.py -> resultados_V7/evaluar_parada_V7.txt|json
"""
import json
from msapso_early_V7 import *

CH = json.load(open("resultados_V7/seleccion_regla_V7.json"))
def rule_of(c): return Rule(c["kind"], c["k"], c["eps"], c["delta"], c["t_min"])
R_main, R_cau = rule_of(CH["principal (<= 0.10 pp)"]), rule_of(CH["prudente (<= 0.02 pp)"])
def trunc(T):
    def fn(plant, curve, rng):
        sw = Swarm(first_pass="ascending"); sw.restart(curve.Isc, first=True)
        for _ in range(T): sw.sweep(plant, 1.0); sw.update(paper_beta(sw.t))
    return fn
METHODS = [("MSAPSO completo (25 pasadas)", make_msapso_early(Rule("none"))), (f"parada principal ({CH['principal (<= 0.10 pp)']['nombre']})", make_msapso_early(R_main)),
           (f"parada prudente ({CH['prudente (<= 0.02 pp)']['nombre']})", make_msapso_early(R_cau)), ("comprimido T=12", make_msapso_early(Rule("none"), compress_T=12)),
           ("comprimido T=10", make_msapso_early(Rule("none"), compress_T=10)), ("comprimido T=8", make_msapso_early(Rule("none"), compress_T=8)), ("truncado fijo T=12 (beta del paper)", trunc(12))]
sets = make_sets(); lines = []; out = {}
def P(s=""): print(s, flush=True); lines.append(s)
rb = np.random.default_rng(0)
def boot(d, B=4000):
    i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
for noise in (0.0, 1.0, 2.0):
    P(f"\n=== PRUEBA FRESCA, ruido {noise:g} W | final / energia (ventana de 200 mediciones) ===")
    P(f"{'metodo':58s} | med. | PRUEBA ORIG (100) | PRUEBA ATENUADA (100) | REALES (4)")
    per = {}
    for name, fn in METHODS:
        row = []; per[name] = {}
        for g, reps in (("test_orig", 1), ("test_att", 1), ("real", 5 if noise else 1)):
            f, e, n = eval_curves(fn, sets[g], noise_w=noise, reps=reps); per[name][g] = (f, e, n); row.append(f"{f.mean():7.3f} / {e.mean():6.2f}")
        P(f"{name:58s} | {n.mean():4.0f} | " + " | ".join(row))
    ref = METHODS[0][0]; cat = lambda nm, j: np.concatenate([per[nm]["test_orig"][j], per[nm]["test_att"][j]])
    P("  Diferencias PAREADAS (200 curvas de prueba) respecto al MSAPSO completo, IC95 %:")
    for name, _ in METHODS[1:]:
        a = boot(cat(name, 0) - cat(ref, 0)); b = boot(cat(name, 1) - cat(ref, 1)); m = per[name]["test_orig"][2].mean()
        P(f"    {name:56s}: mediciones {m:4.0f} | final {a[0]:+.3f} [{a[1]:+.3f}, {a[2]:+.3f}] | energia {b[0]:+.2f} [{b[1]:+.2f}, {b[2]:+.2f}]")
        out[f"{noise}|{name}"] = dict(final=a, energia=b, mediciones=float(m))
open("resultados_V7/evaluar_parada_V7.txt", "w").write("\n".join(lines)); json.dump(out, open("resultados_V7/evaluar_parada_V7.json", "w"), indent=1)
