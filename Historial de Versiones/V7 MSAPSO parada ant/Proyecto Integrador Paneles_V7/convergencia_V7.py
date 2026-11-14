"""
convergencia_V7.py — ¿Cuando alcanza el MSAPSO su punto final? Con el MSAPSO completo (25 pasadas, sin ruido) sobre las 200 curvas de VALIDACION se registra, por pasada,
la exactitud (potencia verdadera en el mejor punto medido hasta ahi / GMPP), la mejora de Pbest y la dispersion del enjambre. Sirve para disenar las reglas de parada
(solo se mira VALIDACION, no la prueba). USO: python3 convergencia_V7.py -> resultados_V7/convergencia_V7.txt|json
"""
import json
from msapso_early_V7 import *

sets = make_sets(); curves = sets["val"]; lines = []
def P(s=""): print(s, flush=True); lines.append(s)
acc = np.zeros((len(curves), T_MAX)); disp = np.zeros((len(curves), T_MAX)); gain = np.zeros((len(curves), T_MAX)); passes_999 = []
for i, c in enumerate(curves):
    pl = StaticPlant(c); sw = Swarm(first_pass="ascending"); sw.restart(c.Isc, first=True); prev = 0.0
    for t in range(T_MAX):
        sw.sweep(pl, 1.0); disp[i, t] = sw.dispersion(); gain[i, t] = sw.Pbest - prev; prev = sw.Pbest
        j = int(np.where(np.array(pl.log_Pmeas) == max(pl.log_Pmeas))[0][-1]); acc[i, t] = 100 * pl.log_Ptrue[j] / c.P_gmpp
        sw.update(paper_beta(sw.t))
    passes_999.append(int(np.argmax(acc[i] >= acc[i, -1] - 0.1)) + 1)
P(f"MSAPSO completo, 200 curvas de validacion, sin ruido | exactitud final con 25 pasadas: {acc[:, -1].mean():.3f} %")
P(f"pasada en la que se alcanza (a 0.1 pp) la exactitud final de CADA curva: mediana {np.median(passes_999):.0f}, p90 {np.percentile(passes_999, 90):.0f}, p99 {np.percentile(passes_999, 99):.0f}, maximo {max(passes_999)}")
P(f"{'pasada':>6s} {'mediciones':>10s} {'exactitud media':>16s} {'exactitud p05':>14s} {'dispersion media':>17s} {'mejora media de Pbest (W)':>26s}")
for t in range(T_MAX):
    P(f"{t+1:6d} {7*(t+1):10d} {acc[:, t].mean():16.3f} {np.percentile(acc[:, t], 5):14.2f} {disp[:, t].mean():17.3f} {gain[:, t].mean():26.3f}")
open("resultados_V7/convergencia_V7.txt", "w").write("\n".join(lines)); json.dump(dict(acc=acc.tolist(), disp=disp.tolist(), gain=gain.tolist()), open("resultados_V7/convergencia_V7.json", "w"))
