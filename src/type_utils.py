"""
Types shared between files
"""

from pygame import Surface

ColorType = tuple[int, ...]

BlitSequence = list[tuple[Surface, tuple[int, int]]]
# Last element is the layer
LayeredBlitInfo = tuple[Surface, tuple[int, int], int]
LayeredBlitSequence = list[LayeredBlitInfo]
