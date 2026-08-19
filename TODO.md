# TODO — Capacidad hospitalaria durante una epidemia

Checklist compartido. Ver `docs/alcance_y_plan_de_trabajo.md` para el detalle completo.

## A. Lógica de simulación (Persona A)
- [ ] Implementar `Person` con estado (`susceptible/infected/grave/recovered`) y temporizador reutilizable.
- [ ] Implementar transición infectado → recuperado / grave (según `pct_grave`).
- [ ] Implementar clase `Hospital` (camas, `waiting_list`, `admit`, `discharge`, asignación FIFO).
- [ ] Implementar transición grave → recuperado / fallecido (mortalidad según hospitalizado o no).
- [ ] Verificar que al liberarse una cama se reasigna automáticamente al primero en espera.

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
