"""
sensibilidad_V7.py — V7.3: ANALISIS DE SENSIBILIDAD de la parada anticipada (regla de dispersion < delta) alrededor de la configuracion de la V7 (delta = 0.02, t_min = 3, 7 particulas, t_max = 25).
Se varia UN parametro a la vez (y una malla delta x particulas) sobre 200 curvas FRESCAS (semillas 8100/8101) y los 4 casos reales, con ruido de 0 y 2 W; la referencia es el MSAPSO completo del paper
(7 particulas, 25 pasadas). Metricas: mediciones, perdida de exactitud final (pp), perdida en el peor caso (percentil 99 y maximo) y energia de ventana. Aparte (modo D) se mide la sensibilidad a delta
en OPERACION (simulador dinamico, 5 ms): cambio unico y sombra frecuente.
USO: python3 sensibilidad_V7.py S   (estatico)   |   python3 sensibilidad_V7.py D   (dinamico, delta)
"""
import json, sys
from msapso_early_V7 import *
from pvsim_V7.msapso_V7 import INIT_FRACS


def fracs_for(npart):
    return INIT_FRACS if npart == 7 else tuple(np.linspace(0.95, 0.10, npart))


def make_variant(delta=0.02, t_min=3, npart=7, tmax=25, beta=(0.1, 0.95)):
    fr = fracs_for(npart)
    def f(plant, curve, rng):
        sw = Swarm(first_pass="ascending", fracs=fr); sw.restart(curve.Isc, first=True)
        for _ in range(tmax):
            sw.sweep(plant, 1.0); disp = sw.dispersion(); t = sw.t
            sw.update(beta[0] + (sw.t / tmax) * (beta[1] - beta[0]))
            if delta is not None and t >= t_min and disp < delta: break
    return f


if __name__ == "__main__":
    mode = sys.argv[1]; lines = []; out = {}
    def P(s=""): print(s, flush=True); lines.append(s)
    if mode == "S":
        r1 = np.random.default_rng(8100); r2 = np.random.default_rng(8101)
        curves = [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(100)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(100)]
        real, _ = scenarios()
        base = {ns: (eval_curves(make_variant(None), curves, noise_w=ns, reps=1 if ns == 0 else 2), eval_curves(make_variant(None), real, noise_w=ns, reps=1 if ns == 0 else 6)) for ns in (0.0, 2.0)}
        def row(label, kw, group):
            res = []
            for ns in (0.0, 2.0):
                f, e, n = eval_curves(make_variant(**kw), curves, noise_w=ns, reps=1 if ns == 0 else 2); fr, er, nr = eval_curves(make_variant(**kw), real, noise_w=ns, reps=1 if ns == 0 else 6)
                d = base[ns][0][0] - f; res.append((float(n.mean()), float(d.mean()), float(np.percentile(d, 99)), float(d.max()), float(e.mean()), float(base[ns][1][0].mean() - fr.mean())))
            out[f"{group}|{label}"] = res
            P(f"{label:28s} | " + " | ".join(f"{r[0]:5.0f} {r[1]:+.3f} {r[2]:6.3f} {r[3]:6.2f} {r[4]:6.2f} {r[5]:+.3f}" for r in res))
        P("columnas por ruido (0 W | 2 W): mediciones, perdida media (pp), p99, maximo, energia, perdida en los 4 casos reales (pp)")
        P(f"MSAPSO completo (referencia): " + " | ".join(f"{base[ns][0][2].mean():.0f} med." for ns in (0.0, 2.0)))
        P("\n-- delta (t_min = 3, 7 particulas, t_max = 25) --"); [row(f"delta = {d}", dict(delta=d), "delta") for d in (0.005, 0.01, 0.015, 0.02, 0.03, 0.05)]
        P("\n-- t_min (delta = 0.02) --"); [row(f"t_min = {t}", dict(t_min=t), "t_min") for t in (1, 2, 3, 5, 8)]
        P("\n-- numero de particulas (delta = 0.02; el MSAPSO completo de referencia es el de 7 particulas) --"); [row(f"{n} particulas", dict(npart=n), "particulas") for n in (5, 7, 9, 12)]
        P("\n-- t_max, que fija la rapidez de contraccion de beta (delta = 0.02) --"); [row(f"t_max = {t}", dict(tmax=t), "t_max") for t in (12, 15, 25, 40)]
        P("\n-- malla delta x particulas (delta = 0.01 / 0.02 / 0.03) --"); [row(f"{n} part., delta = {d}", dict(delta=d, npart=n), "malla") for n in (5, 9) for d in (0.01, 0.02, 0.03)]
        open("resultados_V7/sensibilidad_S_V7.txt", "w").write("\n".join(lines)); json.dump(out, open("resultados_V7/sensibilidad_S_V7.json", "w"))
    elif mode == "D":
        from operacion_V7 import run_ops, make_curves_aug, make_sequence, SEG
        real, _ = scenarios(); wait = 5e-3; rb = np.random.default_rng(0)
        def boot(d, B=4000):
            i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
        pairs = [([real[a], real[b]], [0, SEG]) for a in range(4) for b in range(4) if a != b]; cs = make_curves_aug(80, 8200); synth = [([cs[2 * k], cs[2 * k + 1]], [0, SEG]) for k in range(40)]
        pool = make_curves_aug(200, 8201); rng = np.random.default_rng(8202); freq = [make_sequence(rng, pool, 100, 3000) for _ in range(12)]
        groups = [("cambio unico, 12 pares reales", pairs, 2 * SEG), ("cambio unico, 40 sinteticos", synth, 2 * SEG), ("sombra frecuente (alto), 12 secuencias", freq, 3000)]
        P("Sensibilidad a delta en OPERACION (5 ms): diferencia de energia respecto al MSAPSO completo, pp [IC95 %]")
        P(f"{'delta':10s} | " + " | ".join(g[0] for g in groups))
        base = {g: np.array([run_ops(make_variant(None), c, b, wait, tot, seed=k)[0] for k, (c, b) in enumerate(sc)]) for g, sc, tot in groups}
        for d in (0.005, 0.01, 0.02, 0.03, 0.05):
            row = []
            for g, sc, tot in groups:
                e = np.array([run_ops(make_variant(d), c, b, wait, tot, seed=k)[0] for k, (c, b) in enumerate(sc)]); r = boot(e - base[g]); row.append(f"{r[0]:+.2f} [{r[1]:+.2f}, {r[2]:+.2f}]"); out[f"{d}|{g}"] = r
            P(f"{d:<10} | " + " | ".join(row))
        open("resultados_V7/sensibilidad_D_V7.txt", "w").write("\n".join(lines)); json.dump(out, open("resultados_V7/sensibilidad_D_V7.json", "w"))
