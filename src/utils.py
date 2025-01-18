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

    @property
    def xy(self) -> PosPair:
        """
        Gets the x and y coordinates.

        Returns:
            x coordinate, y coordinate
        """

        return (self.x, self.y)


@dataclass(slots=True)
class Size:
    """
    Dataclass for representing a size.

    Args:
        width, height
    """

    w: int
    h: int

    @property
    def wh(self) -> SizePair:
        """
        Gets the width and height.

        Returns:
            width, height
        """

        return (self.w, self.h)


@dataclass(slots=True)
class Ratio:
    """
    Dataclass for representing a ratio.

    Args:
        width ratio, height ratio
    """

    w: float
    h: float

    @property
    def wh(self) -> tuple[float, float]:
        """
        Gets the width and height ratios.

        Returns:
            width ratio, height ratio
        """

        return (self.w, self.h)


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

    @property
    def xy(self) -> PosPair:
        """
        Gets the x and y coordinates.

        Returns:
            x coordinate, y coordinate
        """

        return (self.x, self.y)


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
        img_ratio_w = img_ratio_h = min(win_ratio.wh)

    resized_xy: PosPair = (round(init_pos.x * win_ratio.w), round(init_pos.y * win_ratio.h))
    resized_wh: SizePair = (ceil(init_w * img_ratio_w), ceil(init_h * img_ratio_h))

    return resized_xy, resized_wh


def rec_resize(main_objs: list[Any], win_ratio: Ratio) -> None:
    """
    Resizes objects and their sub objects, modifies the original list.

    Args:
        objects, window size ratio
    """

    ptr_objs_hierarchy: list[Any] = main_objs
    while ptr_objs_hierarchy:
        obj: Any = ptr_objs_hierarchy.pop()
        if hasattr(obj, "resize"):
            obj.resize(win_ratio)
        if hasattr(obj, "objs_info"):
            ptr_objs_hierarchy.extend([info.obj for info in obj.objs_info])


def rec_move_rect(main_obj: Any, init_x: int, init_y: int, win_ratio: Ratio) -> None:
    """
    Moves an object and all it's sub objects.

    Args:
        object, initial x, initial y, window size ratio.
    """

    change_x: int = 0
    change_y: int = 0
    objs_hierarchy: list[Any] = [main_obj]

    is_first: bool = True
    while objs_hierarchy:
        obj: Any = objs_hierarchy.pop()
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
            objs_hierarchy.extend([info.obj for info in obj.objs_info])


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
        Sets the active flag for the object and its sub objects and calls the enter/leave method.

        Args:
            activate flag
        """

        method_name: str = "enter" if should_activate else "leave"

        objs_info: list[ObjInfo] = [self]
        while objs_info:
            info: ObjInfo = objs_info.pop()
            info.is_active = should_activate

            if hasattr(info.obj, method_name):
                getattr(info.obj, method_name)()
            if hasattr(info.obj, "objs_info"):
                objs_info.extend(info.obj.objs_info)


@dataclass(slots=True)
class Mouse:
    """
    Dataclass for storing mouse info.

    Args:
        x, y, pressed buttons, released buttons, scroll amount, hovered object
    """

    x: int
    y: int
    pressed: tuple[bool, bool, bool]
    released: tuple[bool, bool, bool, bool, bool]
    scroll_amount: int
    hovered_obj: Any

    @property
    def xy(self) -> PosPair:
        """
        Gets the x and y coordinates.

        Returns:
            x coordinate, y coordinate
        """

        return (self.x, self.y)


@dataclass(slots=True)
class Keyboard:
    """
    Dataclass for storing keyboard info.

    Args:
        pressed keys, timed keys, control flag, shift flag, alt flag, numpad flag
    """

    pressed: list[int]
    timed: list[int]
    is_ctrl_on: bool
    is_shift_on: bool
    is_alt_on: bool
    is_numpad_on: bool
