"""Functions and dataclasses shared between files."""

import shutil

from tkinter import messagebox
from pathlib import Path
from dataclasses import dataclass
from math import ceil
from collections.abc import Callable
from errno import *
from typing import BinaryIO, Protocol, Final, Any

import pygame as pg
import numpy as np
from numpy import uint8
from numpy.typing import NDArray

from src.lock_utils import FileException
from src.type_utils import XY, WH, BlitInfo
import src.vars as VARS
from src.consts import (
    BLACK,
    EMPTY_TILE_ARR, TILE_W, TILE_H,
    FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I,
)

_FUNCS_NAMES: Final[list[str]] = []
_FUNCS_TOT_TIMES: Final[list[float]] = []
_FUNCS_NUM_CALLS: Final[list[int]] = []

_FILE_TRANSIENT_ERROR_CODES: tuple[int, ...] = (
    EIO, EBUSY, ENFILE, EMFILE, EDEADLK,
)


def profile(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to time the average runtime of a function."""

    func_i: int = len(_FUNCS_NAMES)
    _FUNCS_NAMES.append(func.__qualname__)
    _FUNCS_TOT_TIMES.append(0)
    _FUNCS_NUM_CALLS.append(0)

    def _upt_info(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
        """Runs a function and updates its total runtime and number of calls."""

        start: int = pg.time.get_ticks()
        res: Any = func(*args, **kwargs)
        stop: int  = pg.time.get_ticks()

        _FUNCS_TOT_TIMES[func_i] += stop - start
        _FUNCS_NUM_CALLS[func_i] += 1
        return res

    return _upt_info


def print_funcs_profiles() -> None:
    """Prints the info of every profiled function."""

    name: str
    tot_time: float
    num_calls: int

    for name, tot_time, num_calls in zip(_FUNCS_NAMES, _FUNCS_TOT_TIMES, _FUNCS_NUM_CALLS):
        avg_time: float = tot_time / num_calls if num_calls else 0
        print(f"{name}: {avg_time:.4f}ms | calls: {num_calls}")


class UIElement(Protocol):
    """Class to reinforce type hinting."""

    hover_rects: list[pg.Rect]
    layer: int
    cursor_type: int

    @property
    def blit_sequence(self) -> list[BlitInfo]:
        """TODO"""

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

    @property
    def objs_info(self) -> list["ObjInfo"]:
        """
        Gets the sub objects info.

        Returns:
            objects info
        """


@dataclass(slots=True)
class RectPos:
    """
    Dataclass for representing a rect position.

    Args:
        x coordinate, y coordinate, coordinate type (topleft, midtop, etc.)
    """

    x: int
    y: int
    coord_type: str


@dataclass(slots=True)
class ObjInfo:
    """
    Dataclass for storing an object and its active flag.

    Args:
        object
    """

    obj: UIElement
    is_active: bool = True

    def rec_set_active(self, should_activate: bool) -> None:
        """
        Sets the active flag for the object and sub objects, calls the leave method if inactive.

        Args:
            activate flag
        """

        VARS.should_refresh_active_objs = True
        objs_info: list[ObjInfo] = [self]
        while objs_info != []:
            info: ObjInfo = objs_info.pop()
            info.is_active = should_activate

            if should_activate:
                info.obj.enter()
            else:
                info.obj.leave()
            objs_info.extend(info.obj.objs_info)


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
    return np.dstack((pixels_rgb, alpha_values))


def add_border(img: pg.Surface, border_color: pg.Color) -> pg.Surface:
    """
    Adds a border to an image.

    Args:
        image, border color
    Returns:
        image
    """

    new_img: pg.Surface = img.copy()
    side_w: int = round(min(new_img.get_size()) / 10)
    pg.draw.rect(new_img, border_color, new_img.get_rect(), side_w)
    return new_img


def get_brush_dim_checkbox_info(dim: int) -> tuple[pg.Surface, str]:
    """
    Gets the checkbox info for a brush dimension.

    Args:
        dimension
    Returns:
        image, hovering text
    """

    img_arr: NDArray[uint8] = np.tile(EMPTY_TILE_ARR, (8, 8, 1))
    rect: pg.Rect = pg.Rect(0, 0, dim * TILE_W, dim * TILE_H)
    rect.center = (round(img_arr.shape[0] / 2), round(img_arr.shape[1] / 2))

    img: pg.Surface = pg.surfarray.make_surface(img_arr)
    pg.draw.rect(img, BLACK, rect)
    img = pg.transform.scale_by(img, 4).convert()
    hovering_text: str = f"{dim}px\n(CTRL+{dim})"
    return img, hovering_text


def prettify_path_str(path_str: str) -> str:
    """
    If a path string is longer than 32 chars it transform into the form root/.../parent/element.

    It then transforms it into an absolute and resolved string.

    Args:
        path string
    Returns:
        path string
    """

    path_obj: Path = Path(path_str).resolve()
    path_str = str(path_obj)
    if len(path_str) > 32:
        parts: tuple[str, ...] = path_obj.parts
        num_extra_parts: int = len(parts) - 1  # Drive is always present

        start: str = path_obj.drive
        parent: str = path_obj.parent.name
        name: str = path_obj.name
        if start == "":
            # Represent start as /home or similar if there's something between root and element
            start = parts[0]
            if num_extra_parts >= 2:
                start += "/" + parts[1]
                num_extra_parts -= 1

        path_str = f"{start[:3]}...{start[-3:]}" if len(start) > 10 else start
        if num_extra_parts >= 3:  # There's something between root and parent so add dots
            path_str += "/..."
        if num_extra_parts >= 2:  # There's something between root and element so add parent
            path_str += "/" + (f"{parent[:4]}...{parent[-4:]}" if len(parent) > 16 else parent)
        if num_extra_parts >= 1:  # Root and element are different so add element
            path_str += "/" + (f"{name[:4]}...{name[-4:]}" if len(name) > 16 else name)

        path_str = str(Path(path_str))  # Replaces / with the right linker

    return path_str


def try_read_file(f: BinaryIO) -> bytes:
    """
    Reads a file with retries.

    Args:
        file
    Returns:
        content
    Raises:
        FileException
    """

    content: bytes = b""
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            content = f.read()
            break
        except OSError as e:
            if attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            raise FileException(str(e) + ".") from e

    return content


def try_write_file(f: BinaryIO, content: bytes) -> None:
    """
    Writes to a file with retries.

    Args:
        file, content
    Raises:
        FileException
    """

    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            f.truncate(0)
            num_written_bytes: int = f.write(content)
            if num_written_bytes == len(content):
                break

            raise FileException("Failed to write full file.")
        except OSError as e:
            if attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            raise FileException(str(e) + ".") from e


def handle_file_os_error(e: OSError) -> tuple[str, bool]:
    """
    Handles an OSError from a file opening, deciding if a retry should occur or not.

    Args:
        error
    Returns:
        message, retry flag
    """

    error_str: str = e.strerror + "." if e.strerror is not None else ""
    if e.errno == EINVAL:
        error_str = "Reserved path."

    return error_str, e in _FILE_TRANSIENT_ERROR_CODES


def try_clear_dir(dir_path: Path) -> None:
    """
    Tries to clear a directory with retries.

    Args:
        path
    """

    element: Path
    _error_str: str
    should_retry: bool

    for element in dir_path.iterdir():
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                if element.is_file():
                    element.unlink()
                else:
                    shutil.rmtree(element)
                break
            except (FileNotFoundError, PermissionError):
                break
            except OSError as e:
                _error_str, should_retry = handle_file_os_error(e)
                if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                break

def try_create_dir(dir_path: Path, should_ask_create: bool, creation_attempt_i: int) -> bool:
    """
    Creates a directory with retries.

    Args:
        path, ask creation flag, attempt index
    Returns:
        failed flag
    """

    system_attempt_i: int
    error_str: str
    should_retry: bool

    if creation_attempt_i == 1 and should_ask_create:
        should_create: bool = messagebox.askyesno(
            "Image Save Failed",
            f"Directory missing: {dir_path.name}\nDo you wanna create it?",
            icon="warning"
        )

        if not should_create:
            return True
    elif creation_attempt_i == FILE_ATTEMPT_STOP_I:
        messagebox.showerror("Directory Creation Failed", "Repeated failure in creation.")
        return True

    did_fail: bool = True
    for system_attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            did_fail = False
            break
        except PermissionError:
            messagebox.showerror(
                "Directory Creation Failed", f"{dir_path.name}: permission denied."
            )
            break
        except FileExistsError:
            messagebox.showerror(
                "Directory Creation Failed", f"{dir_path.name}: file with the same name exists."
            )
            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** system_attempt_i)
                continue

            messagebox.showerror(
                "Directory Creation Failed", f"{dir_path.name}: {error_str}"
            )
            break

    return did_fail


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

    resized_wh: WH

    resized_xy: XY = (round(init_pos.x * win_w_ratio), round(init_pos.y * win_h_ratio))
    if should_keep_wh_ratio:
        min_ratio: float = min(win_w_ratio, win_h_ratio)
        resized_wh = (ceil(init_w * min_ratio  ), ceil(init_h * min_ratio  ))
    else:
        resized_wh = (ceil(init_w * win_w_ratio), ceil(init_h * win_h_ratio))

    return resized_xy, resized_wh


def rec_move_rect(
        main_obj: UIElement, init_x: int, init_y: int, win_w_ratio: float, win_h_ratio: float
) -> None:
    """
    Moves an object and it's sub objects to a specific coordinate.

    Args:
        object, initial x, initial y, window width ratio, window height ratio
    """

    objs_hierarchy: list[UIElement] = [main_obj]
    change_x: int = 0
    change_y: int = 0
    while objs_hierarchy != []:
        obj: UIElement = objs_hierarchy.pop()
        if hasattr(obj, "move_rect"):
            class_name: str = obj.__class__.__name__
            assert                              callable(  obj.move_rect        ), class_name
            assert hasattr(obj, "init_pos") and isinstance(obj.init_pos, RectPos), class_name

            if obj != main_obj:
                obj.move_rect(
                    obj.init_pos.x + change_x, obj.init_pos.y + change_y,
                    win_w_ratio, win_h_ratio
                )
            else:
                change_x, change_y = init_x - obj.init_pos.x, init_y - obj.init_pos.y
                obj.move_rect(init_x, init_y, win_w_ratio, win_h_ratio)

        objs_hierarchy.extend([info.obj for info in obj.objs_info])
