# V7 — MSAPSO con parada anticipada

El MSAPSO del paper (reproducido de la Fig. 6) sigue buscando de la pasada 13 a la 25 aunque su exactitud final ya se alcanzó hacia la pasada 9–13. Esta corrida lo detiene cuando la **dispersión del enjambre baja de 0.02**, sin entrenamiento, sin datos del panel y sin cambiar el algoritmo.
**Resultados, razonamiento paso a paso y siguientes pasos:** `Reporte_Corrida_V7.pdf` (fuente: `bitacora_V7.md`). Diseño y protocolo: `diseno_V7.md`.

**Resultado corto:** 175 → 70 mediciones (−60 %) con −0.05 pp de exactitud final en la prueba fresca (la regla se eligió en validación con un criterio fijado de antemano); en el simulador dinámico con reinicio por 5 W empata con un cambio único de sombra en casos reales, pierde ≈ 0.6 pp con 60 patrones sintéticos, no pierde nada en estable largo y gana +2.6 a +8.9 pp de energía con sombra que cambia seguido. Comprimir la β a T = 10–12 pasadas es una variante competitiva a 5 ms pero menos segura a 0.5 ms.

**Refuerzo (Paso 6, V7.1):** la regla de dispersión se sometió, sin re-ajustarla, a pruebas de estrés (1000 curvas nuevas, cuatro paneles, flicker parcial, ruido en el simulador dinámico, otros t_wait). Resiste: pérdida estática de 0.04–0.07 pp en los paneles, cola acotada (máximo 0.97 pp), ventaja con flicker parcial y con ruido en sombra frecuente; debilidades: cambio único con sintéticos (−0.4 a −0.6 pp) y ruido de 2 W (la variante prudente es más segura). La β comprimida tiene una cola de 16.7 pp y no se recomienda sin respaldo.

**Regla de reinicio (Paso 7, V7.2):** se probaron reglas más robustas que el umbral de 5 W (relativo, confirmación, filtro, adaptativo al ruido); ninguna cumplió el criterio previo, así que se mantiene la del paper. Con ruido de medición alto, añadir una confirmación de 2 ventanas es un ajuste de instalación razonable.

**Sensibilidad y cómputo (Paso 8, V7.3):** la configuración de la V7 está en una zona estable (t_min inerte; δ entre 0.01 y 0.02 casi igual); los puntos peligrosos son t_max ≤ 15 (cola de 12–17 pp), δ ≥ 0.03 y 5 partículas con ruido. La regla añade ≈ 30 operaciones por pasada y una constante de memoria.

**Campaña Monte Carlo (Paso 9):** 2400 escenarios dinámicos aleatorios; la V7 mejora al MSAPSO en promedio (+3.03 pp [+2.74, +3.32]) pero la ventaja está concentrada en sombra que cambia seguido (+4 a +7 pp); con cambio aislado o estable empata (−0.03 y −0.55 pp) con una cola de pérdidas (≈ 8 % de los escenarios pierde más de 3 pp). Las mitigaciones mínimas ayudan en parte y no se adoptan.

## Requisitos
Python 3.10+ y `pip install -r requirements_V7.txt`. Todo corre en CPU. Para regenerar el PDF: Google Chrome (macOS) y `pdftotext`.

## Cómo reproducir
```bash
python3 convergencia_V7.py && python3 seleccion_regla_V7.py && python3 evaluar_parada_V7.py
for p in A B L; do python3 operacion_V7.py $p & done; wait
for m in F N P S T; do python3 refuerzo_V7.py $m & done; wait
python3 graficas_V7.py && python3 construir_reporte_V7.py
```

## Estructura
`pvsim_V7/` simulador, plantas y métricas · `datasets_V7/` 4 casos reales · `resultados_V7/` resultados y figuras · `reporte_frag_V7/` fuentes del PDF.

Las corridas V2 a V6 no se modificaron. El PDF del paper no se incluye.
