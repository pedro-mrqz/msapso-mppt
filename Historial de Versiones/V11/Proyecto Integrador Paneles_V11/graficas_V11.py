"""graficas_V11.py — Figuras del reporte V11. USO: python3 graficas_V11.py"""
import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
AZ, GR, RJ, VD, NA = "#1f5fa8", "#8e959e", "#d9382b", "#1e9e4a", "#d98a1f"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
E = json.load(open("resultados_V11/evaluar_V11_estatico.json")); N = ["MSAPSO completo (paper)", "V7 (parada por dispersion)", "MLP + CEM", "sin modelo (CEM desde el mejor punto)", "solo MLP (8 med.)"]
SH = ["MSAPSO\n(175)", "V7\n(70)", "MLP+CEM\n(≈37)", "sin modelo\n(≈40)", "solo MLP\n(8)"]; C = [GR, AZ, VD, NA, RJ]
fin = [np.mean(E[f"{n}|grande|0.0"]["final"]) for n in N]; fail = [100 * np.mean(np.array(E[f"{n}|grande|0.0"]["final"]) < 98) for n in N]
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
ax[0].bar(range(5), [100 - v for v in fin], color=C); ax[1].bar(range(5), fail, color=C)
for a, t, v, f in ((ax[0], "Pérdida de exactitud final (pp)", [100 - v for v in fin], "{:.2f}"), (ax[1], "% de curvas con exactitud < 98 %", fail, "{:.1f} %")):
    a.set_xticks(range(5)); a.set_xticklabels(SH, fontsize=8); a.set_ylabel(t)
    for i, x in enumerate(v): a.text(i, x * 1.02 + 0.02, f.format(x), ha="center", fontsize=8)
fig.suptitle("Nivel estático, 1000 curvas frescas, sin ruido (medición promedio entre paréntesis)", fontweight="bold"); fig.tight_layout(); fig.savefig("graficas_V11/fig_estatico_V11.png", dpi=130); plt.close(fig)
ref = {json.loads(l)["idx"]: json.loads(l) for l in open("resultados_V11/campana_V7_referencia.jsonl")}; R = [json.loads(l) for l in open("resultados_V11/evaluar_V11_dinamico.jsonl")]
regs = ["unico", "estable", "moderado", "alto", "muy alto", "flicker"]
def dm(f): return [np.mean([f(r) for r in R if r["regimen"] == g]) for g in regs]
v7 = dm(lambda r: ref[r["idx"]]["principal"]["e"] - ref[r["idx"]]["full"]["e"]); ml = dm(lambda r: r["MLP + CEM"]["e"] - ref[r["idx"]]["full"]["e"]); sm = dm(lambda r: r["sin modelo (CEM desde el mejor punto)"]["e"] - ref[r["idx"]]["full"]["e"])
fig, ax = plt.subplots(figsize=(10, 3.8)); w = 0.27
for j, (v, lab, c) in enumerate(((v7, "V7", AZ), (sm, "sin modelo (CEM desde el mejor punto)", NA), (ml, "MLP + CEM", VD))): ax.bar(np.arange(6) + (j - 1) * w, v, w, color=c, label=lab)
ax.axhline(0, color="k", lw=.8); ax.set_xticks(range(6)); ax.set_xticklabels([f"{g}\n(n={sum(1 for r in R if r['regimen']==g)})" for g in regs]); ax.set_ylabel("Energía vs MSAPSO completo (pp)"); ax.legend(fontsize=8)
ax.set_title("Simulador dinámico: 600 escenarios aleatorios, por régimen de cambio de sombra", fontweight="bold"); fig.tight_layout(); fig.savefig("graficas_V11/fig_dinamico_V11.png", dpi=130); plt.close(fig)
