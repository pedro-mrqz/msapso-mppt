"""
passrunner_V2 — Mecanica de UNA pasada del enjambre, compartida por el entorno de RL y por los controladores
que se evaluan con el mismo arnes (una sola fuente de verdad: lo que aprende el agente y lo que se mide son identicos).

Observacion del agente (SOLO senales medibles en un controlador real; sin informacion privilegiada):
  La V1 normalizaba la potencia por el GMPP real (desconocido para un controlador) y avisaba directamente del cambio de
  sombra. Aqui NO: la potencia se expresa en unidades de 100 W (escala del panel) y el cambio de sombra solo se puede
  inferir de la potencia medida. El GMPP real y P_ceiling se usan UNICAMENTE en la recompensa durante el entrenamiento.
    f0  P_max_pasada / 100 W        mejor potencia medida en la ultima pasada
    f1  P_media_pasada / 100 W      potencia media de la ultima pasada
    f2  Pbest / 100 W               mejor potencia almacenada desde el (re)inicio
    f3  1 - P_max_pasada / Pbest    caida relativa respecto al mejor guardado (senal de cambio de sombra), en [0,1]
    f4  dispersion de particulas    std(x)/Isc  (cuan colapsado esta el enjambre = historial acumulado de beta)
    f5  pasadas desde el reinicio / 25  (recortado a 3)
    f6  beta usado en la pasada anterior (memoria propia del agente)
    f7  (Pbest - Pbest_anterior) / 100 W   cuanto subio Pbest en la ultima pasada
"""
import numpy as np
from pvsim_V2.msapso_V2 import Swarm

P_SCALE = 100.0
FEATURES = ["P_max", "P_media", "Pbest", "caida_rel", "dispersion", "t_reinicio", "beta_prev", "dPbest"]


class PassRunner:
    def __init__(self, wait, first_pass="ascending"):
        self.wait = wait
        self.sw = Swarm(first_pass=first_pass)
        self.started = False
        self.since_reset = 0
        self.last_beta = 0.5
        self.last = dict(P_max=0.0, P_mean=0.0, dPbest=0.0)

    def start(self, plant):
        self.sw.restart(plant.curve.Isc, first=True)
        self.started = True
        self.since_reset = 0
        self.last_beta = 0.5
        self.last = dict(P_max=0.0, P_mean=0.0, dPbest=0.0)

    def observe(self):
        sw, L = self.sw, self.last
        drop = 0.0 if sw.Pbest <= 1e-9 else float(np.clip(1.0 - L["P_max"] / sw.Pbest, 0.0, 1.0))
        return np.array([L["P_max"] / P_SCALE, L["P_mean"] / P_SCALE, sw.Pbest / P_SCALE, drop,
                         sw.dispersion(), min(self.since_reset / 25.0, 3.0), self.last_beta,
                         L["dPbest"] / P_SCALE], dtype=np.float32)

    def do_pass(self, plant, beta, reset):
        """Ejecuta una pasada (7 ventanas de `wait`) con el paso `beta` elegido y, opcionalmente, reiniciando antes."""
        if not self.started:
            self.start(plant)
        sw = self.sw
        if reset:
            sw.restart(plant.curve.Isc)
            self.since_reset = 0
        Pbest_before = sw.Pbest
        E, Ps = sw.sweep(plant, self.wait)
        disp = sw.dispersion()
        sw.update(beta)
        self.since_reset += 1
        self.last_beta = float(beta)
        self.last = dict(P_max=float(Ps.max()), P_mean=float(Ps.mean()), dPbest=float(sw.Pbest - Pbest_before))
        return dict(E=E, P_end=float(Ps[-1]), P_max=float(Ps.max()), beta=float(beta), mode="search", disp=disp,
                    t=self.since_reset, Gbest=sw.Gbest, Pbest=sw.Pbest, restart=bool(reset))


class PolicyController:
    """Adaptador: un 'agente' (funcion obs -> (beta, reset)) con la misma interfaz .step(plant) que MSAPSOController,
    para evaluarlo con el MISMO arnes (run_scenario / segment_metrics) que los baselines."""

    def __init__(self, wait, act_fn, mask=None):
        self.runner = PassRunner(wait)
        self.act_fn = act_fn
        self.mask = mask                      # indices de features visibles (para la ablacion)
        self.sw = self.runner.sw

    def step(self, plant):
        r = self.runner
        if not r.started:
            r.start(plant)
        obs = r.observe()
        if self.mask is not None:
            obs = obs[self.mask]
        beta, reset = self.act_fn(obs)
        return r.do_pass(plant, beta, reset)
