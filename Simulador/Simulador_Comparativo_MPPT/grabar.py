"""
grabar.py — Graba, ventana por ventana, la corrida REAL (simulador dinamico Boost + Super-Twisting) de cada metodo sobre los escenarios del catalogo.
El visor (simulador.html) solo REPRODUCE estas trazas: lo que ves es exactamente lo que produce el codigo de los metodos.

USO:
  python grabar.py                          graba TODOS los metodos en TODOS los escenarios del catalogo (unos minutos)
  python grabar.py --solo mi_metodo         graba solo ese metodo y lo MEZCLA con lo ya grabado (rapido; lo normal al probar un metodo nuevo)
  python grabar.py --agregar 1234 --nombre "Mi escenario" --texto "Por qué es interesante"
                                            agrega el escenario 1234 (cualquier indice 0-2399) al catalogo y lo graba con todos los metodos
Cada escenario se graba con tiempo de espera {5, 2, 1, 0.5} ms x ruido {0, 1, 2} W. Mismo escenario y misma semilla para todos los metodos.
El catalogo vive en catalogo.json (id, nombre, texto); editalo para renombrar o quitar escenarios y vuelve a correr grabar.py.
Escenarios especiales: id "trans" = transiciones de sombra (caso real 1 -> sintetico 2 -> sintetico 5 -> caso real 3 -> sintetico 10 -> caso real 4).
"""
import os, sys, json, zlib, base64, argparse
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
from multiprocessing import Pool
import numpy as np
from entorno import make_scenario, DynamicPlantLogged
from algoritmos.msapso_early import SyntheticPVCurve, random_shading_mix
from baselines import scenarios
from metodos import METODOS

WAITS = [5e-3, 2e-3, 1e-3, 5e-4]; NOISES = [0.0, 1.0, 2.0]; R_ = "resultados/"

def run_trace(search_fn, curves, bounds, wait, total, seed, noise_w, backoff):
    """Copia EXACTA de entorno.run_ops (mismo orden de llamadas y mismos numeros aleatorios) que ademas anota la fase de cada ventana: 0 busqueda, 1 fijo/asentamiento, 2 ventana que dispara reinicio."""
    THRESH, SETTLE_MAX = 5.0, 10
    sched = {b: c for b, c in zip(bounds, curves) if b > 0}
    pl = DynamicPlantLogged(curves[0], wait, noise_w=noise_w, rng=np.random.default_rng(seed), schedule=sched); rng = np.random.default_rng(seed + 1); phase = []
    while len(pl.log_E) < total:
        n0 = len(pl.log_E); search_fn(pl, pl.curve, rng); n1 = len(pl.log_E); phase += [0] * (n1 - n0)
        j = n0 + int(np.argmax(pl.log_Pmeas[n0:n1])); I_sel = pl.log_Ipv[j] * (1.0 - backoff)
        Pb, _ = pl.run(wait, I_sel); phase.append(1)
        for _ in range(SETTLE_MAX):
            Pn, _ = pl.run(wait, I_sel); phase.append(1); done = abs(Pn - Pb) < 1.0; Pb = Pn
            if done: break
        while len(pl.log_E) < total:
            Pm, _ = pl.run(wait, I_sel); phase.append(1)
            if abs(Pb - Pm) >= THRESH: phase[-1] = 2; break
    E = np.array(pl.log_E[:total]); ref = 0.0; edges = list(bounds) + [total]
    for c, a, b in zip(curves, edges[:-1], edges[1:]): ref += c.P_ceiling * wait * (b - a)
    return 100 * E.sum() / ref, dict(Ipv=np.array(pl.log_Ipv[:total]), P=np.array(pl.log_Ptrue[:total]), E=E, ph=np.array(phase[:total], dtype=np.uint8))

def enc(tr, wait):
    b = np.concatenate([np.clip(np.round(tr["Ipv"] * 4000), 0, 65535).astype("<u2").view(np.uint8), np.clip(np.round(tr["P"] * 50), 0, 65535).astype("<u2").view(np.uint8),
                        np.clip(np.round(tr["E"] / wait * 100), 0, 65535).astype("<u2").view(np.uint8), tr["ph"]])
    return base64.b64encode(zlib.compress(b.tobytes(), 9)).decode()

def pack_curve(c, n=240):
    g = np.linspace(0, float(c.Isc), n); P = np.interp(g, c.I, c.P, right=0.0)
    return dict(Isc=round(float(c.Isc), 4), Pmax=round(float(c.P_ceiling), 2), Ic=round(float(c.I_ceiling), 4), Pg=round(float(c.P_gmpp), 2), Ig=round(float(c.I_gmpp), 4), P=[round(float(v), 1) for v in P])

def transiciones():
    real, _ = scenarios(); r = np.random.default_rng(11); syn = [SyntheticPVCurve(random_shading_mix(r)) for _ in range(12)]
    seq = [("Caso real 1", real[0]), ("Sintético 2", syn[1]), ("Sintético 5", syn[4]), ("Caso real 3", real[2]), ("Sintético 10", syn[9]), ("Caso real 4", real[3])]
    curves = [c for _, c in seq]; bounds = [i * 300 for i in range(6)]
    return dict(idx=-1, wait=5e-3, ruido=0.0, regimen="transiciones"), curves, bounds, 1800

def get(sid):
    if sid == "trans": return transiciones()
    return make_scenario(int(sid))

def job(a):
    sid, wait, noise, m = a; meta, curves, bounds, total = get(sid); nm, mk, b = METODOS[m]
    e, tr = run_trace(mk(), curves, bounds, wait, total, 777777 if sid == "trans" else int(sid), noise, b); return (str(sid), wait, noise, m), (e, enc(tr, wait))

def escenario_json(sid, name, text):
    meta, curves, bounds, total = get(sid); uniq = []; seq = []
    for c in curves:
        for k, u in enumerate(uniq):
            if u is c: seq.append(k); break
        else: uniq.append(c); seq.append(len(uniq) - 1)
    return dict(id=str(sid), name=name, text=text, total=total, bounds=bounds, seq=seq, curves=[pack_curve(c) for c in uniq], names=None,
                meta=dict(wait=meta["wait"], ruido=meta["ruido"], panel=meta.get("panel", "base"), regimen=meta["regimen"], idx=meta["idx"]))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--solo", default=""); ap.add_argument("--agregar", default=""); ap.add_argument("--nombre", default=""); ap.add_argument("--texto", default=""); a = ap.parse_args()
    solo = [m for m in a.solo.split(",") if m] or list(METODOS)
    for m in solo: assert m in METODOS, f"metodo desconocido: {m} (ver metodos.py)"
    cat = json.load(open("catalogo.json", encoding="utf-8"))
    if a.agregar:
        if not any(str(c["id"]) == a.agregar for c in cat): cat.append(dict(id=a.agregar, name=a.nombre or f"Escenario {a.agregar}", text=a.texto or f"Escenario {a.agregar} de la campaña."))
        json.dump(cat, open("catalogo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1); cat = [c for c in cat if str(c["id"]) == a.agregar]; parcial = True
    else: parcial = bool(a.solo)
    ruta = R_ + "traces.json"; T = json.load(open(ruta)) if (os.path.exists(ruta) and (parcial or a.solo)) else dict(scen=[], runs={})
    jobs = [(c["id"], w, nz, m) for c in cat for w in WAITS for nz in NOISES for m in solo]
    with Pool(os.cpu_count() or 4) as pool: Rr = pool.map(job, jobs, chunksize=6)
    for k, v in Rr: T["runs"]["|".join(map(str, k))] = dict(e=round(v[0], 3), d=v[1])
    have = {str(s["id"]): s for s in T["scen"]}
    for c in cat:
        if str(c["id"]) not in have: have[str(c["id"])] = escenario_json(c["id"], c["name"], c["text"])
        else: have[str(c["id"])].update(name=c["name"], text=c["text"])
    full_cat = json.load(open("catalogo.json", encoding="utf-8")); T["scen"] = [have[str(c["id"])] for c in full_cat if str(c["id"]) in have]
    T["waits"] = WAITS; T["noises"] = NOISES; json.dump(T, open(ruta, "w")); print(len(T["scen"]), "escenarios,", len(T["runs"]), "corridas,", round(os.path.getsize(ruta) / 1e6, 2), "MB ->", ruta)
