"""graficas_V2.py — Figuras de la corrida V2 (se llama por funcion desde otros scripts o por CLI)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pvsim_V2.pvcurve_V2 import load_case
from pvsim_V2.converter_V2 import Plant
from pvsim_V2.msapso_V2 import MSAPSOController, Swarm, run_scenario

AMBER, TEAL, GREEN, INK, GREY, RED = "#b3661a", "#2b5f63", "#3f7a4a", "#262320", "#8a8377", "#a8482f"
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": GREY,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "axes.titlesize": 9.5,
                     "figure.dpi": 140, "axes.grid": True, "grid.alpha": 0.25})
OUT = "resultados_V2"


def fig_beta_convergencia(wait=5e-3, fname=None):
    """Para los 4 casos reales (MSAPSO fiel): beta_t (Eq.14), dispersion de las particulas y Gbest/Pbest vs numero de pasada."""
    fig, axes = plt.subplots(3, 4, figsize=(13, 7.2), sharex=True)
    for idx in range(4):
        c = load_case(idx)
        log = run_scenario(lambda: MSAPSOController(wait), [(c, 40 * 7 * wait)], wait)
        n = 28
        k = np.arange(1, n + 1)
        ax = axes[0, idx]; ax.plot(k, log["beta"][:n], color=AMBER, lw=1.8, marker="o", ms=2.5)
        ax.set_title(f"Caso {idx+1}"); ax.set_ylim(0, 1.0)
        if idx == 0: ax.set_ylabel("β de la pasada (Eq. 14)")
        ax = axes[1, idx]; ax.plot(k, log["disp"][:n], color=TEAL, lw=1.8, marker="o", ms=2.5)
        ax2 = ax.twinx(); ax2.grid(False); ax2.spines["right"].set_visible(True)
        ax2.plot(k, log["Gbest"][:n] / c.Isc, color=GREEN, lw=1.4, ls="--"); ax2.axhline(c.I_ceiling / c.Isc, color=GREEN, lw=0.8, ls=":")
        ax2.set_ylim(0, 1.05)
        if idx == 0: ax.set_ylabel("dispersión de partículas (azul)")
        if idx == 3: ax2.set_ylabel("Gbest / Isc (verde); línea = óptimo", color=GREEN)
        ax = axes[2, idx]; ax.plot(k, 100 * log["Pbest"][:n] / c.P_ceiling, color=INK, lw=1.6, label="Pbest")
        ax.plot(k, 100 * log["P_end"][:n] / c.P_ceiling, color=RED, lw=1.0, alpha=0.8, label="P de la última partícula")
        ax.axvline(25.5, color=GREY, lw=0.8, ls="--"); ax.set_ylim(40, 105); ax.set_xlabel("pasada")
        if idx == 0: ax.set_ylabel("% del techo alcanzable"); ax.legend(fontsize=7, loc="lower right")
    fig.suptitle(f"MSAPSO fiel (Fig. 6) — cómo cambian β, la dispersión y Gbest conforme las partículas se acercan al MPP (t_wait = {wait*1e3:g} ms; línea punteada vertical = fin de la búsqueda, t_max = 25)", fontsize=9.5)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(fname or f"{OUT}/fig_beta_convergencia_msapso_{wait*1e3:g}ms.png", bbox_inches="tight"); plt.close(fig)


def fig_escalera(wait, idx=1, fname=None, n_pass=4):
    """Escalera del barrido: referencia I_ref (en pasos), corriente real del inductor y potencia del panel, alternando ascendente/descendente."""
    c = load_case(idx); pl = Plant(c); sw = Swarm(); sw.restart(c.Isc, first=True)
    T, IREF, IL, P, marks = [], [], [], [], []
    t0 = 0.0
    for p in range(n_pass):
        order = np.argsort(sw.x); order = order[::-1] if sw.direction == "descending" else order
        marks.append((t0, sw.direction))
        for i in order:
            t, Pw, V, I = pl.run_trace(wait, sw.x[i])
            T.append(t); P.append(Pw); IL.append(I); IREF.append(np.full_like(t, sw.x[i]))
            if Pw[-1] >= sw.Pbest: sw.Pbest = Pw[-1]; sw.Gbest = pl.Ipv
        sw.update(0.1 + (sw.t / 25) * 0.85)
        t0 = pl.t
    T, IREF, IL, P = map(np.concatenate, (T, IREF, IL, P))
    fig, ax = plt.subplots(2, 1, figsize=(9.5, 5.2), sharex=True)
    ax[0].step(T * 1e3, IREF, where="post", color=AMBER, lw=1.6, label="referencia I_ref (escalera)")
    ax[0].plot(T * 1e3, IL, color=TEAL, lw=1.1, label="corriente real del inductor")
    ax[0].set_ylabel("corriente (A)"); ax[0].legend(fontsize=7.5, loc="upper right")
    ax[1].plot(T * 1e3, P, color=INK, lw=1.0); ax[1].axhline(c.P_ceiling, color=GREEN, ls=":", lw=1); ax[1].set_ylabel("potencia del panel (W)"); ax[1].set_xlabel("tiempo (ms)")
    for t_s, d in marks:
        for a in ax: a.axvline(t_s * 1e3, color=GREY, lw=0.7, ls="--")
        ax[0].text(t_s * 1e3 + 0.5 * wait * 1e3, ax[0].get_ylim()[1] * 0.97, "↑ menor→mayor" if d == "ascending" else "↓ mayor→menor", fontsize=7.5, va="top", color=GREY)
    fig.suptitle(f"Barrido escalonado alternante del MSAPSO (Caso {idx+1}, t_wait = {wait*1e3:g} ms): cada conjunto se prueba en sentido contrario al anterior", fontsize=9.5)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(fname or f"{OUT}/fig_escalera_{wait*1e3:g}ms.png", bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    for w in (5e-3, 0.5e-3):
        fig_beta_convergencia(w); fig_escalera(w, idx=1, n_pass=4)
    print("figuras base listas")


def fig_agente(model_path, features, wait, scenarios, titles, fname, passes=62):
    """Compara, escenario por escenario, lo que HACE el agente PPO (beta elegido, dispersion, reinicios, potencia) con el MSAPSO fiel."""
    from evaluar_rl_V2 import policy_factory
    n = len(scenarios)
    fig, axes = plt.subplots(3, n, figsize=(3.3 * n, 7.4), sharex="col")
    axes = np.atleast_2d(axes).reshape(3, n)
    for j, (curves, title) in enumerate(zip(scenarios, titles)):
        segs = [(c, passes * 7 * wait) for c in curves]
        rl = run_scenario(policy_factory(model_path, wait, features), segs, wait)
        ms = run_scenario(lambda: MSAPSOController(wait), segs, wait)
        k = np.arange(1, len(rl["E"]) + 1)
        Pref = np.concatenate([np.full(passes, c.P_ceiling) for c in curves])
        ax = axes[0, j]
        ax.plot(k, ms["beta"], color=GREY, lw=1.3, ls="--", label="MSAPSO (Eq. 14; 0 = mantenimiento)")
        ax.plot(k, rl["beta"], color=AMBER, lw=1.6, label="PPO")
        ax.set_ylim(-0.02, 1.0); ax.set_title(title)
        ax = axes[1, j]
        ax.plot(k, ms["disp"], color=GREY, lw=1.3, ls="--"); ax.plot(k, rl["disp"], color=TEAL, lw=1.6)
        ax = axes[2, j]
        ax.plot(k, 100 * ms["P_end"] / Pref, color=GREY, lw=1.0, ls="--"); ax.plot(k, 100 * rl["P_end"] / Pref, color=GREEN, lw=1.4)
        rs = np.where(rl["restart"])[0]
        ax.scatter(rs + 1, np.full(len(rs), 45), marker="^", color=RED, s=22, zorder=5, label="reinicio (PPO)")
        ax.set_ylim(40, 105); ax.set_xlabel("pasada")
        for a in axes[:, j]:
            if len(curves) > 1: a.axvline(passes + 0.5, color=RED, lw=0.9, ls=":")
        if j == 0:
            axes[0, j].set_ylabel("β elegido en la pasada"); axes[1, j].set_ylabel("dispersión de partículas"); axes[2, j].set_ylabel("% del techo (última partícula)")
            axes[0, j].legend(fontsize=6.5, loc="lower right"); axes[2, j].legend(fontsize=6.5, loc="lower right")
    fig.suptitle("Qué hace el agente PPO frente al MSAPSO del paper (línea punteada roja vertical = cambio de sombra)", fontsize=9.5)
    fig.tight_layout(rect=[0, 0, 1, 0.96]); fig.savefig(fname, bbox_inches="tight"); plt.close(fig)
