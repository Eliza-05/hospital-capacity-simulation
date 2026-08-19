from person import Person
from simulation import Simulation


def make_simulation(**overrides):
    params = dict(
        population=0,
        initial_infected=0,
        pct_grave=0.5,
        mortality_hospitalized=0.1,
        mortality_waiting=0.9,
        infection_duration=5,
        grave_duration=3,
        initial_beds=1,
        width=100,
        height=100,
        random_fn=lambda: 0.5,
    )
    params.update(overrides)
    return Simulation(**params)


def test_infect_sets_person_state_and_infection_timer():
    sim = make_simulation(infection_duration=7)
    person = Person(x=0, y=0)

    sim._infect(person)

    assert person.state == "infected"
    assert person.timer == 7


def test_recover_plain_infected_person_just_sets_recovered_state():
    sim = make_simulation()
    person = Person(x=0, y=0)
    sim._infect(person)

    sim._recover(person)

    assert person.state == "recovered"
    assert person.hospitalized is False


def test_recover_hospitalized_person_frees_the_bed():
    sim = make_simulation(initial_beds=1)
    person = Person(x=0, y=0)
    sim.hospital.admit(person)

    sim._recover(person)

    assert person.state == "recovered"
    assert sim.hospital.occupied == 0


def test_recover_hospitalized_person_frees_bed_for_next_in_waiting_list():
    sim = make_simulation(initial_beds=1)
    occupant = Person(x=0, y=0)
    waiting = Person(x=0, y=0)
    sim.hospital.admit(occupant)
    sim.hospital.admit(waiting)

    sim._recover(occupant)

    assert waiting.hospitalized is True


def test_recover_waiting_person_leaves_the_waiting_list():
    sim = make_simulation(initial_beds=1)
    occupant = Person(x=0, y=0)
    waiting = Person(x=0, y=0)
    sim.hospital.admit(occupant)
    sim.hospital.admit(waiting)

    sim._recover(waiting)

    assert waiting.state == "recovered"
    assert list(sim.hospital.waiting_list) == []
    assert sim.hospital.occupied == 1


def test_infection_expire_low_roll_becomes_grave_and_admits_to_free_bed():
    sim = make_simulation(pct_grave=0.3, grave_duration=4, initial_beds=1,
                           random_fn=lambda: 0.1)
    person = Person(x=0, y=0)
    sim._infect(person)

    sim._infection_expire(person)

    assert person.state == "grave"
    assert person.timer == 4
    assert person.hospitalized is True
    assert sim.hospital.occupied == 1


def test_infection_expire_low_roll_queues_when_hospital_full():
    sim = make_simulation(pct_grave=0.3, initial_beds=1, random_fn=lambda: 0.1)
    occupant = Person(x=0, y=0)
    sim.hospital.admit(occupant)
    person = Person(x=0, y=0)
    sim._infect(person)

    sim._infection_expire(person)

    assert person.state == "grave"
    assert person.hospitalized is False
    assert list(sim.hospital.waiting_list) == [person]


def test_infection_expire_high_roll_recovers_without_becoming_grave():
    sim = make_simulation(pct_grave=0.3, random_fn=lambda: 0.9)
    person = Person(x=0, y=0)
    sim._infect(person)

    sim._infection_expire(person)

    assert person.state == "recovered"


def test_grave_expire_hospitalized_low_roll_dies_and_frees_the_bed():
    sim = make_simulation(mortality_hospitalized=0.5, initial_beds=1,
                           random_fn=lambda: 0.1)
    person = Person(x=0, y=0)
    sim.hospital.admit(person)
    person.set_grave(3)

    sim._grave_expire(person)

    assert person.state == "dead"
    assert person.hospitalized is False
    assert sim.hospital.occupied == 0


def test_grave_expire_hospitalized_high_roll_recovers_and_frees_the_bed():
    sim = make_simulation(mortality_hospitalized=0.5, initial_beds=1,
                           random_fn=lambda: 0.9)
    person = Person(x=0, y=0)
    sim.hospital.admit(person)
    person.set_grave(3)

    sim._grave_expire(person)

    assert person.state == "recovered"
    assert sim.hospital.occupied == 0


def test_grave_expire_waiting_uses_waiting_mortality_and_dies():
    sim = make_simulation(mortality_hospitalized=0.9, mortality_waiting=0.1,
                           initial_beds=1, random_fn=lambda: 0.05)
    occupant = Person(x=0, y=0)
    waiting = Person(x=0, y=0)
    sim.hospital.admit(occupant)
    sim.hospital.admit(waiting)
    waiting.set_grave(3)

    sim._grave_expire(waiting)

    assert waiting.state == "dead"
    assert list(sim.hospital.waiting_list) == []
    assert sim.hospital.occupied == 1


def test_grave_expire_waiting_high_roll_recovers_and_leaves_queue():
    sim = make_simulation(mortality_waiting=0.5, initial_beds=1,
                           random_fn=lambda: 0.9)
    occupant = Person(x=0, y=0)
    waiting = Person(x=0, y=0)
    sim.hospital.admit(occupant)
    sim.hospital.admit(waiting)
    waiting.set_grave(3)

    sim._grave_expire(waiting)

    assert waiting.state == "recovered"
    assert list(sim.hospital.waiting_list) == []


def test_record_history_appends_a_counters_snapshot():
    sim = make_simulation(initial_beds=1)
    susceptible = Person(x=0, y=0)
    infected = Person(x=0, y=0)
    sim._infect(infected)
    hospitalized = Person(x=0, y=0)
    sim.hospital.admit(hospitalized)
    hospitalized.set_grave(3)
    waiting = Person(x=0, y=0)
    sim.hospital.admit(waiting)
    waiting.set_grave(3)
    dead = Person(x=0, y=0)
    dead.die()
    sim.people = [susceptible, infected, hospitalized, waiting, dead]

    sim._record_history()

    assert len(sim.history) == 1
    snapshot = sim.history[0]
    assert snapshot["susceptible"] == 1
    assert snapshot["infected"] == 1
    assert snapshot["grave"] == 2
    assert snapshot["dead"] == 1
    assert snapshot["hospitalized"] == 1
    assert snapshot["waiting"] == 1
    assert snapshot["free_beds"] == 0
    assert snapshot["capacity"] == 1
    assert snapshot["saturated"] is True


def test_update_ticks_infected_person_without_expiring_early():
    sim = make_simulation(infection_duration=2, random_fn=lambda: 0.9)
    person = Person(x=0, y=0)
    sim._infect(person)
    sim.people = [person]

    sim.update()

    assert person.state == "infected"
    assert person.timer == 1


def test_update_triggers_infection_expire_when_timer_hits_zero():
    sim = make_simulation(infection_duration=1, pct_grave=0.0,
                           random_fn=lambda: 0.9)
    person = Person(x=0, y=0)
    sim._infect(person)
    sim.people = [person]

    sim.update()

    assert person.state == "recovered"


def test_update_triggers_grave_expire_when_timer_hits_zero():
    sim = make_simulation(grave_duration=1, mortality_hospitalized=1.0,
                           initial_beds=1, random_fn=lambda: 0.0)
    person = Person(x=0, y=0)
    sim.hospital.admit(person)
    person.set_grave(1)
    sim.people = [person]

    sim.update()

    assert person.state == "dead"


def test_update_appends_one_history_snapshot_per_call():
    sim = make_simulation()
    sim.people = [Person(x=0, y=0)]

    sim.update()
    sim.update()

    assert len(sim.history) == 2


def test_populate_creates_the_configured_population_size():
    sim = make_simulation(population=5, initial_infected=0, width=100, height=100)

    sim.populate()

    assert len(sim.people) == 5


def test_populate_places_people_within_screen_bounds():
    sim = make_simulation(population=3, width=100, height=200, random_fn=lambda: 1.0)

    sim.populate()

    for person in sim.people:
        assert person.x == 100
        assert person.y == 200


def test_populate_infects_exactly_initial_infected_people():
    sim = make_simulation(population=4, initial_infected=2)

    sim.populate()

    states = [person.state for person in sim.people]
    assert states.count("infected") == 2
    assert states.count("susceptible") == 2


def test_populate_records_an_initial_history_snapshot():
    sim = make_simulation(population=2, initial_infected=1)

    sim.populate()

    assert len(sim.history) == 1
    assert sim.history[0]["infected"] == 1
    assert sim.history[0]["susceptible"] == 1


def test_update_moves_a_living_person():
    sim = make_simulation(width=100, height=100, random_fn=lambda: 1.0)
    person = Person(x=50, y=50)
    sim.people = [person]

    sim.update()

    assert person.x == 54
    assert person.y == 54


def test_update_does_not_move_a_dead_person():
    sim = make_simulation(width=100, height=100, random_fn=lambda: 1.0)
    person = Person(x=50, y=50)
    person.die()
    sim.people = [person]

    sim.update()

    assert person.x == 50
    assert person.y == 50


def test_update_does_nothing_while_paused():
    sim = make_simulation(infection_duration=1, random_fn=lambda: 0.9)
    person = Person(x=0, y=0)
    sim._infect(person)
    sim.people = [person]
    sim.paused = True

    sim.update()

    assert person.state == "infected"
    assert person.timer == 1
    assert sim.history == []
