"""Constants shared between files."""

from typing import Final

import numpy as np
from numpy.typing import NDArray

from src.utils import Size
from src.type_utils import Color

CHR_LIMIT: Final[int] = 1_114_111
MOUSE_LEFT: Final[int] = 0
MOUSE_WHEEL: Final[int] = 1
MOUSE_RIGHT: Final[int] = 2

INIT_WIN_SIZE: Final[Size] = Size(1_200, 900)

BLACK: Final[Color] = (0, 0, 0)
WHITE: Final[Color] = (255, 255, 255)
LIGHT_GRAY: Final[Color] = (85, 85, 85)
DARK_GRAY: Final[Color] = (75, 75, 75)

EMPTY_TILE_ARR: Final[NDArray[np.uint8]] = np.array(
    [
        [LIGHT_GRAY, DARK_GRAY],
        [DARK_GRAY, LIGHT_GRAY]
    ],
    np.uint8
)

BG_LAYER: Final[int] = 0
ELEMENT_LAYER: Final[int] = 1
TEXT_LAYER: Final[int] = 2
TOP_LAYER: Final[int] = 3
SPECIAL_LAYER: Final[int] = 4  # Base for the special layers
UI_LAYER: Final[int] = SPECIAL_LAYER * 2  # Base for the UI layers

STATE_MAIN: Final[int] = 0
STATE_COLOR: Final[int] = 1
STATE_GRID: Final[int] = 2

IMG_STATE_OK: Final[int] = 0
IMG_STATE_MISSING: Final[int] = 1
IMG_STATE_DENIED: Final[int] = 2
IMG_STATE_LOCKED: Final[int] = 3
IMG_STATE_CORRUPTED: Final[int] = 4
