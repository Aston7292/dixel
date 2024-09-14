"""
Functions and dataclasses shared between files
"""

import pygame as pg
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from src.type_utils import ColorType


def load_img(*path_sections: str) -> pg.Surface:
    """
    Creates a surface from an image
    Args:
        path sections
    Returns:
        image
    """

    constructed_path: str = str(Path(*path_sections))

    return pg.image.load(constructed_path).convert_alpha()


def add_border(img: pg.Surface, border_color: ColorType) -> pg.Surface:
    """
    Adds a border to an image
    Args:
        image, border color
    Returns:
        modified image
    """

    img_copy: pg.Surface = img.copy()

    w: int
    h: int
    w, h = img_copy.get_size()
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
class ObjInfo:
    """
    Dataclass for storing a name, object and active boolean
    Args:
        name, object
    """

    name: str
    obj: Any
    active: bool = field(default=True, init=False)

    def set_active(self, active: bool) -> None:
        """
        Sets the active flag for the object and it's sub objects
        Args:
            active boolean
        """

        objs_info: list[ObjInfo] = [self]
        while objs_info:
            info: ObjInfo = objs_info.pop()
            info.active = active

            if hasattr(info.obj, 'objs_info'):
                objs_info.extend(info.obj.objs_info)


@dataclass(frozen=True, slots=True)
class MouseInfo:
    """
    Dataclass for storing mouse information
    Args:
        x, y, buttons states, recently released buttons
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
