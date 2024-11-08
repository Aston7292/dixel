"""Types shared between files."""

from typing import Any
from pygame import Surface

ColorType = tuple[int, ...]
ToolInfo = tuple[str, dict[str, Any]]

BlitSequence = list[tuple[Surface, tuple[int, int]]]
LayeredBlitInfo = tuple[Surface, tuple[int, int], int]  # Last element is the layer
LayeredBlitSequence = list[LayeredBlitInfo]
