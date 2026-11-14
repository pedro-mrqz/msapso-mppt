"""
operacion_V7.py — La parada anticipada en OPERACION (simulador dinamico Boost + Super-Twisting, reinicio por 5 W, mismo protocolo de asentamiento de la V6).
(A) Cambio abrupto UNICO de sombra: 12 pares de casos reales + 60 pares sinteticos NUEVOS (semilla 6060), 300 + 300 ventanas.
(B) Cambios de sombra FRECUENTES: regimenes estable largo (100 s), moderado, alto y muy alto (duracion media de segmento 1500/300/100/40 ventanas; series de 3000 ventanas,
    20 escenarios sinteticos semilla 9090 y 12 secuencias de los 4 casos reales). t_wait = 5 ms y 0.5 ms (el del paper).
Metodos: MSAPSO completo | parada principal | parada prudente | comprimido T=12 | comprimido T=10 (reglas CONGELADAS en validacion estatica).
Eficiencia = energia REAL integrada / suma(P_ceiling del segmento * duracion).
USO: python3 operacion_V7.py [A|B|L] -> resultados_V7/operacion_<parte>_V7.txt|json   (A = cambio unico, B = frecuentes 15 s, L = estable largo 100 s)
"""
import json, sys
from msapso_early_V7 import *
from pvsim_V7.static_plant_V7 import DynamicPlantLogged

THRESH, SETTLE_MAX, SEG = 5.0, 10, 300
CH = json.load(open("resultados_V7/seleccion_regla_V7.json"))
def rule_of(c): return Rule(c["kind"], c["k"], c["eps"], c["delta"], c["t_min"])
METHODS = [("MSAPSO completo", make_msapso_early(Rule("none"))), ("parada principal", make_msapso_early(rule_of(CH["principal (<= 0.10 pp)"]))),
           ("parada prudente", make_msapso_early(rule_of(CH["prudente (<= 0.02 pp)"]))), ("comprimido T=12", make_msapso_early(Rule("none"), compress_T=12)),
           ("comprimido T=10", make_msapso_early(Rule("none"), compress_T=10))]


def make_curves_aug(M, seed, p_global=0.5, smin=0.25):
    rng = np.random.default_rng(seed); out = []
    for _ in range(M):
        irr = random_shading_mix(rng)
        if rng.random() < p_global: irr = irr * rng.uniform(smin, 1.0)
        out.append(SyntheticPVCurve(irr))
    return out


def run_ops(search_fn, curves, bounds, wait, total, seed=0, noise_w=0.0):
    """Operacion: busqueda -> asentamiento -> park -> si |Pbest - P| >= 5 W, reinicio. curves/bounds: sombras y ventana de inicio de cada una."""
    sched = {b: c for b, c in zip(bounds, curves) if b > 0}
    pl = DynamicPlantLogged(curves[0], wait, noise_w=noise_w, rng=np.random.default_rng(seed), schedule=sched); rng = np.random.default_rng(seed + 1); nr = 0; ns = 0
    while len(pl.log_E) < total:
        n0 = len(pl.log_E); search_fn(pl, pl.curve, rng); ns += 1; n1 = len(pl.log_E)
        j = n0 + int(np.argmax(pl.log_Pmeas[n0:n1])); I_sel = pl.log_Ipv[j]
        Pb, _ = pl.run(wait, I_sel)
        for _ in range(SETTLE_MAX):
            Pn, _ = pl.run(wait, I_sel); done = abs(Pn - Pb) < 1.0; Pb = Pn
            if done: break
        while len(pl.log_E) < total:
            Pm, _ = pl.run(wait, I_sel)
            if abs(Pb - Pm) >= THRESH: nr += 1; break
    E = np.array(pl.log_E[:total]); ref = 0.0; edges = list(bounds) + [total]
    for c, a, b in zip(curves, edges[:-1], edges[1:]): ref += c.P_ceiling * wait * (b - a)
    Pt = np.array(pl.log_Ptrue[:total]); last = edges[-1]; fin = Pt[last - 20:last].mean() / curves[-1].P_ceiling
    return 100 * E.sum() / ref, 100 * fin, nr, ns


def make_sequence(rng, pool, mean_len, total):
    bounds, w = [0], 0
    while True:
        w += max(15, int(rng.exponential(mean_len)))
        if w >= total: break
        bounds.append(w)
    curves = [pool[int(rng.integers(len(pool)))]]
    for _ in bounds[1:]:
        nxt = pool[int(rng.integers(len(pool)))]
        while nxt is curves[-1]: nxt = pool[int(rng.integers(len(pool)))]
        curves.append(nxt)
    return curves, bounds


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "A"; lines = []
    def P(s=""): print(s, flush=True); lines.append(s)
    real, _ = scenarios(); out = {}
    rb = np.random.default_rng(0)
    def boot(d, B=4000):
        i = rb.integers(0, len(d), (B, len(d))); m = d[i].mean(1); return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
    def table(title, scen, wait, total):
        P(f"\n=== {title} | t_wait = {wait*1e3:g} ms | energia real / exactitud final (% de P_ceiling), reinicios, busquedas por escenario ==="); res = {}
        for name, fn in METHODS:
            r = np.array([run_ops(fn, cs, bd, wait, total, seed=k) for k, (cs, bd) in enumerate(scen)]); res[name] = r
            P(f"{name:20s} | {r[:,0].mean():6.2f} / {r[:,1].mean():7.2f} | {r[:,2].mean():5.1f} reinic. | {r[:,3].mean():5.1f} busq.")
        ref = res["MSAPSO completo"][:, 0]
        for name, _ in METHODS[1:]:
            d = boot(res[name][:, 0] - ref); P(f"   {name:20s} - MSAPSO completo (energia): {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]"); out[f"{title}|{wait}|{name}"] = d
    for wait in (5e-3, 5e-4):
        if part == "A":
            pairs = [([real[a], real[b]], [0, SEG]) for a in range(4) for b in range(4) if a != b]
            cs = make_curves_aug(120, 6060); synth = [([cs[2 * k], cs[2 * k + 1]], [0, SEG]) for k in range(60)]
            table("A) cambio unico: 12 pares de casos reales", pairs, wait, 2 * SEG); table("A) cambio unico: 60 pares sinteticos NUEVOS", synth, wait, 2 * SEG)
        elif part == "B":
            pool_syn = make_curves_aug(300, 9090)
            for kind, ml in (("moderado", 300), ("alto", 100), ("muy alto", 40)):
                rng = np.random.default_rng(31 + ml); table(f"B) sombra frecuente ({kind}), sinteticos", [make_sequence(rng, pool_syn, ml, 3000) for _ in range(20)], wait, 3000)
            rng = np.random.default_rng(77); table("B) sombra frecuente (alto), 4 casos reales", [make_sequence(rng, real, 100, 3000) for _ in range(12)], wait, 3000)
        elif part == "L" and wait == 5e-3:
            pool_syn = make_curves_aug(300, 9090); rng = np.random.default_rng(55)
            table("L) estable LARGO (100 s), sinteticos", [make_sequence(rng, pool_syn, 15000, 20000) for _ in range(12)], wait, 20000)
    open(f"resultados_V7/operacion_{part}_V7.txt", "w").write("\n".join(lines)); json.dump(out, open(f"resultados_V7/operacion_{part}_V7.json", "w"))
