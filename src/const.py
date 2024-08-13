"""
constants shared between files
"""

from pygame import SurfaceType
from typing import Tuple, List, Final

from src.utils import Size

ColorType = Tuple[int, ...]
BlitSequence = List[Tuple[SurfaceType, Tuple[float, float]]]

INIT_WIN_SIZE: Final[Size] = Size(1_200, 900)

BLACK: Final[ColorType] = (0, 0, 0)
WHITE: Final[ColorType] = (255, 255, 255)
EMPTY_1: Final[ColorType] = (85, 85, 85)
EMPTY_2: Final[ColorType] = (75, 75, 75)
