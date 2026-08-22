"""Tests de los controles en vivo y del dibujado (Persona B).

`handle_event` y `draw` se prueban sin abrir ninguna ventana: los eventos
se construyen a mano y el dibujo se hace sobre una Surface en memoria.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from config import PANEL_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH
from person import Person
from simulation import MAX_SPEED, Simulation


def make_simulation(**overrides):
    params = dict(
        population=0, initial_infected=0, transmission_probability=0.0,
        infection_radius=0.0, pct_grave=0.5, mortality_hospitalized=0.1,
        mortality_waiting=0.9, infection_duration=5, grave_duration=3,
        initial_beds=5, random_fn=lambda: 0.5,
    )
    params.update(overrides)
    return Simulation(**params)


def press(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


# ----------------------------------------------------------------------
# Pausa
# ----------------------------------------------------------------------

def test_space_toggles_pause():
    sim = make_simulation()

    sim.handle_event(press(pygame.K_SPACE))
    assert sim.paused is True

    sim.handle_event(press(pygame.K_SPACE))
    assert sim.paused is False


def test_paused_simulation_does_not_advance_the_cycle():
    sim = make_simulation(population=5, initial_infected=1)
    sim.populate()

    sim.handle_event(press(pygame.K_SPACE))
    sim.update()

    assert sim.current_cycle == 0


# ----------------------------------------------------------------------
# Camas
# ----------------------------------------------------------------------

def test_up_arrow_adds_a_bed():
    sim = make_simulation(initial_beds=5)

    sim.handle_event(press(pygame.K_UP))

    assert sim.hospital.capacity == 6


def test_down_arrow_removes_a_bed():
    sim = make_simulation(initial_beds=5)

    sim.handle_event(press(pygame.K_DOWN))

    assert sim.hospital.capacity == 4


def test_down_arrow_is_ignored_when_every_bed_is_occupied():
    """Reducir camas por debajo de las ocupadas dejaría pacientes
    hospitalizados de forma inconsistente: el control lo ignora."""
    sim = make_simulation(initial_beds=2)
    for _ in range(2):
        sim.hospital.admit(Person(x=0, y=0))

    sim.handle_event(press(pygame.K_DOWN))

    assert sim.hospital.capacity == 2
    assert sim.hospital.occupied == 2


def test_up_arrow_admits_someone_from_the_waiting_list():
    sim = make_simulation(initial_beds=1)
    occupant, waiting = Person(x=0, y=0), Person(x=0, y=0)
    sim.hospital.admit(occupant)
    sim.hospital.admit(waiting)

    sim.handle_event(press(pygame.K_UP))

    assert waiting.hospitalized is True
    assert list(sim.hospital.waiting_list) == []


# ----------------------------------------------------------------------
# Velocidad
# ----------------------------------------------------------------------

def test_right_arrow_increases_speed():
    sim = make_simulation()

    sim.handle_event(press(pygame.K_RIGHT))

    assert sim.speed == 2


def test_left_arrow_decreases_speed():
    sim = make_simulation()
    sim.speed = 4

    sim.handle_event(press(pygame.K_LEFT))

    assert sim.speed == 3


def test_speed_never_drops_below_one():
    sim = make_simulation()

    for _ in range(5):
        sim.handle_event(press(pygame.K_LEFT))

    assert sim.speed == 1


def test_speed_is_capped_at_the_maximum():
    sim = make_simulation()

    for _ in range(MAX_SPEED + 10):
        sim.handle_event(press(pygame.K_RIGHT))

    assert sim.speed == MAX_SPEED


# ----------------------------------------------------------------------
# Eventos que no son teclas
# ----------------------------------------------------------------------

def test_non_keyboard_events_are_ignored():
    sim = make_simulation()

    sim.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0)))

    assert sim.paused is False
    assert sim.speed == 1


def test_unrelated_keys_change_nothing():
    sim = make_simulation(initial_beds=5)

    sim.handle_event(press(pygame.K_a))

    assert (sim.paused, sim.speed, sim.hospital.capacity) == (False, 1, 5)


# ----------------------------------------------------------------------
# Dibujado
# ----------------------------------------------------------------------

@pytest.fixture
def screen():
    pygame.init()
    return pygame.Surface((SCREEN_WIDTH + PANEL_WIDTH, SCREEN_HEIGHT))


def test_draw_runs_over_a_full_simulation_without_errors(screen):
    """Recorre estados reales (sanos, infectados, graves con y sin cama,
    recuperados y muertos) para que ningún estado quede sin dibujar."""
    sim = make_simulation(population=60, initial_infected=10, initial_beds=2,
                           transmission_probability=0.5, infection_radius=80,
                           width=SCREEN_WIDTH, height=SCREEN_HEIGHT,
                           random_fn=__import__("random").Random(3).random)
    sim.populate()
    for _ in range(40):
        sim.update()
        sim.draw(screen)

    counts = sim._state_counts()
    assert sum(counts.values()) == 60


def test_draw_shows_the_finished_state_without_errors(screen):
    sim = make_simulation(population=10, initial_infected=1,
                           width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
    sim.populate()
    while not sim.is_finished():
        sim.update()

    sim.draw(screen)

    assert sim.is_finished() is True


def test_draw_handles_a_hospital_with_zero_beds(screen):
    """La barra de ocupación divide por la capacidad: con 0 camas no
    puede romperse."""
    sim = make_simulation(population=10, initial_infected=2, initial_beds=0,
                           width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
    sim.populate()

    sim.draw(screen)

    assert sim.hospital.capacity == 0


def test_state_counts_covers_every_drawable_state():
    sim = make_simulation(population=4)
    sim.people = [Person(x=0, y=0, state=s)
                  for s in ("susceptible", "infected", "grave", "dead")]

    counts = sim._state_counts()

    assert counts["susceptible"] == 1 and counts["dead"] == 1
    assert counts["recovered"] == 0
