"""curva_aprendizaje_V2.py — Evalua los puntos de control (25 %, 50 %, 75 %, 100 % del entrenamiento) de las 3 semillas de PPO (5 ms)
con el arnes comun, para ver si el agente sigue mejorando con mas pasos o si ya se estabilizo."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from pvsim_V2.harness_V2 import build_scenarios, evaluate
from evaluar_rl_V2 import policy_factory
from train_V2 import OBS_VARIANTS
scen = build_scenarios(); out = {}
for s in range(3):
    for steps in (250000, 500000, 750000, 1000000):
        p = f"modelos_V2/ppo_5ms_full_s{s}_ckpt_{steps}_steps" if steps < 1000000 else f"modelos_V2/ppo_5ms_full_s{s}"
        if not os.path.exists(p + ".zip"): continue
        res = evaluate(policy_factory(p, 5e-3, OBS_VARIANTS["full"]), 5e-3, scen)
        out[f"s{s}_{steps}"] = {g: float(np.mean([m["eff_energy"] for m in res[g]])) for g in res}
        print(s, steps, out[f"s{s}_{steps}"], flush=True)
json.dump(out, open("resultados_V2/curva_aprendizaje_V2.json", "w"), indent=1)
