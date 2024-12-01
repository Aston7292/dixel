"""Constants shared between files."""

from typing import Final

import pygame as pg

from src.utils import Size
from src.type_utils import Color

CHR_LIMIT: Final[int] = 1_114_111

ACCESS_SUCCESS: Final[int] = 0
ACCESS_MISSING: Final[int] = 1
ACCESS_DENIED: Final[int] = 2
ACCESS_LOCKED: Final[int] = 3

INIT_WIN_SIZE: Final[Size] = Size(1_200, 900)

BLACK: Final[Color] = (0, 0, 0)
WHITE: Final[Color] = (255, 255, 255)
LIGHT_GRAY: Final[Color] = (85, 85, 85)
DARK_GRAY: Final[Color] = (75, 75, 75)

EMPTY_TILE_IMG: pg.Surface = pg.Surface((2, 2))
for y in range(2):
    for x in range(2):
        pixel_color: Color = DARK_GRAY if (x + y) % 2 else LIGHT_GRAY
        EMPTY_TILE_IMG.set_at((x, y), pixel_color)

BG_LAYER: Final[int] = 0
ELEMENT_LAYER: Final[int] = 1
TEXT_LAYER: Final[int] = 2
TOP_LAYER: Final[int] = 3
SPECIAL_LAYER: Final[int] = 4  # Base for the special layers
UI_LAYER: Final[int] = SPECIAL_LAYER * 2  # Base for the UI layers
