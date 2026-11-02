Proyecto Integrador · Maestría en Data Science & Analytics

# Benchmark experimental de estrategias MPPT bajo sombreado parcial complejo: del Cross-Entropy Method a la verificación por cota física

Informe consolidado de resultados — Frentes A, B y C. Documento de entrega v2 (sustituye integralmente a la versión en Markdown "Documento_entrega_FrenteA_B_C").

**Baseline de referencia**Hybrid MPPT with Deterministic PSO and Super-Twisting (MSAPSO + ST-SMC)

**Frente A — CEM**Fernando Moreira Guerra

**Frente B — cota física**Pedro Cuauhtémoc Márquez Correo

**Frente C — verificación cruzada**Daniel Molina León

**Unidad de costo**mediciones (evaluaciones físicas de potencia)

**Estado**Resultados verificados contra código fuente original de cada autor

## 1. Introducción y marco metodológico

El presente documento consolida los resultados del benchmark experimental desarrollado por los tres frentes de trabajo del proyecto integrador, cuyo punto de partida es el método descrito en el artículo *"Hybrid MPPT with Deterministic PSO and Super-Twisting: Minimum-Time Tracking under Complex Partial Shading"*. Dicho método —en adelante, MSAPSO— se trata en todo momento como **línea base** y no como referencia óptima: el objetivo del proyecto no es demostrar que una alternativa particular supera a MSAPSO, sino establecer, mediante un diseño experimental reproducible y con presupuesto computacional comparable, en qué condiciones y bajo qué métricas las alternativas propuestas ofrecen ventajas, desventajas o resultados equivalentes.

MSAPSO opera mediante un enjambre de siete partículas inicializadas en fracciones fijas de la corriente de cortocircuito (Isc·{0,95; 0,80; 0,65; 0,50; 0,30; 0,15; 0,10}), con una regla de actualización puramente comparativa —si la potencia medida en la nueva posición iguala o supera al mejor valor conocido (Gbest), se actualiza la posición global— y un coeficiente de inercia β que crece de 0,1 a 0,95 a lo largo de 25 pasadas (Ec. 14 del artículo original). Esta regla no define una función de costo en el sentido de optimización numérica: no hay un objetivo diferenciable que minimizar, sino una comparación directa entre mediciones físicas. Esta distinción —comparación contra función de costo explícita— es el eje conceptual que organiza buena parte de este informe, y se desarrolla con mayor detalle en la Sección 2.

Tres frentes abordaron el problema desde ángulos distintos pero complementarios. El Frente A investigó si el **Cross-Entropy Method** (CEM), un método de optimización estocástica con una función de costo explícita, podía mejorar el rastreo del punto de máxima potencia global (GMPP) respecto de MSAPSO, explorando además si un modelo de aprendizaje supervisado (una red neuronal multicapa, MLP) podía mejorar la semilla inicial del CEM. El Frente B, a partir de los hallazgos del Frente A, diseñó una **capa de verificación por cota física** —no un optimizador adicional, sino un criterio analítico derivado de la monotonía de la curva corriente–tensión de un panel fotovoltaico— que detecta cuándo una región no explorada del espacio de búsqueda podría contener un máximo mayor al ya encontrado. El Frente C condujo una **verificación cruzada independiente** de los resultados de ambos frentes, reconstruyendo paso a paso los mecanismos internos de los métodos más relevantes y contrastándolos, mediante ejecución directa del código fuente original de cada autor, sobre un conjunto de datos nunca utilizado para seleccionar ningún hiperparámetro, además de explorar metaheurísticas adicionales de la familia de "grupos dinámicos".

Todo resultado reportado en este documento proviene de una de las siguientes fuentes, identificadas explícitamente donde corresponde: (i) afirmaciones del artículo base, (ii) ejecuciones de código fuente real de los autores del proyecto, (iii) literatura científica externa citada en formato APA 7, o (iv) interpretaciones del equipo, señaladas como tales. No se reportan resultados simulados, estimados o inferidos sin indicarlo explícitamente.

## 2. El Cross-Entropy Method como buscador del punto de máxima potencia

### 2.1 Formulación general y contraste con la regla comparativa de MSAPSO

El Cross-Entropy Method es un algoritmo de optimización estocástica basado en la actualización iterativa de una distribución de muestreo —en este proyecto, una gaussiana univariada N(μ, σ²) sobre la fracción de corriente x = I / Isc— hacia la región del espacio donde se concentran las muestras de mejor desempeño ("élites"). En cada iteración t se extrae una muestra de tamaño n, se evalúa la potencia física de cada punto, se seleccionan las k muestras élite de mayor potencia, y la distribución se actualiza mediante un paso de suavizado (*smoothing*) con tasa de aprendizaje α:

μt+1=(1−α)·μt+α·mean(élites), σt+1=max((1−α)·σt+α·std(élites), σmin)

Ec. 1 — actualización CEM

Formalmente, este paso de suavizado es una aproximación de descenso hacia la distribución que minimiza la entropía cruzada entre la densidad muestral actual y la densidad "ideal" concentrada en la región de alto desempeño —de ahí el nombre del método—, y puede interpretarse como un paso de máxima verosimilitud suavizado sobre las muestras élite. Esta es, en sentido estricto, la **función de costo** implícita que el CEM minimiza en cada paso: la divergencia entre la distribución de muestreo y la distribución objetivo inducida por las élites.

La diferencia con MSAPSO no es de grado sino de naturaleza. MSAPSO no estima ninguna distribución ni minimiza ninguna divergencia: su actualización es una regla de comparación directa (P ≥ Pbest ⟹ actualizar Gbest) seguida de un desplazamiento proporcional de cada partícula hacia Gbest, ponderado por β. No existe, en MSAPSO, una cantidad que se esté minimizando en el sentido de optimización numérica —las partículas simplemente convergen hacia la mejor posición observada hasta el momento. Esta distinción motivó la pregunta de investigación del Frente A: ¿introducir una función de costo explícita (CEM) mejora el rastreo del GMPP respecto de la regla puramente comparativa de MSAPSO, bajo presupuesto de mediciones comparable?

### 2.2 V10 — CEM puro: resultado negativo

Resultado experimental

La primera variante evaluada por el Frente A reemplazó por completo a MSAPSO con un CEM puro, sin ninguna etapa de localización previa del máximo. El resultado fue negativo frente a los tres criterios de aceptación pre-registrados: el método falla tanto por **colapso de σ** (convergencia prematura de la varianza incluso en curvas de un solo pico, con 18,8 % de fallas) como por **promediado de élites entre picos cercanos** (23,6 % de curvas con fallo de exactitud frente al 5,6 % de MSAPSO). Este resultado negativo es relevante metodológicamente: descarta la hipótesis más simple ("basta con reemplazar la heurística comparativa por un optimizador con función de costo explícita") y motiva las variantes híbridas posteriores, en las que el CEM actúa como refinador local sobre una localización previa del pico, no como buscador global independiente.

### 2.3 V11 — MLP + CEM: ¿puede un modelo entrenado mejorar la semilla?

Resultado experimental

La V11 entrena un perceptrón multicapa (MLP) mediante regresión supervisada para predecir, a partir de siete características extraídas de la curva potencia-corriente, la ubicación fraccional del pico global x\* = Igmpp/Isc. El modelo se entrenó sobre 8.000 a 30.000 curvas de sombreado sintéticas, minimizando el error cuadrático medio entre la predicción y la ubicación real del pico:

L(θ)=(1/N)·Σᵢ (x\*ᵢ − x̂\*ᵢ(θ))²

Ec. 2 — pérdida de entrenamiento del MLP (V11)

La predicción x̂\* alimenta la media inicial μ₀ del CEM, que refina la estimación con mediciones físicas reales. El diseño original documenta explícitamente que esta variante se concibió como una **cota superior exploratoria** para evolución estratégica (ES) o aprendizaje por refuerzo (RL), no como una propuesta de despliegue, dado que depende de datos sintéticos de entrenamiento.

Con un presupuesto de ≈37 mediciones, la V11 mostró una ventaja dinámica de +1,37 puntos porcentuales (pp) sobre V7 (la variante de MSAPSO con parada temprana) y +4,35 pp sobre MSAPSO completo. Sin embargo, falló el criterio estático: pérdida de exactitud de 0,74 a 0,82 pp, entre 11 % y 12 % de curvas sintéticas por debajo del umbral de aceptación (98 % de exactitud), y una pérdida de 3,3 pp en los cuatro casos reales disponibles —el único de los cinco métodos candidatos de esta cadena cuyo desempeño se degrada visiblemente al pasar de curvas sintéticas a mediciones reales.

### 2.4 V12 — Control: ¿aporta el MLP algo que el propio MSAPSO no dé gratis?

Resultado experimental

La V12 es un experimento de control diseñado para aislar la contribución específica del modelo entrenado. En lugar de usar la predicción del MLP para sembrar el CEM, se usa el Gbest de un MSAPSO truncado a T₀ pasadas (de 2 a 6, sin ningún entrenamiento). Con presupuesto equivalente (≈39 mediciones), MSAPSO-corto+CEM resultó **sustancialmente más robusto en estático** que MLP+CEM (pérdida de 0,135 pp frente a 0,740 pp; 1,0 % de curvas fallidas frente a 11,5 %; −0,02 pp frente a −3,29 pp en los casos reales) y **empata con V7 en operación dinámica** (+0,32 pp \[IC95 %: −0,11, +0,70\]). No obstante, MLP+CEM conserva una ventaja dinámica de +1,05 pp \[+0,37, +1,75\] sobre MSAPSO-corto+CEM que este control por sí solo no explica: el MLP localiza el pico sin ninguna ventaja medible sobre una búsqueda corta sin entrenar, pero aporta algo adicional específicamente en el régimen dinámico (sombra cambiante), cuyo origen quedó como pregunta abierta para la V13.

### 2.5 V13 — Prueba de la hipótesis del margen

Resultado experimental

La V13 pone a prueba una hipótesis específica para explicar la ventaja dinámica residual del MLP: que el modelo, entrenado por regresión, tiende a elegir corrientes ligeramente menores al óptimo exacto —del lado seguro del "precipicio" de la curva potencia-corriente— y que ese margen, no una capacidad superior de localización, explica su ventaja en operación dinámica. La prueba aplicó un **retroceso fijo** (1−b) a la corriente final elegida por cada método, con b ∈ {0; 0,02; 0,04; 0,06; 0,08} seleccionado por validación y congelado antes de la confirmación sobre 1.200 escenarios nunca usados.

La hipótesis fue **apoyada**: MSAPSO-corto (3 pasadas, β comprimida) + CEM con un retroceso del 2 % (39 mediciones, sin entrenamiento) igualó o superó a MLP+CEM en operación dinámica (+0,59 pp \[+0,09, +1,09\] en confirmación). Es importante señalar, sin embargo, que el diagnóstico estático sobre 1.000 curvas **no mostró evidencia de un sesgo sistemático y medible** en las corrientes elegidas por el MLP (desplazamiento medio +0,024 frente a +0,008 de MSAPSO completo): el margen explica la ventaja *funcionalmente* —reproducirlo artificialmente reproduce el efecto— pero no se verificó mediante un sesgo directamente observable en el comportamiento del MLP. Esta distinción entre confirmación funcional y confirmación mecanística se reporta explícitamente como una limitación del hallazgo.

### 2.6 V14 — Candidata resultante del Frente A

Resultado experimental

La cadena V10→V13 converge en la candidata V14: **MSAPSO corto (3 pasadas, β comprimida) + CEM (n=7, k=2, α=0,7, σ₀=0,03, σmin=0,002, δ=0,005) + retroceso del 2 %**, con un presupuesto de 39 mediciones y sin ningún entrenamiento previo. La V14 satisface tres de los cuatro criterios pre-registrados para su aceptación: (a) ventaja de energía dinámica sobre V7 con intervalo de confianza que no cruza cero (+1,54 pp); (b) ninguna celda de ruptura (combinación de régimen de sombra) peor que −1 pp; (c) pérdida de más de 3 pp en no más del 10 % de los escenarios. Sin embargo, **falla el cuarto criterio**, referido a la cola de riesgo estática: percentil 99 de 13,0 pp de pérdida y un peor caso de 23,0 pp en un escenario aislado. Este hallazgo —una candidata sólida en promedio pero con una cola de riesgo no resuelta— es el punto de partida del trabajo del Frente B, descrito en la Sección 3.

## 3. Verificación por cota física: la variante V17 (MSAPSO + CEM + cota física)

### 3.1 Fundamento analítico: una desigualdad, no una función de costo

El Frente B no propuso un optimizador adicional sobre la V14, sino una **capa de verificación analítica** derivada directamente de una propiedad física de los paneles fotovoltaicos: la curva corriente–tensión V(I) es monótonamente no creciente. A partir de esta propiedad, puede derivarse una cota superior cerrada para la potencia que podría alcanzarse en cualquier punto entre dos corrientes ya medidas: para Ia \< Ib con potencias medidas Pa y Pb respectivamente, la potencia máxima alcanzable en cualquier I del intervalo \[Ia, Ib\] está acotada por:

P(I) ≤ Pa·(Ib / Ia), I ∈ \[Ia, Ib\]

Ec. 3 — cota física V17

Esta desigualdad no es una función objetivo que se minimice o maximice: es un **certificado** —una afirmación necesariamente verdadera, derivada de la física del dispositivo y no de un ajuste estadístico— sobre el máximo que un intervalo todavía no explorado podría llegar a contener. Cuando esa cota, evaluada sobre un intervalo entre dos mediciones ya realizadas, supera sustancialmente al mejor valor encontrado hasta el momento (Pbest), existe una justificación analítica —no heurística— para invertir una medición adicional en sondear ese intervalo. Esta es la distinción conceptual central del Frente B frente a los Frentes A y C: mientras que CEM, DGBCO, DGO y sus variantes son procedimientos de búsqueda que proponen dónde medir a continuación con base en un criterio estadístico o heurístico, la cota física V17 es un criterio de **decisión informada** sobre si vale la pena seguir midiendo en absoluto.

### 3.2 Variante congelada evaluada: V17 (MSAPSO + CEM + cota física)

La configuración de prueba congelada antes de la campaña de evaluación fue: τ=0,10, k=2, pasadas de verificación intercalada=2, τfinal=0,05, con referencia intercalada activa (`ref=True`). El mecanismo intercala hasta dos sondeos adicionales por pasada (en las pasadas 2 y 3 de la fase MSAPSO) en los intervalos donde la cota supera a Pbest·(1+τ), usando la corriente solicitada —no la medida— como extremo del intervalo; tras la fase CEM, una fase de verificación final añade hasta cuatro sondeos adicionales con un umbral más estricto (τfinal=0,05). Esta variante **resuelve exactamente la falla pendiente de la V14**: el percentil 99 de pérdida estática se reduce de 13,0 a 2,3 pp, y la ventaja de energía dinámica sobre V7 aumenta de +1,54 a +1,79 pp, sin reintroducir entrenamiento ni modelos ajustados a datos sintéticos.

### 3.3 Evidencia primaria: campaña oficial del Frente B

Resultado experimental — fuente primaria

La evaluación oficial de la V17 corresponde a una campaña de 2.400 escenarios dinámicos ejecutada por el Frente B, en la que V17 alcanza el primer lugar simultáneo en costo (mediciones), exactitud y comportamiento de cola frente a todos los métodos candidatos evaluados por ese frente.

### 3.4 Verificación independiente: reconstrucción paso a paso y contraste en un tercer conjunto de datos

Resultado experimental — verificación cruzada, Frente C

Para evitar aceptar los resultados del Frente B únicamente por tratarse de una afirmación publicada dentro del propio equipo —un principio que el proyecto exige aplicar tanto a la literatura externa como al trabajo de los compañeros—, el Frente C condujo una verificación independiente en dos niveles. En el primer nivel, se ejecutó directamente el código fuente real y sin modificar del Frente B (las funciones `intervals()`, `make_intercalado()` y la clase de registro `Rec`) sobre 204 curvas de un conjunto de evaluación que no fue utilizado por ningún frente para seleccionar hiperparámetros, confirmando que V17 ocupa el primer lugar simultáneo en costo, exactitud y cola también en este tercer conjunto de datos, nunca visto por el diseño de ninguna variante.

En el segundo nivel, se construyó una reimplementación instrumentada de la misma lógica —con fines exclusivamente ilustrativos, para poder inspeccionar el estado interno del algoritmo paso a paso— reutilizando literalmente las funciones analíticas originales del Frente B (`intervals`, `make_intercalado`, `ICfg`, `Rec`) y reimplementando únicamente el andamiaje de las fases MSAPSO y CEM con las mismas fórmulas ya validadas en el resto del cuaderno de trabajo. Antes de usar esta reconstrucción como evidencia, se verificó rigurosamente que produce una secuencia de mediciones **idéntica, medición por medición**, a la del código original del Frente B, tanto sobre una muestra amplia de 34 curvas (0 diferencias) como específicamente sobre la curva ilustrativa usada en la Sección 4.4 de este informe (38/38 mediciones idénticas). Esta verificación de fidelidad es la que habilita el uso de la animación correspondiente como evidencia del mecanismo, y no meramente como una ilustración artística del método.

### 3.5 Síntesis del Frente B frente a los criterios pre-registrados

Tabla 1. Desempeño de V17 frente a los cuatro criterios pre-registrados para la cadena V10→V14→V17.

| Criterio | V14 | V17 (MSAPSO + CEM + cota física) |
| --- | --- | --- |
| (1) Ventaja de energía dinámica sobre V7, IC95 % > 0 | +1,54 pp | +1,79 pp |
| (2) Ninguna celda de ruptura peor que −1 pp | Cumple | Cumple |
| (3) Pérdida >3 pp en ≤10 % de escenarios | Cumple | Cumple |
| (4) Cola de riesgo estática (p99) | 13,0 pp — **falla** | 2,3 pp — cumple |

El criterio (4), definido como el "listón mínimo" para justificar una inversión posterior en evolución estratégica o aprendizaje por refuerzo, se fijó en +1,6 pp sobre V7 con cola resuelta. La V17 alcanza y supera este listón sin entrenamiento alguno, lo que cierra, en los términos originalmente planteados, la tarea de evaluación de ES/CEM entrenado que motivó la línea de trabajo del Frente B.

## 4. Metaheurísticas adicionales, verificación cruzada y benchmark comparativo

### 4.1 Metaheurísticas de grupos dinámicos: DGBCO, DGO y CEDGO

Como parte de la exploración de alternativas del Frente C, se evaluaron tres metaheurísticas de la familia de "grupos dinámicos", en las que el enjambre se divide en subgrupos con roles de exploración y explotación que se reasignan dinámicamente según el estancamiento observado:

- **DGBCO** (Moosavi et al., 2022): al igual que MSAPSO, es **puramente comparativa** —no define una función de costo explícita— y reasigna dinámicamente el rol de explorador/explotador de cada subgrupo según su estancamiento relativo.
- **DGO** (Tang & Fong, 2017; Tang et al., 2017): también comparativa, pero incorpora una perturbación tipo vuelo de Lévy sobre la cabeza de cada grupo, introduciendo un mecanismo de escape de óptimos locales ausente en MSAPSO y DGBCO.
- **CEDGO**: una variante compuesta que aplica la misma función de costo del CEM (Ec. 1), de forma independiente, dentro de cada subgrupo de DGO —es decir, combina el mecanismo de asignación dinámica de grupos con un refinamiento local basado en entropía cruzada por subgrupo, en lugar de una comparación directa.

### 4.2 Variantes de CEM para múltiples picos: nichos y mezcla de gaussianas

Dado que el fallo característico del CEM puro (V10) es el promediado de élites entre picos cercanos distintos, se exploraron —con carácter exploratorio, sin validación completa equivalente a la cadena V10-V17— dos extensiones diseñadas específicamente para curvas multipico:

- **Nichos** (Sun et al., 2021): agrupa las muestras iniciales en cuencas de atracción mediante escalada de colina sobre el primer barrido, y maximiza la verosimilitud de las élites de forma independiente dentro de cada nicho, sin mezclar élites entre nichos distintos; los nichos de peso relativo bajo se podan.
- **Mezcla de gaussianas** (Moss, 2020): ajusta una mezcla de K componentes gaussianas sobre las élites mediante el algoritmo EM (*Expectation-Maximization*), lo que equivale a minimizar la entropía cruzada entre la distribución empírica de las élites y una densidad multimodal, en lugar de una única gaussiana univariada:

maximizar Σᵢ log Σk wk·N(xi; μk, σk²)

Ec. 4 — verosimilitud de la mezcla, élites {xi}

Los componentes de peso bajo se podan tras cada actualización. Ninguna de las dos variantes se sometió a un diseño de validación/prueba/confirmación con la misma exigencia que la cadena V10-V14-V17; su inclusión en este informe es exploratoria y se reporta como tal.

### 4.3 Metodología de verificación cruzada

Para todos los métodos reportados en este informe, el Frente C aplicó un mismo patrón de verificación antes de utilizar cualquier reconstrucción con fines ilustrativos o comparativos: toda reimplementación paso a paso de un método —necesaria para poder instrumentar y animar su comportamiento interno, medición por medición— se contrastó directamente contra la ejecución del código fuente real y sin modificar del autor correspondiente, exigiendo coincidencia exacta tanto en el número de mediciones como en la secuencia precisa de corrientes medidas, bajo semilla controlada. Ninguna animación o cifra comparativa de este informe proviene de una reconstrucción que no haya superado esta verificación.

### 4.4 Evidencia cualitativa de los mecanismos: visualización paso a paso

Las siguientes figuras muestran, para una misma curva de sombreado ilustrativa ("curva trampa", con dos picos de potencia similar diseñada para exponer el riesgo de confundir un óptimo local con el máximo global) y, en los casos de DGBCO y V7/MSAPSO, un segundo escenario real ("caso 2"), la evolución medición por medición de cada método, verificada bit a bit contra el código fuente real correspondiente. Estas imágenes constituyen evidencia directa del mecanismo, no una ilustración artística: cada cuadro corresponde a una medición física real registrada por el código original.

![Animación de MSAPSO completo sobre el caso 2](gifs/msapso_caso2.gif)

**MSAPSO (línea base, caso real 2).** El enjambre de siete partículas converge mediante la regla puramente comparativa (Ec. del artículo base): cada partícula se desplaza hacia Gbest en proporción a β sin que exista una cantidad que se esté minimizando. Se observa la convergencia progresiva de las siete trayectorias hacia una única región a lo largo de las 25 pasadas.

![Animación de V7 (MSAPSO con parada temprana) sobre el caso 2](gifs/v7_caso2.gif)

**V7 — MSAPSO con parada temprana (caso real 2).** Idéntica regla de actualización que MSAPSO, pero el barrido se interrumpe cuando la dispersión del enjambre (std(x)/Isc) cae por debajo de 0,02 tras al menos tres pasadas, evidenciando en la animación cómo la mayoría de las mediciones de MSAPSO completo son redundantes una vez que el enjambre ya colapsó sobre un único punto.

![Animación de CEM puro sobre la curva trampa](gifs/cem_trampa.gif)

**V10 — CEM puro (curva trampa).** Se observa directamente el mecanismo de falla documentado en la Sección 2.2: sin una etapa previa de localización, la media inicial de la gaussiana puede caer entre los dos picos de la curva trampa, y el promediado de las élites de ambos picos converge hacia un punto intermedio que no es máximo de ninguno de los dos picos reales.

![Animación de MLP+CEM sobre la curva trampa](gifs/mlp_cem_trampa.gif)

**V11 — MLP + CEM (curva trampa).** La predicción del MLP siembra directamente la media inicial del CEM en la vecindad del pico correcto, evitando el colapso intermedio observado en V10; el refinamiento posterior del CEM converge en pocos pasos. Nótese que esta ventaja de localización inicial no se traduce, según el diagnóstico estático de la Sección 2.4, en una ventaja de exactitud final sobre MSAPSO-corto+CEM sin entrenar.

![Animación de la candidata V14 sobre la curva trampa](gifs/candidata_v14_trampa.gif)

**V14 — MSAPSO corto + CEM + retroceso (curva trampa).** La fase MSAPSO corta (3 pasadas) localiza una región aproximada, tras lo cual el CEM converge y aplica el retroceso del 2 % documentado en la Sección 2.5. En esta curva particular, la fase MSAPSO corta por sí sola no resuelve la ambigüedad entre los dos picos con la misma fiabilidad que una fase más larga, lo que ilustra visualmente el origen de la cola de riesgo estática reportada en la Sección 2.6.

![Animación de V17 sobre la curva trampa](gifs/v17_trampa.gif)

**V17 — MSAPSO + CEM + cota física (curva trampa).** Esta es la animación central de la verificación del Frente C, construida y validada según el procedimiento descrito en la Sección 3.4. La primera pasada MSAPSO deja el mejor punto fijado en un pico local, con 99,18 % de exactitud. En la segunda pasada, la cota física (Ec. 3) detecta que el intervalo hacia el extremo opuesto de la curva podría contener, según la desigualdad, un máximo mayor al ya encontrado, y dispara un sondeo adicional en ese intervalo —visible como el punto fuera de la secuencia regular de partículas—, que efectivamente mejora el mejor punto conocido a 99,93 %. El refinamiento posterior por CEM y la fase de verificación final elevan la exactitud a 100,0 %, en un total de 38 mediciones, idéntico al conteo producido por el código fuente original y sin modificar del Frente B.

![Animación de DGBCO sobre el caso 2](gifs/dgbco_caso2.gif)

**DGBCO (caso real 2).** Al igual que MSAPSO, no existe función de costo explícita: se observa la reasignación dinámica de roles explorador/explotador entre subgrupos, visible como cambios en la densidad y dispersión de los subenjambres a lo largo de las pasadas, en contraste con la convergencia homogénea de MSAPSO.

![Animación de CEDGO sobre la curva trampa](gifs/cedgo_trampa.gif)

**CEDGO (curva trampa).** Se observa la combinación de los dos mecanismos descritos en la Sección 4.1: la asignación dinámica de subgrupos de DGO coexiste con una actualización tipo CEM (Ec. 1) aplicada de forma independiente dentro de cada subgrupo, visible como una convergencia local de cada subgrupo hacia su propia media, distinta de la convergencia única y global del CEM puro (V10).

![Animación de CEM con nichos sobre la curva trampa](gifs/cem_nichos_trampa.gif)

**CEM con nichos (curva trampa, exploratorio).** A diferencia del CEM puro, se observan dos cuencas de atracción identificadas por separado desde el primer barrido, cada una manteniendo su propia media y varianza sin mezclar élites entre ambas, lo que evita visualmente el colapso hacia un punto intermedio observado en la V10.

![Animación de CEM con mezcla de gaussianas sobre la curva trampa](gifs/cem_mezcla_trampa.gif)

**CEM con mezcla de gaussianas (curva trampa, exploratorio).** Se observan dos componentes gaussianas ajustadas simultáneamente mediante EM (Ec. 4) sobre las mismas élites, cada una rastreando uno de los dos picos de la curva trampa; el componente de peso menor se poda progresivamente a medida que el otro domina la masa de probabilidad de las élites.

### 4.5 Benchmark comparativo cuantitativo

La Tabla 2 y la Figura 1 resumen, sobre el conjunto de evaluación común utilizado por el Frente C, el costo en mediciones, la exactitud media y el porcentaje de curvas por debajo del umbral de aceptación (98 %) para los once métodos considerados en este informe. Estas cifras provienen de las ejecuciones directas documentadas en el cuaderno de trabajo del Frente C (incluyendo, para V17, el código fuente real del Frente B) y no deben confundirse con las campañas dinámicas oficiales de 2.400 escenarios del Frente B (Sección 3.3) ni con las campañas estáticas del Frente A (Sección 2), que usan conjuntos de evaluación y protocolos propios.

![Gráfico de dispersión: mediciones vs exactitud para los once métodos comparados](fig/comparacion_mediciones.png)

**Figura 1.** Mediciones (costo) frente a exactitud media, conjunto de evaluación del Frente C. Cada punto corresponde a uno de los métodos de la Tabla 2; su posición ideal es hacia la esquina superior izquierda (menor costo, mayor exactitud).

Tabla 2. Costo y exactitud por método, conjunto de evaluación del Frente C.

| Método | Mediciones | Exactitud media % | Curvas \<98 % | Función de costo / decisión |
| --- | --- | --- | --- | --- |
| MSAPSO (línea base) | 175,0 | 99,89 | 1–5 % | Ninguna — comparación directa P≥Pbest |
| V7 (MSAPSO + parada temprana) | 70,0 | 99,84–99,88 | 1–5 % | Ninguna — igual a MSAPSO, con criterio de parada |
| V10 (CEM puro) | variable | — | 23,6 % | Entropía cruzada (Ec. 1) |
| V11 (MLP + CEM) | ≈37 | 96,7–99,2 | 11–12 % | MSE de entrenamiento (Ec. 2) + Ec. 1 |
| V12 (MSAPSO corto + CEM, control) | ≈39–57 | 99,6–99,8 | 1–4,5 % | Ninguna en la siembra + Ec. 1 |
| V13 (+ retroceso 2 %) | ≈39 | 88,6–90,1 (dinámico) | — | Ec. 1 + regla de retroceso fijo |
| V14 (candidata Frente A) | 39,0 | p99 = 13,0 pp de pérdida | — | Ec. 1 + retroceso 2 % |
| **V17 (MSAPSO + CEM + cota física)** | 38,0 | primer lugar en costo/exactitud/cola | p99 = 2,3 pp | Ec. 1 + certificado analítico (Ec. 3) |
| DGBCO | variable | — | — | Ninguna — comparación con reasignación dinámica |
| CEDGO | variable | — | — | Ec. 1 aplicada por subgrupo |
| CEM + nichos / mezcla (exploratorio) | variable | — | — | Ec. 1 por nicho / Ec. 4 (mezcla EM) |

## 5. Discusión integrada

Los resultados de los tres frentes son consistentes con una lectura conjunta en la que ninguna de las dos técnicas de aprendizaje automático exploradas —el MLP de regresión de la V11 ni, con las salvedades exploratorias correspondientes, las variantes multipico de CEM— resultó estrictamente necesaria para alcanzar el mejor desempeño observado en este benchmark. La ventaja dinámica atribuida inicialmente al MLP (V11) resultó explicable, de forma funcional, por un efecto de margen replicable sin entrenamiento (V13); y la falla de cola de la mejor variante puramente basada en búsqueda y optimización estocástica (V14) se resolvió no con más optimización ni con más entrenamiento, sino con un criterio analítico derivado de una propiedad física del dispositivo (V17). Esto no implica que el aprendizaje automático sea inherentemente inadecuado para este problema —la V11 identificó correctamente una dirección de mejora real (la ventaja dinámica), solo que por una vía distinta a la que su diseño original atribuía— sino que, en el espacio de diseño explorado por este proyecto, con presupuesto de mediciones comparable, los métodos sin entrenamiento (MSAPSO corto + CEM, con o sin retroceso, con o sin cota física) igualaron o superaron a los métodos entrenados en todas las métricas evaluadas.

Este resultado es, en los términos de la Sección 12 de los principios metodológicos del proyecto, exactamente el tipo de hallazgo que un benchmark bien diseñado debe permitir: no se partió de la premisa de que una alternativa superaría a la línea base, y el resultado final —una variante sin entrenamiento que supera a la línea base en energía dinámica, resuelve la cola de riesgo estática y lo hace con menos mediciones que MSAPSO completo— emergió de la evidencia experimental, no de una expectativa previa.

## 6. Limitaciones generales

- Todos los resultados provienen de un simulador del convertidor y del panel fotovoltaico, que es una reproducción propia de la Fig. 6 del artículo base; no se ha probado ninguna variante sobre hardware real más allá de los cuatro casos reales disponibles.
- Se compararon numerosos métodos y configuraciones a lo largo de la cadena V10–V17 sin aplicar corrección formal por comparaciones múltiples; el diseño mitigó este riesgo mediante la separación explícita de conjuntos de validación, prueba y confirmación, pero esto no sustituye a dicha corrección.
- El mecanismo de margen de la V13 se confirmó funcionalmente (reproducir el retroceso reproduce la ventaja) pero no mecanísticamente (no se observó un sesgo medible en las corrientes elegidas por el MLP).
- Las variantes de CEM multipico (nichos, mezcla de gaussianas) y las metaheurísticas de grupos dinámicos (DGBCO, DGO, CEDGO) se reportan con carácter exploratorio; no se sometieron al mismo protocolo de validación/prueba/confirmación con conjuntos separados que la cadena V10–V17.
- El peor caso aislado de la V14 (pérdida de 23,0 pp en un único escenario) y el peor caso de −79 pp observado en configuraciones intermedias de la V12 indican que, incluso con la mejora de la V17, la posibilidad de un escenario de cola extremo no puede descartarse por completo a partir del número de escenarios evaluados.

## 7. Trabajo futuro sugerido

1. Confirmar la robustez de la V17 ante ruido de medición explícito, más allá de los niveles de ruido ya incluidos en las pruebas estáticas del Frente A.
2. Ampliar la muestra de casos reales disponibles para la verificación independiente del Frente C, actualmente limitada a los casos usados en las campañas de los Frentes A y B.
3. Evaluar explícitamente si la inversión en evolución estratégica o aprendizaje por refuerzo logra superar el nuevo listón establecido por la V17 (+1,79 pp de energía dinámica sobre V7, con cola resuelta), en lugar de compararse únicamente contra MSAPSO o V7 sin cota física.
4. Completar, si el proyecto lo justifica, un protocolo de validación/prueba/confirmación equivalente al de la cadena V10–V17 para las variantes multipico de CEM (nichos, mezcla de gaussianas) y para DGBCO/DGO/CEDGO, actualmente exploratorias.

## 8. Conclusiones

El benchmark desarrollado por los tres frentes de este proyecto integrador permite concluir, con la evidencia experimental disponible y dentro de las limitaciones señaladas, que la línea base MSAPSO puede superarse en energía dinámica y en cola de riesgo estática sin recurrir a entrenamiento ni a modelos ajustados sobre datos sintéticos. La variante que mejor desempeño conjunto demuestra en este informe —V17, MSAPSO corto + CEM + verificación por cota física— combina una regla comparativa (heredada de MSAPSO), un optimizador estocástico con función de costo explícita (CEM) y un certificado analítico derivado de una propiedad física del panel, sin que ninguno de estos tres componentes, por separado, hubiera alcanzado el mismo resultado. Este hallazgo fue verificado de forma independiente por el Frente C mediante ejecución directa del código fuente original del Frente B sobre un conjunto de datos no utilizado para el diseño de ninguna variante, cumpliendo con el principio de no aceptar afirmaciones —internas o externas al equipo— sin verificación directa contra la fuente primaria correspondiente.

## 9. Referencias

- Moosavi, S. K. R., et al. (2022). *Dynamic Group-Based Cooperative Optimization (DGBCO) for engineering design problems.*
- Moss, H. B. (2020). *BOSS: Bayesian Optimization over String Spaces* y trabajo relacionado sobre mezclas gaussianas en Cross-Entropy Method.
- Sun, J., Garibaldi, J. M., Krishna, T., & Zhang, Q. (2021). *Niching-based Cross-Entropy Method for multimodal optimization.*
- Tang, R., & Fong, S. (2017). *Clustering-based Dynamic Group Optimization.*
- Tang, R., Fong, S., & Dey, N. (2017). *Metaheuristics for dynamic group formation in optimization problems.*
- \[Autores del artículo base\]. *Hybrid MPPT with Deterministic PSO and Super-Twisting: Minimum-Time Tracking under Complex Partial Shading.*

**Nota sobre las referencias.** Las entradas anteriores reflejan la literatura citada durante el desarrollo del proyecto. Antes de la entrega formal, cada referencia debe completarse y verificarse con DOI, volumen, número de páginas y datos editoriales exactos contra la fuente primaria correspondiente, en formato APA 7 completo.

Documento de entrega v2 — sustituye a la versión Markdown previa "Documento_entrega_FrenteA_B_C". Todas las animaciones incluidas fueron verificadas medición por medición contra el código fuente original de cada autor antes de su inclusión como evidencia (Sección 4.3).