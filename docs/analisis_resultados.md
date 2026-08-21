# Análisis de resultados — ¿cómo afecta la capacidad hospitalaria?

**Pregunta de decisión:** ¿cómo afecta la capacidad hospitalaria (número de
camas) a la mortalidad, la saturación del sistema y la cantidad de pacientes
sin atención durante una epidemia?

**Evidencia:** `resultados/comparacion_camas.xlsx`, hoja `promedios`.
Reproducible con `python main.py --comparar`.

---

## 1. Cómo se obtuvieron los datos

Tres escenarios que se diferencian **únicamente** en el número de camas
(5 / 10 / 20). Todo lo demás —población, contagiosidad, duración de la
infección, probabilidad de gravedad, mortalidades— es idéntico:

| Parámetro | Valor |
|---|---|
| Población | 300 |
| Infectados iniciales | 5 |
| Probabilidad de contagio por contacto | 0.10 |
| Radio de contagio | 45 |
| % que desarrolla gravedad | 30% |
| Duración de la infección | 60 ciclos |
| Duración de la gravedad | 40 ciclos |
| Mortalidad con cama todo el periodo | 0.15 |
| Mortalidad sin cama en ningún momento | 0.60 |

Cada escenario se corrió **5 veces** con las semillas 42 a 46, **las mismas
cinco para las tres capacidades**, y se compararon los promedios. Esto no es
un detalle: en la corrida individual de la semilla 46 el escenario de 10
camas dio *más* muertos que el de 5 (25 contra 23), y con la semilla 99 pasó
lo mismo de forma más marcada. Con una sola corrida por escenario el azar
alcanza para invertir la conclusión del trabajo.

---

## 2. Resultados

| | 5 camas | 10 camas | 20 camas |
|---|---|---|---|
| **Fallecidos** | **34.0** | **23.6** | **13.0** |
| Mortalidad sobre la población | 11% | 8% | 4% |
| Letalidad entre contagiados | 12% | 8% | 5% |
| Contagiados totales | 275.8 | 281.6 | 287.2 |
| Pico de pacientes graves simultáneos | 31.0 | 31.4 | 31.0 |
| Pico de pacientes sin cama | 26.0 | 21.4 | 11.0 |
| Personas que esperaron cama | 73.2 | 63.8 | 24.8 |
| Espera promedio (ciclos) | 28.4 | 19.1 | 9.8 |
| Espera acumulada (persona-ciclo) | 2120 | 1227 | 296 |
| **% del tiempo con el hospital saturado** | **66%** | **54%** | **14%** |

---

## 3. Respuesta a la pregunta de decisión

### 3.1 La capacidad no cambia cuánta gente se enferma, cambia cuánta se muere

El dato más importante de la tabla es que **el pico de pacientes graves es
prácticamente idéntico en los tres escenarios** (31.0 / 31.4 / 31.0). La
epidemia genera la misma demanda de camas sin importar cuántas haya: agregar
camas no evita que la gente se enferme ni se agrave.

Lo que cambia es **cuántos de esos pacientes reciben atención**. Pasar de 5 a
20 camas reduce los fallecidos de 34 a 13, un **62% menos de muertes**, con
exactamente la misma cantidad de gente enfermándose.

Dicho de otro modo: en este modelo la capacidad hospitalaria no es una
herramienta de prevención, es una herramienta de **supervivencia**.

### 3.2 El mecanismo: el tiempo sin atención

La cadena causal que conecta las camas con la mortalidad se ve en una sola
fila de la tabla: **la espera promedio**.

La gravedad dura 40 ciclos. Con 5 camas, un paciente grave pasa en promedio
**28.4 de esos 40 ciclos sin cama** — el 71% de su periodo crítico sin
atención. Con 20 camas, la espera baja a 9.8 ciclos, el 25%.

Como el riesgo de morir se calcula según qué fracción del periodo crítico se
pasó sin atención, esa diferencia de tiempo de espera es exactamente lo que
se traduce en la diferencia de fallecidos. Más camas no curan mejor: **acortan
el tiempo que un paciente pasa esperando**.

### 3.3 La saturación no desaparece, ni siquiera con 20 camas

Con 20 camas el hospital sigue saturado el **14% del tiempo**, y todavía hay
un pico de 11 pacientes sin cama. Cuadruplicar la capacidad respecto del peor
escenario **no elimina** el problema, solo lo reduce.

La razón está en la misma tabla: el pico de demanda es de ~31 pacientes
graves simultáneos. Con 20 camas se cubre el 65% del peor momento; con 5, el
16%. Dimensionar el sistema para no saturarse nunca exigiría más de 31 camas,
es decir más del 10% de la población total.

### 3.4 Rendimientos decrecientes: las primeras camas valen más

| Ampliación | Camas agregadas | Muertes evitadas | Muertes evitadas por cama |
|---|---|---|---|
| 5 → 10 | +5 | 10.4 | **2.08** |
| 10 → 20 | +10 | 10.6 | **1.06** |

Ambas ampliaciones evitan aproximadamente la misma cantidad de muertes (~10),
pero la segunda cuesta el doble de camas. **La primera cama que se agrega a un
sistema colapsado vale el doble que la que se agrega a uno que ya funciona
razonablemente.**

Si la decisión fuera dónde invertir un presupuesto limitado, la respuesta del
modelo es clara: **sacar a un sistema de la saturación extrema rinde mucho
más que optimizar uno que ya está cerca de cubrir la demanda.**

### 3.5 Un efecto contraintuitivo

Los contagiados totales **suben** levemente con más camas (275.8 → 287.2) y
la epidemia **dura más** (296 → 366 ciclos). No es un error: al morir menos
gente, quedan más personas vivas circulando y contagiándose. Salvar vidas
alarga la epidemia. Es un buen recordatorio de que optimizar una métrica
(muertes) puede empeorar otra (duración, contagios totales).

---

## 4. Respuesta corta

> **Con la misma epidemia y la misma cantidad de enfermos, pasar de 5 a 20
> camas reduce las muertes un 62% (34 → 13) y el tiempo de saturación del 66%
> al 14%. El mecanismo es el tiempo de espera: con 5 camas un paciente grave
> pasa el 71% de su periodo crítico sin atención, contra el 25% con 20 camas.
> Aun así, ni con 20 camas el sistema deja de saturarse, y las primeras camas
> que se agregan salvan el doble de vidas por cama que las últimas.**

---

## 5. Limitaciones

Honestidad sobre qué **no** se puede concluir de estos números:

- **Las probabilidades son parámetros del modelo, no cifras clínicas.** El
  0.15 / 0.60 de mortalidad con y sin cama se eligió para estudiar el efecto
  de un recurso limitado, no para representar ninguna enfermedad real. Los
  porcentajes de reducción dependen de esa elección.
- **La única regla de asignación es orden de llegada (FIFO).** Otras reglas
  (priorizar a quien tiene más chances de sobrevivir, por ejemplo) podrían dar
  resultados distintos con la misma cantidad de camas. Está fuera de alcance.
- **5 repeticiones son pocas.** Alcanzan para que la tendencia se sostenga,
  pero la dispersión sigue siendo grande (con 5 camas los fallecidos fueron
  entre 23 y 43 según la semilla). Para afirmaciones más finas —por ejemplo
  "12 camas es mejor que 11"— harían falta muchas más corridas.
- **El hospital es abstracto:** un contador de camas, sin médicos,
  ventiladores, ni traslados. La cama es el único recurso escaso del modelo.
- **La mortalidad interpolada según el tiempo sin atención** es un supuesto
  del modelo (ver `TODO.md`, sección "Corrección del modelo de mortalidad").
  Con la regla binaria original —mirar solo si el paciente tenía cama en el
  instante exacto en que vencía su temporizador— la capacidad no tenía
  **ningún** efecto sobre la mortalidad, que era un artefacto de modelado.
