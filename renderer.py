"""Renderizado de la simulación: mapa, hospital, gráficos y panel.

Este módulo es el único que sabe cómo se ve la simulación. `Simulation`
le pasa su estado y el renderer devuelve un frame completo dibujado
sobre un lienzo de tamaño fijo (`theme.CANVAS_WIDTH` x `CANVAS_HEIGHT`)
que después se escala a la ventana real.

La idea central es que la pantalla cuente una historia sin que haga
falta leer el código: la comunidad a la izquierda, el hospital a la
derecha con sus camas dibujadas una por una, y animaciones explícitas
para cada cosa que le pasa a un paciente (ingresa, pasa a cama, espera,
recibe el alta o fallece). Para lograrlo el renderer mantiene su propio
estado visual —qué persona ocupa qué cama, qué traslados están en curso,
qué pasó en los últimos ciclos— y lo actualiza comparando el estado
actual de la simulación con el del frame anterior. Así la lógica del
modelo queda intacta: no necesita avisar nada, el renderer se da cuenta.
"""

import math
import os
from collections import deque

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

import theme as T
from theme import CANVAS_HEIGHT, CANVAS_WIDTH

# ----------------------------------------------------------------------
# Distribución de la pantalla
# ----------------------------------------------------------------------

# Todas las medidas son sobre el lienzo lógico, nunca sobre la ventana.
HEADER = pygame.Rect(0, 0, CANVAS_WIDTH, 66)
FIELD = pygame.Rect(18, 80, 620, 465)       # mapa de la comunidad
CHART = pygame.Rect(18, 559, 620, 283)      # curvas de la epidemia
HOSPITAL = pygame.Rect(652, 80, 430, 762)   # planta del hospital
PANEL = pygame.Rect(1096, 80, 326, 762)     # panel de indicadores

# Bloques del panel lateral, de arriba hacia abajo.
CARD_POP = pygame.Rect(1096, 80, 326, 214)
CARD_HOSP = pygame.Rect(1096, 302, 326, 170)
CARD_LOG = pygame.Rect(1096, 480, 326, 186)
CARD_CTRL = pygame.Rect(1096, 674, 326, 168)

# Zonas internas del hospital.
BEDS_AREA = pygame.Rect(666, 182, 402, 436)
WAIT_AREA = pygame.Rect(666, 652, 402, 176)

# Puerta de ingreso: por acá "entran" visualmente los traslados.
DOOR = (HOSPITAL.left, HOSPITAL.top + 300)

# ----------------------------------------------------------------------
# Ajustes de animación
# ----------------------------------------------------------------------

BED_GAP = 8
BED_ASPECT = 1.5          # relación ancho/alto de una cama dibujada
BED_MAX_WIDTH = 132
# Con muchas camas cada una queda chica y el detalle deja de entrar. En
# vez de dibujar texto encimado, se pasa a versiones más simples.
BED_DETAIL_FULL = 100     # número, tiempo restante, paciente y monitor
BED_DETAIL_MEDIUM = 58    # número y paciente, sin monitor ni textos

QUEUE_COLS = 8
QUEUE_ROWS = 3
QUEUE_SLOTS = QUEUE_COLS * QUEUE_ROWS

# Ritmo de las animaciones, en frames (la ventana corre a config.FPS).
#
# En el pico de la epidemia se agravan, ingresan y reciben el alta varios
# pacientes por ciclo. Animar cada uno por separado llenaba la pantalla de
# tokens cruzándose y no se entendía nada. La solución no es alargar cada
# animación (eso aumenta cuántas se superponen) sino agrupar: mientras un
# traslado de cierto tipo está en curso, los siguientes del mismo tipo se
# suman a él y el token muestra un contador. Así la cantidad de cosas
# moviéndose queda acotada y cada una puede ser lenta y legible.
TRANSFER_FRAMES = 54      # duración base de un traslado a velocidad x1
TRANSFER_FRAMES_MIN = 18  # piso al acelerar, para que siga siendo legible
TRANSFER_MERGE_UNTIL = 0.55  # hasta qué avance un token sigue absorbiendo
TRANSFER_STAGGER = 5      # retraso que se suma a cada traslado de una tanda
TRANSFER_STAGGER_MAX = 20 # tope del retraso, para no atrasarse demasiado
MAX_TRANSFERS = 24        # red de seguridad; con la fusión no debería tocarse

LOG_LINES = 5             # entradas visibles del registro de eventos
LOG_MEMORY = 40

FLASH_FRAMES = 24         # duración del destello de un contagio
TOAST_FRAMES = 56         # duración de los carteles flotantes
BED_ANIM_FRAMES = 32      # alta/baja de camas

# Etiqueta, color y glifo de cada tipo de traslado. El glifo es lo que
# se dibuja dentro del token que viaja por la pantalla.
TRANSFER_STYLES = {
    "admit_bed": ("INGRESA A CAMA", T.BED_OCCUPIED, "+"),
    "admit_queue": ("SIN CAMA: ESPERA", T.WAITING, "!"),
    "queue_to_bed": ("PASA A CAMA", T.OK, "+"),
    "bed_to_bed": ("CAMBIO DE CAMA", T.INFO, ">"),
    "discharge_recovered": ("ALTA: RECUPERADO", T.OK, "v"),
    "discharge_dead": ("FALLECE", T.STATE_COLORS["dead"], "x"),
    "leave_queue_recovered": ("ALTA SIN CAMA", T.OK, "v"),
    "leave_queue_dead": ("FALLECE ESPERANDO", T.DANGER, "x"),
}


def _bezier(p0, c, p1, t):
    """Punto de una curva cuadrática. Los traslados siguen un arco en vez
    de una recta: se lee mejor de dónde sale y a dónde va cada paciente."""
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0],
            u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1])


def _arc_control(start, end, bend_ratio=0.22, bend_max=70):
    """Punto de control del arco: el medio del trayecto, desplazado en
    perpendicular para que la curva se abra hacia afuera."""
    mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return (mx, my)
    bend = min(length * bend_ratio, bend_max)
    return (mx - dy / length * bend, my + dx / length * bend)


class Transfer:
    """Un paciente viajando entre dos puntos de la pantalla.

    Guarda el punto de salida ya congelado y una forma de calcular el
    destino en cada frame: cuando alguien recibe el alta vuelve a la
    comunidad, y ahí el destino es una persona que sigue moviéndose.

    `delay` retrasa el arranque unos frames. Cuando en un mismo ciclo se
    mueven varios pacientes a la vez, salen escalonados en vez de todos
    juntos, que es lo que hacía que la pantalla se volviera un caos."""

    def __init__(self, kind, start, end_fn, frames, delay=0):
        self.kind = kind
        self.start = start
        self.end_fn = end_fn
        self.frames = max(frames, 4)
        self.delay = delay
        # Cuántos pacientes representa este token. Sube cuando otro
        # traslado del mismo tipo se suma en vez de crear uno nuevo.
        self.count = 1
        self.age = 0
        self.end = end_fn()
        self.control = _arc_control(self.start, self.end)

    @property
    def started(self):
        return self.delay <= 0

    @property
    def absorbs(self):
        """Si todavía puede representar a un paciente más. Un token que
        ya está por llegar no absorbe: se vería aparecer el contador
        justo cuando el traslado termina."""
        return self.progress < TRANSFER_MERGE_UNTIL

    @property
    def progress(self):
        return min(self.age / self.frames, 1.0)

    @property
    def done(self):
        return self.started and self.age >= self.frames

    def advance(self):
        """Avanza un frame y recalcula el arco hacia el destino actual."""
        self.end = self.end_fn()
        self.control = _arc_control(self.start, self.end)
        if not self.started:
            self.delay -= 1
            return
        self.age += 1

    def position(self, offset=0.0):
        """Posición sobre el arco, con `offset` para dibujar la estela."""
        t = T.ease_in_out(min(max(self.progress - offset, 0.0), 1.0))
        return _bezier(self.start, self.control, self.end, t)


class Renderer:
    """Dibuja la simulación y mantiene el estado visual entre frames."""

    def __init__(self):
        self.canvas = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
        self.frame = 0

        # Asignación de camas. La lógica solo cuenta cuántas están
        # ocupadas; acá se decide en qué cama concreta va cada paciente
        # para poder dibujarlo siempre en el mismo lugar.
        self.bed_of = {}
        self.slot_of = {}

        # Animaciones en curso.
        self.transfers = []
        self.flashes = []      # destellos de contagio en el mapa
        self.toasts = []       # carteles flotantes sobre el hospital
        self.bed_anims = {}    # camas apareciendo o desapareciendo

        self.log = deque(maxlen=LOG_MEMORY)

        # Estado del frame anterior, base de todas las comparaciones.
        self._prev_hospitalized = set()
        self._prev_waiting = []
        self._prev_infected = set()
        self._prev_capacity = None
        self._prev_saturated = False
        self._prev_history_len = 0

        self._burst = 0
        self._chart_cache = None
        self._chart_key = None
        self._glyph_cache = {}
        self._synced = False

    # ------------------------------------------------------------------
    # Geometría dependiente del estado
    # ------------------------------------------------------------------

    def field_pos(self, sim, person):
        """Pasa las coordenadas del modelo a píxeles del mapa."""
        sx = FIELD.width / sim.width if sim.width else 0
        sy = FIELD.height / sim.height if sim.height else 0
        return (FIELD.x + person.x * sx, FIELD.y + person.y * sy)

    def bed_layout(self, capacity):
        """Elige cuántas columnas usar y de qué tamaño dibujar cada cama.

        Prueba todas las grillas razonables y se queda con la que da la
        cama más grande, de modo que con 5 camas se vean enormes y con 40
        sigan entrando todas sin desbordar la sala."""
        if capacity <= 0:
            return 0, 0, 0, 0

        best = None
        for cols in range(1, 9):
            rows = math.ceil(capacity / cols)
            cell_w = (BEDS_AREA.width - (cols - 1) * BED_GAP) / cols
            cell_h = (BEDS_AREA.height - (rows - 1) * BED_GAP) / rows
            if cell_w < 26 or cell_h < 20:
                continue
            width = min(cell_w, cell_h * BED_ASPECT, BED_MAX_WIDTH)
            if best is None or width > best[0]:
                best = (width, cols, rows, min(cell_h, width / BED_ASPECT))
        if best is None:
            return 0, 0, 0, 0

        width, cols, rows, height = best
        return cols, rows, width, height

    def bed_rect(self, slot, capacity):
        """Rectángulo de una cama concreta dentro de la sala."""
        cols, _, width, height = self.bed_layout(capacity)
        if cols == 0:
            return pygame.Rect(BEDS_AREA.x, BEDS_AREA.y, 1, 1)
        col, row = slot % cols, slot // cols
        # Se centra en horizontal, pero se ancla arriba: así la primera
        # fila queda siempre justo debajo del título de la sala.
        total_w = cols * width + (cols - 1) * BED_GAP
        x0 = BEDS_AREA.x + (BEDS_AREA.width - total_w) / 2
        y0 = BEDS_AREA.y
        return pygame.Rect(int(x0 + col * (width + BED_GAP)),
                           int(y0 + row * (height + BED_GAP)),
                           int(width), int(height))

    def bed_center(self, slot, capacity):
        return self.bed_rect(slot, capacity).center

    def queue_rect(self, index):
        """Rectángulo de un lugar de la sala de espera."""
        cell_w = WAIT_AREA.width / QUEUE_COLS
        cell_h = WAIT_AREA.height / QUEUE_ROWS
        col, row = index % QUEUE_COLS, index // QUEUE_COLS
        return pygame.Rect(int(WAIT_AREA.x + col * cell_w),
                           int(WAIT_AREA.y + row * cell_h),
                           int(cell_w) - 4, int(cell_h) - 6)

    def queue_center(self, index):
        if index >= QUEUE_SLOTS:
            # A los que no entran en la grilla se los apunta al final de
            # la sala, así el traslado igual termina en un lugar sensato.
            return (WAIT_AREA.centerx, WAIT_AREA.bottom - 12)
        return self.queue_rect(index).center

    # ------------------------------------------------------------------
    # Sincronización: detectar qué cambió desde el frame anterior
    # ------------------------------------------------------------------

    def sync(self, sim):
        """Compara el estado actual con el anterior y genera animaciones,
        entradas del registro y reasignaciones de cama."""
        hospital = sim.hospital
        capacity = hospital.capacity
        # Traslados creados en esta pasada: define cuánto se escalona
        # cada uno para que la tanda no salga toda de golpe.
        self._burst = 0

        if not self._synced:
            # Primera pasada: se adopta el estado tal cual está, sin
            # animar nada. Evita una avalancha de traslados si se empieza
            # a dibujar una simulación ya avanzada.
            self._adopt(sim)
            return

        self._sync_capacity(sim, capacity)
        self._sync_beds(sim, capacity)
        self._sync_queue(sim)
        self._sync_infections(sim)
        self._sync_saturation(sim)
        self._reconcile_beds(sim, capacity)

        self._prev_hospitalized = {p for p in sim.people if p.hospitalized}
        self._prev_waiting = list(hospital.waiting_list)
        self._prev_infected = {p for p in sim.people
                               if p.state == "infected"}
        self._prev_capacity = capacity
        self._prev_saturated = hospital.is_saturated

    def _adopt(self, sim):
        """Toma el estado actual como punto de partida."""
        for person in sim.people:
            if person.hospitalized:
                self._assign_slot(person, sim.hospital.capacity)
        self._prev_hospitalized = {p for p in sim.people if p.hospitalized}
        self._prev_waiting = list(sim.hospital.waiting_list)
        self._prev_infected = {p for p in sim.people if p.state == "infected"}
        self._prev_capacity = sim.hospital.capacity
        self._prev_saturated = sim.hospital.is_saturated
        self._synced = True

    def _assign_slot(self, person, capacity):
        """Le da a un paciente la cama libre de número más bajo."""
        for slot in range(capacity):
            if slot not in self.slot_of:
                self.slot_of[slot] = person
                self.bed_of[person] = slot
                return slot
        return None

    def _release_slot(self, person):
        slot = self.bed_of.pop(person, None)
        if slot is not None and self.slot_of.get(slot) is person:
            del self.slot_of[slot]
        return slot

    def _sync_capacity(self, sim, capacity):
        """Registra altas y bajas de camas y reubica a quien quedó fuera
        de rango cuando se achicó el hospital."""
        previous = self._prev_capacity
        if previous is None or capacity == previous:
            return

        if capacity > previous:
            for slot in range(previous, capacity):
                self.bed_anims[slot] = ["add", 0]
            self._event("+", f"Se habilitan {capacity - previous} cama(s) "
                             f"(total {capacity})", T.OK)
            self._toast(self.bed_center(previous, capacity),
                        f"+{capacity - previous} CAMA", T.OK)
        else:
            for slot in range(capacity, previous):
                rect = self.bed_rect(slot, previous)
                self.bed_anims[f"ghost{slot}"] = ["remove", 0, rect]
            self._event("-", f"Se retiran {previous - capacity} cama(s) "
                             f"(total {capacity})", T.DANGER)
            self._toast(self.bed_rect(capacity, previous).center,
                        f"-{previous - capacity} CAMA", T.DANGER)

            # Quien haya quedado en una cama que ya no existe se muda a
            # una libre; el hospital garantiza que siempre hay lugar.
            for slot in sorted(s for s in list(self.slot_of)
                               if s >= capacity):
                person = self.slot_of[slot]
                origin = self.bed_center(slot, previous)
                self._release_slot(person)
                new_slot = self._assign_slot(person, capacity)
                if new_slot is not None:
                    self._transfer("bed_to_bed", origin,
                                   lambda s=new_slot: self.bed_center(
                                       s, sim.hospital.capacity), sim)

    def _sync_beds(self, sim, capacity):
        """Detecta ingresos a cama y altas.

        Las altas se procesan primero: liberan camas que en ese mismo
        ciclo pueden ocupar quienes ingresan. Al revés, con el hospital
        lleno, un ingreso no encontraría lugar y el paciente quedaría
        internado pero sin cama dibujada."""
        current = {p for p in sim.people if p.hospitalized}

        for person in self._prev_hospitalized - current:
            slot = self._release_slot(person)
            origin = (self.bed_center(slot, capacity) if slot is not None
                      else DOOR)
            recovered = person.state == "recovered"
            kind = "discharge_recovered" if recovered else "discharge_dead"
            self._transfer(kind, origin,
                           lambda p=person: self.field_pos(sim, p), sim)
            cama = f"la cama {slot + 1:02d}" if slot is not None else "el hospital"
            self._event("v" if recovered else "x",
                        f"Alta de {cama}: recuperado" if recovered
                        else f"Fallece en {cama}",
                        T.OK if recovered else T.STATE_COLORS["dead"])
            # Antes acá salía un cartel "FALLECE" sobre la cama. Con
            # varias muertes seguidas se apilaban y tapaban a los
            # pacientes que seguían internados; el token que sale de la
            # cama, con su contador, cuenta lo mismo sin ensuciar la sala.

        for person in current - self._prev_hospitalized:
            was_waiting = person in self._prev_waiting
            origin = (self.queue_center(self._prev_waiting.index(person))
                      if was_waiting else self.field_pos(sim, person))
            slot = self.bed_of.get(person)
            if slot is None:
                slot = self._assign_slot(person, capacity)
            if slot is None:
                continue
            kind = "queue_to_bed" if was_waiting else "admit_bed"
            self._transfer(kind, origin,
                           lambda s=slot: self.bed_center(
                               s, sim.hospital.capacity), sim)
            self._event("+", f"Paciente {'pasa a' if was_waiting else 'ingresa a'} "
                             f"la cama {slot + 1:02d}",
                        T.OK if was_waiting else T.BED_OCCUPIED)

    def _reconcile_beds(self, sim, capacity):
        """Red de seguridad: deja el mapa de camas del renderer igual a lo
        que dice el hospital.

        Las comparaciones de arriba cubren el caso normal, pero si varios
        ciclos entran en un mismo frame puede quedar alguna cama tomada
        por quien ya salió. Sin esto, esa cama se vería ocupada para
        siempre y el próximo paciente no tendría dónde acostarse."""
        for slot, person in list(self.slot_of.items()):
            if slot >= capacity or not person.hospitalized:
                self._release_slot(person)
        for person in sim.people:
            if person.hospitalized and person not in self.bed_of:
                self._assign_slot(person, capacity)

    def _sync_queue(self, sim):
        """Detecta quién entra a la sala de espera y quién la abandona
        sin haber llegado nunca a una cama."""
        current = list(sim.hospital.waiting_list)
        current_set = set(current)
        previous_set = set(self._prev_waiting)

        for person in current:
            if person in previous_set:
                continue
            index = current.index(person)
            self._transfer("admit_queue", self.field_pos(sim, person),
                           lambda i=index: self.queue_center(i), sim)
            self._event("!", "Paciente grave sin cama: entra en espera",
                        T.WAITING)

        for person in previous_set - current_set:
            if person.hospitalized or person.state == "grave":
                continue  # consiguió cama: ya lo maneja _sync_beds
            origin = self.queue_center(self._prev_waiting.index(person))
            recovered = person.state == "recovered"
            kind = ("leave_queue_recovered" if recovered
                    else "leave_queue_dead")
            self._transfer(kind, origin,
                           lambda p=person: self.field_pos(sim, p), sim)
            self._event("v" if recovered else "x",
                        "Se recupera sin haber tenido cama" if recovered
                        else "Fallece esperando una cama",
                        T.OK if recovered else T.DANGER)

    def _sync_infections(self, sim):
        """Marca con un destello a quien se contagió en este ciclo."""
        current = {p for p in sim.people if p.state == "infected"}
        for person in current - self._prev_infected:
            self.flashes.append([self.field_pos(sim, person), 0])
        # Con muchos contagios simultáneos alcanza con mostrar los
        # últimos: dibujarlos todos taparía el mapa.
        if len(self.flashes) > 120:
            del self.flashes[:-120]

    def _sync_saturation(self, sim):
        saturated = sim.hospital.is_saturated
        if saturated == self._prev_saturated:
            return
        if saturated:
            self._event("!", "HOSPITAL SATURADO: no quedan camas", T.DANGER)
        else:
            self._event("v", "El hospital vuelve a tener camas libres", T.OK)

    # ------------------------------------------------------------------
    # Alta de animaciones
    # ------------------------------------------------------------------

    def _transfer(self, kind, start, end_fn, sim):
        """Crea un traslado.

        Si ya hay un traslado de este mismo tipo empezado hace poco, el
        paciente se suma a ese token en lugar de crear otro: es lo que
        evita que el pico de la epidemia llene la pantalla. El registro
        lateral sí lista cada caso por separado, con su número de cama.

        Al acelerar la simulación los traslados se acortan (si no, se
        acumularían tokens de ciclos viejos), pero nunca por debajo de
        `TRANSFER_FRAMES_MIN`, para que se sigan pudiendo seguir con la
        vista. Dentro de un mismo ciclo cada traslado sale un poco
        después que el anterior."""
        for existente in self.transfers:
            if existente.kind == kind and existente.absorbs:
                existente.count += 1
                return

        frames = max(int(TRANSFER_FRAMES / math.sqrt(max(sim.speed, 1))),
                     TRANSFER_FRAMES_MIN)
        delay = min(self._burst * TRANSFER_STAGGER, TRANSFER_STAGGER_MAX)
        self._burst += 1
        self.transfers.append(Transfer(kind, start, end_fn, frames, delay))
        if len(self.transfers) > MAX_TRANSFERS:
            del self.transfers[:-MAX_TRANSFERS]

    def _toast(self, position, label, color):
        """Cartel flotante. Queda reservado para los cambios de capacidad,
        que los provoca el usuario y son puntuales: los eventos de los
        pacientes se cuentan con los tokens y el registro lateral."""
        self.toasts.append([list(position), label, color, 0])
        if len(self.toasts) > 6:
            del self.toasts[:-6]

    def _event(self, icon, text, color):
        self.log.appendleft([icon, text, color, self.frame])

    def _advance_animations(self):
        """Hace correr un frame de todo lo que está animándose."""
        for transfer in self.transfers:
            transfer.advance()
        self.transfers = [t for t in self.transfers if not t.done]

        for flash in self.flashes:
            flash[1] += 1
        self.flashes = [f for f in self.flashes if f[1] < FLASH_FRAMES]

        for toast in self.toasts:
            toast[3] += 1
        self.toasts = [t for t in self.toasts if t[3] < TOAST_FRAMES]

        for key in list(self.bed_anims):
            anim = self.bed_anims[key]
            anim[1] += 1
            if anim[1] >= BED_ANIM_FRAMES:
                del self.bed_anims[key]

    # ------------------------------------------------------------------
    # Dibujo: encabezado
    # ------------------------------------------------------------------

    def _phase(self, sim):
        """Resume en dos palabras en qué momento está la epidemia, para
        que se entienda la curva sin tener que interpretarla."""
        if sim.is_finished() and sim.people:
            return "EPIDEMIA TERMINADA", T.STATE_COLORS["recovered"]
        if len(sim.history) < 12:
            return "BROTE INICIAL", T.WAITING

        def active(record):
            return record["infected"] + record["grave"]

        now = active(sim.history[-1])
        before = active(sim.history[-12])
        umbral = max(sim.population * 0.01, 1)
        if now - before > umbral:
            return "EN EXPANSION", T.STATE_COLORS["infected"]
        if before - now > umbral:
            return "EN DESCENSO", T.INFO
        return "EN SU PICO", T.DANGER

    def _draw_header(self, surface, sim):
        pygame.draw.rect(surface, T.SURFACE, HEADER)
        pygame.draw.line(surface, T.BORDER, (0, HEADER.bottom - 1),
                         (CANVAS_WIDTH, HEADER.bottom - 1), 1)

        T.text(surface, "h1", "Capacidad hospitalaria durante una epidemia",
               (18, 12))
        T.text(surface, "small",
               "Modelo epidemico basado en agentes  ·  la capacidad de camas "
               "decide quien se salva", (19, 40), T.TEXT_FAINT)

        # Las píldoras se acomodan de derecha a izquierda para que el
        # ancho de cada una no descoloque a las demás.
        x = CANVAS_WIDTH - 18
        estado = ("PAUSADO", T.WAITING) if sim.paused else \
            ("CORRIENDO", T.OK) if not sim.is_finished() else \
            ("FINALIZADO", T.TEXT_DIM)
        phase, phase_color = self._phase(sim)
        for label, color, filled in (
            (estado[0], estado[1], True),
            (f"VELOCIDAD x{sim.speed}", T.TEXT_DIM, False),
            (f"CICLO {sim.current_cycle}", T.INFO, False),
            (phase, phase_color, False),
        ):
            width = T.fonts()["tiny_b"].size(label.upper())[0] + 18
            x -= width
            T.chip(surface, (x, 22), label, color, filled)
            x -= 8

    # ------------------------------------------------------------------
    # Dibujo: mapa de la comunidad
    # ------------------------------------------------------------------

    def _draw_field(self, surface, sim):
        T.card(surface, FIELD, fill=(13, 17, 24), border=T.BORDER, radius=10)

        # Retícula tenue: da sensación de espacio y ayuda a percibir el
        # movimiento de los agentes.
        for gx in range(FIELD.x + 40, FIELD.right, 62):
            pygame.draw.line(surface, (19, 24, 33), (gx, FIELD.y + 2),
                             (gx, FIELD.bottom - 2), 1)
        for gy in range(FIELD.y + 40, FIELD.bottom, 62):
            pygame.draw.line(surface, (19, 24, 33), (FIELD.x + 2, gy),
                             (FIELD.right - 2, gy), 1)

        previous_clip = surface.get_clip()
        surface.set_clip(FIELD)

        self._draw_flashes(surface)
        self._draw_people(surface, sim)

        surface.set_clip(previous_clip)
        pygame.draw.rect(surface, T.BORDER, FIELD, width=1, border_radius=10)

        self._draw_field_legend(surface, sim)

    def _draw_people(self, surface, sim):
        """Dibuja a cada agente según su estado.

        Los graves no aparecen acá: están internados o esperando, y se
        los ve dentro del hospital. Eso hace que el mapa muestre solo a
        quien efectivamente circula por la comunidad."""
        infected_color = T.STATE_COLORS["infected"]
        # Con cientos de infectados los halos se funden en una mancha:
        # cuanto más hay, más tenue es cada uno.
        infected_total = sum(1 for p in sim.people if p.state == "infected")
        halo = 0.30 * min(max(70 / max(infected_total, 1), 0.30), 1.0)
        for person in sim.people:
            if person.state == "grave":
                continue

            x, y = self.field_pos(sim, person)
            position = (int(x), int(y))

            if person.state == "dead":
                # Una cruz apagada: no se mueve y no debe competir por la
                # atención con los vivos.
                color = T.shade(T.STATE_COLORS["dead"], 0.75)
                pygame.draw.line(surface, color, (position[0] - 3, position[1] - 3),
                                 (position[0] + 3, position[1] + 3), 2)
                pygame.draw.line(surface, color, (position[0] - 3, position[1] + 3),
                                 (position[0] + 3, position[1] - 3), 2)
                continue

            if person.state == "infected":
                T.blit_glow(surface, 11, infected_color, position, halo)
                T.dot(surface, position, 5, infected_color, (26, 18, 8), 1)
            elif person.state == "recovered":
                color = T.STATE_COLORS["recovered"]
                T.dot(surface, position, 4, T.shade(color, 0.55))
                T.dot(surface, position, 4, color, outline_width=1)
            else:
                T.dot(surface, position, 4, T.STATE_COLORS["susceptible"],
                      (14, 22, 38), 1)

    def _draw_flashes(self, surface):
        """Anillo que se expande donde acaba de ocurrir un contagio."""
        for (x, y), age in self.flashes:
            t = age / FLASH_FRAMES
            radius = int(4 + 14 * T.ease_in_out(t))
            alpha = int(235 * (1 - t) ** 1.4)
            if alpha <= 0:
                continue
            size = radius * 2 + 4
            layer = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(layer, (*T.STATE_COLORS["infected"], alpha),
                               (size // 2, size // 2), radius, 2)
            surface.blit(layer, (x - size // 2, y - size // 2))

    def _draw_field_legend(self, surface, sim):
        """Rótulo y leyenda superpuestos en el mapa, para que se entienda
        qué es cada punto sin mirar el panel."""
        strip = pygame.Rect(FIELD.x + 1, FIELD.y + 1, FIELD.width - 2, 30)
        T.alpha_rect(surface, strip, (10, 13, 19), 220, radius=9)
        T.text(surface, "h2", "COMUNIDAD", (FIELD.x + 12, FIELD.y + 9))

        x = FIELD.x + 118
        for state, label in (("susceptible", "sano"), ("infected", "infectado"),
                             ("recovered", "recuperado"), ("dead", "fallecido")):
            color = T.STATE_COLORS[state]
            T.dot(surface, (x, FIELD.y + 16), 4, color)
            rect = T.text(surface, "tiny", label, (x + 9, FIELD.y + 10),
                          T.TEXT_DIM)
            x = rect.right + 14

        note = pygame.Rect(FIELD.x + 1, FIELD.bottom - 25, FIELD.width - 2, 24)
        T.alpha_rect(surface, note, (10, 13, 19), 205, radius=9)
        graves = sum(1 for p in sim.people if p.state == "grave")
        nota = ("Ningun paciente grave en curso" if graves == 0 else
                f"{graves} graves fuera del mapa: internados o en espera")
        T.text(surface, "tiny", nota, (FIELD.x + 12, FIELD.bottom - 19),
               T.TEXT_FAINT)
        T.text(surface, "tiny_b", "HOSPITAL >",
               (FIELD.right - 12, FIELD.bottom - 19), T.STATE_COLORS["grave"],
               align="right")

    # ------------------------------------------------------------------
    # Dibujo: hospital
    # ------------------------------------------------------------------

    def _draw_hospital(self, surface, sim):
        hospital = sim.hospital
        T.card(surface, HOSPITAL, fill=T.SURFACE, border=T.BORDER, radius=10)

        # Encabezado del bloque.
        T.text(surface, "h1", "HOSPITAL", (HOSPITAL.x + 16, HOSPITAL.y + 12))
        T.text(surface, "tiny",
               "manta azul: entro directo  ·  manta roja: espero sin cama",
               (HOSPITAL.x + 17, HOSPITAL.y + 40), T.TEXT_FAINT)

        x = HOSPITAL.right - 16
        for label, color in ((f"{hospital.free_beds} LIBRES",
                              T.OK if hospital.free_beds else T.DANGER),
                             (f"{hospital.occupied} OCUPADAS", T.BED_OCCUPIED),
                             (f"{hospital.capacity} CAMAS", T.TEXT_DIM)):
            width = T.fonts()["tiny_b"].size(label)[0] + 18
            x -= width
            T.chip(surface, (x, HOSPITAL.y + 16), label, color)
            x -= 6

        self._draw_entrance(surface)
        self._draw_beds(surface, sim)
        self._draw_waiting_room(surface, sim)

        if hospital.is_saturated and hospital.capacity >= 0:
            alpha = int(T.pulse(self.frame, 40, 70, 170))
            T.glow_border(surface, HOSPITAL, T.DANGER, alpha, radius=10)

    def _draw_entrance(self, surface):
        """Pestaña con una cruz médica en el costado del hospital: marca
        por dónde entran los traslados que vienen del mapa."""
        tab = pygame.Rect(HOSPITAL.left - 8, DOOR[1] - 24, 22, 48)
        pygame.draw.rect(surface, T.SURFACE_HI, tab, border_radius=6)
        pygame.draw.rect(surface, T.BORDER_HI, tab, width=1, border_radius=6)
        cx, cy = tab.centerx + 2, tab.centery
        pygame.draw.rect(surface, T.BED_OCCUPIED,
                         pygame.Rect(cx - 2, cy - 8, 5, 17), border_radius=1)
        pygame.draw.rect(surface, T.BED_OCCUPIED,
                         pygame.Rect(cx - 8, cy - 2, 17, 5), border_radius=1)

    def _draw_beds(self, surface, sim):
        capacity = sim.hospital.capacity
        header = pygame.Rect(BEDS_AREA.x, BEDS_AREA.y - 26, BEDS_AREA.width, 20)
        T.section_title(surface, header, "Sala de internacion",
                        f"{sim.hospital.occupied} de {capacity} camas en uso")

        if capacity == 0:
            box = pygame.Rect(BEDS_AREA.x, BEDS_AREA.y, BEDS_AREA.width, 64)
            T.card(surface, box, fill=T.SURFACE_ALT, border=T.DANGER, radius=8)
            T.text(surface, "body_b", "Sin camas habilitadas",
                   (box.centerx, box.y + 14), T.DANGER, align="center")
            T.text(surface, "tiny", "usa la flecha ARRIBA para agregar camas",
                   (box.centerx, box.y + 36), T.TEXT_DIM, align="center")
        else:
            _, _, width, _ = self.bed_layout(capacity)
            detail = ("full" if width >= BED_DETAIL_FULL else
                      "medium" if width >= BED_DETAIL_MEDIUM else "mini")
            for slot in range(capacity):
                self._draw_bed(surface, self.bed_rect(slot, capacity), slot,
                               self.slot_of.get(slot), sim, detail,
                               self.bed_anims.get(slot))

        # Camas que se acaban de retirar: se las ve encogerse y salir.
        for key, anim in list(self.bed_anims.items()):
            if isinstance(key, str) and anim[0] == "remove":
                self._draw_ghost_bed(surface, anim[2], anim[1])

    def _bed_scale(self, anim):
        """Factor de escala de una cama que está apareciendo."""
        if not anim or anim[0] != "add":
            return 1.0, 0
        t = anim[1] / BED_ANIM_FRAMES
        return max(T.ease_out_back(t), 0.05), int(200 * (1 - t))

    def _draw_bed(self, surface, rect, slot, person, sim, detail, anim):
        """Dibuja una cama: vacía, ocupada, o creciendo si es nueva.

        Se divide en tres franjas: la cabecera con el número y el tiempo
        que le falta al paciente, el colchón con la persona acostada, y
        el pie con la barra de tratamiento. Con camas chicas se van
        soltando primero los textos y después el paciente."""
        scale, flash = self._bed_scale(anim)
        if scale < 0.999:
            rect = rect.inflate(-rect.width * (1 - scale),
                                -rect.height * (1 - scale))
            if rect.width < 6 or rect.height < 6:
                return

        occupied = person is not None
        frame_color = T.BORDER_HI if occupied else T.BORDER
        T.card(surface, rect, fill=T.SURFACE_ALT if occupied else (19, 24, 32),
               border=frame_color, radius=6)
        if flash:
            T.glow_border(surface, rect, T.OK, flash, radius=6)

        if detail == "mini":
            self._draw_bed_compact(surface, rect, person, sim)
            return

        pad = 8 if detail == "full" else 5
        head_h = 16 if detail == "full" else 13
        T.text(surface, "num_sm" if detail == "full" else "tiny_b",
               f"{slot + 1:02d}", (rect.x + pad, rect.y + 4),
               T.TEXT_DIM if occupied else T.TEXT_FAINT)
        if detail == "full":
            label = (f"alta en {max(person.timer or 0, 0)}" if occupied
                     else "libre")
            T.text(surface, "tiny", label, (rect.right - pad, rect.y + 5),
                   T.TEXT_FAINT, align="right")

        # Respaldo de la cama y colchón.
        top = rect.y + head_h + 4
        bottom = rect.bottom - 14
        pygame.draw.rect(surface, frame_color,
                         pygame.Rect(rect.x + pad, top, 4, bottom - top),
                         border_radius=2)
        mattress = pygame.Rect(rect.x + pad + 6, top,
                               rect.width - pad * 2 - 6, bottom - top)
        pygame.draw.rect(surface, (26, 32, 43), mattress, border_radius=4)

        if occupied:
            self._draw_patient(surface, mattress, person, sim,
                               monitor=detail == "full")

        # Pie de la cama: cuánto del periodo crítico ya pasó.
        track = pygame.Rect(rect.x + pad, rect.bottom - 10,
                            rect.width - pad * 2, 4)
        if occupied:
            T.bar(surface, track, self._treatment_progress(person, sim), T.OK,
                  back=(26, 32, 43), radius=2)
        else:
            pygame.draw.rect(surface, (26, 32, 43), track, border_radius=2)

    def _draw_bed_compact(self, surface, rect, person, sim):
        """Versión mínima: con decenas de camas no entra ni el número, así
        que solo se distingue ocupada de libre y cuánto lleva el
        tratamiento."""
        inner = rect.inflate(-8, -8)
        if person is None:
            pygame.draw.rect(surface, (26, 32, 43), inner, border_radius=3)
            return

        waited = (min(person.cycles_waiting / sim.grave_duration, 1.0)
                  if sim.grave_duration else 0.0)
        pygame.draw.rect(surface, T.lerp_color((66, 94, 132), (196, 66, 72),
                                               waited),
                         inner, border_radius=3)
        T.dot(surface, (inner.x + 6, inner.centery - 2), 3, (226, 205, 190))
        track = pygame.Rect(inner.x + 3, inner.bottom - 5, inner.width - 6, 3)
        T.bar(surface, track, self._treatment_progress(person, sim), T.OK,
              back=(26, 32, 43), radius=1)

    def _treatment_progress(self, person, sim):
        """Fracción del periodo crítico que el paciente ya superó."""
        if person.timer is None or sim.grave_duration <= 0:
            return 1.0
        return 1 - min(max(person.timer / sim.grave_duration, 0.0), 1.0)

    def _draw_patient(self, surface, mattress, person, sim, monitor=True):
        """Paciente acostado: almohada, cabeza, manta y monitor cardíaco.

        La manta va del azul clínico al rojo según cuántos ciclos esperó
        antes de conseguir cama: cuanto más esperó, mayor es su riesgo de
        no salir de esta, y eso se ve sin leer ningún número."""
        waited = (min(person.cycles_waiting / sim.grave_duration, 1.0)
                  if sim.grave_duration else 0.0)
        blanket = T.lerp_color((66, 94, 132), (196, 66, 72), waited)

        pillow = pygame.Rect(mattress.x + 3, mattress.y + 4, 14,
                             mattress.height - 8)
        pygame.draw.rect(surface, (62, 74, 95), pillow, border_radius=3)

        body = pygame.Rect(mattress.x + 20, mattress.y + 4,
                           mattress.width - 24, mattress.height - 8)
        if body.width > 6 and body.height > 4:
            pygame.draw.rect(surface, blanket, body, border_radius=4)
            for offset in (0.5, 0.74):
                lx = int(body.x + body.width * offset)
                pygame.draw.line(surface, T.shade(blanket, 1.2),
                                 (lx, body.y + 2), (lx, body.bottom - 2), 1)
            if monitor and body.width > 44:
                self._draw_ecg(surface, body.inflate(-10, -6))

        T.dot(surface, (pillow.centerx, mattress.centery), 5,
              (226, 205, 190), (40, 30, 26), 1)

    def _draw_ecg(self, surface, rect):
        """Traza un latido que corre de derecha a izquierda dentro de la
        manta. Es lo que hace que una cama ocupada se vea 'viva'."""
        points = []
        offset = (self.frame * 0.9) % 28
        for i in range(0, rect.width, 2):
            phase = (i + offset) % 28
            if phase < 9:
                height = 0
            elif phase < 11:
                height = -0.55
            elif phase < 13:
                height = 0.95
            elif phase < 15:
                height = -0.35
            else:
                height = 0
            points.append((rect.x + i, rect.centery - height * rect.height * 0.34))
        if len(points) > 1:
            pygame.draw.aalines(surface, (150, 226, 190), False, points)

    def _draw_ghost_bed(self, surface, rect, age):
        """Cama retirada: se encoge con un destello rojo."""
        t = age / BED_ANIM_FRAMES
        scale = max(1 - T.ease_in_out(t), 0.02)
        shrunk = rect.inflate(-rect.width * (1 - scale),
                              -rect.height * (1 - scale))
        if shrunk.width < 3 or shrunk.height < 3:
            return
        T.card(surface, shrunk, fill=(30, 18, 22), border=T.DANGER, radius=6)
        T.glow_border(surface, shrunk, T.DANGER, int(200 * (1 - t)), radius=6)

    def _draw_waiting_room(self, surface, sim):
        """Sala de espera: quienes se agravaron y no encontraron cama.

        Cada persona muestra una barra de deterioro que se llena con los
        ciclos esperados; cuando llega al final su riesgo de morir es el
        de un paciente sin atención."""
        waiting = list(sim.hospital.waiting_list)
        header = pygame.Rect(WAIT_AREA.x, WAIT_AREA.y - 26, WAIT_AREA.width, 20)
        subtitle = "nadie esperando" if not waiting else (
            f"{len(waiting)} sin cama"
            + (f" ({QUEUE_SLOTS} visibles)" if len(waiting) > QUEUE_SLOTS
               else ""))
        T.section_title(surface, header, "Sala de espera", subtitle,
                        T.WAITING if waiting else T.TEXT_DIM)

        if not waiting:
            T.text(surface, "tiny",
                   "Todos los pacientes graves consiguieron cama",
                   (WAIT_AREA.centerx, WAIT_AREA.y + 12), T.TEXT_FAINT,
                   align="center")
            return

        visible = waiting[:QUEUE_SLOTS]
        for index, person in enumerate(visible):
            rect = self.queue_rect(index)
            risk = min(person.cycles_waiting / sim.grave_duration, 1.0) \
                if sim.grave_duration else 0.0
            color = T.risk_color(risk)

            T.card(surface, rect, fill=(28, 24, 20), border=T.shade(color, 0.7),
                   radius=5)
            # Figura de pie: cabeza y cuerpo.
            cx = rect.centerx
            T.dot(surface, (cx, rect.y + 14), 5, color)
            pygame.draw.rect(surface, T.shade(color, 0.8),
                             pygame.Rect(cx - 6, rect.y + 21, 12, 13),
                             border_radius=4)
            track = pygame.Rect(rect.x + 5, rect.bottom - 9, rect.width - 10, 4)
            T.bar(surface, track, risk, color, back=(20, 25, 34), radius=2)


    # ------------------------------------------------------------------
    # Dibujo: traslados y carteles
    # ------------------------------------------------------------------

    def _glyph(self, char, color):
        """Cachea los glifos de los tokens: se dibujan muchos por frame."""
        key = (char, color)
        cached = self._glyph_cache.get(key)
        if cached is None:
            cached = T.fonts()["tiny_b"].render(char, True, color)
            self._glyph_cache[key] = cached
        return cached

    def _draw_transfers(self, surface):
        """Dibuja cada paciente en tránsito con su estela y su etiqueta.

        Las etiquetas solo se muestran cuando hay pocos traslados a la
        vez: con la simulación acelerada taparían el hospital."""
        # Con varios traslados a la vez las etiquetas se pisarían entre
        # sí; ahí el registro lateral ya cuenta lo que pasó.
        en_curso = [t for t in self.transfers if t.started]
        show_labels = len(en_curso) <= 6
        for transfer in en_curso:
            label, color, glyph = TRANSFER_STYLES[transfer.kind]
            fade = 1.0
            if transfer.progress > 0.85:
                fade = (1 - transfer.progress) / 0.15

            for step in range(1, 7):
                tx, ty = transfer.position(step * 0.045)
                alpha = int(120 * fade * (1 - step / 7))
                if alpha <= 0:
                    continue
                radius = max(6 - step, 1)
                layer = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(layer, (*color, alpha), (radius, radius),
                                   radius)
                surface.blit(layer, (tx - radius, ty - radius))

            x, y = transfer.position()
            position = (int(x), int(y))
            T.blit_glow(surface, 14, color, position, 0.38 * fade)
            T.dot(surface, position, 7, color, T.BG, 1)
            glyph_surf = self._glyph(glyph, T.BG)
            surface.blit(glyph_surf, glyph_surf.get_rect(center=position))

            label_x = position[0] + 13
            if transfer.count > 1:
                label_x = self._draw_transfer_count(
                    surface, position, transfer.count, color) + 4
                label = f"{label}  x{transfer.count}"

            if show_labels and transfer.progress < 0.75:
                self._draw_transfer_label(surface, position, label, color,
                                          label_x)

    def _draw_transfer_count(self, surface, position, count, color):
        """Chapa con el número de pacientes que representa el token: disco
        oscuro, aro del color del traslado y el número adentro."""
        radio = 10 if count >= 10 else 8
        centro = (position[0] + radio + 1, position[1] - radio - 1)
        T.dot(surface, centro, radio, T.BG, color, 1)
        numero = self._glyph(str(count), color)
        surface.blit(numero, numero.get_rect(center=centro))
        return centro[0] + radio

    def _draw_transfer_label(self, surface, position, label, color, x):
        """Etiqueta del traslado, sobre una placa oscura para que se lea
        aunque pase por encima de una cama o del mapa."""
        font = T.fonts()["tiny_b"]
        width, height = font.size(label)
        plate = pygame.Rect(x, position[1] - height // 2 - 3,
                            width + 12, height + 6)
        if plate.right > CANVAS_WIDTH - 6:
            plate.right = position[0] - 13
        T.alpha_rect(surface, plate, (8, 11, 16), 225, radius=4)
        pygame.draw.rect(surface, T.shade(color, 0.55), plate, width=1,
                         border_radius=4)
        surface.blit(font.render(label, True, color),
                     (plate.x + 6, plate.y + 3))

    def _draw_toasts(self, surface):
        """Carteles cortos que suben y se desvanecen donde pasó algo."""
        for (x, y), label, color, age in self.toasts:
            t = age / TOAST_FRAMES
            alpha = int(255 * (1 - t) ** 1.5)
            if alpha <= 0:
                continue
            surf = T.fonts()["tiny_b"].render(label, True, color)
            surf.set_alpha(alpha)
            surface.blit(surf, (x - surf.get_width() // 2, y - 18 - 26 * t))

    # ------------------------------------------------------------------
    # Dibujo: gráficos de la epidemia
    # ------------------------------------------------------------------

    def _draw_chart(self, surface, sim):
        """Curvas históricas. Se redibujan solo cuando hay un ciclo nuevo
        y el resultado se cachea: es lo más caro de la pantalla."""
        T.card(surface, CHART, fill=T.SURFACE, border=T.BORDER, radius=10)

        header = pygame.Rect(CHART.x + 14, CHART.y + 14, CHART.width - 28, 20)
        T.section_title(surface, header, "Evolucion de la epidemia",
                        f"{len(sim.history)} ciclos")

        area = pygame.Rect(CHART.x + 14, CHART.y + 46, CHART.width - 28, 132)
        pressure = pygame.Rect(CHART.x + 14, CHART.y + 206, CHART.width - 28, 64)

        key = (len(sim.history), sim.population)
        if key != self._chart_key:
            self._chart_key = key
            self._chart_cache = self._render_chart(sim, area.size, pressure.size)

        chart_area, chart_pressure = self._chart_cache
        surface.blit(chart_area, area.topleft)
        pygame.draw.rect(surface, T.BORDER, area, width=1, border_radius=4)

        T.text(surface, "tiny", "PRESION SOBRE EL HOSPITAL",
               (CHART.x + 14, CHART.y + 186), T.TEXT_DIM)
        T.text(surface, "tiny",
               "camas ocupadas  ·  cola de espera por encima de la capacidad",
               (CHART.right - 14, CHART.y + 187), T.TEXT_FAINT, align="right")
        surface.blit(chart_pressure, pressure.topleft)
        pygame.draw.rect(surface, T.BORDER, pressure, width=1, border_radius=4)

    def _samples(self, history, width):
        """Submuestrea el historial para que nunca haya más puntos que
        píxeles disponibles."""
        if not history:
            return []
        stride = max(1, math.ceil(len(history) / max(width, 1)))
        samples = history[::stride]
        if samples[-1] is not history[-1]:
            samples.append(history[-1])
        return samples

    def _render_chart(self, sim, area_size, pressure_size):
        """Genera las dos superficies del bloque de gráficos."""
        return (self._render_sir(sim, area_size),
                self._render_pressure(sim, pressure_size))

    def _render_sir(self, sim, size):
        """Área apilada con la composición de la población ciclo a ciclo.

        De abajo hacia arriba: fallecidos, recuperados, graves, infectados
        y susceptibles. La banda de arriba se va comiendo, las de abajo se
        acumulan, y en el medio se ve pasar la ola de contagios."""
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((15, 19, 26))
        width, height = size
        samples = self._samples(sim.history, width)
        if len(samples) < 2:
            return surf

        total = max(sim.population, 1)
        for y_frac in (0.25, 0.5, 0.75):
            y = int(height * y_frac)
            pygame.draw.line(surf, (26, 32, 43), (0, y), (width, y), 1)

        step = width / (len(samples) - 1)
        # Cada banda se dibuja entre su borde superior y el de la banda
        # anterior; si se dibujara hasta el piso, la última taparía todo.
        lower = [(i * step, float(height)) for i in range(len(samples))]
        for state in ("dead", "recovered", "grave", "infected", "susceptible"):
            upper = [(i * step, lower[i][1] - samples[i][state] / total * height)
                     for i in range(len(samples))]
            pygame.draw.polygon(surf, T.STATE_COLORS[state],
                                upper + list(reversed(lower)))
            pygame.draw.aalines(surf, T.shade(T.STATE_COLORS[state], 1.25),
                                False, upper)
            lower = upper

        # Franja roja arriba en los ciclos en los que no quedaba una cama.
        for i, record in enumerate(samples):
            if record["saturated"]:
                x = int(i * step)
                pygame.draw.line(surf, T.DANGER, (x, 0), (x, 5), 2)
        return surf

    def _render_pressure(self, sim, size):
        """Ocupación y cola de espera contra la capacidad instalada."""
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((15, 19, 26))
        width, height = size
        samples = self._samples(sim.history, width)
        if len(samples) < 2:
            return surf

        # Un 15% de aire arriba: si no, la línea de capacidad queda
        # pegada al borde del gráfico y se confunde con el título.
        peak = max(max(r["capacity"], r["hospitalized"] + r["waiting"])
                   for r in samples) * 1.15
        peak = max(peak, 1)
        step = width / (len(samples) - 1)

        def y_of(value):
            return height - value / peak * (height - 4) - 2

        # Ciclos saturados como fondo rojo tenue: se ve de un vistazo
        # cuánto tiempo estuvo el hospital al límite.
        run_start = None
        for i, record in enumerate(samples + [None]):
            saturated = record is not None and record["saturated"]
            if saturated and run_start is None:
                run_start = i
            elif not saturated and run_start is not None:
                x0 = int(run_start * step)
                pygame.draw.rect(surf, (70, 22, 28),
                                 pygame.Rect(x0, 0,
                                             max(int((i - run_start) * step), 1),
                                             height))
                run_start = None

        occupied = [(i * step, y_of(r["hospitalized"]))
                    for i, r in enumerate(samples)]
        queued = [(i * step, y_of(r["hospitalized"] + r["waiting"]))
                  for i, r in enumerate(samples)]

        pygame.draw.polygon(surf, (52, 74, 104),
                            queued + [(width, height), (0, height)])
        pygame.draw.polygon(surf, T.shade(T.WAITING, 0.55),
                            queued + list(reversed(occupied)))
        pygame.draw.polygon(surf, T.shade(T.BED_OCCUPIED, 0.55),
                            occupied + [(width, height), (0, height)])

        # Línea de capacidad, punteada.
        capacity_points = [(i * step, y_of(r["capacity"]))
                           for i, r in enumerate(samples)]
        for i in range(0, len(capacity_points) - 1, 2):
            pygame.draw.line(surf, T.TEXT, capacity_points[i],
                             capacity_points[i + 1], 1)
        return surf

    # ------------------------------------------------------------------
    # Dibujo: panel lateral
    # ------------------------------------------------------------------

    def _draw_panel(self, surface, sim):
        self._draw_population_card(surface, sim)
        self._draw_hospital_card(surface, sim)
        self._draw_log_card(surface)
        self._draw_controls_card(surface, sim)

    def _draw_population_card(self, surface, sim):
        T.card(surface, CARD_POP)
        counts = sim._state_counts()
        total = max(sum(counts.values()), 1)

        inner = pygame.Rect(CARD_POP.x + 14, CARD_POP.y + 14,
                            CARD_POP.width - 28, 20)
        y = T.section_title(surface, inner, "Poblacion", f"{total} personas")

        T.stacked_bar(surface, pygame.Rect(inner.x, y, inner.width, 12),
                      [(counts[state], T.STATE_COLORS[state])
                       for state, _ in T.STATE_LABELS])
        y += 24

        for state, label in T.STATE_LABELS:
            color = T.STATE_COLORS[state]
            value = counts[state]
            pygame.draw.rect(surface, color,
                             pygame.Rect(inner.x, y + 5, 9, 9), border_radius=2)
            T.text(surface, "small", label, (inner.x + 16, y + 2), T.TEXT)
            T.text(surface, "tiny", f"{value / total * 100:4.1f}%",
                   (inner.right - 40, y + 4), T.TEXT_FAINT, align="right")
            T.text(surface, "num", value, (inner.right, y + 1), color,
                   align="right")
            y += 22

    def _draw_hospital_card(self, surface, sim):
        hospital = sim.hospital
        T.card(surface, CARD_HOSP)
        inner = pygame.Rect(CARD_HOSP.x + 14, CARD_HOSP.y + 14,
                            CARD_HOSP.width - 28, 20)
        y = T.section_title(surface, inner, "Hospital")

        # Tres cifras grandes: ocupadas, libres y en espera.
        column = inner.width / 3
        for i, (value, label, color) in enumerate((
            (hospital.occupied, "ocupadas", T.BED_OCCUPIED),
            (hospital.free_beds, "libres",
             T.OK if hospital.free_beds else T.DANGER),
            (len(hospital.waiting_list), "en espera",
             T.WAITING if hospital.waiting_list else T.TEXT_DIM),
        )):
            cx = int(inner.x + column * (i + 0.5))
            T.text(surface, "num_lg", value, (cx, y), color, align="center")
            T.text(surface, "tiny", label, (cx, y + 30), T.TEXT_FAINT,
                   align="center")
        y += 52

        fraction = (hospital.occupied / hospital.capacity
                    if hospital.capacity else 1.0)
        color = T.DANGER if hospital.is_saturated else T.OK
        T.bar(surface, pygame.Rect(inner.x, y, inner.width, 12), fraction,
              color)
        y += 18

        T.text(surface, "tiny", f"ocupacion {fraction * 100:.0f}%",
               (inner.x, y), T.TEXT_DIM)
        T.text(surface, "tiny",
               f"{hospital.occupied}/{hospital.capacity} camas",
               (inner.right, y), T.TEXT_DIM, align="right")
        y += 18

        if hospital.is_saturated:
            alpha = T.pulse(self.frame, 34, 0.45, 1.0)
            T.chip(surface, (inner.x, y), "saturado: sin camas",
                   T.lerp_color(T.SURFACE, T.DANGER, alpha), filled=True)
        else:
            T.chip(surface, (inner.x, y), "con capacidad disponible", T.OK)

    def _draw_log_card(self, surface):
        T.card(surface, CARD_LOG)
        inner = pygame.Rect(CARD_LOG.x + 14, CARD_LOG.y + 14,
                            CARD_LOG.width - 28, 20)
        y = T.section_title(surface, inner, "Que esta pasando")

        if not self.log:
            T.text(surface, "tiny", "sin movimientos todavia",
                   (inner.x, y + 4), T.TEXT_FAINT)
            return

        for icon, message, color, frame in list(self.log)[:LOG_LINES]:
            # Las entradas más viejas se apagan, así la vista se va sola
            # hacia lo que acaba de ocurrir.
            age = min((self.frame - frame) / 240, 1.0)
            tint = T.lerp_color(color, T.SURFACE, age * 0.55)
            text_color = T.lerp_color(T.TEXT, T.SURFACE, age * 0.5)

            pygame.draw.rect(surface, tint,
                             pygame.Rect(inner.x, y + 3, 3, 16),
                             border_radius=2)
            T.text(surface, "tiny_b", icon, (inner.x + 9, y + 4), tint)
            T.text(surface, "tiny", message, (inner.x + 22, y + 4), text_color)
            y += 25

    def _draw_controls_card(self, surface, sim):
        T.card(surface, CARD_CTRL)
        inner = pygame.Rect(CARD_CTRL.x + 14, CARD_CTRL.y + 14,
                            CARD_CTRL.width - 28, 20)
        y = T.section_title(surface, inner, "Controles")

        for keys, description in (
            (("ESPACIO",), "pausar / reanudar"),
            (("^", "v"), "agregar / quitar camas"),
            (("<", ">"), "velocidad de simulacion"),
            (("N", "ESC"), "un ciclo / salir"),
        ):
            x = inner.x
            for key in keys:
                x = T.keycap(surface, (x, y), key).right + 4
            T.text(surface, "tiny", description, (x + 4, y + 3), T.TEXT_DIM)
            y += 25

    # ------------------------------------------------------------------
    # Avisos a pantalla completa
    # ------------------------------------------------------------------

    def _draw_overlays(self, surface, sim):
        if sim.is_finished() and sim.people:
            self._draw_summary(surface, sim)

    def _draw_summary(self, surface, sim):
        """Resumen final sobre el mapa, con el saldo de la epidemia."""
        counts = sim._state_counts()
        box = pygame.Rect(0, 0, 400, 142)
        box.center = FIELD.center

        T.alpha_rect(surface, box, (12, 16, 23), 242, radius=12)
        pygame.draw.rect(surface, T.BORDER_HI, box, width=1, border_radius=12)

        T.text(surface, "banner", "EPIDEMIA TERMINADA",
               (box.centerx, box.y + 16), T.TEXT, align="center")
        T.text(surface, "tiny", f"{sim.current_cycle} ciclos simulados",
               (box.centerx, box.y + 42), T.TEXT_FAINT, align="center")

        saturated = sum(1 for r in sim.history if r["saturated"])
        for i, (value, label, color) in enumerate((
            (counts["recovered"], "recuperados", T.STATE_COLORS["recovered"]),
            (counts["dead"], "fallecidos", T.STATE_COLORS["dead"]),
            (saturated, "ciclos saturado", T.DANGER),
        )):
            cx = int(box.x + box.width / 3 * (i + 0.5))
            T.text(surface, "num_lg", value, (cx, box.y + 70), color,
                   align="center")
            T.text(surface, "tiny", label, (cx, box.y + 102), T.TEXT_FAINT,
                   align="center")

    # ------------------------------------------------------------------
    # Frame completo
    # ------------------------------------------------------------------

    def render(self, sim):
        """Devuelve el lienzo con el frame ya dibujado."""
        self.frame += 1
        self.sync(sim)
        self._advance_animations()

        surface = self.canvas
        T.fill_background(surface)

        self._draw_header(surface, sim)
        self._draw_field(surface, sim)
        self._draw_chart(surface, sim)
        self._draw_hospital(surface, sim)
        self._draw_panel(surface, sim)

        # Los traslados van al final: cruzan del mapa al hospital y deben
        # verse por encima de ambos bloques.
        self._draw_transfers(surface)
        self._draw_toasts(surface)
        self._draw_overlays(surface, sim)
        return surface
