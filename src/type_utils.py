"""Types shared between files."""

from typing import TypeAlias

from pygame import Surface, Rect

XY: TypeAlias = tuple[int, int]
WH: TypeAlias = tuple[int, int]
RGBColor: TypeAlias = tuple[int, int, int]
RGBAColor: TypeAlias = tuple[int, int, int, int]
HexColor: TypeAlias = str

BlitInfo: TypeAlias = tuple[Surface, Rect, int]
