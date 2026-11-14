# Diseño V7 — MSAPSO con parada anticipada

Carpeta independiente de la V2 a la V6 (intactas). Archivos con sufijo `_V7`.

## 1. Motivación
Las corridas V4–V6 mostraron que mejorar al MSAPSO en exactitud final es difícil (≈ 100 % con 175 mediciones). Pero el MSAPSO tiene margen en OTRA métrica: el costo de búsqueda. En la V2 se observó que el Gbest queda fijo en las primeras 1–3 pasadas y que el enjambre colapsa hacia la pasada 12; las pasadas 13–25 no cambian nada. Pregunta de la V7: **¿se puede parar antes, sin entrenamiento ni información extra, y obtener la misma exactitud con menos mediciones?**

## 2. Método (msapso_early_V7.py)
El algoritmo del paper intacto (7 partículas, β 0.1 → 0.95 por la Eq. 14 con t_max = 25, Eq. 13 determinista, pasadas alternantes, Gbest inmediato). Lo único que cambia es CUÁNDO se detiene: una regla OBSERVABLE (solo potencias medidas y el estado del propio enjambre) evaluada tras cada pasada t ≥ 3:
- `disp(δ)`: dispersión del enjambre std(x)/Isc < δ.
- `noimp(k, ε)`: Pbest no mejoró más de ε W en las últimas k pasadas.
- `or` / `and`: combinaciones.
Referencias: MSAPSO completo (25 pasadas), truncado fijo (t_max fijo con la β del paper sin comprimir) y β comprimida a T pasadas (se hallaron en validación; no son una regla de parada).

## 3. Protocolo (definido antes de ver la prueba)
- VALIDACIÓN (elegir la regla): 200 curvas (semillas 3030 y 3031, esta última con atenuación global), sin ruido.
- Criterio fijo: entre las reglas cuya exactitud final media no baja más de 0.10 pp de la del MSAPSO completo, la que usa menos mediciones (principal); variante prudente: ≤ 0.02 pp. Se congelan.
- PRUEBA fresca: 100 originales (semilla 4040) + 100 con atenuación (4041) + los 4 casos reales; ruido de 1 y 2 W sin re-ajustar; IC95 % bootstrap pareados.
- OPERACIÓN en el simulador dinámico (Boost + Super-Twisting, reinicio por 5 W, mismo protocolo de asentamiento de la V6), t_wait = 5 ms y 0.5 ms: (A) cambio único de sombra (12 pares de casos reales y 60 pares sintéticos nuevos, semilla 6060); (B) sombra frecuente (moderado, alto, muy alto; 20 escenarios sintéticos semilla 9090 y 12 secuencias de casos reales); (L) estable largo de 100 s.

## 4. Estado
- [x] Convergencia del MSAPSO, selección de la regla, prueba fresca con ruido y operación dinámica.
- [ ] Parada aprendida (clasificador de convergencia), combinar con el V6.1 en la alternancia, memoria de patrones y 0.5 ms con t_wait aprendido.
