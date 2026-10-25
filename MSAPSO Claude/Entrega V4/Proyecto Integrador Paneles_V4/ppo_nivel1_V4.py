"""
ppo_nivel1_V4.py — PPO (stable-baselines3) sobre MPPTSampleEnvV4 en el NIVEL 1 (potencia estatica).
Bandido contextual: gamma = 0 (cada paso es una muestra independiente del mismo patron). MLP 64x64. sigma inicial pequena
(log_std_init = -2  =>  sigma = 0.135 en unidades de accion, ~0.057 de la Isc nominal); PPO aprende despues su propia sigma.
Recompensa = potencia MEDIDA / 250 W (sin GMPP). Evaluacion sobre reales (4) y sinteticos (100) nunca vistos.
USO:  python3 ppo_nivel1_V4.py --N 7 --K 5 --steps 200000 --seed 0
"""
import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
from pvsim_V4.gym_env_V4 import MPPTSampleEnvV4
from pvsim_V4.static_plant_V4 import StaticPlant
from pvsim_V4.medicion_V4 import scan, metrics_from_plant, action_to_current, P_NOM


def eval_sb3(model, N, K, curves, mode="stoch", noise_w=0.0, seed=11, reps=1):
    out = []
    for k, c in enumerate(curves):
        for r in range(reps):
            rng = np.random.default_rng(seed + 1000 * k + r)
            pl = StaticPlant(c, noise_w=noise_w, rng=rng)
            _, P = scan(pl, N)
            obs = np.clip(P / P_NOM, 0, 10).astype(np.float32)
            if mode == "mu":
                pl.run(1.0, action_to_current(model.predict(obs, deterministic=True)[0][0]))
            else:
                for _ in range(K):
                    pl.run(1.0, action_to_current(model.predict(obs, deterministic=False)[0][0]))
            out.append(metrics_from_plant(pl, c))
    return {m: float(np.nanmean([o[m] for o in out])) for m in out[0]}


if __name__ == "__main__":
    from baselines_nivel1_V4 import scenarios
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=7); ap.add_argument("--K", type=int, default=5)
    ap.add_argument("--steps", type=int, default=200000); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--noise", type=float, default=0.0); ap.add_argument("--log-std", type=float, default=-2.0)
    ap.add_argument("--tag", default=None); ap.add_argument("--ent", type=float, default=0.0)
    a = ap.parse_args()
    tag = a.tag or f"ppo_N{a.N}_K{a.K}_s{a.seed}"
    venv = VecMonitor(DummyVecEnv([lambda i=i: MPPTSampleEnvV4(N=a.N, K=a.K, noise_w=a.noise) for i in range(8)]))
    venv.seed(a.seed)
    model = PPO("MlpPolicy", venv, seed=a.seed, gamma=0.0, gae_lambda=0.0, n_steps=256, batch_size=256, verbose=0, ent_coef=a.ent,
                policy_kwargs=dict(net_arch=[64, 64], log_std_init=a.log_std))
    t0 = time.time(); model.learn(a.steps)
    os.makedirs("modelos_V4", exist_ok=True); model.save(f"modelos_V4/{tag}")
    real, synth = scenarios()
    res = dict(tag=tag, steps=a.steps, seconds=time.time() - t0, sigma_aprendida=float(np.exp(model.policy.log_std.detach().numpy()).mean()))
    for mode in ("stoch", "mu"):
        r = eval_sb3(model, a.N, a.K, real, mode, a.noise, reps=5); s = eval_sb3(model, a.N, a.K, synth, mode, a.noise, reps=3)
        res[mode] = dict(real=r, synth=s)
        print(f"{tag} {mode:5s} | reales: n={r['n_meas']:.0f} fin {r['eff_final']:.2f} ener {r['eff_energy']:.2f} | sint: n={s['n_meas']:.0f} fin {s['eff_final']:.2f} ener {s['eff_energy']:.2f} | sigma={res['sigma_aprendida']:.3f} | {res['seconds']:.0f} s", flush=True)
    json.dump(res, open(f"resultados_V4/{tag}.json", "w"), indent=1)
