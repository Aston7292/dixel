"""Types shared between files."""

from dataclasses import dataclass
from typing import Literal, TypeAlias, Any

from pygame import Surface, Rect

XY: TypeAlias = tuple[int, int]
WH: TypeAlias = tuple[int, int]
RGBColor: TypeAlias = tuple[int, int, int]
HexColor: TypeAlias = str

DropdownOptionsInfo: TypeAlias = tuple[tuple[str, str, Any], ...]

BlitInfo: TypeAlias = tuple[Surface, Rect, int]


@dataclass(slots=True)
class RectPos:
    """
    Dataclass for representing a rect position.

    Args:
        x coordinate, y coordinate, coordinate type (topleft, midtop, etc.)
    """

    x: int
    y: int
    coord_type: Literal[
        "topleft", "midtop", "topright",
        "midleft", "center", "midright",
        "bottomleft", "midbottom", "bottomright",
    ]
