"""
probar_metodo.py — Prueba RAPIDA de un metodo (unos 30-60 s): lo compara contra el MSAPSO del paper y la V7 con los mismos escenarios y la misma metrica de las campañas.
USO:
  python probar_metodo.py mi_metodo                   (usa 150 escenarios dinamicos de confirmacion y 200 curvas estaticas)
  python probar_metodo.py mi_metodo --n 600 --curvas 1000    (mas escenarios = intervalos mas estrechos, tarda mas)
Muestra: energia dinamica (diferencia en puntos porcentuales con intervalo de confianza 95 %, bootstrap pareado), cuantos escenarios pierden > 3 pp frente al MSAPSO,
y la COLA estatica (perdida media, p99 y peor caso de exactitud final). Referencia de aceptacion del proyecto: cola con media <= 0.5 pp y p99 <= 3 pp.
Es solo una vista rapida: para cifras oficiales usa  python campana.py dyn --solo mi_metodo  y  python campana.py est --solo mi_metodo.
"""
import os, sys, argparse
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
from multiprocessing import Pool
import numpy as np
from campana import task, static_set, boot, METODOS
from pvsim.static_plant import StaticPlant

def est(args):
    m, curvas = args; nm, mk, b = METODOS[m]; fn = mk(); fin, cnt = [], []
    for k, c in enumerate(static_set()[:curvas]):
        rng = np.random.default_rng(7 + 1000 * k); pl = StaticPlant(c, rng=rng); fn(pl, c, rng); Pm = np.array(pl.log_Pmeas); sel = int(np.where(Pm == Pm.max())[0][-1])
        fin.append(100.0 * pl.p_true(pl.log_I[sel] * (1 - b)) / c.P_gmpp); cnt.append(len(Pm))
    return np.array(fin), np.array(cnt)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("metodo"); ap.add_argument("--n", type=int, default=150); ap.add_argument("--curvas", type=int, default=200); a = ap.parse_args()
    assert a.metodo in METODOS, f"'{a.metodo}' no esta en metodos.py"
    ms = list(dict.fromkeys(["msapso", "v7", a.metodo])); nproc = os.cpu_count() or 4
    with Pool(nproc) as pool:
        A = pool.map(task, [(i, ms) for i in range(1200, 1200 + a.n)], chunksize=2); S = pool.map(est, [(m, a.curvas) for m in ms])
    E = {m: np.array([r[m][0] for r in A]) for m in ms}; F = {m: S[i] for i, m in enumerate(ms)}; base = F["msapso"][0]
    print(f"\n{METODOS[a.metodo][0]}  (b = {METODOS[a.metodo][2]})   —   {a.n} escenarios dinámicos, {a.curvas} curvas estáticas")
    print(f"{'método':26s} | energía media | vs MSAPSO (pp, IC 95 %)   | vs V7 (pp, IC 95 %)      | pierde>3pp | med. | cola: media / p99 / máx (pp)")
    for m in ms:
        d1, d2 = boot(E[m] - E["msapso"]), boot(E[m] - E["v7"]); dl = base - F[m][0]
        print(f"{METODOS[m][0]:26s} | {E[m].mean():10.2f} % | {d1[0]:+6.2f} [{d1[1]:+.2f},{d1[2]:+.2f}] | {d2[0]:+6.2f} [{d2[1]:+.2f},{d2[2]:+.2f}] | {100*np.mean(E[m]-E['msapso']<-3):8.0f} % | {F[m][1].mean():4.0f} | {dl.mean():5.2f} / {np.percentile(dl,99):5.2f} / {dl.max():5.2f}")
    dl = base - F[a.metodo][0]; ok = dl.mean() <= 0.5 and np.percentile(dl, 99) <= 3
    print(f"\nCola estática: {'CUMPLE' if ok else 'NO cumple'} el umbral del proyecto (media ≤ 0.5 pp y p99 ≤ 3 pp).")
