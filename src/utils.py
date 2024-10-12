"""
Functions and dataclasses shared between files
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from pathlib import Path
from dataclasses import dataclass, field
from math import ceil
from typing import Any

from src.type_utils import ColorType


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
class RectPos:
    """
    Dataclass for representing a rect's position
    Args:
        x, y, coordinate type (e.g. topleft)
    """

    x: int
    y: int
    coord_type: str

    @property
    def xy(self) -> tuple[int, int]:
        """
        Returns:
            x, y
        """

        return self.x, self.y


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

    return np.transpose(pixels, (1, 0, 2))  # Swaps columns and rows


def add_border(img: pg.Surface, border_color: ColorType) -> pg.Surface:
    """
    Adds a border to an image
    Args:
        image, border color
    Returns:
        image with border
    """

    img_with_border: pg.Surface = img.copy()

    border_dim: int = round(min(img_with_border.get_size()) / 10.0)
    pg.draw.rect(img_with_border, border_color, img_with_border.get_rect(), border_dim)

    return img_with_border


def resize_obj(
        pos: RectPos, w: float, h: float, win_ratio_w: float, win_ratio_h: float,
        keep_size_ratio: bool = False
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Scales position and size of an object without creating gaps between attached objects
    Args:
        x, y, width, height, window width ratio, window height ratio,
        keep size ratio boolean (default = False)
    Returns:
        position, size
    """

    img_ratio_w: float
    img_ratio_h: float
    if keep_size_ratio:
        img_ratio_w = img_ratio_h = min(win_ratio_w, win_ratio_h)
    else:
        img_ratio_w, img_ratio_h = win_ratio_w, win_ratio_h

    new_pos: tuple[int, int] = (round(pos.x * win_ratio_w), round(pos.y * win_ratio_h))
    new_size: tuple[int, int] = (ceil(w * img_ratio_w), ceil(h * img_ratio_h))

    return new_pos, new_size


@dataclass(slots=True)
class ObjInfo:
    """
    Dataclass for storing a name, object and active boolean
    Args:
        name, object
    """

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
