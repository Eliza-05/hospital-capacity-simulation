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


def test_move_stays_put_when_random_fn_returns_the_midpoint():
    person = Person(x=50, y=50)

    person.move(width=100, height=100, step=4, random_fn=lambda: 0.5)

    assert person.x == 50
    assert person.y == 50


def test_move_shifts_position_by_up_to_step_in_either_direction():
    person = Person(x=50, y=50)

    person.move(width=100, height=100, step=4, random_fn=lambda: 1.0)

    assert person.x == 54
    assert person.y == 54


def test_move_clamps_to_the_left_and_top_edges():
    person = Person(x=1, y=1)

    person.move(width=100, height=100, step=4, random_fn=lambda: 0.0)

    assert person.x == 0
    assert person.y == 0


def test_move_clamps_to_the_right_and_bottom_edges():
    person = Person(x=99, y=99)

    person.move(width=100, height=100, step=4, random_fn=lambda: 1.0)

    assert person.x == 100
    assert person.y == 100
