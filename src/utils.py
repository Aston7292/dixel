"""
collections of shared dataclasses/funcs
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Point:
    """
    dataclass for representing the coordinates of a point
    takes x and y
    """

    x: int
    y: int

    @property
    def xy(self) -> Tuple[int, int]:
        """
        returns x and y
        """

        return self.x, self.y


@dataclass
class RectPos:
    """
    dataclass for representing the position of a rect
    takes x, y and the value they represent (e.g. topleft)
    """

    x: float
    y: float
    pos: str

    @property
    def xy(self) -> Tuple[float, float]:
        """
        returns x and y
        """

        return self.x, self.y


@dataclass
class Size:
    """
    dataclass for representing the size of an object
    takes width and height
    """

    w: int
    h: int

    @property
    def wh(self) -> Tuple[int, int]:
        """
        returns w and h
        """

        return self.w, self.h


@dataclass
class MouseInfo:
    """
    dataclass for storing every info needed about the mouse
    """

    x: int
    y: int
    buttons: Tuple[bool, ...]
    released: Tuple[bool, ...]

    @property
    def xy(self) -> Tuple[int, int]:
        """
        returns x and y
        """

        return self.x, self.y
