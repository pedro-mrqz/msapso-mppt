"""
analisis_final_V2.py — Agrega TODOS los resultados de la corrida V2 con el arnes comun y produce tablas (JSON) y figuras.
 * PPO (3 semillas) por regimen de tiempo; ablacion de senales (2 semillas por variante); controles sin RL (paper, optimizado formal,
   reglas simples post-hoc); REINFORCE (de reinforce_grid*.json).
 * Estadisticos: media ± desv. tipica entre semillas; diferencia pareada vs MSAPSO del paper por escenario con IC95% bootstrap.
Cache por modelo en resultados_V2/raw/*.json.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from pvsim_V2.msapso_V2 import MSAPSOController
from pvsim_V2.harness_V2 import build_scenarios, evaluate
from evaluar_rl_V2 import policy_factory
from train_V2 import OBS_VARIANTS

RAW = "resultados_V2/raw"
GROUPS = ("static", "pairs", "synth")
SCEN = None


def energies(res):
    return {g: [m["eff_energy"] for m in res[g]] for g in GROUPS}, {g: [m["eff_final"] for m in res[g]] for g in GROUPS}, \
           {g: [m["n_restarts"] for m in res[g]] for g in GROUPS}


def cached(tag, make):
    path = f"{RAW}/{tag}.json"
    if os.path.exists(path):
        return json.load(open(path))
    global SCEN
    SCEN = SCEN or build_scenarios()
    e, f, r = energies(make(SCEN))
    out = dict(energy=e, final=f, restarts=r)
    json.dump(out, open(path, "w"))
    return out


def ctrl(tag, wait, **kw):
    return cached(tag, lambda scen: evaluate(lambda: MSAPSOController(wait, **kw), wait, scen))


def model(tag, wait, path, features):
    if not os.path.exists(path + ".zip"):
        return None
    return cached(tag, lambda scen: evaluate(policy_factory(path, wait, features), wait, scen))


def boot_ci(d, n=4000, seed=0):
    rng = np.random.default_rng(seed)
    d = np.asarray(d); idx = rng.integers(0, len(d), (n, len(d)))
    m = d[idx].mean(axis=1)
    return float(np.mean(d)), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


if __name__ == "__main__":
    out = {}
    for regime, wait, wtag in (("5ms", 5e-3, "5ms"), ("0.5ms", 5e-4, "05ms")):
        R = {}
        R["MSAPSO fiel (paper)"] = ctrl(f"paper_{wtag}", wait)
        R["MSAPSO sin reinicio"] = ctrl(f"noreset_{wtag}", wait, restart_mode="none")
        if regime == "5ms":
            R["MSAPSO optimizado (formal)"] = ctrl(f"tuned_{wtag}", wait, beta_min=0.185, beta_max=0.732, t_max=25)
        R["regla simple β=0.95, t_max=5 (post-hoc)"] = ctrl(f"simple1_{wtag}", wait, beta_min=0.95, beta_max=0.95, t_max=5)
        R["regla simple β 0.5→0.95, t_max=8 (post-hoc)"] = ctrl(f"simple2_{wtag}", wait, beta_min=0.5, beta_max=0.95, t_max=8)
        # PPO por semillas
        seeds = {}
        for s in range(3):
            tag = f"ppo_{wtag}_full_s{s}"
            r = model(tag, wait, f"modelos_V2/{tag}", OBS_VARIANTS["full"])
            if r: seeds[s] = r
        out[regime] = dict(controls=R, ppo_seeds=seeds)
    # ablacion (5 ms)
    abl = {}
    for v in ("full", "no_disp", "no_time", "no_drop", "minimal"):
        for s in range(2):
            tag = f"ppo_5ms_{v}_s{s}"
            r = model(tag, 5e-3, f"modelos_V2/{tag}", OBS_VARIANTS[v])
            if r: abl.setdefault(v, {})[s] = r
    out["ablation"] = abl
    extra = {}
    for tag, lab in (("ppo_5ms_full3M_s0", "PPO 3 M pasos, semilla 0"), ("ppo_5ms_full3M_s1", "PPO 3 M pasos, semilla 1"),
                     ("a2c_5ms_full_s0", "A2C 1 M pasos, semilla 0"), ("sac_5ms_full_s0", "SAC 300 k pasos, semilla 0")):
        r = model(tag, 5e-3, f"modelos_V2/{tag}", OBS_VARIANTS["full"])
        if r: extra[lab] = r
    out["extra"] = extra
    json.dump(out, open("resultados_V2/final_raw_V2.json", "w"))

    # ------------------ tablas de resumen ------------------
    lines = []
    def P(s=""): print(s); lines.append(s)
    for regime in ("5ms", "0.5ms"):
        D = out[regime]
        P(f"\n##### Regimen t_wait = {regime} — energia % (media sobre escenarios) | potencia final % ")
        P(f"{'metodo':46s}" + "".join(f"{g:>20s}" for g in GROUPS))
        for name, r in D["controls"].items():
            P(f"{name:46s}" + "".join(f"{np.mean(r['energy'][g]):10.2f}/{np.mean(r['final'][g]):6.2f}  " for g in GROUPS))
        if D["ppo_seeds"]:
            per_seed = {g: [np.mean(r["energy"][g]) for r in D["ppo_seeds"].values()] for g in GROUPS}
            per_seed_f = {g: [np.mean(r["final"][g]) for r in D["ppo_seeds"].values()] for g in GROUPS}
            P(f"{'PPO (media ± sd de '+str(len(D['ppo_seeds']))+' semillas)':46s}" + "".join(
                f"{np.mean(per_seed[g]):7.2f}±{np.std(per_seed[g]):4.2f}/{np.mean(per_seed_f[g]):6.2f}" for g in GROUPS))
            for s, r in D["ppo_seeds"].items():
                P(f"{'   semilla '+str(s):46s}" + "".join(f"{np.mean(r['energy'][g]):10.2f}/{np.mean(r['final'][g]):6.2f}  " for g in GROUPS))
            # diferencia pareada PPO(promedio de semillas) - paper, por escenario
            paper = out[regime]["controls"]["MSAPSO fiel (paper)"]
            P("   diferencia pareada PPO − MSAPSO fiel (puntos de energia; IC95% bootstrap sobre escenarios):")
            for g in GROUPS:
                ppo_sc = np.mean([r["energy"][g] for r in D["ppo_seeds"].values()], axis=0)
                d = ppo_sc - np.array(paper["energy"][g]); m, lo, hi = boot_ci(d)
                P(f"      {g:7s}: {m:+.2f}  [{lo:+.2f}, {hi:+.2f}]   (PPO mejor en {int((d>0).sum())}/{len(d)} escenarios)")
            for cname in ("MSAPSO optimizado (formal)", "regla simple β=0.95, t_max=5 (post-hoc)", "regla simple β 0.5→0.95, t_max=8 (post-hoc)"):
                if cname in D["controls"]:
                    P(f"   PPO − {cname}:")
                    for g in GROUPS:
                        ppo_sc = np.mean([r["energy"][g] for r in D["ppo_seeds"].values()], axis=0)
                        d = ppo_sc - np.array(D["controls"][cname]["energy"][g]); m, lo, hi = boot_ci(d)
                        P(f"      {g:7s}: {m:+.2f}  [{lo:+.2f}, {hi:+.2f}]")
    if abl:
        P("\n##### Ablacion de senales de observacion (5 ms) — energia % (media de 2 semillas)")
        P(f"{'variante (senales visibles)':46s}" + "".join(f"{g:>14s}" for g in GROUPS))
        names = {"full": "completa (8)", "no_disp": "sin dispersion (7)", "no_time": "sin t. desde reinicio (7)", "no_drop": "sin caida_rel ni dPbest (6)", "minimal": "minima: P_max, Pbest, caida_rel (3)"}
        for v, ss in abl.items():
            P(f"{names[v]:46s}" + "".join(f"{np.mean([np.mean(r['energy'][g]) for r in ss.values()]):14.2f}" for g in GROUPS))
    if out["extra"]:
        P("\n##### Otros algoritmos / mas entrenamiento (5 ms) — energia % / potencia final %")
        P(f"{'metodo':46s}" + "".join(f"{g:>20s}" for g in GROUPS))
        for lab, r in out["extra"].items():
            P(f"{lab:46s}" + "".join(f"{np.mean(r['energy'][g]):10.2f}/{np.mean(r['final'][g]):6.2f}  " for g in GROUPS))
    open("resultados_V2/analisis_final_V2.txt", "w").write("\n".join(lines))
