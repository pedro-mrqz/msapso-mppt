"""
campana_mitigacion_V7.py — V7.5: la campana Monte Carlo (campana_V7.py) mostro que la V7 empata en promedio con un cambio unico pero tiene una COLA IZQUIERDA (8 % de los escenarios pierde > 3 pp; el peor, −53 pp).
Hipotesis: tras la parada anticipada, el punto elegido por la potencia MEDIDA puede quedar justo mas alla del «precipicio» de la curva P-I (la medicion es una foto transitoria) y, una vez asentado, la potencia
real es mucho menor; ademas, el cambio de punto genera reinicios falsos. Mitigaciones MINIMAS (una comparacion o un parametro), probadas sobre LOS MISMOS escenarios de la campana (mismas semillas):
  ret3        : parking 3 % por debajo de la corriente elegida.
  ret3+hist   : ret3 + histeresis anti-vaiven (si la busqueda repetida da lo mismo, se tolera 10 W de deriva).
  verif       : VERIFICACION de consistencia: tras asentar, si la potencia asentada es < 90 % de la potencia medida en la busqueda (foto transitoria enganosa), se ejecuta una vez el MSAPSO completo (25 pasadas) y se vuelve a asentar.
  verif+ret3  : verificacion + retroceso de 3 %.
Se aplican solo a la parada principal de la V7; el MSAPSO completo y la parada principal sin cambios son los de la campana original (mismos escenarios, mismas semillas).
USO: python3 campana_mitigacion_V7.py run <fragmento> <n_fragmentos> <n_escenarios>   |   python3 campana_mitigacion_V7.py agregar
"""
import json, sys, os, glob
from campana_V7 import *
from pvsim_V7.static_plant_V7 import DynamicPlantLogged

SETTLE_MAX = 10; THRESH = 5.0
FULL_FN = METHODS[0][1]; V7_FN = METHODS[1][1]


def run_ops_mit(curves, bounds, wait, total, seed, noise_w, backoff=0.0, hyst=False, verify=0.0):
    sched = {b: c for b, c in zip(bounds, curves) if b > 0}
    pl = DynamicPlantLogged(curves[0], wait, noise_w=noise_w, rng=np.random.default_rng(seed), schedule=sched); rng = np.random.default_rng(seed + 1); nr = 0; prev = None
    def settle(I):
        Pb, _ = pl.run(wait, I)
        for _ in range(SETTLE_MAX):
            Pn, _ = pl.run(wait, I); done = abs(Pn - Pb) < 1.0; Pb = Pn
            if done: break
        return Pb
    while len(pl.log_E) < total:
        n0 = len(pl.log_E); V7_FN(pl, pl.curve, rng); n1 = len(pl.log_E)
        j = n0 + int(np.argmax(pl.log_Pmeas[n0:n1])); I_sel = pl.log_Ipv[j]; P_meas = pl.log_Pmeas[j]
        Pb = settle(I_sel * (1 - backoff))
        if verify > 0 and Pb < (1 - verify) * P_meas and len(pl.log_E) < total:         # foto transitoria enganosa: se completa la busqueda con el MSAPSO completo
            n0 = len(pl.log_E); FULL_FN(pl, pl.curve, rng); n1 = len(pl.log_E)
            j = n0 + int(np.argmax(pl.log_Pmeas[n0:n1])); I_sel = pl.log_Ipv[j]; Pb = settle(I_sel * (1 - backoff))
        I_use = I_sel * (1 - backoff); th = THRESH
        if hyst and prev is not None and abs(I_use - prev[0]) < 0.15 and abs(Pb - prev[1]) < 10.0: th = 2 * THRESH
        prev = (I_use, Pb)
        while len(pl.log_E) < total:
            Pm, _ = pl.run(wait, I_use)
            if abs(Pb - Pm) >= th: nr += 1; break
    E = np.array(pl.log_E[:total]); ref = 0.0; edges = list(bounds) + [total]
    for c, a, b in zip(curves, edges[:-1], edges[1:]): ref += c.P_ceiling * wait * (b - a)
    return 100 * E.sum() / ref, nr


VARIANTS = [("ret3", dict(backoff=0.03)), ("ret3+hist", dict(backoff=0.03, hyst=True)), ("verif", dict(verify=0.10)), ("verif+ret3", dict(verify=0.10, backoff=0.03))]

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "run":
        shard, nshard, N = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]); outf = f"resultados_V7/campana_mit_fragmento_{shard}.jsonl"; done = set()
        if os.path.exists(outf): done = {json.loads(l)["idx"] for l in open(outf)}
        with open(outf, "a") as f:
            for idx in range(shard, N, nshard):
                if idx in done: continue
                meta, curves, bounds, total = make_scenario(idx); rec = dict(idx=idx)
                for name, kw in VARIANTS:
                    e, nr = run_ops_mit(curves, bounds, meta["wait"], total, idx, meta["ruido"], **kw); rec[name] = dict(e=e, nr=nr)
                f.write(json.dumps(rec) + "\n"); f.flush()
        print(f"fragmento {shard} listo", flush=True)
    elif mode == "agregar":
        _b = ["resultados_V7/campana_V7.jsonl"] if os.path.exists("resultados_V7/campana_V7.jsonl") else glob.glob("resultados_V7/campana_fragmento_*.jsonl")
        _m = ["resultados_V7/campana_mitigacion_V7.jsonl"] if os.path.exists("resultados_V7/campana_mitigacion_V7.jsonl") else glob.glob("resultados_V7/campana_mit_fragmento_*.jsonl")
        base = {json.loads(l)["idx"]: json.loads(l) for fn in _b for l in open(fn)}
        mit = {json.loads(l)["idx"]: json.loads(l) for fn in _m for l in open(fn)}
        ids = sorted(set(base) & set(mit)); rb = np.random.default_rng(0); lines = []
        def P(s=""): print(s, flush=True); lines.append(s)
        def boot(d, B=3000):
            i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
        P(f"MITIGACIONES sobre los mismos {len(ids)} escenarios de la campana. Diferencia de energia respecto al MSAPSO completo (pp).")
        P(f"{'variante':22s} | media [IC95 %] | mediana | p1 / p5 | peor | pierde (<-0.5) | pierde mucho (<-3) | (<-5) | unico: media | reinicios")
        meths = [("V7 principal (sin cambios)", lambda i: base[i]["principal"]["e"], lambda i: base[i]["principal"]["nr"])] + [(n, (lambda n: lambda i: mit[i][n]["e"])(n), (lambda n: lambda i: mit[i][n]["nr"])(n)) for n, _ in VARIANTS]
        out = {}
        for name, fe, fr in meths:
            d = np.array([fe(i) - base[i]["full"]["e"] for i in ids]); u = np.array([fe(i) - base[i]["full"]["e"] for i in ids if base[i]["regimen"] == "unico"]); b = boot(d)
            P(f"{name:26s} | {b[0]:+.2f} [{b[1]:+.2f}, {b[2]:+.2f}] | {np.median(d):+.2f} | {np.percentile(d,1):+.1f} / {np.percentile(d,5):+.1f} | {d.min():+.1f} | {100*np.mean(d<-0.5):.1f} % | {100*np.mean(d<-3):.1f} % | {100*np.mean(d<-5):.1f} % | {u.mean():+.2f} | {np.mean([fr(i) for i in ids]):.1f}")
            out[name] = dict(media=b, mediana=float(np.median(d)), p1=float(np.percentile(d, 1)), p5=float(np.percentile(d, 5)), peor=float(d.min()), pierde=float(np.mean(d < -0.5)), pierde_mucho=float(np.mean(d < -3)), pierde_muy_mucho=float(np.mean(d < -5)), unico=float(u.mean()))
        P("\nPor regimen (media de la diferencia vs MSAPSO completo, pp):")
        for reg in ("unico", "moderado", "alto", "muy alto", "flicker", "estable"):
            ii = [i for i in ids if base[i]["regimen"] == reg]
            P(f"  {reg:9s} n={len(ii):4d} | " + " | ".join(f"{n[:12]}: {np.mean([fe(i) - base[i]['full']['e'] for i in ii]):+.2f}" for n, fe, fr in meths))
        open("resultados_V7/campana_mitigacion_V7.txt", "w").write("\n".join(lines)); json.dump(out, open("resultados_V7/campana_mitigacion_V7.json", "w"))
