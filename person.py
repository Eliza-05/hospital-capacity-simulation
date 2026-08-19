"""Clase Person: agente individual de la simulación.

Modela a cada individuo que se mueve por el mapa y transita entre
estados epidemiológicos (susceptible, infectado, grave, recuperado o
fallecido). Es usada tanto por la lógica de la simulación, que decide
cuándo ocurren las transiciones, como por el módulo de renderizado,
que dibuja a cada persona según su estado y posición.
"""

import random

from config import SCREEN_HEIGHT, SCREEN_WIDTH


class Person:
    """Representa a un individuo dentro de la simulación epidémica.

    Cada persona guarda su posición en el mapa y su estado de salud actual,
    que puede ser: susceptible (sana, puede contagiarse), infectada, grave
    (necesita hospitalización), recuperada o fallecida. También lleva un
    contador interno que indica cuántos ciclos faltan para que cambie de
    estado, y un indicador de si en este momento está ocupando una cama
    de hospital.
    """

    def __init__(self, x, y, state="susceptible"):
        self.x = x
        self.y = y
        self.state = state
        self.hospitalized = False
        self.timer = None

    def infect(self, duration):
        """La persona pasa de sana a infectada y arranca el
        conteo de ciclos hasta que su estado vuelva a cambiar."""
        self.state = "infected"
        self.timer = duration

    def tick(self):
        """Avanza el conteo de ciclos en uno. Avisa (devolviendo True) cuando el conteo llega a cero, para
        que la simulación sepa que debe aplicar el siguiente cambio de
        estado en esa persona."""
        if self.timer is None:
            return False
        self.timer -= 1
        return self.timer <= 0

    def set_grave(self, duration):
        """Agrava la condición de la persona infectada, que ahora necesita
        hospitalización, y reinicia el conteo de ciclos."""
        self.state = "grave"
        self.timer = duration

    def recover(self):
        """Marca a la persona como recuperada y si tiene una cama asignada, la libera"""
        self.state = "recovered"
        self.timer = None
        self.hospitalized = False

    def die(self):
        """Marca a la persona como fallecida y si tiene una cama asignada, la libera."""
        self.state = "dead"
        self.timer = None
        self.hospitalized = False

    def move(self, width=SCREEN_WIDTH, height=SCREEN_HEIGHT, step=4,
              random_fn=random.random):
        """Actualiza la posición de la persona con un desplazamiento aleatorio pequeño, manteniéndola dentro de los límites de la pantalla."""
        dx = (random_fn() * 2 - 1) * step
        dy = (random_fn() * 2 - 1) * step
        self.x = min(max(self.x + dx, 0), width)
        self.y = min(max(self.y + dy, 0), height)
