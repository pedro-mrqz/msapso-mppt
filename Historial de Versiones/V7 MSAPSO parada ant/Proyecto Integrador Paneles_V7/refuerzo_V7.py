"""
refuerzo_V7.py — V7.1: PRUEBAS DE ESTRES de la parada anticipada del MSAPSO (regla de dispersion < 0.02 de la V7, SIN re-ajustar nada). Responde a los huecos de la V7:
  F  flicker PARCIAL y de menor amplitud (simulador dinamico): cada cambio multiplica la irradiancia de cada sub-string por 1 - a*U(0,1) con prob. 0.5 (a = 0.1, 0.3, 0.6) sobre un patron base;
     cambios cada ~100 o ~40 ventanas (0.5 s / 0.2 s a 5 ms); 3000 ventanas; 15 escenarios por celda.
  N  RUIDO de medicion (1 y 2 W) en el simulador dinamico (cambio unico y sombra frecuente), donde el umbral de reinicio de 5 W tambien se ve afectado.
  P  OTROS PANELES (36, 72, 96 celdas; 3 a 6 sub-strings; Isc de 5.5 a 11 A; otro factor de idealidad): exactitud estatica y operacion con cambio unico.
  S  ESTADISTICA GRANDE y COLA: 1000 curvas estaticas frescas (semillas 7777/7778): perdida media, percentiles 95/99 y maximo.
  T  OTROS t_wait (2 ms y 1 ms): cambio unico.
Metodos: MSAPSO completo | parada principal (dispersion < 0.02) | parada prudente (Y, k=2, eps=0.1 W, delta=0.01) | dispersion < 0.01 (extra) | beta comprimida T=12 (extra).
USO: python3 refuerzo_V7.py F|N|P|S|T  -> resultados_V7/refuerzo_<modo>_V7.txt|json
"""
import json, sys, contextlib
from msapso_early_V7 import *
import pvsim_V7.array_model_V7 as am
from operacion_V7 import run_ops, make_curves_aug, make_sequence, SEG

CH = json.load(open("resultados_V7/seleccion_regla_V7.json"))
def rule_of(c): return Rule(c["kind"], c["k"], c["eps"], c["delta"], c["t_min"])
METHODS = [("MSAPSO completo", make_msapso_early(Rule("none"))), ("parada principal (disp<0.02)", make_msapso_early(rule_of(CH["principal (<= 0.10 pp)"]))),
           ("parada prudente", make_msapso_early(rule_of(CH["prudente (<= 0.02 pp)"]))), ("dispersion<0.01 (extra)", make_msapso_early(Rule("disp", delta=0.01))),
           ("comprimido T=12 (extra)", make_msapso_early(Rule("none"), compress_T=12))]
rb = np.random.default_rng(0)
def boot(d, B=4000):
    i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


@contextlib.contextmanager
def panel(ns, isc, A, nsub=None):
    """Cambia temporalmente los parametros del modelo de un diodo (las curvas guardan sus tablas al construirse)."""
    old = (am.NS, am.ISC_REF, am.RS, am.A_IDEAL, am.IO)
    am.NS, am.ISC_REF, am.A_IDEAL = ns, isc, A
    am.RS = 0.00497 * ns * (8.9 / isc); am.IO = 1.9164e-9 * (isc / 8.9)
    try: yield
    finally: am.NS, am.ISC_REF, am.RS, am.A_IDEAL, am.IO = old


def mix_curves(rng, n, nsub, att=True):
    out = []
    for _ in range(n):
        irr = random_shading_mix(rng, n_sub=nsub)
        if att and rng.random() < 0.5: irr = irr * rng.uniform(0.25, 1.0)
        out.append(SyntheticPVCurve(irr))
    return out


def flicker_sequence(rng, mean_len, amp, total=3000, nsub=4):
    base = random_shading_mix(rng, n_sub=nsub) * (rng.uniform(0.5, 1.0) if rng.random() < 0.5 else 1.0)
    bounds, w = [0], 0
    while True:
        w += max(15, int(rng.exponential(mean_len)))
        if w >= total: break
        bounds.append(w)
    curves = []
    for _ in bounds:
        f = 1.0 - amp * rng.uniform(0, 1, nsub) * (rng.random(nsub) < 0.5)
        curves.append(SyntheticPVCurve(base * f))
    return curves, bounds


def table(P, out, title, scen, wait, total, noise=0.0):
    P(f"\n=== {title} | t_wait = {wait*1e3:g} ms | energia real / exactitud final (% P_ceiling), reinicios por escenario ==="); res = {}
    for name, fn in METHODS:
        r = np.array([run_ops(fn, cs, bd, wait, total, seed=k, noise_w=noise) for k, (cs, bd) in enumerate(scen)]); res[name] = r
        P(f"{name:30s} | {r[:,0].mean():6.2f} / {r[:,1].mean():7.2f} | {r[:,2].mean():5.1f} reinic.")
    ref = res["MSAPSO completo"][:, 0]
    for name, _ in METHODS[1:]:
        d = boot(res[name][:, 0] - ref); P(f"   {name:28s} - MSAPSO completo (energia): {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]"); out[f"{title}|{wait}|{noise}|{name}"] = d


if __name__ == "__main__":
    mode = sys.argv[1]; lines = []; out = {}
    def P(s=""): print(s, flush=True); lines.append(s)
    real, _ = scenarios()
    if mode == "F":
        for wait in (5e-3, 5e-4):
            for ml in (100, 40):
                for amp in (0.1, 0.3, 0.6):
                    rng = np.random.default_rng(int(1000 * amp) + ml); scen = [flicker_sequence(rng, ml, amp) for _ in range(15)]
                    table(P, out, f"F) flicker parcial: amplitud {amp}, cambio cada ~{ml} ventanas", scen, wait, 3000)
    elif mode == "N":
        wait = 5e-3
        pairs = [([real[a], real[b]], [0, SEG]) for a in range(4) for b in range(4) if a != b]; cs = make_curves_aug(80, 6060); synth = [([cs[2 * k], cs[2 * k + 1]], [0, SEG]) for k in range(40)]
        pool = make_curves_aug(300, 9090)
        for ns in (1.0, 2.0):
            table(P, out, f"N) ruido {ns:g} W: cambio unico, 12 pares reales", pairs, wait, 2 * SEG, ns); table(P, out, f"N) ruido {ns:g} W: cambio unico, 40 pares sinteticos", synth, wait, 2 * SEG, ns)
            rng = np.random.default_rng(31 + int(ns)); table(P, out, f"N) ruido {ns:g} W: sombra frecuente (alto), sinteticos", [make_sequence(rng, pool, 100, 3000) for _ in range(15)], wait, 3000, ns)
    elif mode == "P":
        panels = [("72 celdas, 6 sub-strings, Isc 9.5 A", 72, 9.5, 1.5, 6), ("36 celdas, 3 sub-strings, Isc 5.5 A", 36, 5.5, 1.5, 3), ("60 celdas, 4 sub-strings, Isc 11 A, A=1.3", 60, 11.0, 1.3, 4), ("96 celdas, 4 sub-strings, Isc 6.5 A, A=1.7", 96, 6.5, 1.7, 4)]
        P("ESTATICO: 100 curvas por panel (semilla 5151); final / energia / mediciones")
        for name, ns, isc, A, nsub in panels:
            with panel(ns, isc, A):
                curves = mix_curves(np.random.default_rng(5151), 100, nsub)
                row = []
                for mn, fn in METHODS[:4]:
                    f, e, n = eval_curves(fn, curves); row.append((mn, f.mean(), e.mean(), n.mean()))
                base = row[0][1]
                P(f"  {name:42s} | " + " | ".join(f"{m.split(' (')[0][:20]:20s} {f:7.3f}/{e:6.2f}/{n:4.0f}" for m, f, e, n in row) + f" | perdida principal {base-row[1][1]:+.3f} pp")
                out[f"estatico|{name}"] = [(m, f, e, n) for m, f, e, n in row]
        wait = 5e-3
        for name, ns, isc, A, nsub in panels:
            with panel(ns, isc, A):
                rng = np.random.default_rng(777); cs = mix_curves(rng, 40, nsub); scen = [([cs[2 * k], cs[2 * k + 1]], [0, SEG]) for k in range(20)]
                table(P, out, f"P) operacion, cambio unico, {name}", scen, wait, 2 * SEG)
    elif mode == "S":
        r1 = np.random.default_rng(7777); r2 = np.random.default_rng(7778)
        curves = [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(500)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(500)]
        base = eval_curves(METHODS[0][1], curves); P("1000 curvas estaticas frescas (500 originales + 500 con atenuacion); sin ruido")
        P(f"{'metodo':30s} | med. | final | perdida media | p95 | p99 | maximo | % curvas con perdida > 0.5 pp | energia")
        for name, fn in METHODS:
            f, e, n = eval_curves(fn, curves); d = base[0] - f
            P(f"{name:30s} | {n.mean():4.0f} | {f.mean():6.3f} | {d.mean():+.4f} | {np.percentile(d,95):.3f} | {np.percentile(d,99):.3f} | {d.max():.2f} | {100*np.mean(d>0.5):5.1f} % | {e.mean():.2f}")
            out[name] = dict(mediciones=float(n.mean()), perdida=float(d.mean()), p95=float(np.percentile(d, 95)), p99=float(np.percentile(d, 99)), max=float(d.max()))
        d = boot(eval_curves(METHODS[1][1], curves)[0] - base[0]); P(f"  parada principal - MSAPSO completo (final): {d[0]:+.4f} [{d[1]:+.4f}, {d[2]:+.4f}]")
    elif mode == "T":
        pairs = [([real[a], real[b]], [0, SEG]) for a in range(4) for b in range(4) if a != b]; cs = make_curves_aug(120, 6060); synth = [([cs[2 * k], cs[2 * k + 1]], [0, SEG]) for k in range(60)]
        for wait in (2e-3, 1e-3):
            table(P, out, "T) cambio unico, 12 pares reales", pairs, wait, 2 * SEG); table(P, out, "T) cambio unico, 60 pares sinteticos", synth, wait, 2 * SEG)
    open(f"resultados_V7/refuerzo_{mode}_V7.txt", "w").write("\n".join(lines)); json.dump(out, open(f"resultados_V7/refuerzo_{mode}_V7.json", "w"), default=float)
