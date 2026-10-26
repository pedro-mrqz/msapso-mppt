"""Control sin aprendizaje MAS FUERTE: del barrido de N puntos se ajusta una parabola a los 3 puntos vecinos del mejor (interpolacion
parabolica) y se toma su vertice como centro; luego K muestras gaussianas alrededor (y el mejor medido). Es lo que haria un competidor sin RL.
Se compara con 'mejor de N + K gauss.' (control simple) y con el RL corregido (reward gain, baseline value, sigma 0.05, K_train = K)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from pvsim_V5.static_plant_V5 import StaticPlant
from pvsim_V5.medicion_V5 import *
from baselines_nivel1_V5 import scenarios, make_best_of_n, evaluate
from reinforce_nn_V5 import train, eval_policy, build_pool


def make_parabolic(N, K, sigma_frac=0.05):
    def f(plant, curve, rng):
        I, P = scan(plant, N); j = int(np.argmax(P)); mu = I[j]
        if 0 < j < N - 1:
            y0, y1, y2 = P[j - 1], P[j], P[j + 1]; den = y0 - 2 * y1 + y2
            if den < -1e-9:
                mu = I[j] + 0.5 * (I[1] - I[0]) * (y0 - y2) / den
        mu = float(np.clip(mu, I_MIN, I_MAX))
        for _ in range(K):
            plant.run(1.0, float(np.clip(rng.normal(mu, sigma_frac * ISC_NOM), I_MIN, I_MAX)))
    return f

if __name__ == "__main__":
    real, synth = scenarios(); pool = build_pool(6000, seed=0)
    print("N  K  med | simple fin  ener | parabolico fin  ener | RL corregido fin  ener   [100 sinteticos | (reales: parabolico / RL)]")
    for N, K in ((3, 3), (4, 3), (5, 3), (5, 5), (7, 3), (7, 5), (10, 5)):
        a = evaluate(make_best_of_n(N, K, 0.05), synth); b = evaluate(make_parabolic(N, K), synth); br = evaluate(make_parabolic(N, K), real)
        rl, rr = [], []
        for seed in range(3):
            pol = train(N, K, 0.05, None, "value", "gain", 4000, seed=seed, pool=pool)
            s = eval_policy(pol, N, K, 0.05, synth, "stoch", reps=3); r = eval_policy(pol, N, K, 0.05, real, "stoch", reps=5)
            rl.append((s["eff_final"], s["eff_energy"])); rr.append((r["eff_final"], r["eff_energy"]))
        rl, rr = np.mean(rl, 0), np.mean(rr, 0)
        print(f"{N:2d} {K:2d} {N+K:3d} | {a['eff_final']:10.2f} {a['eff_energy']:5.2f} | {b['eff_final']:13.2f} {b['eff_energy']:5.2f} | {rl[0]:12.2f} {rl[1]:5.2f}   | reales: parab {br['eff_final']:.1f}/{br['eff_energy']:.1f}  RL {rr[0]:.1f}/{rr[1]:.1f}", flush=True)
