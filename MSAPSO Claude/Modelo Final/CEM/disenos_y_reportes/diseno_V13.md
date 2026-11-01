# V13 — ¿La ventaja del MLP en dinámico es un efecto de margen (retroceso de corriente)?

Origen: la V12 mostró que MSAPSO corto + CEM iguala/supera al MLP + CEM en estático, pero MLP + CEM entrega +1.05 pp [+0.37, +1.75] más energía en dinámico (exactitud final 93.2 % contra ≈ 88 %).
**Hipótesis (formulada antes de correr):** el MLP, entrenado por regresión, promedia y elige corrientes algo MENORES que el máximo, del lado seguro del «precipicio» de la curva P-I; ese margen ayuda en dinámico (la V6.1 ya había visto que retroceder la corriente elegida ayuda). Si es cierto, un **retroceso fijo** aplicado a los otros métodos reproduce la ventaja sin MLP.

## Qué se mide
1. **Diagnóstico estático (sin elegir nada):** desplazamiento firmado de la corriente final respecto al máximo global, (I_sel − I_gmpp) / Isc, en 1000 curvas frescas (7777/7778), para MSAPSO completo, V7, MLP + CEM y MSAPSO corto + CEM (≤ 40 med.). Si el MLP elige más a la izquierda del pico que los demás, apoya la hipótesis.
2. **Retroceso en dinámico:** la corriente a la que se fija el convertidor tras la búsqueda se multiplica por (1 − b). Rejilla b ∈ {0, 0.02, 0.04, 0.06, 0.08}. **b se elige POR MÉTODO en escenarios de validación distintos (índices 600–1199 de la campaña V7)** por mayor energía media; la prueba usa los índices 0–599 (los de V11/V12) con b congelado. Métodos: MSAPSO completo, V7, MLP + CEM (V11), MSAPSO corto + CEM (≤ 40 med. y principal, V12). Reglas, entorno y reinicios de 5 W idénticos a la V7 (con b = 0 el entorno reproduce exacto la V7).

## Criterios de lectura (fijados antes de correr)
- **Hipótesis apoyada** si, en la prueba, MSAPSO corto + CEM con su b elegido iguala o supera a MLP + CEM **sin retroceso** (IC95 % pareado de la diferencia que incluye 0 o es positivo), y/o si MLP + CEM mejora poco con retroceso (ya tendría el margen incorporado).
- **Hipótesis no apoyada** si MSAPSO corto + CEM con retroceso sigue por debajo de MLP + CEM con IC95 % < 0: el MLP aportaría algo más.
- Se reportan cola de riesgo (p1, peor, % que pierde > 3 pp) y exactitud al final.
