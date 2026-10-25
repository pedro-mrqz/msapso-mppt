# V4 — Proponer el máximo a partir de N potencias medidas (nivel 1)

Implementa el esquema propuesto por el profesor (observación = N potencias medidas, MLP, política gaussiana, muestreo de puntos aledaños) con REINFORCE y PPO, y lo compara con referencias sin aprendizaje y con el MSAPSO del paper.
**Resultados, razonamiento paso a paso y siguientes pasos:** `Reporte_Corrida_V4.pdf` (fuente: `bitacora_V4.md`). Diseño: `diseno_V4.md`.

**Resultado corto:** con N = 7 y K = 5 (12 mediciones; el MSAPSO usa 175), REINFORCE-MLP y PPO no superan a la referencia sin aprendizaje «mejor de 7 + 5 gaussianas»; más entrenamiento no cambia el resultado. Hay margen según una cota de diagnóstico (que usa el GMPP como etiqueta y no es un método válido).

## Requisitos
Python 3.10+ y `pip install -r requirements_V4.txt`. Todo corre en CPU (los entrenamientos del nivel 1 toman segundos o pocos minutos). Para regenerar el PDF: Google Chrome (macOS) y `pdftotext`.

## Cómo reproducir
```bash
python3 probar_entorno_V4.py          # entorno valido
python3 baselines_nivel1_V4.py        # referencias sin aprendizaje
python3 cota_diagnostico_V4.py        # cota supervisada (solo diagnostico)
python3 grid_reinforce_V4.py          # malla de REINFORCE
for s in 0 1 2; do python3 ppo_nivel1_V4.py --N 7 --K 5 --steps 1000000 --seed $s; done
python3 entrenamiento_largo_V4.py     # efecto de entrenar mas
python3 graficas_V4.py && python3 construir_reporte_V4.py
```

## Estructura
`pvsim_V4/` simulador, plantas (estática y dinámica), métricas y entorno Gymnasium · `datasets_V4/` 4 casos reales · `resultados_V4/` resultados y figuras · `modelos_V4/` modelos PPO · `reporte_frag_V4/` fuentes del PDF.

La V2 (`Proyecto Integrador Paneles_V2`) no se modificó. El PDF del paper no se incluye.
