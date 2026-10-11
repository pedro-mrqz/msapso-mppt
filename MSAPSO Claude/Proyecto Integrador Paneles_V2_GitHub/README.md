# RL sobre MSAPSO para MPPT con sombreado parcial — Corrida V2

Comparación justa entre el MSAPSO del paper (Fig. 6) y agentes de aprendizaje por refuerzo (PPO, A2C, SAC, REINFORCE gaussiano) en un simulador panel + Boost + Super-Twisting.
**Resultado principal y recomendaciones:** `Reporte_Corrida_V2.pdf` (sección "Resumen General y recomendaciones"). Paso a paso con razonamiento: `bitacora_V2.md`.

## Requisitos
Python 3.10+ y `pip install -r requirements_V2.txt` (para generar el PDF se necesita además Google Chrome en macOS y `pdftotext`).

## Estructura
- `pvsim_V2/` simulador (curvas, convertidor con numba, MSAPSO, entorno Gymnasium, REINFORCE, arnés de evaluación)
- `datasets_V2/` los 4 casos reales de sombreado
- `*.py`, `*.sh` scripts de validación, evaluación, entrenamiento, análisis y gráficas
- `modelos_V2/` modelos finales de PPO (5 ms y 0.5 ms, semillas 0–2)
- `modelos_extra_V2.zip` resto de modelos (ablaciones, A2C, SAC, 3M pasos y checkpoints de la curva de aprendizaje). Descomprimir en la raíz: `unzip modelos_extra_V2.zip` (recrea `modelos_V2/`)
- `resultados_V2/` figuras, JSON y logs que respaldan las cifras del reporte
- `reporte_frag/`, `construir_reporte_V2.py` fuentes del PDF

## Cómo reproducir
```bash
python3 validar_simulador_V2.py        # simulador V2 vs V1
python3 evaluar_baselines_V2.py        # MSAPSO fiel y variantes
python3 reinforce_grid_V2.py           # malla REINFORCE
unzip modelos_extra_V2.zip             # (opcional) usar los modelos ya entrenados
python3 analisis_final_V2.py           # estadística final (PPO vs MSAPSO, ablaciones)
python3 graficas_resultados_V2.py      # figuras
# Reentrenar desde cero (horas): ./lanzar_entrenamientos_V2.sh
```
Los comandos completos y qué produce cada script están en la sección 7 del PDF. Los modelos y la caché `resultados_V2/raw/` se regeneran con los scripts.

## Nota sobre el paper
El PDF del paper (APSO_modificado_all.pdf) no se incluye; solicitarlo al autor.
