"""
dgo.py — V16: Dynamic Group Optimization (DGO; Tang y Fong 2016) y su hibrido con CEM (CEDGO; Tang, Fong, Dey, Wong y Mohammed, Entropy 19(10):533, 2017) como buscador de MPPT.
Mismo contrato que el MSAPSO: buscar(planta, curva, rng); cada planta.run(1.0, I) es UNA medicion. x = I / Isc en [0, 1]. Presupuesto = n * G mediciones (sin parada anticipada).
Ecuaciones del paper (Entropy 2017):
 miembros, intragrupo:  Eq.4  v = H_i + mu (H_r - b)   si rand > Mr1, si no x          (H_i cabeza de su grupo, H_r cabeza de un grupo al azar, b mejor global, mu ~ N(0,1))
                        Eq.5  v = b + mu (x_r1 - x_r2) si rand > Mr2, si no x          (r1, r2 miembros distintos al azar)
 cabezas, intergrupo:   Eq.6  H' = H + alpha (*) Levy(lambda);   Eq.7  alpha = alpha0 (H - b);   Eq.8  Levy ~ t^-lambda
 seleccion voraz: el nuevo individuo se conserva solo si su potencia medida es >= a la del anterior.
 CEDGO: el operador intragrupo se reemplaza por CE:  Eq.10  x = mu + s randn;  Eq.11  Mu = (1-Lr) Mu + Lr muestras;  Eq.12  S = (1-Lr) S + Lr muestras;  y tiempo de vida (TtL).
INTERPRETACIONES declaradas (el paper no las precisa): 2 grupos; cabeza = mejor del grupo; Mr1 = Mr2 = 0.25 (valor del paper); alpha0 = 0.1; lambda = 1.5 con el muestreo de Mantegna;
 Eq.4 y Eq.5 se aplican en secuencia a cada miembro (la Eq.5 sobreescribe si su sorteo sale); variacion de grupo: tras cada generacion, el grupo con la mejor cabeza recibe un miembro del otro (si le quedan >= 2);
 CEDGO: Mu y S por grupo (Mu0 = cabeza, S0 = s0 = 0.1, Lr = 0.7; las muestras = los 2 mejores del grupo); TtL = 3 generaciones sin mejorar -> el individuo se reemplaza por el promedio de 3 cabezas al azar
 (con reemplazo) mas N(0, 0.05); posiciones recortadas a [0, 1]; barrido alternante; inicializacion 'random' (paper) o 'estratificada' (linspace .95 a .10).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from math import gamma, sin, pi
from dataclasses import dataclass


@dataclass(frozen=True)
class Cfg:
    variant: str = "dgo"      # dgo | cedgo
    n: int = 8
    G: int = 5
    init: str = "random"      # random | strat
    groups: int = 2
    mr: float = 0.25
    alpha0: float = 0.1
    lam: float = 1.5
    lr: float = 0.7
    s0: float = 0.1
    ttl: int = 3


def levy(rng, lam):
    su = (gamma(1 + lam) * sin(pi * lam / 2) / (gamma((1 + lam) / 2) * lam * 2 ** ((lam - 1) / 2))) ** (1 / lam)
    return rng.normal(0, su) / abs(rng.normal(0, 1)) ** (1 / lam)


def make_dgo(cfg: Cfg):
    def buscar(planta, curva, rng):
        n, G = cfg.n, cfg.G
        x = rng.uniform(0, 1, n) if cfg.init == "random" else np.linspace(0.95, 0.10, n)
        def medir(xs, t):
            order = np.argsort(xs)
            if t % 2 == 1: order = order[::-1]
            P = np.empty(len(xs))
            for j in order: P[j] = planta.run(1.0, xs[j] * curva.Isc)[0]
            return P
        P = medir(x, 0); grp = rng.permutation(n) % cfg.groups; age = np.zeros(n, int)
        j = int(np.argmax(P)); b, Pb = x[j], P[j]
        mu = {g: None for g in range(cfg.groups)}; sd = {g: cfg.s0 for g in range(cfg.groups)}
        for t in range(1, G):
            heads = {}
            for g in range(cfg.groups):
                idx = np.where(grp == g)[0]
                if len(idx): heads[g] = idx[int(np.argmax(P[idx]))]
            hl = list(heads.values()); xn = x.copy()
            for i in range(n):
                g = grp[i]
                if i == heads.get(g):                                  # cabeza: vuelo de Levy (Eq. 6-7)
                    xn[i] = x[i] + cfg.alpha0 * (x[i] - b) * levy(rng, cfg.lam)
                elif cfg.variant == "dgo":                             # miembro: Eq. 4 y 5
                    c = x[i]; Hr = x[hl[int(rng.integers(len(hl)))]]
                    if rng.random() > cfg.mr: c = x[heads[g]] + rng.normal() * (Hr - b)
                    mem = [k for k in range(n) if k not in hl]
                    if rng.random() > cfg.mr and len(mem) >= 2:
                        r1, r2 = rng.choice(mem, 2, replace=False); c = b + rng.normal() * (x[r1] - x[r2])
                    xn[i] = c
                else:                                                  # miembro CEDGO: operador CE (Eq. 10)
                    if mu[g] is None: mu[g] = x[heads[g]]
                    xn[i] = mu[g] + sd[g] * rng.normal()
            xn = np.clip(xn, 0, 1); Pn = medir(xn, t)
            if cfg.variant == "cedgo":                                 # Eq. 11-12 por grupo con los 2 mejores muestreados
                for g in range(cfg.groups):
                    idx = np.where((grp == g) & ~np.isin(np.arange(n), hl))[0]
                    if len(idx) >= 1:
                        el = idx[np.argsort(Pn[idx])[::-1][:2]]; mu[g] = (1 - cfg.lr) * mu[g] + cfg.lr * xn[el].mean(); sd[g] = max((1 - cfg.lr) * sd[g] + cfg.lr * (xn[el].std() if len(el) > 1 else sd[g]), 0.002)
            better = Pn >= P; age = np.where(better & (Pn > P), 0, age + 1)
            x = np.where(better, xn, x); P = np.where(better, Pn, P)
            if cfg.variant == "cedgo":                                 # tiempo de vida: reemplazo por promedio de 3 cabezas
                for i in range(n):
                    if age[i] >= cfg.ttl and i not in hl and hl:
                        pick = [x[hl[int(rng.integers(len(hl)))]] for _ in range(3)]; x[i] = float(np.clip(np.mean(pick) + 0.05 * rng.normal(), 0, 1)); P[i] = -np.inf; age[i] = 0
                        P[i] = planta.run(1.0, x[i] * curva.Isc)[0]
            j = int(np.argmax(P))
            if P[j] > Pb: b, Pb = x[j], P[j]
            hs = {g: P[np.where(grp == g)[0]].max() for g in range(cfg.groups) if (grp == g).any()}
            if len(hs) == cfg.groups:                                  # variacion de grupo: el mejor grupo recibe un miembro del otro
                gb = max(hs, key=hs.get); gw = [g for g in hs if g != gb][0]; iw = np.where(grp == gw)[0]
                if len(iw) >= 2: m = iw[int(np.argsort(P[iw])[::-1][1])]; grp[m] = gb
    return buscar
