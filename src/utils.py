"""Functions and dataclasses shared between files."""

from pathlib import Path
from dataclasses import dataclass, field
from math import ceil
from typing import Any

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.type_utils import PosPair, SizePair, Color


@dataclass(slots=True)
class Point:
    """
    Dataclass for representing a point.

    Args:
        x, y
    """

    x: int
    y: int


@dataclass(slots=True)
class Size:
    """
    Dataclass for representing a size.

    Args:
        width, height
    """

    w: int
    h: int


@dataclass(slots=True)
class Ratio:
    """
    Dataclass for representing a ratio.

    Args:
        width ratio, height ratio
    """

    w: float
    h: float


@dataclass(slots=True)
class RectPos:
    """
    Dataclass for representing a rect position.

    Args:
        x, y, coordinate type (e.g. topleft)
    """

    x: int
    y: int
    coord_type: str


def get_img(*path_sections: str) -> pg.Surface:
    """
    Loads an image with transparency.

    Args:
        path sections (args)
    Returns:
        image
    """

    img_file_obj: Path = Path(*path_sections)

    return pg.image.load(img_file_obj).convert_alpha()


def get_pixels(img: pg.Surface) -> NDArray[np.uint8]:
    """
    Gets the rgba values of the pixels in an image.

    Args:
        image
    Returns:
        pixels
    """

    pixels_rgb: NDArray[np.uint8] = pg.surfarray.pixels3d(img)
    pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img)
    pixels: NDArray[np.uint8] = np.dstack((pixels_rgb, pixels_alpha))

    # Swaps columns and rows, because pygame uses it like this
    return np.transpose(pixels, (1, 0, 2))


def add_border(img: pg.Surface, border_color: Color) -> pg.Surface:
    """
    Adds a border to an image.

    Args:
        image, border color
    Returns:
        image
    """

    copy_img: pg.Surface = img.copy()
    border_dim: int = round(min(copy_img.get_size()) / 10)
    pg.draw.rect(copy_img, border_color, copy_img.get_rect(), border_dim)

    return copy_img


def resize_obj(
        init_pos: RectPos, init_w: float, init_h: float, win_ratio: Ratio,
        should_keep_size_ratio: bool = False
) -> tuple[PosPair, SizePair]:
    """
    Scales position and size of an object without creating gaps between attached objects.

    Args:
        initial position, initial width, initial height, window size ratio,
        keep size ratio flag (default = False)
    Returns:
        position, size
    """

    img_ratio_w: float = win_ratio.w
    img_ratio_h: float = win_ratio.h
    if should_keep_size_ratio:
        img_ratio_w = img_ratio_h = min(win_ratio.w, win_ratio.h)

    resized_xy: PosPair = (round(init_pos.x * win_ratio.w), round(init_pos.y * win_ratio.h))
    resized_wh: SizePair = (ceil(init_w * img_ratio_w), ceil(init_h * img_ratio_h))

    return resized_xy, resized_wh


def rec_resize(main_objs: list[Any], win_ratio: Ratio) -> None:
    """
    Resizes objects and their sub objects, modifies the original list.

    Args:
        objects, window size ratio
    """

    pointer_objs: list[Any] = main_objs
    while pointer_objs:
        obj: Any = pointer_objs.pop()
        if hasattr(obj, "resize"):
            obj.resize(win_ratio)
        if hasattr(obj, "objs_info"):
            pointer_objs.extend(info.obj for info in obj.objs_info)


def rec_move_rect(main_obj: Any, init_x: int, init_y: int, win_ratio: Ratio) -> None:
    """
    Moves an object and all it's sub objects.

    Args:
        object, initial x, initial y, window size ratio.
    """
    # TODO: update tests (utils, file utils, clickable, checkbox grid)
    change_x: int = 0
    change_y: int = 0
    objs: list[Any] = [main_obj]

    is_first: bool = True
    while objs:
        obj: Any = objs.pop()
        if hasattr(obj, "move_rect"):
            if not is_first:
                x: int = obj.init_pos.x + change_x
                y: int = obj.init_pos.y + change_y
                obj.move_rect(x, y, win_ratio)
            else:
                prev_init_x: int = obj.init_pos.x
                prev_init_y: int = obj.init_pos.y
                obj.move_rect(init_x, init_y, win_ratio)

                change_x = obj.init_pos.x - prev_init_x
                change_y = obj.init_pos.y - prev_init_y
                is_first = False
        if hasattr(obj, "objs_info"):
            objs.extend(info.obj for info in obj.objs_info)


@dataclass(slots=True)
class ObjInfo:
    """
    Dataclass for storing a name, object and active flag.

    Args:
        object
    """

    obj: Any
    is_active: bool = field(default=True, init=False)

    def set_active(self, should_activate: bool) -> None:
        """
        Sets the active flag for the object and its sub objects.

        Args:
            activate flag
        """

        objs_info: list[ObjInfo] = [self]
        while objs_info:
            info: ObjInfo = objs_info.pop()
            info.is_active = should_activate

            if hasattr(info.obj, "objs_info"):
                objs_info.extend(info.obj.objs_info)


@dataclass(frozen=True, slots=True)
class MouseInfo:
    """
    Dataclass for storing mouse info.

    Args:
        x, y, pressed buttons, recently released buttons, scroll amount
    """

    x: int
    y: int
    pressed: tuple[bool, bool, bool]
    released: tuple[bool, bool, bool, bool, bool]
    scroll_amount: int
