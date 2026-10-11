"""
evaluar_baselines_V2.py — Evalua el MSAPSO FIEL (y variantes declaradas) en el simulador V2.
  A) 4 casos estaticos (1 s cada uno), con t_wait = 0.5 ms (valor del paper) y 5 ms.
  B) 12 transiciones de sombra (todos los pares ordenados de los 4 casos), 1 s + 1 s como en el paper (Fig. 14).
Metrica principal: eficiencia de ENERGIA entregada = (energia del panel) / (P_alcanzable * tiempo).
Resultados -> resultados_V2/baselines_V2.json y .txt
"""
import sys, json, itertools
sys.path.insert(0, ".")
import numpy as np
from pvsim_V2.pvcurve_V2 import load_case
from pvsim_V2.msapso_V2 import MSAPSOController, run_scenario, segment_metrics

CASES = [load_case(i) for i in range(4)]
V1_LIKE = dict(restart_mode="none", alternate=False, gbest_from="reference", beta_max=0.9, t_max=30,
               fracs=tuple(np.linspace(0.05, 0.95, 5)))     # reconstruccion del 'baseline' de la V1 (5 part., sin reinicio, orden fijo, Gbest=referencia)

VARIANTS = {
    "MSAPSO fiel (paper)":                dict(),
    "1.a pasada descendente (Fig.6 lit.)": dict(first_pass="descending"),
    "reinicio temprano (cada pasada)":    dict(restart_mode="early"),
    "sin reinicio":                       dict(restart_mode="none"),
    "sin alternar barrido":               dict(alternate=False),
    "Gbest = referencia (estilo V1)":     dict(gbest_from="reference"),
    "baseline V1 reconstruido":           V1_LIKE,
}


def make(wait, kw):
    kw = dict(kw)
    w = 0.975e-3 if kw is V1_LIKE else wait
    return lambda: MSAPSOController(wait, **kw)


out = {"static": {}, "pairs": {}}
lines = []
def P(s=""):
    print(s); lines.append(s)

for wait in (0.5e-3, 5e-3):
    P(f"\n=== A) CASOS ESTATICOS, 1 s, t_wait = {wait*1e3:.1f} ms  (cada celda: eficiencia final % / energia % / reinicios) ===")
    P(f"{'variante':40s}" + "".join(f"{'caso '+str(i+1):>20s}" for i in range(4)))
    for name, kw in VARIANTS.items():
        w = 1e-3 if name.startswith("baseline V1") else wait
        row = f"{name:40s}"
        res = []
        for idx, c in enumerate(CASES):
            log = run_scenario(lambda: MSAPSOController(w, **kw), [(c, 1.0)], w)
            m = segment_metrics(log, 0); res.append(m)
            row += f"{m['eff_final']:9.1f}/{m['eff_energy']:5.1f}/{m['n_restarts']:2d}"
        out["static"][f"{name}|{wait*1e3:.1f}ms"] = res
        P(row)

pairs = [(a, b) for a in range(4) for b in range(4) if a != b]
for wait in (5e-3, 0.5e-3):
    search = 25 * 7 * wait
    dur = max(1.0, 2.5 * search)
    P(f"\n=== B) TRANSICIONES (12 pares ordenados), t_wait = {wait*1e3:.1f} ms, segmentos de {dur:.2f} s — metricas del 2.o segmento (tras el cambio) ===")
    P(f"{'variante':40s}{'energia %':>11s}{'final %':>10s}{'t99 ms':>9s}{'reinic.':>9s}{'#final>=99':>11s}   | pares a<b (6): energia %")
    for name, kw in VARIANTS.items():
        w = 1e-3 if name.startswith("baseline V1") else wait
        d = max(1.0, 2.5 * 25 * 7 * w)
        ms = []
        for (a, b) in pairs:
            log = run_scenario(lambda: MSAPSOController(w, **kw), [(CASES[a], d), (CASES[b], d)], w)
            m = segment_metrics(log, 1); m["pair"] = f"{a+1}->{b+1}"; ms.append(m)
        out["pairs"][f"{name}|{wait*1e3:.1f}ms"] = ms
        e = np.mean([m["eff_energy"] for m in ms]); f = np.mean([m["eff_final"] for m in ms])
        t99 = np.nanmean([m["t99"] for m in ms]) * 1e3; r = np.mean([m["n_restarts"] for m in ms])
        e6 = np.mean([m["eff_energy"] for m in ms if int(m["pair"][0]) < int(m["pair"][-1])])
        P(f"{name:40s}{e:11.2f}{f:10.2f}{t99:9.1f}{r:9.2f}{sum(m['eff_final']>=99 for m in ms):9d}/12   | {e6:6.2f}")
    P(f"\nDetalle por par — MSAPSO fiel (paper), t_wait = {wait*1e3:.1f} ms:")
    P(f"{'par':6s}{'energia %':>11s}{'final %':>10s}{'t99 ms':>9s}{'reinic.':>9s}")
    for m in out["pairs"][f"MSAPSO fiel (paper)|{wait*1e3:.1f}ms"]:
        P(f"{m['pair']:6s}{m['eff_energy']:11.2f}{m['eff_final']:10.2f}{m['t99']*1e3:9.1f}{m['n_restarts']:9d}")

json.dump(out, open("resultados_V2/baselines_V2.json", "w"), indent=1, default=float)
open("resultados_V2/baselines_V2.txt", "w").write("\n".join(lines))
