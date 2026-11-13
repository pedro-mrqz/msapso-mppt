"""
construir_html.py — Arma simulador.html (UN solo archivo, sin dependencias ni servidor) a partir de:
  resultados/traces.json  corridas grabadas con grabar.py      resultados/dyn.json y est.json  cifras de campaña (campana.py)
  metodos.py (nombres)    fichas.py (textos del boton ⓘ)       plantilla.html (el visor: HTML + CSS + JS)
USO: python construir_html.py        -> simulador.html
El navegador solo REPRODUCE las trazas: no reimplementa ningun algoritmo. Para cambiar el aspecto o los controles edita plantilla.html y vuelve a correr este script.
"""
import os, sys, json
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
import numpy as np
from pathlib import Path
from metodos import METODOS
import fichas

R_ = Path("resultados")
def boot(d, B=3000):
    rb = np.random.default_rng(0); i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
T = json.load(open(R_ / "traces.json")); dyn = [a for a in json.load(open(R_ / "dyn.json")) if a["idx"] >= 1200]; est = json.load(open(R_ / "est.json"))
en_trazas = {k.split("|")[-1] for k in T["runs"]}
ids = [m for m in METODOS if m in en_trazas]
faltan = [m for m in METODOS if m not in en_trazas]
if faltan: print("AVISO: sin trazas grabadas (python grabar.py --solo ...):", faltan)
tabla = {}
full = np.array([a["msapso"][0] for a in dyn]); v7 = np.array([a["v7"][0] for a in dyn])
for m in ids:
    if m not in est or not all(m in a for a in dyn): print(f"AVISO: {m} no tiene cifras de campaña (python campana.py dyn|est --solo {m}); no aparece en la tabla de resultados"); continue
    e = np.array([a[m][0] for a in dyn]); tabla[m] = dict(vs_full=boot(e - full), vs_v7=boot(e - v7), pierde3=float(100 * np.mean(e - full < -3)), reinicios=float(np.mean([a[m][2] for a in dyn])), **est[m])
fmt = lambda t: f"{t[0]:+.2f} pp [{t[1]:+.2f}, {t[2]:+.2f}]"
def res_html(m):
    if m not in tabla: return "<p class='res'><i>Este método aún no tiene cifras de campaña: corre <code>python campana.py dyn --solo %s</code> y <code>python campana.py est --solo %s</code>.</i></p>" % (m, m)
    t = tabla[m]
    return (f"<p class='res'><b>Resultado en las campañas</b> (1200 escenarios de confirmación, nunca usados para elegir parámetros): energía contra el MSAPSO del paper {fmt(t['vs_full'])}; contra la V7 {fmt(t['vs_v7'])}; "
            f"pierde más de 3 pp frente al MSAPSO en el {t['pierde3']:.0f} % de los escenarios. <b>Cola estática</b> (1000 curvas, una sola búsqueda sin cambios de sombra): {t['med']:.0f} mediciones, pérdida media {t['media']:.2f} pp, "
            f"p99 {t['p99']:.1f} pp, peor caso {t['max']:.1f} pp.</p>")
GENERICA = "<p><b>Método sin ficha.</b> Agrega una entrada en <code>fichas.py</code> con el mismo id (<code>%s</code>) para describirlo aquí.</p>"
metodos = [dict(id=m, name=METODOS[m][0], short=fichas.SHORT.get(m, "Método nuevo"), ficha=fichas.FICHA.get(m, GENERICA % m) + res_html(m), b=METODOS[m][2]) for m in ids]
D = dict(scen=T["scen"], runs=T["runs"], wk=[str(w) for w in T["waits"]], nk=[str(n) for n in T["noises"]], waits=T["waits"], noises=T["noises"], metodos=metodos, tabla=tabla)
tpl = Path("plantilla.html").read_text(encoding="utf-8")
html = tpl.replace("/*DATA*/null", json.dumps(D, ensure_ascii=False, separators=(",", ":")))
Path("simulador.html").write_text(html, encoding="utf-8"); print("listo: simulador.html", round(len(html) / 1e6, 2), "MB;", len(ids), "métodos,", len(T["scen"]), "escenarios")
