"""Clase Simulation: coordina a las personas, el hospital y la presentación.

Es el motor central de la simulación: crea la población inicial, avanza
el estado de cada persona ciclo a ciclo, gestiona los ingresos y altas
en el hospital, y se encarga de dibujar todo en pantalla con Pygame.
También guarda en self.history un registro por cada paso simulado, que
luego usa exporter.py para generar reportes.
"""

import math
import os
import random

# Silencia el banner que pygame imprime al importarse, para que no ensucie
# la salida del modo comparación ni la de los tests.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from config import FPS, PANEL_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH
from hospital import Hospital
from person import Person

# Un color por estado
STATE_COLORS = {
    "susceptible": (70, 130, 220),    # azul
    "infected": (240, 150, 50),       # naranja
    "grave": (225, 60, 60),           # rojo
    "recovered": (80, 200, 120),      # verde
    "dead": (150, 90, 200),           # morado
}
STATE_LABELS = (
    ("susceptible", "Susceptibles"),
    ("infected", "Infectados"),
    ("grave", "Graves"),
    ("recovered", "Recuperados"),
    ("dead", "Fallecidos"),
)

BACKGROUND = (18, 18, 24)
PANEL_BACKGROUND = (30, 30, 40)
TEXT = (235, 235, 240)
TEXT_DIM = (150, 150, 165)
BED_RING = (245, 245, 250)      # aro de quien tiene cama
WAITING_RING = (250, 210, 70)   # aro de quien está en la lista de espera
ALERT = (225, 60, 60)

PERSON_RADIUS = 4
MAX_SPEED = 10


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
        """Responde a las teclas del usuario: pausar la simulación con
        espacio, cambiar el número de camas con las flechas arriba/abajo,
        y ajustar la velocidad con las flechas izquierda/derecha."""
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_SPACE:
            self.paused = not self.paused
        elif event.key == pygame.K_UP:
            # set_capacity devuelve False si el cambio no se puede aplicar;
            # subir siempre se puede, así que no hay nada que manejar.
            self.hospital.set_capacity(self.hospital.capacity + 1)
        elif event.key == pygame.K_DOWN:
            # Bajar se rechaza si dejaría pacientes sin cama: se ignora.
            self.hospital.set_capacity(self.hospital.capacity - 1)
        elif event.key == pygame.K_RIGHT:
            self.speed = min(self.speed + 1, MAX_SPEED)
        elif event.key == pygame.K_LEFT:
            self.speed = max(self.speed - 1, 1)

    # -- dibujo ---------------------------------------------------------

    def _fonts(self):
        """Crea (una sola vez) las tipografías del panel."""
        if getattr(self, "_font_cache", None) is None:
            if not pygame.font.get_init():
                pygame.font.init()
            self._font_cache = {
                "title": pygame.font.SysFont("Arial", 17, bold=True),
                "body": pygame.font.SysFont("Arial", 15),
                "small": pygame.font.SysFont("Arial", 13),
                "alert": pygame.font.SysFont("Arial", 22, bold=True),
            }
        return self._font_cache

    def _state_counts(self):
        """Cuenta cuánta gente hay en cada estado en este momento."""
        counts = {state: 0 for state in STATE_COLORS}
        for person in self.people:
            counts[person.state] += 1
        return counts

    def _draw_people(self, screen):
        """Dibuja a cada persona como un punto del color de su estado.

        Los pacientes graves llevan además un aro: blanco si consiguieron
        cama, amarillo si están en la lista de espera. Así se ve de un
        vistazo a quién está atendiendo el hospital y a quién no."""
        for person in self.people:
            position = (int(person.x), int(person.y))
            if person.state == "dead":
                pygame.draw.circle(screen, STATE_COLORS["dead"], position,
                                    PERSON_RADIUS - 1)
                continue

            pygame.draw.circle(screen, STATE_COLORS[person.state], position,
                                PERSON_RADIUS)
            if person.state == "grave":
                ring = BED_RING if person.hospitalized else WAITING_RING
                pygame.draw.circle(screen, ring, position,
                                    PERSON_RADIUS + 3, 2)

    def _draw_counter(self, screen, y, label, value, color=None):
        """Escribe una fila `etiqueta ..... valor` del panel, con un
        cuadradito del color del estado cuando corresponde."""
        fonts = self._fonts()
        x = SCREEN_WIDTH + 16
        if color is not None:
            pygame.draw.rect(screen, color, pygame.Rect(x, y + 4, 10, 10))
            x += 18

        screen.blit(fonts["body"].render(label, True, TEXT), (x, y))
        value_text = fonts["body"].render(str(value), True, TEXT)
        screen.blit(value_text,
                    (SCREEN_WIDTH + PANEL_WIDTH - 16 - value_text.get_width(), y))
        return y + 21

    def _draw_bed_bar(self, screen, y):
        """Barra de ocupación de camas: se llena a medida que se ocupan y
        se pone roja cuando el hospital queda saturado."""
        x = SCREEN_WIDTH + 16
        width = PANEL_WIDTH - 32
        pygame.draw.rect(screen, (60, 60, 75), pygame.Rect(x, y, width, 16))

        if self.hospital.capacity > 0:
            fraction = self.hospital.occupied / self.hospital.capacity
            color = ALERT if self.hospital.is_saturated else (80, 200, 120)
            pygame.draw.rect(screen, color,
                              pygame.Rect(x, y, int(width * fraction), 16))
        return y + 24

    def _draw_panel(self, screen):
        """Panel lateral con los contadores, la ocupación de camas, el
        estado de los controles y la ayuda de teclas."""
        fonts = self._fonts()
        counts = self._state_counts()
        hospital = self.hospital

        pygame.draw.rect(screen, PANEL_BACKGROUND,
                          pygame.Rect(SCREEN_WIDTH, 0, PANEL_WIDTH,
                                      SCREEN_HEIGHT))

        x = SCREEN_WIDTH + 16
        y = 16
        screen.blit(fonts["title"].render("Ciclo " + str(self.current_cycle),
                                           True, TEXT), (x, y))
        y += 30

        for state, label in STATE_LABELS:
            y = self._draw_counter(screen, y, label, counts[state],
                                    STATE_COLORS[state])

        y += 10
        screen.blit(fonts["title"].render("Hospital", True, TEXT), (x, y))
        y += 26
        y = self._draw_counter(screen, y, "Hospitalizados",
                                hospital.occupied, BED_RING)
        y = self._draw_counter(screen, y, "En espera",
                                len(hospital.waiting_list), WAITING_RING)
        y = self._draw_counter(screen, y, "Camas libres", hospital.free_beds)
        y = self._draw_counter(
            screen, y, "Ocupación",
            f"{hospital.occupied}/{hospital.capacity}")
        y = self._draw_bed_bar(screen, y)

        if hospital.is_saturated:
            screen.blit(fonts["body"].render("SATURADO", True, ALERT), (x, y))
        y += 30

        screen.blit(fonts["title"].render("Controles", True, TEXT), (x, y))
        y += 26
        y = self._draw_counter(screen, y, "Estado",
                                "PAUSADO" if self.paused else "corriendo")
        y = self._draw_counter(screen, y, "Velocidad", f"x{self.speed}")

        y = SCREEN_HEIGHT - 92
        for line in ("ESPACIO   pausar / reanudar",
                     "ARRIBA / ABAJO   +/- camas",
                     "IZQ / DER   velocidad",
                     "ESC   salir"):
            screen.blit(fonts["small"].render(line, True, TEXT_DIM), (x, y))
            y += 18

    def _draw_alerts(self, screen):
        """Avisos grandes sobre el área de simulación: hospital saturado
        (con cuánta gente está esperando cama) y epidemia terminada."""
        fonts = self._fonts()

        if self.hospital.is_saturated:
            waiting = len(self.hospital.waiting_list)
            banner = pygame.Surface((SCREEN_WIDTH, 34))
            banner.set_alpha(210)
            banner.fill(ALERT)
            screen.blit(banner, (0, 0))
            text = fonts["alert"].render(
                f"HOSPITAL SATURADO  -  {waiting} SIN CAMA", True, TEXT)
            screen.blit(text, ((SCREEN_WIDTH - text.get_width()) // 2, 5))

        if self.is_finished() and self.people:
            text = fonts["alert"].render("EPIDEMIA TERMINADA", True, TEXT)
            box = pygame.Surface((text.get_width() + 40, 48))
            box.set_alpha(220)
            box.fill((40, 40, 55))
            position = ((SCREEN_WIDTH - box.get_width()) // 2,
                        SCREEN_HEIGHT // 2 - 24)
            screen.blit(box, position)
            screen.blit(text, (position[0] + 20, position[1] + 12))

    def draw(self, screen):
        """Dibuja en pantalla a cada persona con un color según su estado,
        muestra un panel con los contadores generales y una advertencia
        visual cuando el hospital se queda sin camas."""
        screen.fill(BACKGROUND)
        self._draw_people(screen)
        self._draw_alerts(screen)
        self._draw_panel(screen)

    def run(self):
        """Arranca y controla la ventana de Pygame: inicializa todo, y en
        cada vuelta del loop procesa eventos, actualiza la simulación y
        vuelve a dibujar la pantalla."""
        pygame.init()
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH + PANEL_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(
            "Capacidad hospitalaria durante una epidemia")
        clock = pygame.time.Clock()

        if not self.people:
            self.populate()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif (event.type == pygame.KEYDOWN
                        and event.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle_event(event)

            # `speed` no acelera el tiempo: corre más ciclos por frame. Al
            # terminar la epidemia se deja de actualizar para que el
            # historial no siga creciendo con frames idénticos.
            for _ in range(self.speed):
                if self.is_finished():
                    break
                self.update()

            self.draw(screen)
            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
