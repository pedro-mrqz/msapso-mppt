"""graficas_V7.py — Figuras del reporte V7 (lee resultados_V7/*). Paleta de referencia validada (azul/naranja/aqua), referencias en gris."""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, AQUA, GREY, INK, SOFT, BG = "#2a78d6", "#eb6834", "#1baf7a", "#9a9a94", "#0b0b0b", "#52514e", "#fcfcfb"
OUT = "resultados_V7"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c9c8c2", "axes.facecolor": BG, "figure.facecolor": BG, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.labelcolor": SOFT, "xtick.color": SOFT, "ytick.color": SOFT, "text.color": INK})


def fig_convergencia():
    d = json.load(open(f"{OUT}/convergencia_V7.json")); acc = np.array(d["acc"]); disp = np.array(d["disp"]); t = np.arange(1, 26)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    ax.plot(t, acc.mean(0), "-o", color=BLUE, markersize=4, label="Exactitud media"); ax.plot(t, np.percentile(acc, 5, axis=0), "--", color=ORANGE, label="Percentil 5 (peores curvas)")
    ax.axhline(acc[:, -1].mean(), color=GREY, linestyle=":", linewidth=1); ax.text(25, acc[:, -1].mean() - 1.2, "exactitud con 25 pasadas", ha="right", fontsize=7.5, color=SOFT)
    ax.set_ylim(75, 101); ax.set_xlabel("Pasada del MSAPSO (7 mediciones por pasada)"); ax.set_ylabel("% del GMPP si se detuviera ahí"); ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("El MSAPSO ya alcanzó su exactitud final hacia la pasada 9–13", loc="left", fontsize=9.5); ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    ax = axes[1]
    ax.plot(t, disp.mean(0), "-o", color=AQUA, markersize=4); ax.axhline(0.02, color=ORANGE, linestyle="--", linewidth=1.2); ax.text(25, 0.026, "umbral δ = 0.02 (regla elegida)", ha="right", fontsize=8, color=ORANGE)
    ax.set_xlabel("Pasada del MSAPSO"); ax.set_ylabel("Dispersión del enjambre (std de posiciones / Isc)"); ax.set_title("La dispersión del enjambre colapsa y avisa la convergencia", loc="left", fontsize=9.5)
    ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_convergencia_V7.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_reglas():
    rows = []
    for l in open(f"{OUT}/seleccion_regla_V7.txt"):
        m = re.match(r"^(disp|noimp|OR |AND)(.*?)\s+\|\s+(\d+)\s+\|\s+([\d.]+)\s+\|\s+([+-][\d.]+)\s+\|", l)
        if m: rows.append((m.group(1).strip(), int(m.group(3)), float(m.group(5))))
        m = re.match(r"^(truncado|comprimido) T=(\d+).*?\|\s+(\d+)\s+\|\s+([\d.]+)\s+\|\s+([+-][\d.]+)\s+\|", l)
        if m: rows.append((m.group(1), int(m.group(3)), float(m.group(5))))
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    style = {"disp": ("Parada por dispersión", BLUE, "o"), "noimp": ("Parada «sin mejora en k pasadas»", ORANGE, "s"), "OR": ("O (dispersión o sin mejora)", "#c9c8c2", "^"), "AND": ("Y (dispersión y sin mejora)", AQUA, "D"),
             "truncado": ("Truncado fijo (beta del paper)", GREY, "x"), "comprimido": ("Beta comprimida a T pasadas", "#6250d6", "P")}
    for k, (lab, col, mk) in style.items():
        pts = [(n, d) for kk, n, d in rows if kk == k]
        if pts: ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=42, color=col, marker=mk, edgecolor=BG, linewidth=0.8, label=lab, zorder=3)
    ax.axhline(0.10, color=GREY, linestyle=":", linewidth=1); ax.text(176, 0.12, "tolerancia 0.10 pp", ha="right", fontsize=7.5, color=SOFT)
    ax.set_yscale("symlog", linthresh=0.05); ax.set_ylim(-0.1, 4); ax.set_xlim(20, 180); ax.set_xlabel("Mediciones gastadas (el MSAPSO completo usa 175)"); ax.set_ylabel("Pérdida de exactitud final frente al MSAPSO completo (pp)")
    ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    ax.set_title("Validación: solo algunas reglas paran pronto sin perder exactitud", loc="left", fontsize=9.5)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_reglas_V7.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_operacion():
    J = {}
    for part in "ABL":
        f = f"{OUT}/operacion_{part}_V7.json"
        if os.path.exists(f): J.update(json.load(open(f)))
    def get(title_start, wait, name):
        for k, v in J.items():
            t, w, n = k.split("|")
            if t.startswith(title_start) and abs(float(w) - wait) < 1e-9 and n == name: return v
    scen = [("A) cambio unico: 12 pares", 5e-3, "Cambio único,\n12 pares reales"), ("A) cambio unico: 60 pares", 5e-3, "Cambio único,\n60 sintéticos"), ("B) sombra frecuente (moderado)", 5e-3, "Frecuente:\nmoderado"),
            ("B) sombra frecuente (alto), sinteticos", 5e-3, "Frecuente:\nalto"), ("B) sombra frecuente (muy alto)", 5e-3, "Frecuente:\nmuy alto"), ("B) sombra frecuente (alto), 4", 5e-3, "Frecuente alto,\n4 reales"), ("L)", 5e-3, "Estable largo\n(100 s)")]
    series = [("parada principal", "Parada anticipada (dispersión < 0.02)", BLUE), ("comprimido T=12", "Beta comprimida a T = 12", AQUA), ("comprimido T=10", "Beta comprimida a T = 10", ORANGE)]
    fig, ax = plt.subplots(figsize=(11.5, 4.5)); x = np.arange(len(scen)); w = 0.26
    for j, (name, lab, col) in enumerate(series):
        m, lo, hi = [], [], []
        for t, wt, _ in scen:
            v = get(t, wt, name); m.append(v[0]); lo.append(v[0] - v[1]); hi.append(v[2] - v[0])
        ax.bar(x + (j - 1) * (w + 0.02), m, w, color=col, edgecolor=BG, linewidth=1.2, label=lab, yerr=[lo, hi], capsize=2, error_kw=dict(ecolor=SOFT, lw=0.8))
    ax.axhline(0, color=INK, linewidth=0.8); ax.set_xticks(x); ax.set_xticklabels([n for _, _, n in scen], fontsize=8); ax.set_ylabel("Energía real: método − MSAPSO completo (pp)")
    ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=8, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.06))
    ax.set_title("Simulador dinámico, t_wait = 5 ms (barras de error: IC95 % bootstrap)", loc="left", fontsize=9.5, pad=34)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_operacion_V7.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_refuerzo():
    rows = []   # (grupo, etiqueta, media, lo, hi)
    for mode in "FNPT":
        f = f"{OUT}/refuerzo_{mode}_V7.json"
        if not os.path.exists(f): continue
        for k, v in json.load(open(f)).items():
            p = k.split("|")
            if len(p) != 4 or p[3] != "parada principal (disp<0.02)": continue
            title, wait, noise = p[0], float(p[1]), float(p[2])
            if mode == "F":
                m = re.search(r"amplitud ([\d.]+), cambio cada ~(\d+)", title); rows.append((f"Flicker parcial, {wait*1e3:g} ms", f"amplitud {m.group(1)}, cada ~{m.group(2)} vent.", *v))
            elif mode == "N":
                m = re.search(r"ruido (\d+) W: (.*?)(,|$)", title); what = title.split(": ")[1].replace("cambio unico, ", "cambio único, ").replace("sombra frecuente (alto), sinteticos", "sombra frecuente (alto)")
                rows.append((f"Ruido de medición, 5 ms", f"{m.group(1)} W · {what}", *v))
            elif mode == "P":
                rows.append(("Otros paneles, 5 ms (cambio único)", title.replace("P) operacion, cambio unico, ", ""), *v))
            elif mode == "T":
                rows.append((f"Otros t_wait (cambio único)", f"{wait*1e3:g} ms · " + ("12 pares reales" if "reales" in title else "60 sintéticos"), *v))
    groups = []
    for r in rows:
        if r[0] not in groups: groups.append(r[0])
    fig, ax = plt.subplots(figsize=(9.5, 0.27 * len(rows) + 1.6)); y = 0; yt, yl = [], []
    for g in groups:
        for r in [r for r in rows if r[0] == g]:
            col = BLUE if r[3] > 0 else (ORANGE if r[4] < 0 else GREY)
            ax.plot([r[3], r[4]], [y, y], color=col, linewidth=1.4); ax.plot(r[2], y, "o", color=col, markersize=5, markeredgecolor=BG)
            yt.append(y); yl.append(r[1]); y += 1
        y += 0.6
    ax.axvline(0, color=INK, linewidth=0.8); ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=7); ax.invert_yaxis(); ax.set_xlabel("Energía real: parada principal − MSAPSO completo (pp), IC95 % bootstrap")
    ax.xaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    yy = 0
    for g in groups:
        n = len([r for r in rows if r[0] == g]); ax.text(ax.get_xlim()[1], yy - 0.7 if yy else -0.9, g, ha="right", fontsize=8, color=SOFT, fontweight="bold"); yy += n + 0.6
    ax.set_title("Pruebas de estrés: azul = ventaja demostrable, gris = intervalo que incluye cero, naranja = pérdida demostrable", loc="left", fontsize=9)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_refuerzo_V7.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_sensibilidad():
    J = json.load(open(f"{OUT}/sensibilidad_S_V7.json")); groups = [("delta", "δ (umbral de dispersión)", BLUE, "o"), ("particulas", "Número de partículas", ORANGE, "s"), ("t_max", "t_max (rapidez de contracción de β)", AQUA, "D"), ("malla", "Malla δ × partículas (5 y 9)", GREY, "^")]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5))
    for ax, (idx, ylab) in zip(axes, ((1, "Pérdida media de exactitud (pp)"), (3, "Pérdida en el peor caso (pp, máximo en 200 curvas)"))):
        for g, lab, col, mk in groups:
            pts = [(v[0][0], v[0][idx], k.split("|")[1]) for k, v in J.items() if k.startswith(g + "|")]
            ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=40, color=col, marker=mk, edgecolor=BG, linewidth=0.8, label=lab, zorder=3)
            for n, y, name in pts:
                if g in ("delta", "t_max") or name.startswith("5 part., delta = 0.02") or name.startswith("9 part., delta = 0.02"): ax.annotate(name.replace("delta = ", "δ=").replace(" particulas", " part.").replace("t_max = ", "t_max="), (n, y), textcoords="offset points", xytext=(4, 4), fontsize=6.5, color=SOFT)
        ax.axvline(70, color=GREY, linestyle=":", linewidth=1); ax.set_yscale("symlog", linthresh=0.05); ax.set_ylim(bottom=0); ax.set_xlabel("Mediciones gastadas (el MSAPSO completo usa 175)"); ax.set_ylabel(ylab)
        ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper right"); axes[0].set_title("Sensibilidad (sin ruido): la V7 (δ = 0.02, 7 partículas, t_max = 25) está en la rodilla", loc="left", fontsize=9)
    axes[1].set_title("La cola de pérdidas explota con t_max ≤ 15, δ ≥ 0.03 o 5 partículas", loc="left", fontsize=9)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_sensibilidad_V7.png", dpi=170, bbox_inches="tight"); plt.close(fig)


def fig_campana():
    R = [json.loads(l) for l in open(f"{OUT}/campana_V7.jsonl")]
    d = lambda r: r["principal"]["e"] - r["full"]["e"]
    iso = np.array([d(r) for r in R if r["regimen"] in ("unico", "estable")]); fre = np.array([d(r) for r in R if r["regimen"] in ("moderado", "alto", "muy alto")]); fli = np.array([d(r) for r in R if r["regimen"] == "flicker"])
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4)); ax = axes[0]; bins = np.linspace(-30, 40, 71)
    for arr, lab, col in ((iso, f"Cambio aislado o estable (n={len(iso)})", GREY), (fre, f"Sombra frecuente (n={len(fre)})", BLUE), (fli, f"Flicker parcial (n={len(fli)})", ORANGE)):
        ax.hist(np.clip(arr, -30, 40), bins=bins, alpha=0.6, color=col, label=lab, edgecolor=BG, linewidth=0.3, density=True)
    ax.axvline(0, color=INK, linewidth=0.8); ax.set_xlabel("Energía real: V7 − MSAPSO completo (pp; recortado a −30…+40)"); ax.set_ylabel("Densidad de escenarios"); ax.legend(frameon=False, fontsize=8)
    ax.set_title("Distribución de la diferencia por escenario (2400 escenarios)", loc="left", fontsize=9.5); ax.yaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    ax = axes[1]; rows = []; rb = np.random.default_rng(0)
    def ci(x):
        i = rb.integers(0, len(x), (3000, len(x))); m = x[i].mean(1); return float(x.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
    for key, vals, fmt in (("regimen", ("unico", "estable", "moderado", "alto", "muy alto", "flicker"), "{}"), ("ruido", (0.0, 1.0, 2.0), "ruido {:g} W"), ("wait", (5e-3, 2e-3, 1e-3, 5e-4), "t_wait {:g} ms")):
        for v in vals:
            x = np.array([d(r) for r in R if r[key] == v]); rows.append((fmt.format(v * 1e3 if key == "wait" else v), *ci(x), len(x)))
        rows.append(None)
    y = 0
    for r in rows:
        if r is None: y += 0.6; continue
        col = BLUE if r[2] > 0 else (ORANGE if r[3] < 0 else GREY); ax.plot([r[2], r[3]], [y, y], color=col, linewidth=1.5); ax.plot(r[1], y, "o", color=col, markersize=5, markeredgecolor=BG); ax.text(max(r[3], 0) + 0.2, y, f"n={r[4]}", va="center", fontsize=6.5, color=SOFT); y += 1
    ax.set_yticks([i for i in range(0, 1)]); labs = [r[0] for r in rows if r is not None]; pos = []; y = 0
    for r in rows:
        if r is None: y += 0.6; continue
        pos.append(y); y += 1
    ax.set_yticks(pos); ax.set_yticklabels(labs, fontsize=7); ax.invert_yaxis(); ax.axvline(0, color=INK, linewidth=0.8); ax.set_xlabel("Diferencia media de energía (pp), IC95 % bootstrap")
    ax.set_title("Por estrato: ventaja con sombra frecuente; empate con cambio aislado", loc="left", fontsize=9.5); ax.xaxis.grid(True, color="#e4e3dd", linewidth=0.8); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig_campana_V7.png", dpi=170, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    fig_convergencia(); fig_reglas(); fig_operacion(); fig_refuerzo(); fig_sensibilidad(); fig_campana(); print("figuras listas")
