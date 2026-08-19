"""Punto de entrada: arma la simulación y la corre.

Uso previsto:
    - Modo interactivo (demo/video): una corrida con parámetros configurables
      y controles en vivo (UP/DOWN, SPACE, LEFT/RIGHT).
    - Modo comparación (Excel): correr varios escenarios (5/10/20 camas) con
      semilla fija y capacidad fija por corrida, exportando todo a Excel.
"""

import random

import numpy as np

from simulation import Simulation
from exporter import export_results


def run_interactive():
    """Corre una simulación con visualización y controles en vivo."""
    pass


def run_comparison(bed_scenarios, seed):
    """Corre un escenario por cada valor en `bed_scenarios`, todos con la
    misma semilla aleatoria y capacidad fija, y exporta los resultados."""
    pass


if __name__ == "__main__":
    pass
