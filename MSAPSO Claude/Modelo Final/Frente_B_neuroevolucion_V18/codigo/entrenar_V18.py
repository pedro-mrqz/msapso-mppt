"""
entrenar_V18.py — Entrena por CEM sobre los pesos las redes de la rejilla V18 (ver diseno_V18.md). Datos: los de la V11 (30000 curvas, semilla 1111).
Monitoreo: 2000 curvas con semilla 2222 (del mismo generador; no son validacion ni prueba). Referencia: la red supervisada de la V11 en el mismo monitoreo.
USO: python3 entrenar_V18.py        -> V18 (objetivo: potencia en el punto predicho), 6 redes
     python3 entrenar_V18.py v181   -> V18.1 (objetivo: cadena completa con refinado), 8 redes; se agregan a los mismos archivos
-> resultados_V18/redes_V18.npz, entrenamiento_V18.json|txt
"""
import os
for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[v] = "1"
import json, sys, time
from multiprocessing import Pool
import numpy as np
from neuroevolucion_V18 import NECfg, entrenar, make_tables, lookup, forward_batch, ne_name, n_params, Red, cadena
from metodos_V18 import red

GENS = 2000
GRID_NE = [NECfg(h=h, cola=c, gens=GENS) for h in ((16, 16), (32, 32), (64, 64)) for c in (0.0, 1.0)]
GRID_NE1 = [NECfg(h=h, cola=c, gens=GENS, batch=500, s0_ref=s) for h in ((16, 16), (64, 64)) for c in (0.0, 1.0) for s in (0.03, 0.1)]   # V18.1
X = T = Xm = ym = Tm = None


def job(c):
    t = time.time(); mu, log = entrenar(c, X, T, Xm, Tm); return c, mu, log, time.time() - t


def resumen(pred, ym, Tm, s0=0.1):
    p = lookup(Tm, pred[None])[0]; q = cadena(Tm, pred[None].astype(np.float32), s0, np.random.default_rng(99).standard_normal((len(ym), 12, 7)).astype(np.float32))[0]
    return dict(cadena_media=float(q.mean()), cadena_bajo_98=float(100 * np.mean(q < 0.98)), potencia_media=float(p.mean()), potencia_p1=float(np.percentile(p, 1)), pct_bajo_90=float(100 * np.mean(p < 0.9)), error_x_medio=float(np.abs(np.clip(pred, 0, 1) - ym).mean()))


if __name__ == "__main__":
    X, _, T = make_tables(30000, 1111); Xm, ym, Tm = make_tables(2000, 2222)
    v181 = len(sys.argv) > 1 and sys.argv[1] == "v181"; grid = GRID_NE1 if v181 else GRID_NE
    with Pool(len(grid)) as p: R = p.map(job, grid, chunksize=1)
    previo = os.path.exists("resultados_V18/redes_V18.npz")              # se agrega a lo ya entrenado (V18 y V18.1 conviven en los mismos archivos)
    out = json.load(open("resultados_V18/entrenamiento_V18.json")) if previo else dict(datos="make_tables(30000, 1111) (los de la V11); monitoreo make_tables(2000, 2222)", redes={})
    arr = dict(np.load("resultados_V18/redes_V18.npz")) if previo else {}
    for c, mu, log, tt in R:
        n = ne_name(c)
        if n + "|theta" in arr: print(f"{n}: reentrenada; pesos identicos a los guardados: {np.array_equal(arr[n + '|theta'], mu)}", flush=True)
        n = ne_name(c); out["redes"][n] = dict(cfg=dict(c.__dict__), params=n_params(c.h), segundos=tt, registro=log); arr[n + "|theta"] = mu; arr[n + "|h"] = np.array(c.h)
    lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    v11 = resumen(red("V11").predict(Xm), ym, Tm); out["V11 (retropropagacion, 64x64)"] = v11
    P("ENTRENAMIENTO V18 / V18.1: CEM sobre los pesos del MLP. Monitoreo: 2000 curvas (2222). 'solo red' = barrido de 7 + 1 medicion en la prediccion;")
    P("  'cadena' = barrido + red + CEM sobre la corriente (sigma0 de la red; 0.1 si no tiene), simulado sin ruido: potencia media y % de curvas < 98 %")
    P("  Redes sin 'ref': objetivo = potencia en el punto predicho (V18). Con 'ref=s0': objetivo = cadena completa con ese sigma0 (V18.1).")
    P(f"  {'red':28s} | params | tiempo  | solo red: media | p1 | % < 90 % | error |x - x*| | cadena: media | % < 98 %")
    P(f"  {'V11 (retropropagacion)':28s} | {4801:6d} |   --    | {v11['potencia_media']:.4f} | {v11['potencia_p1']:.3f} | {v11['pct_bajo_90']:5.1f} | {v11['error_x_medio']:.4f} | {v11['cadena_media']:.4f} | {v11['cadena_bajo_98']:5.1f}")
    for n, d in out["redes"].items():
        c = NECfg(**{**d["cfg"], "h": tuple(d["cfg"]["h"])}); r = resumen(Red.from_theta(arr[n + "|theta"], c.h).predict(Xm), ym, Tm, c.s0_ref or 0.1); d["monitoreo"] = r
        P(f"  {n:28s} | {d['params']:6d} | {d['segundos']:5.0f} s | {r['potencia_media']:.4f} | {r['potencia_p1']:.3f} | {r['pct_bajo_90']:5.1f} | {r['error_x_medio']:.4f} | {r['cadena_media']:.4f} | {r['cadena_bajo_98']:5.1f}")
    np.savez("resultados_V18/redes_V18.npz", **arr)
    json.dump(out, open("resultados_V18/entrenamiento_V18.json", "w"), indent=1); open("resultados_V18/entrenamiento_V18.txt", "w").write("\n".join(lines))
