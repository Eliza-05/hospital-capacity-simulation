"""Clase Simulation: coordina a las personas, el hospital y la presentación.

Es el motor central de la simulación: crea la población inicial, avanza
el estado de cada persona ciclo a ciclo, gestiona los ingresos y altas
en el hospital, y se encarga de dibujar todo en pantalla con Pygame.
También guarda en self.history un registro por cada paso simulado, que
luego usa exporter.py para generar reportes.
"""

import random

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from hospital import Hospital
from person import Person


class Simulation:
    def __init__(self, population, initial_infected, pct_grave,
                 mortality_hospitalized, mortality_waiting,
                 infection_duration, grave_duration, initial_beds,
                 width=SCREEN_WIDTH, height=SCREEN_HEIGHT,
                 random_fn=random.random):
        self.population = population
        self.initial_infected = initial_infected
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

        for person in self.people:
            if person.state == "dead":
                continue

            person.move(self.width, self.height, random_fn=self.random_fn)

            if person.state == "infected" and person.tick():
                self._infection_expire(person)
            elif person.state == "grave" and person.tick():
                self._grave_expire(person)

        self._record_history()

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
