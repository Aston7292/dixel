"""
Types shared between files
"""

from pygame import Surface
from typing import Any

ColorType = tuple[int, ...]
ToolInfo = tuple[str, dict[str, Any]]

BlitSequence = list[tuple[Surface, tuple[int, int]]]
# Last element is the layer
LayeredBlitInfo = tuple[Surface, tuple[int, int], int]
LayeredBlitSequence = list[LayeredBlitInfo]
