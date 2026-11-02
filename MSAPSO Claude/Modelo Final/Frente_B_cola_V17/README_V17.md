# V17 — Verificación por cota física: evita que la búsqueda corta se quede en el pico equivocado

Frente B, sin entrenamiento. Mejora sobre la candidata V14 (MSAPSO de 3 pasadas + CEM + retroceso del 2 %), que ganaba energía pero tenía una cola de fallos grave en estático (p99 de 13 pp); su reporte dejaba pendiente un «respaldo contra la cola».

- Diseño y criterios fijados antes de correr la prueba: `diseno_V17.md` (incluye las dos revisiones hechas en validación). 
- Código y resultados: `codigo/` (copia del código V14 más los archivos `*_V17.py`; resultados en `codigo/resultados_V17/`).

## Resumen
Una verificación sin modelo ni entrenamiento, basada en que el voltaje del panel no sube al subir la corriente, detecta cuándo la búsqueda corta se quedó en el pico equivocado. Con ella, la candidata V14 cumple todos los criterios en simulación sin ruido de medición: p99 estático de 13 pp → 2.3 pp y +1.79 pp de energía dinámica sobre la V7 (la V14 daba +1.52). Con ruido de 1–2 W la cola estática vuelve a pasar de 3 pp en algunos paneles.

## Método (variante congelada: V17.2 `ref intercalado tau=0.1 k=2 pasadas=2 final tau=0.05`)
- **Cota física.** Entre dos mediciones Ia < Ib, la potencia no puede pasar de Pa·Ib/Ia. Si esa cota supera la mejor potencia medida, ahí podría haber un pico mayor; si no, el intervalo queda descartado.
- **Paso 1. Sondeos intercalados.** En las pasadas 2 y 3 del MSAPSO corto se agregan hasta 2 mediciones en los puntos medios de los intervalos cuya cota supera Pbest·1.10. Se miden en su lugar de la escalera, así que son pasos pequeños de corriente. Si un sondeo supera a Pbest, pasa a ser Gbest.
- **Paso 2.** El CEM de la V14 refina, sin cambios.
- **Paso 3. Verificación final.** Hasta 4 sondeos donde la cota supere Pbest·1.05. Si alguno mejora, el CEM refina desde ahí.
- **Corriente de la cota.** Se usa la corriente pedida, no la medida. En estático son iguales. En dinámico, a t_wait corto la medida va rezagada y producía disparos falsos.
- **Retroceso.** Se mantiene el 2 % de la V14.
- **Costo.** ≈ 40 mediciones en estático (V14: 39; V7: 70) y ≈ 30 operaciones extra por búsqueda.

## Veredicto contra los criterios (prueba, variante congelada)
| Criterio | Resultado |
|---|---|
| 1. p99 estático ≤ 3 pp (b = 0.02) en S, P y conjuntos frescos | **Cumple.** S: p99 2.33 pp (V14: 13.0), máximo 3.88 (V14: 23.0). Los 4 paneles de P: 1.38–1.93 pp. Frescos (9393/9394 y paneles 5252): 0.71–2.02 pp. Ninguno pasa de 2.4 pp. |
| 1b. Pérdida media (criterio (d) de la V14, ≤ 0.5 pp) | Al límite. Con b = 0.02: 0.27–0.59 pp (S: 0.52). Sin retroceso: −0.18 a +0.05 pp. El costo lo pone el retroceso del 2 %, no la búsqueda. |
| 2. Mantiene la ganancia dinámica | **Cumple.** Contra la V7: +1.74 [+1.33, +2.17] pp en prueba (0–599) y +1.81 [+1.44, +2.16] en confirmación (1200–2399). Contra la V14: +0.38 [+0.03, +0.75] y +0.21 [−0.08, +0.47]. |
| 3a. Ninguna celda con debilidad peor que −1 pp | **Cumple.** 33 ventajas, 0 debilidades, 3 indeterminadas. La debilidad de la V14 a t_wait = 0.5 ms (−0.67 pp) desaparece (+0.01, indeterminada; +0.98 contra la V14). |
| 3b. Pierde > 3 pp contra el MSAPSO en ≤ 10 % | **Cumple.** 6.5 % / 6.9 % (V7: 6.5 % / 8.3 %; V14: 8.0 % / 7.5 %). |
| 4. Listón ES/RL (+1.6 pp sobre la V7 con esa cola) | **Lo alcanza en estimación puntual.** +1.79 pp en los 1800 escenarios de prueba, con IC [+1.51, +2.06]: el límite inferior no llega a 1.6. Según el diseño, el listón para ES/RL pasa a ser esta V17: +1.8 pp sobre la V7 con p99 estático ≤ 2.4 pp. |

Exactitud final media en dinámico: MSAPSO 83.2 %, V7 87.2 %, V14 90.2 %, V17 90.2 %.

**Conclusión.** Se cumplen los criterios 1–3, así que la V17 se puede proponer como alternativa a la V7 en dinámico. No es mejor en todo:
- **Ruido de medición.** Con ruido estático de 1–2 W la cola vuelve a pasar de 3 pp: el p99 sube a 3–6 pp en el panel base y a 7.7–9.5 pp en el panel de 36 celdas, el de menor potencia. La V7 queda en ≤ 2.5 pp. Con ruido, la V17 sigue siendo mucho mejor que la V14 (p99 de 9–14 pp), pero peor que la V7.
- **Casos reales.** Pierde contra la V14 en los escenarios con curvas reales: −0.98 [−1.60, −0.43] pp, n = 100, solo 4 curvas distintas.
- **t_wait de 5 ms.** Queda −0.22 [−0.47, +0.04] pp contra la V14.

## Recorrido (todo en `resultados_V17/`)
1. **Diagnóstico** (`diagnostico_V17.txt`, 1000 curvas nuevas). La búsqueda corta se queda en el pico de corriente alta (≈ 0.94·Isc) cuando el global está a ≈ 0.2–0.3·Isc, entre las partículas iniciales 0.15 y 0.3. La dispersión del enjambre tras 3 pasadas es siempre ≈ 0.003, así que no sirve como detector. La cota física sí: atrapa 32 de 33 fallos y se activa en ≈ 20 % de las curvas.
2. **V17, verificación al final** (`estatico_val`, `dinamico_val`). Resuelve la cola estática, pero cuesta 0.7–1.1 pp dinámicos contra la V14, casi todo a t_wait de 0.5–1 ms. El control sin cota («ciega») no resuelve la cola, así que lo que funciona es la cota.
3. **V17.1, sondeos intercalados** (`val2`). Más barato en dinámico, pero sin verificación final no baja de 3 pp de p99.
4. **V17.2, cota con corriente pedida** (`val3`). Pasa el filtro estático y queda entre −0.08 y +0.22 pp contra la V14 en validación. Se congeló y se probó.

## Reservas
- Todo es simulación, con una reproducción propia del MSAPSO.
- No se aplicó corrección por comparaciones múltiples.
- Los escenarios 600–1199 se usaron para elegir en tres rondas de diseño (y en la V14 para elegir b), así que las cifras de validación son optimistas. Las de prueba no se usaron para nada antes.
- S y P ya se habían reportado en la V14, aunque no para elegir; por eso se agregaron conjuntos frescos, que dan lo mismo.
- En los paneles de 100 curvas, el p99 es prácticamente la 2.ª peor curva.
- El ruido estático no tenía criterio fijado y se reporta tal cual.

## Reproducir
Con numpy, scipy, numba y scikit-learn (`requirements_V14.txt`), desde `codigo/`:
```
python3 diagnostico_V17.py
python3 estatico_V17.py val | val2 | val3
python3 dinamico_V17.py val | val2 | val3
python3 estatico_V17.py test "ref intercalado tau=0.1 k=2 pasadas=2 final tau=0.05"      # RUIDO=1 o RUIDO=2 para la versión con ruido
python3 dinamico_V17.py test "ref intercalado tau=0.1 k=2 pasadas=2 final tau=0.05"
```
La parte estática tarda segundos; cada corrida dinámica, alrededor de 1–2 min con 22 núcleos.

## Siguiente paso sugerido
Hacer la verificación robusta al ruido: un margen absoluto en la cota (p. ej. Pa + 2σ) o repetir la medición antes de aceptar un sondeo que mejora. Es el único hueco que queda contra la V7.
