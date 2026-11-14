# V11 (exploratorio) — MLP ubica el pico, CEM converge

Primera aproximación rápida al Frente B (idea 4 de la reunión del 28-oct-2026 con el profesor Gerardo Jesús Camacho González). Detalle en `Reporte_Corrida_V11.pdf` (6 pp).

**Resultado:** hay señal, pero no es una solución final.
- Dinámico (600 escenarios de la campaña V7): MLP + CEM (≈ 37 mediciones) da **+1.37 pp** de energía frente a la V7 [+0.74, +2.00] y **+4.35 pp** frente al MSAPSO [+3.52, +5.14]; el MLP aporta +4.83 pp sobre CEM sin modelo.
- Estático: pierde 0.74–0.82 pp de exactitud final (V7: 0.05 pp), 11–12 % de las curvas < 98 %; con los 4 casos reales pierde 3.3 pp (n = 4). **No cumple el criterio estático** fijado antes de correr.
- El MLP se entrenó supervisado (cota superior para ES/RL). Falta generalización, ruido en el entrenamiento y entrenamiento con Evolution Strategies.

## Reproducir
```bash
python3 -m pip install -r requirements_V11.txt      # incluye scikit-learn
python3 seleccion_V11.py                            # validación (~40 s) -> MLP elegido
python3 evaluar_V11.py estatico                     # prueba fresca
python3 evaluar_V11.py dinamico                     # 600 escenarios dinámicos (~1 min)
python3 graficas_V11.py && python3 construir_reporte_V11.py
```
Diseño y criterios (escritos antes de correr): `diseno_V11.md`.
