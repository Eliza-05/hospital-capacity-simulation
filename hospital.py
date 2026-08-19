"""Clase Hospital: capacidad de camas y lista de espera FIFO.

Responsable: Persona A (lógica)
"""

from collections import deque


class Hospital:
    """Administra las camas disponibles y la lista de espera (FIFO).

    Contrato de atributos usado por Simulation (no cambiar los nombres sin
    avisar a la otra persona del equipo):
        - capacity: int -> número total de camas configuradas
        - occupied: int -> camas actualmente ocupadas
        - free_beds: int (property) -> capacity - occupied
        - waiting_list: deque -> pacientes graves esperando cama, orden de llegada
        - is_saturated: bool (property) -> True si no hay camas libres
    """

    def __init__(self, capacity):
        self.capacity = capacity
        self.occupied = 0
        self.waiting_list = deque()

    @property
    def free_beds(self):
        """Camas libres actualmente."""
        pass

    @property
    def is_saturated(self):
        """True si no quedan camas libres."""
        pass

    def admit(self, person):
        """Asigna una cama a `person` si hay disponible; si no, lo agrega a waiting_list."""
        pass

    def discharge(self, person):
        """Libera la cama de `person` (por recuperación o fallecimiento) y
        reasigna automáticamente al primero en waiting_list, si hay alguno."""
        pass

    def set_capacity(self, new_capacity):
        """Cambia el número de camas.

        Regla: aumentar siempre se permite; reducir solo se permite si
        new_capacity >= self.occupied.
        """
        pass
