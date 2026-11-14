"""
gif_V7.py — GIF animado de la V7 (MSAPSO con parada anticipada) sobre un patron de sombra: un cuadro por medicion.
Izquierda: curva P-I, las 7 particulas (posiciones de la pasada), puntos ya medidos y Gbest. Derecha: dispersion del enjambre por pasada y umbral de parada (0.02).
Tras la parada de la V7 se muestra en gris lo que el MSAPSO completo habria seguido haciendo hasta la pasada 25.
Uso: python3 gif_V7.py [caso 0-3]  -> graficas_V7/anim_V7_casoN.gif
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import io
from pvsim_V7.msapso_V7 import Swarm
from pvsim_V7.static_plant_V7 import StaticPlant
from baselines_nivel1_V7 import scenarios, paper_beta
from msapso_early_V7 import Rule, should_stop, T_MAX

CASO = int(sys.argv[1]) if len(sys.argv) > 1 else 2
RULE = Rule("disp", delta=0.02, t_min=3)
curve = scenarios()[0][CASO]
pl = StaticPlant(curve); sw = Swarm(first_pass="ascending"); sw.restart(curve.Isc, first=True)

# --- simulacion completa (25 pasadas), guardando cada medicion ---
ev, passes, hist, stop_pass = [], [], [], None
for p in range(1, T_MAX + 1):
    xs = sw.x.copy(); order = np.argsort(xs)
    if sw.direction == "descending": order = order[::-1]
    for i in order:
        P, _ = pl.run(1.0, xs[i])
        if P >= sw.Pbest: sw.Pbest, sw.Gbest = P, pl.Ipv
        ev.append(dict(p=p, I=xs[i], P=P, xs=xs, G=sw.Gbest, Pb=sw.Pbest))
    hist.append(sw.Pbest); disp = sw.dispersion(); passes.append(disp)
    sw.update(paper_beta(sw.t, t_max=T_MAX))
    if stop_pass is None and should_stop(RULE, hist, disp): stop_pass = p
Pmax = float(np.max(curve.P)); n_v7 = 7 * stop_pass

AZ, GR, RJ, VD = "#1f5fa8", "#9aa0a6", "#d9382b", "#1e9e4a"
def frame(k, banner=None, grey=False):
    e = ev[k]; fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw=dict(width_ratios=[1.35, 1]))
    a.plot(curve.I, curve.P, color=AZ, lw=1.8)
    prev = ev[:k]; col = GR if grey else RJ
    if prev: a.scatter([q["I"] for q in prev], [q["P"] for q in prev], s=14, color=col, alpha=.35, zorder=3)
    xs = e["xs"]; a.vlines(xs, 0, [np.interp(x, curve.I, curve.P) for x in xs], color=GR, lw=.8, ls=":", zorder=1)
    a.scatter(xs, [np.interp(x, curve.I, curve.P) for x in xs], s=26, facecolor="white", edgecolor=GR if grey else "#444", zorder=4)
    a.scatter([e["I"]], [e["P"]], s=70, color=col, zorder=6, label="medición actual")
    a.scatter([e["G"]], [np.interp(e["G"], curve.I, curve.P)], marker="D", s=110, color="#7CFC00" if not grey else "#cfd8c0", edgecolor="k", zorder=7, label="Gbest")
    a.set_xlim(0, curve.Isc * 1.03); a.set_ylim(0, Pmax * 1.12); a.set_xlabel("Corriente I (A)"); a.set_ylabel("Potencia P (W)")
    a.set_title(f"Pasada {e['p']}  |  medición {k+1}  |  Pbest = {e['Pb']:.1f} W ({100*e['Pb']/Pmax:.1f} % del máximo)", fontsize=10)
    a.legend(loc="upper left", fontsize=8, framealpha=.9)
    ps = e["p"]; shown = list(range(1, ps + 1)) if (k + 1) % 7 == 0 else list(range(1, ps))
    b.axhline(RULE.delta, color=VD, ls="--", lw=1.2); b.text(T_MAX, RULE.delta * 1.12, "umbral de parada 0.02", color=VD, ha="right", fontsize=8)
    lim = stop_pass if not grey else T_MAX
    b.plot(shown, [passes[i - 1] for i in shown], "o-", color=GR if grey and ps > stop_pass else AZ, ms=4)
    if grey: b.plot(range(1, stop_pass + 1), passes[:stop_pass], "o-", color=AZ, ms=4)
    b.set_xlim(0, T_MAX + 1); b.set_ylim(0, max(passes) * 1.08); b.set_xlabel("Pasada"); b.set_ylabel("Dispersión del enjambre  std(x)/Isc")
    b.set_title("¿Ya convergieron las partículas?", fontsize=10)
    if banner: b.text(.5, .62, banner, transform=b.transAxes, ha="center", fontsize=11, fontweight="bold", color=RJ if not grey else "#555",
                      bbox=dict(boxstyle="round", fc="white", ec=RJ if not grey else GR))
    fig.suptitle(f"V7 — MSAPSO con parada anticipada (caso real {CASO+1})", fontsize=12, fontweight="bold"); fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=80); plt.close(fig); buf.seek(0)
    return Image.open(buf).convert("P", palette=Image.ADAPTIVE)

frames, dur = [], []
for k in range(n_v7):
    frames.append(frame(k)); dur.append(260)
for _ in range(1):
    frames.append(frame(n_v7 - 1, f"PARADA V7: {n_v7} mediciones\nse fija en Gbest")); dur.append(2600)
for p in range(stop_pass + 1, T_MAX + 1):   # lo que seguiría el MSAPSO completo, una imagen por pasada
    frames.append(frame(7 * p - 1, f"MSAPSO completo seguiría...\npasada {p} de {T_MAX} ({7*p} mediciones)", grey=True)); dur.append(220)
frames.append(frame(len(ev) - 1, f"MSAPSO completo: {len(ev)} mediciones\nV7: {n_v7} ({100*(1-n_v7/len(ev)):.0f} % menos), mismo punto", grey=True)); dur.append(4000)
os.makedirs("graficas_V7", exist_ok=True); out = f"graficas_V7/anim_V7_caso{CASO+1}.gif"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=dur, loop=0, optimize=True)
print(out, "| parada en pasada", stop_pass, "| mediciones V7", n_v7, "vs", len(ev), "| Pbest V7 %.2f vs completo %.2f W" % (ev[n_v7-1]["Pb"], ev[-1]["Pb"]), "| techo %.2f" % Pmax, "| MB", os.path.getsize(out)/1e6)
