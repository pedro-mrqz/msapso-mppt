"""
campana_V14.py — Retroceso de corriente (backoff) en operacion dinamica. USO:
  python3 campana_V14.py val   -> escenarios 600-1199 (VALIDACION), rejilla b in {0, .02, .04, .06, .08}, elige b por metodo -> resultados_V14/backoff_validacion_V14.json|txt
  python3 campana_V14.py test  -> escenarios 0-599 (PRUEBA), b congelado (+ b = 0) -> resultados_V14/backoff_prueba_V14.json|txt
  python3 campana_V14.py conf  -> escenarios 1200-2399 (CONFIRMACION, nunca usados antes), mismo b congelado -> resultados_V14/backoff_confirmacion_V14.json|txt
"""
import json, pickle, sys
from multiprocessing import Pool
from mlp_cem_V14 import Cfg as CfgL, make_mlp_cem
from msapso_cem_V14 import Cfg as CfgM, make_msapso_cem
from entorno_V14 import *

S12 = json.load(open("resultados_V14/seleccion_V12.json")); V11 = json.load(open("resultados_V14/seleccion_V11.json")); MODEL = pickle.load(open("resultados_V14/mlp_elegido_V11.pkl", "rb"))
NAMES = ["MSAPSO completo", "V7 (parada)", "MLP + CEM", "corto + CEM (<=40)", "corto + CEM (principal)"]
def methods():
    return {NAMES[0]: make_msapso_early(Rule("none")), NAMES[1]: make_msapso_early(Rule("disp", delta=0.02, t_min=3)), NAMES[2]: make_mlp_cem(MODEL, CfgL(**V11["mlp_cem"]["cfg"])),
            NAMES[3]: make_msapso_cem(CfgM(**S12["le40"]["cfg"])), NAMES[4]: make_msapso_cem(CfgM(**S12["principal"]["cfg"]))}
def task(a):
    idx, bos = a; meta, curves, bounds, total = make_scenario(idx); M = methods(); out = dict(idx=idx, regimen=meta["regimen"])
    for n, bs in bos.items():
        for b in bs:
            e, fin, nr, ns = run_ops(M[n], curves, bounds, meta["wait"], total, seed=idx, noise_w=meta["ruido"], backoff=b); out[f"{n}|{b}"] = [e, fin, nr]
    return out
def boot(d, B=3000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
