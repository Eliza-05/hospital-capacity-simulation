"""Clase Simulation: coordina a las personas, el hospital y la presentación.

Es el motor central de la simulación: crea la población inicial, avanza
el estado de cada persona ciclo a ciclo, gestiona los ingresos y altas
en el hospital, y se encarga de dibujar todo en pantalla con Pygame.
También guarda en self.history un registro por cada paso simulado, que
luego usa exporter.py para generar reportes.
"""

import math
import random

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from hospital import Hospital
from person import Person


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

    # ------------------------------------------------------------------
    # Lógica de la simulación
    # ------------------------------------------------------------------

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

    def _grave_expire(self, person):
        """Se ejecuta cuando termina el periodo crítico de un paciente
        grave: decide si se recupera o fallece. La probabilidad de morir
        es distinta según si el paciente logró conseguir cama o estuvo
        esperando sin ser atendido."""
        was_hospitalized = person.hospitalized
        mortality = (self.mortality_hospitalized if was_hospitalized
                     else self.mortality_waiting)
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

    # ------------------------------------------------------------------
    # Presentación (ventana de Pygame)
    # ------------------------------------------------------------------

    def handle_event(self, event):
        """Responde a las teclas del usuario: pausar la simulación con
        espacio, cambiar el número de camas con las flechas arriba/abajo,
        y ajustar la velocidad con las flechas izquierda/derecha."""
        pass

    def draw(self, screen):
        """Dibuja en pantalla a cada persona con un color según su estado,
        muestra un panel con los contadores generales y una advertencia
        visual cuando el hospital se queda sin camas."""
        pass

    def run(self):
        """Arranca y controla la ventana de Pygame: inicializa todo, y en
        cada vuelta del loop procesa eventos, actualiza la simulación y
        vuelve a dibujar la pantalla."""
        pass
