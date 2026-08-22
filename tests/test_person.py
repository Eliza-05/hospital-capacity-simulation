import pytest

from person import Person


def test_infect_moves_susceptible_to_infected_and_sets_timer():
    person = Person(x=0, y=0)

    person.infect(duration=5)

    assert person.state == "infected"
    assert person.timer == 5


def test_tick_decrements_timer_and_returns_false_while_running():
    person = Person(x=0, y=0)
    person.infect(duration=2)

    expired = person.tick()

    assert person.timer == 1
    assert expired is False


def test_tick_returns_true_exactly_when_timer_reaches_zero():
    person = Person(x=0, y=0)
    person.infect(duration=1)

    expired = person.tick()

    assert person.timer == 0
    assert expired is True


def test_tick_does_nothing_when_person_has_no_timer():
    person = Person(x=0, y=0)

    expired = person.tick()

    assert person.timer is None
    assert expired is False


def test_set_grave_moves_infected_to_grave_and_resets_timer():
    person = Person(x=0, y=0)
    person.infect(duration=1)
    person.tick()

    person.set_grave(duration=3)

    assert person.state == "grave"
    assert person.timer == 3


def test_recover_moves_person_to_recovered_and_clears_hospitalization():
    person = Person(x=0, y=0)
    person.infect(duration=1)
    person.hospitalized = True

    person.recover()

    assert person.state == "recovered"
    assert person.timer is None
    assert person.hospitalized is False


def test_die_moves_person_to_dead_and_clears_hospitalization():
    person = Person(x=0, y=0)
    person.set_grave(duration=1)
    person.hospitalized = True

    person.die()

    assert person.state == "dead"
    assert person.timer is None
    assert person.hospitalized is False


def test_move_never_gains_velocity_when_random_fn_stays_at_the_midpoint():
    """random_fn=0.5 siempre cae en el centro del rango [-1, 1], así que
    tanto la dirección inicial como cada ajuste posterior dan cero."""
    person = Person(x=50, y=50)

    person.move(width=100, height=100, step=4, random_fn=lambda: 0.5)
    person.move(width=100, height=100, step=4, random_fn=lambda: 0.5)

    assert person.vx == 0
    assert person.vy == 0
    assert person.x == 50
    assert person.y == 50


def test_move_sets_velocity_from_a_random_direction_and_updates_position():
    """La primera vez que se mueve, la velocidad sale directo de
    random_fn (todavía no hay nada que perturbar)."""
    values = iter([0.8, 0.3])
    person = Person(x=50, y=50)

    person.move(width=100, height=100, step=4, random_fn=lambda: next(values))

    assert person.vx == pytest.approx(2.4)
    assert person.vy == pytest.approx(-1.6)
    assert person.x == pytest.approx(52.4)
    assert person.y == pytest.approx(48.4)


def test_move_perturbs_existing_velocity_instead_of_replacing_it():
    """Con velocidad ya asignada, move() debe sumarle un ajuste chico,
    no sortear una velocidad nueva de cero (eso sería el comportamiento
    viejo, sin inercia)."""
    person = Person(x=50, y=50)
    person.vx, person.vy = 2.0, 0.0

    person.move(width=100, height=100, step=4, random_fn=lambda: 0.75)

    assert person.vx == pytest.approx(2.6)
    assert person.vy == pytest.approx(0.6)


def test_move_caps_velocity_at_the_configured_step():
    person = Person(x=50, y=50)
    person.vx, person.vy = 10.0, 0.0

    person.move(width=100, height=100, step=4, random_fn=lambda: 0.5)

    assert person.vx == pytest.approx(4.0)
    assert person.vy == pytest.approx(0.0)
    assert person.x == pytest.approx(54.0)
    assert person.y == pytest.approx(50.0)


def test_move_clamps_at_the_right_edge():
    person = Person(x=95, y=50)
    person.vx, person.vy = 10.0, 0.0

    person.move(width=100, height=100, step=20, random_fn=lambda: 0.5)

    assert person.x == pytest.approx(100.0)


def test_move_clamps_at_the_left_edge():
    person = Person(x=2, y=50)
    person.vx, person.vy = -10.0, 0.0

    person.move(width=100, height=100, step=20, random_fn=lambda: 0.5)

    assert person.x == pytest.approx(0.0)


def test_move_clamps_at_the_bottom_edge():
    person = Person(x=50, y=95)
    person.vx, person.vy = 0.0, 10.0

    person.move(width=100, height=100, step=20, random_fn=lambda: 0.5)

    assert person.y == pytest.approx(100.0)


def test_move_clamps_at_the_top_edge():
    person = Person(x=50, y=2)
    person.vx, person.vy = 0.0, -10.0

    person.move(width=100, height=100, step=20, random_fn=lambda: 0.5)

    assert person.y == pytest.approx(0.0)
