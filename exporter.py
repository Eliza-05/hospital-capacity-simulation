"""Exportación de resultados a Excel usando pandas.

Responsable: Persona B

Lee `simulation.history` (lista de dicts, un registro por frame) para
generar, por cada corrida, una hoja `timeline_run_N`, y una hoja `resumen`
con una fila agregada por escenario ejecutado.
"""


def export_timeline(history, sheet_name, writer):
    """Escribe la hoja timeline_run_N a partir de `history`."""
    pass


def build_summary_row(run_params, history):
    """Calcula la fila de resumen de un escenario: camas usadas, pico de
    ocupación, muertos, pacientes sin cama, tiempo saturado, etc."""
    pass


def export_results(runs, output_path):
    """Genera el archivo .xlsx completo.

    `runs`: lista de tuplas (run_params, history), una por escenario.
    Escribe una hoja timeline por corrida + una hoja `resumen` consolidada.
    """
    pass
