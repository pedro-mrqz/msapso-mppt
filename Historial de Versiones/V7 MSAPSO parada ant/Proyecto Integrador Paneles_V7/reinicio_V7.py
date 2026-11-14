"""
reinicio_V7.py — V7.2: REGLA DE REINICIO ROBUSTA (complemento minimo de la V7; sin aprendizaje, sin entrenamiento).
La regla del paper reinicia la busqueda cuando |Pbest - P| >= 5 W en una ventana. Es fragil: 5 W no escala con el tamano del panel y una sola lectura ruidosa basta para reiniciar; la parada anticipada
(V7) acorta cada busqueda y por eso expone mas al panel a esos reinicios falsos. Variantes (familia fijada ANTES de ver la prueba):
  abs5            : |Pbest - P| >= 5 W en una ventana (la del paper).
  rel r           : |Pbest - P| >= max(r * Pbest, 1 W)            (umbral RELATIVO al nivel de potencia; escala con el panel)
  confirm k       : la condicion debe cumplirse en k ventanas SEGUIDAS antes de reiniciar
  filtro m        : se compara la MEDIA de las ultimas m ventanas en lugar de una sola lectura
Se evalua en el simulador dinamico con el MSAPSO completo y con la V7 (parada anticipada) por igual. Un reinicio es «falso» si excede el numero de cambios reales de sombra del escenario.
USO: python3 reinicio_V7.py sel <i>   (valida la regla i de la familia)   |   python3 reinicio_V7.py test   (prueba fresca con la regla elegida)   |   python3 reinicio_V7.py elegir
"""
import json, sys, os
from dataclasses import dataclass
from msapso_early_V7 import *
from pvsim_V7.static_plant_V7 import DynamicPlantLogged
from operacion_V7 import make_curves_aug, make_sequence, SEG
import refuerzo_V7 as rf

SETTLE_MAX = 10
CH = json.load(open("resultados_V7/seleccion_regla_V7.json"))
def rule_of(c): return Rule(c["kind"], c["k"], c["eps"], c["delta"], c["t_min"])
FULL = make_msapso_early(Rule("none")); V7 = make_msapso_early(rule_of(CH["principal (<= 0.10 pp)"]))


@dataclass(frozen=True)
class RRule:
    name: str
    rel: float = 0.0      # 0 = umbral absoluto de 5 W
    confirm: int = 1
    filt: int = 1
    adapt_k: float = 0.0   # >0: umbral = max(5 W, adapt_k * sigma_estimada), sigma por MAD de las ultimas <= 10 lecturas en reposo (RONDA 2)

    def triggered(self, Pb, hist):
        h = hist[-self.filt:] if self.filt > 1 else hist[-1:]
        if len(hist) < self.filt: return False
        P = float(np.mean(h)) if self.filt > 1 else hist[-1]
        thr = 5.0 if self.rel == 0 else max(self.rel * Pb, 1.0)
        if self.adapt_k > 0 and len(hist) >= 5:
            w = np.array(hist[-11:-1] if len(hist) > 5 else hist); sig = 1.4826 * float(np.median(np.abs(w - np.median(w)))); thr = max(5.0, self.adapt_k * sig)
        return abs(Pb - P) >= thr


FAMILY = [RRule("abs5 (paper)"), RRule("rel 2 %", rel=0.02), RRule("rel 3 %", rel=0.03), RRule("rel 5 %", rel=0.05), RRule("abs5 + confirm 2", confirm=2), RRule("rel 3 % + confirm 2", rel=0.03, confirm=2),
          RRule("rel 2 % + confirm 2", rel=0.02, confirm=2), RRule("rel 5 % + confirm 2", rel=0.05, confirm=2), RRule("rel 3 % + confirm 3", rel=0.03, confirm=3),
          RRule("abs5 + filtro 3", filt=3), RRule("rel 3 % + filtro 3", rel=0.03, filt=3), RRule("rel 2 % + confirm 3", rel=0.02, confirm=3)]


FAMILY2 = [RRule("umbral adaptativo al ruido (k=4)", adapt_k=4.0), RRule("umbral adaptativo al ruido (k=3)", adapt_k=3.0), RRule("adaptativo (k=4) + confirm 2", confirm=2, adapt_k=4.0)]
FULLFAM = FAMILY + FAMILY2


def run_ops_rule(search_fn, curves, bounds, wait, total, rule, seed=0, noise_w=0.0):
    """Como operacion_V7.run_ops pero con la regla de reinicio `rule`. Devuelve (energia %, exactitud final %, reinicios, falsos)."""
    sched = {b: c for b, c in zip(bounds, curves) if b > 0}
    pl = DynamicPlantLogged(curves[0], wait, noise_w=noise_w, rng=np.random.default_rng(seed), schedule=sched); rng = np.random.default_rng(seed + 1); nr = 0
    while len(pl.log_E) < total:
        n0 = len(pl.log_E); search_fn(pl, pl.curve, rng); n1 = len(pl.log_E)
        j = n0 + int(np.argmax(pl.log_Pmeas[n0:n1])); I_sel = pl.log_Ipv[j]
        Pb, _ = pl.run(wait, I_sel)
        for _ in range(SETTLE_MAX):
            Pn, _ = pl.run(wait, I_sel); done = abs(Pn - Pb) < 1.0; Pb = Pn
            if done: break
        hist, streak = [], 0
        while len(pl.log_E) < total:
            Pm, _ = pl.run(wait, I_sel); hist.append(Pm)
            streak = streak + 1 if rule.triggered(Pb, hist) else 0
            if streak >= rule.confirm: nr += 1; break
    E = np.array(pl.log_E[:total]); ref = 0.0; edges = list(bounds) + [total]
    for c, a, b in zip(curves, edges[:-1], edges[1:]): ref += c.P_ceiling * wait * (b - a)
    Pt = np.array(pl.log_Ptrue[:total]); last = edges[-1]; fin = Pt[last - 20:last].mean() / curves[-1].P_ceiling
    return 100 * E.sum() / ref, 100 * fin, nr, max(nr - (len(curves) - 1), 0)


def groups(seed0, scale=1.0):
    """Grupos de escenarios (dinamico, 5 ms). `seed0` separa validacion y prueba. Devuelve {nombre: (escenarios, total_ventanas, ruido)}."""
    real, _ = scenarios(); G = {}; wait = 5e-3
    pairs = [([real[a], real[b]], [0, SEG]) for a in range(4) for b in range(4) if a != b]; G["cambio unico, 12 pares reales"] = (pairs, 2 * SEG, 0.0)
    n = int(40 * scale); cs = make_curves_aug(2 * n, seed0 + 1); sy = [([cs[2 * k], cs[2 * k + 1]], [0, SEG]) for k in range(n)]; G["cambio unico, sinteticos"] = (sy, 2 * SEG, 0.0)
    pool = make_curves_aug(200, seed0 + 2); r = np.random.default_rng(seed0 + 3); G["sombra frecuente (alto), sinteticos"] = ([make_sequence(r, pool, 100, 3000) for _ in range(int(12 * scale))], 3000, 0.0)
    r = np.random.default_rng(seed0 + 4); G["flicker parcial (a=0.3, ~100 vent.)"] = ([rf.flicker_sequence(r, 100, 0.3) for _ in range(int(10 * scale))], 3000, 0.0)
    G["ruido 1 W, cambio unico, sinteticos"] = (sy[:int(20 * scale)], 2 * SEG, 1.0); G["ruido 2 W, cambio unico, sinteticos"] = (sy[:int(20 * scale)], 2 * SEG, 2.0)
    r = np.random.default_rng(seed0 + 5); G["ruido 2 W, sombra frecuente (alto)"] = ([make_sequence(r, pool, 100, 3000) for _ in range(int(10 * scale))], 3000, 2.0)
    for nm, ns, isc, A, nsub in (("panel de 36 celdas", 36, 5.5, 1.5, 3), ("panel de 96 celdas", 96, 6.5, 1.7, 4)):
        with rf.panel(ns, isc, A):
            rr = np.random.default_rng(seed0 + 6 + ns); c2 = rf.mix_curves(rr, 2 * int(15 * scale), nsub); G[f"{nm}, cambio unico"] = ([([c2[2 * k], c2[2 * k + 1]], [0, SEG]) for k in range(int(15 * scale))], 2 * SEG, 0.0)
    return G


def evaluate_rule(rule, G, wait=5e-3):
    """Devuelve {grupo: {metodo: (energia por escenario, reinicios, falsos)}}."""
    out = {}
    for gname, (scen, total, noise) in G.items():
        out[gname] = {}
        for mname, fn in (("MSAPSO completo", FULL), ("V7", V7)):
            r = np.array([run_ops_rule(fn, cs, bd, wait, total, rule, seed=k, noise_w=noise) for k, (cs, bd) in enumerate(scen)]); out[gname][mname] = r
    return out


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "sel":
        i = int(sys.argv[2]); rule = FULLFAM[i]; G = groups(3000); res = evaluate_rule(rule, G)
        np.save(f"resultados_V7/reinicio_val_{i}.npy", np.array([[res[g][m][:, 0].mean() for m in ("MSAPSO completo", "V7")] for g in G]))
        json.dump({g: {m: dict(energia=float(res[g][m][:, 0].mean()), reinicios=float(res[g][m][:, 2].mean()), falsos=float(res[g][m][:, 3].mean())) for m in res[g]} for g in G}, open(f"resultados_V7/reinicio_val_{i}.json", "w"))
        print(f"regla {i} ({rule.name}) lista", flush=True)
    elif mode == "test":
        i = int(sys.argv[2]); G = groups(4000); base = evaluate_rule(FULLFAM[0], G); new = evaluate_rule(FULLFAM[i], G); rb = np.random.default_rng(0); lines = []; out = {}
        def boot(d, B=4000):
            idx = rb.integers(0, len(d), (B, len(d))); m = d[idx].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
        lines.append(f"PRUEBA FRESCA (semillas 4000+) | regla {FULLFAM[i].name} contra la del paper (5 W): diferencia de energia en pp [IC95 %] | reinicios falsos por escenario (paper -> regla)")
        for g in G:
            row = []
            for m in ("MSAPSO completo", "V7"):
                d = boot(new[g][m][:, 0] - base[g][m][:, 0]); fa0, fa1 = base[g][m][:, 3].mean(), new[g][m][:, 3].mean(); row.append(f"{m}: {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}] ({fa0:.1f}->{fa1:.1f})"); out[f"{g}|{m}"] = d
            lines.append(f"  {g:40s} | " + " | ".join(row))
        print("\n".join(lines)); open(f"resultados_V7/reinicio_prueba_{i}.txt", "w").write("\n".join(lines)); json.dump(out, open(f"resultados_V7/reinicio_prueba_{i}.json", "w"))
