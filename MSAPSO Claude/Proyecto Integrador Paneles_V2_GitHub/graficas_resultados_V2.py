"""graficas_resultados_V2.py — Figuras de resultados consolidados (lee resultados_V2/*.json)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from graficas_V2 import AMBER, TEAL, GREEN, INK, GREY, RED
OUT = "resultados_V2"
GROUPS = ("static", "pairs", "synth")
GLAB = {"static": "4 casos estáticos", "pairs": "12 transiciones reales (holdout)", "synth": "100 transiciones sintéticas nuevas"}
raw = json.load(open(f"{OUT}/final_raw_V2.json"))
ext = json.load(open(f"{OUT}/reinforce_grid_ext_V2.json")) if os.path.exists(f"{OUT}/reinforce_grid_ext_V2.json") else None


def mean_g(r, g): return float(np.mean(r["energy"][g]))


def fig_comparacion(regime, fname):
    D = raw[regime]
    items = [("MSAPSO fiel\n(paper)", D["controls"]["MSAPSO fiel (paper)"], GREY, None)]
    if "MSAPSO optimizado (formal)" in D["controls"]:
        items.append(("MSAPSO\noptimizado\n(formal)", D["controls"]["MSAPSO optimizado (formal)"], TEAL, None))
    items.append(("regla simple\nβ=.95, t=5\n(post-hoc)", D["controls"]["regla simple β=0.95, t_max=5 (post-hoc)"], "#d9b27c", "//"))
    items.append(("regla simple\nβ .5→.95\nt=8 (post-hoc)", D["controls"]["regla simple β 0.5→0.95, t_max=8 (post-hoc)"], "#d9b27c", "\\\\"))
    seeds = list(D["ppo_seeds"].values())
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), sharey=True)
    for ax, g in zip(axes, GROUPS):
        xs, labels = [], []
        for i, (lab, r, col, hatch) in enumerate(items):
            ax.bar(i, mean_g(r, g), color=col, hatch=hatch, edgecolor="white", width=0.7); labels.append(lab); xs.append(i)
            ax.text(i, mean_g(r, g) + 0.15, f"{mean_g(r, g):.1f}", ha="center", fontsize=7.5)
        i = len(items)
        vals = [mean_g(r, g) for r in seeds]
        ax.bar(i, np.mean(vals), color=AMBER, width=0.7, yerr=np.std(vals), capsize=3, edgecolor="white")
        ax.scatter(np.full(len(vals), i), vals, color=INK, s=12, zorder=5)
        ax.text(i, max(vals) + 0.3, f"{np.mean(vals):.1f}", ha="center", fontsize=7.5)
        labels.append(f"PPO\n({len(vals)} semillas)"); xs.append(i)
        if regime == "5ms" and ext is not None:
            c = ext["test"]["B-none | lr=fixed0.001"][g]["energy"]
            j = len(items) + 1
            ax.bar(j, c, color=GREEN, width=0.7, edgecolor="white"); ax.text(j, c + 0.15, f"{c:.1f}", ha="center", fontsize=7.5)
            labels.append("REINFORCE\n(forma B,\nσ=0.05)"); xs.append(j)
        ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=6.5); ax.set_title(GLAB[g]); ax.set_ylim(84 if regime == "5ms" else 60, 101.5)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("energía entregada / energía ideal (%)")
    ttl = "t_wait = 5 ms (régimen principal)" if regime == "5ms" else "t_wait = 0.5 ms (valor literal del paper; el convertidor no alcanza a seguir la referencia)"
    fig.suptitle(f"Comparación justa de métodos — {ttl}", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.94]); fig.savefig(fname, bbox_inches="tight"); plt.close(fig)


def fig_curva_aprendizaje(fname):
    p = f"{OUT}/curva_aprendizaje_V2.json"
    if not os.path.exists(p): return
    d = json.load(open(p)); paper = raw["5ms"]["controls"]["MSAPSO fiel (paper)"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    for ax, g in zip(axes, GROUPS):
        for s, col in zip(range(3), (AMBER, TEAL, GREEN)):
            pts = [(int(k.split("_")[1]), v[g]) for k, v in d.items() if k.startswith(f"s{s}_")]
            pts.sort(); ax.plot([x / 1e3 for x, _ in pts], [y for _, y in pts], marker="o", color=col, label=f"semilla {s}")
        ax.axhline(mean_g(paper, g), color=GREY, ls="--", lw=1, label="MSAPSO fiel")
        ax.set_title(GLAB[g], fontsize=9); ax.set_xlabel("pasos de entrenamiento (miles)"); ax.grid(alpha=0.25)
    axes[0].set_ylabel("energía %"); axes[0].legend(fontsize=7)
    fig.suptitle("Curva de aprendizaje de PPO (puntos de control al 25, 50, 75 y 100 % del entrenamiento)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(fname, bbox_inches="tight"); plt.close(fig)


def fig_reinforce(fname):
    if ext is None: return
    base = json.load(open(f"{OUT}/reinforce_grid_V2.json"))
    rows = base["stage1"] + ext["stage1"]
    lrs = [("fixed", 0.1), ("fixed", 0.01), ("fixed", 0.001), ("accel", None), ("inv_t", None)]
    lab = ["0.1", "0.01", "0.001", "acelerada", "1/t"]
    sigs = [0.05, 0.1, 0.2, 0.3, 0.5, 0.8]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6))
    for ax, (form, bl, title) in zip(axes, (("B", "none", "Forma B (profesor), sin baseline"), ("A", "V", "Forma A (libro), baseline R−V"), ("A", "QV", "Forma A, baseline Q̂−V"))):
        M = np.full((len(lrs), len(sigs)), np.nan)
        for i, (lr, lv) in enumerate(lrs):
            for j, s in enumerate(sigs):
                vals = [r["train_energy"] for r in rows if r["form"] == form and r["baseline"] == bl and r["lr"] == lr and
                        (lv is None or r["lr_value"] == lv) and abs(r["sigma"] - s) < 1e-9]
                if vals: M[i, j] = max(vals)
        im = ax.imshow(M, vmin=78, vmax=96, cmap="YlGnBu", aspect="auto")
        ax.set_xticks(range(len(sigs))); ax.set_xticklabels(sigs); ax.set_yticks(range(len(lrs))); ax.set_yticklabels(lab)
        for i in range(len(lrs)):
            for j in range(len(sigs)):
                if not np.isnan(M[i, j]): ax.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=7, color="white" if M[i, j] > 90 else INK)
        ax.set_title(title, fontsize=9); ax.set_xlabel("σ (fracción de Isc)"); ax.grid(False)
    axes[0].set_ylabel("tasa de aprendizaje")
    fig.suptitle("REINFORCE gaussiano — energía % en sombras de entrenamiento (mejor normalización de recompensa por celda; MSAPSO fiel ≈ 95–96 %)", fontsize=9.5)
    fig.tight_layout(rect=[0, 0, 1, 0.92]); fig.savefig(fname, bbox_inches="tight"); plt.close(fig)


def fig_slew(fname):
    k = ["1× (paper)", "10×", "100×", "1000×"]
    down = [0.59, 1.00, 1.00, 1.00]; up = [0.33, 1.75, 1.75, 1.75]
    fig, ax = plt.subplots(figsize=(6.5, 3.4)); x = np.arange(4)
    ax.bar(x - 0.18, down, 0.36, color=TEAL, label="bajada 6.7→0.7 A"); ax.bar(x + 0.18, up, 0.36, color=AMBER, label="subida 0.7→6.7 A")
    ax.axhline(0.95, color=TEAL, ls=":", lw=1); ax.axhline(1.5, color=AMBER, ls=":", lw=1)
    ax.text(3.45, 0.97, "límite físico ↓ 0.95", fontsize=7, ha="right", color=TEAL); ax.text(3.45, 1.52, "límite físico ↑ 1.50", fontsize=7, ha="right", color=AMBER)
    ax.set_xticks(x); ax.set_xticklabels(k); ax.set_xlabel("ganancias del Super-Twisting (λ, Υ) × las del paper"); ax.set_ylabel("|ΔI inductor| en 0.5 ms (A)"); ax.legend(fontsize=7.5, loc="upper left")
    ax.set_title("Re-sintonizar no ayuda: la respuesta satura en el límite de L = 10 mH", fontsize=9); ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(fname, bbox_inches="tight"); plt.close(fig)


def fig_ablacion(fname):
    a = raw.get("ablation", {})
    if len(a) < 2: return
    names = {"full": "completa (8)", "no_disp": "sin\ndispersión (7)", "no_time": "sin t. desde\nreinicio (7)", "no_drop": "sin caída_rel\nni dPbest (6)", "minimal": "mínima:\nP_max, Pbest,\ncaída_rel (3)"}
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.2), sharey=False)
    paper = raw["5ms"]["controls"]["MSAPSO fiel (paper)"]
    for ax, g in zip(axes, GROUPS):
        for i, v in enumerate([k for k in names if k in a]):
            vals = [mean_g(r, g) for r in a[v].values()]
            ax.bar(i, np.mean(vals), color=AMBER if v == "full" else "#d9b27c", width=0.65, edgecolor="white")
            ax.scatter(np.full(len(vals), i), vals, color=INK, s=12, zorder=5)
            ax.text(i, max(vals) + 0.15, f"{np.mean(vals):.1f}", ha="center", fontsize=7.5)
        ax.axhline(mean_g(paper, g), color=GREY, ls="--", lw=1, label="MSAPSO fiel")
        ax.set_xticks(range(len([k for k in names if k in a]))); ax.set_xticklabels([names[k] for k in names if k in a], fontsize=6.5)
        ax.set_title(GLAB[g], fontsize=9); ax.set_ylim(90 if g != "synth" else 88, 100.2); ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("energía % (media de 2 semillas)"); axes[0].legend(fontsize=7)
    fig.suptitle("Ablación de señales de observación (PPO, 5 ms)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(fname, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    fig_comparacion("5ms", f"{OUT}/fig_comparacion_5ms.png")
    fig_comparacion("0.5ms", f"{OUT}/fig_comparacion_05ms.png")
    fig_curva_aprendizaje(f"{OUT}/fig_curva_aprendizaje.png")
    fig_reinforce(f"{OUT}/fig_reinforce_malla.png")
    fig_slew(f"{OUT}/fig_slew_controlador.png")
    fig_ablacion(f"{OUT}/fig_ablacion_senales.png")
    print("figuras de resultados listas")
