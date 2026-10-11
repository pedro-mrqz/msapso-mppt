"""
evaluar_rl_V2.py — Evalua modelos PPO (uno o varios, p. ej. varias semillas) contra el MSAPSO fiel con el arnes comun.
USO:  python3 evaluar_rl_V2.py --wait 5e-3 --models modelos_V2/prueba_200k [mas modelos...] --out resultados_V2/eval_prueba.json
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from stable_baselines3 import PPO, SAC, A2C
from pvsim_V2.gym_env_V2 import decode_action
from pvsim_V2.passrunner_V2 import PolicyController, FEATURES
from pvsim_V2.msapso_V2 import MSAPSOController
from pvsim_V2.harness_V2 import build_scenarios, evaluate, summarize
from train_V2 import OBS_VARIANTS


def policy_factory(model_path, wait, features):
    meta = json.load(open(model_path + ".json")) if os.path.exists(model_path + ".json") else {}
    Algo = {"ppo": PPO, "sac": SAC, "a2c": A2C}[meta.get("algo", "ppo")]
    model = Algo.load(model_path, device="cpu")
    mask = np.array([FEATURES.index(f) for f in features])
    def act_fn(obs):
        a, _ = model.predict(obs, deterministic=True)
        return decode_action(a)
    return lambda: PolicyController(wait, act_fn, mask=mask)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=float, default=5e-3)
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--obs", default="full")
    ap.add_argument("--out", default="resultados_V2/eval_rl.json")
    a = ap.parse_args()
    scen = build_scenarios()
    results = {}
    base = {"MSAPSO fiel (paper)": dict(), "MSAPSO sin reinicio": dict(restart_mode="none")}
    for name, kw in base.items():
        results[name] = evaluate(lambda: MSAPSOController(a.wait, **kw), a.wait, scen)
    for mp in a.models:
        tag = os.path.basename(mp)
        meta = json.load(open(mp + ".json")) if os.path.exists(mp + ".json") else {}
        feats = meta.get("features", OBS_VARIANTS[a.obs])
        results[tag] = evaluate(policy_factory(mp, a.wait, feats), a.wait, scen)
    print(f"{'metodo':34s}" + "".join(f"{g:>28s}" for g in ("static", "pairs (12)", "synth (100)")))
    print(f"{'':34s}" + "".join(f"{'energia% final% reinic':>28s}" for _ in range(3)))
    for name, res in results.items():
        s = summarize(res)
        print(f"{name:34s}" + "".join(f"{s[g]['eff_energy']:11.2f}{s[g]['eff_final']:8.2f}{s[g]['restarts']:7.2f}   " for g in ("static", "pairs", "synth")))
    json.dump(results, open(a.out, "w"), default=float)
