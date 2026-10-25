# Diseño V4 — Proponer el máximo a partir de N potencias medidas (RL con MLP)

Carpeta independiente de la V2 (que queda intacta). Todos los archivos terminan en `_V4`.

## 1. Propuesta del profesor (reunión del 21-oct-2026 y respuestas posteriores)
1. Medir N potencias en N corrientes uniformes y ascendentes (N = 7, 10, 20 a comparar).
2. Un agente de RL con un MLP sencillo toma esas potencias como observación y propone dónde está el máximo.
3. El muestreo de puntos aledaños es parte de policy gradients (política gaussiana, σ pequeña); no es una etapa aparte.
4. Variante con árbol de decisión dentro del RL (el árbol debe recalcularse en cada iteración): entrenarlo y ver si, con muy pocos muestreos, propone bien el máximo en prueba.
5. Algoritmos: REINFORCE con baselines → PPO → SAC y DDPG.
6. NO usar el GMPP real en entrenamiento (evitar fuga de datos). Recompensa solo con potencias medidas.
7. Métrica: medir número de mediciones y energía; priorizar mediciones. Preferir iteraciones al tiempo (su Colab no modela la dinámica).
8. Rango de corrientes fijado con la Isc NOMINAL. t_wait = 0.5 ms (base del paper).
9. Reinicio: ante una variación de potencia de 5 W se remuestrean los N puntos. Aprender el umbral óptimo: más adelante.
10. Escenarios adicionales: sombra que se desplaza gradualmente y ruido de medición.

## 2. Decisiones de diseño (las marcadas «propuesta» las tomamos nosotros; confirmar)
| Decisión | Valor | Origen |
|---|---|---|
| Rango de corrientes | [0.10, 0.95] · Isc_nom, Isc_nom = 8.9 A | indicación del profesor + fracciones del paper |
| Observación | N potencias medidas / 250 W (potencia nominal de hoja de datos) | propuesta |
| Acción | corriente propuesta en el rango; gaussiana alrededor de μ(obs) | profesor |
| Recompensa | potencia MEDIDA en la corriente muestreada / 250 W | profesor (sin GMPP) |
| Episodio | N + K mediciones (K muestras por patrón); bandido contextual (γ = 0) | propuesta |
| Evaluación | el GMPP real solo calcula eficiencias, nunca entra al entrenamiento | profesor |
| Dos niveles | 1: potencia estática (iteraciones, Colab del profesor). 2: simulador con Boost + Super-Twisting a 0.5 ms (y 5 ms) | propuesta |
| Referencias | MSAPSO fiel, regla simple, mejor-de-N, mejor-de-N + gaussiana (control sin aprendizaje), PPO V2, optimización bayesiana | propuesta |
| Umbral de reinicio | 5 W fijo (aprenderlo queda para después) | profesor |

## 3. Métricas (nivel 1)
`n_meas` (mediciones usadas), `n99` (primera medición ≥ 99 % del GMPP), `eff_final` (punto elegido / GMPP), `eff_energy`
(promedio de potencia verdadera sobre una ventana de 200 mediciones). Ver `pvsim_V4/medicion_V4.py`.
Advertencia: `eff_energy` depende de la longitud de la ventana (200); favorece búsquedas cortas. Se reportan todas.

## 4. Estado
- [x] Entorno Gymnasium (nivel estático y dinámico) y pruebas de humo (`probar_entorno_V4.py`).
- [x] Referencias sin aprendizaje en el nivel 1 (`baselines_nivel1_V4.py` → `resultados_V4/baselines_nivel1_V4.txt`).
- [x] REINFORCE con baselines (MLP) y PPO en el nivel 1 (N=7, K=5): ver `resultados_V4/` (reinforce_grid_*, reinforce_reward_*, ppo_*). Resultado: no superan a la referencia sin aprendizaje «mejor-de-7 + 5 gauss.» en sintéticos (ver bitácora/mensaje).
- [ ] SAC, DDPG, variante con árbol, barrido de N y K.
- [ ] Reinicio por 5 W, sombra gradual, ruido en entrenamiento, nivel dinámico completo, optimización bayesiana.
- [ ] Nota: en el nivel dinámico la eficiencia debe medirse contra P_ceiling (Boost con R = 12 Ω), no contra el GMPP teórico.
