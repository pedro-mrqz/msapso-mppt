"""
metodos.py — REGISTRO de metodos del simulador. Cada entrada:   id -> (nombre, constructor, retroceso b)

  nombre        texto que se ve en los menus del simulador.
  constructor   funcion SIN argumentos que devuelve  buscar(planta, curva, rng)  (ver docs/anadir_un_metodo.md).
  b             retroceso de corriente al operar: tras buscar, el convertidor se fija en (1 - b) * I_elegida. 0 = sin retroceso.

Los 9 metodos de abajo usan la configuracion CONGELADA de sus campanas (V7, V10-V17). Para anadir uno nuevo copia
algoritmos/plantilla_metodo.py, impórtalo aqui y agrega una linea al diccionario METODOS.
"""
import os, sys, pickle
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from algoritmos.msapso_early import make_msapso_early, Rule
from algoritmos.cem import CEMCfg, make_cem
from algoritmos.mlp_cem import Cfg as CfgL, make_mlp_cem
from algoritmos.msapso_cem import Cfg as CfgM, make_msapso_cem
from algoritmos.dgbco import Cfg as CfgB, make_dgbco
from algoritmos.dgo import Cfg as CfgD, make_dgo
from algoritmos.decentcem import Cfg as CfgC, make_decent
# from algoritmos.plantilla_metodo import make_mi_metodo          # <- descomenta para probar el ejemplo

_MODEL = None
def _mlp():
    """MLP entrenado (modelos/mlp_elegido.pkl). Si tu version de scikit-learn no lo abre: python entrenar_mlp.py"""
    global _MODEL
    if _MODEL is None: _MODEL = pickle.load(open(os.path.join(ROOT, "modelos", "mlp_elegido.pkl"), "rb"))
    return _MODEL

METODOS = {
    "msapso":  ("MSAPSO del paper",           lambda: make_msapso_early(Rule("none")), 0.0),
    "v7":      ("V7 (parada anticipada)",     lambda: make_msapso_early(Rule("disp", delta=0.02, t_min=3)), 0.0),
    "v7b":     ("V7 + retroceso 2 %",         lambda: make_msapso_early(Rule("disp", delta=0.02, t_min=3)), 0.02),
    "cem":     ("CEM puro (V10)",             lambda: make_cem(CEMCfg(n=10, k=3, alpha=0.7, mu0=0.5, sigma0=0.3, sigma_min=0.0, delta=0.01, t_min=3, t_max=25)), 0.0),
    "mlp":     ("MLP + CEM (V11)",            lambda: make_mlp_cem(_mlp(), CfgL(modo="mlp", n=7, k=2, alpha=0.7, sigma0=0.1, sigma_min=0.002, delta=0.005, t_min=2, t_max=12)), 0.0),
    "v14":     ("Candidata V14",              lambda: make_msapso_cem(CfgM(T0=3, comprimida=True, n=7, k=2, alpha=0.7, sigma0=0.03, sigma_min=0.002, delta=0.005, t_min=2, t_max=12)), 0.02),
    "dgbco":   ("DGBCO (V15)",                lambda: make_dgbco(CfgB(n=4, T=10, init="msapso")), 0.02),
    "cedgo":   ("CEDGO (V16)",                lambda: make_dgo(CfgD(variant="cedgo", n=8, G=5, init="random")), 0.02),
    "decent":  ("DecentCEM (V17)",            lambda: make_decent(CfgC(kind="sweep", sigma_mode="fixed", N=10, sigma0=0.03, tau=0.15, n=4, T=4)), 0.0),
    # "mi_metodo": ("Mi método",               lambda: make_mi_metodo(), 0.0),              # <- ejemplo de entrada nueva
}
