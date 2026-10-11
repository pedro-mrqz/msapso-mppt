"""
array_model_V2 — generador SINTETICO de curvas I-V / P-V para patrones de sombreado arbitrarios.

Modelo de un diodo (ec. 1 del paper) por sub-string, cada uno con diodo de bypass:
  Iph_j  = ISC_REF * (Irr_j / 1000)
  V_j(I) = (Ns_sub*A*k*Tc/q) * ln((Iph_j - I)/Io + 1) - I*Rs_sub     si I < Iph_j
         = V_BYPASS (~ -0.5 V, el bypass conduce)                     si I >= Iph_j
  V(I)   = suma de los V_j(I)
La corriente maxima de la serie la limita el sub-string MENOS sombreado (max Iph), porque los demas
quedan en bypass (correccion de fisica hecha en la V1 y conservada aqui).

Sirve para entrenar con miles de patrones distintos; los 4 casos reales del paper quedan como
conjunto de validacion (holdout) que el agente nunca ve en entrenamiento.
"""
import numpy as np
from pvsim_V2.pvcurve_V2 import CurveBase

Q = 1.602e-19
K = 1.381e-23
IO = 1.9164e-9       # A, corriente de saturacion inversa del panel completo (Tabla 1)
RS = 0.29838         # ohm, resistencia serie del panel completo (Tabla 1)
NS = 60              # celdas en serie (Tabla 1)
A_IDEAL = 1.5        # factor de idealidad (aprox.; no viene en la tabla)
ISC_REF = 8.9        # A, Isc a 1000 W/m2 (consistente con los datasets)
V_BYPASS = -0.5      # V
TC = 298.15          # K


def _substring_voltage(I, Iph, ns_sub, rs_sub):
    with np.errstate(invalid="ignore"):
        arg = (Iph - I) / IO + 1
    I = np.asarray(I, dtype=float)
    bypass = (I >= Iph - 1e-9) | (arg <= 0)
    safe_arg = np.where(arg <= 0, 1.0, arg)
    v = (ns_sub * A_IDEAL * K * TC / Q) * np.log(safe_arg) - I * rs_sub
    return np.where(bypass, V_BYPASS, v)


class SyntheticPVCurve(CurveBase):
    """Curva generada a partir de una lista de irradiancias (una por sub-string)."""

    def __init__(self, irradiances, n_points=400):
        irradiances = np.asarray(irradiances, dtype=float)
        n_sub = len(irradiances)
        ns_sub, rs_sub = NS / n_sub, RS / n_sub
        Iph = ISC_REF * (irradiances / 1000.0)
        Isc_total = Iph.max()
        I_grid = np.linspace(1e-6, Isc_total * 0.999999, n_points)
        V_grid = np.zeros(n_points)
        for j in range(n_sub):
            V_grid += _substring_voltage(I_grid, Iph[j], ns_sub, rs_sub)
        V_grid = np.clip(V_grid, 0.0, None)
        V0 = float(sum(_substring_voltage(np.array(0.0), Iph[j], ns_sub, rs_sub) for j in range(n_sub)))
        I_all = np.concatenate([[0.0], I_grid])
        V_all = np.concatenate([[V0], V_grid])
        self.irradiances = irradiances
        self._finalize(I_all, V_all, I_all * V_all, Isc_total, name="sintetica")


def random_shading(rng, n_sub=4, irr_min=100.0, irr_max=1000.0):
    return rng.uniform(irr_min, irr_max, size=n_sub)


def random_shading_mix(rng, n_sub=4):
    """Patrones mas exigentes (picos multiples y cambios grandes): con prob. 0.5 uniforme en [100,1000] por sub-string
    (como la V1); con prob. 0.5 cada sub-string es 'soleado' U[700,1000] o 'sombreado' U[100,500] al azar (>=1 de cada tipo
    para garantizar escalones en la curva P-I). Los 4 casos reales del paper (holdout) NO se usan para generar estos patrones."""
    if rng.random() < 0.5:
        return rng.uniform(100.0, 1000.0, size=n_sub)
    shaded = rng.random(n_sub) < 0.5
    if shaded.all():
        shaded[rng.integers(n_sub)] = False
    if not shaded.any():
        shaded[rng.integers(n_sub)] = True
    return np.where(shaded, rng.uniform(100.0, 500.0, n_sub), rng.uniform(700.0, 1000.0, n_sub))
