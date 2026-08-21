# Presentación (2 minutos)

Contenido diapositiva por diapositiva, listo para pasar a PowerPoint / Canva /
Google Slides. **6 diapositivas, ~20 segundos cada una.**

Los gráficos ya están dentro de `resultados/comparacion_camas.xlsx`: la hoja
`promedios` trae los dos de barras y cada `timeline_run_N` trae el de líneas.
Se copian y pegan directo, no hay que rehacerlos.

---

## Diapositiva 1 — El caso *(0:00-0:20)*

**Título:** Capacidad hospitalaria durante una epidemia

**En pantalla:**
- Simulación por agentes en Pygame (300 personas)
- Estados: sano → infectado → **grave** → recuperado / fallecido
- El estado **grave** necesita una cama. Las camas son limitadas.
- Lista de espera por orden de llegada

**Qué decir:**
> "Simulamos una epidemia agregando a los estados clásicos uno nuevo: el
> estado **grave**, que necesita una cama de hospital. Y el hospital tiene
> camas limitadas."

---

## Diapositiva 2 — La pregunta de decisión *(0:20-0:40)*

**En pantalla, en grande:**

> ### ¿Cómo afecta el número de camas a la mortalidad, la saturación y la cantidad de pacientes sin atención?

**Debajo, chico:**
- Se responde corriendo 5, 10 y 20 camas
- Todo lo demás idéntico: misma población, mismo contagio, mismas semillas
- 5 repeticiones por escenario

**Qué decir:**
> "La decisión que estudiamos es qué pasa cuando la demanda de camas supera la
> oferta. Corrimos tres escenarios cambiando **únicamente** el número de camas."

---

## Diapositiva 3 — La simulación *(0:40-1:00)*

**En pantalla:** una captura de la ventana con el hospital saturado
(cartel rojo **HOSPITAL SATURADO** + panel de contadores visible).

**Señalar:**
- Aro blanco = tiene cama · Aro amarillo = está esperando
- Panel con los 8 contadores en tiempo real
- Camas y velocidad se cambian en vivo

**Qué decir:**
> "Los pacientes graves con aro blanco consiguieron cama; los de aro amarillo
> están esperando, sin atención. Cada ciclo en esa lista aumenta su riesgo."

---

## Diapositiva 4 — El resultado principal *(1:00-1:25)*

**En pantalla:** el gráfico de barras `Fallecidos según capacidad hospitalaria`
(hoja `promedios`), + esta tabla:

| | 5 camas | 10 camas | 20 camas |
|---|---|---|---|
| **Fallecidos** | **34** | **24** | **13** |
| % tiempo saturado | 66% | 54% | 14% |
| Espera promedio (de 40 ciclos) | 28.4 | 19.1 | 9.8 |
| **Pico de pacientes graves** | **31** | **31** | **31** |

**Qué decir:**
> "De 5 a 20 camas, las muertes bajan un 62%. Pero fíjense en la última fila:
> **el pico de pacientes graves es el mismo en los tres casos.** La misma
> cantidad de gente se enferma. Lo único que cambia es cuántos son atendidos."

---

## Diapositiva 5 — El mecanismo *(1:25-1:45)*

**En pantalla, en grande:**

> ### La gravedad dura 40 ciclos.
> ### Con 5 camas se esperan 28 sin atención (71%).
> ### Con 20 camas, 10 (25%).

**Debajo:** rendimientos decrecientes

| Ampliación | Camas | Muertes evitadas por cama |
|---|---|---|
| 5 → 10 | +5 | **2.08** |
| 10 → 20 | +10 | **1.06** |

**Qué decir:**
> "Más camas no curan mejor: **acortan el tiempo de espera**, y eso es lo que
> salva vidas. Y las primeras camas rinden el doble que las últimas: sacar a un
> sistema del colapso vale más que optimizar uno que ya funciona."

---

## Diapositiva 6 — Conclusión y límites *(1:45-2:00)*

**En pantalla:**

**Respuesta:** más camas no evitan contagios, evitan **muertes evitables**,
reduciendo el tiempo sin atención. Pero ni con 20 camas el sistema deja de
saturarse: el pico de demanda es de 31 pacientes simultáneos.

**Límites:**
- Las probabilidades son parámetros del modelo, **no cifras clínicas reales**
- Única regla de asignación: orden de llegada
- 5 repeticiones: alcanza para la tendencia, no para afirmaciones finas

**Qué decir:**
> "Para dimensionar un sistema que nunca se sature harían falta más de 31
> camas: más del 10% de la población. Y aclaramos que las probabilidades son
> parámetros del modelo, no datos clínicos: lo que estudiamos es el efecto de
> un recurso limitado, no una enfermedad real."

---

## Reparto sugerido (2 personas)

| Quien | Diapositivas |
|---|---|
| Persona A (lógica) | 1, 2, 5 — el modelo, la pregunta y el mecanismo |
| Persona B (visualización/datos) | 3, 4, 6 — la demo, los resultados y el cierre |

## Si hay preguntas

- **"¿Por qué 5 repeticiones y no una?"** → Porque con una sola el azar
  invierte la conclusión: con la semilla 46, 10 camas dio más muertos que 5.
- **"¿Por qué la epidemia dura más con más camas?"** → Porque muere menos
  gente, quedan más personas vivas circulando y contagiándose.
- **"¿De dónde salen las probabilidades?"** → Son parámetros configurables
  elegidos por nosotros, no cifras clínicas. El objetivo es estudiar el efecto
  de un recurso limitado.
- **"¿Cómo se asignan las camas?"** → Orden de llegada, cola FIFO. Otras
  reglas están explícitamente fuera de alcance.
