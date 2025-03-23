"""Functions and dataclasses shared between files."""

from time import time as get_time
from dataclasses import dataclass, field
from functools import wraps
from math import ceil
from collections.abc import Callable
from typing import Final, Any

import pygame as pg
from numpy import dstack as dstack_arr, tile as tile_arr, uint8
from numpy.typing import NDArray
from src.type_utils import XY, WH
from src.consts import BLACK, EMPTY_TILE_ARR, NUM_TILE_COLS, NUM_TILE_ROWS


FUNCS_NAMES: Final[list[str]] = []
FUNCS_TOT_TIMES: Final[list[float]] = []
FUNCS_NUM_CALLS: Final[list[int]] = []


def profile(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to time the average run time of a function."""

    func_i: int = len(FUNCS_NAMES)
    FUNCS_NAMES.append(func.__qualname__)
    FUNCS_TOT_TIMES.append(0)
    FUNCS_NUM_CALLS.append(0)

    @wraps(func)
    def upt_info(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
        """Runs a function and updates its total run time and number of calls."""

        start: float = get_time()
        res: Any = func(*args, **kwargs)
        FUNCS_TOT_TIMES[func_i] += (get_time() - start) * 1_000
        FUNCS_NUM_CALLS[func_i] += 1

        return res

    return upt_info


def print_funcs_profiles() -> None:
    """Prints the info of every timed function."""

    name: str
    tot_time: float
    num_calls: int

    for name, tot_time, num_calls in zip(FUNCS_NAMES, FUNCS_TOT_TIMES, FUNCS_NUM_CALLS):
        avg_time: float = tot_time / num_calls if num_calls else 0
        print(f"{name}: {avg_time:.4f}ms | calls: {num_calls}")


@dataclass(slots=True)
class Point:
    """
    Dataclass for representing a point.

    Args:
        x coordinate, y coordinate
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
class RectPos:
    """
    Dataclass for representing a rect position.

    Args:
        x coordinate, y coordinate, coordinate type (e.g. topleft)
    """

    x: int
    y: int
    coord_type: str


@dataclass(slots=True)
class ObjInfo:
    """
    Dataclass for storing a name, object and active flag.

    Args:
        object
    """

    obj: Any
    is_active: bool = field(init=False)

    def __post_init__(self) -> None:
        """Initializes is_active."""

        self.is_active = True  # field(default=True) only works on python 3.10.16 or higher

    def set_active(self, should_activate: bool) -> None:
        """
        Sets the active flag for the object and its sub objects and calls the enter/leave method.

        Args:
            activate flag
        """

        method_name: str = "enter" if should_activate else "leave"

        objs_info: list[ObjInfo] = [self]
        while objs_info != []:
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
        x coordinate, y coordinate pressed buttons, released buttons, scroll amount, hovered object
    """

    x: int
    y: int
    pressed: list[bool]
    released: list[bool]
    scroll_amount: int
    hovered_obj: Any


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


def get_pixels(img: pg.Surface) -> NDArray[uint8]:
    """
    Gets the rgba values of the pixels in an image.

    Args:
        image
    Returns:
        pixels
    """

    pixels_rgb: NDArray[uint8] = pg.surfarray.pixels3d(img)
    alpha_values: NDArray[uint8] = pg.surfarray.pixels_alpha(img)

    return dstack_arr(pixels_rgb, alpha_values)

def add_border(img: pg.Surface, border_color: pg.Color) -> pg.Surface:
    """
    Adds a border to an image.

    Args:
        image, border color
    Returns:
        image
    """

    new_img: pg.Surface = img.copy()
    width: int = round(min(new_img.get_size()) / 10)
    pg.draw.rect(new_img, border_color, new_img.get_rect(), width)

    return new_img


def get_brush_dim_img(dim: int) -> pg.Surface:
    """
    Gets an image to represent a brush dimension.

    Args:
        dimension
    Returns:
        image
    """

    img_arr: NDArray[uint8] = tile_arr(EMPTY_TILE_ARR, (8, 8, 1))
    rect: pg.Rect = pg.Rect(0, 0, dim * NUM_TILE_COLS, dim * NUM_TILE_ROWS)
    rect.center = (round(img_arr.shape[0] / 2), round(img_arr.shape[1] / 2))

    img: pg.Surface = pg.surfarray.make_surface(img_arr)
    pg.draw.rect(img, BLACK, rect)

    return pg.transform.scale_by(img, 4)


def resize_obj(
        init_pos: RectPos, init_w: float, init_h: float, win_w_ratio: float, win_h_ratio: float,
        should_keep_wh_ratio: bool = False
) -> tuple[XY, WH]:
    """
    Scales position and size of an object without creating gaps between attached objects.

    Args:
        initial position, initial width, initial height, window width ratio, window height ratio
        keep size ratio flag (default = False)
    Returns:
        position, size
    """

    img_w_ratio: float
    img_h_ratio: float

    if should_keep_wh_ratio:
        img_w_ratio = img_h_ratio = min(win_w_ratio, win_h_ratio)
    else:
        img_w_ratio, img_h_ratio = win_w_ratio, win_h_ratio

    resized_xy: XY = (round(init_pos.x * win_w_ratio), round(init_pos.y * win_h_ratio))
    resized_wh: WH = (ceil(init_w * img_w_ratio), ceil(init_h * img_h_ratio))

    return resized_xy, resized_wh


def rec_resize(main_objs: list[Any], win_w_ratio: float, win_h_ratio: float) -> None:
    """
    Resizes objects and their sub objects, modifies the original list.

    Args:
        objects, window width ratio, window height ratio
    """

    while main_objs != []:
        obj: Any = main_objs.pop()
        if hasattr(obj, "resize"):
            obj.resize(win_w_ratio, win_h_ratio)
        if hasattr(obj, "objs_info"):
            main_objs.extend([info.obj for info in obj.objs_info])


def rec_move_rect(
        main_obj: Any, init_x: int, init_y: int, win_w_ratio: float, win_h_ratio: float
) -> None:
    """
    Moves an object and all it's sub objects.

    Args:
        object, initial x, initial y, window width ratio, window height ratio
    """

    change_x: int
    change_y: int

    change_x = change_y = 0
    objs_hierarchy: list[Any] = [main_obj]

    is_sub_obj: bool = False
    while objs_hierarchy != []:
        obj: Any = objs_hierarchy.pop()
        if hasattr(obj, "move_rect"):
            if is_sub_obj:
                obj.move_rect(
                    obj.init_pos.x + change_x, obj.init_pos.y + change_y,
                    win_w_ratio, win_h_ratio
                )
            else:
                change_x, change_y = init_x - obj.init_pos.x, init_y - obj.init_pos.y
                obj.move_rect(init_x, init_y, win_w_ratio, win_h_ratio)
                is_sub_obj = True

        if hasattr(obj, "objs_info"):
            objs_hierarchy.extend([info.obj for info in obj.objs_info])
