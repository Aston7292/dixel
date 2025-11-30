"""Types shared between files."""

from dataclasses import dataclass
from typing import Literal, TypeAlias, Any

from pygame import Surface, Rect

XY: TypeAlias = tuple[int, int]
WH: TypeAlias = tuple[int, int]
HexColor: TypeAlias = str
CoordType: TypeAlias = Literal[
    "topleft", "midtop", "topright",
    "midleft", "center", "midright",
    "bottomleft", "midbottom", "bottomright",
]

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
    coord_type: CoordType
