# Cómo añadir un método

## 1. El contrato
Un método es una función `buscar(planta, curva, rng)` que no devuelve nada:
```python
def buscar(planta, curva, rng):
    P, _ = planta.run(1.0, I)     # UNA medición: opera en la corriente I (A) durante una ventana y devuelve la potencia medida (con ruido)
    ...                            # curva.Isc = corriente de cortocircuito del patrón actual (el rango útil es 0 .. Isc)
```
- Cada llamada a `planta.run` cuesta una ventana: mientras buscas, el panel entrega menos. **Menos mediciones = más energía**, siempre que encuentres el pico correcto.
- Tu método solo conoce las potencias medidas (nada de `curva.P`, `curva.I_gmpp`…: eso sería hacer trampa, el controlador real no lo sabe).
- Usa `rng` (un `numpy.random.Generator`) para todo el azar, para que los resultados sean reproducibles.
- No hace falta elegir la corriente final: el entorno fija la de mayor potencia medida durante tu búsqueda.
- Si tu método necesita memoria entre búsquedas, guárdala en una variable de la función que crea `buscar` (cierre).

## 2. Archivos
1. Copia `algoritmos/plantilla_metodo.py` → `algoritmos/mi_algoritmo.py` y edita `make_mi_metodo`.
2. En `metodos.py`: `from algoritmos.mi_algoritmo import make_mi_metodo` y una línea en `METODOS`:
   ```python
   "mi_metodo": ("Mi método", lambda: make_mi_metodo(), 0.0),    # el 0.0 es el retroceso b (0.02 = operar al 98 %)
   ```
3. (Opcional) `fichas.py`: `FICHA["mi_metodo"] = "<p><b>Qué es.</b> …</p>"` y `SHORT["mi_metodo"] = "una línea · ~N mediciones"`.

## 3. Probar y publicar en el simulador
```bash
python probar_metodo.py mi_metodo            # vista rápida (~30 s)
python grabar.py --solo mi_metodo            # sus corridas para el visor
python campana.py dyn --solo mi_metodo       # cifras de energía (≈2 min)
python campana.py est --solo mi_metodo       # cola estática
python construir_html.py                     # simulador.html con tu método
```

## 4. Criterios del proyecto (para saber si «vale la pena»)
(a) ventaja demostrable sobre la V7 (intervalo de confianza 95 % por encima de 0) en prueba y confirmación; (b) sin condiciones con debilidad demostrable peor que −1 pp; (c) pierde > 3 pp frente al MSAPSO en ≤ 10 % de escenarios; (d) cola estática: pérdida media ≤ 0.5 pp y p99 ≤ 3 pp. Hasta hoy ningún método los cumple y supera a la V7.
**Consejo:** elige parámetros con los escenarios 600–1199 (`make_scenario`) y reserva 1200–2399 para confirmar; si ajustas sobre la confirmación, sus intervalos dejan de ser honestos.
