"""
validar_simulador_V2.py — Verifica que el simulador compilado (RK4 + numba, converter_V2) reproduce el
simulador de la V1 (scipy.solve_ivp) y mide el aumento de velocidad.

Pruebas:
  1) Convergencia en el paso dt (el resultado no debe depender de dt a la precision usada).
  2) Equivalencia con la V1 (solve_ivp) sobre una escalera de corrientes en los 4 casos reales.
  3) Velocidad: tiempo de computo por milisegundo simulado.
"""
import sys, time
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
V1 = HERE.parent / "Proyecto Integrador Paneles"          # la V1 NO se modifica, solo se lee para comparar
sys.path.insert(0, str(V1))
sys.path.insert(0, str(HERE))

from pvsim_V2.pvcurve_V2 import load_case as load_V2
from pvsim_V2.converter_V2 import Plant
from pvsim.pvcurve import load_case as load_V1             # noqa  (paquete V1)
from pvsim.converter import BoostSTSMCSystem               # noqa  (paquete V1)

FRACS = [0.1, 0.15, 0.3, 0.5, 0.65, 0.8, 0.95]             # escalera tipo MSAPSO (valores de Isc)


def staircase(plant, curve, wait, reps=3):
    Ps, Es = [], 0.0
    for _ in range(reps):
        for f in FRACS:
            P, E = plant.run(wait, f * curve.Isc)
            Ps.append(P); Es += E
    return np.array(Ps), Es


print("=== 1) Convergencia en dt (RK4) — Caso 1, ventanas de 0.5 ms ===")
c = load_V2(0)
ref = None
for dt in [1e-6, 2.5e-6, 5e-6, 1e-5, 2e-5, 5e-5]:
    p = Plant(c, dt=dt)
    Ps, Es = staircase(p, c, 0.5e-3)
    if ref is None:
        ref = (Ps, Es)
    err = np.max(np.abs(Ps - ref[0]) / np.maximum(ref[0], 1e-9)) * 100
    print(f"dt={dt:7.1e}  max error relativo en P_final vs dt=1e-6: {err:8.4f} %   |  dError energia: {abs(Es-ref[1])/ref[1]*100:7.4f} %")

print("\n=== 2) V2 (RK4+numba, dt=1e-5) vs V1 (solve_ivp) — escalera de 7 corrientes x 3, ventanas 0.5 ms y 5 ms ===")
print(f"{'caso':6s}{'ventana':>9s}{'max |dP|/P (%)':>18s}{'dE/E (%)':>12s}")
for idx in range(4):
    for wait in (0.5e-3, 5e-3):
        c2, c1 = load_V2(idx), load_V1(idx)
        p2 = Plant(c2, dt=1e-5)
        s1 = BoostSTSMCSystem(c1)
        P2, E2 = [], 0.0
        P1, E1 = [], 0.0
        for _ in range(3):
            for f in FRACS:
                P, E = p2.run(wait, f * c2.Isc); P2.append(P); E2 += E
                r = s1.run_for(wait, f * c1.Isc, record=True)
                P1.append(r["P_final"])
        # energia V1 por trapecio sobre el log completo
        t = np.array(s1.log["t"]); Pp = np.array(s1.log["Ppv"])
        E1 = np.trapezoid(Pp, t)
        P1, P2 = np.array(P1), np.array(P2)
        print(f"{idx+1:<6d}{wait*1e3:7.1f}ms{np.max(np.abs(P1-P2)/np.maximum(P1,1e-9))*100:16.3f}{abs(E1-E2)/E1*100:12.3f}")

print("\n=== 3) Velocidad (computo por ms simulado) ===")
c1 = load_V1(0); s1 = BoostSTSMCSystem(c1)
t0 = time.perf_counter()
for _ in range(2):
    for f in FRACS:
        s1.run_for(5e-3, f * c1.Isc, record=False)
dt1 = time.perf_counter() - t0
sim_ms = 2 * 7 * 5.0
print(f"V1 (solve_ivp): {dt1/sim_ms*1e3:8.3f} ms de computo por ms simulado")
c2 = load_V2(0); p2 = Plant(c2, dt=1e-5)
p2.run(1e-3, 1.0)  # calentamiento / compilacion
t0 = time.perf_counter()
for _ in range(200):
    for f in FRACS:
        p2.run(0.5e-3, f * c2.Isc)
dt2 = time.perf_counter() - t0
sim_ms = 200 * 7 * 0.5
print(f"V2 (numba RK4): {dt2/sim_ms*1e3:8.3f} ms de computo por ms simulado   -> aceleracion ~{(dt1/(2*7*5.0))/(dt2/sim_ms):.0f}x")
