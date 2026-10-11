"""
train_V2.py — Entrenamiento PPO (stable-baselines3) del agente que decide beta y reinicio en MPPTSwarmEnvV2.

USO:
  python3 train_V2.py --wait 5e-3 --seed 0 --timesteps 1000000 --n-envs 4 --tag main_s0
  python3 train_V2.py --wait 5e-3 --seed 0 --obs full|no_disp|no_time|no_drop|minimal ... (ablacion de senales)
Hiperparametros de PPO: los POR DEFECTO de stable-baselines3 (n_steps=2048, batch=64, gamma=0.99, gae_lambda=0.95,
clip=0.2, lr=3e-4), red 64x64 para politica y valor. Solo cambia el numero de pasos, el # de entornos y la semilla.
"""
import argparse, os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from stable_baselines3 import PPO, SAC, A2C
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecMonitor
from stable_baselines3.common.callbacks import CheckpointCallback
from pvsim_V2.gym_env_V2 import MPPTSwarmEnvV2
from pvsim_V2.passrunner_V2 import FEATURES

OBS_VARIANTS = {
    "full":     FEATURES,
    "no_disp":  [f for f in FEATURES if f != "dispersion"],
    "no_time":  [f for f in FEATURES if f != "t_reinicio"],
    "no_drop":  [f for f in FEATURES if f not in ("caida_rel", "dPbest")],      # sin las senales explicitas de caida/subida
    "minimal":  ["P_max", "Pbest", "caida_rel"],
}


def make_env(wait, feats, seed):
    def _init():
        env = MPPTSwarmEnvV2(wait=wait, obs_features=feats)
        env.reset(seed=seed)
        return env
    return _init


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=float, default=5e-3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--timesteps", type=int, default=1_000_000)
    ap.add_argument("--n-envs", type=int, default=4)
    ap.add_argument("--obs", default="full", choices=list(OBS_VARIANTS))
    ap.add_argument("--algo", default="ppo", choices=["ppo", "sac", "a2c"])
    ap.add_argument("--tag", default=None)
    ap.add_argument("--outdir", default="modelos_V2")
    a = ap.parse_args()
    tag = a.tag or f"{a.algo}_w{a.wait*1e3:g}ms_{a.obs}_s{a.seed}"
    os.makedirs(a.outdir, exist_ok=True)
    feats = OBS_VARIANTS[a.obs]
    Vec = DummyVecEnv if a.n_envs == 1 else SubprocVecEnv
    venv = VecMonitor(Vec([make_env(a.wait, feats, 1000 * a.seed + i) for i in range(a.n_envs)]))
    Algo = {"ppo": PPO, "sac": SAC, "a2c": A2C}[a.algo]       # hiperparametros por defecto de stable-baselines3 en los tres
    model = Algo("MlpPolicy", venv, verbose=0, seed=a.seed, policy_kwargs=dict(net_arch=[64, 64]),
                 tensorboard_log=os.path.join(a.outdir, "tb"))
    ck = CheckpointCallback(save_freq=max(a.timesteps // 4 // a.n_envs, 1000), save_path=a.outdir, name_prefix=tag + "_ckpt")
    t0 = time.time()
    model.learn(total_timesteps=a.timesteps, callback=ck, tb_log_name=tag, progress_bar=False)
    model.save(os.path.join(a.outdir, tag))
    json.dump(dict(tag=tag, algo=a.algo, wait=a.wait, seed=a.seed, obs=a.obs, features=feats, timesteps=a.timesteps,
                   n_envs=a.n_envs, seconds=time.time() - t0), open(os.path.join(a.outdir, tag + ".json"), "w"), indent=1)
    print(f"{tag}: listo en {time.time()-t0:.0f} s")
