"""
estatico_V17.py — Cola ESTATICA de las variantes con verificacion (V17). Misma medida que refuerzo_V14.py: perdida de exactitud final contra el MSAPSO completo (pp).
USO: python3 estatico_V17.py val|val2 -> (val2 = rejilla V17.1 intercalada) VALIDACION (elegir la variante): 1000 curvas 8080/8081 + 100 curvas por panel (semilla 6161), 4 paneles
     python3 estatico_V17.py test <variante> [...] -> PRUEBA: S (7777/7778, la de la V7.1 y V14), P (5151) y conjuntos frescos (9393/9394; paneles 5252)
-> resultados_V17/estatico_<modo>_V17.txt|json
"""
import json, sys
from multiprocessing import Pool
from msapso_early_V14 import *
from entorno_V14 import mix_curves, panel_ctx
from verificacion_V17 import GRID, GRID_I, GRID_R, VCfg, make_any, name

PANELS = [("base 60c", 60, 8.9, 1.5, 4), ("72c-6s", 72, 9.5, 1.5, 6), ("36c-3s", 36, 5.5, 1.5, 3), ("60c-11A", 60, 11.0, 1.3, 4), ("96c-6.5A", 96, 6.5, 1.7, 4)]
FULL, V7 = make_msapso_early(Rule("none")), make_msapso_early(Rule("disp", delta=0.02, t_min=3))


def final_acc(fn, curves, b=0.0, noise=0.0):
    fin, nm = [], []
    for k, c in enumerate(curves):
        rng = np.random.default_rng(7 + 1000 * k); pl = StaticPlant(c, noise_w=noise, rng=rng); fn(pl, c, rng)
        Pm = np.array(pl.log_Pmeas); sel = int(np.where(Pm == Pm.max())[0][-1]); fin.append(100.0 * pl.p_true(pl.log_I[sel] * (1 - b)) / c.P_gmpp); nm.append(len(Pm))
    return np.array(fin), np.array(nm)


def build(seed_pair, panel_seed):
    """{nombre_conjunto: (params_panel, curvas)}; el panel base usa 1000 curvas (500 originales + 500 atenuadas), los otros 100 mezcladas."""
    r1, r2 = np.random.default_rng(seed_pair[0]), np.random.default_rng(seed_pair[1])
    sets = {f"base 1000 ({seed_pair[0]}/{seed_pair[1]})": (None, [SyntheticPVCurve(random_shading_mix(r1)) for _ in range(500)] + [SyntheticPVCurve(random_shading_mix(r2) * r2.uniform(0.25, 1.0)) for _ in range(500)])}
    for nm, ns, isc, A, nsub in PANELS[1:]:
        with panel_ctx(ns, isc, A): sets[f"{nm} 100 ({panel_seed})"] = ((ns, isc, A), mix_curves(np.random.default_rng(panel_seed), 100, nsub))
    return sets


def job(args):
    key, vc, b, params, curves, noise = args
    fn = FULL if vc == "FULL" else V7 if vc == "V7" else make_any(vc)
    if params:
        with panel_ctx(*params): f, n = final_acc(fn, curves, b, noise)
    else: f, n = final_acc(fn, curves, b, noise)
    return key, f, n


def run(sets, variants, noise=0.0):
    jobs = []
    for s, (params, curves) in sets.items():
        jobs.append(((s, "FULL", 0.0), "FULL", 0.0, params, curves, noise)); jobs.append(((s, "V7", 0.0), "V7", 0.0, params, curves, noise))
        for vc in variants:
            for b in (0.0, 0.02): jobs.append(((s, name(vc), b), vc, b, params, curves, noise))
    with Pool(22) as p: R = {k: (f, n) for k, f, n in p.map(job, jobs, chunksize=1)}
    return R


def table(R, sets, variants, P):
    out = {}
    for s in sets:
        base = R[(s, "FULL", 0.0)][0]
        P(f"\n{s}: perdida vs MSAPSO completo (pp) | med. | media | p95 | p99 | max | % > 3 pp")
        rows = [("V7 (parada)", "V7", 0.0)] + [(f"{name(v)} b={b:g}", name(v), b) for v in variants for b in (0.0, 0.02)]
        for lbl, n, b in rows:
            f, m = R[(s, n, b)]; d = base - f
            P(f"  {lbl:32s} | {m.mean():5.1f} | {d.mean():+.3f} | {np.percentile(d,95):5.2f} | {np.percentile(d,99):5.2f} | {d.max():5.2f} | {100*np.mean(d>3):4.1f}")
            out[f"{s}|{lbl}"] = dict(med=float(m.mean()), media=float(d.mean()), p95=float(np.percentile(d, 95)), p99=float(np.percentile(d, 99)), max=float(d.max()), gt3=float(np.mean(d > 3)))
    return out


if __name__ == "__main__":
    mode = sys.argv[1]; lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    if mode == "val":
        sets = build((8080, 8081), 6161); variants = GRID; noise = 0.0
    elif mode == "val2":
        sets = build((8080, 8081), 6161); variants = [GRID[0]] + GRID_I; noise = 0.0
    elif mode == "val3":
        sets = build((8080, 8081), 6161); variants = [GRID[0]] + GRID_R; noise = 0.0
    else:
        sel = [v for v in GRID + GRID_I + GRID_R if name(v) in sys.argv[2:]]; assert len(sel) == len(sys.argv[2:]), sys.argv[2:]
        variants = [GRID[0]] + sel; noise = float(os.environ.get("RUIDO", 0.0))
        sets = build((7777, 7778), 5151) | build((9393, 9394), 5252)
        mode = mode + (f"_ruido{noise:g}" if noise else "")
    P(f"ESTATICO V17 ({mode}); ruido {noise:g} W; perdida = exactitud final MSAPSO completo - metodo")
    R = run(sets, variants, noise); out = table(R, sets, variants, P)
    open(f"resultados_V17/estatico_{mode}_V17.txt", "w").write("\n".join(lines)); json.dump(out, open(f"resultados_V17/estatico_{mode}_V17.json", "w"), indent=1)
