# Simulador comparativo de métodos MPPT bajo sombreado parcial

Proyecto Integrador · Maestría en Inteligencia Artificial Aplicada · Tecnológico de Monterrey
Pregunta del proyecto: ¿se puede mejorar el **MSAPSO** del paper (7 partículas, 175 mediciones por búsqueda) en energía entregada, sin empeorar su exactitud ni su cola de riesgo?

Este repositorio contiene el **simulador interactivo** con el que se comparan 9 métodos (MSAPSO, V7, V7 + retroceso, CEM puro, MLP + CEM, candidata V14, DGBCO, CEDGO y DecentCEM) y todo lo necesario para **añadir tus propios métodos, escenarios y cambios al visor**.

## 1. Solo quiero jugar con él (sin instalar nada)

Abre **`simulador.html`** con doble clic (Chrome, Edge, Safari 16.4+ o Firefox 113+). Es un solo archivo de ~10 MB, funciona sin internet.
Elige dos métodos (uno a cada lado), un escenario, el tiempo de espera y el ruido, y pulsa **Iniciar**. El botón **ⓘ** explica cada método; la pestaña **Resultados** trae las cifras de las campañas.

> Lo que ves son **corridas reales** del simulador dinámico (convertidor Boost + control Super-Twisting), grabadas con el mismo código que está en este repositorio. El navegador solo las reproduce.
> Para compartirlo como página web: en GitHub, *Settings → Pages → Deploy from a branch → main / root*, y abre `https://<usuario>.github.io/<repo>/simulador.html`.

## 2. Quiero modificar o añadir cosas

### Instalación (una vez)
```bash
python3 -m venv .venv && source .venv/bin/activate     # opcional pero recomendado
pip install -r requirements.txt                         # numpy, numba, scikit-learn
```
Probado con Python 3.14; debería funcionar con 3.10 o superior. Si `pickle` no abre `modelos/mlp_elegido.pkl` (otra versión de scikit-learn), corre `python entrenar_mlp.py`.

### Flujo para probar un método nuevo
| Paso | Comando | Qué hace | Tiempo |
|---|---|---|---|
| 1. Escríbelo | copia `algoritmos/plantilla_metodo.py` y edítalo; regístralo en `metodos.py` | ver [docs/anadir_un_metodo.md](docs/anadir_un_metodo.md) | — |
| 2. Vista rápida | `python probar_metodo.py mi_metodo` | lo compara con el MSAPSO y la V7 (energía, cola) | ~30 s |
| 3. Grábalo | `python grabar.py --solo mi_metodo` | graba sus corridas en todos los escenarios | ~15 s |
| 4. Cifras oficiales | `python campana.py dyn --solo mi_metodo` y `python campana.py est --solo mi_metodo` | energía en 1 800 escenarios y cola en 1 000 curvas | ~2 min |
| 5. Reconstruye | `python construir_html.py` | genera `simulador.html` con tu método | segundos |

(Opcional) escribe su ficha del botón ⓘ en `fichas.py`.

### Otras cosas que se pueden cambiar
- **Parámetros de un método existente**: edita su línea en `metodos.py` (por ejemplo `delta=0.02` de la V7) y repite los pasos 2–5 con `--solo v7`. *Ojo:* eso cambia los resultados de ese método; conviene registrarlo como un id nuevo (`v7_delta03`) y comparar.
- **Un escenario nuevo en el simulador**: `python grabar.py --agregar 1234 --nombre "Mi escenario" --texto "Por qué es interesante"` (cualquier índice 0–2399; el índice fija panel, sombra, espera y ruido). Luego `python construir_html.py`.
- **El visor** (colores, controles, gráficas, textos): edita `plantilla.html` y corre `python construir_html.py`. Ver [docs/modificar_el_visor.md](docs/modificar_el_visor.md).
- **El simulador físico** (inductor, carga, control): `pvsim/converter.py`. Si lo cambias hay que volver a correr `campana.py` (todos) y `grabar.py` (todos), porque cambian todos los resultados.

### Ideas para empezar
1. Mejora el método de ejemplo de `plantilla_metodo.py` (solo usa ~23 mediciones y su cola es mala: ¿puedes bajar el p99 a ≤ 3 pp?).
2. Prueba una V7 con otro umbral de parada o con retroceso de 4 %.
3. Combina la V7 con la verificación de cola que propone el artículo (un barrido de verificación cuando el enjambre no converge).
4. Añade un escenario donde un método se luzca y otro falle, y comparte el índice.

## 3. Mapa del repositorio

```
simulador.html          el simulador listo para abrir (generado; ~10 MB)
plantilla.html          el visor (HTML + CSS + JS) con un marcador donde se inyectan los datos
metodos.py              REGISTRO de métodos: id -> (nombre, constructor, retroceso)
fichas.py               texto del botón ⓘ de cada método
algoritmos/             un archivo por familia de métodos (msapso_early, cem, mlp_cem, msapso_cem, dgbco, dgo, decentcem, plantilla_metodo)
pvsim/                  simulador físico: modelo de un diodo del arreglo, convertidor Boost + Super-Twisting, plantas estática y dinámica, MSAPSO base
entorno.py              generador de escenarios (semilla 100000 + índice) y lazo de operación (búsqueda → fijo → reinicio si |ΔP| ≥ 5 W)
campana.py              mide los métodos (energía dinámica y cola estática) -> resultados/dyn.json, est.json
grabar.py               graba las corridas ventana por ventana -> resultados/traces.json
construir_html.py       junta todo en simulador.html
probar_metodo.py        prueba rápida de un método contra el MSAPSO y la V7
entrenar_mlp.py         re-entrena el MLP (si no abre el .pkl incluido)
catalogo.json           escenarios que aparecen en el simulador (editable)
datasets/               4 casos reales del paper (curvas I-V)
modelos/                MLP entrenado (V11)
resultados/             datos que usa el visor (traces.json ~10 MB, dyn.json, est.json)
docs/                   guías: cómo funciona, cómo añadir un método, cómo modificar el visor
```
Cómo encaja todo: [docs/como_funciona.md](docs/como_funciona.md).

## 4. Preguntas frecuentes
- **¿Por qué no puedo dibujar mi propia sombra?** El visor reproduce corridas grabadas con el simulador en Python (para que sean idénticas a los resultados reportados). Para escenarios nuevos usa `grabar.py --agregar`.
- **¿Qué es el «máximo alcanzable»?** Con la carga de 12 Ω un Boost solo alcanza puntos con V/I ≤ 12 Ω; a veces el máximo teórico de la curva queda fuera de alcance. La energía se mide contra el máximo **alcanzable** (rombo verde lleno; el teórico, cuando difiere, se dibuja con rombo vacío).
- **¿Qué significa «cola»?** El peor caso. Un método puede ganar energía en promedio y fallar gravemente en algunas sombras (se queda en un máximo local). El umbral del proyecto: pérdida media ≤ 0.5 pp y p99 ≤ 3 pp (1 000 curvas estáticas).
- **¿Los resultados coinciden con los reportes del proyecto?** Sí: los 9 métodos reproducen al decimal las campañas V13, V15, V16 y V17 (comprobado al construir esta versión).

## 5. Reservas
Todo es simulación; el MSAPSO es una reproducción propia a partir de la Fig. 6 del manuscrito base (versión borrador), no la implementación del autor; las implementaciones de DGBCO y CEDGO incluyen interpretaciones propias de partes que los artículos no precisan; no se corrigió por comparaciones múltiples. Detalles en el artículo del proyecto.

*Licencia: [[por definir por el equipo]]*
