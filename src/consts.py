"""Constants shared between files."""

from dataclasses import dataclass
from typing import Final

import pygame as pg
import numpy as np
from numpy import uint8
from numpy.typing import NDArray

from src.type_utils import RGBColor, HexColor


@dataclass(slots=True)
class _Time:
    """Dataclass for sharing ticks and delta time."""

    ticks: int = 0
    delta: float = 0

MOUSE_LEFT: Final[int]  = 0
MOUSE_WHEEL: Final[int] = 1
MOUSE_RIGHT: Final[int] = 2

BLACK: Final[pg.Color]       = pg.Color(0  , 0  , 0)
WHITE: Final[pg.Color]       = pg.Color(255, 255, 255)
DARKER_GRAY: Final[pg.Color] = pg.Color(50 , 50 , 50)

_RGB_LIGHT_GRAY: Final[RGBColor] = (70, 70, 70)
_RGB_DARK_GRAY: Final[RGBColor]  = (60, 60, 60)
HEX_BLACK: Final[HexColor] = "000000"

WIN_INIT_W: Final[int] = 1_250
WIN_INIT_H: Final[int] = 900

# Flip x and y because, when making it a surface, pygame uses it like this
EMPTY_TILE_ARR: Final[NDArray[uint8]] = np.array(
    (
        (_RGB_LIGHT_GRAY, _RGB_DARK_GRAY ),
        (_RGB_DARK_GRAY , _RGB_LIGHT_GRAY),
    ), uint8
).transpose((1, 0, 2))
TILE_W: Final[int] = EMPTY_TILE_ARR.shape[0]
TILE_H: Final[int] = EMPTY_TILE_ARR.shape[1]

FILE_ATTEMPT_START_I: Final[int] = 4
FILE_ATTEMPT_STOP_I: Final[int]  = 8

BG_LAYER: Final[int]      = 0
ELEMENT_LAYER: Final[int] = 1
TEXT_LAYER: Final[int]    = 2
TOP_LAYER: Final[int]     = 3
SPECIAL_LAYER: Final[int] = 4  # Base for the special layers
UI_LAYER: Final[int]      = SPECIAL_LAYER * 2  # Base for the UI layers

TIME: Final[_Time] = _Time()
ANIMATION_I_GROW: Final[int]   = 0
ANIMATION_I_SHRINK: Final[int] = 1
