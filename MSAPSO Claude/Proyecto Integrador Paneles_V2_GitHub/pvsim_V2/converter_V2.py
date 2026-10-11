"""
converter_V2 — modelo dinamico PV + convertidor Boost + controlador Super-Twisting (ST-SMC),
ecuaciones (2)-(7) del paper, integrado con RK4 de paso fijo y COMPILADO con numba.

POR QUE ESTA REESCRITURA (respecto a pvsim/converter.py de la V1):
  La V1 integraba con scipy.solve_ivp (Python puro en cada evaluacion de la EDO): ~5 ms de computo por
  cada ms simulado. Con los tiempos fieles al paper (7 particulas x 0.5 ms, 25 pasadas, decenas de miles
  de episodios de entrenamiento) eso era inviable. Mismo modelo fisico, nucleo compilado => ~100x mas rapido.
  La equivalencia numerica con la V1 se verifica en validar_simulador_V2.py (resultado en la bitacora).

Estado x = [Vpv, Ipv, Vo, z]:
  Vpv: voltaje en el capacitor de entrada (terminales del panel)     Ipv: corriente del inductor
  Vo : voltaje de salida                                              z  : integrador del Super-Twisting
EDO (promediada, sin PWM):
  dVpv/dt = (I_panel(Vpv) - Ipv)/Ce          (balance de corriente en Ce; I_panel = curva I(V) del panel)
  dIpv/dt = Vpv/L - (1-u) Vo/L               (ec. 2)
  dVo/dt  = (1-u) Ipv/Cs - Vo/(R Cs)         (ec. 3)
Control u = u_eq + u_st  (ec. 4), con s = Ipv - I_ref (ec. 5), u_eq = 1 - Vpv/Vo (ec. 6),
  u_st = -lambda*sqrt(|s|)*sign(s) - z  (ec. 7),  dz/dt = Upsilon*sign(s);  u saturado a [0,1].
sign(s) se suaviza con tanh(s/eps) (el modelo promediado no resuelve el chattering de conmutacion).

La potencia que ve el algoritmo MPPT es la que REALMENTE entrega el panel: P = Vpv * I_panel(Vpv)
(no Vpv*Ipv: Ipv es la corriente del inductor y en transitorios difiere de la del panel; ver bitacora V1).
"""
import math
import numpy as np
from numba import njit

# Parametros del Boost (Tabla 2 del paper)
R_LOAD = 12.0
CS = 470e-6
L_IND = 10e-3
CE = 330e-6
# Ganancias del Super-Twisting tomadas del paper (ref. [43])
LAMBDA = 0.1
UPSILON = 0.01
SIGN_EPS = 1e-3


@njit(cache=True)
def _interp(x, xp, fp):
    """Interpolacion lineal escalar (xp ascendente); satura en los extremos."""
    n = xp.shape[0]
    if x <= xp[0]:
        return fp[0]
    if x >= xp[n - 1]:
        return fp[n - 1]
    lo = 0
    hi = n - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xp[mid] <= x:
            lo = mid
        else:
            hi = mid
    dx = xp[hi] - xp[lo]
    if dx <= 0.0:
        return fp[lo]
    return fp[lo] + (x - xp[lo]) / dx * (fp[hi] - fp[lo])


@njit(cache=True)
def _rhs(s0, s1, s2, s3, Iref, Vx, Ix, prm):
    """Lado derecho de la EDO. prm = [L, Ce, Cs, R, lambda, upsilon, eps]."""
    L, Ce, Cs, R, lam, ups, eps = prm[0], prm[1], prm[2], prm[3], prm[4], prm[5], prm[6]
    Vo = s2 if s2 > 1e-3 else 1e-3
    s = s1 - Iref
    th = math.tanh(s / eps)
    ueq = 1.0 - s0 / Vo
    ust = -lam * math.sqrt(abs(s)) * th - s3
    u = ueq + ust
    if u < 0.0:
        u = 0.0
    elif u > 1.0:
        u = 1.0
    Ip = _interp(s0, Vx, Ix)
    return ((Ip - s1) / Ce,
            s0 / L - (1.0 - u) * Vo / L,
            (1.0 - u) * s1 / Cs - Vo / (R * Cs),
            ups * th)


@njit(cache=True)
def run_window(st, Iref, T, dt_max, Vx, Ix, prm):
    """Integra la EDO durante T segundos con I_ref constante (RK4, paso fijo <= dt_max).
    Modifica `st` en sitio. Devuelve (P_final, E): potencia del panel al final de la ventana (W) y
    energia entregada por el panel en la ventana (J)."""
    n = int(math.ceil(T / dt_max))
    if n < 1:
        n = 1
    h = T / n
    a0, a1, a2, a3 = st[0], st[1], st[2], st[3]
    P_prev = a0 * _interp(a0, Vx, Ix)
    E = 0.0
    for _ in range(n):
        k10, k11, k12, k13 = _rhs(a0, a1, a2, a3, Iref, Vx, Ix, prm)
        k20, k21, k22, k23 = _rhs(a0 + 0.5 * h * k10, a1 + 0.5 * h * k11, a2 + 0.5 * h * k12, a3 + 0.5 * h * k13, Iref, Vx, Ix, prm)
        k30, k31, k32, k33 = _rhs(a0 + 0.5 * h * k20, a1 + 0.5 * h * k21, a2 + 0.5 * h * k22, a3 + 0.5 * h * k23, Iref, Vx, Ix, prm)
        k40, k41, k42, k43 = _rhs(a0 + h * k30, a1 + h * k31, a2 + h * k32, a3 + h * k33, Iref, Vx, Ix, prm)
        a0 += h * (k10 + 2.0 * k20 + 2.0 * k30 + k40) / 6.0
        a1 += h * (k11 + 2.0 * k21 + 2.0 * k31 + k41) / 6.0
        a2 += h * (k12 + 2.0 * k22 + 2.0 * k32 + k42) / 6.0
        a3 += h * (k13 + 2.0 * k23 + 2.0 * k33 + k43) / 6.0
        if a0 < 0.0:
            a0 = 0.0
        P_new = a0 * _interp(a0, Vx, Ix)
        E += 0.5 * (P_prev + P_new) * h
        P_prev = P_new
    st[0], st[1], st[2], st[3] = a0, a1, a2, a3
    return P_prev, E


@njit(cache=True)
def run_window_trace(st, Iref, T, dt_max, Vx, Ix, prm, out_t, out_P, out_V, out_I):
    """Igual que run_window pero guarda la trayectoria (para graficas). Arreglos de tamano n+1."""
    n = int(math.ceil(T / dt_max))
    if n < 1:
        n = 1
    h = T / n
    a0, a1, a2, a3 = st[0], st[1], st[2], st[3]
    out_t[0] = 0.0
    out_P[0] = a0 * _interp(a0, Vx, Ix)
    out_V[0] = a0
    out_I[0] = a1
    for i in range(n):
        k10, k11, k12, k13 = _rhs(a0, a1, a2, a3, Iref, Vx, Ix, prm)
        k20, k21, k22, k23 = _rhs(a0 + 0.5 * h * k10, a1 + 0.5 * h * k11, a2 + 0.5 * h * k12, a3 + 0.5 * h * k13, Iref, Vx, Ix, prm)
        k30, k31, k32, k33 = _rhs(a0 + 0.5 * h * k20, a1 + 0.5 * h * k21, a2 + 0.5 * h * k22, a3 + 0.5 * h * k23, Iref, Vx, Ix, prm)
        k40, k41, k42, k43 = _rhs(a0 + h * k30, a1 + h * k31, a2 + h * k32, a3 + h * k33, Iref, Vx, Ix, prm)
        a0 += h * (k10 + 2.0 * k20 + 2.0 * k30 + k40) / 6.0
        a1 += h * (k11 + 2.0 * k21 + 2.0 * k31 + k41) / 6.0
        a2 += h * (k12 + 2.0 * k22 + 2.0 * k32 + k42) / 6.0
        a3 += h * (k13 + 2.0 * k23 + 2.0 * k33 + k43) / 6.0
        if a0 < 0.0:
            a0 = 0.0
        out_t[i + 1] = (i + 1) * h
        out_P[i + 1] = a0 * _interp(a0, Vx, Ix)
        out_V[i + 1] = a0
        out_I[i + 1] = a1
    st[0], st[1], st[2], st[3] = a0, a1, a2, a3
    return n


class Plant:
    """Planta PV + Boost + ST-SMC con estado persistente entre ventanas (la inercia del convertidor
    se arrastra de un candidato al siguiente, como en el hardware real)."""

    def __init__(self, curve, lam=LAMBDA, ups=UPSILON, eps=SIGN_EPS, dt=1e-5, R=R_LOAD):
        self.curve = curve
        self.prm = np.array([L_IND, CE, CS, R, lam, ups, eps], dtype=np.float64)
        self.dt = dt
        self.st = np.array([0.5, 0.0, 0.5, 0.0], dtype=np.float64)  # arranque en frio (igual que la V1)
        self.t = 0.0

    @property
    def Ipv(self):
        """Corriente de SALIDA DEL MODULO en los terminales del panel al final de la ultima ventana,
        I_panel(Vpv). Es la 'Ipv' del paper (Eq.1: 'corriente de salida del modulo'); la usa MSAPSO en
        Gbest = Ipv y en Ppv = Vpv*Ipv. Asi Pbest y Gbest son siempre el MISMO punto de la curva P-V.
        (La corriente del inductor, st[1], difiere de esta durante los transitorios.)"""
        return float(np.interp(self.st[0], self.curve.Vx, self.curve.Ix))

    @property
    def I_inductor(self):
        return float(self.st[1])

    def set_curve(self, curve):
        """Cambio abrupto de sombra: cambia la fuente, el convertidor conserva su estado."""
        self.curve = curve

    def run(self, duration, I_ref):
        """Aplica I_ref durante `duration` s. Devuelve (P_final [W], E [J])."""
        P, E = run_window(self.st, float(I_ref), float(duration), self.dt, self.curve.Vx, self.curve.Ix, self.prm)
        self.t += duration
        return P, E

    def run_trace(self, duration, I_ref):
        n = int(math.ceil(duration / self.dt))
        t = np.empty(n + 1); P = np.empty(n + 1); V = np.empty(n + 1); I = np.empty(n + 1)
        run_window_trace(self.st, float(I_ref), float(duration), self.dt, self.curve.Vx, self.curve.Ix, self.prm, t, P, V, I)
        t = t + self.t
        self.t += duration
        return t, P, V, I
