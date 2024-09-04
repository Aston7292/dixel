"""
constants shared between files
"""

from typing import Final

from src.utils import Size, ColorType

INIT_WIN_SIZE: Final[Size] = Size(1_200, 900)

BLACK: Final[ColorType] = (0, 0, 0)
WHITE: Final[ColorType] = (255, 255, 255)
EMPTY_1: Final[ColorType] = (85, 85, 85)
EMPTY_2: Final[ColorType] = (75, 75, 75)

BG_LAYER: Final[int] = 0
ELEMENT_LAYER: Final[int] = 1
TEXT_LAYER: Final[int] = 2
HOVERING_LAYER: Final[int] = 3
S_LAYER: Final[int] = 4  # base for special layers
UI_LAYER: Final[int] = S_LAYER * 2  # base for ui layers
