"""Paleta, tipografías y primitivas de dibujo de la interfaz.

Concentra todo lo puramente estético de la simulación: los colores de la
interfaz y de cada estado epidemiológico, las fuentes que usa el HUD y un
puñado de ayudantes de dibujo (paneles redondeados, texto alineado,
resplandores, barras) que `renderer.py` combina para armar la pantalla.

No sabe nada del modelo: recibe superficies y rectángulos, y dibuja.
"""

import math
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

# ----------------------------------------------------------------------
# Lienzo lógico
# ----------------------------------------------------------------------

# Todo se dibuja siempre sobre un lienzo de este tamaño y recién al final
# se escala a la ventana real. Así el diseño no depende de la resolución
# del monitor: las posiciones y tamaños de acá son fijos y confiables.
CANVAS_WIDTH = 1440
CANVAS_HEIGHT = 860


# ----------------------------------------------------------------------
# Paleta
# ----------------------------------------------------------------------

# Fondos, del más oscuro (lienzo) al más claro (tarjetas destacadas).
BG = (11, 14, 20)
SURFACE = (22, 27, 36)
SURFACE_ALT = (29, 36, 48)
SURFACE_HI = (38, 47, 62)
BORDER = (44, 55, 72)
BORDER_HI = (70, 86, 110)

# Texto, en tres niveles de jerarquía.
TEXT = (231, 236, 245)
TEXT_DIM = (146, 157, 176)
TEXT_FAINT = (98, 108, 126)

# Un color por estado epidemiológico. Son los mismos que usa el panel,
# la leyenda, el gráfico y los agentes, para que el ojo asocie siempre
# color y significado.
STATE_COLORS = {
    "susceptible": (76, 141, 246),   # azul
    "infected": (242, 163, 60),      # naranja
    "grave": (233, 70, 75),          # rojo
    "recovered": (63, 207, 142),     # verde
    "dead": (138, 124, 184),         # violeta
}
STATE_LABELS = (
    ("susceptible", "Susceptibles"),
    ("infected", "Infectados"),
    ("grave", "Graves"),
    ("recovered", "Recuperados"),
    ("dead", "Fallecidos"),
)

# Colores propios del hospital.
BED_FREE = (74, 92, 118)         # cama vacía
BED_OCCUPIED = (232, 238, 245)   # cama con paciente
WAITING = (255, 201, 74)         # ámbar de la sala de espera
DANGER = (255, 77, 87)           # saturación y avisos críticos
OK = (63, 207, 142)              # altas y confirmaciones
INFO = (86, 178, 255)            # traslados y avisos neutros

# Escala de riesgo (verde -> ámbar -> rojo) para las barras de deterioro.
RISK_LOW = (63, 207, 142)
RISK_MID = (255, 201, 74)
RISK_HIGH = (233, 70, 75)


# ----------------------------------------------------------------------
# Tipografías
# ----------------------------------------------------------------------

# Familias por preferencia: pygame toma la primera que exista en el
# sistema, así se ve bien tanto en macOS como en Linux o Windows.
_UI_FAMILY = "Helvetica Neue,Helvetica,Segoe UI,DejaVu Sans,Arial"
_MONO_FAMILY = "SF Mono,Menlo,Consolas,DejaVu Sans Mono,Courier New"

_FONT_SPECS = {
    "h1": (_UI_FAMILY, 22, True),
    "h2": (_UI_FAMILY, 14, True),
    "body": (_UI_FAMILY, 15, False),
    "body_b": (_UI_FAMILY, 15, True),
    "small": (_UI_FAMILY, 13, False),
    "small_b": (_UI_FAMILY, 13, True),
    "tiny": (_UI_FAMILY, 11, False),
    "tiny_b": (_UI_FAMILY, 11, True),
    "num": (_MONO_FAMILY, 15, True),
    "num_lg": (_MONO_FAMILY, 26, True),
    "num_sm": (_MONO_FAMILY, 12, True),
    "banner": (_UI_FAMILY, 20, True),
}

_fonts = {}


def fonts():
    """Devuelve el diccionario de fuentes, creándolo la primera vez.

    Se cachea porque construir una fuente es caro y acá se dibuja texto
    decenas de veces por frame."""
    if not _fonts:
        if not pygame.font.get_init():
            pygame.font.init()
        for name, (family, size, bold) in _FONT_SPECS.items():
            _fonts[name] = pygame.font.SysFont(family, size, bold=bold)
    return _fonts


# ----------------------------------------------------------------------
# Utilidades de color y animación
# ----------------------------------------------------------------------

def lerp(a, b, t):
    """Interpola linealmente entre dos números."""
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    """Mezcla dos colores; `t` va de 0 (el primero) a 1 (el segundo)."""
    t = min(max(t, 0.0), 1.0)
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))


def risk_color(fraction):
    """Color de una barra de riesgo: verde cuando recién empieza, ámbar
    a mitad de camino y rojo cuando el paciente está al límite."""
    fraction = min(max(fraction, 0.0), 1.0)
    if fraction < 0.5:
        return lerp_color(RISK_LOW, RISK_MID, fraction * 2)
    return lerp_color(RISK_MID, RISK_HIGH, (fraction - 0.5) * 2)


def shade(color, factor):
    """Aclara (factor > 1) u oscurece (factor < 1) un color."""
    return tuple(min(255, max(0, int(c * factor))) for c in color)


def ease_in_out(t):
    """Curva suave: arranca lento, acelera y frena al llegar. Se usa en
    los traslados de pacientes para que no se muevan como robots."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def ease_out_back(t):
    """Curva con un pequeño rebote al final. Se usa cuando aparece una
    cama nueva, para que el cambio se note."""
    t = min(max(t, 0.0), 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def pulse(frame, period=48, low=0.35, high=1.0):
    """Oscilación suave entre `low` y `high`, útil para latidos y alertas."""
    phase = (math.sin(frame * 2 * math.pi / period) + 1) / 2
    return low + (high - low) * phase


# ----------------------------------------------------------------------
# Primitivas de dibujo
# ----------------------------------------------------------------------

def fill_background(surface):
    """Pinta el fondo del lienzo con una viñeta muy suave, para que el
    contenido del centro resalte sobre los bordes."""
    surface.fill(BG)


def card(surface, rect, fill=SURFACE, border=BORDER, radius=10, width=1):
    """Dibuja una tarjeta: rectángulo redondeado con borde fino. Es la
    caja base de todos los bloques de la interfaz."""
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if width:
        pygame.draw.rect(surface, border, rect, width=width,
                         border_radius=radius)


def text(surface, key, string, pos, color=TEXT, align="left"):
    """Escribe una línea de texto y devuelve el rectángulo que ocupó.

    `align` acepta "left", "right" o "center" y se interpreta respecto de
    `pos`, lo que evita tener que calcular anchos en cada llamada."""
    surf = fonts()[key].render(str(string), True, color)
    rect = surf.get_rect()
    if align == "right":
        rect.topright = pos
    elif align == "center":
        rect.midtop = pos
    else:
        rect.topleft = pos
    surface.blit(surf, rect)
    return rect


def section_title(surface, rect, title, subtitle=None, color=TEXT_DIM):
    """Encabezado de un bloque del panel: título en versalitas y una
    línea divisoria fina debajo. Devuelve la Y donde sigue el contenido."""
    text(surface, "h2", title.upper(), (rect.x, rect.y), color)
    if subtitle:
        text(surface, "tiny", subtitle, (rect.right, rect.y + 3), TEXT_FAINT,
             align="right")
    y = rect.y + 20
    pygame.draw.line(surface, BORDER, (rect.x, y), (rect.right, y), 1)
    return y + 10


_glow_cache = {}


def glow(radius, color, intensity=0.55):
    """Devuelve (y cachea) un halo circular difuso del color pedido.

    Se dibuja una sola vez por combinación y después se pega con mezcla
    aditiva, que es mucho más barato que recalcular el degradado."""
    key = (radius, color, round(intensity, 2))
    cached = _glow_cache.get(key)
    if cached is not None:
        return cached

    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        # El alfa cae con el cuadrado del radio: da un degradado más
        # parecido a una luz real que uno lineal.
        falloff = (1 - r / radius) ** 2
        alpha = int(255 * intensity * falloff)
        if alpha <= 0:
            continue
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), r)
    _glow_cache[key] = surf
    return surf


def blit_glow(surface, radius, color, center, intensity=0.55):
    """Pega un halo centrado en `center` sumando luz sobre el fondo."""
    sprite = glow(radius, color, intensity)
    surface.blit(sprite, (center[0] - radius, center[1] - radius),
                 special_flags=pygame.BLEND_RGBA_ADD)


def dot(surface, center, radius, color, outline=None, outline_width=1):
    """Círculo antialiaseado, con borde opcional. Los agentes se dibujan
    con esto: el borde oscuro los separa entre sí cuando se amontonan."""
    x, y = int(center[0]), int(center[1])
    pygame.draw.aacircle(surface, color, (x, y), radius)
    if outline is not None:
        pygame.draw.aacircle(surface, outline, (x, y), radius, outline_width)


def bar(surface, rect, fraction, color, back=SURFACE_HI, radius=3):
    """Barra de progreso horizontal recortada al rango [0, 1]."""
    pygame.draw.rect(surface, back, rect, border_radius=radius)
    fraction = min(max(fraction, 0.0), 1.0)
    filled = int(rect.width * fraction)
    if filled > 0:
        pygame.draw.rect(surface, color,
                         pygame.Rect(rect.x, rect.y, max(filled, 2),
                                     rect.height),
                         border_radius=radius)


def stacked_bar(surface, rect, segments, radius=4):
    """Barra apilada: una sola barra dividida en tramos proporcionales.

    `segments` es una lista de (valor, color). Sirve para mostrar de un
    vistazo cómo se reparte la población entre estados."""
    total = sum(value for value, _ in segments)
    pygame.draw.rect(surface, SURFACE_HI, rect, border_radius=radius)
    if total <= 0:
        return

    # Se dibuja sobre una capa aparte y se recorta con la máscara del
    # rectángulo redondeado, así los extremos quedan con las esquinas
    # curvas sin tener que dibujar cada tramo redondeado.
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    x = 0.0
    for value, color in segments:
        width = rect.width * value / total
        if width > 0:
            pygame.draw.rect(layer, color,
                             pygame.Rect(int(x), 0,
                                         max(int(round(width)), 1),
                                         rect.height))
        x += width

    mask = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                     border_radius=radius)
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(layer, rect.topleft)


def keycap(surface, pos, label):
    """Dibuja una tecla estilo teclado y devuelve su rectángulo."""
    font = fonts()["tiny_b"]
    width = max(font.size(label)[0] + 14, 24)
    rect = pygame.Rect(pos[0], pos[1], width, 19)
    pygame.draw.rect(surface, SURFACE_HI, rect, border_radius=4)
    pygame.draw.rect(surface, BORDER_HI, rect, width=1, border_radius=4)
    surf = font.render(label, True, TEXT_DIM)
    surface.blit(surf, surf.get_rect(center=rect.center))
    return rect


def chip(surface, pos, label, color, filled=False):
    """Etiqueta compacta (píldora) para estados y avisos del encabezado."""
    font = fonts()["tiny_b"]
    surf = font.render(label.upper(), True, BG if filled else color)
    rect = pygame.Rect(pos[0], pos[1], surf.get_width() + 18, 22)
    if filled:
        pygame.draw.rect(surface, color, rect, border_radius=11)
    else:
        pygame.draw.rect(surface, shade(color, 0.22), rect, border_radius=11)
        pygame.draw.rect(surface, color, rect, width=1, border_radius=11)
    surface.blit(surf, surf.get_rect(center=rect.center))
    return rect


def alpha_rect(surface, rect, color, alpha, radius=0):
    """Rectángulo semitransparente, para bandas y velos sobre el mapa."""
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (*color, alpha), layer.get_rect(),
                     border_radius=radius)
    surface.blit(layer, rect.topleft)


def glow_border(surface, rect, color, alpha, radius=10, width=2):
    """Contorno luminoso alrededor de un bloque. Se usa para marcar el
    hospital cuando está saturado, sin tapar lo que hay adentro."""
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    for i in range(3, 0, -1):
        pygame.draw.rect(layer, (*color, max(int(alpha / (i * 2)), 0)),
                         layer.get_rect().inflate(-i, -i),
                         width=width + i * 2, border_radius=radius + i)
    pygame.draw.rect(layer, (*color, alpha), layer.get_rect(), width=width,
                     border_radius=radius)
    surface.blit(layer, rect.topleft)
