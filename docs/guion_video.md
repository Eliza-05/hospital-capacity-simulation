# Guion del video demo (2 minutos)

Lo que pide el profesor mostrar: **la simulación corriendo, cambiar camas en
vivo, la saturación, y el Excel generado.**

## Antes de grabar — checklist

- [ ] `pip install -r requirements.txt` en un entorno limpio.
- [ ] `python main.py --comparar` ya ejecutado, con
      `resultados/comparacion_camas.xlsx` abierto en otra ventana y
      **posicionado en la hoja `promedios`** (para no perder tiempo buscándola).
- [ ] Ventana de la simulación en primer plano, tamaño 1060x600.
- [ ] Grabar pantalla completa o solo la ventana, pero que el panel de la
      derecha se lea bien: **es donde están todos los contadores**.

> La demo usa semilla fija (42), así que la corrida es siempre la misma: podés
> ensayar y saber exactamente en qué ciclo pasa cada cosa.

---

## Minutado

### 0:00 – 0:20 · El caso y la pregunta

*(Pantalla: la simulación recién arrancada, `python main.py`)*

> "Simulamos una epidemia con agentes. Cada punto es una persona: **azul**
> sana, **naranja** infectada, **roja** grave —necesita cama de hospital—,
> **verde** recuperada y **morada** fallecida. El hospital tiene camas
> limitadas y una lista de espera por orden de llegada.
> La pregunta que estudiamos es: **¿cómo cambia la mortalidad cuando la
> demanda de camas supera la oferta?**"

**Acción:** apretar `→` dos o tres veces para subir la velocidad a x3 o x4
mientras hablás, así la epidemia arranca.

---

### 0:20 – 0:50 · La simulación corriendo y la saturación

*(Pantalla: alrededor del ciclo 100-150, el hospital ya saturado)*

> "El panel de la derecha muestra los ocho contadores en tiempo real.
> Fíjense en los graves: los que tienen **aro blanco** consiguieron cama, los
> que tienen **aro amarillo** están en la lista de espera, sin atención."

**Acción:** señalar la barra de ocupación de camas cuando se pone roja y el
cartel **HOSPITAL SATURADO** arriba.

> "Acá el hospital ya está saturado. Cero camas libres y 16 personas graves
> esperando. Y este es el punto del trabajo: **cada ciclo que un paciente pasa
> en esa lista aumenta su probabilidad de morir.**"

---

### 0:50 – 1:15 · Los controles en vivo

**Acción:** apretar `ESPACIO` para pausar.

> "Podemos pausar en cualquier momento…"

**Acción:** apretar `↑` unas 10-15 veces seguidas. Se ve cómo los aros
amarillos se convierten en blancos y la lista de espera baja.

> "…y cambiar la capacidad del hospital en vivo. Al subir las camas, los
> pacientes que estaban esperando entran automáticamente, respetando el orden
> de llegada. Miren cómo el cartel de saturado desaparece."

**Acción:** apretar `↓` varias veces hasta que el control se **niegue** a bajar.

> "Y bajar camas solo se permite hasta la cantidad ya ocupada: el sistema no
> deja dejar pacientes hospitalizados en un estado inconsistente."

**Acción:** `ESPACIO` para reanudar, `→` para acelerar.

---

### 1:15 – 1:45 · Los resultados en Excel

*(Pantalla: cambiar a `comparacion_camas.xlsx`, hoja `promedios`)*

> "Para responder la pregunta corrimos tres escenarios —5, 10 y 20 camas—
> cinco veces cada uno, con las mismas semillas aleatorias, cambiando
> únicamente el número de camas."

**Acción:** señalar la fila de `fallecidos` en los gráficos de barras.

> "Con 5 camas mueren 34 personas en promedio. Con 20, mueren 13: **un 62%
> menos.** Y el hospital pasa de estar saturado el 66% del tiempo, al 14%."

**Acción:** señalar la columna `pico_graves`.

> "Lo interesante es que el pico de pacientes graves es el mismo en los tres
> casos: **31**. La misma cantidad de gente se enferma. Lo que cambia es
> cuántos alcanzan a ser atendidos."

---

### 1:45 – 2:00 · Cierre

*(Pantalla: hoja `promedios` o una de las `timeline_run_N` con su gráfico)*

> "La conclusión: más camas no evitan que la gente se enferme, **reducen el
> tiempo que un paciente grave pasa sin atención** —de 28 ciclos a 10—, y eso
> es lo que salva vidas. Pero ni siquiera con 20 camas el sistema deja de
> saturarse: el pico de demanda es de 31 pacientes simultáneos."

---

## Plan B si algo falla en vivo

- **La ventana no abre / pygame falla:** grabar sobre capturas de pantalla
  ya tomadas y narrar encima.
- **La epidemia se apaga temprano:** no debería (semilla fija), pero si pasa,
  cerrar y volver a correr; o bajar camas con `↓` para forzar saturación.
- **Te pasás de 2 minutos:** el tramo más recortable es el de los controles
  (0:50-1:15); mostrá solo `↑` y salteá el `↓`.
