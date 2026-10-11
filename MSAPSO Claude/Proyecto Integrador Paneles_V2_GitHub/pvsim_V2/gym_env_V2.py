"""
gym_env_V2 — Entorno Gymnasium V2 para MPPT bajo sombreado parcial cambiante.

DIFERENCIAS CLAVE RESPECTO A LA V1 (cada una responde a una observacion del profesor o a una autocritica propia):
  1. La mecanica de una pasada es la del MSAPSO FIEL (7 particulas, barrido alternante, Gbest inmediato, Eq.13), compartida
     con los baselines via PassRunner => comparacion justa.
  2. Observacion SIN informacion privilegiada (ver passrunner_V2.py): sin normalizar por GMPP, sin aviso de cambio de sombra.
  3. Recompensa = ENERGIA entregada en la pasada / energia ideal (P_ceiling * duracion de la pasada). Premia exactamente lo que
     importa (energia cosechada) y castiga de forma natural explorar de mas o reiniciar sin necesidad. P_ceiling solo se usa aqui.
  4. El tiempo de espera NO lo decide el agente (fijo e igual para todos los metodos): se aisla lo que aportan beta y el reinicio.
  5. Episodios que contienen una busqueda inicial, un cambio abrupto de sombra (80 % de los episodios) y la re-busqueda.
Accion (Box [-1,1]^2):  a0 -> beta = 0.05 + 0.90*(a0+1)/2 ;  a1 > 0.8 -> reiniciar el enjambre (umbral alto para que la politica
inicial casi nunca reinicie y aprenda a hacerlo cuando conviene).
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from pvsim_V2.array_model_V2 import SyntheticPVCurve, random_shading_mix
from pvsim_V2.converter_V2 import Plant
from pvsim_V2.passrunner_V2 import PassRunner, FEATURES

N_PART = 7
RESET_THRESH = 0.8


def decode_action(a):
    beta = 0.05 + 0.90 * (float(np.clip(a[0], -1, 1)) + 1.0) / 2.0
    reset = bool(a[1] > RESET_THRESH)
    return beta, reset


class MPPTSwarmEnvV2(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, wait=5e-3, ep_len=130, p_change=0.8, change_range=(20, 70), n_sub=4,
                 obs_features=None, dt=1e-5):
        super().__init__()
        self.wait, self.ep_len, self.p_change, self.change_range = wait, ep_len, p_change, change_range
        self.n_sub, self.dt = n_sub, dt
        names = list(obs_features) if obs_features is not None else list(FEATURES)
        self.obs_idx = np.array([FEATURES.index(n) for n in names])
        self.action_space = spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)
        self.observation_space = spaces.Box(-10.0, 10.0, shape=(len(names),), dtype=np.float32)
        self._rng = np.random.default_rng()
        self.T_pass = N_PART * wait

    def _curve(self):
        return SyntheticPVCurve(random_shading_mix(self._rng, n_sub=self.n_sub))

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        options = options or {}
        self.curve = options.get("curve_a") or self._curve()
        self.curve_b = options.get("curve_b")
        if self.curve_b is None and self._rng.random() < self.p_change:
            self.curve_b = self._curve()
        self.change_at = options.get("change_at")
        if self.change_at is None:
            self.change_at = int(self._rng.integers(*self.change_range)) if self.curve_b is not None else None
        self.plant = Plant(self.curve, dt=self.dt)
        self.runner = PassRunner(self.wait)
        self.runner.start(self.plant)
        self.k = 0
        return self.runner.observe()[self.obs_idx], {}

    def step(self, action):
        if self.change_at is not None and self.k == self.change_at:   # cambio abrupto de sombra, sin aviso al agente
            self.curve = self.curve_b
            self.plant.set_curve(self.curve)
        beta, reset = decode_action(action)
        info = self.runner.do_pass(self.plant, beta, reset)
        reward = info["E"] / (self.curve.P_ceiling * self.T_pass)      # eficiencia de energia de esta pasada
        self.k += 1
        truncated = self.k >= self.ep_len
        info.update(reward_eff=reward, P_ceiling=self.curve.P_ceiling)
        return self.runner.observe()[self.obs_idx], float(reward), False, truncated, info
