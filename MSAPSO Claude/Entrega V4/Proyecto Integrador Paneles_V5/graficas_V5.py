"""graficas_V5.py — Figuras del reporte V5 (lee resultados_V5/resumen_comparar_V5.txt, margen_NK_V5.txt y revision_reales_V5.txt).
Paleta de referencia validada (azul/naranja/aqua) sobre fondo claro; controles en gris; etiquetas directas y leyenda."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, AQUA, GREY, INK, SOFT, BG = "#2a78d6", "#eb6834", "#1baf7a", "#9a9a94", "#0b0b0b", "#52514e", "#fcfcfb"
OUT = "resultados_V5"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c9c8c2", "axes.facecolor": BG, "figure.facecolor": BG, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.labelcolor": SOFT, "xtick.color": SOFT, "ytick.color": SOFT, "text.color": INK})


def parse_resumen():
    sec, cur = {}, None
    for l in open(f"{OUT}/resumen_comparar_V5.txt"):
        m = re.match(r"=== ruido ([\d.]+) W \| N=(\d+), K=(\d+)", l)
        if m:
            cur = (float(m.group(1)), int(m.group(2)), int(m.group(3))); sec[cur] = {}; continue
        if cur and "|" in l and "solo mu" not in l:
            name = l.split("|")[0].strip(); nums = [float(x) for x in re.findall(r"(?<![\d.])\d+\.\d+(?=\s*/|\s*\(|\s*\[|\s*$)", l.split("|", 1)[1].replace("(+-", "(").replace("+-", ""))]
            allnums = [float(x) for x in re.findall(r"\d+\.\d+", l.split("|", 1)[1])]
            key = name.split()[0] if name.startswith(("reinforce", "ppo", "sac", "ddpg", "arbol")) else ("control simple" if "simple" in name else "control parabolico")
            if key.startswith("control"):
                sec[cur][key] = (allnums[0], allnums[1], allnums[2], allnums[3])
            else:
                sec[cur][key] = (allnums[0], allnums[1], allnums[4], allnums[5])    # sint fin, ener, real fin, ener (se salta el +-sd)
    return sec


S = parse_resumen()
NAMES = [("control simple", "Control\nsimple", GREY), ("control parabolico", "Control\nparabólico", "#c9c8c2"), ("reinforce", "REINFORCE", BLUE), ("ppo", "PPO", AQUA),
         ("sac", "SAC", "#eda100"), ("ddpg", "DDPG", ORANGE), ("arbol", "Árbol", "#6250d6")]


def fig_comparacion():
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), sharey=True)
    for ax, N in zip(axes, (5, 7)):
        d = S[(0.0, N, 5)]; x = np.arange(len(NAMES)); w = 0.38
        for j, (lab, col) in enumerate((("Eficiencia final", BLUE), ("Energía (ventana de 200 med.)", ORANGE))):
            v = [d[k][j] for k, _, _ in NAMES]
            bars = ax.bar(x + (j - 0.5) * (w + 0.03), v, w, color=col, edgecolor=BG, linewidth=1.5, label=lab if ax is axes[0] else None)
            for xi, vi in zip(x, v):
                ax.text(xi + (j - 0.5) * (w + 0.03), vi + 0.12, f"{vi:.1f}", ha="center", fontsize=7)
        ax.set_xticks(x); ax.set_xticklabels([n for _, n, _ in NAMES], fontsize=8); ax.set_ylim(90, 99.3)
        ax.set_title(f"N = {N}, K = 5  ({N+5} mediciones)", loc="left", fontsize=10); ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    axes[0].set_ylabel("% respecto al GMPP (100 sintéticos nuevos)")
    h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", ncol=2, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 1.03))
    fig.text(0.01, -0.02, "El MSAPSO del paper usa 175 mediciones: 99.98 % de exactitud final y 92.8 % de energía. Media de 3 semillas; sin ruido.", fontsize=7.5, color=SOFT)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_comparacion_V5.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_frontera():
    ctl = {}
    for l in open(f"{OUT}/margen_NK_V5.txt"):
        m = re.match(r"\s*(\d+)\s+(\d+)\s+(\d+)\s+\|\s+([\d.]+)\s+([\d.]+)", l)
        if m: ctl[(int(m.group(1)), int(m.group(2)))] = (int(m.group(3)), float(m.group(4)), float(m.group(5)))
    best = {}
    for (noise, N, K), d in S.items():
        if noise != 0.0: continue
        cand = {k: v for k, v in d.items() if not k.startswith("control")}
        k_best = max(cand, key=lambda k: cand[k][1]); best[(N, K)] = (N + K, cand[k_best][0], cand[k_best][1], k_best)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5))
    for ax, (idx, ylab) in zip(axes, ((1, "Eficiencia final (% del GMPP)"), (2, "Energía en ventana de 200 mediciones (%)"))):
        for (N, K), v in sorted(ctl.items()):
            ax.scatter(v[0], v[idx], s=40, color=GREY, edgecolor=BG, linewidth=1.2, zorder=3, label="Control simple (mejor de N + K gauss.)" if (N, K) == (3, 3) else None)
            ax.annotate(f"({N},{K})", (v[0], v[idx]), textcoords="offset points", xytext=(-4, -12), ha="right", fontsize=7, color=SOFT)
        for (N, K), v in sorted(best.items()):
            ax.scatter(v[0], v[idx], s=52, color=BLUE, edgecolor=BG, linewidth=1.2, zorder=4, label="Mejor algoritmo aprendido" if (N, K) == (3, 3) else None)
            ax.annotate(f"{v[3]} ({N},{K})", (v[0], v[idx]), textcoords="offset points", xytext=(6, -12) if (N, K) == (7, 3) else (6, 4), fontsize=7, color=INK)
        ax.set_xlabel("Mediciones gastadas (N + K); etiquetas = (N, K)"); ax.set_ylabel(ylab); ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    axes[0].set_ylim(78, 100); axes[1].set_ylim(78, 98.5)
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    axes[0].set_title("Con las mismas mediciones, el RL llega más alto", loc="left", fontsize=10); axes[1].set_title("Energía vs. costo", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_frontera_V5.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_reales():
    rows = {}
    N = None
    for l in open(f"{OUT}/revision_reales_V5.txt"):
        m = re.match(r"N=(\d+): corrientes", l)
        if m: N = int(m.group(1))
        m = re.match(r"\s+(control simple|arbol \(banco original\)|arbol \(con atenuacion global\))\s+\|\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", l)
        if m and N: rows[(N, m.group(1))] = [float(m.group(i)) for i in (2, 3, 4, 5)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.0), sharey=True)
    series = (("control simple", "Control simple", GREY), ("arbol (banco original)", "Árbol (banco original)", BLUE), ("arbol (con atenuacion global)", "Árbol (con atenuación global)", ORANGE))
    for ax, N in zip(axes, (5, 7)):
        x = np.arange(4); w = 0.26
        for j, (k, lab, col) in enumerate(series):
            v = rows[(N, k)]; ax.bar(x + (j - 1) * w, v, w, color=col, edgecolor=BG, linewidth=1.2, label=lab if ax is axes[0] else None)
            for xi, vi in zip(x, v): ax.text(xi + (j - 1) * w, vi + 0.3, f"{vi:.0f}", ha="center", fontsize=7)
        ax.set_xticks(x); ax.set_xticklabels(["Caso 1\n(Isc 7.1 A)", "Caso 2\n(Isc 8.9 A)", "Caso 3\n(Isc 3.25 A)", "Caso 4\n(Isc 8.9 A)"], fontsize=8)
        ax.set_ylim(80, 102); ax.set_title(f"N = {N}, K = 5", loc="left", fontsize=10); ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    axes[0].set_ylabel("Eficiencia final (% del GMPP)")
    h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", ncol=3, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_reales_V5.png", dpi=170, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    fig_comparacion(); fig_frontera(); fig_reales(); print("figuras listas")
