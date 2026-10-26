"""
algoritmos_V5.py — Entrenamiento y evaluacion de TODOS los algoritmos sobre la MISMA formulacion corregida (nivel 1, sin GMPP en entrenamiento):
  reinforce : REINFORCE-MLP, recompensa de grupo 'gain', baseline de valor, sigma fija (reinforce_nn_V5)
  ppo       : PPO (sb3), episodio de 1 paso, recompensa 'gain', sigma FIJA (log_std congelada)
  sac       : SAC (sb3), episodio de 1 paso, recompensa 'gain'
  ddpg      : DDPG (sb3), politica determinista + ruido gaussiano de exploracion, recompensa 'gain'
  arbol     : arbol de decision DENTRO del bucle de RL, RECALCULADO en cada iteracion (propuesta del profesor):
              en cada iteracion se muestrean K acciones alrededor de la propuesta actual, se mide la potencia y el arbol se REAJUSTA con
              la mejor accion MEDIDA de cada patron (si mejora al barrido); sigma decrece entre iteraciones. Solo potencias medidas.
Evaluacion comun: se mide el barrido de N puntos, el modelo propone mu y se toman K muestras N(mu, sigma_eval^2); se elige la mejor LEIDA.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch
from pvsim_V5.medicion_V5 import ISC_NOM, I_MIN, I_MAX, P_NOM, grid_currents, scan, metrics_from_plant, action_to_current, current_to_action
from pvsim_V5.static_plant_V5 import StaticPlant
from pvsim_V5.bandit_env_V5 import MPPTBanditEnvV5, IGRID
from reinforce_nn_V5 import build_pool, table_lookup, sigma_action, train as train_reinforce

SIGMA_EVAL = 0.05


def make_obs_all(pool, N):
    """Potencias del barrido ascendente (N corrientes uniformes) para cada curva del banco, / 250 W."""
    return np.stack([table_lookup(pool, np.tile(i, (pool.shape[0], 1)))[:, 0] for i in grid_currents(N)], axis=1) / P_NOM


def eval_mu(mu_fn, N, K, sigma, curves, mode="gauss", reps=1, noise_w=0.0, seed=11):
    """mu_fn(obs_vector) -> accion en [-1,1]. mode 'gauss': N + K muestras N(mu, sigma); 'mu': N + 1 en mu."""
    sa = sigma_action(sigma); out = []
    for k, c in enumerate(curves):
        for r in range(reps):
            rng = np.random.default_rng(seed + 1000 * k + r)
            pl = StaticPlant(c, noise_w=noise_w, rng=rng)
            _, P = scan(pl, N)
            mu = float(np.clip(mu_fn(np.clip(P / P_NOM, 0, 10).astype(np.float32)), -1, 1))
            if mode == "mu":
                pl.run(1.0, action_to_current(mu))
            else:
                for _ in range(K):
                    pl.run(1.0, action_to_current(mu + sa * rng.normal()))
            out.append(metrics_from_plant(pl, c))
    return {m: float(np.nanmean([o[m] for o in out])) for m in out[0]}


# ------------------------------------------------------------------ arbol dentro del RL
class TreeMu:
    def __init__(self, tree, init_fn):
        self.tree, self.init_fn = tree, init_fn

    def __call__(self, obs):
        return float(self.tree.predict(obs[None])[0]) if self.tree is not None else float(self.init_fn(obs[None])[0])


def _init_mu(obs):                                     # propuesta inicial: la corriente del mejor punto del barrido (potencia MEDIDA)
    N = obs.shape[1]; return current_to_action(grid_currents(N)[np.argmax(obs, axis=1)])


def train_tree(N, pool, obs_all, iters=15, B=4000, K=10, sigma0=0.15, sigma1=0.04, depth=10, min_leaf=8, seed=0, noise_w=0.0):
    from sklearn.tree import DecisionTreeRegressor
    rng = np.random.default_rng(seed); tree = None
    for t in range(iters):
        sig = sigma0 + (sigma1 - sigma0) * t / max(iters - 1, 1); sa = sigma_action(sig)
        idx = rng.integers(0, pool.shape[0], B); obs = obs_all[idx] + (rng.normal(0, noise_w, (B, obs_all.shape[1])) / P_NOM if noise_w > 0 else 0.0)
        mu = _init_mu(obs) if tree is None else np.clip(tree.predict(obs), -1, 1)
        a = np.clip(mu[:, None] + sa * rng.normal(size=(B, K)), -1, 1)
        I = I_MIN + 0.5 * (a + 1.0) * (I_MAX - I_MIN)
        Pn = table_lookup(pool[idx], I) / P_NOM + (rng.normal(0, noise_w, (B, K)) / P_NOM if noise_w > 0 else 0.0)
        j = np.argmax(Pn, axis=1); best_a = a[np.arange(B), j]; improved = Pn.max(axis=1) > obs.max(axis=1)
        target = np.where(improved, best_a, mu)         # solo se mueve el objetivo si la muestra MEJORA al barrido (potencia medida)
        tree = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=min_leaf, random_state=seed).fit(obs, target)   # se RECALCULA en cada iteracion
    return TreeMu(tree, _init_mu)


# ------------------------------------------------------------------ algoritmos de stable-baselines3
def train_sb3(algo, N, pool, obs_all, steps, seed, noise_w=0.0):
    from stable_baselines3 import PPO, SAC, DDPG
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.noise import NormalActionNoise
    sa = sigma_action(SIGMA_EVAL)
    if algo == "ppo":
        venv = DummyVecEnv([lambda i=i: MPPTBanditEnvV5(N, pool, obs_all, "gain", noise_w, seed=seed * 100 + i) for i in range(8)])
        m = PPO("MlpPolicy", venv, seed=seed, gamma=0.0, gae_lambda=0.0, n_steps=256, batch_size=256, policy_kwargs=dict(net_arch=[64, 64]), verbose=0)
        m.policy.log_std.data.fill_(float(np.log(sa))); m.policy.log_std.requires_grad_(False)      # sigma FIJA
    else:
        env = DummyVecEnv([lambda: MPPTBanditEnvV5(N, pool, obs_all, "gain", noise_w, seed=seed)])
        kw = dict(policy_kwargs=dict(net_arch=[64, 64]), learning_starts=2000, seed=seed, verbose=0, gamma=0.0)
        if algo == "sac":
            m = SAC("MlpPolicy", env, **kw)
        else:
            m = DDPG("MlpPolicy", env, action_noise=NormalActionNoise(np.zeros(1), sa * np.ones(1)), **kw)
    m.learn(steps)
    return m


def sb3_mu(model):
    return lambda obs: float(model.predict(obs, deterministic=True)[0][0])


def reinforce_mu(pol):
    return lambda obs: float(pol(torch.tensor(obs, dtype=torch.float32)[None])[0])
