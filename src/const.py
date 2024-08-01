'''
constants shared between files
'''

from pygame import SurfaceType
from typing import Tuple, Final

from src.utils import Size

ColorType = Tuple[int, int, int]
BlitSequence = Tuple[Tuple[SurfaceType, Tuple[int, int]], ...]

S_INIT_WIN: Final[Size] = Size(1_200, 900)

BLACK: Final[ColorType] = (0, 0, 0)
