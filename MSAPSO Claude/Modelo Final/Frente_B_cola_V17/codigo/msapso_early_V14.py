"""
msapso_early_V14.py — V7: MSAPSO con PARADA ANTICIPADA. Mismo algoritmo del paper (7 particulas Isc*[.95 .8 .65 .5 .3 .15 .1], beta 0.1->0.95 segun la Eq. 14 con t_max = 25,
Eq. 13 determinista, pasadas alternantes, Gbest inmediato); lo unico que cambia es CUANDO se deja de buscar: en vez de hacer siempre las 25 pasadas (175 mediciones) se
detiene en cuanto una regla OBSERVABLE (solo potencias medidas y el estado del propio enjambre) indica que ya convergio. Meta: misma exactitud con menos pasadas.
Reglas (despues de cada pasada t >= t_min):
  noimp(k, eps): Pbest no mejoro mas de eps watts en las ultimas k pasadas.
  disp(delta):   dispersion del enjambre std(x)/Isc < delta (las particulas ya colapsaron sobre el Gbest).
  or / and:      combinacion de ambas.
Referencias: MSAPSO completo (25 pasadas) y TRUNCADOS fijos (t_max fijo = T con la beta del paper SIN comprimir, o beta comprimida a T pasadas).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from dataclasses import dataclass
from pvsim_V14.msapso_V14 import Swarm
from pvsim_V14.array_model_V14 import SyntheticPVCurve, random_shading_mix
from pvsim_V14.static_plant_V14 import StaticPlant
from pvsim_V14.medicion_V14 import ISC_NOM, metrics_from_plant, P_NOM
from baselines_nivel1_V14 import scenarios, paper_beta

T_MAX = 25


@dataclass(frozen=True)
class Rule:
    kind: str = "noimp"      # noimp | disp | or | and | none
    k: int = 3
    eps: float = 0.5         # W
    delta: float = 0.03
    t_min: int = 3


def should_stop(rule: Rule, pbest_hist, disp):
    t = len(pbest_hist)
    if rule.kind == "none" or t < rule.t_min:
        return False
    ni = t > rule.k and (pbest_hist[-1] - pbest_hist[-1 - rule.k]) < rule.eps
    di = disp < rule.delta
    return {"noimp": ni, "disp": di, "or": ni or di, "and": ni and di}[rule.kind]


def make_msapso_early(rule: Rule, isc="real", compress_T=None):
    """compress_T: si se da, la beta de la Eq. 14 se comprime a ESA cantidad de pasadas (t_max = compress_T) y se hacen exactamente compress_T pasadas."""
    def f(plant, curve, rng):
        sw = Swarm(first_pass="ascending"); sw.restart(curve.Isc if isc == "real" else ISC_NOM, first=True)
        tmax = compress_T or T_MAX; hist = []
        for _ in range(tmax):
            sw.sweep(plant, 1.0)
            hist.append(sw.Pbest); disp = sw.dispersion()
            sw.update(paper_beta(sw.t, t_max=tmax))
            if compress_T is None and should_stop(rule, hist, disp):
                break
    return f


def eval_curves(method, curves, noise_w=0.0, seed=7, reps=1):
    fin, ene, nm, n99 = [], [], [], []
    for k, c in enumerate(curves):
        a, b, n = [], [], 0
        for r in range(reps):
            rng = np.random.default_rng(seed + 1000 * k + r)
            pl = StaticPlant(c, noise_w=noise_w, rng=rng); method(pl, c, rng)
            m = metrics_from_plant(pl, c); a.append(m["eff_final"]); b.append(m["eff_energy"]); n = m["n_meas"]
        fin.append(np.mean(a)); ene.append(np.mean(b)); nm.append(n)
    return np.array(fin), np.array(ene), np.array(nm)


def make_sets():
    """VALIDACION (elegir la regla): 100 originales (semilla 3030) + 100 con atenuacion global (3031). PRUEBA fresca: 4040 / 4041. Mas los 4 casos reales."""
    def orig(seed, n=100):
        r = np.random.default_rng(seed); return [SyntheticPVCurve(random_shading_mix(r)) for _ in range(n)]
    def att(seed, n=100):
        r = np.random.default_rng(seed); return [SyntheticPVCurve(random_shading_mix(r) * r.uniform(0.25, 1.0)) for _ in range(n)]
    real, _ = scenarios()
    return dict(val=orig(3030) + att(3031), test_orig=orig(4040), test_att=att(4041), real=real)
