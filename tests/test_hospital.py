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
