'''
constants shared between files
'''

from pygame import SurfaceType
from typing import Tuple, Final

from utils import Size

S_INIT_WIN: Final[Size] = Size(1_200, 900)

ColorType = Tuple[int, int, int]
BlitPair = Tuple[SurfaceType, Tuple[int, int]]
