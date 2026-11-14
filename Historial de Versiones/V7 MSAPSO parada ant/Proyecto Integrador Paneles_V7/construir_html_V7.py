"""
construir_html_V7.py — genera demo_interactiva_V7.html (un solo archivo, sin dependencias): el MSAPSO completo y la V7 (parada anticipada) corriendo lado a lado sobre
las curvas P-I (4 casos reales + 12 patrones sintéticos). La logica (Swarm, Eq. 13/14, regla de parada, reinicio de 5 W) esta reescrita en JavaScript a partir de
pvsim_V7/msapso_V7.py y msapso_early_V7.py. Las curvas se incrustan como JSON.
"""
import json, numpy as np
from pathlib import Path
from msapso_early_V7 import scenarios, SyntheticPVCurve, random_shading_mix

ROOT = Path(__file__).resolve().parent
def pack(name, c, n=360):
    g = np.linspace(0, float(c.Isc), n); P = np.interp(g, c.I, c.P, right=0.0)
    return dict(name=name, Isc=round(float(c.Isc), 4), P=[round(float(v), 2) for v in P])

real, _ = scenarios(); r = np.random.default_rng(11)
curves = [pack(f"Caso real {i+1}", c) for i, c in enumerate(real)] + [pack(f"Sintético {k+1}", SyntheticPVCurve(random_shading_mix(r))) for k in range(12)]
html = (ROOT / "reporte_frag_V7" / "demo_plantilla.html").read_text(encoding="utf-8").replace("/*CURVES*/", json.dumps(curves))
(ROOT / "demo_interactiva_V7.html").write_text(html, encoding="utf-8")
print("listo:", len(curves), "curvas,", round(len(html) / 1024), "KB")
