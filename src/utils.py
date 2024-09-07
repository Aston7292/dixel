"""
collections of shared functions, dataclasses and types
"""

import pygame as pg
from dataclasses import dataclass
from typing import Iterable, Any

from src.type_utils import ColorType


def check_nested_hover(
        mouse_pos: tuple[int, int], objs: Iterable[Any], hover_obj: Any, hover_layer: int
) -> tuple[Any, int]:
    """
    checks if the mouse is hovering any object in a list
    takes mouse position, objects, hovered object (can be None) and its layer
    returns the hovered object (can be None) and its layer
    """

    for obj in objs:
        current_hover_obj: Any
        current_hover_layer: int
        current_hover_obj, current_hover_layer = obj.check_hover(mouse_pos)
        if current_hover_obj and current_hover_layer > hover_layer:
            hover_obj = current_hover_obj
            hover_layer = current_hover_layer

    return hover_obj, hover_layer


def add_border(img: pg.SurfaceType, color: ColorType) -> pg.SurfaceType:
    """
    adds a colored border to an image
    takes image and color
    returns image
    """

    img_copy: pg.SurfaceType = img.copy()

    w: int
    h: int
    w, h = img.get_size()
    dim: int = min(w, h) // 10

    pg.draw.rect(img_copy, color, (0, 0, w, dim))
    pg.draw.rect(img_copy, color, (w - dim, 0, dim, h))
    pg.draw.rect(img_copy, color, (0, h - dim, w, dim))
    pg.draw.rect(img_copy, color, (0, 0, dim, h))

    return img_copy


@dataclass
class Point:
    """
    dataclass for representing the coordinates of a point
    takes x and y
    """

    x: int
    y: int

    @property
    def xy(self) -> tuple[int, int]:
        """
        returns x and y
        """

        return self.x, self.y


@dataclass
class RectPos:
    """
    dataclass for representing the position of a rect
    takes x, y and the coordinate they represent (e.g. topleft)
    """

    x: float
    y: float
    coord: str

    @property
    def xy(self) -> tuple[float, float]:
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
    def wh(self) -> tuple[int, int]:
        """
        returns width and height
        """

        return self.w, self.h


@dataclass
class MouseInfo:
    """
    dataclass for storing all info needed about the mouse
    """

    x: int
    y: int
    buttons: tuple[bool, ...]
    released: tuple[bool, ...]

    @property
    def xy(self) -> tuple[int, int]:
        """
        returns x and y
        """

        return self.x, self.y
