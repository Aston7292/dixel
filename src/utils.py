"""
Functions and dataclasses shared between files
"""

import pygame as pg
from dataclasses import dataclass

from src.type_utils import ColorType


def add_border(img: pg.SurfaceType, border_color: ColorType) -> pg.SurfaceType:
    """
    Adds a border to an image
    Args:
        image, border color
    Returns:
        modified image
    """

    img_copy: pg.SurfaceType = img.copy()

    w: int
    h: int
    w, h = img.get_size()
    dim: int = min(w, h) // 10

    pg.draw.rect(img_copy, border_color, (0, 0, w, dim))
    pg.draw.rect(img_copy, border_color, (w - dim, 0, dim, h))
    pg.draw.rect(img_copy, border_color, (0, h - dim, w, dim))
    pg.draw.rect(img_copy, border_color, (0, 0, dim, h))

    return img_copy


@dataclass(slots=True)
class Point:
    """
    Dataclass for representing a point
    Args:
        x, y
    """

    x: int
    y: int

    @property
    def xy(self) -> tuple[int, int]:
        """
        Returns:
            x, y
        """

        return self.x, self.y


@dataclass(slots=True)
class RectPos:
    """
    Dataclass for representing a rect's position
    Args:
        x, y, coordinate (e.g. topleft)
    """

    x: float
    y: float
    coord: str

    @property
    def xy(self) -> tuple[float, float]:
        """
        Returns:
            x, y
        """

        return self.x, self.y


@dataclass(slots=True)
class Size:
    """
    Dataclass for representing a size
    Args:
        width, height
    """

    w: int
    h: int

    @property
    def wh(self) -> tuple[int, int]:
        """
        Returns:
            width, height
        """

        return self.w, self.h


@dataclass(slots=True)
class MouseInfo:
    """
    Dataclass for storing mouse information
    Args:
        x, y, buttons state, recently released buttons
    """

    x: int
    y: int
    buttons: tuple[bool, ...]
    released: tuple[bool, ...]

    @property
    def xy(self) -> tuple[int, int]:
        """
        Returns:
            x, y
        """

        return self.x, self.y
