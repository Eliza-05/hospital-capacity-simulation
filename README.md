# hospital-capacity-simulation
Simulación en Pygame de una epidemia con capacidad hospitalaria limitada: agentes que se contagian, hospital con camas y lista de espera FIFO, controles en tiempo real y exportación a Excel para analizar cómo la capacidad afecta la mortalidad y la saturación del sistema.

Detalle completo del alcance, la pregunta de decisión y la organización del equipo: [`docs/alcance_y_plan_de_trabajo.md`](docs/alcance_y_plan_de_trabajo.md). Checklist de avance: [`TODO.md`](TODO.md).

## Estructura del proyecto

```
hospital-capacity-simulation/
├── README.md
├── requirements.txt
├── person.py          # clase Person (Persona A)
├── hospital.py         # clase Hospital: capacidad, waiting_list (Persona A)
├── simulation.py        # clase Simulation: lógica (Persona A) + draw()/eventos (Persona B)
├── exporter.py            # self.history -> Excel (Persona B)
├── main.py                 # arma todo y corre
├── resultados/               # .xlsx generados por cada escenario
├── docs/
│   └── alcance_y_plan_de_trabajo.md
└── TODO.md
```

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

*(Pendiente de implementar — ver `TODO.md`.)*

## Equipo

| Persona | Responsabilidad |
|---|---|
| _(completar)_ | Lógica: `person.py`, `hospital.py`, métodos de lógica en `simulation.py` |
| _(completar)_ | Visualización/controles: `draw()` y eventos en `simulation.py`, `exporter.py` |
