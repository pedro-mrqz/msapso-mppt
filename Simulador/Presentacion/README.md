# Simulador de presentación — Métodos MPPT con sombras parciales

Versión simplificada del simulador comparativo para presentar: los **8 métodos** de la revisión del profesor (MSAPSO del paper, V7, CEM puro, MLP + CEM, MLP + CEM con pares, CEDGO, DecentCEM y DecentCEM en zona alcanzable) sobre los **4 casos del manuscrito base**, cada uno con sombra fija durante 600 mediciones. Solo se elige el tipo de sombra (caso), la espera por medición y el ruido; los colores por población y la corriente pedida están siempre activos.

| Archivo | Contenido |
|---|---|
| `simulador_metodos_mppt.html` | Esperas de 0.5, 1, 2 y 5 ms (las de las campañas). |
| `simulador_metodos_mppt_tiempos.html` | Esperas de 0.5, 1, 2, 4, 5, 6, 8, 10, 12, 14, 16, 18 y 20 ms. |
| `construir_presentacion.py` | Toma el `simulador.html` generado con los 4 casos y produce la versión de presentación. |
| `catalogo_casos.json` | Catálogo con los 4 casos del manuscrito (ids `caso1` … `caso4`). |

Ambos HTML se abren con doble clic y no necesitan internet. Las cifras de la pestaña «Resultados» son las de las campañas (miles de escenarios aleatorios), no las de estos cuatro casos.

## Cómo regenerarlos

En una copia de `Simulador/Simulador_Comparativo_MPPT` (para no tocar las trazas del simulador completo):

1. Reemplazar `catalogo.json` por `catalogo_casos.json` (renombrado a `catalogo.json`) y borrar `resultados/traces.json`.
2. Para la versión de 13 tiempos, cambiar en `grabar.py` la línea `WAITS = [...]` por
   `WAITS = [5e-4, 1e-3, 2e-3, 4e-3, 5e-3, 6e-3, 8e-3, 10e-3, 12e-3, 14e-3, 16e-3, 18e-3, 20e-3]`.
3. `python grabar.py --solo msapso,v7,cem,mlp,mlp_pares,cedgo,decent,decent_alc`
4. `python construir_html.py`
5. `python ../Presentacion/construir_presentacion.py simulador.html simulador_metodos_mppt.html artefacto.html`
