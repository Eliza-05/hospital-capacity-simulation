# TODO — Capacidad hospitalaria durante una epidemia

Checklist compartido. Ver `docs/alcance_y_plan_de_trabajo.md` para el detalle completo.

## ⚠️ Antes de correr el proyecto — léeme

La lógica de Persona A (`person.py`, `hospital.py`, `config.py`, y todos los
métodos de lógica de `simulation.py`, incluyendo `populate()` y el movimiento
de agentes) está completa y probada (45 tests en `tests/`, correr con
`python -m pytest`). El tamaño de ventana quedó fijo en `config.py`
(`SCREEN_WIDTH=800, SCREEN_HEIGHT=600`) — usa esas mismas constantes en
`draw()`/`run()` en vez de hardcodear otro tamaño.

**Lo único que sigue bloqueado es el Bloque D** (correr 5/10/20 camas con
semilla fija y redactar el análisis): no se puede ejecutar todavía porque
depende de `exporter.py`, que sigue siendo un stub vacío (`export_results`,
`export_timeline`, `build_summary_row` sin implementar — es tarea de Persona B
en la sección C). En cuanto `exporter.py` funcione, correr los escenarios es
inmediato: `Simulation` ya expone `self.history` con todo lo necesario.

## A. Lógica de simulación (Persona A)
- [x] Implementar `Person` con estado (`susceptible/infected/grave/recovered`) y temporizador reutilizable. (`infect`, `tick`, `set_grave`, `recover`, `die` — ver `tests/test_person.py`)
- [x] Implementar transición infectado → recuperado / grave (según `pct_grave`) en `Simulation._infection_expire`.
- [x] Implementar clase `Hospital` (camas, `waiting_list`, `admit`, `discharge`, asignación FIFO). (ver `tests/test_hospital.py`)
- [x] Implementar transición grave → recuperado / fallecido (mortalidad según hospitalizado o no) en `Simulation._grave_expire`.
- [x] Verificar que al liberarse una cama se reasigna automáticamente al primero en espera. (`test_discharge_reassigns_freed_bed_to_first_in_waiting_list`)
- [x] Bucle principal de lógica `Simulation.update()` (sin dibujo) — conecta timers + eventos + `_record_history`, mueve a los agentes vivos.
- [x] `Person.move()` — random walk acotado a `[0, width] x [0, height]` (constantes en `config.py`).
- [x] `Simulation.populate()` — crea la población inicial con posiciones dentro de pantalla y marca a los `initial_infected`; registra el frame t=0 en `self.history`.
- [ ] Bloque D: correr los 3 escenarios (5/10/20 camas) y redactar el análisis — depende de `exporter.py` (Persona B) para poder generar el Excel.

## B. Visualización y controles (Persona B)
- [ ] Panel de texto en pantalla con los 8 contadores + ocupación de camas.
- [ ] Aviso visual cuando `hospital.is_saturated`.
- [ ] Colores distintos por estado (azul/verde/naranja/rojo/morado).
- [ ] Controles en vivo: pausa (`SPACE`), subir/bajar camas (`UP`/`DOWN`), velocidad (`LEFT`/`RIGHT`).

## C. Datos y Excel (Persona B, con datos de Persona A)
- [ ] Registrar historial por frame (`self.history`).
- [ ] Exportar hoja `timeline_run_N` por cada corrida.
- [ ] Exportar hoja `resumen` con una fila por escenario (parámetros + resultados agregados).
- [ ] Correr y guardar al menos 3 escenarios (5 / 10 / 20 camas), misma semilla, capacidad fija por corrida.

## D. Análisis (Persona A)
- [ ] Redactar la respuesta a la pregunta de decisión con evidencia del Excel.

## E. Entregables finales (conjunto)
- [ ] Grabar video demo de 2 min.
- [ ] Preparar presentación de 2 min.
- [ ] Revisar que el código corra limpio desde cero.
- [ ] Empaquetar entrega: código + video + presentación + README.
