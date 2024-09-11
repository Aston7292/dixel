"""
Types shared between files
"""

from pygame import SurfaceType
from typing import Any

ObjsInfo = list[tuple[str, Any]]

ColorType = tuple[int, ...]
BlitSequence = list[tuple[SurfaceType, tuple[float, float]]]
# Last element is the layer
LayeredBlitSequence = list[tuple[SurfaceType, tuple[float, float], int]]
# Contains the name, layer and depth counter (used for nicer printing)
LayerSequence = list[tuple[str, int, int]]
