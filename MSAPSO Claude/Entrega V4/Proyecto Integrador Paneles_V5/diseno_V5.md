# Diseño V5 — Formulación corregida y comparación de algoritmos (nivel 1)

Carpeta independiente de la V2 y de la V4 (que quedan intactas). Todos los archivos terminan en `_V5`.

## 1. Punto de partida (conclusión de la V4)
Con la formulación de la V4 (recompensa = potencia media de las K muestras; σ aprendida o fija; K de entrenamiento = K de evaluación), REINFORCE-MLP y PPO no superaron a «mejor de N + K gaussianas» (sin aprendizaje) con N = 7, K = 5. Causa probable: se optimiza la potencia PROMEDIO de las muestras, lo que empuja σ a 0 (σ de PPO colapsó a 0.013) y no premia al MEJOR punto, que es el que se elige al final.

## 2. Reglas que se mantienen (indicaciones del profesor)
Sin GMPP real en entrenamiento (observación y recompensa solo con potencias medidas; el GMPP solo calcula eficiencias al evaluar); rango de corrientes [0.10, 0.95]·Isc_nominal (8.9 A); N potencias uniformes y ascendentes como observación; muestreo de puntos aledaños con política gaussiana de σ pequeña; métrica: número de mediciones y energía (prioridad: mediciones); orden de algoritmos REINFORCE → PPO → SAC y DDPG; variante con árbol de decisión recalculado en cada iteración; ruido de medición como escenario adicional.

## 3. Correcciones de la V5
| # | Corrección | Dónde |
|---|---|---|
| a | Recompensa de grupo: `max` (mejor de las K muestras) o `gain` (mejora sobre el mejor punto del barrido), en vez de la potencia media | `reinforce_nn_V5.py`, `bandit_env_V5.py` |
| b | σ fija o decreciente (no se aprende) | `reinforce_nn_V5.py`, `algoritmos_V5.py` |
| c | K de entrenamiento distinto del K de evaluación | `reinforce_nn_V5.py` |
| d | Un mismo entorno de un paso (bandido contextual) con recompensa `gain` para PPO, SAC y DDPG | `pvsim_V5/bandit_env_V5.py` |
| e | Árbol de decisión dentro del bucle de RL, reajustado en cada iteración con la mejor acción MEDIDA | `algoritmos_V5.py` |

## 4. Decisiones propias (por confirmar con el profesor)
Normalizar por 250 W; σ de evaluación = 0.05·Isc_nominal; ventana de 200 mediciones para la métrica de energía; controles sin aprendizaje (simple y parabólico) como referencia; atenuación global en el generador sintético (se propuso después de ver el fallo en los casos reales; ver el Paso 6).

## 5. Estado
- [x] Corrección de REINFORCE (malla de 24 configuraciones).
- [x] Barrido de N y K y control más fuerte (parabólico).
- [x] PPO, SAC, DDPG y árbol sobre la misma formulación (N = 3, 5, 7; 3 semillas).
- [x] Ruido de medición (1 y 2 W) y revisión de los casos reales.
- [ ] Nivel dinámico (con la eficiencia contra P_ceiling), reinicio por 5 W, sombra gradual, optimización bayesiana, rango adaptable a la Isc.
