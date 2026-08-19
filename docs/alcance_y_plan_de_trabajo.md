# Proyecto: Capacidad hospitalaria durante una epidemia
### Documento de alcance, tareas y organización de equipo

---

## 1. Definición del caso

### 1.1 Idea central
Simulación por agentes (Pygame) de una epidemia donde, además de los estados clásicos vistos en clase (susceptible, infectado, recuperado/fallecido), se agrega un estado **grave** que requiere hospitalización. El hospital tiene **camas limitadas**. La decisión que se estudia es qué pasa cuando la demanda de camas supera la oferta.

### 1.2 Pregunta de decisión
**¿Cómo afecta la capacidad hospitalaria (número de camas) a la mortalidad, la saturación del sistema y la cantidad de pacientes sin atención durante una epidemia?**

Se responde ejecutando la simulación con distintos números de camas (por ejemplo 5 / 10 / 20) y comparando los resultados con evidencia cuantitativa (Excel).

### 1.3 Diagrama de estados
```
Susceptible → Infectado (leve) → ¿desarrolla gravedad?
                                    │
                          ┌─────────┴─────────┐
                          no                  sí
                          │                    │
                     Recuperado            GRAVE
                                              │
                                        ¿hay cama libre?
                                       ┌───────┴───────┐
                                       sí               no
                                       │                 │
                                 HOSPITALIZADO      EN ESPERA
                                (menor mortalidad) (mayor mortalidad)
                                       │                 │
                                       └───────┬─────────┘
                                    Recuperado / Fallecido
                          (al liberarse una cama, se reasigna
                           al primero en espera, orden de llegada)
```

### 1.4 Qué SÍ se hará (alcance completo del proyecto)
- Simulación de propagación basada en agentes, tomando como referencia la estructura orientada a objetos utilizada en los videos de epidemias vistos en clase. Cada persona se representa mediante una clase `Person`, mientras que una clase `Simulation` coordina la evolución general del sistema y una clase `Hospital` administra la capacidad hospitalaria y la lista de espera. No es una reutilización literal del código de clase, sino de la misma idea de organización (agentes como sprites + un coordinador central).
- Estados: susceptible → infectado (leve, durante un número de ciclos definido) → al vencer ese tiempo, **recuperado o grave** → si es grave: hospitalizado o en espera → al vencer el tiempo de gravedad, recuperado o fallecido. La decisión de gravedad/muerte se evalúa **una sola vez, en un evento definido** (cuando vence el temporizador correspondiente) — nunca en cada frame, para que las probabilidades configuradas tengan el efecto esperado.
- Hospital **abstracto**: un contador de camas, no una ubicación física a la que los agentes deban desplazarse.
- Lista de espera (`waiting_list`, FIFO real con `collections.deque`) con asignación por **orden de llegada** cuando se libera una cama — es la única regla de asignación del proyecto.
- **Regla de reducción de camas:** aumentar la capacidad siempre se permite; reducirla solo se permite si la nueva capacidad sigue siendo ≥ a la cantidad de camas ya ocupadas (para no dejar pacientes "hospitalizados" de forma inconsistente).
- Parámetros configurables **antes de iniciar**: población, infectados iniciales, % de casos graves, mortalidad con/sin cama, duración de infección, duración de hospitalización, número inicial de camas.
- Parámetros/controles ajustables **durante la simulación**: subir/bajar camas, pausar/reanudar, velocidad de la simulación.
- Visualización en tiempo real: agentes moviéndose coloreados por estado + panel con contadores (susceptibles, infectados, graves, hospitalizados, en espera, recuperados, muertos, ocupación de camas) y aviso visible cuando el sistema está saturado.
- Exportación a Excel al finalizar: hoja de evolución temporal (`timeline`) + hoja `resumen` con una fila por escenario ejecutado (camas usadas, pico de ocupación, muertos, pacientes sin cama, tiempo saturado).
- Comparar al menos 3 escenarios variando solo el número de camas (ej. 5 / 10 / 20) para responder la pregunta de decisión con evidencia del Excel, siguiendo la metodología de la sección 1.7.

### 1.5 Qué NO se hará (fuera de alcance)
- Distintas estrategias de asignación de camas (prioridad a vulnerables, mayor probabilidad de recuperación, etc.) — el proyecto usa únicamente orden de llegada.
- Hospital como ubicación física con desplazamiento, rutas o colisiones de entrada.
- Datos médicos reales, tasas clínicas reales de COVID-19 u otra enfermedad específica.
- Diagnósticos médicos, tipos de tratamiento, medicamentos.
- Otros recursos hospitalarios (médicos, enfermeros, ventiladores) o traslados entre hospitales.
- Costos económicos del sistema de salud.
- Calibración con datos reales o predicción de casos reales.
- Aprendizaje automático / Reinforcement Learning para elegir parámetros automáticamente.
- Dashboard visual elaborado — un panel de texto simple con los contadores es suficiente.

### 1.6 Aclaración para la presentación
Las probabilidades de gravedad, recuperación y mortalidad son **parámetros configurables del modelo**, no cifras clínicas reales. El objetivo es estudiar el efecto de la capacidad hospitalaria como recurso limitado, no representar cifras médicas reales.

### 1.7 Metodología para que la comparación de escenarios sea válida
Como la simulación es probabilística, correr 5 / 10 / 20 camas una sola vez cada una puede dar resultados engañosos (dos corridas con la misma capacidad pueden diferir bastante solo por azar). Para que la comparación tenga sentido:
- **Fijar una semilla aleatoria** (`np.random.seed(...)` + `random.seed(...)`) al inicio de cada corrida, la misma para los 3 escenarios — así la principal variable que cambia entre corridas es la capacidad, no la secuencia de eventos aleatorios.
- **No usar el control en vivo de +/- camas durante las corridas de comparación.** La capacidad debe quedar fija desde el inicio de cada corrida (5, 10 o 20) para poder decir "este escenario corresponde a 5 camas". El control `UP`/`DOWN` en vivo se usa únicamente como demostración del controlador en el video de 2 minutos, no en las corridas que alimentan el Excel de comparación.
- *(Opcional, no obligatorio para esta entrega)*: si sobra tiempo, correr varias repeticiones por escenario y promediar resultados — conecta directamente con la idea de muestreo/convergencia de Monte Carlo vista en el material de Pygame, pero no es necesario para responder la pregunta de decisión de forma razonable.

### 1.8 Contrato de la lógica ya implementada (para quien construya la parte visual)

Toda la lógica (`person.py`, `hospital.py`, `simulation.py`, `config.py`) está terminada y probada con tests (`python -m pytest tests/ -v`). Esta sección documenta exactamente qué hace, para que la parte visual (`draw()`, `handle_event()`, `run()`) se pueda construir sin tener que leer el código de lógica primero.

**Contagio por proximidad (nuevo respecto al diagrama de 1.3):** el diagrama de estados de la sección 1.3 no mostraba cómo un susceptible se contagia — ahora sí está implementado. En cada `update()`, cada persona `infected` puede contagiar a cada `susceptible` que esté a una distancia ≤ `infection_radius`, con probabilidad `transmission_probability`. El contagio se calcula **al final** de cada ciclo (después de mover a todos y de resolver los vencimientos de temporizador de ese ciclo), así que un contagio nuevo empieza a contar sus propios ciclos recién en el siguiente `update()`.

**Parámetros del constructor de `Simulation`** (los que no tienen valor por defecto son obligatorios):

| Parámetro | Significado | Rango válido |
|---|---|---|
| `population` | Cantidad total de personas a crear en `populate()` | entero ≥ 0 |
| `initial_infected` | Cuántas de esas personas arrancan infectadas | entero, `0 ≤ initial_infected ≤ population` |
| `transmission_probability` | Probabilidad de contagio al haber contacto | `0.0` – `1.0` (default `0.0` = contagio desactivado) |
| `infection_radius` | Distancia máxima para considerar "contacto" | número ≥ 0 (default `0.0`) |
| `pct_grave` | Probabilidad de que un infectado pase a grave al vencer `infection_duration` | `0.0` – `1.0` |
| `infection_duration` | Ciclos que dura el estado `infected` | entero > 0 |
| `grave_duration` | Ciclos que dura el estado `grave` | entero > 0 |
| `mortality_hospitalized` | Probabilidad de morir al vencer `grave_duration` estando hospitalizado | `0.0` – `1.0` |
| `mortality_waiting` | Probabilidad de morir al vencer `grave_duration` estando en espera | `0.0` – `1.0` |
| `initial_beds` | Capacidad inicial del hospital | entero ≥ 0 |
| `width`, `height` | Límites de la pantalla para posiciones y movimiento | default: `config.SCREEN_WIDTH`/`SCREEN_HEIGHT` (800×600) |
| `random_fn` | Función sin argumentos que devuelve un float en `[0, 1)` | default `random.random`; para reproducibilidad usar `random.Random(seed).random` |

Si un valor no cumple su rango, el constructor lanza `ValueError` con un mensaje indicando cuál parámetro falló — no hace falta validar nada por fuera antes de crear `Simulation`.

**Atributos y métodos que puede usar la parte visual:**

- `sim.people` — lista de `Person` (cada una con `.x`, `.y`, `.state`, `.hospitalized`) para dibujar.
- `sim.hospital.occupied` / `.capacity` / `.free_beds` / `.is_saturated` / `.waiting_list` — para el panel de contadores y el aviso de saturación.
- `sim.current_cycle` — entero, arranca en 0, sube de a 1 en cada `update()` efectivo (no sube si `sim.paused` es `True`).
- `sim.is_finished()` — `True` cuando ya no queda nadie `infected` ni `grave` (útil para saber cuándo cortar una corrida del Bloque D o mostrar "epidemia terminada" en pantalla).
- `sim.paused` — booleano, lo lee `update()` para no avanzar nada si es `True`. `handle_event()` solo necesita alternarlo con `SPACE`.
- `sim.speed` — está declarado pero **no tiene efecto todavía**; la forma pensada de usarlo es llamar a `sim.update()` esa cantidad de veces por frame (no escalar un delta-time), pero eso se implementa en `run()`.
- `sim.hospital.set_capacity(n)` — devuelve `True`/`False` según si el cambio se aplicó; si sube la capacidad, reasigna automáticamente a quien estaba esperando. Úsalo directamente para `UP`/`DOWN`, ignorando el `False` sin necesidad de manejar excepciones.
- `sim.populate()` — se llama una sola vez al arrancar (crea `sim.people` y registra el primer frame en `sim.history` con `cycle=0`).
- `sim.history` — lista de diccionarios, uno por frame, con las claves: `cycle, susceptible, infected, grave, recovered, dead, hospitalized, waiting, free_beds, capacity, saturated`. Es lo que después usará `exporter.py`.

**Lo que la parte visual NO necesita tocar:** cualquier método que empiece con `_` (`_infect`, `_infection_expire`, `_grave_expire`, `_recover`, `_record_history`, `_spread_contagion`, `_in_contagion_range`, `_validate_params`) es interno de `Simulation` y ya está resuelto.

---

## 2. Lista de tareas (según lo que pide el profesor)

El entregable exige: **código + video demo de 2 min + presentación de 2 min**, con simulación, controladores de parámetros, visualización en tiempo real y resultados en Excel. Desglosado en tareas concretas:

### A. Lógica de simulación
- [ ] Implementar `Person` con estado (`susceptible/infected/grave/recovered`) y temporizador reutilizable.
- [ ] Implementar transición infectado → recuperado / grave (según `pct_grave`).
- [ ] Implementar clase `Hospital` (camas, `waiting_list`, `admit`, `discharge`, asignación FIFO).
- [ ] Implementar transición grave → recuperado / fallecido (mortalidad según hospitalizado o no).
- [ ] Verificar que al liberarse una cama se reasigna automáticamente al primero en espera.

### B. Visualización y controles
- [ ] Panel de texto en pantalla con los 8 contadores + ocupación de camas.
- [ ] Aviso visual cuando `hospital.is_saturated`.
- [ ] Colores distintos por estado (azul/verde/naranja/rojo/morado).
- [ ] Controles en vivo: pausa (`SPACE`), subir/bajar camas (`UP`/`DOWN`), velocidad (`LEFT`/`RIGHT`).

### C. Datos y Excel
- [ ] Registrar historial por frame (`self.history`) — ya en el esqueleto.
- [ ] Exportar hoja `timeline_run_N` por cada corrida.
- [ ] Exportar hoja `resumen` con una fila por escenario (parámetros + resultados agregados).
- [ ] Correr y guardar al menos 3 escenarios (5 / 10 / 20 camas), con la **misma semilla aleatoria** y **capacidad fija** durante cada corrida (ver sección 1.7), para tener evidencia comparativa válida.

### D. Análisis
- [ ] Con los resultados del Excel, redactar la respuesta a la pregunta de decisión (¿cómo cambia mortalidad/saturación con la capacidad?).

### E. Entregables finales
- [ ] Grabar video demo de 2 min (mostrar la simulación corriendo, cambiar camas en vivo, mostrar saturación, mostrar el Excel generado).
- [ ] Preparar presentación de 2 min (planteamiento del caso, decisión estudiada, resultado principal, 1-2 gráficas del Excel).
- [ ] Revisar que el código corra limpio desde cero (sin dependencias rotas) antes de entregar.
- [ ] Empaquetar entrega: código + video + presentación + README con instrucciones para correrlo.

---

## 3. Repartición del trabajo entre 2 personas

La clave para no bloquearse es dividir por **módulos con una interfaz clara entre ellos**, para que cada quien pueda avanzar sin esperar a que el otro termine. El esqueleto ya está pensado así: la lógica (`Person`, `Hospital`, `Simulation` — transiciones de estado) es independiente de la presentación (dibujo en pantalla, texto, teclas, Excel).

**Importante:** el `draw()` (dibujo) se deja como un método dentro de `Simulation`, no en un archivo/clase de visualización aparte — Pygame mezcla naturalmente `update`/`draw`/eventos, y separarlo demasiado pronto genera más trabajo de integración del que ahorra. Por eso la división no es "archivo A vs. archivo B" sino "métodos de lógica vs. métodos de presentación dentro de las mismas clases", más los archivos que sí son 100% independientes (`hospital.py`, `exporter.py`).

### Persona A — Lógica y experimentos
- `person.py` y `hospital.py` completos (estados, temporizadores, capacidad, lista de espera).
- Dentro de `simulation.py`: los métodos de lógica (`_infect`, `_infection_expire`, `_grave_expire`, `_recover`, `_record_history`, el bucle principal sin la parte de dibujo).
- Bloque D (correr los escenarios con semilla fija y analizar resultados).

### Persona B — Visualización, controles y salida de datos
- Dentro de `simulation.py`: el método `draw()` (panel de texto, colores, aviso de saturación) y el manejo de teclado (`pausa`, `UP/DOWN` con el guard de camas, `LEFT/RIGHT`) — son métodos separados del resto, así que se puede trabajar sin tocar las líneas de Persona A.
- `exporter.py` completo (exportación a Excel con pandas, usando `self.history` que ya expone Persona A).
- Apoya en la grabación del video demo (tiene más contacto con la parte visual).

### Trabajo conjunto (no se puede dividir)
- Bloque E (video y presentación) — ambos deben entender el proyecto completo para exponerlo bien.
- Definir juntos, **antes de separarse a programar**, el "contrato" de nombres: qué atributos expone `Simulation`/`Hospital` (`self.history`, `self.hospital.free_beds`, `self.hospital.occupied`, `self.hospital.waiting_list`, `person.state`, `person.hospitalized`) — si cambian un nombre después, avisar al otro antes de tocarlo, porque ahí es donde se generan los bloqueos, aunque estén en el mismo archivo.

Con esta división, Persona B puede empezar a programar `draw()` y el manejo de teclado **desde el primer día**, usando el esqueleto ya compartido como referencia, sin esperar a que Persona A termine de pulir la lógica — solo necesita que los nombres de atributos no cambien.

---

## 4. ¿Conviene usar GitHub?

**Sí, para un proyecto de 2 personas con entrega en una semana, conviene** — evita el clásico problema de mandarse el `.py` por WhatsApp y perder cambios. No hace falta nada elaborado:

### Estructura de repo sugerida
No conviene separar la visualización en su propio archivo desde el día 1 (ver nota más arriba) — se empieza simple y solo se refactoriza si de verdad hace falta:
```
hospital-capacity-simulation/
├── README.md              # cómo correr el proyecto, quién hizo qué
├── requirements.txt        # pygame, numpy, pandas, openpyxl
├── person.py                # clase Person (Persona A)
├── hospital.py               # clase Hospital: capacidad, waiting_list (Persona A)
├── simulation.py              # clase Simulation: logica (Persona A) + draw()/eventos (Persona B)
├── exporter.py                 # self.history -> Excel (Persona B)
├── main.py                      # arma todo y corre
├── resultados/                    # .xlsx generados por cada escenario
└── docs/
    └── alcance_y_plan_de_trabajo.md   # este mismo documento
```

### Flujo de trabajo recomendado (simple, sin complicarse)
1. Uno de los dos crea el repo y sube el esqueleto base (commit inicial).
2. `hospital.py` y `exporter.py` son cada uno de una sola persona (Persona A y Persona B respectivamente) — ahí casi no hay riesgo de conflicto. `simulation.py` lo tocan ambos, pero en métodos distintos (lógica vs. `draw()`/eventos, ver sección 3) — mientras no editen las mismas líneas, Git combina los cambios sin problema.
3. Hacer commits pequeños y frecuentes (no un solo commit gigante al final) — más fácil de revisar y de revertir si algo se rompe.
4. Antes de cambiar un nombre de método/atributo que el otro esté usando, avisar por chat — eso es más importante que cualquier configuración de Git.
5. Opcional pero recomendado: usar el **README o un `TODO.md`** como checklist compartido (pueden copiar la lista de la sección 2 de este documento) y marcar lo que cada quien va completando, así ambos ven el avance sin tener que preguntarse constantemente.
6. No es necesario usar ramas (`branches`) para un proyecto de este tamaño — con hacer `pull` antes de empezar a trabajar y `push` frecuente alcanza. Si de todas formas quieren usar ramas, nómbrenlas por responsabilidad (no por persona), para que sigan siendo claras aunque cambien de tarea:
   - `feature/simulation-logic` → lógica: `Person`, `Hospital`, transiciones de estado, temporizadores.
   - `feature/visualization-export` → `draw()`, controles de teclado, exportación a Excel (`exporter.py`).

---

## 5. Cronograma sugerido (si la entrega es en ~1 semana)

| Día | Persona A | Persona B |
|---|---|---|
| 1 | Definir contrato de nombres juntos; empezar transiciones de estado | Empezar panel de texto sobre el esqueleto (con datos de ejemplo) |
| 2-3 | Terminar lógica de `Hospital` y temporizadores | Controles en vivo (pausa, +/- camas, velocidad) |
| 4 | Integrar y probar que todo funcione junto | Función de exportación a Excel |
| 5 | Correr los 3 escenarios (5/10/20 camas) y guardar resultados | Revisar formato del Excel, ajustar hoja resumen |
| 6 | Redactar el análisis de resultados | Grabar el video demo (2 min) |
| 7 | Preparar presentación juntos, ensayar, entregar | Preparar presentación juntos, ensayar, entregar |
