"""
pvcurve_V2 — curvas I-V / P-V de los 4 casos reales del paper (datasets_V2/caso_N.npy)
y clase base compartida con las curvas sinteticas (array_model_V2).

CAMBIOS RESPECTO A LA V1 (y por que):
  * `P_ceiling`: potencia maxima FISICAMENTE ALCANZABLE por el convertidor Boost con la carga
    R_LOAD=12 ohm. Un Boost solo puede presentar al panel una resistencia de entrada aparente en
    [0, R], asi que solo son alcanzables los puntos con V/I <= R. En la V1 la recompensa y las
    metricas usaban el GMPP teorico, que a veces es inalcanzable (Caso 3 y varias curvas sinteticas);
    eso castigaba a cualquier metodo por algo imposible. Ahora toda eficiencia se mide contra
    `P_ceiling` (que coincide con el GMPP cuando este es alcanzable).
  * `Vx`, `Ix`: tablas contiguas (float64) de I(V) monotona, listas para el nucleo compilado (numba).
"""
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "datasets_V2"
R_LOAD = 12.0  # ohm, carga resistiva del Boost (Tabla 2 del paper)


class CurveBase:
    """Calcula y guarda los atributos derivados que necesitan el simulador y las metricas."""

    def _finalize(self, I, V, P, Isc, name=""):
        self.name = name
        self.I, self.V, self.P = I, V, P
        self.Isc = float(Isc)                 # corriente de cortocircuito (la usa el algoritmo para sembrar particulas)
        self.Voc = float(V.max())
        gi = int(np.argmax(P))
        self.I_gmpp, self.V_gmpp, self.P_gmpp = float(I[gi]), float(V[gi]), float(P[gi])  # GMPP teorico

        # Techo alcanzable con R fija: solo puntos con V/I <= R  <=>  V <= R*I
        reachable = V <= R_LOAD * I + 1e-12
        if reachable.any():
            ci = int(np.argmax(np.where(reachable, P, -np.inf)))
            self.I_ceiling, self.V_ceiling, self.P_ceiling = float(I[ci]), float(V[ci]), float(P[ci])
        else:  # curva degenerada (nada alcanzable): evitar divisiones por cero
            self.I_ceiling, self.V_ceiling, self.P_ceiling = self.I_gmpp, self.V_gmpp, max(self.P_gmpp * 0.5, 1e-3)
        self.P_ceiling = max(self.P_ceiling, 1e-3)

        # Tabla I(V): V ascendente, I forzada a ser no-creciente (fisicamente un panel nunca sube
        # su corriente al subir el voltaje; el ruido numerico de los datos crearia equilibrios falsos).
        order_v = np.argsort(V)
        self.Vx = np.ascontiguousarray(V[order_v], dtype=np.float64)
        self.Ix = np.ascontiguousarray(np.minimum.accumulate(I[order_v]), dtype=np.float64)

    def power_at_I(self, I_query):
        """Potencia estatica P(I) por interpolacion (solo para analisis estatico / graficas)."""
        return np.interp(np.clip(I_query, 0.0, self.Isc), self.I, self.P)


class PVCurve(CurveBase):
    """Curva de uno de los 4 casos reales del paper. idx = 0..3  (caso_0 = Caso 1, etc.)."""

    def __init__(self, idx):
        arr = np.load(DATA_DIR / f"caso_{idx}.npy")
        I, V, P = arr[:, 0], arr[:, 1], arr[:, 2]
        order = np.argsort(I)
        self._finalize(I[order], V[order], P[order], I.max(), name=f"Caso {idx + 1}")


def load_case(idx):
    return PVCurve(idx)
