"""Clase Simulation: coordina a las personas, el hospital y la presentación.

Es el motor central de la simulación: crea la población inicial, avanza
el estado de cada persona ciclo a ciclo, gestiona los ingresos y altas
en el hospital, y coordina la ventana de Pygame. También guarda en
self.history un registro por cada paso simulado, que luego usa
exporter.py para generar reportes.

El dibujo en sí vive en renderer.py: acá solo se decide *cuándo* se
dibuja y se le pasa el estado. Esa separación permite que el modo
comparación corra sin tocar nada del renderizado.
"""

import math
import os
import random

# Silencia el banner que pygame imprime al importarse, para que no ensucie
# la salida del modo comparación ni la de los tests.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from config import CYCLE_RATE, FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from hospital import Hospital
from person import Person
from renderer import Renderer
from theme import CANVAS_HEIGHT, CANVAS_WIDTH, STATE_COLORS

MAX_SPEED = 10

# Tope de ciclos que se pueden simular en un mismo frame. Sin él, un
# tirón del sistema operativo haría que la simulación intente ponerse al
# día de golpe y la ventana se congelaría.
MAX_STEPS_PER_FRAME = 20

# Cuánto de la pantalla puede ocupar la ventana como máximo.
WINDOW_SCREEN_RATIO = (0.94, 0.90)


class Simulation:
    def __init__(self, population, initial_infected, pct_grave,
                 mortality_hospitalized, mortality_waiting,
                 infection_duration, grave_duration, initial_beds,
                 transmission_probability=0.0, infection_radius=0.0,
                 width=SCREEN_WIDTH, height=SCREEN_HEIGHT,
                 random_fn=random.random):
        self._validate_params(
            population=population, initial_infected=initial_infected,
            pct_grave=pct_grave, mortality_hospitalized=mortality_hospitalized,
            mortality_waiting=mortality_waiting,
            infection_duration=infection_duration,
            grave_duration=grave_duration, initial_beds=initial_beds,
            transmission_probability=transmission_probability,
            infection_radius=infection_radius,
        )

        self.population = population
        self.initial_infected = initial_infected
        self.transmission_probability = transmission_probability
        self.infection_radius = infection_radius
        self.pct_grave = pct_grave
        self.mortality_hospitalized = mortality_hospitalized
        self.mortality_waiting = mortality_waiting
        self.infection_duration = infection_duration
        self.grave_duration = grave_duration
        self.width = width
        self.height = height
        self.random_fn = random_fn

        self.hospital = Hospital(initial_beds)
        self.people = []
        self.history = []

        self.paused = False
        self.speed = 1
        self.current_cycle = 0

    @staticmethod
    def _validate_params(population, initial_infected, pct_grave,
                          mortality_hospitalized, mortality_waiting,
                          infection_duration, grave_duration, initial_beds,
                          transmission_probability, infection_radius):
        """Valida los parámetros del modelo al construir la simulación.
        Lanza ValueError con un mensaje claro ante cualquier valor fuera
        de rango, en vez de dejar que el modelo corra con datos inválidos."""
        if population < 0:
            raise ValueError("population no puede ser negativo")
        if initial_infected < 0:
            raise ValueError("initial_infected no puede ser negativo")
        if initial_infected > population:
            raise ValueError("initial_infected no puede superar a population")
        if initial_beds < 0:
            raise ValueError("initial_beds no puede ser negativo")
        if infection_radius < 0:
            raise ValueError("infection_radius no puede ser negativo")
        if infection_duration <= 0:
            raise ValueError("infection_duration debe ser mayor que 0")
        if grave_duration <= 0:
            raise ValueError("grave_duration debe ser mayor que 0")
        for name, value in (
            ("transmission_probability", transmission_probability),
            ("pct_grave", pct_grave),
            ("mortality_hospitalized", mortality_hospitalized),
            ("mortality_waiting", mortality_waiting),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} debe estar entre 0 y 1")

    # Lógica de la simulación


    def populate(self):
        """Genera la población inicial en posiciones aleatorias dentro de
        la pantalla y marca a algunas personas como infectadas desde el
        arranque. También guarda el primer registro en el historial."""
        self.people = [
            Person(x=self.random_fn() * self.width,
                   y=self.random_fn() * self.height)
            for _ in range(self.population)
        ]
        for person in self.people[:self.initial_infected]:
            self._infect(person)
        self._record_history()

    def _infect(self, person):
        """Marca a la persona como contagiada e inicia su periodo de infección."""
        person.infect(self.infection_duration)

    def _infection_expire(self, person):
        """Se ejecuta cuando termina el periodo de infección leve de una
        persona: según una probabilidad, decide si se agrava (y en ese
        caso intenta hospitalizarla) o si se recupera directamente."""
        if self.random_fn() < self.pct_grave:
            person.set_grave(self.grave_duration)
            self.hospital.admit(person)
        else:
            self._recover(person)

    def _grave_mortality(self, person):
        """Probabilidad de que un paciente grave fallezca al vencer su
        temporizador.

        No alcanza con mirar si tiene cama justo en ese instante: quien
        esperó casi todo su periodo crítico y consiguió cama sobre el
        final no recibió la misma atención que quien la tuvo desde el
        principio, y contarlos igual haría que la capacidad hospitalaria
        no tuviera ningún efecto sobre la mortalidad. Por eso el riesgo
        se interpola entre ambos extremos según qué fracción del periodo
        grave pasó sin atención."""
        if not person.hospitalized:
            return self.mortality_waiting

        sin_atencion = min(person.cycles_waiting / self.grave_duration, 1.0)
        return (self.mortality_hospitalized
                + sin_atencion * (self.mortality_waiting
                                  - self.mortality_hospitalized))

    def _grave_expire(self, person):
        """Se ejecuta cuando termina el periodo crítico de un paciente
        grave: decide si se recupera o fallece. La probabilidad de morir
        depende de cuánto tiempo del periodo crítico pasó con cama y
        cuánto esperando sin ser atendido."""
        was_hospitalized = person.hospitalized
        mortality = self._grave_mortality(person)
        if self.random_fn() < mortality:
            if was_hospitalized:
                self.hospital.discharge(person)
            else:
                self.hospital.remove_from_waiting_list(person)
            person.die()
        else:
            self._recover(person)

    def _recover(self, person):
        """Marca a una persona como recuperada, liberando su cama de
        hospital o sacándola de la lista de espera según corresponda."""
        if person.hospitalized:
            self.hospital.discharge(person)
        else:
            self.hospital.remove_from_waiting_list(person)
        person.recover()

    def _record_history(self):
        """Guarda en el historial un resumen del estado actual de la
        simulación: cuántas personas hay en cada estado, cuántas camas
        están libres u ocupadas, y si el hospital está saturado."""
        counts = {"susceptible": 0, "infected": 0, "grave": 0,
                  "recovered": 0, "dead": 0}
        for person in self.people:
            counts[person.state] += 1

        self.history.append({
            "cycle": self.current_cycle,
            **counts,
            "hospitalized": sum(1 for p in self.people if p.hospitalized),
            "waiting": len(self.hospital.waiting_list),
            "free_beds": self.hospital.free_beds,
            "capacity": self.hospital.capacity,
            "saturated": self.hospital.is_saturated,
        })

    def update(self):
        """Avanza la simulación un ciclo: mueve a cada persona y revisa si
        le toca cambiar de estado. No dibuja nada en pantalla. Para que
        la simulación vaya más rápido, este método se llama varias veces
        seguidas por cada frame en lugar de acelerar el tiempo."""
        if self.paused:
            return

        self.current_cycle += 1

        for person in self.people:
            if person.state == "dead":
                continue

            person.move(self.width, self.height, random_fn=self.random_fn)

            if person.state == "grave" and not person.hospitalized:
                person.cycles_waiting += 1

            if person.state == "infected" and person.tick():
                self._infection_expire(person)
            elif person.state == "grave" and person.tick():
                self._grave_expire(person)

        self._spread_contagion()
        self._record_history()

    def _spread_contagion(self):
        """Revisa a las personas infectadas y, según qué tan cerca estén
        de otras personas sanas y con qué probabilidad de contagio,
        decide quién se enferma en este ciclo. Los nuevos contagios se
        aplican todos al final, para que una persona recién contagiada
        no pueda a su vez contagiar a otras en ese mismo ciclo."""
        sources = [p for p in self.people if p.state == "infected"]
        if not sources:
            return

        newly_infected = set()
        for source in sources:
            for other in self.people:
                if other in newly_infected or not self._in_contagion_range(source, other):
                    continue
                if self.random_fn() < self.transmission_probability:
                    newly_infected.add(other)

        for person in newly_infected:
            self._infect(person)

    def _in_contagion_range(self, source, other):
        """Indica si la segunda persona es sana y está lo bastante cerca
        de la primera como para poder contagiarse de ella."""
        if other.state != "susceptible":
            return False
        distance = math.dist((source.x, source.y), (other.x, other.y))
        return distance <= self.infection_radius

    def is_finished(self):
        """Indica si la simulación ya llegó a su fin, es decir, si ya no
        queda nadie infectado ni en estado grave que pueda seguir
        contagiando o empeorando."""
        return not any(p.state in ("infected", "grave") for p in self.people)


    # Presentación (ventana de Pygame)


    def handle_event(self, event):
        """Responde a las teclas del usuario: espacio pausa, las flechas
        arriba/abajo cambian las camas (de a 5 con SHIFT), las flechas
        izquierda/derecha la velocidad, y N adelanta un solo ciclo
        mientras la simulación está en pausa."""
        if event.type != pygame.KEYDOWN:
            return

        # Los eventos construidos a mano en los tests no traen `mod`.
        step = 5 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1

        if event.key == pygame.K_SPACE:
            self.paused = not self.paused
        elif event.key == pygame.K_UP:
            # set_capacity devuelve False si el cambio no se puede aplicar;
            # subir siempre se puede, así que no hay nada que manejar.
            self.hospital.set_capacity(self.hospital.capacity + step)
        elif event.key == pygame.K_DOWN:
            # Bajar se rechaza si dejaría pacientes sin cama. Se prueba con
            # pasos cada vez más chicos para que la tecla haga algo aunque
            # no quepa el salto completo.
            for size in range(step, 0, -1):
                if self.hospital.set_capacity(
                        max(self.hospital.capacity - size, 0)):
                    break
        elif event.key == pygame.K_RIGHT:
            self.speed = min(self.speed + 1, MAX_SPEED)
        elif event.key == pygame.K_LEFT:
            self.speed = max(self.speed - 1, 1)
        elif event.key == pygame.K_n and self.paused:
            # Avance ciclo a ciclo: útil para explicar en detalle qué pasa
            # en un momento puntual sin que la simulación siga corriendo.
            self.paused = False
            self.update()
            self.paused = True

    # -- dibujo ---------------------------------------------------------

    def _state_counts(self):
        """Cuenta cuánta gente hay en cada estado en este momento."""
        counts = {state: 0 for state in STATE_COLORS}
        for person in self.people:
            counts[person.state] += 1
        return counts

    def _renderer(self):
        """Devuelve el renderer, creándolo la primera vez que se dibuja.

        Se crea perezosamente para que el modo comparación, que nunca
        dibuja, no cargue fuentes ni superficies que no va a usar."""
        if getattr(self, "_renderer_cache", None) is None:
            self._renderer_cache = Renderer()
        return self._renderer_cache

    def _scaled(self, frame, size):
        """Escala el frame al tamaño de la ventana, reutilizando siempre
        la misma superficie destino para no reservar memoria por frame."""
        cache = getattr(self, "_scaled_cache", None)
        if cache is None or cache.get_size() != size:
            cache = pygame.Surface(size)
            self._scaled_cache = cache
        try:
            pygame.transform.smoothscale(frame, size, cache)
        except (ValueError, pygame.error):
            # smoothscale exige 24/32 bits; con otras profundidades se cae
            # al escalado simple, que acepta cualquier superficie.
            cache.blit(pygame.transform.scale(frame, size), (0, 0))
        return cache

    def draw(self, screen):
        """Dibuja un frame completo sobre `screen`.

        El renderer trabaja siempre sobre un lienzo de tamaño fijo y acá
        se lo ajusta al destino, así la interfaz se ve igual sin importar
        el tamaño de la ventana."""
        frame = self._renderer().render(self)
        size = screen.get_size()
        if size == frame.get_size():
            screen.blit(frame, (0, 0))
        else:
            screen.blit(self._scaled(frame, size), (0, 0))

    @staticmethod
    def _window_size():
        """Tamaño inicial de la ventana: el lienzo completo si entra en la
        pantalla, o la mayor reducción proporcional que sí entre."""
        try:
            desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError, AttributeError):
            info = pygame.display.Info()
            desktop_w, desktop_h = info.current_w, info.current_h

        ratio_w, ratio_h = WINDOW_SCREEN_RATIO
        scale = min(1.0,
                    desktop_w * ratio_w / CANVAS_WIDTH,
                    desktop_h * ratio_h / CANVAS_HEIGHT)
        return (int(CANVAS_WIDTH * scale), int(CANVAS_HEIGHT * scale))

    def run(self):
        """Arranca y controla la ventana de Pygame.

        El dibujo corre a `FPS` cuadros por segundo y la simulación avanza
        a `CYCLE_RATE` ciclos por segundo multiplicados por `speed`: así
        las animaciones se ven fluidas aunque el modelo vaya lento, y
        acelerar no convierte la pantalla en un parpadeo."""
        pygame.init()
        screen = pygame.display.set_mode(self._window_size(),
                                          pygame.RESIZABLE)
        pygame.display.set_caption(
            "Capacidad hospitalaria durante una epidemia")
        clock = pygame.time.Clock()

        if not self.people:
            self.populate()

        # Ciclos pendientes de simular; guarda la fracción sobrante entre
        # frames para que la velocidad promedio sea exacta.
        pending = 0.0
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif (event.type == pygame.KEYDOWN
                        and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(event.size,
                                                      pygame.RESIZABLE)
                else:
                    self.handle_event(event)

            delta = clock.tick(FPS) / 1000.0
            if not self.paused and not self.is_finished():
                pending += delta * CYCLE_RATE * self.speed
                steps = min(int(pending), MAX_STEPS_PER_FRAME)
                pending -= steps
                for _ in range(steps):
                    if self.is_finished():
                        pending = 0.0
                        break
                    self.update()

            self.draw(screen)
            pygame.display.flip()

        pygame.quit()
