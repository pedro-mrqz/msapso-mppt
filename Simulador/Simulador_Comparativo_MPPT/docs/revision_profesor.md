# Revisión pedida por el profesor (noviembre 2026)

Rama `revision-profesor`. Este documento resume qué se cambió, qué se midió y qué se encontró. Ningún método original cambió su comportamiento; las dos variantes nuevas tienen ids propios.

## 1. Notas del profesor y qué se hizo

| Nota | Qué se hizo |
|---|---|
| Pintar cada población por colores en el simulador, sobre todo en el MLP + CEM | Cada algoritmo **registra la población de cada medición** al medir (`pvsim/static_plant.py: set_tag`): pasada, iteración, generación, grupo/worker y rol (cabeza o reemplazo por tiempo de vida en CEDGO). `grabar.py` guarda además la **corriente pedida**. El visor colorea cada medición por población, dibuja la corriente pedida frente a la medida, sombrea la zona V/I > 12 Ω, tiene un selector de tramo de sombra y una etiqueta con la población actual dentro de la gráfica. |
| MSAPSO y V7: revisar el primer muestreo, no se mapea bien | Confirmado con las corrientes pedidas: las partículas pedidas en 0.10, 0.15 y a veces 0.30 de Isc caen en la zona que el Boost con 12 Ω no alcanza y se miden en el borde; la primera medición suele arrastrar la corriente anterior. El enjambre arranca en la práctica con 4–5 posiciones distintas. |
| CEM puro: ver la población inicial y cada medición | Visible en el simulador (un color por iteración). Los candidatos pedidos en la zona gris se miden en el borde, pero la gaussiana se actualiza con la posición **pedida**. |
| MLP + CEM: darle a la red pares (corriente, potencia) | Variante nueva `mlp_pares` (`algoritmos/mlp_cem.py`, modelo `modelos/mlp_pares.pkl`, `python entrenar_mlp.py --pares`). Misma receta de entrenamiento que la V11, pero cada corriente pedida por debajo del borde se mide en el borde. |
| CEDGO: por qué se detiene antes del máximo | Las mediciones que pasan de 40 son **reemplazos por tiempo de vida** (un individuo con 3 generaciones sin mejorar se reemplaza y se mide de inmediato). Candidatas a explicar la convergencia prematura: la cabeza que es el mejor global nunca se mueve (el vuelo de Lévy es proporcional a α₀·(H − b)); presupuesto fijo de 5 generaciones sin criterio de convergencia; σ por grupo que se contrae con los 2 mejores. El simulador ahora muestra grupos, cabezas y reemplazos para verificarlo. |
| DecentCEM: analizar la creación de workers; muestreo uniforme (misma distancia entre puntos) | El barrido original **ya es uniforme** en la corriente pedida (10 puntos de 0.10 a 0.95 de Isc), pero los que caen en la zona gris se miden en el borde, así que los medidos no quedan parejos; y como la separación entre workers (0.15) se mide en lo pedido, dos workers pueden medir el mismo punto físico. Variante nueva `decent_alc`: los 10 puntos a la misma distancia **dentro de la zona alcanzable**. Usa el borde calculado con la curva verdadera (oráculo, cota superior); un sondeo medido (pedir I = 0) se probó y no es confiable con esperas ≤ 2 ms. |

## 2. Resultados de las variantes nuevas

Energía dinámica, 1200 escenarios de confirmación (diferencia en pp, IC 95 % bootstrap pareado):

| Método | vs MSAPSO | vs V7 | pierde > 3 pp | 5 ms | 2 ms | 1 ms | 0.5 ms (vs V7) |
|---|---|---|---|---|---|---|---|
| MLP + CEM (V11) | +3.79 [3.19, 4.38] | +1.01 [0.48, 1.50] | 18 % | +2.54 | +1.31 | +1.31 | −2.56 |
| **MLP + CEM con pares** | −3.81 [−4.57, −2.98] | **−6.59 [−7.36, −5.82]** | 40 % | +1.22 | −3.91 | −12.64 | −18.09 |
| DecentCEM (V17) | +3.13 [2.59, 3.65] | +0.35 [−0.11, 0.79] | 17 % | +3.40 | +0.60 | −0.25 | −5.17 |
| **DecentCEM zona alcanzable** | −3.56 [−4.31, −2.80] | **−6.34 [−7.05, −5.63]** | 42 % | −1.97 | −5.73 | −7.16 | −14.55 |

En prueba (0–599) el resultado es el mismo (−7.31 y −6.01 pp frente a la V7). **Ninguna de las dos variantes mejora**; empeoran sobre todo con esperas cortas.

Cola estática (1000 curvas), oficial y **con el borde de 12 Ω** (`cola_con_borde.py`, ver §3):

| Método | Mediciones | Oficial: media / p99 / máx (pp) | Con borde: media / p99 / máx (pp) |
|---|---|---|---|
| V7 | 70 | 0.05 / 0.64 / 0.97 | 0.03 / 0.27 / 0.64 |
| MLP + CEM (V11) | 37 | 0.82 / 11.66 / 21.30 | 2.74 / 15.33 / 20.36 |
| MLP + CEM con pares | 37 | 1.32 / 17.59 / 29.50 | 0.40 / 6.94 / 10.15 |
| DecentCEM (V17) | 40 | 0.25 / 5.34 / 7.64 | 0.19 / 4.00 / 9.43 |
| DecentCEM zona alcanzable | 31 | 2.39 / 33.99 / 51.08 | 0.05 / 1.17 / 3.05 |
| Candidata V14 | 39 | 0.88 / 13.0 / 23.0 | 0.41 / 1.40 / 6.31 |

**Lectura.** Las dos variantes funcionan muy bien cuando el convertidor llega a donde se le pide (cola con borde), pero no en la dinámica: con esperas cortas la corriente medida va rezagada respecto de la pedida. *Interpretación:* la red con pares recibe pares que nunca vio al entrenar (se entrenó con el borde estático), y el barrido comprimido del DecentCEM deja los mejores puntos a menos de 0.15 entre sí, así que probablemente crea un solo worker (*hipótesis*: no se aisló). Siguientes pasos posibles: entrenar la red con barridos del simulador dinámico y hacer el umbral de separación proporcional al espaciado del barrido.

## 3. Hallazgos que afectan la evaluación (para que el equipo los revise)

1. **La cola estática oficial no modela el límite de la carga.** `StaticPlant` mide la potencia exactamente en la corriente pedida aunque esté en la zona que el Boost con 12 Ω no alcanza, y compara contra el máximo **teórico**. Eso premia a los métodos que buscan en la zona inalcanzable. Con la cola con borde, la **candidata V14 cumpliría el criterio de cola** (media 0.41 ≤ 0.5 pp y p99 1.40 ≤ 3 pp), que es el motivo por el que el artículo la descarta. Su peor caso dinámico (escenario 1822, −34.6 pp) sí ocurre con el convertidor, así que la conclusión no cambia automáticamente, pero el criterio (d) merece revisarse.
2. **El máximo alcanzable de cada curva (`P_ceiling`) está subestimado** porque se calcula solo en los ~400 puntos muestreados: cuando el borde V/I = 12 Ω cae entre dos muestras, el máximo real queda entre ellas. En las 1000 curvas estáticas la subestimación es 1 % en promedio (máximo 29 %). Afecta a la referencia de la energía de todos los métodos por igual; `cola_con_borde.py` usa una rejilla fina.
3. **El MLP de la V11 se entrenó con datos que no corresponden a la operación.** Se entrenó midiendo exactamente en las 7 corrientes pedidas; con las potencias que realmente se miden con el borde de 12 Ω, su error medio al ubicar el pico sube de 0.06 a 0.53 de Isc (3000 curvas nuevas, semilla 9999).
4. **Reproducibilidad entre plataformas.** Las trazas originales se grabaron con numba (probablemente en macOS); aquí, sin numba, el núcleo del convertidor se ejecutó en C con las mismas operaciones (ver §4). Comparando las 1188 corridas comunes: MSAPSO, V7 y V7 + retroceso son **idénticas al 100 %**; MLP, V14 y DecentCEM 98–99 %; CEM 97.7 %; CEDGO 69 %; DGBCO 38 %. Las diferencias promedian −0.02 pp, pero en métodos poblacionales una corrida individual puede cambiar hasta 36 pp por diferencias en el último decimal (probablemente de `tanh`). *Hipótesis:* los puntos pedidos en la zona inalcanzable se miden en el borde con potencias casi iguales y el desempate depende de ese último decimal. Las cifras de campaña de los métodos originales se reprodujeron al decimal (p. ej., V7 +2.78 [2.39, 3.18] pp en confirmación).

## 4. Cómo se corrió y cómo reproducirlo

- Las trazas del simulador (`resultados/traces.json`) se volvieron a grabar para **todos** los métodos con el formato nuevo (corriente pedida + etiquetas). `dyn.json` y `est.json` de los métodos originales **no se tocaron** (son las cifras oficiales); se agregaron `mlp_pares` y `decent_alc`. `est_borde.json` es nuevo.
- En una máquina con numba basta con: `python entrenar_mlp.py --pares`, `python grabar.py`, `python campana.py dyn --solo mlp_pares,decent_alc`, `python campana.py est --solo mlp_pares,decent_alc`, `python cola_con_borde.py` y `python construir_html.py`.
- Aquí no había numba ni red para instalarlo: se usó un sustituto local que ejecuta `run_window` en C (mismo algoritmo RK4, mismas operaciones y orden, aritmética IEEE estricta, `-O2 -ffp-contract=off`) y deja el resto en Python. Ese sustituto no forma parte del repositorio.
- `simulador.html` pesa ~16 MB por las etiquetas nuevas (11 métodos × 11 escenarios × 12 condiciones).
