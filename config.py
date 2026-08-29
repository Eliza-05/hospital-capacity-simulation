"""Constantes de configuración compartidas por todo el proyecto.

Centraliza parámetros globales, como las dimensiones de la ventana de
Pygame, para que los distintos módulos de la simulación (lógica y
renderizado) usen siempre los mismos valores.
"""

# Área donde se mueven los agentes. La lógica de la simulación usa estos
# límites para posicionar y mover a las personas.
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Panel lateral de contadores, a la derecha del área de simulación. La
# ventana total mide SCREEN_WIDTH + PANEL_WIDTH de ancho, para que el panel
# no tape a los agentes.
PANEL_WIDTH = 260

# Frames por segundo de la ventana de Pygame. La velocidad de la simulación
# no se cambia tocando esto, sino corriendo varios update() por frame.
FPS = 12
