"""
cola_con_borde.py — Cola estatica CON el limite de la carga (revision del profesor, nov. 2026).

Por que existe: la cola estatica oficial (campana.py est) usa StaticPlant, que mide la potencia EXACTAMENTE en la corriente pedida
aunque este en la zona que el Boost con carga de 12 ohm no puede alcanzar (V/I > 12 ohm), y compara contra el maximo TEORICO.
Eso es coherente con como se diseñaron los metodos originales, pero penaliza a un metodo que, por diseño, no busca en la zona
inalcanzable (p. ej. decent_alc) por no encontrar un pico que el convertidor real nunca podria usar. Aqui:
  * lo pedido por debajo del borde alcanzable se MIDE en el borde (corriente y potencia del borde), como en el simulador dinamico;
  * la exactitud final se mide contra el maximo ALCANZABLE calculado en una rejilla fina (la misma del borde). Nota: el P_ceiling de las curvas
    se calcula solo en sus ~400 puntos muestreados y, cuando el borde cae entre dos muestras, subestima el maximo alcanzable
    (en estas 1000 curvas, 1 % en promedio); por eso aqui se usa la rejilla fina.
Mismas 1000 curvas y semillas que campana.py est. La perdida de cada metodo se mide frente al MSAPSO del paper en esta misma planta.
USO:  python cola_con_borde.py [--solo id1,id2]      -> resultados/est_borde.json  (no modifica est.json)
"""
import os, sys, json, argparse
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
from multiprocessing import Pool
import numpy as np
from campana import static_set
from metodos import METODOS
from pvsim.static_plant import StaticPlant
from algoritmos.decentcem import borde_alcanzable


class StaticPlantBorde(StaticPlant):
    """StaticPlant con el limite V/I <= 12 ohm: una corriente pedida por debajo del borde se mide en el borde."""
    def __init__(self, curve, **kw):
        super().__init__(curve, **kw); self.Ib = borde_alcanzable(curve, x_min=0.0) * curve.Isc

    def run(self, duration, I_ref):
        I = max(float(I_ref), self.Ib)
        Pt = self.p_true(I); Pm = Pt + (self.rng.normal(0.0, self.noise_w) if self.noise_w > 0 else 0.0)
        self.Ipv = min(I, self.curve.Isc); self.log_I.append(I); self.log_Ptrue.append(Pt); self.log_Pmeas.append(Pm)
        return Pm, Pm * duration


def max_alcanzable(c, R=12.0, n=4000):
    I = np.linspace(1e-3, c.Isc, n); P = np.interp(I, c.I, c.P, right=0.0); ok = P <= R * I * I
    return float(P[ok].max()) if ok.any() else float(c.P_ceiling)


def final_acc(m):
    nm, mk, b = METODOS[m]; fn = mk(); fin, cnt = [], []
    for k, c in enumerate(static_set()):
        rng = np.random.default_rng(7 + 1000 * k); pl = StaticPlantBorde(c, rng=rng); fn(pl, c, rng); Pm = np.array(pl.log_Pmeas); sel = int(np.where(Pm == Pm.max())[0][-1])
        fin.append(100.0 * pl.p_true(max(pl.log_I[sel] * (1 - b), pl.Ib)) / max_alcanzable(c)); cnt.append(len(Pm))
    return m, (np.array(fin), np.array(cnt))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--solo", default=""); a = ap.parse_args()
    solo = [m for m in a.solo.split(",") if m] or list(METODOS)
    with Pool(os.cpu_count() or 4) as pool: R = dict(pool.map(final_acc, solo + ([] if "msapso" in solo else ["msapso"])))
    base = R["msapso"][0]; ruta = "resultados/est_borde.json"; old = json.load(open(ruta)) if os.path.exists(ruta) else {}
    print(f"{'metodo':12s} | med   | exactitud media vs alcanzable | perdida vs MSAPSO: media / p95 / p99 / max | >3 pp")
    for m in R:
        f, n = R[m]; d = base - f
        old[m] = dict(med=float(n.mean()), exact=float(f.mean()), media=float(d.mean()), p95=float(np.percentile(d, 95)), p99=float(np.percentile(d, 99)), max=float(d.max()), gt3=float(100 * np.mean(d > 3)))
        print(f"{m:12s} | {n.mean():5.1f} | {f.mean():8.2f} %                    | {d.mean():+.3f} / {np.percentile(d,95):5.2f} / {np.percentile(d,99):5.2f} / {d.max():6.2f} | {100*np.mean(d>3):4.1f} %")
    json.dump(old, open(ruta, "w"), indent=1)
