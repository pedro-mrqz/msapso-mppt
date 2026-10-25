"""Pruebas de humo del entorno V4: contrato Gymnasium, ruido, nivel dinamico y politicas de referencia (aleatoria / oraculo)."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from stable_baselines3.common.env_checker import check_env
from pvsim_V4.gym_env_V4 import MPPTSampleEnvV4
from pvsim_V4.medicion_V4 import current_to_action
from pvsim_V4.pvcurve_V4 import load_case

for level, wait in (("static", 5e-4), ("dynamic", 5e-4), ("dynamic", 5e-3)):
    env = MPPTSampleEnvV4(N=7, K=5, level=level, wait=wait)
    check_env(env, warn=True)
    rng = np.random.default_rng(0)
    t0 = time.time(); R, effs = [], {"azar": [], "oraculo": []}
    for pol in ("azar", "oraculo"):
        for ep in range(100 if level == "static" else 20):
            o, _ = env.reset(seed=ep)
            done = False
            while not done:
                a = rng.uniform(-1, 1, 1) if pol == "azar" else np.array([current_to_action(env.curve.I_gmpp)])
                o, r, done, _, info = env.step(a)
            effs[pol].append(info["metrics"]["eff_final"])
    print(f"{level:8s} wait={wait*1e3:g} ms | eficiencia final media: azar {np.mean(effs['azar']):.1f} % | oraculo (propone el GMPP real) {np.mean(effs['oraculo']):.1f} % | {time.time()-t0:.1f} s")
print("OK: entorno valido en nivel estatico y dinamico")
