"""
gym_env_V4 — Entorno Gymnasium de la V4: «proponer el maximo a partir de N potencias medidas» (propuesta del profesor).

Un EPISODIO = un patron de sombra desconocido (curva sintetica al azar, 4 sub-strings):
  1. El entorno mide N potencias en N corrientes uniformes y ascendentes (rango fijado con la Isc NOMINAL). Eso es la OBSERVACION
     (constante durante el episodio): vector de N potencias / 250 W.
  2. El agente propone una corriente (accion en [-1,1] -> [I_MIN, I_MAX]). Con politica gaussiana (PPO/SAC/REINFORCE) cada
     paso es una muestra de N(mu(obs), sigma^2): el «muestreo de puntos aledanos» es PARTE de policy gradients, no una etapa aparte.
  3. Se hacen K pasos (K muestras). Recompensa de cada paso = potencia MEDIDA en la corriente propuesta / 250 W.
Reglas anti-fuga (profesor): la recompensa y la observacion usan SOLO potencias medidas; el GMPP/P_ceiling NO se usan en
entrenamiento (solo en las metricas de evaluacion, que salen en `info['metrics']` al terminar).
Costo en mediciones por episodio = N + K  (el MSAPSO del paper usa 175).
Como cada episodio es de un solo contexto con K muestras independientes, es un problema de bandido contextual: usar gamma = 0.
level="static": potencia estatica P(I) (nivel 1, Colab del profesor). level="dynamic": simulador con Boost + Super-Twisting (nivel 2).
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from pvsim_V4.array_model_V4 import SyntheticPVCurve, random_shading_mix
from pvsim_V4.static_plant_V4 import StaticPlant, DynamicPlantLogged
from pvsim_V4.medicion_V4 import grid_currents, action_to_current, metrics_from_plant, P_NOM


class MPPTSampleEnvV4(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, N=7, K=5, noise_w=0.0, level="static", wait=5e-4, n_sub=4):
        super().__init__()
        self.N, self.K, self.noise_w, self.level, self.wait, self.n_sub = N, K, noise_w, level, wait, n_sub
        self.action_space = spaces.Box(-1.0, 1.0, shape=(1,), dtype=np.float32)
        self.observation_space = spaces.Box(0.0, 10.0, shape=(N,), dtype=np.float32)
        self._rng = np.random.default_rng()

    def _plant(self, curve):
        if self.level == "static":
            return StaticPlant(curve, self.noise_w, rng=self._rng)
        return DynamicPlantLogged(curve, self.wait, self.noise_w, rng=self._rng)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        options = options or {}
        self.curve = options.get("curve") or SyntheticPVCurve(random_shading_mix(self._rng, n_sub=self.n_sub))
        self.plant = self._plant(self.curve)
        P = np.array([self.plant.run(1.0, i)[0] for i in grid_currents(self.N)])        # barrido ascendente de N puntos
        self.obs = np.clip(P / P_NOM, 0.0, 10.0).astype(np.float32)
        self.k = 0
        return self.obs.copy(), {}

    def step(self, action):
        I = action_to_current(float(np.asarray(action).reshape(-1)[0]))
        Pm, _ = self.plant.run(1.0, I)
        self.k += 1
        done = self.k >= self.K
        info = {"I": I}
        if done:
            info["metrics"] = metrics_from_plant(self.plant, self.curve)
        return self.obs.copy(), float(Pm / P_NOM), done, False, info
