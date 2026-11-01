# Frente A — CEM como buscador de MPPT (V10–V14)
Lee primero `Resumen_Frente_A_CEM.pdf` (3 páginas).

- `disenos_y_reportes/`: diseño (criterios escritos antes de correr) y reporte de cada versión: V10 CEM puro, V11 MLP + CEM, V12 MSAPSO corto + CEM, V13 retroceso 2 %, V14 campaña completa.
- `graficas/`: figuras y `anim_CEM_V10.gif` (caso donde el CEM puro falla).
- `codigo/`: código y resultados de la V14 (`cem_V14.py`, `msapso_cem_V14.py`, `entorno_V14.py`, `campana_V14.py`, `refuerzo_V14.py`). Requiere `pip install -r requirements_V14.txt` (la campaña carga también el MLP de la V11 como referencia, por eso necesita scikit-learn).

Pendiente del Frente A: GIF de transiciones de sombra (caso 1 → S2 → S5 → caso 3 → S10 → caso 4).
