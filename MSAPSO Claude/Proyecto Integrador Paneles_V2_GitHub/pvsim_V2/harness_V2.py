"""
harness_V2 — Arnes de evaluacion COMUN para todos los metodos (MSAPSO fiel, agentes PPO, REINFORCE...).
Mismos escenarios, mismo simulador, misma metrica => comparacion justa.

Escenarios (cada segmento dura PASSES pasadas = PASSES*7*t_wait segundos):
  static : los 4 casos reales del paper, un solo segmento
  pairs  : los 12 pares ordenados de los 4 casos reales (sombra A durante un segmento, luego B)  [HOLDOUT: nunca vistos en entrenamiento]
  synth  : N pares de curvas sinteticas nuevas (semilla fija, distintas de las de entrenamiento)  [generalizacion]
Metricas por escenario (del ultimo segmento, tras el cambio en 'pairs'/'synth'): ver msapso_V2.segment_metrics.
"""
import numpy as np
from pvsim_V2.pvcurve_V2 import load_case
from pvsim_V2.array_model_V2 import SyntheticPVCurve, random_shading_mix
from pvsim_V2.msapso_V2 import run_scenario, segment_metrics

PASSES = 62          # pasadas por segmento (el MSAPSO tarda 25 en la 1.a busqueda; el resto es mantenimiento)


def build_scenarios(n_synth=100, seed=2026):
    cases = [load_case(i) for i in range(4)]
    rng = np.random.default_rng(seed)
    synth = [(SyntheticPVCurve(random_shading_mix(rng)), SyntheticPVCurve(random_shading_mix(rng))) for _ in range(n_synth)]
    return {
        "static": [(f"caso {i+1}", [cases[i]]) for i in range(4)],
        "pairs":  [(f"{a+1}->{b+1}", [cases[a], cases[b]]) for a in range(4) for b in range(4) if a != b],
        "synth":  [(f"s{k}", list(pair)) for k, pair in enumerate(synth)],
    }


def evaluate(make_ctrl, wait, scen=None, groups=("static", "pairs", "synth"), passes=PASSES):
    scen = scen or build_scenarios()
    res = {}
    for g in groups:
        res[g] = []
        for name, curves in scen[g]:
            segs = [(c, passes * 7 * wait) for c in curves]
            log = run_scenario(make_ctrl, segs, wait)
            m = segment_metrics(log, len(curves) - 1)
            m["name"] = name
            res[g].append(m)
    return res


def summarize(res):
    out = {}
    for g, ms in res.items():
        out[g] = dict(
            eff_energy=float(np.mean([m["eff_energy"] for m in ms])),
            eff_final=float(np.mean([m["eff_final"] for m in ms])),
            t99_ms=float(np.nanmean([m["t99"] for m in ms]) * 1e3) if np.isfinite([m["t99"] for m in ms]).any() else float("nan"),
            restarts=float(np.mean([m["n_restarts"] for m in ms])),
            n_final99=int(sum(m["eff_final"] >= 99.0 for m in ms)), n=len(ms),
        )
    return out
