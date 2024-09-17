"""
Constants shared between files
"""

from typing import Final

from src.utils import Size
from src.type_utils import ColorType

INIT_WIN_SIZE: Final[Size] = Size(1_200, 900)

BLACK: Final[ColorType] = (0, 0, 0)
WHITE: Final[ColorType] = (255, 255, 255)
LIGHT_GRAY: Final[ColorType] = (85, 85, 85)
DARK_GRAY: Final[ColorType] = (75, 75, 75)

BG_LAYER: Final[int] = 0
ELEMENT_LAYER: Final[int] = 1
TEXT_LAYER: Final[int] = 2
TOP_LAYER: Final[int] = 3
SPECIAL_LAYER: Final[int] = 4  # Base for the special layers
UI_LAYER: Final[int] = SPECIAL_LAYER * 2  # Base for the UI layers
