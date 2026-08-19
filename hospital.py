"""Clase Hospital: capacidad de camas y lista de espera.

Modela el hospital de la simulación: cuántas camas tiene disponibles,
cuáles están ocupadas y qué pacientes graves quedan esperando cuando
no hay cupo. Es usada por la simulación para decidir qué pasa con cada
persona que se agrava o se recupera.
"""

from collections import deque


class Hospital:
    """Administra las camas disponibles y la lista de espera de pacientes.

    El hospital tiene una capacidad total de camas y lleva la cuenta de
    cuántas están ocupadas en cada momento. Cuando un paciente grave
    llega y no hay camas libres, se agrega a una lista de espera y se le
    asigna una cama automáticamente en cuanto se libera alguna, respetando
    el orden de llegada.
    """

    def __init__(self, capacity):
        self.capacity = capacity
        self.occupied = 0
        self.waiting_list = deque()

    @property
    def free_beds(self):
        """Cantidad de camas que siguen disponibles en este momento."""
        return self.capacity - self.occupied

    @property
    def is_saturated(self):
        """Indica si el hospital está lleno y no tienecamas libres."""
        return self.free_beds <= 0

    def admit(self, person):
        """Ingresa a una persona al hospital si hay cama disponible.
        Si no la hay, la persona pasa a la lista de espera."""
        if self.free_beds > 0:
            self.occupied += 1
            person.hospitalized = True
        else:
            self.waiting_list.append(person)

    def discharge(self, person):
        """Da de alta a una persona, liberando su cama (ya sea porque se
        recuperó o porque falleció), y de inmediato ingresa al primero
        de la lista de espera, si hay alguien esperando."""
        self.occupied -= 1
        person.hospitalized = False
        if self.waiting_list:
            next_person = self.waiting_list.popleft()
            self.admit(next_person)

    def set_capacity(self, new_capacity):
        """Cambia el número total de camas del hospital.

        Se puede aumentar la capacidad libremente, pero no se puede
        reducir por debajo de la cantidad de camas ya ocupadas. Devuelve
        True si el cambio se aplicó y False si fue rechazado
        """
        if new_capacity < self.occupied:
            return False
        self.capacity = new_capacity
        return True

    def remove_from_waiting_list(self, person):
        """Saca a una persona de la lista de espera si estaba en ella.

        Se usa cuando un paciente grave se recupera o fallece mientras
        todavía estaba esperando cama, para que no quede en la lista

        """
        if person in self.waiting_list:
            self.waiting_list.remove(person)
