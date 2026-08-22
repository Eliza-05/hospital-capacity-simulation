"""Punto de entrada: arma la simulación y la corre.

Uso previsto:
    - Modo interactivo (demo/video): una corrida con parámetros configurables
      y controles en vivo (UP/DOWN, SPACE, LEFT/RIGHT).
    - Modo comparación (Excel): correr varios escenarios (5/10/20 camas) con
      semilla fija y capacidad fija por corrida, exportando todo a Excel.

    python main.py                     -> modo interactivo (semilla fija)
    python main.py --random            -> modo interactivo, semilla al azar
    python main.py --comparar          -> modo comparación (genera el .xlsx)
    python main.py --comparar --reps 1 -> una sola corrida por escenario
"""

import os
import random
import sys

from simulation import Simulation
from exporter import export_results

# Parámetros del modelo, iguales para todos los escenarios. Lo único que
# cambia entre corridas es la capacidad del hospital (ver docs, sección 1.7).
SIM_PARAMS = {
    "population": 300,
    "initial_infected": 5,
    "transmission_probability": 0.10,
    "infection_radius": 45,
    "pct_grave": 0.30,
    "infection_duration": 60,
    "grave_duration": 40,
    "mortality_hospitalized": 0.15,
    "mortality_waiting": 0.60,
}

BED_SCENARIOS = (5, 10, 20)
SEED = 42
INTERACTIVE_BEDS = 10

# Repeticiones por escenario. Con una sola corrida el azar alcanza para
# invertir la comparación entre capacidades (lo verificamos: con la semilla
# 99, 10 camas daba más muertos que 5). Promediar varias corridas con las
# mismas semillas en los 3 escenarios hace que la comparación se sostenga.
REPETICIONES = 5

RESULTS_DIR = "resultados"
OUTPUT_FILE = os.path.join(RESULTS_DIR, "comparacion_camas.xlsx")

# Corte de seguridad: si por los parámetros elegidos la epidemia no se
# apagara nunca, la corrida termina igual en vez de colgarse.
MAX_CYCLES = 5000


def build_simulation(beds, seed, **overrides):
    """Crea una Simulation con los parámetros base, la capacidad indicada y
    un generador aleatorio propio sembrado con `seed`, para que la corrida
    sea reproducible."""
    params = dict(SIM_PARAMS)
    params.update(overrides)
    params["initial_beds"] = beds
    params["random_fn"] = random.Random(seed).random
    return Simulation(**params)


def run_headless(beds, seed, max_cycles=MAX_CYCLES):
    """Corre un escenario sin ventana hasta que la epidemia se apaga.

    Devuelve (run_params, history) listo para pasarle al exporter."""
    sim = build_simulation(beds, seed)
    sim.populate()

    cycles = 0
    while not sim.is_finished() and cycles < max_cycles:
        sim.update()
        cycles += 1

    if not sim.is_finished():
        print(f"  aviso: se cortó en {max_cycles} ciclos sin que terminara "
              f"la epidemia")

    # `history` es un agregado por ciclo y no distingue cuánto esperó cada
    # paciente; eso solo se puede leer de las personas al terminar.
    esperas = [p.cycles_waiting for p in sim.people if p.cycles_waiting > 0]

    run_params = dict(SIM_PARAMS)
    run_params.update(
        initial_beds=beds, seed=seed, escenario=f"{beds} camas",
        personas_que_esperaron=len(esperas),
        espera_promedio_ciclos=round(sum(esperas) / len(esperas), 2) if esperas else 0,
        espera_maxima_ciclos=max(esperas) if esperas else 0,
    )
    return run_params, sim.history


def run_interactive(beds=None, seed=SEED):
    """Corre una simulación con visualización y controles en vivo.

    Usa la misma semilla que el modo comparación para que la demo sea
    reproducible: garantiza que el hospital se sature y que haya algo que
    mostrar en el video, en vez de depender de que la corrida salga
    interesante por azar."""
    sim = build_simulation(INTERACTIVE_BEDS if beds is None else beds, seed)
    sim.populate()
    sim.run()


def run_comparison(bed_scenarios=BED_SCENARIOS, seed=SEED,
                   output_path=OUTPUT_FILE, repeticiones=REPETICIONES):
    """Corre un escenario por cada valor en `bed_scenarios`, todos con la
    misma semilla aleatoria y capacidad fija, y exporta los resultados.

    Con `repeticiones > 1` cada capacidad se corre varias veces con semillas
    consecutivas (`seed`, `seed+1`, ...), siempre las mismas para todas las
    capacidades. Sirve porque el modelo es probabilístico: en una sola
    corrida el azar alcanza para invertir la comparación entre escenarios."""
    # Se siembra también el RNG global por si algún módulo lo usa de forma
    # indirecta; la lógica del modelo va toda por `random_fn`.
    random.seed(seed)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    semillas = [seed + i for i in range(repeticiones)]
    runs = []
    for beds in bed_scenarios:
        for s in semillas:
            print(f"Corriendo escenario de {beds} camas (semilla {s})...")
            run_params, history = run_headless(beds, s)
            final = history[-1]
            print(f"  {final['cycle']} ciclos | fallecidos: {final['dead']} | "
                  f"pico en espera: {max(r['waiting'] for r in history)} | "
                  f"ciclos saturado: {sum(1 for r in history if r['saturated'])}")
            runs.append((run_params, history))

    export_results(runs, output_path, promediar=repeticiones > 1)
    print(f"\nExcel generado en: {output_path}")
    if repeticiones > 1:
        print(f"  {len(runs)} corridas ({repeticiones} por escenario). "
              f"Para el análisis usar la hoja `promedios`.")
    return runs


def _parse_reps(argv):
    """Lee `--reps N` de la línea de comandos."""
    if "--reps" not in argv:
        return REPETICIONES
    try:
        return max(1, int(argv[argv.index("--reps") + 1]))
    except (IndexError, ValueError):
        sys.exit("uso: python main.py --comparar --reps N")


def _resolve_seed(argv, default_seed=SEED, randint_fn=random.randint):
    """Lee `--random` de la línea de comandos: sin el flag usa la semilla
    fija (demo reproducible), con el flag sortea una nueva en cada
    corrida."""
    if "--random" not in argv:
        return default_seed
    return randint_fn(0, 999_999)


if __name__ == "__main__":
    if "--comparar" in sys.argv:
        run_comparison(repeticiones=_parse_reps(sys.argv))
    else:
        run_interactive(seed=_resolve_seed(sys.argv))
