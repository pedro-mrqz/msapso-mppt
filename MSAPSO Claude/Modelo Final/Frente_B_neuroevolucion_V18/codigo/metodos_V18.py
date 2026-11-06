"""
metodos_V18.py — Registro de metodos por nombre (para que estatico_V18 / dinamico_V18 los construyan dentro de cada proceso).
Referencias: MSAPSO completo, V7, V14, V17 (variante congelada), V11 (red supervisada de la V11 con el refinado de la V11).
V18: «NE <capas> cola=<peso> s0=<sigma0> [+cota]» = red entrenada por CEM sobre los pesos (redes_V18.npz) + refinado CEM sobre la corriente.
«V11 s0=... [+cota]»: la red de la V11 con EXACTAMENTE el mismo despliegue que una variante V18 (solo cambian los pesos: control de la pregunta principal).
"""
import os, re, pickle, warnings
import numpy as np
from msapso_early_V14 import make_msapso_early, Rule
from verificacion_V17 import VCfg, ICfg, make_verificada, make_intercalado
from neuroevolucion_V18 import Red, PCfg, make_red_cem, p_name

AQUI = os.path.dirname(os.path.abspath(__file__))
V17_CFG = ICfg(0.10, 2, 2, 0.05, ref=True)                     # variante congelada de la V17
GRID_P = [PCfg(s, c) for s in (0.03, 0.1) for c in (False, True)]
_REDES = {}


def red(clave):
    if clave not in _REDES:
        if clave == "V11":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore"); _REDES[clave] = Red.from_sklearn(pickle.load(open(os.path.join(AQUI, "resultados_V14/mlp_elegido_V11.pkl"), "rb")))
        else:
            z = np.load(os.path.join(AQUI, "resultados_V18/redes_V18.npz")); _REDES[clave] = Red.from_theta(z[clave + "|theta"], tuple(int(v) for v in z[clave + "|h"]))
    return _REDES[clave]


def nombres_ne():
    z = np.load(os.path.join(AQUI, "resultados_V18/redes_V18.npz")); return sorted({k.split("|")[0] for k in z.files}, key=lambda s: (int(s.split()[1].split("x")[0]), s))


def variantes(ronda=None):
    """ronda None: todas; 'V18': redes con objetivo «punto» (x 4 despliegues); 'V18.1': redes con objetivo «cadena» (solo con su sigma0, con y sin cota)."""
    out = []
    for n in nombres_ne():
        m = re.search(r"ref=([\d.]+)", n)
        if m and ronda != "V18": out += [f"{n} {p_name(PCfg(float(m.group(1)), c))}" for c in (False, True)]
        if not m and ronda != "V18.1": out += [f"{n} {p_name(pc)}" for pc in GRID_P]
    return out


def parse(nombre):
    """'NE 32x32 cola=1 s0=0.1 +cota' -> ('NE 32x32 cola=1', PCfg(0.1, True)); 'V11 s0=0.1' -> ('V11', PCfg(0.1, False))."""
    m = re.match(r"^(.*) s0=([\d.]+)( \+cota)?$", nombre); assert m, nombre
    return m.group(1), PCfg(float(m.group(2)), bool(m.group(3)))


def metodo(nombre):
    if nombre == "MSAPSO": return make_msapso_early(Rule("none"))
    if nombre == "V7": return make_msapso_early(Rule("disp", delta=0.02, t_min=3))
    if nombre == "V14": return make_verificada(VCfg("ninguna"))
    if nombre == "V17": return make_intercalado(V17_CFG)
    if nombre == "V11": return make_red_cem(red("V11"), PCfg(0.1, False))
    clave, pc = parse(nombre); return make_red_cem(red(clave), pc)


def retroceso(nombre): return 0.0 if nombre in ("MSAPSO", "V7") else 0.02
