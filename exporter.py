"""Exportación de resultados a Excel usando pandas.

Responsable: Persona B

Lee `simulation.history` (lista de dicts, un registro por frame) para
generar, por cada corrida, una hoja `timeline_run_N`, y una hoja `resumen`
con una fila agregada por escenario ejecutado.
"""

import pandas as pd
from openpyxl.chart import BarChart, LineChart, Reference

# Orden y nombre en español de las columnas de las hojas `timeline_run_N`.
# `camas_ocupadas` no viene en `history`: se deriva de capacidad - libres.
TIMELINE_COLUMNS = [
    ("cycle", "ciclo"),
    ("susceptible", "susceptibles"),
    ("infected", "infectados"),
    ("grave", "graves"),
    ("hospitalized", "hospitalizados"),
    ("waiting", "en_espera"),
    ("recovered", "recuperados"),
    ("dead", "fallecidos"),
    ("occupied", "camas_ocupadas"),
    ("free_beds", "camas_libres"),
    ("capacity", "capacidad"),
    ("saturated", "saturado"),
]

# Series que se grafican en el eje Y de cada hoja timeline.
TIMELINE_CHART_SERIES = ["infectados", "graves", "hospitalizados",
                         "en_espera", "fallecidos"]

# Nombre en español de los parámetros del escenario en la hoja `resumen`.
PARAM_COLUMNS = [
    ("escenario", "escenario"),
    ("seed", "semilla"),
    ("initial_beds", "camas"),
    ("population", "poblacion"),
    ("initial_infected", "infectados_iniciales"),
    ("transmission_probability", "prob_contagio"),
    ("infection_radius", "radio_contagio"),
    ("pct_grave", "pct_graves"),
    ("infection_duration", "dur_infeccion"),
    ("grave_duration", "dur_gravedad"),
    ("mortality_hospitalized", "mortalidad_con_cama"),
    ("mortality_waiting", "mortalidad_sin_cama"),
]


def _timeline_dataframe(history):
    """Convierte `history` en un DataFrame con las columnas ordenadas y
    renombradas al español, agregando `camas_ocupadas`."""
    df = pd.DataFrame(list(history))
    if df.empty:
        return pd.DataFrame(columns=[label for _, label in TIMELINE_COLUMNS])

    df["occupied"] = df["capacity"] - df["free_beds"]
    keys = [key for key, _ in TIMELINE_COLUMNS if key in df.columns]
    df = df[keys]
    return df.rename(columns=dict(TIMELINE_COLUMNS))


def export_timeline(history, sheet_name, writer):
    """Escribe la hoja timeline_run_N a partir de `history`."""
    df = _timeline_dataframe(history)
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    return df


def build_summary_row(run_params, history):
    """Calcula la fila de resumen de un escenario: camas usadas, pico de
    ocupación, muertos, pacientes sin cama, tiempo saturado, etc."""
    row = {}
    for key, label in PARAM_COLUMNS:
        if key in run_params:
            row[label] = run_params[key]
    # Cualquier parámetro extra que no esté en PARAM_COLUMNS se conserva.
    known = {key for key, _ in PARAM_COLUMNS}
    for key, value in run_params.items():
        if key not in known and isinstance(value, (int, float, str, bool)):
            row[key] = value

    if not history:
        return row

    final = history[-1]
    poblacion = (final["susceptible"] + final["infected"] + final["grave"]
                 + final["recovered"] + final["dead"])
    ocupadas = [r["capacity"] - r["free_beds"] for r in history]
    ciclos_saturado = sum(1 for r in history if r["saturated"])
    # Contagiados alguna vez = todos menos los que nunca se enfermaron.
    contagiados = poblacion - final["susceptible"]

    row.update({
        "ciclos_simulados": final["cycle"],
        "contagiados_totales": contagiados,
        "fallecidos": final["dead"],
        "recuperados": final["recovered"],
        "nunca_contagiados": final["susceptible"],
        "tasa_mortalidad_poblacion": round(final["dead"] / poblacion, 4) if poblacion else 0,
        "tasa_letalidad_contagiados": round(final["dead"] / contagiados, 4) if contagiados else 0,
        "pico_infectados": max(r["infected"] for r in history),
        "pico_graves": max(r["grave"] for r in history),
        "pico_camas_ocupadas": max(ocupadas),
        "pico_en_espera": max(r["waiting"] for r in history),
        # Suma de personas-ciclo sin cama: mide la carga total de desatención,
        # no solo el peor momento.
        "espera_acumulada_persona_ciclo": sum(r["waiting"] for r in history),
        "ciclos_con_pacientes_sin_cama": sum(1 for r in history if r["waiting"] > 0),
        "ciclos_saturado": ciclos_saturado,
        "pct_tiempo_saturado": round(ciclos_saturado / len(history), 4),
    })
    return row


def _add_timeline_chart(worksheet, n_rows, columns):
    """Agrega a una hoja timeline un gráfico de líneas de la evolución
    de la epidemia, para poder usarlo directamente en la presentación."""
    if n_rows < 2:
        return
    chart = LineChart()
    chart.title = "Evolución de la epidemia"
    chart.x_axis.title = "ciclo"
    chart.y_axis.title = "personas"
    chart.height, chart.width = 10, 24

    for name in TIMELINE_CHART_SERIES:
        if name not in columns:
            continue
        col = columns.index(name) + 1
        chart.add_data(Reference(worksheet, min_col=col, min_row=1,
                                 max_row=n_rows + 1), titles_from_data=True)
    chart.set_categories(Reference(worksheet, min_col=columns.index("ciclo") + 1,
                                   min_row=2, max_row=n_rows + 1))
    for serie in chart.series:
        serie.smooth = False
    worksheet.add_chart(chart, f"A{n_rows + 4}")


def _add_summary_charts(worksheet, n_rows, columns):
    """Agrega a la hoja `resumen` dos gráficos de barras comparando los
    escenarios: fallecidos y tiempo saturado según el número de camas."""
    if n_rows < 1 or "camas" not in columns:
        return
    camas_col = columns.index("camas") + 1
    anchor_row = n_rows + 4

    for titulo, columna, eje_y, ancla in (
        ("Fallecidos según capacidad hospitalaria", "fallecidos", "personas", "A"),
        ("Ciclos con hospital saturado", "ciclos_saturado", "ciclos", "L"),
    ):
        if columna not in columns:
            continue
        chart = BarChart()
        chart.type = "col"
        chart.title = titulo
        chart.x_axis.title = "camas"
        chart.y_axis.title = eje_y
        chart.height, chart.width = 9, 14
        col = columns.index(columna) + 1
        chart.add_data(Reference(worksheet, min_col=col, min_row=1,
                                 max_row=n_rows + 1), titles_from_data=True)
        chart.set_categories(Reference(worksheet, min_col=camas_col,
                                       min_row=2, max_row=n_rows + 1))
        worksheet.add_chart(chart, f"{ancla}{anchor_row}")


def build_average_summary(summary, group_column="camas"):
    """Promedia las filas de `resumen` que comparten capacidad.

    La simulación es probabilística: una sola corrida por escenario puede
    dar una comparación engañosa. Cuando se corren varias repeticiones,
    esta hoja es la que hay que mirar para responder la pregunta de
    decisión (ver docs, sección 1.7)."""
    numeric = summary.select_dtypes(include="number")
    promedios = numeric.groupby(summary[group_column]).mean().round(2)
    promedios.insert(0, "repeticiones",
                     summary.groupby(group_column).size())
    return promedios.reset_index()


def export_results(runs, output_path, promediar=False):
    """Genera el archivo .xlsx completo.

    `runs`: lista de tuplas (run_params, history), una por escenario.
    Escribe una hoja timeline por corrida + una hoja `resumen` consolidada.
    Con `promediar=True` agrega además una hoja `promedios` que agrupa las
    repeticiones de cada capacidad, y es ahí donde van los gráficos
    comparativos.
    """
    summary = pd.DataFrame([build_summary_row(params, history)
                            for params, history in runs])
    promedios = (build_average_summary(summary)
                 if promediar and "camas" in summary.columns else None)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # `resumen` primero para que sea la hoja que se abre por defecto.
        summary.to_excel(writer, sheet_name="resumen", index=False)

        if promedios is not None:
            promedios.to_excel(writer, sheet_name="promedios", index=False)
            _add_summary_charts(writer.sheets["promedios"], len(promedios),
                                list(promedios.columns))
        else:
            _add_summary_charts(writer.sheets["resumen"], len(summary),
                                list(summary.columns))

        for i, (_, history) in enumerate(runs, start=1):
            sheet_name = f"timeline_run_{i}"
            df = export_timeline(history, sheet_name, writer)
            _add_timeline_chart(writer.sheets[sheet_name], len(df),
                                list(df.columns))

    return output_path
