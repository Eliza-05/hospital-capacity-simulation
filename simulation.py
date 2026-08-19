"""Clase Simulation: coordina agentes, hospital, lógica de eventos y presentación.

Métodos de lógica -> Persona A
Métodos de presentación (draw, manejo de teclado) -> Persona B

Contrato de atributos expuesto a exporter.py:
    - self.history: list[dict] -> un registro por frame/paso simulado
"""

from hospital import Hospital
from person import Person


class Simulation:
    def __init__(self, population, initial_infected, pct_grave,
                 mortality_hospitalized, mortality_waiting,
                 infection_duration, grave_duration, initial_beds):
        self.population = population
        self.pct_grave = pct_grave
        self.mortality_hospitalized = mortality_hospitalized
        self.mortality_waiting = mortality_waiting
        self.infection_duration = infection_duration
        self.grave_duration = grave_duration

        self.hospital = Hospital(initial_beds)
        self.people = []
        self.history = []

        self.paused = False
        self.speed = 1

    # ------------------------------------------------------------------
    # Lógica (Persona A)
    # ------------------------------------------------------------------

    def _infect(self, person):
        """Marca a `person` como infectado e inicia su temporizador."""
        pass

    def _infection_expire(self, person):
        """Evento: vence el tiempo de infección leve.
        Decide, una sola vez, si pasa a grave o a recuperado (según pct_grave)."""
        pass

    def _grave_expire(self, person):
        """Evento: vence el tiempo de gravedad.
        Decide, una sola vez, si el paciente se recupera o fallece
        (mortalidad distinta según person.hospitalized)."""
        pass

    def _recover(self, person):
        """Transición a recovered; libera cama si estaba hospitalizado."""
        pass

    def _record_history(self):
        """Agrega una entrada a self.history con los contadores del frame actual."""
        pass

    def update(self, dt):
        """Bucle principal de lógica: mueve agentes, revisa temporizadores,
        dispara los eventos de transición de estado."""
        pass

    # ------------------------------------------------------------------
    # Presentación (Persona B)
    # ------------------------------------------------------------------

    def handle_event(self, event):
        """Maneja teclado: pausa (SPACE), camas (UP/DOWN), velocidad (LEFT/RIGHT)."""
        pass

    def draw(self, screen):
        """Dibuja agentes coloreados por estado, panel de contadores y
        aviso visual cuando self.hospital.is_saturated."""
        pass

    def run(self):
        """Loop principal de Pygame (init, eventos, update, draw, flip)."""
        pass
