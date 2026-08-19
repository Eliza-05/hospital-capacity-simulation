import random

import pytest

from person import Person
from simulation import Simulation


def make_simulation(**overrides):
    params = dict(
        population=0,
        initial_infected=0,
        transmission_probability=0.0,
        infection_radius=0.0,
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


def test_simulation_stores_transmission_probability_and_infection_radius():
    sim = make_simulation(transmission_probability=0.4, infection_radius=12)

    assert sim.transmission_probability == 0.4
    assert sim.infection_radius == 12


def test_rejects_negative_population():
    with pytest.raises(ValueError):
        make_simulation(population=-1)


def test_rejects_negative_initial_infected():
    with pytest.raises(ValueError):
        make_simulation(initial_infected=-1)


def test_rejects_initial_infected_greater_than_population():
    with pytest.raises(ValueError):
        make_simulation(population=2, initial_infected=3)


def test_rejects_negative_initial_beds():
    with pytest.raises(ValueError):
        make_simulation(initial_beds=-1)


def test_rejects_negative_infection_radius():
    with pytest.raises(ValueError):
        make_simulation(infection_radius=-1)


def test_rejects_zero_infection_duration():
    with pytest.raises(ValueError):
        make_simulation(infection_duration=0)


def test_rejects_zero_grave_duration():
    with pytest.raises(ValueError):
        make_simulation(grave_duration=0)


def test_rejects_transmission_probability_below_zero():
    with pytest.raises(ValueError):
        make_simulation(transmission_probability=-0.1)


def test_rejects_transmission_probability_above_one():
    with pytest.raises(ValueError):
        make_simulation(transmission_probability=1.1)


def test_rejects_pct_grave_out_of_range():
    with pytest.raises(ValueError):
        make_simulation(pct_grave=-0.1)


def test_rejects_mortality_hospitalized_out_of_range():
    with pytest.raises(ValueError):
        make_simulation(mortality_hospitalized=1.1)


def test_rejects_mortality_waiting_out_of_range():
    with pytest.raises(ValueError):
        make_simulation(mortality_waiting=-0.1)


def test_accepts_boundary_values_zero_and_one():
    sim = make_simulation(population=0, initial_infected=0,
                           infection_radius=0, transmission_probability=0.0,
                           pct_grave=1.0, mortality_hospitalized=0.0,
                           mortality_waiting=1.0)

    assert sim.pct_grave == 1.0


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


def test_contagion_infects_susceptible_within_radius_with_favorable_roll():
    sim = make_simulation(infection_radius=10, transmission_probability=1.0,
                           infection_duration=5, random_fn=lambda: 0.0)
    source = Person(x=0, y=0)
    sim._infect(source)
    target = Person(x=5, y=0)
    sim.people = [source, target]

    sim._spread_contagion()

    assert target.state == "infected"
    assert target.timer == 5


def test_contagion_does_not_infect_susceptible_outside_radius():
    sim = make_simulation(infection_radius=2, transmission_probability=1.0,
                           random_fn=lambda: 0.0)
    source = Person(x=0, y=0)
    sim._infect(source)
    target = Person(x=10, y=0)
    sim.people = [source, target]

    sim._spread_contagion()

    assert target.state == "susceptible"


def test_contagion_does_not_infect_on_unfavorable_roll():
    sim = make_simulation(infection_radius=10, transmission_probability=0.3,
                           random_fn=lambda: 0.9)
    source = Person(x=0, y=0)
    sim._infect(source)
    target = Person(x=5, y=0)
    sim.people = [source, target]

    sim._spread_contagion()

    assert target.state == "susceptible"


def test_contagion_does_not_reinfect_a_recovered_person():
    sim = make_simulation(infection_radius=10, transmission_probability=1.0,
                           random_fn=lambda: 0.0)
    source = Person(x=0, y=0)
    sim._infect(source)
    target = Person(x=5, y=0, state="recovered")
    sim.people = [source, target]

    sim._spread_contagion()

    assert target.state == "recovered"


def test_contagion_does_not_reinfect_a_grave_person():
    sim = make_simulation(infection_radius=10, transmission_probability=1.0,
                           random_fn=lambda: 0.0)
    source = Person(x=0, y=0)
    sim._infect(source)
    target = Person(x=5, y=0, state="grave")
    sim.people = [source, target]

    sim._spread_contagion()

    assert target.state == "grave"


def test_contagion_does_not_infect_a_dead_person():
    sim = make_simulation(infection_radius=10, transmission_probability=1.0,
                           random_fn=lambda: 0.0)
    source = Person(x=0, y=0)
    sim._infect(source)
    target = Person(x=5, y=0, state="dead")
    sim.people = [source, target]

    sim._spread_contagion()

    assert target.state == "dead"


def test_contagion_from_two_sources_infects_target_only_once_without_crashing():
    sim = make_simulation(infection_radius=10, transmission_probability=1.0,
                           infection_duration=5, random_fn=lambda: 0.0)
    source1 = Person(x=0, y=0)
    sim._infect(source1)
    source2 = Person(x=1, y=0)
    sim._infect(source2)
    target = Person(x=0, y=1)
    sim.people = [source1, source2, target]

    sim._spread_contagion()

    assert target.state == "infected"
    assert target.timer == 5


def test_update_end_to_end_infects_a_nearby_susceptible_person():
    sim = make_simulation(infection_radius=10, transmission_probability=1.0,
                           width=100, height=100, random_fn=lambda: 0.0)
    source = Person(x=0, y=0)
    sim._infect(source)
    target = Person(x=5, y=0)
    sim.people = [source, target]

    sim.update()

    assert target.state == "infected"


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
    assert snapshot["cycle"] == 0


def test_record_history_reflects_the_current_cycle():
    sim = make_simulation()
    sim.current_cycle = 5

    sim._record_history()

    assert sim.history[0]["cycle"] == 5


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


def test_current_cycle_starts_at_zero():
    sim = make_simulation()

    assert sim.current_cycle == 0


def test_update_advances_current_cycle_by_one():
    sim = make_simulation()
    sim.people = [Person(x=0, y=0)]

    sim.update()

    assert sim.current_cycle == 1


def test_update_advances_current_cycle_once_per_call():
    sim = make_simulation()
    sim.people = [Person(x=0, y=0)]

    sim.update()
    sim.update()
    sim.update()

    assert sim.current_cycle == 3


def test_update_does_not_advance_current_cycle_while_paused():
    sim = make_simulation()
    sim.people = [Person(x=0, y=0)]
    sim.paused = True

    sim.update()

    assert sim.current_cycle == 0


def test_is_finished_false_when_someone_is_infected():
    sim = make_simulation()
    person = Person(x=0, y=0)
    sim._infect(person)
    sim.people = [person]

    assert sim.is_finished() is False


def test_is_finished_false_when_someone_is_grave():
    sim = make_simulation()
    person = Person(x=0, y=0)
    person.set_grave(3)
    sim.people = [person]

    assert sim.is_finished() is False


def test_is_finished_true_when_nobody_is_infected_or_grave():
    sim = make_simulation()
    susceptible = Person(x=0, y=0)
    recovered = Person(x=0, y=0)
    recovered.recover()
    dead = Person(x=0, y=0)
    dead.die()
    sim.people = [susceptible, recovered, dead]

    assert sim.is_finished() is True


def test_invariants_hold_through_a_full_run():
    sim = make_simulation(
        population=15, initial_infected=5, transmission_probability=0.6,
        infection_radius=20, pct_grave=0.5, mortality_hospitalized=0.2,
        mortality_waiting=0.6, infection_duration=3, grave_duration=2,
        initial_beds=3, width=200, height=200,
        random_fn=random.Random(42).random,
    )
    sim.populate()

    for _ in range(30):
        sim.update()

        assert sim.hospital.occupied == sum(1 for p in sim.people if p.hospitalized)
        assert sim.hospital.occupied <= sim.hospital.capacity
        waiting_grave = sum(
            1 for p in sim.people if p.state == "grave" and not p.hospitalized
        )
        assert len(sim.hospital.waiting_list) == waiting_grave

        snapshot = sim.history[-1]
        total = (snapshot["susceptible"] + snapshot["infected"]
                 + snapshot["grave"] + snapshot["recovered"] + snapshot["dead"])
        assert total == sim.population


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
