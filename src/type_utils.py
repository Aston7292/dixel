"""
Types shared between files
"""

from pygame import Surface

ColorType = tuple[int, ...]
BlitSequence = list[tuple[Surface, tuple[float, float]]]
# Last element is the layer
LayeredBlitSequence = list[tuple[Surface, tuple[float, float], int]]
# Contains the name, layer and depth counter (used for nicer printing)
LayerSequence = list[tuple[str, int, int]]
