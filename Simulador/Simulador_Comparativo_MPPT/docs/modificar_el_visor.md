# Cómo modificar el visor (`plantilla.html`)

El visor es un solo archivo con HTML, CSS y JavaScript sin librerías. `construir_html.py` reemplaza la línea `const D=/*DATA*/null;` por los datos y escribe `simulador.html`. Para ver cambios: edita `plantilla.html`, corre `python construir_html.py` y recarga el navegador.
**Probar con un servidor local** (opcional): `python -m http.server 8000` en esta carpeta y abre `http://localhost:8000/simulador.html`.

## Dónde está cada cosa
- **Colores y tema** (claro/oscuro automático): variables CSS en `:root` al inicio (`--a` método A, `--b` método B, `--green`, `--red`).
- **Controles**: tarjeta superior (`id="sc"` escenario, `tw` espera, `nz` ruido, `sp` velocidad, botones `play`, `rst`, `stp`, `prv`, `swap`, `camp`).
- **Velocidades**: arreglo `speeds` (ventanas por segundo); la opción «Acelerar cuando ambos están fijos» multiplica la velocidad por 10 (mínimo 400) cuando ninguno busca (función `frame`).
- **Zoom de la gráfica de tiempo**: arreglos `ZY` (niveles verticales) y `ZX` (horizontales); función `timeDraw`.
- **Curva P–I de cada método**: función `curveDraw` (rastro de las últimas 70 ventanas, máximo alcanzable y máximo teórico).
- **Estadísticas y energía acumulada**: función `stats`; diferencia A − B en `draw`.
- **Pestaña de resultados**: se construye al final del script a partir de `D.tabla`.
- **Textos de ayuda**: pestaña «Cómo leer esta demo» (sección `id="t-how"`).

## Datos disponibles en JavaScript (`D`)
`D.scen` (escenarios con sus curvas), `D.runs` (corridas codificadas; `load(m)` las decodifica con `DecompressionStream('deflate')`), `D.metodos` (id, nombre, ficha), `D.tabla` (cifras de campaña), `D.waits` y `D.noises`.

## Ideas
Mostrar la corriente pedida además de la medida; añadir una gráfica de la ventaja acumulada A − B; exportar la corrida a CSV; añadir un tercer método a comparar.
