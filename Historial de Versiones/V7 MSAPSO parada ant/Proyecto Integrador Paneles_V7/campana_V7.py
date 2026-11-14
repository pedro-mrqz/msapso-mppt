"""
campana_V7.py — V7.4: CAMPANA MONTE CARLO de validacion final de la parada anticipada (miles de escenarios dinamicos aleatorios, UNA sola corrida, configuracion CONGELADA: parada principal (dispersion < 0.02)
y parada prudente de la V7; sin ajustar nada despues de ver los resultados). Cada escenario se genera por completo a partir de su semilla (100000 + indice) con la distribucion FIJADA ANTES de correr:
  panel      : base (60 celdas, 4 sub-strings, Isc 8.9 A) | 72 celdas, 6 sub-strings | 36 celdas, 3 sub-strings | 60 celdas, Isc 11 A, A = 1.3 | 96 celdas, Isc 6.5 A, A = 1.7   (uniforme)
  t_wait     : 5 ms (40 %) | 2 ms (20 %) | 1 ms (20 %) | 0.5 ms (20 %)
  regimen    : cambio unico (30 %) | sombra frecuente moderada (15 %, ~300 ventanas entre cambios) | alta (20 %, ~100) | muy alta (10 %, ~40) | flicker parcial (20 %, amplitud 0.1/0.3/0.6, ~100 o ~40) | estable (5 %, ~1500)
  ruido      : 0 W (50 %) | 1 W (25 %) | 2 W (25 %)
  patrones   : sinteticos (con atenuacion global la mitad de las veces); en el panel base, 30 % de los escenarios usan los 4 casos reales del paper
Metodos: MSAPSO completo (referencia) | V7 parada principal | V7 parada prudente. Energia real integrada en el simulador dinamico (Boost + Super-Twisting, reinicio por 5 W, asentamiento de la V6) / (P_ceiling x duracion).
USO: python3 campana_V7.py run <fragmento> <n_fragmentos> <n_escenarios>   |   python3 campana_V7.py agregar
"""
import json, sys, os, glob
from msapso_early_V7 import *
from operacion_V7 import run_ops, SEG, make_sequence
import refuerzo_V7 as rf

CH = json.load(open("resultados_V7/seleccion_regla_V7.json"))
def rule_of(c): return Rule(c["kind"], c["k"], c["eps"], c["delta"], c["t_min"])
METHODS = [("full", make_msapso_early(Rule("none"))), ("principal", make_msapso_early(rule_of(CH["principal (<= 0.10 pp)"]))), ("prudente", make_msapso_early(rule_of(CH["prudente (<= 0.02 pp)"])))]
PANELS = [("base", 60, 8.9, 1.5, 4), ("72c-6s", 72, 9.5, 1.5, 6), ("36c-3s", 36, 5.5, 1.5, 3), ("60c-11A", 60, 11.0, 1.3, 4), ("96c-6.5A", 96, 6.5, 1.7, 4)]
WAITS = [(5e-3, 0.40), (2e-3, 0.20), (1e-3, 0.20), (5e-4, 0.20)]
REGIMES = [("unico", 0.30), ("moderado", 0.15), ("alto", 0.20), ("muy alto", 0.10), ("flicker", 0.20), ("estable", 0.05)]
NOISES = [(0.0, 0.50), (1.0, 0.25), (2.0, 0.25)]
MEAN = {"moderado": 300, "alto": 100, "muy alto": 40, "estable": 1500}


def pick(rng, table):
    vals = [v for v, _ in table]; p = np.array([w for _, w in table]); return vals[int(rng.choice(len(vals), p=p / p.sum()))]


def make_scenario(idx):
    rng = np.random.default_rng(100000 + idx)
    panel = PANELS[int(rng.integers(len(PANELS)))]; wait = pick(rng, WAITS); reg = pick(rng, REGIMES); noise = pick(rng, NOISES)
    real_src = panel[0] == "base" and rng.random() < 0.30
    meta = dict(idx=idx, panel=panel[0], wait=wait, regimen=reg, ruido=noise, fuente="reales" if real_src else "sinteticos")
    real, _ = scenarios()
    with rf.panel(panel[1], panel[2], panel[3]):
        nsub = panel[4]
        if reg == "unico":
            if real_src:
                a, b = rng.choice(4, 2, replace=False); curves = [real[a], real[b]]
            else:
                curves = rf.mix_curves(rng, 2, nsub)
            bounds, total = [0, SEG], 2 * SEG
        elif reg == "flicker":
            amp = float(rng.choice([0.1, 0.3, 0.6])); ml = int(rng.choice([100, 40])); meta.update(amp=amp, ml=ml)
            curves, bounds = rf.flicker_sequence(rng, ml, amp, nsub=nsub); total = 3000
        else:
            pool = real if real_src else rf.mix_curves(rng, 30, nsub)
            curves, bounds = make_sequence(rng, pool, MEAN[reg], 3000); total = 3000
    meta["n_seg"] = len(curves)
    return meta, curves, bounds, total


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "run":
        shard, nshard, N = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]); outf = f"resultados_V7/campana_fragmento_{shard}.jsonl"; done = set()
        if os.path.exists(outf): done = {json.loads(l)["idx"] for l in open(outf)}
        with open(outf, "a") as f:
            for idx in range(shard, N, nshard):
                if idx in done: continue
                meta, curves, bounds, total = make_scenario(idx)
                for name, fn in METHODS:
                    e, fin, nr, ns = run_ops(fn, curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"]); meta[name] = dict(e=e, fin=fin, nr=nr, ns=ns)
                f.write(json.dumps(meta) + "\n"); f.flush()
        print(f"fragmento {shard} listo", flush=True)
    elif mode == "agregar":
        _fn = ["resultados_V7/campana_V7.jsonl"] if os.path.exists("resultados_V7/campana_V7.jsonl") else sorted(glob.glob("resultados_V7/campana_fragmento_*.jsonl"))
        R = [json.loads(l) for fn in _fn for l in open(fn)]
        rb = np.random.default_rng(0); lines = []
        def P(s=""): print(s, flush=True); lines.append(s)
        def boot(d, B=3000):
            i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
        P(f"CAMPANA MONTE CARLO: {len(R)} escenarios dinamicos aleatorios (semillas 100000+).")
        out = {}
        for m in ("principal", "prudente"):
            d = np.array([r[m]["e"] - r["full"]["e"] for r in R]); df = np.array([r[m]["fin"] - r["full"]["fin"] for r in R]); b = boot(d)
            P(f"\n== V7 {m} menos MSAPSO completo (diferencia de energia, pp) ==")
            P(f"  media {b[0]:+.3f} [{b[1]:+.3f}, {b[2]:+.3f}] | mediana {np.median(d):+.3f} | percentiles 1/5/25/75/95/99: " + " / ".join(f"{np.percentile(d, q):+.2f}" for q in (1, 5, 25, 75, 95, 99)) + f" | peor {d.min():+.2f}")
            P(f"  escenarios: gana (> +0.5 pp) {100*np.mean(d > 0.5):.1f} % | empata (±0.5) {100*np.mean(np.abs(d) <= 0.5):.1f} % | pierde (< -0.5) {100*np.mean(d < -0.5):.1f} % | pierde mucho (< -3) {100*np.mean(d < -3):.1f} % | (< -5) {100*np.mean(d < -5):.1f} %")
            P(f"  exactitud final al terminar (ultimas 20 ventanas): media {df.mean():+.2f} pp | reinicios por escenario: MSAPSO {np.mean([r['full']['nr'] for r in R]):.1f}, V7 {np.mean([r[m]['nr'] for r in R]):.1f}")
            out[m] = dict(media=b, p5=float(np.percentile(d, 5)), peor=float(d.min()), pierde=float(np.mean(d < -0.5)), pierde_mucho=float(np.mean(d < -3)))
            for title, key in (("regimen", "regimen"), ("t_wait (s)", "wait"), ("ruido (W)", "ruido"), ("panel", "panel"), ("fuente de patrones", "fuente")):
                P(f"  -- por {title} --")
                for v in sorted(set(r[key] for r in R), key=lambda x: (str(type(x)), x)):
                    sub = np.array([r[m]["e"] - r["full"]["e"] for r in R if r[key] == v]); bb = boot(sub)
                    P(f"    {str(v):12s} n={len(sub):4d} | {bb[0]:+.2f} [{bb[1]:+.2f}, {bb[2]:+.2f}] | pierde (< -0.5) {100*np.mean(sub < -0.5):5.1f} % | peor {sub.min():+.1f}")
                    out[f"{m}|{key}|{v}"] = dict(n=len(sub), media=bb, pierde=float(np.mean(sub < -0.5)), peor=float(sub.min()))
        # los peores escenarios de la parada principal
        worst = sorted(R, key=lambda r: r["principal"]["e"] - r["full"]["e"])[:8]
        P("\n== Los 8 peores escenarios de la parada principal ==")
        for r in worst: P(f"  idx {r['idx']:5d} | {r['panel']:9s} | t_wait {r['wait']*1e3:g} ms | {r['regimen']:9s} | ruido {r['ruido']:g} W | {r['fuente']:10s} | MSAPSO {r['full']['e']:.1f}% -> V7 {r['principal']['e']:.1f}% ({r['principal']['e']-r['full']['e']:+.1f} pp), reinicios {r['full']['nr']} -> {r['principal']['nr']}")
        open("resultados_V7/campana_V7.txt", "w").write("\n".join(lines)); json.dump(out, open("resultados_V7/campana_V7.json", "w"))
