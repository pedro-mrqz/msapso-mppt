"""
medicion_V5 — Definicion unica de la rejilla de medicion, la observacion y las metricas del NIVEL 1 (algoritmico) de la V4.

Decisiones de diseno (cada una responde a una indicacion del profesor; ver diseno_V5.md):
  * Rango de corrientes [I_MIN, I_MAX] = [0.10, 0.95] * ISC_NOMINAL (Isc de la hoja de datos, 8.9 A): «Isc nominal para fijar
    minimo y maximo». NO se usa la Isc real del patron (un controlador real no la conoce). Mismas fracciones que el paper.
  * Observacion = las N potencias medidas en N corrientes UNIFORMES entre I_MIN e I_MAX, en orden ASCENDENTE (no perturba
    el circuito), divididas entre la potencia nominal del panel (250 W, dato de hoja de datos; no es el GMPP).
  * La recompensa usa SOLO potencias medidas. El GMPP real (P_gmpp) se usa unicamente para EVALUAR (calcular eficiencias).
Metricas (por patron de sombra, busqueda en frio):
  n_meas   : mediciones gastadas hasta fijar el punto (prioridad del profesor)
  n99      : numero de la primera medicion cuya potencia VERDADERA >= 99 % del GMPP (nan si nunca)
  eff_final: potencia verdadera en el punto elegido (la mejor LEIDA) / GMPP
  eff_energy: promedio de la potencia verdadera durante una ventana de W mediciones (busqueda + permanencia en el punto
              elegido) / GMPP. Es la «energia en unidades de iteracion»; mismo W para todos los metodos.
"""
import numpy as np
from pvsim_V5.array_model_V5 import ISC_REF

ISC_NOM = ISC_REF            # 8.9 A (hoja de datos)
FRAC_MIN, FRAC_MAX = 0.10, 0.95
I_MIN, I_MAX = FRAC_MIN * ISC_NOM, FRAC_MAX * ISC_NOM
P_NOM = 250.0                # W, potencia nominal del panel (hoja de datos)
W_ENERGIA = 200              # ventana (en mediciones) para la metrica de energia


def grid_currents(n):
    return np.linspace(I_MIN, I_MAX, n)


def scan(plant, n):
    """Mide la potencia en n corrientes uniformes, en orden ascendente. Devuelve (I, P_leida)."""
    I = grid_currents(n)
    P = np.array([plant.run(1.0, i)[0] for i in I])
    return I, P


def action_to_current(a):
    """a en [-1, 1] -> corriente en [I_MIN, I_MAX]."""
    return I_MIN + 0.5 * (float(np.clip(a, -1, 1)) + 1.0) * (I_MAX - I_MIN)


def current_to_action(I):
    return 2.0 * (np.clip(I, I_MIN, I_MAX) - I_MIN) / (I_MAX - I_MIN) - 1.0


def metrics_from_plant(plant, curve, window=W_ENERGIA):
    Pt, Pm, I = np.array(plant.log_Ptrue), np.array(plant.log_Pmeas), np.array(plant.log_I)
    Pg = curve.P_gmpp
    n = len(Pt)
    sel = int(np.where(Pm == Pm.max())[0][-1])           # el controlador elige la mejor potencia LEIDA (empates: la ultima)
    Psel = Pt[sel]
    ok = np.where(Pt >= 0.99 * Pg)[0]
    head = Pt[:window]
    energy = (head.sum() + max(window - n, 0) * Psel) / (window * Pg)
    return dict(n_meas=n, n99=float(ok[0] + 1) if len(ok) else float("nan"),
                eff_final=100.0 * Psel / Pg, eff_energy=100.0 * energy, I_sel=float(I[sel]))
