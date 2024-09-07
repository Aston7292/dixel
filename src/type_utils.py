"""
collection of shared type aliases
"""

from pygame import SurfaceType

ColorType = tuple[int, ...]
BlitSequence = list[tuple[SurfaceType, tuple[float, float]]]
LayeredBlitSequence = list[tuple[SurfaceType, tuple[float, float], int]]  # last element is layer
LayerSequence = list[tuple[str, int, int]]  # name, layer, nesting counter (for nicer printing)
