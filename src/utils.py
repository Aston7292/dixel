"""
collections of shared functions, dataclasses and types
"""

import pygame as pg
from dataclasses import dataclass
from typing import Tuple, List

ColorType = Tuple[int, ...]
BlitSequence = List[Tuple[pg.SurfaceType, Tuple[float, float]]]


def add_border(img: pg.SurfaceType, color: ColorType) -> pg.SurfaceType:
    """
    add a colored border to an image
    takes image
    returns image
    """

    img = img.copy()

    w: int
    h: int
    w, h = img.get_size()
    dim: int = min(w, h) // 10

    pg.draw.rect(img, color, (0, 0, w, dim))
    pg.draw.rect(img, color, (w - dim, 0, dim, h))
    pg.draw.rect(img, color, (0, h - dim, w, dim))
    pg.draw.rect(img, color, (0, 0, dim, h))

    return img


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
    coord: str

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
