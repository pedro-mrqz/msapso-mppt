# V18 — Neuroevolución: el MLP de la V11 entrenado con CEM sobre sus pesos

Frente B. Se probó entrenar la red de la V11 (MLP, *Multi-Layer Perceptron*) sin retropropagación. Cada peso es la media de una gaussiana; se muestrean 200 redes, cada una se evalúa por la potencia que logra en las curvas, se conservan las 20 mejores y se vuelve a muestrear. Es el CEM (*Cross-Entropy Method*) aplicado a los **pesos** de la red, no a la corriente. Misma red, mismos datos y mismo despliegue que la V11: solo cambia cómo se entrena.

- Diseño y criterios fijados antes de correr: `diseno_V18.md`, que incluye la revisión V18.1 hecha en validación.
- Código y resultados: `codigo/`, con una copia del código de la V14 y la V17 más los archivos `*_V18.py`. Los resultados están en `codigo/resultados_V18/`.
- Notebook de revisión con gráficas y la comparación con todos los modelos: `Notebooks/revision_V18.ipynb`.

## Resumen
**No funciona mejor que la retropropagación ni que la V17.** Con el puntaje correcto (V18.1: la potencia final de la cadena completa barrido → red → CEM sobre la corriente), la red entrenada por CEM empata en energía dinámica con la misma red de la V11 y el mismo despliegue (−0.01 y −0.08 pp). Su cola estática es peor: en S, el p99 es de 7.6 pp contra 6.1 pp. Contra la V17 pierde en todo: −0.6 a −1.0 pp de energía y p99 estático de 5.5 a 10.6 pp, contra ≤ 2.3 pp. Además necesita entrenamiento y la V17 no. **La V17 sigue siendo la candidata en dinámico y la V7 el método principal.**

## Método (variante congelada: V18.1 `NE 16x16 cola=0 ref=0.1 s0=0.1 +cota`)
- **Red.** 8 entradas (7 potencias del barrido normalizadas por la mayor, más la mayor / P_nom) → 16 → 16 → 1 (x̂ = I/Isc), ReLU, 433 parámetros. La de la V11 es 64 × 64, con 4801 parámetros. También se probaron 32 × 32 y 64 × 64.
- **Entrenamiento (CEM sobre los pesos).** Cada parámetro sigue N(μ, σ²), con μ = 0 y σ = escala de He al inicio. Cada generación tiene 200 redes y 500 curvas al azar de las 30 000 de la V11 (semilla 1111). El puntaje es la **potencia final de la cadena completa** (barrido de 7 → predicción → CEM sobre la corriente con σ0 = 0.1, simulado sin ruido). Se toman 20 élites y se suaviza con α = 0.7. Hay ruido extra que decrece hasta 0. Son 2000 generaciones, ≈ 12 min con un núcleo.
- **Despliegue.** Barrido de 7 → la red predice x̂ → CEM sobre la corriente (el de la V11: n = 7, k = 2, α = 0.7, δ = 0.005) → verificación final por cota física de la V17 (hasta 4 sondeos) → retroceso 2 %. Usa ≈ 40 mediciones en estático.
- **Control.** La red de la V11 con el mismo despliegue (σ0 = 0.1 + cota): solo cambian los pesos.

## Veredicto contra los criterios (prueba, variante congelada)
| Criterio | Resultado |
|---|---|
| 0. CEM sobre pesos contra retropropagación (mismo despliegue) | **Sin diferencia demostrable en energía; peor en cola estática.** Energía: −0.01 [−0.36, +0.34] pp en prueba y −0.08 [−0.38, +0.22] en confirmación. p99 estático: peor en 7 de 10 conjuntos sintéticos (S: 7.58 contra 6.14 pp). En los 4 casos reales del paper sale mejor (p99 1.1 contra 9.3 pp), pero con n = 4. |
| 1. p99 estático ≤ 3 pp en S, P y frescos | **No cumple.** p99 de 5.5 a 10.6 pp en los 10 conjuntos sintéticos (V17: 0.7 a 2.3). Sí cumple en los 4 casos reales (1.1 pp). |
| 2. Ganancia dinámica sobre la V7 | **Cumple.** +1.14 [+0.56, +1.76] pp en prueba (0–599) y +0.85 [+0.39, +1.31] en confirmación (1200–2399). |
| 3a. Ninguna celda con debilidad peor que −1 pp | **No cumple.** t_wait de 0.5 ms: −1.41 [−2.55, −0.29] pp (14 ventajas, 1 debilidad, 21 indeterminadas). |
| 3b. Pierde > 3 pp contra el MSAPSO en ≤ 10 % | **No cumple.** 14.8 % / 19.1 % (V17: 6.5 % / 6.9 %). |
| 4. Listón ES/RL (V17) | **No lo alcanza.** V18.1 − V17: −0.59 [−1.10, −0.10] pp en prueba y −0.96 [−1.33, −0.54] en confirmación. |

Mediciones en estático (S): V7 70, V11 36.6, V14 38.8, V17 40.1, V18.1 40.5.

**Conclusión.** La neuroevolución no supera a la retropropagación con esta red y estos datos. Solo llega a su nivel cuando se le da el puntaje correcto, que es la cadena completa. Sigue en pie la idea de la V11: el entrenamiento supervisado marca el máximo práctico de ES (Evolution Strategies) o RL con esta red. La lección útil es de método: **hay que puntuar lo que el sistema hace en operación**, no un paso intermedio (ver V18 abajo).

## Recorrido (todo en `codigo/resultados_V18/`)
1. **Piloto** (solo entrenamiento y monitoreo 2222; ver el diseño). 800 generaciones no bastaban para la red 64 × 64, así que se fijaron 2000. Un objetivo con ventana (±0.05·Isc) se degeneró y se descartó.
2. **V18: puntaje = potencia en el punto predicho** (`entrenamiento_V18.txt`, `estatico_val`, `dinamico_val`). Se probaron 6 redes × 4 despliegues. Sin refinar, las redes dan más potencia que la V11 (92.7 % contra 88.0 %). Lo logran prediciendo casi siempre ≈ 0.5 o ≈ 0.93·Isc, una regla fija que ignora el pico global. Su error contra x* es el doble. Después del refinado, ninguna pasa el filtro estático (p99 de 11 a 28 pp) y todas quedan por debajo de la V17.
3. **V18.1: puntaje = cadena completa** (`estatico_val2`, `dinamico_val2`). Se probaron 8 redes × con o sin cota. La cadena simulada coincide con la planta real (0.9922 contra 0.9924 de potencia media en 300 curvas). Mejora a la V18 (cadena: 99.1 % contra 98.2 %), pero no alcanza a la V11 (99.4 %).
4. **Selección** (`seleccion_V18.txt`). Ninguna de las 40 variantes pasó el filtro de p99 ≤ 3 pp. Según la regla, se eligió la de menor p99 máximo (11.1 pp) y se congeló.
5. **Prueba** (`estatico_test`, con ruido 1 y 2 W, y `dinamico_test`). Ver la tabla.

## Reservas
- Todo es simulación, con una reproducción propia del MSAPSO.
- No se aplicó corrección por comparaciones múltiples.
- La red se entrena solo con el panel base y sin ruido (como la V11), pero se prueba en 5 paneles y con ruido.
- La validación (600–1199) se usó en dos rondas de diseño (V18 y V18.1), además de las de la V14 y la V17.
- El puntaje con cola, el número de generaciones y el puntaje de cadena se fijaron después del piloto y de la primera validación.
- Las cifras de V10, V15 y V16 en la comparación del notebook vienen del resumen consolidado (otras campañas), no se recalcularon.

## Reproducir
Con numpy, scipy, numba, scikit-learn, matplotlib y pandas (`requirements_V14.txt`), desde `codigo/`:
```
python3 entrenar_V18.py          # V18: 6 redes (≈ 5 min)
python3 entrenar_V18.py v181     # V18.1: 8 redes (≈ 13 min en paralelo)
python3 estatico_V18.py val ; python3 estatico_V18.py val2
python3 dinamico_V18.py val ; python3 dinamico_V18.py val2
python3 seleccion_V18.py
python3 estatico_V18.py test "NE 16x16 cola=0 ref=0.1 s0=0.1 +cota"     # RUIDO=1 o RUIDO=2 para la versión con ruido
python3 dinamico_V18.py test "NE 16x16 cola=0 ref=0.1 s0=0.1 +cota"
```
La parte estática tarda segundos. Cada corrida dinámica tarda 1–3 min con 22 núcleos (ajusta `Pool(22)` si tienes menos). El entrenamiento es determinista: volver a entrenar da exactamente los mismos pesos.
