"""
optimizar_msapso_V2.py — CONTROL SIN RL: MSAPSO con el calendario de beta OPTIMIZADO a mano (busqueda aleatoria),
conservando todo lo demas del paper (7 particulas, barrido alternante, Gbest inmediato, regla de reinicio de 5 W).
Se optimizan (beta_min, beta_max, t_max) con escenarios del tipo de ENTRENAMIENTO (sombras sinteticas con semilla distinta a la de prueba);
la mejor configuracion se evalua despues en los conjuntos de prueba (casos reales, pares reales, sinteticas nuevas).
Pregunta que responde: ¿lo que gana el agente de RL se explica simplemente por un mejor calendario de beta?
USO: python3 optimizar_msapso_V2.py --wait 5e-3 --n-config 120
"""
import argparse, json, os, sys, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from multiprocessing import Pool
from pvsim_V2.array_model_V2 import SyntheticPVCurve, random_shading_mix
from pvsim_V2.msapso_V2 import MSAPSOController, run_scenario, segment_metrics
from pvsim_V2.harness_V2 import build_scenarios, evaluate, summarize, PASSES

_WAIT = None
_TRAIN = None


def _init(wait, n_train):
    global _WAIT, _TRAIN
    _WAIT = wait
    rng = np.random.default_rng(7)                       # semilla de OPTIMIZACION (distinta de la de prueba, 2026)
    _TRAIN = [(SyntheticPVCurve(random_shading_mix(rng)), SyntheticPVCurve(random_shading_mix(rng))) for _ in range(n_train)]


def _init_val(wait):
    global _WAIT, _TRAIN
    _WAIT = wait
    rng = np.random.default_rng(8)                      # semilla de VALIDACION (distinta de optimizacion=7 y prueba=2026)
    _TRAIN = [(SyntheticPVCurve(random_shading_mix(rng)), SyntheticPVCurve(random_shading_mix(rng))) for _ in range(150)]


def _score(cfg):
    bmin, bmax, tmax = cfg
    vals = []
    for A, B in _TRAIN:
        segs = [(A, PASSES * 7 * _WAIT), (B, PASSES * 7 * _WAIT)]
        log = run_scenario(lambda: MSAPSOController(_WAIT, beta_min=bmin, beta_max=bmax, t_max=tmax), segs, _WAIT)
        vals.append(segment_metrics(log, 1)["eff_energy"])
    return cfg, float(np.mean(vals))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=float, default=5e-3)
    ap.add_argument("--n-config", type=int, default=150)
    ap.add_argument("--n-train", type=int, default=60)
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    rng = np.random.default_rng(11)
    cfgs = [(0.1, 0.95, 25)]                               # configuracion del paper (referencia)
    for _ in range(a.n_config):
        bmin = float(rng.uniform(0.05, 0.95)); bmax = float(rng.uniform(max(bmin, 0.3), 0.99))
        cfgs.append((round(bmin, 3), round(bmax, 3), int(rng.choice([3, 5, 8, 12, 18, 25]))))
    with Pool(a.procs, initializer=_init, initargs=(a.wait, a.n_train)) as pool:
        scored = pool.map(_score, cfgs, chunksize=2)
    scored.sort(key=lambda x: -x[1])
    # ETAPA 2: re-puntuar las 8 mejores + la del paper con 150 pares de VALIDACION (semilla 8) para evitar el sobreajuste
    finalists = [c for c, _ in scored[:8]] + [(0.1, 0.95, 25)]
    with Pool(a.procs, initializer=_init_val, initargs=(a.wait,)) as pool:
        val = pool.map(_score, finalists)
    val.sort(key=lambda x: -x[1])
    paper = [(c, v) for c, v in val if c == (0.1, 0.95, 25)][0]
    scored = val + [x for x in scored if x[0] not in finalists]
    best = val[0][0]
    scen = build_scenarios()
    res_best = evaluate(lambda: MSAPSOController(a.wait, beta_min=best[0], beta_max=best[1], t_max=best[2]), a.wait, scen)
    res_paper = evaluate(lambda: MSAPSOController(a.wait), a.wait, scen)
    out = dict(wait=a.wait, paper_cfg=dict(cfg=paper[0], val_score=paper[1]), best_cfg=dict(cfg=best, val_score=val[0][1]),
               top10=[dict(cfg=c, score=s) for c, s in scored[:10]],
               test_best=summarize(res_best), test_paper=summarize(res_paper), raw_best=res_best)
    json.dump(out, open(f"resultados_V2/msapso_optimizado_{a.wait*1e3:g}ms.json", "w"), default=float, indent=1)
    print(f"t_wait={a.wait*1e3:g} ms | validacion: paper (0.1,0.95,25) {paper[1]:.2f}%  |  mejor {best}: {val[0][1]:.2f}%")
    for g in ("static", "pairs", "synth"):
        print(f"  {g:7s} paper: energia {out['test_paper'][g]['eff_energy']:.2f} final {out['test_paper'][g]['eff_final']:.2f}"
              f"   | optimizado: energia {out['test_best'][g]['eff_energy']:.2f} final {out['test_best'][g]['eff_final']:.2f}")
