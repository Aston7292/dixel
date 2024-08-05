"""
constants shared between files
"""

from pygame import SurfaceType
from typing import Tuple, List, Final

from src.utils import Size

ColorType = Tuple[int, int, int]
BlitSequence = List[Tuple[SurfaceType, Tuple[float, float]]]

INIT_WIN_SIZE: Final[Size] = Size(1_200, 900)

BLACK: Final[ColorType] = (0, 0, 0)
