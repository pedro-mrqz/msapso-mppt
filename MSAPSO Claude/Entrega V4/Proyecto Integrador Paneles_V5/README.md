# V5 — Formulación corregida y comparación de algoritmos (nivel 1)

Continuación de la V4. Corrige el objetivo de entrenamiento (recompensa de grupo = mejor de las K muestras, σ fija o decreciente, más muestras al entrenar que al evaluar) y compara REINFORCE, PPO, SAC, DDPG y un árbol de decisión recalculado en cada iteración para proponer el punto de máxima potencia a partir de N potencias medidas. Sin GMPP real en entrenamiento.
**Resultados, razonamiento paso a paso y siguientes pasos:** `Reporte_Corrida_V5.pdf` (fuente: `bitacora_V5.md`). Diseño: `diseno_V5.md`.

**Resultado corto:** con pocas mediciones (N de 3 a 7), los cinco algoritmos superan a los controles sin aprendizaje; con N = 5 (10 mediciones) DDPG y el árbol ganan ≈ 3 pp, y con N = 7 (12 mediciones) el árbol llega a 98.5 % de exactitud y 96.5 % de energía en sintéticos nuevos. La ventaja persiste con ruido de 1 y 2 W. En los 4 casos reales los resultados son mixtos. No supera la exactitud del MSAPSO (≈ 100 % con 175 mediciones): la ganancia es el costo en mediciones.

## Requisitos
Python 3.10+ y `pip install -r requirements_V5.txt` (incluye scikit-learn para el árbol). Todo corre en CPU. Para regenerar el PDF: Google Chrome (macOS) y `pdftotext`.

## Cómo reproducir
```bash
python3 grid_reinforce_V5.py                  # Paso 2 (unos minutos)
python3 margen_NK_V5.py && python3 control_parabolico_V5.py     # Paso 3
for N in 3 5 7; do python3 comparar_algoritmos_V5.py --N $N --seeds 0 1 2 & done; wait   # Paso 4 (~15 min en paralelo)
for N in 5 7; do for ns in 1.0 2.0; do python3 comparar_algoritmos_V5.py --N $N --noise $ns --seeds 0 1 2 & done; done; wait   # Paso 5
python3 revision_reales_V5.py                 # Paso 6
python3 resumen_comparar_V5.py && python3 graficas_V5.py && python3 construir_reporte_V5.py
```

## Estructura
`pvsim_V5/` simulador, plantas, métricas y entorno de un paso · `datasets_V5/` 4 casos reales · `resultados_V5/` resultados y figuras · `reporte_frag_V5/` fuentes del PDF.

La V2 y la V4 no se modificaron. El PDF del paper no se incluye.
