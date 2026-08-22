"""Clase Person: agente individual de la simulación.

Modela a cada individuo que se mueve por el mapa y transita entre
estados epidemiológicos (susceptible, infectado, grave, recuperado o
fallecido). Es usada tanto por la lógica de la simulación, que decide
cuándo ocurren las transiciones, como por el módulo de renderizado,
que dibuja a cada persona según su estado y posición.
"""

import math
import random

from config import SCREEN_HEIGHT, SCREEN_WIDTH

# Fracción de la velocidad máxima (`step`) que se le suma a la velocidad
# en cada ciclo. Chica a propósito: el movimiento debe cambiar de rumbo
# de a poco (inercia), no saltar a una dirección nueva de golpe.
VELOCITY_JITTER_RATIO = 0.3


class Person:
    """Representa a un individuo dentro de la simulación epidémica.

    Cada persona guarda su posición en el mapa y su estado de salud actual,
    que puede ser: susceptible (sana, puede contagiarse), infectada, grave
    (necesita hospitalización), recuperada o fallecida. También lleva un
    contador interno que indica cuántos ciclos faltan para que cambie de
    estado, un indicador de si en este momento está ocupando una cama
    de hospital, y cuántos ciclos lleva acumulados esperando una.
    """

    def __init__(self, x, y, state="susceptible"):
        self.x = x
        self.y = y
        self.state = state
        self.hospitalized = False
        self.timer = None
        # Ciclos que la persona pasó grave sin conseguir cama. Se usa al
        # vencer la gravedad para saber cuánta atención recibió realmente.
        self.cycles_waiting = 0
        # Vector de velocidad persistente. None marca "todavía sin
        # inicializar" (distinto de (0, 0), que ya es una velocidad
        # válida): move() lo arranca con una dirección al azar la primera
        # vez que se llama.
        self.vx = None
        self.vy = None

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
        self.cycles_waiting = 0

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
        """Actualiza la posición sumando una velocidad persistente, en vez
        de saltar a un punto al azar en cada ciclo.

        La velocidad arranca en una dirección aleatoria la primera vez que
        se llama a move() y luego se perturba levemente en cada ciclo
        siguiente (no se reemplaza), lo que da un movimiento con inercia.
        Se recorta a una magnitud máxima de `step` para que nadie se
        dispare. Quien llega a un borde de la pantalla queda pegado ahí
        (la posición se recorta a [0, width] / [0, height])."""
        if self.vx is None:
            self.vx = (random_fn() * 2 - 1) * step
            self.vy = (random_fn() * 2 - 1) * step
        else:
            jitter = step * VELOCITY_JITTER_RATIO
            self.vx += (random_fn() * 2 - 1) * jitter
            self.vy += (random_fn() * 2 - 1) * jitter

        speed = math.hypot(self.vx, self.vy)
        if speed > step:
            scale = step / speed
            self.vx *= scale
            self.vy *= scale

        self.x = min(max(self.x + self.vx, 0), width)
        self.y = min(max(self.y + self.vy, 0), height)
