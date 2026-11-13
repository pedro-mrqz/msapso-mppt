# Cómo funciona

## Flujo de datos
```
metodos.py ──(buscar)──► entorno.run_ops ──► campana.py ──► resultados/dyn.json, est.json   (cifras)
     │                         │
     │                         └──► grabar.py ──► resultados/traces.json   (corridas ventana por ventana)
     └─ fichas.py, catalogo.json ─┐                                   │
                                   └──► construir_html.py ◄───────────┘ ──► simulador.html
```
El navegador no ejecuta ningún algoritmo: reproduce `traces.json`. Así lo que se ve es exactamente lo que producen los métodos en Python.

## El simulador físico (`pvsim/`)
- `array_model.py`: modelo de un diodo del arreglo (4 subcadenas) y generador de sombras sintéticas (`random_shading_mix`, `SyntheticPVCurve`).
- `pvcurve.py`: curvas de los 4 casos reales (`datasets/`) y el **máximo alcanzable** (`P_ceiling`): puntos con V/I ≤ 12 Ω.
- `converter.py`: convertidor Boost (L = 10 mH, carga 12 Ω) con control Super-Twisting, compilado con numba.
- `static_plant.py`: `StaticPlant` (potencia estática P(I), sin inercia; para colas) y `DynamicPlantLogged` (dinámica completa; para energía). Ambas tienen la misma interfaz `run(duración, I)` = **una medición**.

## El lazo de operación (`entorno.run_ops`)
1. El método busca (`buscar(planta, curva, rng)`): cada `planta.run(1.0, I)` es una ventana de tiempo `t_wait`.
2. Se toma la corriente de **mayor potencia medida** y se fija multiplicada por `(1 − b)` (retroceso).
3. Se deja asentar y se vigila: si la potencia cambia **5 W o más**, se vuelve al paso 1.
La **energía** de un escenario es la energía realmente entregada dividida entre la del máximo alcanzable operando siempre en él (en %).

## Escenarios (`entorno.make_scenario(idx)`)
Semilla `100000 + idx`. Cada uno elige panel (5), tiempo de espera (5, 2, 1, 0.5 ms), régimen de cambio de sombra (único, moderado, alto, muy alto, parpadeo, estable) y ruido (0, 1, 2 W). Índices 0–599 = prueba, 600–1199 = selección de parámetros, 1200–2399 = confirmación.

## Formato de `resultados/traces.json`
```
{ "scen": [ {id, name, text, total, bounds, seq, curves:[{Isc,Pmax,Ic,Pg,Ig,P[240]}], meta} ... ],
  "runs": { "<escenario>|<t_wait>|<ruido>|<método>": {"e": energía %, "d": <base64 de zlib> } },
  "waits": [...], "noises": [...] }
```
`d` descomprimido son 4 bloques de `total` valores: `Ipv·4000` (uint16), `P·50` (uint16), `E/t_wait·100` (uint16) y la fase (uint8: 0 buscando, 1 fijo, 2 ventana que dispara reinicio).
