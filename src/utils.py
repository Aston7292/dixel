"""Functions shared between files."""

from collections.abc import Callable
from typing import Any

import pygame as pg
import numpy as np
from pygame import Color, Surface, Rect, draw, surfarray, transform
from numpy import uint8
from numpy.typing import NDArray

from src.consts import BLACK, EMPTY_TILE_ARR, TILE_W, TILE_H

_FUNCS_NAMES: tuple[str, ...]       = ()
_FUNCS_TOT_TIMES: tuple[float, ...] = ()
_FUNCS_NUM_CALLS: tuple[int, ...]   = ()


def profile(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to time the average runtime of a function."""

    func_i: int = len(_FUNCS_NAMES)
    _FUNCS_NAMES += (func.__qualname__,)
    _FUNCS_TOT_TIMES += (0,)
    _FUNCS_NUM_CALLS += (0,)

    def _run(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
        """Runs a function and updates its total runtime and number of calls."""

        global _FUNCS_TOT_TIMES, _FUNCS_NUM_CALLS

        start: int = pg.time.get_ticks()
        res: Any = func(*args, **kwargs)
        stop: int  = pg.time.get_ticks()

        tot_times_list: list[float] = list(_FUNCS_TOT_TIMES)
        tot_times_list[func_i] += stop - start
        _FUNCS_TOT_TIMES = tuple(tot_times_list)

        num_calls_list: list[int] = list(_FUNCS_NUM_CALLS)
        num_calls_list[func_i] += 1
        _FUNCS_NUM_CALLS = tuple(num_calls_list)

        return res

    return _run


def print_funcs_profiles() -> None:
    """Prints the info of every profiled function."""

    name: str
    tot_time: float
    num_calls: int

    for name, tot_time, num_calls in zip(_FUNCS_NAMES, _FUNCS_TOT_TIMES, _FUNCS_NUM_CALLS):
        avg_time: float = tot_time / num_calls if num_calls else 0
        print(f"{name}: {avg_time:.4f}ms | calls: {num_calls}")


def get_brush_dim_checkbox_info(dim: int) -> tuple[Surface, str]:
    """
    Gets the checkbox info for a brush dimension.

    Args:
        dimension
    Returns:
        image, hovering text
    """

    img_arr: NDArray[uint8] = np.tile(EMPTY_TILE_ARR, (8, 8, 1))
    rect: Rect = Rect(0, 0, dim * TILE_W, dim * TILE_H)
    rect.center = (
        round(img_arr.shape[0] / 2),
        round(img_arr.shape[1] / 2),
    )

    img: Surface = surfarray.make_surface(img_arr)
    draw.rect(img, BLACK, rect)
    return transform.scale_by(img, 4).convert(), f"{dim}px\n(CTRL+{dim})"


def get_pixels(img: Surface) -> NDArray[uint8]:
    """
    Gets the rgba values of the pixels in an image.

    Args:
        image
    Returns:
        pixels
    """

    return np.dstack((surfarray.pixels3d(img), surfarray.pixels_alpha(img)))


def add_border(img: Surface, border_color: Color) -> Surface:
    """
    Adds a border to an image.

    Args:
        image, border color
    Returns:
        image
    """

    new_img: Surface = img.copy()
    smallest_dim: int = min(new_img.get_size())
    draw.rect(new_img, border_color, new_img.get_rect(), width=round(smallest_dim / 10))
    return new_img
