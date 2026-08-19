"""Clase Person: agente individual de la simulación.

Responsable: Persona A (lógica)
"""


class Person:
    """Representa a un individuo dentro de la simulación epidémica.

    Contrato de atributos usado por Simulation/Hospital (no cambiar los
    nombres sin avisar a la otra persona del equipo):
        - state: str -> "susceptible" | "infected" | "grave" | "recovered" | "dead"
        - hospitalized: bool -> True si actualmente ocupa una cama
        - timer: int -> ciclos restantes para la próxima transición de estado
    """

    def __init__(self, x, y, state="susceptible"):
        self.x = x
        self.y = y
        self.state = state
        self.hospitalized = False
        self.timer = None

    def infect(self):
        """Transición susceptible -> infected. Inicia el temporizador de infección."""
        pass

    def update(self, dt):
        """Avanza el temporizador y mueve al agente. No decide transiciones de estado."""
        pass

    def move(self):
        """Actualiza la posición del agente en pantalla."""
        pass
