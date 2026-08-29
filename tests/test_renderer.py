"""Tests del renderizado (renderer.py).

El renderer mantiene su propio estado visual —qué persona ocupa qué cama,
qué traslados están en curso— y lo deduce comparando frames. Estos tests
verifican que esa deducción no se desincronice de la simulación real, que
la grilla de camas entre siempre en la sala, y que dibujar no rompa en
los casos límite (sin camas, sin población, epidemia terminada).
"""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

import renderer as R
from simulation import Simulation
from theme import CANVAS_HEIGHT, CANVAS_WIDTH


def make_simulation(seed=7, **overrides):
    """Una simulación chica pero movida: pocas camas y mucho contagio,
    para que haya ingresos, esperas y altas todo el tiempo."""
    params = dict(
        population=60, initial_infected=8, transmission_probability=0.35,
        infection_radius=90, pct_grave=0.6, mortality_hospitalized=0.2,
        mortality_waiting=0.8, infection_duration=8, grave_duration=6,
        initial_beds=3, random_fn=random.Random(seed).random,
    )
    params.update(overrides)
    return Simulation(**params)


@pytest.fixture
def canvas():
    pygame.init()
    return pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))


def assert_beds_are_consistent(sim):
    """El mapa de camas del renderer tiene que coincidir con el hospital."""
    rend = sim._renderer()
    hospitalizados = {p for p in sim.people if p.hospitalized}

    assert set(rend.slot_of.values()) == hospitalizados
    assert len(rend.slot_of) == sim.hospital.occupied
    assert all(slot < sim.hospital.capacity for slot in rend.slot_of)
    # Las dos tablas son la misma relación vista desde cada lado.
    assert {p: s for s, p in rend.slot_of.items()} == rend.bed_of


# ----------------------------------------------------------------------
# Coherencia entre el hospital y las camas dibujadas
# ----------------------------------------------------------------------

@pytest.mark.parametrize("ciclos_por_frame", [1, 5, 20])
def test_bed_map_tracks_the_hospital_at_any_speed(canvas, ciclos_por_frame):
    """Con la simulación acelerada entran varios ciclos en un mismo frame
    y el renderer ve solo el resultado neto. Aun así ninguna cama puede
    quedar ocupada por alguien que ya salió."""
    sim = make_simulation()
    sim.populate()

    while not sim.is_finished() and sim.current_cycle < 300:
        for _ in range(ciclos_por_frame):
            sim.update()
        sim.draw(canvas)
        assert_beds_are_consistent(sim)


def test_every_hospitalized_patient_gets_a_bed_when_others_are_discharged(canvas):
    """Con el hospital lleno, en un mismo ciclo puede haber un alta y un
    ingreso: la cama que se libera tiene que quedar disponible para el que
    entra, no perderse."""
    sim = make_simulation(initial_beds=2)
    sim.populate()

    ocupacion_maxima = 0
    while not sim.is_finished() and sim.current_cycle < 300:
        sim.update()
        sim.draw(canvas)
        ocupacion_maxima = max(ocupacion_maxima, sim.hospital.occupied)
        assert_beds_are_consistent(sim)

    assert ocupacion_maxima == 2, "el escenario nunca llenó el hospital"


def test_reducing_capacity_moves_patients_into_the_remaining_beds(canvas):
    """Al quitar camas, quien estaba en una que deja de existir se muda a
    otra libre en vez de quedar flotando fuera de la sala."""
    sim = make_simulation(initial_beds=6)
    sim.populate()
    while sim.hospital.occupied < 3 and sim.current_cycle < 300:
        sim.update()
        sim.draw(canvas)

    assert sim.hospital.set_capacity(3) is True
    sim.draw(canvas)

    assert_beds_are_consistent(sim)


def test_adding_capacity_registers_the_new_beds(canvas):
    sim = make_simulation(initial_beds=3)
    sim.populate()
    sim.draw(canvas)

    sim.hospital.set_capacity(7)
    sim.draw(canvas)

    rend = sim._renderer()
    # Las cuatro camas nuevas se animan al aparecer.
    assert sorted(k for k in rend.bed_anims if isinstance(k, int)) == [3, 4, 5, 6]
    assert any("cama" in entrada[1] for entrada in rend.log)


# ----------------------------------------------------------------------
# Geometría
# ----------------------------------------------------------------------

@pytest.mark.parametrize("capacidad", [1, 2, 5, 10, 17, 34, 60, 120])
def test_bed_grid_always_fits_inside_the_ward(capacidad):
    rend = R.Renderer()

    rects = [rend.bed_rect(slot, capacidad) for slot in range(capacidad)]

    assert all(R.BEDS_AREA.contains(rect) for rect in rects)
    # Ninguna cama puede solaparse con otra.
    for i, rect in enumerate(rects):
        assert not any(rect.colliderect(other) for other in rects[i + 1:])


def test_bed_layout_with_no_capacity_is_empty():
    assert R.Renderer().bed_layout(0) == (0, 0, 0, 0)


def test_people_are_mapped_inside_the_field():
    """Las coordenadas del modelo se traducen al rectángulo del mapa: nadie
    puede dibujarse fuera de él."""
    sim = make_simulation(population=200)
    sim.populate()
    rend = R.Renderer()

    for person in sim.people:
        x, y = rend.field_pos(sim, person)
        assert R.FIELD.left <= x <= R.FIELD.right
        assert R.FIELD.top <= y <= R.FIELD.bottom


# ----------------------------------------------------------------------
# Casos límite del dibujado
# ----------------------------------------------------------------------

def test_drawing_scales_to_a_surface_of_any_size():
    """La interfaz se dibuja en un lienzo fijo y se adapta a la ventana."""
    pygame.init()
    sim = make_simulation(population=20)
    sim.populate()

    for size in ((CANVAS_WIDTH, CANVAS_HEIGHT), (1060, 600), (2000, 1200)):
        screen = pygame.Surface(size)
        sim.draw(screen)
        assert screen.get_size() == size


def test_drawing_a_hospital_without_beds_does_not_break(canvas):
    sim = make_simulation(initial_beds=0)
    sim.populate()

    for _ in range(30):
        sim.update()
        sim.draw(canvas)

    assert sim.hospital.capacity == 0
    assert sim._renderer().slot_of == {}


def test_drawing_an_empty_population_does_not_break(canvas):
    sim = make_simulation(population=0, initial_infected=0)
    sim.populate()

    sim.draw(canvas)

    assert sim.is_finished() is True


def test_drawing_a_finished_epidemic_shows_the_summary(canvas):
    sim = make_simulation()
    sim.populate()
    while not sim.is_finished():
        sim.update()

    sim.draw(canvas)

    assert sim.is_finished() and sim.people
