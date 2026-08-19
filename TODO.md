# TODO — Capacidad hospitalaria durante una epidemia

Checklist compartido. Ver `docs/alcance_y_plan_de_trabajo.md` para el detalle completo.

## ⚠️ Antes de correr el proyecto — léeme

La lógica completa (`person.py`, `hospital.py`, `config.py`, `simulation.py`)
está terminada y probada — **82 tests en `tests/`**, correr con
`python -m pytest tests/ -v`. El tamaño de ventana quedó fijo en `config.py`
(`SCREEN_WIDTH=800, SCREEN_HEIGHT=600`) — usa esas mismas constantes en
`draw()`/`run()` en vez de hardcodear otro tamaño.

**Novedad importante:** ahora hay contagio real por proximidad (antes los
susceptibles nunca se contagiaban). Además el constructor de `Simulation`
tiene 2 parámetros nuevos obligatorios: `transmission_probability` e
`infection_radius`. Ver el contrato completo en
`docs/alcance_y_plan_de_trabajo.md` sección 1.8 — ahí está la tabla de todos
los parámetros, sus rangos válidos, y qué atributos/métodos puede usar
`draw()`/`handle_event()`/`run()` sin tener que leer `simulation.py`.

**Lo único que sigue bloqueado es el Bloque D** (correr 5/10/20 camas con
semilla fija y redactar el análisis): no se puede ejecutar todavía porque
depende de `exporter.py`, que sigue siendo un stub vacío (`export_results`,
`export_timeline`, `build_summary_row` sin implementar — es tarea de Persona B
en la sección C). En cuanto `exporter.py` funcione, correr los escenarios es
inmediato: `Simulation` ya expone `self.history` (con `cycle` incluido) con
todo lo necesario, y `sim.is_finished()` dice cuándo cortar cada corrida.

## A. Lógica de simulación (Persona A)
- [x] Implementar `Person` con estado (`susceptible/infected/grave/recovered/dead`) y temporizador reutilizable. (`infect`, `tick`, `set_grave`, `recover`, `die`, `move` — ver `tests/test_person.py`)
- [x] Contagio por proximidad: susceptibles dentro de `infection_radius` de un infectado se contagian con probabilidad `transmission_probability` (`Simulation._spread_contagion`, llamado al final de cada `update()`).
- [x] Implementar transición infectado → recuperado / grave (según `pct_grave`) en `Simulation._infection_expire`.
- [x] Implementar clase `Hospital` (camas, `waiting_list`, `admit`, `discharge`, asignación FIFO). (ver `tests/test_hospital.py`)
- [x] Implementar transición grave → recuperado / fallecido (mortalidad según hospitalizado o no) en `Simulation._grave_expire`.
- [x] Verificar que al liberarse una cama se reasigna automáticamente al primero en espera. (`test_discharge_reassigns_freed_bed_to_first_in_waiting_list`)
- [x] Corregido: subir la capacidad (`Hospital.set_capacity`) ahora también reasigna automáticamente a quien estaba esperando, no solo al dar de alta.
- [x] `current_cycle` — contador de ciclos en `Simulation`, arranca en 0, sube 1 por cada `update()` efectivo (no sube si está pausado); se registra como `cycle` en cada entrada de `self.history`.
- [x] `Simulation.is_finished()` — `True` cuando no queda nadie `infected` ni `grave`.
- [x] Validación de parámetros al construir `Simulation` (`ValueError` si algo está fuera de rango — población negativa, probabilidades fuera de `[0,1]`, etc.).
- [x] Bucle principal de lógica `Simulation.update()` (sin dibujo) — conecta timers + eventos + contagio + `_record_history`, mueve a los agentes vivos.
- [x] `Person.move()` — random walk acotado a `[0, width] x [0, height]` (constantes en `config.py`).
- [x] `Simulation.populate()` — crea la población inicial con posiciones dentro de pantalla y marca a los `initial_infected`; registra el frame `cycle=0` en `self.history`.
- [x] Tests de invariantes (`occupied == hospitalizados`, `occupied <= capacity`, `len(waiting_list) == graves esperando`, suma de estados == población) verificados a lo largo de una corrida completa con semilla fija.
- [ ] Bloque D: correr los 3 escenarios (5/10/20 camas) y redactar el análisis — depende de `exporter.py` (Persona B) para poder generar el Excel.

## B. Visualización y controles (Persona B)
- [ ] Al instanciar `Simulation` en `main.py`/`run()`, recordar pasar los 2 parámetros nuevos: `transmission_probability` e `infection_radius` (si se omiten, quedan en `0.0` y no hay contagio). Ver tabla completa de parámetros en `docs/alcance_y_plan_de_trabajo.md` sección 1.8.
- [ ] Panel de texto en pantalla con los 8 contadores + ocupación de camas (agregar también `sim.current_cycle`, ya disponible).
- [ ] Aviso visual cuando `hospital.is_saturated`.
- [ ] Colores distintos por estado (azul/verde/naranja/rojo/morado).
- [ ] Controles en vivo: pausa (`SPACE`, alterna `sim.paused`), subir/bajar camas (`UP`/`DOWN`, usar `sim.hospital.set_capacity(n)`), velocidad (`LEFT`/`RIGHT`).
- [ ] Opcional: mostrar aviso de "epidemia terminada" cuando `sim.is_finished()` sea `True`.

## C. Datos y Excel (Persona B, con datos de Persona A)
- [ ] Registrar historial por frame (`self.history`, ya incluye `cycle`).
- [ ] Exportar hoja `timeline_run_N` por cada corrida.
- [ ] Exportar hoja `resumen` con una fila por escenario (parámetros + resultados agregados).
- [ ] Correr y guardar al menos 3 escenarios (5 / 10 / 20 camas), misma semilla (`random.Random(seed).random` como `random_fn`), capacidad fija por corrida. Se puede usar `sim.is_finished()` para cortar cada corrida en cuanto la epidemia termine en vez de un número fijo de ciclos.

## D. Análisis (Persona A)
- [ ] Redactar la respuesta a la pregunta de decisión con evidencia del Excel.

## E. Entregables finales (conjunto)
- [ ] Grabar video demo de 2 min.
- [ ] Preparar presentación de 2 min.
- [ ] Revisar que el código corra limpio desde cero.
- [ ] Empaquetar entrega: código + video + presentación + README.
