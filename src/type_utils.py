"""Types shared between files."""

from typing import TypeAlias, Any

from pygame import Surface, Rect

XY: TypeAlias = tuple[int, int]
WH: TypeAlias = tuple[int, int]
RGBColor: TypeAlias = tuple[int, int, int]
RGBAColor: TypeAlias = tuple[int, int, int, int]
HexColor: TypeAlias = str

CheckboxInfo: TypeAlias = tuple[Surface, str]
ToolInfo: TypeAlias = tuple[str, dict[str, Any]]
BlitInfo: TypeAlias = tuple[Surface, Rect, int]
