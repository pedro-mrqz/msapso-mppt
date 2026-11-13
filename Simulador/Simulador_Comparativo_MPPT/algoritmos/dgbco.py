"""
dgbco.py — V15: DGBCO (Dynamic Group-Based Cooperative Optimization; Moosavi et al., Energy Reports 8 (2022) 13529-13543, Eqs. 1-7 y Fig. 6) como buscador de MPPT.
Mismo contrato que el MSAPSO: buscar(planta, curva, rng); cada planta.run(1.0, I) es UNA medicion. x = I / Isc en [0, 1]. Presupuesto = n * T mediciones (sin parada anticipada, como el paper).
Grupos: exploracion (70 %) y explotacion (30 %); los agentes de explotacion son los mejores (por potencia medida) de la iteracion anterior.
 exploracion:  p = U(0,1); si p >= 0.5 MUTACION; si no  D = r1 (x - 1), x' = x + D (2 r2 - 1),  r1 ~ U[0,1], r2 ~ U[0,2]            (Eqs. 1-2)
 explotacion:  p >= 0.5:  x' = x + r3 (L - x), r3 ~ U[0,2]  (Eqs. 3-4);  si no  D = L (K - r4), x' = x + D (2 r5 - 1), K = 2 - 2 t^2 / T^2   (Eqs. 5-7)
 elitismo: L = mejor posicion MEDIDA hasta ahora. Si L no mejora en 2 iteraciones seguidas, un agente pasa a exploracion (Fig. 6).
INTERPRETACIONES declaradas (el paper no las precisa): mutacion = nueva posicion uniforme en [0, 1]; pertenencia a grupos por rango de potencia; barrido alternante ascendente/descendente por iteracion (como el MSAPSO);
 posiciones fuera de [0, 1] se recortan; inicializacion 'random' (paper) o 'msapso' (las mismas fracciones del MSAPSO).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from dataclasses import dataclass
from pvsim.msapso import INIT_FRACS


@dataclass(frozen=True)
class Cfg:
    n: int = 4
    T: int = 10
    init: str = "random"      # random | msapso
    frac_expl: float = 0.7
    p_mut: float = 0.5


def make_dgbco(cfg: Cfg):
    def buscar(planta, curva, rng):
        n, T = cfg.n, cfg.T
        x = rng.uniform(0.0, 1.0, n) if cfg.init == "random" else (np.array(INIT_FRACS) if n == 7 else np.linspace(0.95, 0.10, n))
        nexp = int(round(cfg.frac_expl * n)); Pbest, L, stall = -np.inf, 0.5, 0
        def medir(x, t):
            order = np.argsort(x)
            if t % 2 == 1: order = order[::-1]
            P = np.empty(n)
            for j in order: P[j] = planta.run(1.0, x[j] * curva.Isc)[0]
            return P
        P = medir(x, 0); j = int(np.argmax(P)); Pbest, L = P[j], x[j]
        for t in range(1, T):
            rank = np.argsort(P)[::-1]; expl = set(rank[n - nexp:]); xn = x.copy()
            for i in range(n):
                p = rng.random()
                if i in expl:
                    if p >= cfg.p_mut: xn[i] = rng.uniform(0.0, 1.0)
                    else: D = rng.uniform(0, 1) * (x[i] - 1.0); xn[i] = x[i] + D * (2 * rng.uniform(0, 2) - 1)
                else:
                    if p >= cfg.p_mut: xn[i] = x[i] + rng.uniform(0, 2) * (L - x[i])
                    else:
                        K = 2.0 - 2.0 * t ** 2 / T ** 2; D = L * (K - rng.random()); xn[i] = x[i] + D * (2 * rng.random() - 1)
            x = np.clip(xn, 0.0, 1.0); P = medir(x, t); j = int(np.argmax(P))
            if P[j] > Pbest: Pbest, L, stall = P[j], x[j], 0
            else: stall += 1
            if stall >= 2: nexp = min(n - 1, nexp + 1); stall = 0
    return buscar
