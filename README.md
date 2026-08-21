# hospital-capacity-simulation
Simulación en Pygame de una epidemia con capacidad hospitalaria limitada: agentes que se contagian, hospital con camas y lista de espera FIFO, controles en tiempo real y exportación a Excel para analizar cómo la capacidad afecta la mortalidad y la saturación del sistema.

Detalle completo del alcance, la pregunta de decisión y la organización del equipo: [`docs/alcance_y_plan_de_trabajo.md`](docs/alcance_y_plan_de_trabajo.md). Checklist de avance: [`TODO.md`](TODO.md).

## Estructura del proyecto

```
hospital-capacity-simulation/
├── README.md
├── requirements.txt
├── config.py            # constantes compartidas (tamaño de ventana, FPS)
├── person.py             # clase Person (Persona A)
├── hospital.py            # clase Hospital: capacidad, waiting_list (Persona A)
├── simulation.py           # clase Simulation: lógica (Persona A) + draw()/eventos (Persona B)
├── exporter.py              # self.history -> Excel (Persona B)
├── main.py                   # arma todo y corre
├── tests/                      # 125 tests (pytest)
├── resultados/                  # .xlsx generados por cada escenario
├── docs/
│   ├── alcance_y_plan_de_trabajo.md   # alcance, pregunta de decisión, organización
│   ├── analisis_resultados.md          # Bloque D: la respuesta con evidencia
│   ├── presentacion.md                  # contenido de las 6 diapositivas
│   └── guion_video.md                    # minutado del video de 2 min
└── TODO.md
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate      # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> Se usa `pygame-ce` en vez de `pygame`: es el fork mantenido por la
> comunidad, se importa igual (`import pygame`) y sí tiene instalador para
> Python 3.14, donde `pygame` todavía falla al compilar.

## Ejecución

**Modo comparación** — corre los 3 escenarios (5 / 10 / 20 camas) con semilla
fija y genera el Excel con los resultados:

```bash
python main.py --comparar
```

Corre 5 repeticiones por escenario (las mismas semillas en las 3 capacidades)
y produce `resultados/comparacion_camas.xlsx` con:
- hoja `promedios`: **la del análisis** — promedia las repeticiones de cada
  capacidad y lleva los 2 gráficos de barras comparativos.
- hoja `resumen`: una fila por corrida individual (parámetros + fallecidos,
  picos de ocupación y espera, ciclos saturado).
- hoja `timeline_run_N` por corrida: evolución ciclo a ciclo + gráfico de líneas.

Con `--reps 1` se hace una sola corrida por escenario. Los parámetros del
modelo se editan en `SIM_PARAMS`, dentro de `main.py`.

**Modo interactivo** — ventana de Pygame con controles en vivo:

```bash
python main.py
```

| Tecla | Acción |
|---|---|
| `ESPACIO` | pausar / reanudar |
| `↑` / `↓` | subir / bajar camas (bajar se rechaza si dejaría pacientes sin cama) |
| `←` / `→` | velocidad de la simulación (x1 a x10) |
| `ESC` | salir |

Colores: **azul** susceptible · **naranja** infectado · **rojo** grave ·
**verde** recuperado · **morado** fallecido. Los pacientes graves llevan un
aro **blanco** si tienen cama y **amarillo** si están en la lista de espera.

La demo usa semilla fija, así que la corrida es siempre la misma y se puede
ensayar antes de grabar. Se cambia en `SEED`, dentro de `main.py`.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Resultados

Respuesta completa con evidencia en
[`docs/analisis_resultados.md`](docs/analisis_resultados.md). Resumen
(promedio de 5 corridas por escenario):

| | 5 camas | 10 camas | 20 camas |
|---|---|---|---|
| Fallecidos | 34.0 | 23.6 | **13.0** |
| % del tiempo saturado | 66% | 54% | **14%** |
| Espera promedio sin cama (de 40 ciclos) | 28.4 | 19.1 | **9.8** |
| Pico de pacientes graves simultáneos | 31.0 | 31.4 | 31.0 |

Pasar de 5 a 20 camas reduce las muertes un **62%** sin cambiar en nada
cuánta gente se enferma: lo que cambia es el tiempo que un paciente grave
pasa esperando atención.

## Equipo

| Persona | Responsabilidad |
|---|---|
| [@Eliza-05](https://github.com/Eliza-05) | Lógica: `person.py`, `hospital.py`, métodos de lógica en `simulation.py`, análisis de resultados |
| [@Juanseom](https://github.com/Juanseom) | Visualización/controles: `draw()` y eventos en `simulation.py`, `exporter.py` |
