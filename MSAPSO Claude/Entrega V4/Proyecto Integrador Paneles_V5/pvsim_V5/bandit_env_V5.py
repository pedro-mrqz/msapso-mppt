"""
bandit_env_V5 — Entorno Gymnasium de UN PASO (bandido contextual) para PPO / SAC / DDPG en la formulacion corregida.
Episodio = un patron de sombra: observacion = N potencias medidas / 250 W (barrido ascendente); accion = corriente a probar;
recompensa (reward="gain") = max(0, P_medida(a) - mejor punto del barrido) / 250 W = cuanto MEJORA lo que ya se conocia (solo potencias medidas;
sin GMPP). reward="abs" = P_medida/250 (la de la V4). Usa un banco precalculado de curvas (tablas P(I)) para que cada episodio sea instantaneo.
El muestreo de K puntos aledanos se hace al EVALUAR (mu + gaussiana) o lo hace la politica (PPO/SAC); el entrenamiento premia que la
accion propuesta supere al mejor punto del barrido.
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from pvsim_V5.medicion_V5 import ISC_NOM, I_MIN, I_MAX, P_NOM, grid_currents, action_to_current

TABLE_PTS = 600
IGRID = np.linspace(0.0, ISC_NOM, TABLE_PTS)


class MPPTBanditEnvV5(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, N, pool, obs_all, reward="gain", noise_w=0.0, seed=0):
        super().__init__()
        self.N, self.pool, self.obs_all, self.reward_mode, self.noise_w = N, pool, obs_all, reward, noise_w
        self.action_space = spaces.Box(-1.0, 1.0, shape=(1,), dtype=np.float32)
        self.observation_space = spaces.Box(0.0, 10.0, shape=(N,), dtype=np.float32)
        self._rng = np.random.default_rng(seed)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self.i = int(self._rng.integers(0, self.pool.shape[0]))
        o = self.obs_all[self.i] + (self._rng.normal(0, self.noise_w, self.N) / P_NOM if self.noise_w > 0 else 0.0)
        self.obs = np.clip(o, 0.0, 10.0).astype(np.float32)
        return self.obs.copy(), {}

    def step(self, action):
        I = action_to_current(float(np.asarray(action).reshape(-1)[0]))
        P = float(np.interp(I, IGRID, self.pool[self.i], right=0.0)) + (self._rng.normal(0, self.noise_w) if self.noise_w > 0 else 0.0)
        Pn = P / P_NOM
        r = max(0.0, Pn - float(self.obs.max())) if self.reward_mode == "gain" else Pn
        return self.obs.copy(), r, True, False, {}
