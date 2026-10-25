"""
static_plant_V4 — «Planta» de NIVEL ALGORITMICO (nivel 1) para la V4.

El profesor indico que su Colab NO modela la dinamica del convertidor y que conviene medir la cantidad de ITERACIONES
(mediciones) y no el tiempo, porque el tiempo de transicion depende de muchas cosas. Esta clase hace exactamente eso:
al pedir una corriente I_ref la potencia medida es la ESTATICA de la curva, P(I_ref), sin inercia del inductor.
Tiene la misma interfaz que converter_V4.Plant (run / Ipv / set_curve) para reutilizar Swarm/MSAPSO sin cambios, y registra
cada medicion (cuantas se gastaron = la metrica principal).

  * Corriente pedida > Isc real del patron => el panel opera en cortocircuito: potencia 0 (importa porque el rango de
    busqueda se fija con la Isc NOMINAL de la hoja de datos, no con la real; con sombra la real es menor).
  * Ruido de medicion: gaussiano aditivo de sigma `noise_w` watts sobre la potencia LEIDA. La potencia verdadera se guarda
    aparte, solo para evaluar (el controlador nunca la ve).
  * `run()` registra UNA medicion por llamada, sin importar `duration` (hold/park no es una medicion nueva).
"""
import numpy as np


class StaticPlant:
    def __init__(self, curve, noise_w=0.0, rng=None):
        self.curve = curve
        self.noise_w = float(noise_w)
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.Ipv = 0.0
        self.log_I, self.log_Ptrue, self.log_Pmeas = [], [], []

    def set_curve(self, curve):
        self.curve = curve

    def p_true(self, I):
        """Potencia estatica verdadera en la corriente I (0 si I > Isc del patron)."""
        c = self.curve
        return float(np.interp(max(float(I), 0.0), c.I, c.P, right=0.0))

    def run(self, duration, I_ref):
        I = max(float(I_ref), 0.0)
        Pt = self.p_true(I)
        Pm = Pt + (self.rng.normal(0.0, self.noise_w) if self.noise_w > 0 else 0.0)
        self.Ipv = min(I, self.curve.Isc)                 # corriente «medida»: no puede pasar de Isc
        self.log_I.append(I); self.log_Ptrue.append(Pt); self.log_Pmeas.append(Pm)
        return Pm, Pm * duration

    def reset_log(self):
        self.log_I, self.log_Ptrue, self.log_Pmeas = [], [], []


class DynamicPlantLogged:
    """Envoltura del simulador DINAMICO (converter_V4.Plant, nivel 2) con el mismo registro de mediciones que StaticPlant.
    La potencia 'verdadera' es la que el panel entrega al FINAL de la ventana t_wait (arrastra la inercia del inductor);
    la 'leida' es esa misma mas ruido."""

    def __init__(self, curve, wait, noise_w=0.0, rng=None, dt=1e-5):
        from pvsim_V4.converter_V4 import Plant
        self.plant = Plant(curve, dt=dt)
        self.curve, self.wait = curve, wait
        self.noise_w = float(noise_w)
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.log_I, self.log_Ptrue, self.log_Pmeas = [], [], []

    @property
    def Ipv(self):
        return self.plant.Ipv

    def set_curve(self, curve):
        self.curve = curve
        self.plant.set_curve(curve)

    def run(self, duration, I_ref):
        P, E = self.plant.run(self.wait if duration is None or duration <= 1.0 else duration, float(I_ref))
        Pm = P + (self.rng.normal(0.0, self.noise_w) if self.noise_w > 0 else 0.0)
        self.log_I.append(float(I_ref)); self.log_Ptrue.append(float(P)); self.log_Pmeas.append(float(Pm))
        return Pm, E

    def reset_log(self):
        self.log_I, self.log_Ptrue, self.log_Pmeas = [], [], []
