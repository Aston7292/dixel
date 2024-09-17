"""
Types shared between files
"""

from pygame import Surface

ColorType = tuple[int, ...]
BlitSequence = list[tuple[Surface, tuple[float, float]]]
# Last element is the layer
LayeredBlitInfo = tuple[Surface, tuple[float, float], int]
LayeredBlitSequence = list[LayeredBlitInfo]
# Contains the name, layer and depth counter (used for nicer printing)
LayerSequence = list[tuple[str, int, int]]
