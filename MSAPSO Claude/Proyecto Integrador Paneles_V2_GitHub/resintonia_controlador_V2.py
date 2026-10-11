"""
resintonia_controlador_V2.py — ¿Puede re-sintonizar el Super-Twisting (lambda, Upsilon) lograr que la corriente
del inductor siga a I_ref en 0.5 ms? Se mide cuanto se mueve la corriente del inductor en 0.5 ms tras un escalon
de referencia (de 6.7 A a 0.7 A y de 0.7 A a 6.7 A), Caso 1, para ganancias 1x, 10x, 100x, 1000x las del paper,
y se compara con el limite fisico dI/dt = (Vpv - (1-u) Vo)/L con u saturado en {0,1}.
"""
import sys; sys.path.insert(0, ".")
import numpy as np
from pvsim_V2.pvcurve_V2 import load_case
from pvsim_V2.converter_V2 import Plant, L_IND

c = load_case(0)
print(f"{'ganancia x':>11s}{'lambda':>8s}{'Upsilon':>9s}   {'bajada 6.7->0.7 A: dI en 0.5 ms':>34s}{'subida 0.7->6.7 A: dI en 0.5 ms':>34s}")
for k in (1, 10, 100, 1000):
    lam, ups = 0.1 * k, 0.01 * k
    p = Plant(c, lam=lam, ups=ups); p.run(0.2, 6.69)          # estacionario en el GMPP
    I0 = p.I_inductor; Vpv, Vo = p.st[0], p.st[2]
    p.run(0.5e-3, 0.7); dI_down = p.I_inductor - I0
    p2 = Plant(c, lam=lam, ups=ups); p2.run(0.2, 0.7)
    I1 = p2.I_inductor
    p2.run(0.5e-3, 6.69); dI_up = p2.I_inductor - I1
    print(f"{k:11d}{lam:8.1f}{ups:9.2f}   {dI_down:30.2f} A{dI_up:30.2f} A")
# limite fisico aproximado en el GMPP del caso 1
Vpv, Vo = 30.06, 49.1
print(f"\nLimite fisico (Vpv={Vpv} V, Vo={Vo} V, L={L_IND*1e3:.0f} mH): bajada max ≈ {(Vpv-Vo)/L_IND*0.5e-3:.2f} A en 0.5 ms (u=0);  subida max ≈ {Vpv/L_IND*0.5e-3:.2f} A en 0.5 ms (u=1)")
