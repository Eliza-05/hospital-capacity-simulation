from hospital import Hospital
from person import Person


def test_admit_occupies_a_bed_when_free_beds_available():
    hospital = Hospital(capacity=2)
    person = Person(x=0, y=0)

    hospital.admit(person)

    assert hospital.occupied == 1
    assert hospital.free_beds == 1
    assert person.hospitalized is True


def test_admit_queues_person_when_no_free_beds():
    hospital = Hospital(capacity=1)
    first = Person(x=0, y=0)
    second = Person(x=0, y=0)
    hospital.admit(first)

    hospital.admit(second)

    assert hospital.occupied == 1
    assert second.hospitalized is False
    assert list(hospital.waiting_list) == [second]


def test_hospital_is_saturated_when_no_free_beds():
    hospital = Hospital(capacity=1)
    assert hospital.is_saturated is False

    hospital.admit(Person(x=0, y=0))

    assert hospital.is_saturated is True


def test_discharge_frees_the_bed_when_nobody_is_waiting():
    hospital = Hospital(capacity=1)
    person = Person(x=0, y=0)
    hospital.admit(person)

    hospital.discharge(person)

    assert hospital.occupied == 0
    assert person.hospitalized is False


def test_discharge_reassigns_freed_bed_to_first_in_waiting_list():
    hospital = Hospital(capacity=1)
    first = Person(x=0, y=0)
    second = Person(x=0, y=0)
    third = Person(x=0, y=0)
    hospital.admit(first)
    hospital.admit(second)
    hospital.admit(third)

    hospital.discharge(first)

    assert first.hospitalized is False
    assert second.hospitalized is True
    assert hospital.occupied == 1
    assert list(hospital.waiting_list) == [third]


def test_set_capacity_always_allows_increasing():
    hospital = Hospital(capacity=2)

    result = hospital.set_capacity(5)

    assert result is True
    assert hospital.capacity == 5


def test_set_capacity_allows_decreasing_to_exactly_occupied_beds():
    hospital = Hospital(capacity=3)
    hospital.admit(Person(x=0, y=0))
    hospital.admit(Person(x=0, y=0))

    result = hospital.set_capacity(2)

    assert result is True
    assert hospital.capacity == 2


def test_set_capacity_rejects_decreasing_below_occupied_beds():
    hospital = Hospital(capacity=3)
    hospital.admit(Person(x=0, y=0))
    hospital.admit(Person(x=0, y=0))

    result = hospital.set_capacity(1)

    assert result is False
    assert hospital.capacity == 3


def test_occupied_matches_number_of_hospitalized_people_through_several_operations():
    hospital = Hospital(capacity=3)
    people = [Person(x=0, y=0) for _ in range(5)]
    for person in people:
        hospital.admit(person)
    assert hospital.occupied == sum(1 for p in people if p.hospitalized)

    hospital.discharge(people[0])
    assert hospital.occupied == sum(1 for p in people if p.hospitalized)

    hospital.set_capacity(5)
    assert hospital.occupied == sum(1 for p in people if p.hospitalized)

    hospital.set_capacity(2)
    assert hospital.occupied == sum(1 for p in people if p.hospitalized)


def test_occupied_never_exceeds_capacity_through_several_operations():
    hospital = Hospital(capacity=2)
    people = [Person(x=0, y=0) for _ in range(6)]
    for person in people:
        hospital.admit(person)
        assert hospital.occupied <= hospital.capacity

    hospital.set_capacity(4)
    assert hospital.occupied <= hospital.capacity

    hospital.discharge(people[0])
    assert hospital.occupied <= hospital.capacity


def test_waiting_list_length_matches_people_still_without_a_bed():
    hospital = Hospital(capacity=2)
    people = [Person(x=0, y=0) for _ in range(5)]
    for person in people:
        hospital.admit(person)

    # "sigue en el sistema" = todavía hospitalizado o en la lista de espera;
    # a quien ya se le dio de alta (recuperado/fallecido en el flujo real)
    # deja de contar para esta invariante.
    still_in_system = list(people)
    assert len(hospital.waiting_list) == sum(1 for p in still_in_system if not p.hospitalized)

    hospital.discharge(people[0])
    still_in_system.remove(people[0])

    assert len(hospital.waiting_list) == sum(1 for p in still_in_system if not p.hospitalized)


def test_discharge_on_empty_hospital_does_not_go_negative():
    hospital = Hospital(capacity=1)
    person = Person(x=0, y=0)

    hospital.discharge(person)

    assert hospital.occupied == 0


def test_set_capacity_increase_admits_everyone_waiting_if_enough_new_beds():
    hospital = Hospital(capacity=1)
    occupant = Person(x=0, y=0)
    hospital.admit(occupant)
    waiting = [Person(x=0, y=0) for _ in range(3)]
    for person in waiting:
        hospital.admit(person)

    hospital.set_capacity(4)

    assert hospital.capacity == 4
    assert hospital.occupied == 4
    assert list(hospital.waiting_list) == []
    assert all(person.hospitalized for person in waiting)


def test_set_capacity_increase_admits_only_as_many_as_fit_and_keeps_fifo_order():
    hospital = Hospital(capacity=1)
    occupant = Person(x=0, y=0)
    hospital.admit(occupant)
    waiting = [Person(x=0, y=0) for _ in range(5)]
    for person in waiting:
        hospital.admit(person)

    hospital.set_capacity(3)

    assert hospital.occupied == 3
    assert list(hospital.waiting_list) == waiting[2:]
    assert waiting[0].hospitalized is True
    assert waiting[1].hospitalized is True
    assert waiting[2].hospitalized is False


def test_remove_from_waiting_list_drops_a_queued_person():
    hospital = Hospital(capacity=1)
    occupant = Person(x=0, y=0)
    waiting = Person(x=0, y=0)
    hospital.admit(occupant)
    hospital.admit(waiting)

    hospital.remove_from_waiting_list(waiting)

    assert list(hospital.waiting_list) == []


def test_remove_from_waiting_list_is_a_no_op_for_person_not_queued():
    hospital = Hospital(capacity=1)
    occupant = Person(x=0, y=0)
    hospital.admit(occupant)

    hospital.remove_from_waiting_list(occupant)

    assert hospital.occupied == 1
