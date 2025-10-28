"""Constants shared between files."""

from typing import Literal, Final

import numpy as np
from pygame import Color, event
from numpy import uint8
from numpy.typing import NDArray

from src.type_utils import RGBColor, HexColor


BLACK: Final[Color]       = Color(0  , 0  , 0)
WHITE: Final[Color]       = Color(255, 255, 255)
DARKER_GRAY: Final[Color] = Color(50 , 50 , 50)

_RGB_LIGHT_GRAY: Final[RGBColor] = (70, 70, 70)
_RGB_DARK_GRAY: Final[RGBColor]  = (60, 60, 60)
HEX_BLACK: Final[HexColor] = "000000"

# Flips rows and cols because, when making it a surface, pygame uses it like this
EMPTY_TILE_ARR: Final[NDArray[uint8]] = np.array(
    (
        (_RGB_LIGHT_GRAY, _RGB_DARK_GRAY),
        (_RGB_DARK_GRAY , _RGB_LIGHT_GRAY),
    ),
    uint8
).transpose((1, 0, 2))
TILE_W: Final[int] = EMPTY_TILE_ARR.shape[0]
TILE_H: Final[int] = EMPTY_TILE_ARR.shape[1]

FILE_ATTEMPT_START_I: Final[int] = 4
FILE_ATTEMPT_STOP_I: Final[int]  = 9

MOUSE_LEFT: Final[Literal[0]]  = 0
MOUSE_WHEEL: Final[Literal[1]] = 1
MOUSE_RIGHT: Final[Literal[2]] = 2

STATE_I_MAIN: Final[int]     = 0
STATE_I_COLOR: Final[int]    = 1
STATE_I_GRID: Final[int]     = 2
STATE_I_SETTINGS: Final[int] = 4

BG_LAYER: Final[int]      = 0
ELEMENT_LAYER: Final[int] = 1
TEXT_LAYER: Final[int]    = 2
TOP_LAYER: Final[int]     = 3
SPECIAL_LAYER: Final[int] = 4  # Base for the special layers
UI_LAYER: Final[int]      = SPECIAL_LAYER * 2  # Base for the UI layers

ANIMATION_GROW: Final[int]   = 0
ANIMATION_SHRINK: Final[int] = 1

SETTINGS_FPS_ACTIVENESS_CHANGE: Final[int]   = event.custom_type()
SETTINGS_CRASH_SAVE_DIR_CHOICE: Final[int]   = event.custom_type()
SETTINGS_ZOOM_DIRECTION_CHANGE: Final[int]   = event.custom_type()
SETTINGS_HISTORY_MAX_SIZE_CHANGE: Final[int] = event.custom_type()

del _RGB_LIGHT_GRAY, _RGB_DARK_GRAY
