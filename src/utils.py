"""
Functions and dataclasses shared between files
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from src.type_utils import ColorType


def load_img(*path_sections: str) -> pg.Surface:
    """
    Creates a surface from an image
    Args:
        path sections (args)
    Returns:
        image
    """

    constructed_path: Path = Path(*path_sections)

    return pg.image.load(constructed_path).convert_alpha()


def add_border(img: pg.Surface, border_color: ColorType) -> pg.Surface:
    """
    Adds a border to an image
    Args:
        image, border color
    Returns:
        image with border
    """

    img_with_border: pg.Surface = img.copy()

    border_dim: int = min(img_with_border.get_size()) // 10
    pg.draw.rect(img_with_border, border_color, img_with_border.get_rect(), border_dim)

    return img_with_border


def get_pixels(img: pg.Surface) -> NDArray[np.uint8]:
    """
    Gets the rgba values of the pixels in an image
    Args:
        image
    Returns:
        pixels
    """

    pixels_rgb: NDArray[np.uint8] = pg.surfarray.pixels3d(img)
    pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img)
    pixels: NDArray[np.uint8] = np.dstack((pixels_rgb, pixels_alpha))

    return np.transpose(pixels, (1, 0, 2))


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
        x, y, coordinate type (e.g. topleft)
    """

    x: float
    y: float
    coord_type: str

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
    is_active: bool = field(default=True, init=False)

    def set_active(self, is_active: bool) -> None:
        """
        Sets the active flag for the object and it's sub objects
        Args:
            active boolean
        """

        objs_info: list[ObjInfo] = [self]
        while objs_info:
            info: ObjInfo = objs_info.pop()
            info.is_active = is_active

            if hasattr(info.obj, "objs_info"):
                objs_info.extend(info.obj.objs_info)


@dataclass(frozen=True, slots=True)
class MouseInfo:
    """
    Dataclass for storing mouse info
    Args:
        x, y, pressed buttons, recently released buttons
    """

    x: int
    y: int
    pressed: tuple[bool, bool, bool]
    released: tuple[bool, bool, bool, bool, bool]

    @property
    def xy(self) -> tuple[int, int]:
        """
        Returns:
            x, y
        """

        return self.x, self.y
