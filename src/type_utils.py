"""
Types shared between files
"""

from pygame import Surface
from typing import Optional

ColorType = tuple[int, ...]

BlitSequence = list[tuple[Surface, tuple[float, float]]]
# Last element is the layer
LayeredBlitInfo = tuple[Surface, tuple[float, float], int]
LayeredBlitSequence = list[LayeredBlitInfo]
# Contains the name, layer (can be None) and depth counter (used for nicer printing)
LayerSequence = list[tuple[str, Optional[int], int]]
