# Bitácora de trabajo — Corrida V7 (MSAPSO con parada anticipada)

Documento vivo: cada entrada registra QUÉ se hizo, POR QUÉ (razonamiento), cómo se VERIFICÓ, QUÉ RESULTÓ y QUÉ ARCHIVOS lo respaldan. De aquí se compila el PDF.

## Contexto y punto de partida (octubre 2026)
- Las corridas V4–V6 mostraron que ganarle al MSAPSO del paper en exactitud final es muy difícil (≈ 100 % con 175 mediciones): el híbrido V6.1 empata en casos reales y pierde ≈ 3 pp en patrones sintéticos del simulador dinámico. La alternancia (V6, Paso 7) ayuda con sombra turbulenta, pero su efecto neto anual es pequeño.
- Se planteó cambiar el objetivo: **empatar en exactitud con menos costo** y atacar donde el MSAPSO tiene margen. En la V2 se había observado que el Gbest queda fijo en las primeras 1–3 pasadas y que el enjambre colapsa hacia la pasada 12; las pasadas 13–25 no parecían cambiar nada. Esta corrida (V7) prueba la idea más barata: **detener el MSAPSO cuando ya convergió**, sin entrenamiento, sin datos del panel y sin tocar el algoritmo del paper.
- Reglas del proyecto: solo potencias medidas, sin GMPP en la decisión; el GMPP solo se usa para evaluar.
- Implementación del MSAPSO: reproducción propia de la Fig. 6 del paper (borrador), en el simulador de la V2.
- **Refuerzo (Paso 6, V7.1 en la misma carpeta).** Después del Paso 5 se sometió la regla de dispersión de la V7, SIN re-ajustar nada, a pruebas de estrés que cubren los huecos de la prueba original: flicker parcial y de menor amplitud, ruido de medición en el simulador dinámico, otros paneles, estadística grande y cola de pérdidas, y otros tiempos de espera. Los resultados originales de los Pasos 1–5 no cambian.
- **Regla de reinicio robusta (Paso 7, V7.2 en la misma carpeta).** Se probó, como complemento mínimo y sin aprendizaje, reemplazar el umbral fijo de 5 W del paper por reglas más robustas (umbral relativo, confirmación en varias ventanas, filtro, umbral adaptativo al ruido). Resultado: ninguna regla cumplió el criterio fijado de antemano; se mantiene la del paper.
- **Sensibilidad y huella de cómputo (Paso 8, V7.3 en la misma carpeta).** Análisis de cuánto cambia el resultado al variar δ, t_min, el número de partículas y t_max, y cuantificación del costo de cómputo de la regla.
- **Campaña Monte Carlo (Paso 9, V7.4–V7.5 en la misma carpeta).** Validación final con 2400 escenarios dinámicos aleatorios (una sola corrida, configuración congelada). Resultado: ventaja media real (+3.0 pp) concentrada en sombra cambiante; empate con cambio aislado, con una cola izquierda de pérdidas que las pruebas anteriores no habían mostrado; las mitigaciones mínimas probadas la reducen solo en parte.

---
## PASO 1 — Diseño y protocolo
**Qué hice.** `msapso_early_V7.py`: el MSAPSO intacto (7 partículas Isc·[0.95, 0.8, 0.65, 0.5, 0.3, 0.15, 0.1], β de 0.1 a 0.95 por la Eq. 14 con t_max = 25, Eq. 13 determinista, pasadas alternantes, Gbest inmediato). Lo único nuevo es una regla de parada evaluada tras cada pasada t ≥ 3: `disp(δ)` (dispersión del enjambre std(x)/Isc < δ), `noimp(k, ε)` (Pbest no mejoró más de ε W en las últimas k pasadas) y combinaciones «O» / «Y». Referencias: MSAPSO completo, truncado fijo (t_max fijo con la β del paper sin comprimir) y β comprimida a T pasadas.
**Protocolo (definido antes de ver la prueba).** VALIDACIÓN (elegir la regla): 200 curvas (100 originales semilla 3030 + 100 con atenuación global semilla 3031), sin ruido. Criterio fijado de antemano: entre las reglas cuya exactitud final media no baje más de 0.10 pp de la del MSAPSO completo, la que use menos mediciones (regla «principal»); variante «prudente» con tolerancia de 0.02 pp. Las reglas se congelan. PRUEBA fresca: 100 originales (semilla 4040) + 100 con atenuación (4041) + los 4 casos reales, con ruido de 0, 1 y 2 W (reglas sin re-ajustar) e IC95 % bootstrap pareados. OPERACIÓN en el simulador dinámico (Boost + Super-Twisting, reinicio por 5 W, mismo protocolo de asentamiento que la V6) a 5 ms y 0.5 ms: cambio único de sombra, sombra frecuente y estable largo.
**Archivos.** `msapso_early_V7.py`, `diseno_V7.md`.

---
## PASO 2 — ¿Cuándo alcanza el MSAPSO su punto final? (convergencia)
**Qué hice.** `convergencia_V7.py`: con el MSAPSO completo (25 pasadas, sin ruido) sobre las 200 curvas de validación, registré por pasada la exactitud (potencia verdadera en el mejor punto medido hasta ahí / GMPP), la mejora de Pbest y la dispersión del enjambre. Solo se miró la validación.
**Resultado.** Exactitud final con 25 pasadas: 99.894 %. La pasada en la que cada curva alcanza (a 0.1 pp) su exactitud final: mediana 9, percentil 90 = 11, percentil 99 = 12, máximo 13. A partir de la pasada 13 no cambia nada (dispersión 0.002 → 0). Exactitud media si se detuviera tras la pasada: 1 → 93.2 %; 3 → 96.1 %; 5 → 98.4 %; 6 → 99.0 %; 8 → 99.6 %; 9 → 99.79 %; 10 → 99.84 %; 12 → 99.885 %. Dispersión media: 0.30 (pasada 1), 0.13 (5), 0.028 (9), 0.017 (10), 0.005 (12).
**Lectura.** Las pasadas 13 a 25 (84 de las 175 mediciones) no aportan nada: hay margen para parar sin perder exactitud. El Gbest aparece pronto, pero la exactitud sigue subiendo hasta la pasada ≈ 12 porque el enjambre tiene que contraerse sobre el pico; la dispersión del enjambre sigue ese proceso y puede servir como aviso de convergencia.
**Archivos.** `convergencia_V7.py`, `resultados_V7/convergencia_V7.txt|json`.

---
## PASO 3 — Selección de la regla en validación
**Qué hice.** `seleccion_regla_V7.py`: 25 reglas candidatas (dispersión con δ ∈ {0.005, 0.01, 0.02, 0.03, 0.05}; «sin mejora» con k ∈ {2, 3, 4} y ε ∈ {0.05, 0.1, 0.25, 0.5} W; combinaciones O/Y) y los truncados y comprimidos fijos, sobre las 200 curvas de validación.
**Resultado (mediciones; pérdida de exactitud final frente al MSAPSO completo, 175 mediciones).**
| Regla | Mediciones | Pérdida (pp) |
|---|---|---|
| Dispersión δ = 0.005 | 84 | +0.009 |
| Dispersión δ = 0.01 | 77 | +0.023 |
| **Dispersión δ = 0.02 (principal)** | **70** | **+0.057** |
| Dispersión δ = 0.03 | 63 | +0.104 |
| Dispersión δ = 0.05 | 56 | +0.285 |
| «Sin mejora» k = 2 | 25–26 | +3.1 a +3.2 |
| «Sin mejora» k = 3 | 37–39 | +1.7 a +1.8 |
| «Sin mejora» k = 4 | 49–54 | +0.91 a +0.95 |
| **Y: k = 2, ε = 0.1 W, δ = 0.01 (prudente)** | **80** | **+0.019** |
| Truncado fijo T = 8 / 10 / 12 (β del paper) | 56 / 70 / 84 | +0.285 / +0.057 / +0.009 |
| β comprimida a T = 6 / 8 / 10 / 12 | 42 / 56 / 70 / 84 | +0.479 / +0.119 / +0.097 / −0.041 |
**Reglas elegidas por el criterio fijado de antemano:** principal = dispersión < 0.02 (70 mediciones, 99.837 %, pérdida 0.057 pp); prudente = Y (k = 2, ε = 0.1 W, δ = 0.01) (80 mediciones, 99.875 %, pérdida 0.019 pp).
**Lectura.** (1) Las reglas «sin mejora en k pasadas» paran demasiado pronto (pierden 1–3 pp): el Pbest queda sin cambios varias pasadas (una meseta, porque el pico se encuentra pronto) y luego mejora en saltos conforme el enjambre se contrae. (2) La dispersión del enjambre sí avisa: δ = 0.02 ahorra el 60 % de las mediciones con 0.06 pp de pérdida. (3) Hallazgo lateral, fuera de la familia de reglas definida de antemano: **comprimir la β del paper a T pasadas** (el mismo algoritmo con t_max = T) iguala o supera la exactitud con el mismo número de mediciones y sube la energía de la ventana (94.5–95.5 % contra 92.7 %), porque el enjambre se contrae antes y la potencia durante la búsqueda es mayor. Se evalúa en la prueba como extra.
**Archivos.** `seleccion_regla_V7.py`, `resultados_V7/seleccion_regla_V7.txt|json`.

---
## PASO 4 — Prueba fresca (nivel estático) con ruido
**Qué hice.** `evaluar_parada_V7.py`: reglas congeladas, prueba fresca (200 curvas nuevas + 4 reales), ruido de 0, 1 y 2 W sin re-ajustar.
**Resultado sin ruido (exactitud final / energía en ventana de 200 mediciones; originales | atenuadas | reales).**
| Método | Med. | Originales | Atenuadas | Reales |
|---|---|---|---|---|
| MSAPSO completo (25 pasadas) | 175 | 99.967 / 92.85 | 99.872 / 92.55 | 99.985 / 92.58 |
| Parada principal (dispersión < 0.02) | 70 | 99.924 / 92.90 | 99.810 / 92.68 | 99.949 / 92.58 |
| Parada prudente (Y, k = 2, ε = 0.1 W, δ = 0.01) | 77 | 99.958 / 92.85 | 99.857 / 92.59 | 99.977 / 92.58 |
| β comprimida T = 12 | 84 | 99.924 / 94.60 | 99.980 / 94.46 | 99.985 / 94.54 |
| β comprimida T = 10 | 70 | 99.973 / 95.02 | 99.947 / 94.89 | 99.983 / 94.99 |
| β comprimida T = 8 | 56 | 99.748 / 95.28 | 99.695 / 95.19 | 99.998 / 95.34 |
| Truncado fijo T = 12 (β del paper) | 84 | 99.961 / 92.85 | 99.861 / 92.56 | 99.980 / 92.58 |
Diferencias pareadas con el MSAPSO completo en las 200 curvas de prueba (IC95 %): parada principal: exactitud −0.053 pp [−0.065, −0.041] y energía +0.09 [+0.06, +0.12] con 70 mediciones; parada prudente: −0.012 [−0.015, −0.009] y +0.02 [+0.01, +0.03] con 80; β comprimida T = 12: +0.032 [−0.052, +0.107] y +1.83 [+1.73, +1.93] con 84; T = 10: +0.041 [−0.019, +0.109] y +2.25 [+2.14, +2.37] con 70; T = 8: −0.198 [−0.477, −0.004] y +2.54 [+2.31, +2.73] con 56.
**Con ruido (diferencias de exactitud / energía respecto al MSAPSO completo, pp, sin re-ajustar).** 1 W: principal −0.032 [−0.074, +0.013] / +0.09; prudente −0.023 [−0.043, −0.005] / 0.00; T = 12 +0.004 [−0.134, +0.134] / +1.80; T = 10 −0.087 [−0.268, +0.069] / +2.15; T = 8 −0.320 [−0.642, −0.054] / +2.43. 2 W: principal −0.045 [−0.115, +0.028] / +0.06; prudente −0.010 [−0.034, +0.012] / +0.01; T = 12 −0.173 [−0.436, +0.066] / +1.64; T = 10 −0.173 [−0.402, +0.046] / +2.01; T = 8 −0.246 [−0.595, +0.070] / +2.41.
**Lectura.** (1) En el nivel estático la parada principal reduce las mediciones de 175 a 70 (−60 %) con una pérdida de exactitud de 0.05 pp (significativa pero mínima); la prudente pierde 0.01 pp con 77–87 mediciones. (2) La β comprimida a T = 10–12 empata en exactitud (IC que incluye cero) y suma ≈ +1.8 a +2.3 pp de energía: es un «gana-gana» en esta métrica. (3) El ruido de 1 y 2 W no cambia las conclusiones; con T = 8 y T ≤ 10 la exactitud empieza a bajar de forma apreciable con ruido.
**Archivos.** `evaluar_parada_V7.py`, `resultados_V7/evaluar_parada_V7.txt|json`.

---
## PASO 5 — Operación en el simulador dinámico (cambios de sombra y reinicio por 5 W)
**Qué hice.** `operacion_V7.py`: Boost + Super-Twisting; búsqueda, asentamiento hasta variar < 1 W entre ventanas, parking y reinicio si |Pbest − P| ≥ 5 W (mismo protocolo que la V6). Energía real integrada contra P_ceiling. (A) Cambio único de sombra, 300 + 300 ventanas: 12 pares de casos reales y 60 pares sintéticos nuevos (semilla 6060). (B) Sombra frecuente en series de 3000 ventanas (15 s): moderado (~1.5 s entre cambios), alto (~0.5 s) y muy alto (~0.2 s) con 20 escenarios sintéticos cada uno (semilla 9090), y alto con 12 secuencias de los 4 casos reales. (L) Estable largo de 100 s con 12 escenarios. t_wait = 5 ms y 0.5 ms. Las reglas son las congeladas del Paso 3.
**Resultado a 5 ms: diferencia de energía respecto al MSAPSO completo, pp [IC95 % bootstrap].**
| Escenario (MSAPSO completo, % P_ceiling) | Parada principal | Parada prudente | β comprimida T = 12 | β comprimida T = 10 |
|---|---|---|---|---|
| Cambio único, 12 pares reales (95.81) | +0.08 [+0.03, +0.12] | +0.04 [+0.01, +0.06] | +0.98 [+0.90, +1.07] | +1.23 [+1.11, +1.35] |
| Cambio único, 60 sintéticos (96.54) | −0.57 [−1.09, −0.16] | −0.54 [−1.16, −0.07] | +0.51 [+0.11, +0.82] | +0.39 [−0.18, +0.84] |
| Frecuente: moderado (86.25) | +5.86 [+3.37, +8.90] | +4.31 [+1.27, +7.48] | +4.46 [+1.36, +7.77] | +5.85 [+3.24, +8.77] |
| Frecuente: alto, sintéticos (77.98) | +2.59 [−0.49, +5.57] | +1.04 [−1.61, +3.62] | +1.77 [−0.75, +4.13] | +3.17 [+0.15, +5.96] |
| Frecuente: muy alto (68.00) | +4.13 [+1.17, +6.76] | +4.82 [+2.92, +6.70] | +4.35 [+1.44, +7.40] | +5.09 [+2.14, +7.98] |
| Frecuente: alto, 4 casos reales (76.52) | +3.88 [+0.22, +7.12] | +3.02 [−0.33, +5.87] | +5.09 [+1.84, +7.64] | +4.57 [+1.13, +7.84] |
| Estable largo, 100 s (97.12) | −0.03 [−0.05, −0.00] | −0.22 [−0.65, −0.00] | +0.54 [+0.00, +1.56] | −0.09 [−0.37, +0.08] |
**A 0.5 ms (el del paper)** (MSAPSO completo en cambio único: 96.49 con reales y 88.79 con sintéticos): parada principal −0.02 [−0.05, +0.01] con reales y −0.60 [−1.61, +0.14] con sintéticos; β comprimida T = 12: +0.34 [+0.06, +0.54] y −1.16 [−2.09, −0.22]; T = 10: +0.35 [−0.02, +0.63] y −2.15 [−3.95, −0.68]. Con sombra frecuente a 0.5 ms: parada principal +4.37 [+0.99, +8.20] (moderado), +4.75 [+0.81, +8.46] (alto), +8.85 [+6.55, +11.26] (muy alto) y +6.69 [+2.22, +11.10] (alto, casos reales); la β comprimida da +2.5 a +7.4 con ICs más anchos.
**Reinicios.** En el estable largo, el MSAPSO, la parada principal y T = 12 tuvieron 1.3 reinicios por escenario; la parada prudente 6.7 y T = 10 5.3 (reinicios falsos por deriva tras detenerse); su energía casi no cambió (−0.22 y −0.09), pero su exactitud final bajó a ≈ 98 %.
**Lectura.** (1) Con un cambio único, la parada principal empata con el MSAPSO en casos reales (+0.08 pp) y pierde ≈ 0.6 pp con 60 sintéticos a 5 ms. (2) Con sombra frecuente la ventaja es amplia: +2.6 a +8.9 pp con la parada principal (varios ICs que excluyen cero), porque cada búsqueda es más corta (70 contra 175 mediciones) y el panel pasa más tiempo en su punto. (3) En estable largo la parada principal no pierde nada (−0.03 pp). (4) La β comprimida es la más favorable a 5 ms con un cambio único (+1 a +1.2 pp en casos reales), pero a 0.5 ms pierde con sintéticos (−1.2 y −2.2 pp) y, en el caso de T = 10, genera reinicios falsos en estable largo: es menos segura. (5) La parada principal no necesita entrenamiento, ni datos del panel, ni cambiar el algoritmo; solo observa la dispersión de las partículas.
**Archivos.** `operacion_V7.py`, `resultados_V7/operacion_A_V7.*`, `operacion_B_V7.*`, `operacion_L_V7.*`.

---
## PASO 6 — V7.1: refuerzo con pruebas de estrés (huecos de la prueba original)
**Motivación.** Un revisor señalaría que la V7 se probó con cambios de sombra que reemplazan todo el patrón de golpe, con ruido solo en el nivel estático, con un solo modelo de panel y con 200 curvas de prueba. Este paso intenta romper la regla de dispersión (< 0.02, sin re-ajustarla) en cada uno de esos puntos; todo se ejecuta con `refuerzo_V7.py`. Se mantienen las referencias de la V7: MSAPSO completo, parada principal, parada prudente, dispersión < 0.01 (extra) y β comprimida T = 12 (extra).
**(S) Estadística grande y cola de pérdidas.** 1000 curvas estáticas nuevas (500 originales semilla 7777 + 500 con atenuación semilla 7778), sin ruido.
| Método | Mediciones | Exactitud final | Pérdida media (pp) | Percentil 95 | Percentil 99 | Máximo | Curvas con pérdida > 0.5 pp |
|---|---|---|---|---|---|---|---|
| MSAPSO completo | 175 | 99.934 | 0 | 0 | 0 | 0 | 0 % |
| Parada principal (disp. < 0.02) | 70 | 99.881 | 0.053 | 0.23 | 0.64 | 0.97 | 1.4 % |
| Parada prudente | 80 | 99.919 | 0.015 | 0.06 | 0.16 | 0.33 | 0 % |
| Dispersión < 0.01 (extra) | 77 | 99.914 | 0.020 | 0.09 | 0.23 | 0.35 | 0 % |
| β comprimida T = 12 (extra) | 84 | 99.886 | 0.047 | 0.01 | 1.54 | **16.73** | 1.7 % |
La pérdida de la parada principal respecto al MSAPSO completo es de 0.053 pp [IC95 % 0.047, 0.060]. La cola está acotada (máximo 0.97 pp); la β comprimida, en cambio, tiene una cola peligrosa (una curva pierde 16.7 pp).
**(P) Otros paneles** (se cambian temporalmente los parámetros del modelo de un diodo: celdas, Isc, factor de idealidad y número de sub-strings; 100 curvas por panel en el nivel estático, 20 pares en operación con cambio único a 5 ms). La regla es independiente de la escala porque la dispersión se normaliza por la Isc del panel.
| Panel | Estático: pérdida principal (70 med.) | Operación, diferencia de energía vs MSAPSO |
|---|---|---|
| 72 celdas, 6 sub-strings, Isc 9.5 A | 0.070 pp | −1.34 [−3.72, +0.09] |
| 36 celdas, 3 sub-strings, Isc 5.5 A | 0.043 pp | +0.01 [−0.04, +0.04] |
| 60 celdas, 4 sub-strings, Isc 11 A, A = 1.3 | 0.048 pp | −0.04 [−0.26, +0.10] |
| 96 celdas, 4 sub-strings, Isc 6.5 A, A = 1.7 | 0.043 pp | +0.05 [+0.01, +0.14] |
En el panel de 36 celdas P_ceiling resulta muy conservador (eficiencias > 100 %), lo que afecta a todos los métodos por igual.
**(N) Ruido de medición en el simulador dinámico** (5 ms; el ruido también afecta la regla de reinicio de 5 W): diferencia de energía de la parada principal respecto al MSAPSO completo.
| Escenario | 1 W | 2 W |
|---|---|---|
| Cambio único, 12 pares reales | +0.11 [−0.01, +0.30] | −1.87 [−5.52, +2.02] |
| Cambio único, sintéticos (40 pares) | −0.43 [−0.90, −0.05] | −1.84 [−3.91, +0.58] |
| Sombra frecuente (alto), sintéticos | +8.27 [+2.65, +13.90] | +4.15 [+2.29, +5.93] |
Con 2 W los reinicios se multiplican en todos los métodos (de 2.2 a 5.2 por escenario con parada principal; MSAPSO completo 2.2) porque el ruido dispara la regla de 5 W; la parada prudente se comporta mejor en cambio único (−0.03 [−1.83, +1.92] con sintéticos y −1.11 con reales) y igual en sombra frecuente (+4.01 [+1.59, +6.40]).
**(F) Flicker parcial y de menor amplitud** (15 escenarios por celda, 3000 ventanas): en cada cambio la irradiancia de cada sub-string se multiplica por 1 − a·U(0, 1) con probabilidad 0.5, a partir de un patrón base. Diferencia de energía de la parada principal respecto al MSAPSO completo [IC95 %].
| Amplitud a, cambio cada | 5 ms (MSAPSO completo, %) | 0.5 ms (MSAPSO completo, %) |
|---|---|---|
| 0.1, ~100 ventanas | +1.42 [+0.01, +2.99] (94.6) | +0.20 [−0.83, +1.42] (93.8) |
| 0.3, ~100 ventanas | +3.77 [+1.79, +5.80] (86.6) | +5.42 [+1.85, +9.35] (81.2) |
| 0.6, ~100 ventanas | +2.47 [−1.86, +8.66] (80.7) | +2.36 [−0.95, +5.77] (78.3) |
| 0.1, ~40 ventanas | +1.74 [+0.61, +2.98] (92.4) | −1.85 [−5.50, +0.62] (88.0) |
| 0.3, ~40 ventanas | +0.77 [−0.34, +2.03] (84.4) | +4.56 [+1.91, +7.46] (81.5) |
| 0.6, ~40 ventanas | +2.00 [−1.26, +4.95] (79.0) | +7.31 [+4.79, +9.86] (68.4) |
**(T) Otros tiempos de espera** (cambio único): t_wait = 2 ms: reales −0.39 [−0.89, +0.02], sintéticos −0.62 [−1.15, −0.13]; t_wait = 1 ms: reales −0.01 [−0.05, +0.01], sintéticos +0.60 [−0.25, +1.85]. La β comprimida T = 12 da +1.00 [+0.73, +1.34] (reales) y +0.48 [−0.09, +1.25] (sintéticos) a 2 ms y +0.56 [+0.48, +0.65] y +0.75 [−0.32, +2.20] a 1 ms.
**Lectura.** (1) La regla de dispersión resiste las pruebas: la pérdida estática es de 0.04–0.07 pp con 70 mediciones en cuatro paneles distintos y la cola está acotada (percentil 99 = 0.64 pp, máximo 0.97 pp en 1000 curvas). (2) Con flicker parcial la ventaja se mantiene: la diferencia es positiva en 11 de 12 celdas (hasta +7.3 pp) y demostrable en 6; solo una celda (0.5 ms, amplitud 0.1, cambio cada ~40 ventanas) es negativa, con intervalo que incluye el cero. (3) Con ruido, la ventaja en sombra frecuente se mantiene (+8.3 y +4.2 pp), pero en cambio único hay pérdidas de 0.4 a 1.9 pp (algunas demostrables, otras con intervalos que incluyen el cero): el ruido eleva los reinicios falsos de todos los métodos y la búsqueda corta los expone más; la parada prudente es más segura aquí. (4) En operación con cambio único el efecto es pequeño (−0.6 a +0.6 pp), salvo el panel de 72 celdas y 6 sub-strings (−1.3 pp, no demostrable con 20 pares). (5) La β comprimida a T = 12 da mejoras medias interesantes en cambio único (+0.5 a +1.0 pp), pero su cola de pérdidas es inaceptable (16.7 pp en una curva), por lo que no se recomienda sin un respaldo.
**Conclusión.** La regla de dispersión < 0.02 de la V7 queda mejor respaldada: generaliza a otros paneles, tiene cola acotada, mantiene la ventaja con flicker parcial y con ruido en sombra frecuente. Sus puntos débiles son el cambio único con patrones sintéticos (−0.4 a −0.6 pp en varios ajustes) y el ruido alto (2 W) en cambio único, donde la parada prudente es preferible. **Recomendación de uso:** parada principal (δ = 0.02) como valor por defecto; parada prudente cuando se priorice el peor caso o haya ruido alto; no usar la β comprimida sin respaldo. **Reservas:** solo simulación; escenarios de flicker generados con un modelo sencillo; 12–20 escenarios por celda con intervalos que en varios casos incluyen el cero; los parámetros de otros paneles son plausibles pero no medidos.
**Archivos.** `refuerzo_V7.py` → `resultados_V7/refuerzo_F_V7.*` (flicker), `refuerzo_N_V7.*` (ruido), `refuerzo_P_V7.*` (paneles), `refuerzo_S_V7.*` (estadística y cola), `refuerzo_T_V7.*` (t_wait); cambio de código: `operacion_V7.run_ops` admite `noise_w`.

---
## PASO 7 — V7.2: regla de reinicio robusta (resultado: se mantiene la del paper)
**Motivación.** La regla del paper reinicia la búsqueda cuando |Pbest − P| ≥ 5 W en una ventana. Es frágil: 5 W no escala con el tamaño del panel y una sola lectura ruidosa basta para disparar un reinicio; la parada anticipada acorta cada búsqueda y deja al panel más expuesto a reinicios falsos. El profesor sugirió trabajar el umbral. Se probó una familia de reglas SIN aprendizaje ni entrenamiento, aplicadas por igual al MSAPSO completo y a la V7, con `reinicio_V7.py`.
**Familia (fijada antes de ver la prueba).** (a) umbral relativo max(r·Pbest, 1 W) con r = 2, 3 o 5 %; (b) confirmación: la condición debe cumplirse en k = 2 o 3 ventanas seguidas; (c) filtro: se compara la media de las últimas 3 ventanas; y combinaciones (12 reglas con la del paper). **Ronda 2** (diseñada tras ver la validación): umbral adaptativo al ruido = max(5 W, k·σ), con σ estimada por MAD de las últimas ≤ 10 lecturas en reposo (k = 4 o 3), solo o con confirmación de 2 ventanas.
**Protocolo.** Simulador dinámico (Boost + Super-Twisting, 5 ms). Validación (semillas 3000+) con 9 grupos: cambio único con 12 pares de casos reales y con 40 sintéticos; sombra frecuente (alto); flicker parcial (a = 0.3, ~100 ventanas); ruido de 1 W y de 2 W en cambio único; ruido de 2 W en sombra frecuente; y paneles de 36 y de 96 celdas. Criterio fijado de antemano: entre las reglas cuya energía, en NINGÚN grupo (promedio de MSAPSO completo y V7), baja más de 0.25 pp respecto a la del paper, la de mayor mejora media. Se evalúa luego en una prueba fresca (semillas 4000+).
**Validación (diferencia de energía respecto a la regla del paper, pp; promedio de MSAPSO completo y V7).**
| Regla | Mejora media | Peor grupo |
|---|---|---|
| Umbral relativo 2 % / 3 % / 5 % | −0.62 / −0.08 / +0.46 | −5.01 / −3.21 / −2.08 |
| abs 5 W + confirmación de 2 ventanas | +0.18 | −0.56 |
| Relativo 3 % + confirmación 2 | +0.26 | −2.51 |
| Relativo 5 % + confirmación 2 | +0.61 | −0.88 |
| Relativo 3 % + confirmación 3 | +0.55 | −1.46 |
| abs 5 W + filtro de 3 ventanas | +0.37 | −1.26 |
| Relativo 3 % + filtro 3 | +0.40 | −2.12 |
| Adaptativo al ruido (k = 4) | 0.00 | −0.65 |
| Adaptativo al ruido (k = 3) | −0.11 | −0.98 |
| Adaptativo (k = 4) + confirmación 2 | +0.33 | −1.07 |
Ninguna regla cumple el criterio (peor grupo ≥ −0.25 pp). Las reglas relativas pierden donde el ruido es bajo (1 W: hasta −5 pp con 2 %) porque su umbral queda por debajo de la variabilidad de las lecturas; la confirmación y el filtro ganan con ruido de 2 W (+2.9 a +4.8 pp en cambio único) pero pierden capacidad de respuesta con sombra frecuente (−0.6 a −1.3 pp); el adaptativo no pierde sin ruido pero tampoco gana claramente.
**Prueba fresca (diferencia de energía de la V7 con la regla candidata menos la V7 con la del paper, pp [IC95 %]).**
| Grupo | abs 5 W + confirmación 2 | Relativo 5 % + confirmación 2 | Adaptativo al ruido (k = 4) |
|---|---|---|---|
| Cambio único, 12 pares reales | −0.07 [−0.09, −0.04] | −0.32 [−0.82, −0.05] | 0.00 |
| Cambio único, sintéticos | −0.05 [−0.11, +0.05] | −0.14 [−0.25, −0.07] | +0.01 |
| Sombra frecuente (alto) | +0.01 [−1.59, +2.04] | +0.20 [−1.55, +2.21] | 0.00 |
| Flicker parcial (a = 0.3) | −0.25 [−0.49, −0.06] | −1.03 [−3.11, +0.59] | −0.01 |
| Ruido 1 W, cambio único | +0.11 [−0.11, +0.37] | −1.07 [−3.46, +1.03] | +0.05 |
| Ruido 2 W, cambio único | +3.54 [+0.28, +6.07] | +3.30 [−1.39, +6.81] | +2.20 [−0.78, +4.72] |
| Ruido 2 W, sombra frecuente | −0.90 [−4.62, +2.35] | +4.02 [+1.69, +6.45] | −0.91 [−3.99, +2.30] |
| Panel de 36 celdas | −0.04 [−0.09, −0.01] | +3.24 [−0.23, +9.05] | 0.00 |
| Panel de 96 celdas | −0.08 [−0.15, −0.03] | −0.29 [−0.70, −0.05] | 0.00 |
Con el MSAPSO completo los resultados son análogos (por ejemplo, ruido de 2 W en cambio único: +0.10 [−5.88, +5.66], +6.00 [+3.56, +8.44] y +1.72 [−2.24, +5.90]).
**Lectura.** (1) No existe una regla de reinicio mejor que la del paper en todos los escenarios: cada mejora para el ruido alto se paga con respuesta más lenta o reinicios falsos en otros casos. (2) La confirmación de 2 ventanas es casi inocua con ruido bajo (−0.05 a −0.25 pp) y gana +3.5 pp con ruido de 2 W en cambio único, pero no ayuda con sombra frecuente ruidosa. (3) El umbral relativo del 5 % con confirmación gana mucho con ruido alto y en el panel de 36 celdas, pero pierde en los casos reales, con ruido de 1 W y con flicker. (4) El umbral adaptativo al ruido es neutral sin ruido y modestamente favorable con ruido alto (intervalos que incluyen el cero). (5) Conclusión fijada por el criterio previo: **se mantiene la regla del paper (5 W)**; si se conoce que un sitio tiene ruido de medición alto (≈ 2 W o más en un panel de 250 W), añadir la confirmación de 2 ventanas es un ajuste de instalación razonable, no un cambio de la V7.
**Reservas.** Solo simulación; 10–40 escenarios por grupo y varios intervalos que incluyen el cero; la ronda 2 se diseñó después de ver la validación; los resultados del ruido dependen de que sea gaussiano, aditivo e independiente entre ventanas.
**Archivos.** `reinicio_V7.py` (reglas y escenarios), `elegir_reinicio_V7.py` (selección), `resultados_V7/reinicio_validacion_V7.json`, `reinicio_seleccion_V7*.txt|json`, `reinicio_prueba_*.txt|json`.

---
## PASO 8 — V7.3: análisis de sensibilidad y huella de cómputo
**Motivación.** Para afirmar que la regla de la V7 es robusta hay que saber cuánto depende de sus parámetros (δ = 0.02, t_min = 3, 7 partículas, t_max = 25 del paper) y cuánto cuesta calcularla. Se varió un parámetro a la vez (y una malla δ × partículas) sobre 200 curvas FRESCAS (semillas 8100/8101) y los 4 casos reales, con ruido de 0 y 2 W; la referencia es el MSAPSO completo del paper (7 partículas, 25 pasadas). Aparte se midió la sensibilidad a δ en operación (simulador dinámico, 5 ms). Todo con `sensibilidad_V7.py`.
**Sensibilidad estática (sin ruido): mediciones; pérdida media de exactitud (pp); máximo en 200 curvas (pp).**
| Parámetro | Valor | Mediciones | Pérdida media | Máximo |
|---|---|---|---|---|
| δ | 0.005 | 84 | 0.009 | 0.18 |
| δ | 0.01 y 0.015 | 77 | 0.021 | 0.24 |
| **δ (V7)** | **0.02** | **70** | **0.067** | **0.83** |
| δ | 0.03 | 63 | 0.173 | 2.08 |
| δ | 0.05 | 56 | 0.305 | 4.84 |
| t_min | 1, 2, 3, 5 y 8 | 70 | 0.067 | 0.83 |
| Partículas | 5 | 50 | 0.113 | 2.36 |
| Partículas | 9 | 90 | 0.018 | 0.29 |
| Partículas | 12 | 120 | 0.021 | 1.31 |
| t_max | 12 | 56 | 0.235 | **16.52** |
| t_max | 15 | 56 | 0.176 | **12.68** |
| t_max | 40 | 84 | 0.070 | 2.06 |
(Con ruido de 2 W las pérdidas medias son similares, pero el máximo y el percentil 99 crecen: 5 partículas llegan a un máximo de 7.2 pp y a una pérdida de 0.69 pp en los 4 casos reales; con 9 y 12 partículas el máximo es de 5.2 y 5.6 pp.)
**Sensibilidad de δ en operación (simulador dinámico, 5 ms; diferencia de energía respecto al MSAPSO completo, pp [IC95 %]).**
| δ | Cambio único, 12 pares reales | Cambio único, 40 sintéticos | Sombra frecuente (alto), 12 secuencias |
|---|---|---|---|
| 0.005 | +0.00 [−0.00, +0.00] | −0.99 [−2.67, −0.00] | +6.19 [+0.24, +12.38] |
| 0.01 | +0.04 [+0.01, +0.06] | −1.07 [−2.78, −0.07] | +7.08 [+1.27, +13.19] |
| **0.02 (V7)** | +0.08 [+0.03, +0.12] | −0.97 [−2.68, +0.00] | +7.46 [+2.37, +12.84] |
| 0.03 | +0.14 [+0.07, +0.22] | −1.23 [−3.08, −0.14] | +8.36 [+3.53, +13.63] |
| 0.05 | +0.29 [+0.16, +0.45] | −1.10 [−2.77, +0.01] | +10.81 [+5.35, +16.48] |
**Huella de cómputo (`huella_computo_V7.py`).** La parada anticipada añade ≈ 30 operaciones aritméticas por pasada (la dispersión std(x)/Isc de las 7 posiciones, más una comparación) y una constante (δ) de memoria; no usa historial ni tablas. Frente a ello, cada pasada son 7 mediciones (35 ms de sensado a 5 ms) y se ahorran ≈ 105 mediciones (15 pasadas) por búsqueda. En un microbenchmark de Python/numpy (referencia relativa, no un tiempo de microcontrolador) la dispersión cuesta 5.4 µs por pasada y la actualización de la Eq. 13, 2.5 µs.
**Lectura.** (1) **t_min es inerte** (1 a 8 dan idéntico resultado): la dispersión no baja de δ antes de la pasada ≈ 9. (2) **δ = 0.02 está en la rodilla:** de 0.01 a 0.02 se gana el 9 % de las mediciones con 0.05 pp más de pérdida media; de 0.03 en adelante la pérdida media y sobre todo la cola crecen (máximo 2.1 y 4.8 pp). (3) **En operación δ más alto da más energía** con sombra frecuente (de +6.2 a +10.8 pp de δ = 0.005 a 0.05) y con cambio único en casos reales (hasta +0.29 pp), a costa de mayor cola de pérdidas estática; δ = 0.02 es un compromiso y δ = 0.01 es la opción conservadora. La pérdida de ≈ 1 pp con cambio único y sintéticos aparece con todos los δ, incluso con 0.005, así que no depende de la regla de parada sino de la exposición a reinicios. (4) **Partículas:** 5 partículas ahorran más (50 mediciones) pero con cola de pérdidas y fragilidad ante el ruido; 9 o más cuestan más mediciones sin mejora de energía; 7 es un buen equilibrio. (5) **t_max ≤ 15 es peligroso:** la β se contrae demasiado rápido y la cola de pérdidas llega a 12–17 pp; t_max = 25 (el del paper) o 40 es seguro. (6) El costo de cómputo es despreciable.
**Conclusión.** La configuración de la V7 está en una zona estable del espacio de parámetros: es robusta a t_min y a δ entre 0.01 y 0.02, y los puntos peligrosos son claros (t_max ≤ 15, δ ≥ 0.03 con cola larga, 5 partículas con ruido). **Recomendación:** mantener δ = 0.02, 7 partículas, t_max = 25 y t_min = 3; usar δ = 0.01 cuando se priorice el peor caso; no reducir t_max ni el número de partículas sin respaldo. **Reservas:** solo simulación; 200 curvas y 40–12 escenarios en operación; un parámetro a la vez (sin explorar interacciones más allá de la malla δ × partículas); el MSAPSO de referencia es una reproducción propia de la Fig. 6.
**Archivos.** `sensibilidad_V7.py` → `resultados_V7/sensibilidad_S_V7.*`, `sensibilidad_D_V7.*`; `huella_computo_V7.py` → `resultados_V7/huella_computo_V7.txt`.

---
## PASO 9 — V7.4 y V7.5: campaña Monte Carlo de validación final (y mitigaciones mínimas)
**Motivación.** Las pruebas anteriores de la parte dinámica usaban entre 12 y 60 escenarios por grupo, con intervalos anchos. Se corrió UNA campaña con miles de escenarios dinámicos aleatorios, con la configuración congelada (parada principal δ = 0.02 y parada prudente) y sin ajustar nada después de ver los resultados (`campana_V7.py`).
**Diseño (fijado antes de correr).** 2400 escenarios (semillas 100000 + índice), cada uno generado por completo a partir de su semilla: panel (base de 60 celdas y 4 sub-strings, y otros cuatro: 72 celdas y 6 sub-strings, 36 celdas y 3, 60 celdas con Isc 11 A y A = 1.3, y 96 celdas con Isc 6.5 A y A = 1.7; uniforme), t_wait (5 ms 40 %, 2 ms 20 %, 1 ms 20 %, 0.5 ms 20 %), régimen de sombra (cambio único 30 %, frecuente moderado ~300 ventanas entre cambios 15 %, alto ~100 20 %, muy alto ~40 10 %, flicker parcial 20 %, estable ~1500 5 %), ruido (0 W 50 %, 1 W 25 %, 2 W 25 %) y patrones (sintéticos; en el panel base, 30 % con los 4 casos reales). Métodos: MSAPSO completo, V7 principal y V7 prudente. Energía real integrada en el simulador dinámico (reinicio por 5 W, asentamiento de la V6) frente a P_ceiling.
**Resultado global (V7 principal − MSAPSO completo, pp).** Media **+3.03 [+2.74, +3.32]**; mediana +0.52; percentiles 1 / 5 / 25 / 75 / 95 / 99: −11.1 / −4.5 / −0.1 / +5.8 / +16.4 / +26.8; peor −52.9. El 50.1 % de los escenarios gana más de 0.5 pp, el 29.8 % empata (±0.5), el 20.1 % pierde más de 0.5 pp, el 8.1 % pierde más de 3 pp y el 4.3 % más de 5 pp. Reinicios por escenario: 7.3 (MSAPSO) contra 13.4 (V7). La parada prudente da +2.66 [+2.39, +2.94], mediana +0.30 y el mismo patrón de cola (8 % pierde más de 3 pp; peor −52.8).
**Por régimen (V7 principal − MSAPSO; media [IC95 %]; % que pierde > 0.5 pp; peor).**
| Régimen | n | Diferencia media | Pierde > 0.5 pp | Peor |
|---|---|---|---|---|
| Cambio único | 697 | −0.03 [−0.39, +0.32] | 21.8 % | −35.0 |
| Estable | 113 | −0.55 [−2.00, +0.70] | 23.9 % | −52.9 |
| Frecuente moderado | 362 | **+4.04 [+3.07, +5.09]** | 23.5 % | −24.8 |
| Frecuente alto | 470 | **+6.90 [+6.16, +7.66]** | 13.8 % | −22.1 |
| Frecuente muy alto | 252 | **+6.21 [+5.43, +7.01]** | 11.1 % | −17.1 |
| Flicker parcial | 506 | **+2.15 [+1.76, +2.57]** | 24.9 % | −9.7 |
En cambio único y estable las diferencias son casi simétricas alrededor de cero (gana más de 3 pp en el 7–8 % y pierde más de 3 pp en el 9–11 %); en el caso más limpio (cambio único, 5 ms, sin ruido; n = 148) la media es −0.64 pp y el 5.4 % pierde más de 3 pp contra 0.7 % que gana más de 3 pp. Con sombra frecuente gana más de 3 pp en el 67–71 % de los escenarios (alto y muy alto) y pierde más de 3 pp en el 5 %.
**Por otros estratos.** Ruido 0 / 1 / 2 W: +3.46 / +2.96 / +2.20 (pierde > 0.5 pp en 13 % / 21 % / 34 %); t_wait 5 / 2 / 1 / 0.5 ms: +2.77 / +3.00 / +2.94 / +3.66; paneles: base +2.89, 36 celdas +2.92, 60 celdas con 11 A +2.36, 72 celdas +2.34, 96 celdas +4.49; patrones reales +2.27 y sintéticos +3.07. Todos los intervalos de estos estratos excluyen el cero a favor de la V7.
**Lectura.** (1) La ventaja de la V7 es real y consistente en promedio (+3 pp; todos los estratos de t_wait, ruido y panel con intervalos que la favorecen), pero está **concentrada en sombra que cambia seguido** (+4 a +7 pp) y en el flicker parcial (+2 pp). (2) Con un cambio aislado o en periodos estables es un **empate en promedio**, con mayor varianza: cerca del 20 % de los escenarios pierde más de 0.5 pp y un 9–11 % pierde más de 3 pp, con casos extremos (hasta −53 pp). (3) Esto es una advertencia que las pruebas de estrés anteriores no mostraron por su tamaño reducido: la V7 no debe presentarse como mejora uniforme, sino como mejora con sombra cambiante y neutra con sombra estable, con una cola de riesgo. (4) La parada prudente no elimina la cola, así que no depende de δ. (5) Mecanismos observados en casos extremos: reinicios falsos por deriva lenta tras asentarse (la potencia sube 5 W en 50 ventanas y dispara la regla), búsquedas que cruzan un cambio de sombra y dejan al panel estacionado en un punto muerto (0 W) con referencia 0 W, de modo que la regla de 5 W ya no dispara, y cambios no detectados porque la potencia en el punto estacionado no cambia 5 W aunque exista un pico mejor.
**V7.5: mitigaciones mínimas (`campana_mitigacion_V7.py`, mismos 2400 escenarios y semillas; diferencia con el MSAPSO completo, pp).**
| Variante (solo parada principal) | Media [IC95 %] | Mediana | p1 / p5 | Peor | Pierde > 3 pp | Cambio único | Reinicios |
|---|---|---|---|---|---|---|---|
| V7 principal (sin cambios) | +3.03 [+2.73, +3.33] | +0.52 | −11.1 / −4.5 | −52.9 | 8.1 % | −0.03 | 13.4 |
| Retroceso de 3 % | +3.28 [+2.99, +3.58] | +1.02 | −9.0 / −4.5 | −30.7 | 8.4 % | +0.15 | 13.1 |
| Retroceso 3 % + histéresis | **+3.80 [+3.52, +4.11]** | +1.72 | −8.6 / −3.2 | −35.9 | **5.4 %** | **+0.67** | 11.4 |
| Verificación de consistencia | +3.75 [+3.44, +4.07] | +1.05 | −9.6 / −4.2 | −28.8 | 7.8 % | +0.50 | **8.8** |
| Verificación + retroceso 3 % | +3.69 [+3.35, +4.00] | +1.20 | −10.4 / −4.6 | −30.8 | 8.6 % | +0.19 | 8.7 |
La verificación de consistencia compara la potencia asentada con la medida durante la búsqueda: si es menor al 90 %, ejecuta una vez el MSAPSO completo. Las mitigaciones suman ≈ +0.25 a +0.8 pp de media, mejoran el cambio único hasta +0.67 pp y reducen los reinicios (hasta −35 % con la verificación), pero **no eliminan la cola** (peor −29 a −36 pp; 5–9 % pierde más de 3 pp). Por régimen, «retroceso + histéresis» y «verificación» mejoran sobre todo el cambio único (+0.5 a +0.7), el estable (+1.2) y el frecuente moderado (+0.8 a +1.6).
**Conclusión del paso.** (a) **Validación estadística:** con 2400 escenarios la V7 mejora al MSAPSO en promedio (+3.0 pp [+2.7, +3.3]), de forma consistente en todos los paneles, tiempos de espera y niveles de ruido, concentrada en sombra cambiante. (b) **Matiz importante:** con cambios aislados o estables empata, con una cola de pérdidas que debe declararse (≈ 8 % de los escenarios pierde más de 3 pp). (c) Las mitigaciones mínimas (retroceso + histéresis; verificación) dan una mejora modesta y una reducción de reinicios, pero no resuelven la cola; **no se adoptan como parte de la V7**: se documentan como mejoras opcionales (la combinación «retroceso + histéresis» es la que más mejora la media y reduce los casos extremos de tipo moderado). (d) Recomendación de uso: V7 para instalaciones con sombra que cambia a menudo; con sombra estable o cambios aislados no hay ganancia y conviene el MSAPSO puro si se quiere evitar la varianza.
**Reservas.** Simulación sobre un generador sintético con una reproducción propia del MSAPSO; los escenarios de 2400 sacan la estadística pero no corrigen el sesgo del modelo; la mezcla de regímenes (30 % cambio único, 5 % estable) fue elegida por nosotros y determina la media global; el P_ceiling conservador produce eficiencias mayores a 100 % en algunos escenarios (120 de 2400 con el MSAPSO), lo que afecta a todos los métodos; las mitigaciones se probaron después de ver la campaña.
**Archivos.** `campana_V7.py` → `resultados_V7/campana_V7.jsonl`, `campana_V7.txt|json`; `campana_mitigacion_V7.py` → `resultados_V7/campana_mitigacion_V7.jsonl`, `campana_mitigacion_V7.txt|json`.
