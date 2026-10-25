"""
baselines_nivel1_V4.py — Referencias (sin aprendizaje) en el NIVEL 1 (potencia estatica, sin dinamica del convertidor).
Cuenta MEDICIONES (iteraciones), la metrica prioritaria del profesor, y la energia en unidades de iteracion.

Metodos:
  MSAPSO fiel (Isc real)   Fig. 6 del paper: 7 particulas, beta 0.1->0.95, t_max=25 (175 mediciones). Semilla con la Isc REAL del patron.
  MSAPSO fiel (Isc nom.)   igual, pero sembrado con la Isc NOMINAL (como el rango del profesor) => comparacion justa con la V4.
  regla simple (nom.)      beta=0.95 fijo, t_max=5 (35 mediciones). [POST-HOC en la V2]
  mejor-de-N               N puntos uniformes y se elige el mejor (sin refinar): cota inferior sin aprendizaje.
  mejor-de-N + gauss.      mejor-de-N, luego K muestras N(mejor, sigma^2) y se elige el mejor: lo que haria la politica
                           SIN haber aprendido nada (control del aporte real del modelo).
USO: python3 baselines_nivel1_V4.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from pvsim_V4.pvcurve_V4 import load_case
from pvsim_V4.array_model_V4 import SyntheticPVCurve, random_shading_mix
from pvsim_V4.msapso_V4 import Swarm
from pvsim_V4.static_plant_V4 import StaticPlant
from pvsim_V4.medicion_V4 import (ISC_NOM, I_MIN, I_MAX, W_ENERGIA, scan, metrics_from_plant)


def run_msapso(plant, curve, isc_seed, beta_fn, t_max):
    sw = Swarm(first_pass="ascending")
    sw.restart(isc_seed, first=True)
    for _ in range(t_max):
        sw.sweep(plant, 1.0)
        sw.update(beta_fn(sw.t))


def paper_beta(t, t_max=25, bmin=0.1, bmax=0.95):
    return bmin + (t / t_max) * (bmax - bmin)             # Eq. (14)


def m_msapso_real(plant, curve, rng):  run_msapso(plant, curve, curve.Isc, paper_beta, 25)
def m_msapso_nom(plant, curve, rng):   run_msapso(plant, curve, ISC_NOM, paper_beta, 25)
def m_regla_simple(plant, curve, rng): run_msapso(plant, curve, ISC_NOM, lambda t: 0.95, 5)


def make_best_of_n(N, K=0, sigma_frac=0.05):
    def f(plant, curve, rng):
        I, P = scan(plant, N)
        mu = I[int(np.argmax(P))]
        for _ in range(K):
            plant.run(1.0, float(np.clip(rng.normal(mu, sigma_frac * ISC_NOM), I_MIN, I_MAX)))
    return f


def scenarios(n_synth=100, seed=2026):
    rng = np.random.default_rng(seed)
    real = [load_case(i) for i in range(4)]
    synth = [SyntheticPVCurve(random_shading_mix(rng)) for _ in range(n_synth)]
    return real, synth


def evaluate(method, curves, noise_w=0.0, seed=7, reps=1):
    out = []
    for k, c in enumerate(curves):
        for r in range(reps):
            rng = np.random.default_rng(seed + 1000 * k + r)
            pl = StaticPlant(c, noise_w=noise_w, rng=rng)
            method(pl, c, rng)
            out.append(metrics_from_plant(pl, c))
    return {k: float(np.nanmean([o[k] for o in out])) for k in out[0]} | {"n99_alcanzado": int(np.isfinite([o["n99"] for o in out]).sum()), "n": len(out)}


METHODS = {
    "MSAPSO fiel (Isc real)": m_msapso_real,
    "MSAPSO fiel (Isc nominal)": m_msapso_nom,
    "regla simple b=0.95,t_max=5 (nom.)": m_regla_simple,
    "mejor-de-7": make_best_of_n(7),
    "mejor-de-7 + 5 gauss. (s=0.05)": make_best_of_n(7, 5, 0.05),
    "mejor-de-10 + 5 gauss. (s=0.05)": make_best_of_n(10, 5, 0.05),
    "mejor-de-20": make_best_of_n(20),
    "mejor-de-20 + 5 gauss. (s=0.05)": make_best_of_n(20, 5, 0.05),
}

if __name__ == "__main__":
    real, synth = scenarios()
    res, lines = {}, []
    def P(s=""):
        print(s); lines.append(s)
    for noise in (0.0, 1.0, 2.0):
        P(f"\n=== NIVEL 1 (estatico), ruido de medicion sigma = {noise:g} W | {W_ENERGIA} mediciones de ventana de energia ===")
        P(f"{'metodo':40s} | {'REALES (4): n_meas  n99  efi_fin  energia':44s} | {'SINTETICOS (100): n_meas  n99  efi_fin  energia'}")
        for name, m in METHODS.items():
            a = evaluate(m, real, noise, reps=20 if noise > 0 else 1)
            b = evaluate(m, synth, noise, reps=3 if noise > 0 else 1)
            res[f"{name}|{noise:g}"] = dict(real=a, synth=b)
            P(f"{name:40s} | {a['n_meas']:6.0f} {a['n99']:6.1f} {a['eff_final']:7.2f} {a['eff_energy']:8.2f}      | {b['n_meas']:6.0f} {b['n99']:6.1f} {b['eff_final']:7.2f} {b['eff_energy']:8.2f}")
    json.dump(res, open("resultados_V4/baselines_nivel1_V4.json", "w"), indent=1)
    open("resultados_V4/baselines_nivel1_V4.txt", "w").write("\n".join(lines))
