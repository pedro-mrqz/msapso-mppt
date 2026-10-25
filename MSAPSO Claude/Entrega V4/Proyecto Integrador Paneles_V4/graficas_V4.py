"""graficas_V4.py — Figuras del reporte V4 (lee resultados_V4/*). Paleta de referencia validada (azul #2a78d6 / naranja #eb6834) sobre fondo claro;
referencias en gris; cada barra lleva su valor (etiqueta directa) y hay leyenda."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, GREY, INK, SOFT, BG = "#2a78d6", "#eb6834", "#9a9a94", "#0b0b0b", "#52514e", "#fcfcfb"
OUT = "resultados_V4"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c9c8c2", "axes.facecolor": BG, "figure.facecolor": BG, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.labelcolor": SOFT, "xtick.color": SOFT, "ytick.color": SOFT, "text.color": INK})

base = json.load(open(f"{OUT}/baselines_nivel1_V4.json"))
b = lambda name, g: base[f"{name}|0"][g]
ppo = [json.load(open(f"{OUT}/ppo_N7_K5_s{s}.json")) for s in range(3)]
ppo_e = json.load(open(f"{OUT}/ppo_N7_K5_ent0.1_s0.json"))
# REINFORCE mejor config de la malla (baseline none, sigma 0.05, 'stoch') y valores de la prueba larga
rg = json.load(open(f"{OUT}/reinforce_grid_N7_K5_V4.json"))["none|0.05|stoch"]["mean"]       # [real fin, real ener, sint fin, sint ener, n]

# valores de la cota (resultados_V4/cota_diagnostico_V4.txt, N=7)
cota = dict(real=(97.35, 95.15), synth=(98.12, 96.15))


def fig_comparacion():
    methods = [
        ("MSAPSO fiel\n(175 med.)", b("MSAPSO fiel (Isc real)", "real"), b("MSAPSO fiel (Isc real)", "synth"), "ref"),
        ("Referencia\nsin aprend.\n(12 med.)", b("mejor-de-7 + 5 gauss. (s=0.05)", "real"), b("mejor-de-7 + 5 gauss. (s=0.05)", "synth"), "ref"),
        ("REINFORCE\nMLP (mejor\nconfig.)", None, None, "rl"),
        ("PPO\n(3 sem.)", None, None, "rl"),
        ("PPO + entropía\n(1 sem.)", None, None, "rl"),
        ("Cota\nsupervisada", None, None, "cota"),
    ]
    vals = {  # (real_fin, real_ener, sint_fin, sint_ener)
        0: (b("MSAPSO fiel (Isc real)", "real")["eff_final"], b("MSAPSO fiel (Isc real)", "real")["eff_energy"], b("MSAPSO fiel (Isc real)", "synth")["eff_final"], b("MSAPSO fiel (Isc real)", "synth")["eff_energy"]),
        1: tuple(b("mejor-de-7 + 5 gauss. (s=0.05)", g)[k] for g in ("real", "synth") for k in ("eff_final", "eff_energy")),
        2: (rg[0], rg[1], rg[2], rg[3]),
        3: tuple(np.mean([p["stoch"][g][k] for p in ppo]) for g in ("real", "synth") for k in ("eff_final", "eff_energy")),
        4: tuple(ppo_e["stoch"][g][k] for g in ("real", "synth") for k in ("eff_final", "eff_energy")),
        5: (cota["real"][0], cota["real"][1], cota["synth"][0], cota["synth"][1]),
    }
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), sharey=True)
    for ax, (title, i0) in zip(axes, (("100 patrones sintéticos nuevos", 2), ("4 casos reales (muestra chica)", 0))):
        x = np.arange(len(methods)); w = 0.36
        for j, (lab, col, hatch) in enumerate((("Eficiencia final", BLUE, None), ("Energía (ventana de 200 med.)", ORANGE, None))):
            v = [vals[k][i0 + j] for k in range(len(methods))]
            bars = ax.bar(x + (j - 0.5) * (w + 0.03), v, w, color=col, label=lab if ax is axes[0] else None, edgecolor=BG, linewidth=1.5)
            for k, bar in enumerate(bars):
                if methods[k][3] == "cota":
                    bar.set_alpha(0.45)
                ax.text(bar.get_x() + bar.get_width() / 2, v[k] + 0.25, f"{v[k]:.1f}", ha="center", fontsize=7.5, color=INK)
        ax.set_xticks(x); ax.set_xticklabels([m[0] for m in methods], fontsize=8)
        ax.set_ylim(84, 101.5); ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    axes[0].set_ylabel("% respecto al GMPP")
    h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", ncol=2, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 1.03))
    fig.text(0.01, -0.02, "Cota supervisada (barras tenues): usa el GMPP como etiqueta; es solo diagnóstico, no un método válido. Todos con N = 7, K = 5 salvo el MSAPSO.", fontsize=7.5, color=SOFT)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_comparacion_V4.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_mediciones():
    names = [("MSAPSO fiel (Isc real)", "MSAPSO fiel"), ("regla simple b=0.95,t_max=5 (nom.)", "regla simple"), ("mejor-de-7", "mejor de 7"), ("mejor-de-7 + 5 gauss. (s=0.05)", "mejor de 7 + 5 g."),
             ("mejor-de-10 + 5 gauss. (s=0.05)", "mejor de 10 + 5 g."), ("mejor-de-20", "mejor de 20"), ("mejor-de-20 + 5 gauss. (s=0.05)", "mejor de 20 + 5 g.")]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2))
    for ax, (key, ylab) in zip(axes, (("eff_final", "Eficiencia final (% del GMPP)"), ("eff_energy", "Energía en ventana de 200 mediciones (%)"))):
        for full, short in names:
            r = b(full, "synth"); ax.scatter(r["n_meas"], r[key], s=46, color=BLUE if "gauss" in full or "g." in short else (ORANGE if "MSAPSO" in short else GREY), edgecolor=BG, linewidth=1.2, zorder=3)
            dx, dy, ha = (6, -0.35, "left")
            if short == "mejor de 7": dy = -0.5
            if short == "mejor de 20": dx, dy, ha = -6, 0.25, "right"
            if short == "mejor de 10 + 5 g.": dx, dy = 6, -0.55
            if short == "MSAPSO fiel": dx, ha = -6, "right"
            ax.annotate(short, (r["n_meas"], r[key]), textcoords="offset points", xytext=(dx, dy * 10), ha=ha, fontsize=7.5, color=SOFT)
        ax.set_xscale("log"); ax.set_xticks([7, 12, 20, 35, 175]); ax.set_xticklabels(["7", "12", "20", "35", "175"])
        ax.set_xlabel("Mediciones gastadas (escala log)"); ax.set_ylabel(ylab); ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    from matplotlib.lines import Line2D
    axes[1].legend(handles=[Line2D([], [], marker="o", ls="", color=BLUE, label="con muestreo gaussiano"), Line2D([], [], marker="o", ls="", color=GREY, label="sin muestreo"), Line2D([], [], marker="o", ls="", color=ORANGE, label="MSAPSO del paper")], frameon=False, fontsize=8, loc="upper right")
    axes[0].set_title("Exactitud vs. costo (100 sintéticos, sin ruido)", loc="left", fontsize=10); axes[1].set_title("Energía vs. costo", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_mediciones_V4.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_entrenamiento_largo():
    txt = open(f"{OUT}/entrenamiento_largo_V4.txt").read().strip().splitlines()[1:]
    rows = [[float(x) for x in re.findall(r"[\d.]+", l.split("|", 3)[3] if False else l)] for l in txt]
    # formato: upd | B | sigma | stoch | rfin rener | sfin sener | solo mu (sint) m
    data = []
    for l in txt:
        parts = [p.strip() for p in l.split("|")]
        upd, B = int(parts[0]), int(parts[1]); rf, re_ = map(float, parts[4].split()); sf, se = map(float, parts[5].split()); mu = float(parts[6].split()[-1])
        data.append((upd, B, rf, re_, sf, se, mu))
    labels = [f"{d[0]//1000} mil\n(lote {d[1]})" for d in data]; x = np.arange(len(data))
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    ax.plot(x, [d[4] for d in data], "-o", color=BLUE, label="Eficiencia final con K = 5 muestras", markersize=6, markeredgecolor=BG)
    ax.plot(x, [d[6] for d in data], "-o", color=ORANGE, label="Solo el punto μ (sin muestrear)", markersize=6, markeredgecolor=BG)
    ref = b("mejor-de-7 + 5 gauss. (s=0.05)", "synth")["eff_final"]
    ax.axhline(ref, color=GREY, linestyle="--", linewidth=1); ax.text(-0.35, ref + 0.12, f"Referencia sin aprendizaje {ref:.1f}", fontsize=8, color=SOFT, ha="left")
    ax.axhline(cota["synth"][0], color=GREY, linestyle=":", linewidth=1.2); ax.text(-0.35, cota["synth"][0] + 0.12, f"Cota supervisada {cota['synth'][0]:.1f}", fontsize=8, color=SOFT, ha="left")
    for xi, d in zip(x, data):
        ax.text(xi, d[4] - 0.42, f"{d[4]:.2f}", ha="center", fontsize=7.5); ax.text(xi, d[6] - 0.45, f"{d[6]:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8); ax.set_ylim(93, 99); ax.set_xlim(-0.5, 3.4); ax.set_xlabel("Actualizaciones de REINFORCE"); ax.set_ylabel("% del GMPP (100 sintéticos)")
    ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True); ax.legend(loc="center right", frameon=False, fontsize=8)
    ax.set_title("Más entrenamiento apenas mueve el resultado (media de 3 semillas)", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_entrenamiento_largo_V4.png", dpi=170, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    fig_comparacion(); fig_mediciones(); fig_entrenamiento_largo(); print("figuras listas")
