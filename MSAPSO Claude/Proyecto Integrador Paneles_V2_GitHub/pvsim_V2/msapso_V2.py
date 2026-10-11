"""
msapso_V2 — MSAPSO_I FIEL a la Figura 6 del paper + ejecutor de escenarios y metricas.

Especificacion (leida de la Fig. 6 como imagen, p. 11 del paper; aclaraciones del profesor):
  * Valores:  beta_min=0.1, beta_max=0.95, t_max=25, t_wait=0.5 ms
  * 7 particulas, posiciones iniciales  x_i = Isc * [0.95 0.8 0.65 0.5 0.3 0.15 0.1]   (corrientes de referencia)
  * "Pasada positiva" y "pasada negativa" ALTERNADAS: un conjunto de valores se prueba de menor a mayor corriente,
    el siguiente de mayor a menor, y asi sucesivamente (escalera; evita el salto grande de regreso).
  * Cada candidato se aplica al convertidor durante t_wait y se mide Ppv. Si Ppv >= Pbest -> Pbest=Ppv, Gbest=Ipv
    (Gbest se actualiza AL INSTANTE, dentro del barrido; Ipv = corriente medida).
  * Al terminar cada pasada las posiciones se recalculan con la Eq.(13) determinista:  x <- x + beta*(Gbest - x),
    con beta de la Eq.(14): beta_t = beta_min + (t/t_max)(beta_max - beta_min).
  * Tras t_max pasadas: el convertidor se fija en Gbest ("park") y se mide Ppv; si |Pbest - Ppv| >= 5 W se REINICIA
    todo (Pbest=0, Gbest=0, posiciones iniciales, t=1).
Variantes para comparacion (declaradas en la bitacora): restart_mode = "paper" | "early" | "none";
  first_pass = "ascending" (dicho por el profesor) | "descending" (orden literal de la lista en la Fig. 6).

Unidad de tiempo del entorno: un "paso" = 7 ventanas de t_wait (el tiempo de una pasada completa). Una pasada de barrido
y un paso de mantenimiento (park) duran lo mismo, de modo que la energia de todos los metodos se compara en la misma base.
"""
import numpy as np
from pvsim_V2.converter_V2 import Plant

INIT_FRACS = (0.95, 0.80, 0.65, 0.50, 0.30, 0.15, 0.10)
N_PART = 7


class Swarm:
    """Estado del enjambre y operaciones elementales."""

    def __init__(self, first_pass="ascending", fracs=INIT_FRACS, gbest_from="measured", alternate=True):
        self.alternate = alternate            # False = siempre ascendente (como la V1; solo para ablacion)
        self.first_pass = first_pass
        self.fracs = np.array(sorted(fracs), dtype=float)   # ascendente; el orden de evaluacion lo fija `direction`
        self.gbest_from = gbest_from
        self.n = len(fracs)
        self.n_restarts = 0
        self.Isc = 1.0
        self.restart(1.0, first=True)

    def restart(self, Isc, first=False):
        """Bloque 'Initial Value / Set Initial Particle Position' de la Fig. 6."""
        self.Isc = float(Isc)                 # el algoritmo siembra con Isc (se re-mide al reiniciar)
        self.x = self.Isc * self.fracs.copy()
        self.Pbest = 0.0
        self.Gbest = 0.0
        self.direction = self.first_pass
        self.t = 1                            # contador de pasadas desde el (re)inicio
        if not first:
            self.n_restarts += 1

    def sweep(self, plant, wait):
        """Una pasada: cada particula se aplica durante `wait`, de menor a mayor o de mayor a menor corriente."""
        order = np.argsort(self.x)
        if self.direction == "descending":
            order = order[::-1]
        E, Ps = 0.0, []
        for i in order:
            P, e = plant.run(wait, self.x[i])
            E += e
            Ps.append(P)
            if P >= self.Pbest:               # "Ppv >= Pbest -> Pbest = Ppv, Gbest = Ipv"
                self.Pbest = P
                self.Gbest = plant.Ipv if self.gbest_from == "measured" else float(self.x[i])
        return E, np.array(Ps)

    def update(self, beta):
        """Eq.(13): x <- x + beta (Gbest - x). Despues alterna la direccion del siguiente barrido."""
        self.x = np.clip(self.x + beta * (self.Gbest - self.x), 0.0, self.Isc)
        if self.alternate:
            self.direction = "descending" if self.direction == "ascending" else "ascending"
        self.t += 1

    def hold(self, plant, wait, n=None):
        """Convertidor fijo en Gbest durante una pasada de tiempo (n ventanas). Devuelve (E, P_final)."""
        n = self.n if n is None else n
        P, E = plant.run(n * wait, self.Gbest)
        return E, P

    def dispersion(self):
        return float(np.std(self.x) / max(self.Isc, 1e-9))


class MSAPSOController:
    """Controlador MSAPSO_I (maquina de estados de la Fig. 6). `step(plant)` ejecuta un paso de tiempo."""

    def __init__(self, wait, beta_min=0.1, beta_max=0.95, t_max=25, restart_mode="paper", thresh=5.0,
                 first_pass="ascending", gbest_from="measured", beta_fn=None, alternate=True, fracs=INIT_FRACS):
        self.wait, self.beta_min, self.beta_max, self.t_max = wait, beta_min, beta_max, t_max
        self.restart_mode, self.thresh = restart_mode, thresh
        self.beta_fn = beta_fn                 # opcional: reemplazar la Eq.(14) (p. ej. beta fijo, o beta aprendido)
        self.sw = Swarm(first_pass=first_pass, gbest_from=gbest_from, alternate=alternate, fracs=fracs)
        self.mode = "search"
        self.started = False

    def _beta(self):
        if self.beta_fn is not None:
            return self.beta_fn(self.sw.t)
        return self.beta_min + (self.sw.t / self.t_max) * (self.beta_max - self.beta_min)   # Eq.(14)

    def step(self, plant):
        sw = self.sw
        if not self.started:                   # primer arranque: Isc medido de la curva actual
            sw.restart(plant.curve.Isc, first=True)
            self.started = True
        restarted = False
        if self.mode == "search":
            beta = self._beta()
            E, Ps = sw.sweep(plant, self.wait)
            P_end, P_max = float(Ps[-1]), float(Ps.max())
            disp = sw.dispersion()
            t_now = sw.t
            sw.update(beta)
            if self.restart_mode == "early" and t_now > 1 and (sw.Pbest - P_max) >= self.thresh:
                sw.restart(plant.curve.Isc); restarted = True      # detecta el cambio ya durante la busqueda
            elif sw.t > self.t_max:
                self.mode = "park"             # "Set Gbest, Measure power"
            mode = "search"
        else:
            E, P_end = sw.hold(plant, self.wait)
            P_max, beta, disp, t_now, mode = P_end, 0.0, sw.dispersion(), sw.t, "park"
            if self.restart_mode != "none" and abs(sw.Pbest - P_end) >= self.thresh:   # |Pbest-Ppv| >= 5
                sw.restart(plant.curve.Isc); self.mode = "search"; restarted = True
        return dict(E=E, P_end=P_end, P_max=P_max, beta=beta, mode=mode, disp=disp, t=t_now,
                    Gbest=sw.Gbest, Pbest=sw.Pbest, restart=restarted)


# --------------------------------------------------------------------------------------------------
# Ejecutor de escenarios y metricas
# --------------------------------------------------------------------------------------------------
def run_scenario(make_controller, segments, wait, dt=1e-5):
    """segments = [(curva, duracion_s), ...]. El convertidor conserva su estado al cambiar de sombra.
    Devuelve un dict de arreglos (uno por paso de tiempo) y los datos por segmento."""
    plant = Plant(segments[0][0], dt=dt)
    ctrl = make_controller()
    step_T = ctrl.sw.n * wait
    rec = {k: [] for k in ("t0", "E", "P_end", "P_max", "beta", "mode", "disp", "tpass", "Gbest", "Pbest", "restart", "seg")}
    t = 0.0
    for si, (curve, dur) in enumerate(segments):
        plant.set_curve(curve)
        n_steps = int(round(dur / step_T))
        for _ in range(n_steps):
            info = ctrl.step(plant)
            rec["t0"].append(t); t += step_T
            for k, src in (("E", "E"), ("P_end", "P_end"), ("P_max", "P_max"), ("beta", "beta"), ("mode", "mode"),
                           ("disp", "disp"), ("tpass", "t"), ("Gbest", "Gbest"), ("Pbest", "Pbest"), ("restart", "restart")):
                rec[k].append(info[src])
            rec["seg"].append(si)
    log = {k: np.array(v) for k, v in rec.items()}
    log["step_T"] = step_T
    log["segments"] = segments
    return log


def segment_metrics(log, si):
    """Metricas de un segmento (una sombra). Todas relativas a P_ceiling (potencia alcanzable con R=12 ohm)."""
    curve, dur = log["segments"][si]
    m = log["seg"] == si
    Pref = curve.P_ceiling
    T = m.sum() * log["step_T"]
    E = log["E"][m].sum()
    P_end = log["P_end"][m]
    modes = log["mode"][m]
    n = len(P_end)
    tail = slice(int(0.9 * n), n)                              # ultimo 10 % del segmento
    park_idx = np.where(modes == "park")[0]
    ok99 = np.where(P_end >= 0.99 * Pref)[0]
    return dict(
        eff_energy=100.0 * E / (Pref * T),                     # energia entregada / energia ideal (metrica principal)
        eff_final=100.0 * float(np.mean(P_end[tail])) / Pref,  # potencia al final del segmento / ideal
        t_first_park=float(park_idx[0] * log["step_T"]) if len(park_idx) else float("nan"),   # fin de la 1.a busqueda
        t99=float(ok99[0] * log["step_T"]) if len(ok99) else float("nan"),                    # 1.a vez >= 99 % del techo
        n_restarts=int(log["restart"][m].sum()),
        eff_gmpp_energy=100.0 * E / (curve.P_gmpp * T),         # idem contra el GMPP teorico (para comparar con el paper)
    )
