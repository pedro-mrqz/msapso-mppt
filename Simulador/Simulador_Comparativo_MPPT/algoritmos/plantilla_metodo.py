"""
plantilla_metodo.py — PLANTILLA para escribir tu propio metodo de busqueda del punto de maxima potencia.

CONTRATO (lo unico que necesita el simulador):
    def make_mi_metodo(...) -> buscar
    def buscar(planta, curva, rng) -> None

  planta.run(1.0, I)   pide al convertidor operar en la corriente I (amperes) durante UNA ventana de tiempo y devuelve (P_medida, energia).
                       Cada llamada es UNA medicion y cuesta una ventana: mientras buscas, el panel entrega menos que su maximo.
                       P_medida incluye el ruido del escenario; tu algoritmo solo debe usar esta senal (no conoce la curva real).
  curva.Isc            corriente de cortocircuito del patron de sombra actual (el rango util de busqueda es de 0 a Isc).
  rng                  numpy.random.Generator: usalo para cualquier azar y asi los resultados son reproducibles.

No hace falta devolver nada ni elegir la corriente final: el entorno se queda con la corriente de MAYOR potencia medida durante
tu busqueda, la fija (aplicando el retroceso b del registro) y vigila; si la potencia cambia 5 W o mas, vuelve a llamar a buscar().

Este ejemplo es deliberadamente simple: barrido grueso + escalada local ("hill climbing") con paso decreciente.
"""
import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class Cfg:
    n_barrido: int = 7       # puntos del barrido inicial (fracciones de Isc entre 0.10 y 0.95)
    paso0: float = 0.06      # paso inicial de la escalada (fraccion de Isc)
    iteraciones: int = 8     # numero de pasos de escalada (cada uno mide 2 puntos)


def make_mi_metodo(cfg: Cfg = Cfg()):
    def buscar(planta, curva, rng):
        # 1) barrido grueso para ubicar la region mas prometedora
        xs = np.linspace(0.10, 0.95, cfg.n_barrido)
        P = np.array([planta.run(1.0, x * curva.Isc)[0] for x in xs])
        x, Pb = float(xs[int(np.argmax(P))]), float(P.max())
        # 2) escalada local: prueba a ambos lados y se queda con el mejor; el paso se reduce a la mitad si ninguno mejora
        paso = cfg.paso0
        for _ in range(cfg.iteraciones):
            mejor = None
            for cand in (x - paso, x + paso):
                cand = float(np.clip(cand, 0.0, 1.0)); Pc = planta.run(1.0, cand * curva.Isc)[0]
                if Pc > Pb: Pb, mejor = Pc, cand
            if mejor is None: paso *= 0.5
            else: x = mejor
    return buscar
