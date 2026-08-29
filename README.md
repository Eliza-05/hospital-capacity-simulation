<div align="center">

# 🏥 hospital-capacity-simulation

**Simulación por agentes de una epidemia con capacidad hospitalaria limitada, construida en Pygame.**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![pygame-ce](https://img.shields.io/badge/pygame--ce-simulación-00A86B?logo=python&logoColor=white)](https://pyga.me/)
[![pandas](https://img.shields.io/badge/pandas-exportación%20Excel-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![pytest](https://img.shields.io/badge/tests-132%20passing-brightgreen?logo=pytest&logoColor=white)](tests/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**Elizabeth Correa Suárez · Juan Sebastián Ortega Muñoz**

</div>

---

## 📑 Tabla de contenidos

1. [Introducción](#-introducción)
2. [La pregunta de decisión](#-la-pregunta-de-decisión)
3. [Estructura del proyecto](#-estructura-del-proyecto)
4. [Qué hace cada clase](#-qué-hace-cada-clase)
5. [Cómo funciona el código internamente](#-cómo-funciona-el-código-internamente)
6. [Las 3 formas de ejecutar el proyecto](#-las-3-formas-de-ejecutar-el-proyecto)
7. [Cómo se ejecuta](#-cómo-se-ejecuta)
8. [Evidencia / captura de la simulación](#-evidencia--captura-de-la-simulación)
9. [Parámetros del modelo](#-parámetros-del-modelo)
10. [Resultados (Excel)](#-resultados-excel)
11. [Análisis](#-análisis)
12. [Conclusiones](#-conclusiones)
13. [Límites del modelo](#-límites-del-modelo)
14. [Tests](#-tests)

---

## 📖 Introducción

Este proyecto es un entregable de un curso universitario de Inteligencia Artificial. Consiste en una **simulación por agentes** construida con [Pygame](https://www.pygame.org/) (usando el fork `pygame-ce`) que modela la propagación de una epidemia en una población de personas que se mueven libremente por una pantalla.

A diferencia de una simulación SIR clásica (susceptible → infectado → recuperado), este modelo agrega un estado adicional: **grave**. Una persona grave necesita una cama de hospital, y el hospital tiene **capacidad limitada**. Cuando la demanda de camas supera la oferta, los pacientes graves quedan en una lista de espera, y el tiempo que pasan esperando afecta directamente su probabilidad de sobrevivir.

El proyecto incluye:

- Visualización en tiempo real de la epidemia con controles interactivos (pausa, capacidad de camas, velocidad).
- Exportación de resultados a Excel (`openpyxl` + `pandas`) con hojas de evolución temporal y de resumen comparativo entre escenarios.
- Un análisis cuantitativo que responde a la pregunta de decisión del proyecto con evidencia numérica.

---

## ❓ La pregunta de decisión

> **¿Cómo afecta la capacidad hospitalaria (número de camas) a la mortalidad, la saturación del sistema y la cantidad de pacientes sin atención durante una epidemia?**

Esta es la pregunta que el proyecto busca responder. Importa porque, en una epidemia real, el número de camas disponibles no es algo que se pueda ajustar de un día para el otro: es una decisión de planeamiento con consecuencias directas sobre cuánta gente recibe atención a tiempo. El proyecto la responde ejecutando la misma epidemia con distinto número de camas (5, 10 y 20) y comparando los resultados con evidencia cuantitativa, en vez de intuición.

---

## 🗂️ Estructura del proyecto

```
hospital-capacity-simulation/
├── config.py
├── person.py
├── hospital.py
├── simulation.py
├── exporter.py
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
├── README.md
├── tests/
│   ├── test_person.py
│   ├── test_hospital.py
│   ├── test_simulation.py
│   ├── test_controls.py
│   ├── test_exporter.py
│   └── test_main.py
└── resultados/
    └── comparacion_camas.xlsx
```

| Archivo / carpeta | Qué hace |
|---|---|
| [`config.py`](config.py) | Constantes compartidas por todo el proyecto: tamaño de la ventana de simulación, ancho del panel lateral y FPS. |
| [`person.py`](person.py) | Clase `Person`: agente individual, su posición, estado epidemiológico y movimiento. |
| [`hospital.py`](hospital.py) | Clase `Hospital`: administra las camas disponibles y la lista de espera FIFO. |
| [`simulation.py`](simulation.py) | Clase `Simulation`: motor central que coordina a las personas y al hospital, avanza la lógica ciclo a ciclo y dibuja todo en pantalla con Pygame. |
| [`exporter.py`](exporter.py) | Convierte `simulation.history` en un archivo Excel (`.xlsx`) con hojas de evolución temporal, resumen y promedios, más gráficos embebidos. |
| [`main.py`](main.py) | Punto de entrada: define los parámetros del modelo y arma la simulación en uno de los tres modos de ejecución. |
| [`tests/`](tests/) | Suite de tests (`pytest`) para la lógica, los controles/dibujado, la exportación y el parseo de argumentos. |
| [`resultados/`](resultados/) | Carpeta donde se generan los `.xlsx` del modo comparación (ya contiene `comparacion_camas.xlsx`). |
| [`requirements.txt`](requirements.txt) / [`requirements-dev.txt`](requirements-dev.txt) | Dependencias de ejecución y de desarrollo (tests). |
| [`LICENSE`](LICENSE) | Licencia MIT del proyecto. |

---

## 🧩 Qué hace cada clase

### `Person` — [`person.py`](person.py)

Representa a un individuo dentro de la simulación: guarda su posición, su estado de salud y un temporizador reutilizable para las transiciones de estado.

**Atributos principales:** `x`, `y` (posición), `state` (`susceptible` / `infected` / `grave` / `recovered` / `dead`), `hospitalized` (si ocupa una cama), `timer` (ciclos hasta el próximo cambio de estado), `cycles_waiting` (ciclos que pasó grave sin conseguir cama), `vx`/`vy` (vector de velocidad persistente).

| Método | Qué hace |
|---|---|
| `infect(duration)` | Pasa de sano a infectado y arranca el conteo de ciclos hasta el próximo cambio de estado. |
| `tick()` | Avanza el temporizador en uno; devuelve `True` cuando llega a cero, avisando que toca aplicar la siguiente transición. |
| `set_grave(duration)` | Agrava a la persona infectada (ahora necesita hospitalización) y reinicia el temporizador y el contador de espera. |
| `recover()` | Marca a la persona como recuperada y libera su cama si tenía una asignada. |
| `die()` | Marca a la persona como fallecida y libera su cama si tenía una asignada. |
| `move(width, height, step, random_fn)` | Actualiza la posición sumando una velocidad persistente con inercia (no salta a un punto al azar cada ciclo); recorta la magnitud a `step` y mantiene a la persona dentro de los límites de la pantalla. |

### `Hospital` — [`hospital.py`](hospital.py)

Administra las camas disponibles y la lista de espera de pacientes graves.

**Atributos principales:** `capacity` (camas totales), `occupied` (camas ocupadas), `waiting_list` (`collections.deque` con los pacientes en espera, en orden de llegada). Además expone las propiedades `free_beds` (camas libres) e `is_saturated` (si no quedan camas libres).

| Método | Qué hace |
|---|---|
| `admit(person)` | Ingresa a una persona si hay cama libre; si no la hay, la agrega al final de la lista de espera. |
| `discharge(person)` | Da de alta a una persona (libera su cama) y, si hay alguien esperando, le asigna esa cama de inmediato al primero de la fila. |
| `set_capacity(new_capacity)` | Cambia la capacidad total. Aumentarla siempre se permite; reducirla se rechaza si dejaría a menos camas que pacientes ya ocupándolas. Al subir la capacidad, reasigna automáticamente a quien esté esperando si queda cupo. Devuelve `True`/`False` según si el cambio se aplicó. |
| `remove_from_waiting_list(person)` | Saca a una persona de la lista de espera (se usa cuando alguien se recupera o fallece mientras esperaba). |

### `Simulation` — [`simulation.py`](simulation.py)

Es el motor central del proyecto: crea la población inicial, avanza el estado de cada persona ciclo a ciclo, gestiona los ingresos y altas del hospital, dibuja todo en pantalla y guarda un historial por ciclo para la exportación a Excel.

**Atributos principales:** los parámetros del modelo recibidos en el constructor (ver [tabla de parámetros](#-parámetros-del-modelo)), más `hospital` (instancia de `Hospital`), `people` (lista de `Person`), `history` (lista de snapshots por ciclo), `paused`, `speed` y `current_cycle`.

**Métodos de lógica:**

| Método | Qué hace |
|---|---|
| `_validate_params(...)` *(estático)* | Valida los parámetros del constructor y lanza `ValueError` con un mensaje claro si alguno está fuera de rango. |
| `populate()` | Genera la población inicial en posiciones aleatorias, infecta a las primeras `initial_infected` personas y registra el primer snapshot del historial. |
| `_infect(person)` | Marca a una persona como contagiada e inicia su periodo de infección. |
| `_infection_expire(person)` | Se ejecuta al vencer el periodo de infección leve: según `pct_grave`, decide si la persona se agrava (e intenta hospitalizarla) o se recupera directamente. |
| `_grave_mortality(person)` | Calcula la probabilidad de que un paciente grave fallezca, interpolando entre `mortality_hospitalized` y `mortality_waiting` según el tiempo que pasó sin cama (ver [sección 5](#-cómo-funciona-el-código-internamente)). |
| `_grave_expire(person)` | Se ejecuta al vencer el periodo crítico de un paciente grave: aplica `_grave_mortality` y decide si fallece o se recupera. |
| `_recover(person)` | Marca a una persona como recuperada, liberando su cama o sacándola de la lista de espera según corresponda. |
| `_record_history()` | Guarda en `self.history` un resumen del estado actual: cantidad de personas por estado, ocupación de camas, gente en espera y si el hospital está saturado. |
| `update()` | Avanza la simulación un ciclo completo (ver desglose en la [sección 5](#-cómo-funciona-el-código-internamente)). |
| `_spread_contagion()` | Revisa a las personas infectadas y decide, según distancia y probabilidad de contagio, quién se enferma en ese ciclo. |
| `_in_contagion_range(source, other)` | Indica si `other` está sana y lo bastante cerca de `source` como para poder contagiarse. |
| `is_finished()` | Indica si ya no queda nadie `infected` ni `grave` en la simulación. |

**Métodos de presentación (ventana de Pygame):**

| Método | Qué hace |
|---|---|
| `handle_event(event)` | Responde a las teclas del usuario: pausar (`ESPACIO`), subir/bajar camas (`↑`/`↓`) y ajustar la velocidad (`←`/`→`). |
| `_fonts()` | Crea (una sola vez) las tipografías usadas en el panel lateral. |
| `_state_counts()` | Cuenta cuánta gente hay en cada estado en el momento actual. |
| `_draw_people(screen)` | Dibuja a cada persona como un punto del color de su estado; los pacientes graves llevan además un aro (blanco con cama, amarillo en espera). |
| `_draw_counter(screen, y, label, value, color)` | Dibuja una fila `etiqueta ... valor` del panel lateral. |
| `_draw_bed_bar(screen, y)` | Dibuja la barra de ocupación de camas, que se pone roja cuando el hospital se satura. |
| `_draw_panel(screen)` | Dibuja el panel lateral completo: contadores por estado, datos del hospital, controles y ayuda de teclas. |
| `_draw_alerts(screen)` | Dibuja los avisos grandes sobre el área de simulación: hospital saturado y epidemia terminada. |
| `draw(screen)` | Junta todo el dibujo: fondo, personas, alertas y panel. |
| `run()` | Inicializa Pygame y ejecuta el loop principal (eventos → `update()` × `speed` → `draw()`) hasta que se cierra la ventana o se presiona `ESC`. |

---

## ⚙️ Cómo funciona el código internamente

### El ciclo de `update()`

Cada llamada a `Simulation.update()` (si la simulación no está pausada) hace, en orden:

1. Incrementa `current_cycle` en uno.
2. Para cada persona **viva** (`state != "dead"`):
   - La mueve (`Person.move`).
   - Si está `grave` y no tiene cama, suma un ciclo a `cycles_waiting`.
   - Si está `infected` y su temporizador vence (`tick()` devuelve `True`), llama a `_infection_expire`.
   - Si está `grave` y su temporizador vence, llama a `_grave_expire`.
3. Llama a `_spread_contagion()` para calcular los contagios nuevos de ese ciclo.
4. Llama a `_record_history()` para guardar el snapshot del ciclo en `self.history`.

### Cómo se decide el contagio

`_spread_contagion()` recorre a todas las personas `infected` (fuentes) y, por cada una, revisa a todas las demás personas. Si otra persona está `susceptible` y a una distancia ≤ `infection_radius` de la fuente, se sortea `random_fn() < transmission_probability` para decidir si se contagia. Los nuevos contagios se acumulan en un `set` y se aplican **todos al final** del método — así una persona recién contagiada en este ciclo no puede a su vez contagiar a otras en el mismo ciclo.

### Cómo se asignan y liberan camas

El hospital usa una lista de espera FIFO real (`collections.deque`), con una sola regla de asignación: **orden de llegada**.

- `admit(person)`: si hay camas libres, ocupa una; si no, la persona se agrega al final de `waiting_list`.
- `discharge(person)`: libera la cama de quien se retira (por alta o por fallecimiento) y, si hay alguien esperando, le asigna esa cama de inmediato al primero de la fila (`popleft()`).
- `set_capacity(n)`: subir la capacidad siempre se permite y reasigna camas a quien esperaba si queda cupo disponible; bajarla se rechaza si dejaría camas ocupadas por debajo de cero (es decir, si `n < occupied`).

### Mortalidad según tiempo de espera

Cuando el temporizador de un paciente `grave` vence, `_grave_expire` decide si muere o se recupera. La probabilidad de morir la calcula `_grave_mortality`, y **no depende solo de si el paciente tiene cama en el instante exacto del vencimiento**: se interpola según qué fracción de su periodo crítico (`grave_duration`) pasó sin atención.

```python
if not person.hospitalized:
    return self.mortality_waiting

sin_atencion = min(person.cycles_waiting / self.grave_duration, 1.0)
return (self.mortality_hospitalized
        + sin_atencion * (self.mortality_waiting - self.mortality_hospitalized))
```

En los extremos, esto coincide con lo intuitivo: alguien que nunca esperó (`cycles_waiting = 0`) usa exactamente `mortality_hospitalized`; alguien que jamás consiguió cama usa `mortality_waiting`. Entre esos dos extremos, el riesgo crece linealmente con el tiempo pasado sin atención. `_grave_expire` sortea `random_fn() < mortality` para decidir el desenlace y libera la cama o saca a la persona de la lista de espera según corresponda.

---

## ▶️ Las 3 formas de ejecutar el proyecto

El bloque `if __name__ == "__main__":` de [`main.py`](main.py) decide el modo según los argumentos de línea de comandos:

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `python main.py` | Modo **interactivo** con ventana de Pygame, usando la semilla fija `SEED = 42` (`_resolve_seed` sin `--random`). | Para ensayar o grabar una demo reproducible: la corrida es siempre la misma. |
| `python main.py --random` | Modo **interactivo**, pero `_resolve_seed` sortea una semilla nueva en cada corrida (`random.randint(0, 999_999)`). | Para ver epidemias distintas en cada ejecución, en vez de repetir siempre la misma. |
| `python main.py --comparar [--reps N]` | Modo **comparación**: corre, sin ventana, un escenario por cada valor de `BED_SCENARIOS = (5, 10, 20)`, cada uno `N` veces (`--reps`, por defecto `REPETICIONES = 5`) con semillas consecutivas a partir de `SEED`, y exporta todo a `resultados/comparacion_camas.xlsx`. | Para generar la evidencia cuantitativa que responde la pregunta de decisión. Con `--reps 1` se hace una sola corrida por escenario. |

En el modo comparación, `run_headless()` corre cada escenario ciclo a ciclo (sin dibujar nada) hasta que `sim.is_finished()` es `True`, con un corte de seguridad en `MAX_CYCLES = 5000` por si la epidemia nunca se apagara.

---

## 🚀 Cómo se ejecuta

### 1. Crear y activar un entorno virtual

```bash
python -m venv .venv
source .venv/bin/activate      # en Windows: .venv\Scripts\activate
```

### 2. Instalar dependencias

Para correr la simulación ([`requirements.txt`](requirements.txt): `pygame-ce`, `numpy`, `pandas`, `openpyxl`):

```bash
pip install -r requirements.txt
```

Para además correr los tests ([`requirements-dev.txt`](requirements-dev.txt) agrega `pytest` sobre lo anterior):

```bash
pip install -r requirements-dev.txt
```

> Se usa `pygame-ce` (fork mantenido de `pygame`) en vez de `pygame`. Se importa igual (`import pygame`).

### 3. Ejecutar

```bash
# Modo interactivo, semilla fija (demo reproducible)
python main.py

# Modo interactivo, semilla aleatoria en cada corrida
python main.py --random

# Modo comparación: genera resultados/comparacion_camas.xlsx (5 repeticiones por escenario)
python main.py --comparar

# Modo comparación, una sola corrida por escenario
python main.py --comparar --reps 1
```

### Controles del modo interactivo

| Tecla | Acción |
|---|---|
| `ESPACIO` | Pausar / reanudar. |
| `↑` / `↓` | Subir / bajar camas (bajar se rechaza si dejaría pacientes sin cama). |
| `←` / `→` | Bajar / subir la velocidad de la simulación (x1 a x10). |
| `ESC` | Salir. |

---

## 🖼️ Evidencia / captura de la simulación

> **Placeholder:** reemplazar esta sección con una captura real de la ventana de la simulación corriendo (por ejemplo `captura_simulacion.png`).

```markdown
![Captura de la simulación corriendo](captura_simulacion.png)
```

En la captura debería verse:

- El área de simulación con personas coloreadas según su estado: **azul** susceptible, **naranja** infectado, **rojo** grave, **verde** recuperado, **morado** fallecido.
- Los pacientes graves con su aro distintivo: **blanco** si tienen cama asignada, **amarillo** si están en la lista de espera.
- El panel lateral derecho con los contadores por estado, la ocupación de camas (barra que se pone roja al saturarse) y el estado de los controles (pausado/corriendo, velocidad).
- Idealmente, el banner rojo de **HOSPITAL SATURADO** visible en la parte superior, para mostrar el caso más relevante del análisis.

---

## 🎛️ Parámetros del modelo

`SIM_PARAMS`, definido en [`main.py`](main.py), son los parámetros del modelo que se mantienen **iguales en los tres escenarios** del modo comparación — lo único que cambia entre corridas es la capacidad de camas:

| Parámetro | Valor | Qué significa |
|---|---|---|
| `population` | `300` | Cantidad total de personas de la población. |
| `initial_infected` | `5` | Cuántas personas arrancan infectadas al llamar a `populate()`. |
| `transmission_probability` | `0.10` | Probabilidad de que un infectado contagie a un susceptible dentro de su radio de contagio, en cada ciclo. |
| `infection_radius` | `45` | Distancia máxima (en píxeles) para considerar que dos personas están en contacto. |
| `pct_grave` | `0.30` | Probabilidad de que un infectado pase a estado grave al vencer `infection_duration`. |
| `infection_duration` | `60` | Ciclos que dura el estado `infected` antes de resolverse (grave o recuperado). |
| `grave_duration` | `40` | Ciclos que dura el estado `grave` antes de resolverse (fallecido o recuperado). |
| `mortality_hospitalized` | `0.15` | Probabilidad de morir al vencer `grave_duration` si estuvo hospitalizado todo ese tiempo. |
| `mortality_waiting` | `0.60` | Probabilidad de morir al vencer `grave_duration` si nunca consiguió cama. |

Otras constantes relevantes de `main.py`, fuera de `SIM_PARAMS`:

| Constante | Valor | Qué significa |
|---|---|---|
| `BED_SCENARIOS` | `(5, 10, 20)` | Capacidades de hospital que se comparan en el modo `--comparar`. |
| `SEED` | `42` | Semilla base: fija para el modo interactivo por defecto y punto de partida de las semillas del modo comparación. |
| `INTERACTIVE_BEDS` | `10` | Capacidad inicial del hospital en el modo interactivo. |
| `REPETICIONES` | `5` | Repeticiones por escenario en el modo comparación, salvo que se pase `--reps`. |
| `MAX_CYCLES` | `5000` | Corte de seguridad de ciclos en `run_headless()` por si una epidemia no se apagara nunca. |

---

## 📊 Resultados (Excel)

`python main.py --comparar` genera `resultados/comparacion_camas.xlsx` (ya incluido en el repositorio) con las siguientes hojas, construidas por [`exporter.py`](exporter.py):

| Hoja | Contenido |
|---|---|
| `resumen` | Una fila por cada corrida individual: parámetros del escenario + resultados agregados (ciclos simulados, contagiados totales, fallecidos, recuperados, tasas de mortalidad/letalidad, picos de infectados/graves/ocupación/espera, espera acumulada, ciclos con pacientes sin cama, ciclos saturado y % del tiempo saturado). |
| `promedios` *(solo si hay más de una repetición por escenario)* | Promedia las filas de `resumen` que comparten capacidad de camas, con la cantidad de repeticiones incluida. Incluye dos gráficos de barras: **fallecidos según capacidad hospitalaria** y **ciclos con hospital saturado**. |
| `timeline_run_N` *(una por corrida)* | Evolución ciclo a ciclo de la corrida N: cantidad de personas en cada estado, hospitalizados, en espera, camas ocupadas/libres, capacidad y si estaba saturado. Incluye un gráfico de líneas con la evolución de infectados, graves, hospitalizados, en espera y fallecidos. |

Resumen numérico, promediando 5 corridas por escenario (semillas 42 a 46, las mismas para las tres capacidades):

| | 5 camas | 10 camas | 20 camas |
|---|---|---|---|
| **Fallecidos** | 34.0 | 23.6 | **13.0** |
| Mortalidad sobre la población | 11% | 8% | 4% |
| Letalidad entre contagiados | 12% | 8% | 5% |
| Contagiados totales | 275.8 | 281.6 | 287.2 |
| Pico de pacientes graves simultáneos | 31.0 | 31.4 | 31.0 |
| Pico de pacientes sin cama | 26.0 | 21.4 | 11.0 |
| Personas que esperaron cama | 73.2 | 63.8 | 24.8 |
| Espera promedio (ciclos, de 40) | 28.4 | 19.1 | 9.8 |
| Espera acumulada (persona-ciclo) | 2120 | 1227 | 296 |
| **% del tiempo con el hospital saturado** | 66% | 54% | **14%** |

---

## 🔍 Análisis

Puntos principales:

- **La capacidad no cambia cuánta gente se enferma, cambia cuánta se muere.** El pico de pacientes graves es prácticamente idéntico en los tres escenarios (~31), porque la epidemia genera la misma demanda de camas sin importar cuántas haya. Lo que varía es cuántos de esos pacientes reciben atención a tiempo.
- **El mecanismo es el tiempo sin atención.** La gravedad dura 40 ciclos. Con 5 camas, un paciente grave pasa en promedio 28.4 de esos 40 ciclos sin cama (71% del periodo crítico); con 20 camas, baja a 9.8 ciclos (25%). Como la mortalidad se interpola según esa fracción, la diferencia de tiempo de espera se traduce directamente en la diferencia de fallecidos.
- **La saturación no desaparece ni con 20 camas.** El hospital sigue saturado el 14% del tiempo, con un pico de 11 pacientes sin cama. El pico de demanda (~31 graves simultáneos) es más del 10% de la población total.
- **Rendimientos decrecientes.** Pasar de 5 a 10 camas evita ~10.4 muertes (2.08 por cama agregada); pasar de 10 a 20 evita una cantidad similar (~10.6 muertes) pero con el doble de camas (1.06 por cama). Las primeras camas agregadas a un sistema colapsado valen más que las últimas.
- **Efecto contraintuitivo.** Los contagiados totales suben levemente con más camas (275.8 → 287.2) y la epidemia dura más, porque al morir menos gente quedan más personas vivas circulando y contagiándose.

---

## ✅ Conclusiones

> Con la misma epidemia y la misma cantidad de enfermos, pasar de 5 a 20 camas reduce las muertes un **62%** (34 → 13) y el tiempo de saturación del 66% al 14%. El mecanismo es el tiempo de espera: con 5 camas un paciente grave pasa el 71% de su periodo crítico sin atención, contra el 25% con 20 camas. Aun así, ni con 20 camas el sistema deja de saturarse, y las primeras camas que se agregan salvan el doble de vidas por cama que las últimas.

En otras palabras: en este modelo, **la capacidad hospitalaria no es una herramienta de prevención de contagios, es una herramienta de supervivencia** para quienes ya se enfermaron gravemente.

---

## ⚠️ Límites del modelo

Qué NO representa este modelo:

- **Las probabilidades son parámetros del modelo, no cifras clínicas reales.** `pct_grave`, `mortality_hospitalized` y `mortality_waiting` se eligieron para estudiar el efecto de un recurso limitado, no para representar ninguna enfermedad específica.
- **Única regla de asignación de camas: orden de llegada (FIFO).** El proyecto no implementa otras estrategias (priorizar por vulnerabilidad, por probabilidad de recuperación, etc.); eso está explícitamente fuera de alcance.
- **El hospital es abstracto.** Es un contador de camas, sin ubicación física, médicos, enfermeros, ventiladores ni traslados entre hospitales. La cama es el único recurso escaso del modelo.
- **5 repeticiones por escenario son pocas.** Alcanzan para que la tendencia general se sostenga (una sola corrida por escenario puede invertir la comparación por azar), pero la dispersión entre semillas sigue siendo grande. Para afirmaciones más finas harían falta muchas más corridas.
- **La mortalidad interpolada según tiempo sin atención es un supuesto del modelo**, no un dato observado. Es una elección de diseño para que la capacidad hospitalaria tenga un efecto real sobre la mortalidad, no una regla derivada de evidencia clínica.
- **No hay calibración con datos reales** ni predicción de casos reales, ni aprendizaje automático para elegir parámetros.

---

## 🧪 Tests

El proyecto tiene una suite de **132 tests** (`pytest`) en [`tests/`](tests/):

| Archivo | Qué cubre |
|---|---|
| [`test_person.py`](tests/test_person.py) | Transiciones de estado de `Person` (`infect`, `tick`, `set_grave`, `recover`, `die`) y el movimiento con inercia (`move`). |
| [`test_hospital.py`](tests/test_hospital.py) | Admisión y alta de pacientes, la lista de espera FIFO, el cambio de capacidad (incluyendo los casos de rechazo) y la reasignación automática de camas liberadas. |
| [`test_simulation.py`](tests/test_simulation.py) | La validación de parámetros del constructor, las transiciones de infección y gravedad, el contagio por proximidad, `_grave_mortality` (incluyendo la interpolación y sus casos límite), `populate()`, `update()`, `current_cycle`, `is_finished()`, y una prueba de invariantes a lo largo de una corrida completa. |
| [`test_controls.py`](tests/test_controls.py) | `handle_event` (pausa, teclas de camas y velocidad) y `draw` sobre una `Surface` en memoria, sin abrir ninguna ventana. |
| [`test_exporter.py`](tests/test_exporter.py) | La conversión de `history` a DataFrame, el cálculo de la fila de resumen (`build_summary_row`), el promedio por capacidad (`build_average_summary`) y la generación del archivo `.xlsx` completo con sus hojas y gráficos. |
| [`test_main.py`](tests/test_main.py) | El parseo de `--random` en `_resolve_seed`. |

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

---

