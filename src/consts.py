"""Constants shared between files."""

from typing import Final

from pygame import Color
from numpy import array as np_array, uint8
from numpy.typing import NDArray

from src.type_utils import RGBColor, HexColor

CHR_LIMIT: Final[int] = 1_114_111
MOUSE_LEFT: Final[int] = 0
MOUSE_WHEEL: Final[int] = 1
MOUSE_RIGHT: Final[int] = 2

BLACK: Final[Color] = Color(0, 0, 0)
WHITE: Final[Color] = Color(255, 255, 255)
DARKER_GRAY: Final[Color] = Color(50, 50, 50)

RGB_LIGHT_GRAY: Final[RGBColor] = [70, 70, 70]
RGB_DARK_GRAY: Final[RGBColor] = [60, 60, 60]
HEX_BLACK: Final[HexColor] = "000000"

# Flip x and y, when making it a surface, pygame uses it like this
EMPTY_TILE_ARR: Final[NDArray[uint8]] = np_array(
    (
        (RGB_LIGHT_GRAY, RGB_DARK_GRAY),
        (RGB_DARK_GRAY, RGB_LIGHT_GRAY)
    ),
    uint8
).transpose((1, 0, 2))
NUM_TILE_COLS: Final[int] = EMPTY_TILE_ARR.shape[0]
NUM_TILE_ROWS: Final[int] = EMPTY_TILE_ARR.shape[1]

NUM_VISIBLE_CHECKBOX_GRID_ROWS: Final[int] = 10

BG_LAYER: Final[int] = 0
ELEMENT_LAYER: Final[int] = 1
TEXT_LAYER: Final[int] = 2
TOP_LAYER: Final[int] = 3
SPECIAL_LAYER: Final[int] = 4  # Base for the special layers
UI_LAYER: Final[int] = SPECIAL_LAYER * 2  # Base for the UI layers

STATE_I_MAIN: Final[int] = 0
STATE_I_COLOR: Final[int] = 1
STATE_I_GRID: Final[int] = 2

IMG_STATE_OK: Final[int] = 0
IMG_STATE_MISSING: Final[int] = 1
IMG_STATE_DENIED: Final[int] = 2
IMG_STATE_LOCKED: Final[int] = 3
IMG_STATE_CORRUPTED: Final[int] = 4
