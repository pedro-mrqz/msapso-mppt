"""
reinforce_grid_V2.py — Malla en ETAPAS de la rama REINFORCE (propuesta del profesor).
Etapa 1 (coarse): 6 formas/baselines x 5 tasas de aprendizaje x 3 sigmas x 2 normalizaciones de recompensa = 180 configuraciones,
  puntuadas con sombras sinteticas de ENTRENAMIENTO (semilla 7; 30 pares x 2 repeticiones; energia del 2.o segmento).
Etapa 2: la mejor configuracion de cada (forma, baseline) y la mejor de cada tasa de aprendizaje (forma B) se evaluan en los
  conjuntos de PRUEBA (4 estaticos, 12 pares reales, 100 sinteticas nuevas) con 5 repeticiones (semillas distintas).
Salida: resultados_V2/reinforce_grid_V2.json
"""
import json, os, sys, itertools, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from multiprocessing import Pool
from pvsim_V2.array_model_V2 import SyntheticPVCurve, random_shading_mix
from pvsim_V2.msapso_V2 import run_scenario, segment_metrics
from pvsim_V2.reinforce_V2 import ReinforceController
from pvsim_V2.harness_V2 import build_scenarios, PASSES

WAIT = 5e-3
_TRAIN = None


def _init():
    global _TRAIN
    rng = np.random.default_rng(7)
    _TRAIN = [(SyntheticPVCurve(random_shading_mix(rng)), SyntheticPVCurve(random_shading_mix(rng))) for _ in range(30)]


def _lr_options():
    return [("fixed", 0.1), ("fixed", 0.01), ("fixed", 0.001), ("accel", None), ("inv_t", None)]


def _cfg_kwargs(cfg):
    form, base, (lr, lv), sigma, rnorm = cfg
    return dict(form=form, baseline=base, lr=lr, lr_value=(lv if lv is not None else 0.0), sigma=sigma, rnorm=rnorm)


def _score(cfg):
    kw = _cfg_kwargs(cfg)
    vals = []
    for k, (A, B) in enumerate(_TRAIN):
        for rep in range(2):
            segs = [(A, PASSES * 7 * WAIT), (B, PASSES * 7 * WAIT)]
            seed = 10_000 + 17 * k + rep
            log = run_scenario(lambda: ReinforceController(WAIT, rng=np.random.default_rng(seed), **kw), segs, WAIT)
            vals.append(segment_metrics(log, 1)["eff_energy"])
    return cfg, float(np.mean(vals))


def _test(args):
    cfg, scen_group, name, curves, rep = args
    kw = _cfg_kwargs(cfg)
    segs = [(c, PASSES * 7 * WAIT) for c in curves]
    seed = 777 + 31 * rep + hash(name) % 1000
    log = run_scenario(lambda: ReinforceController(WAIT, rng=np.random.default_rng(seed), **kw), segs, WAIT)
    m = segment_metrics(log, len(curves) - 1)
    return cfg, scen_group, rep, m["eff_energy"], m["eff_final"], m["n_restarts"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sigmas", nargs="*", type=float, default=[0.3, 0.5, 0.8])
    ap.add_argument("--arms", nargs="*", default=["B-none", "B-V", "A-none", "A-V", "A-Q", "A-QV"])
    ap.add_argument("--out", default="resultados_V2/reinforce_grid_V2.json")
    ap.add_argument("--procs", type=int, default=3)
    args = ap.parse_args()
    t0 = time.time()
    forms = [tuple(x.split("-")) for x in args.arms]
    grid = [(f, b, lr, s, rn) for (f, b) in forms for lr in _lr_options() for s in args.sigmas for rn in ("rated", "best")]
    with Pool(args.procs, initializer=_init) as pool:
        scored = pool.map(_score, grid, chunksize=2)
        stage1 = [dict(form=c[0], baseline=c[1], lr=c[2][0], lr_value=c[2][1], sigma=c[3], rnorm=c[4], train_energy=s) for c, s in scored]
        # seleccion
        chosen = {}
        for (f, b) in forms:
            best = max([x for x in scored if x[0][0] == f and x[0][1] == b], key=lambda x: x[1])
            chosen[f"{f}-{b}"] = best[0]
        if ("B", "none") in forms:
            for lr in _lr_options():
                cand = [x for x in scored if x[0][0] == "B" and x[0][1] == "none" and x[0][2] == lr]
                chosen[f"B-none | lr={lr[0]}{'' if lr[1] is None else lr[1]}"] = max(cand, key=lambda x: x[1])[0]
        scen = build_scenarios()
        jobs = []
        for key, cfg in chosen.items():
            for g in ("static", "pairs", "synth"):
                for name, curves in scen[g]:
                    for rep in range(5 if g != "synth" else 2):
                        jobs.append((cfg, g, name, curves, rep))
        res = pool.map(_test, jobs, chunksize=8)
    summary = {}
    for key, cfg in chosen.items():
        summary[key] = dict(cfg=dict(zip(["form", "baseline", "lr", "sigma", "rnorm"], [cfg[0], cfg[1], list(cfg[2]), cfg[3], cfg[4]])))
        for g in ("static", "pairs", "synth"):
            rows = [r for r in res if r[0] == cfg and r[1] == g]
            summary[key][g] = dict(energy=float(np.mean([r[3] for r in rows])), final=float(np.mean([r[4] for r in rows])),
                                   restarts=float(np.mean([r[5] for r in rows])), n=len(rows))
    json.dump(dict(stage1=stage1, chosen={k: dict(form=v[0], baseline=v[1], lr=list(v[2]), sigma=v[3], rnorm=v[4]) for k, v in chosen.items()},
                   test=summary), open(args.out, "w"), indent=1, default=float)
    print(f"listo en {time.time()-t0:.0f} s")
    print(f"{'configuracion elegida':30s}{'static':>16s}{'pairs':>16s}{'synth':>16s}   (energia % / final %)")
    for k, v in summary.items():
        print(f"{k:30s}" + "".join(f"{v[g]['energy']:9.2f}/{v[g]['final']:5.1f}  " for g in ("static", "pairs", "synth")) + f"  {v['cfg']['lr']} s={v['cfg']['sigma']} {v['cfg']['rnorm']}")
