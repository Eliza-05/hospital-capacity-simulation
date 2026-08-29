"""Constantes de configuración compartidas por todo el proyecto.

Centraliza los parámetros globales para que la lógica de la simulación y
el renderizado usen siempre los mismos valores.
"""

# Área lógica donde se mueven los agentes. La simulación posiciona y
# mueve a las personas dentro de estos límites; el renderer se encarga
# de traducirlos al tamaño real del mapa en pantalla, así que cambiar
# la resolución de la ventana no altera la dinámica del modelo.
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Ancho del panel lateral original. Se conserva porque define la ventana
# mínima esperada por los tests de dibujado.
PANEL_WIDTH = 260

# Cuadros por segundo de la ventana. Solo afecta la fluidez de las
# animaciones: la velocidad del modelo la fija CYCLE_RATE.
FPS = 60

# Ciclos de simulación por segundo a velocidad x1. La tecla de velocidad
# multiplica este valor, de modo que acelerar no cambia cuántos frames se
# dibujan sino cuántos ciclos entran en cada uno.
#
# Es la perilla para que la simulación se vea más calma: bajarlo hace que
# las personas se desplacen más despacio en pantalla y que la epidemia
# avance más lento, sin tocar el modelo. Cuánto se mueve cada persona por
# ciclo (`step` en Person.move) sí es parte del modelo: cambiarlo alteraría
# la mezcla de la población y, con ella, los resultados del Excel.
CYCLE_RATE = 10
