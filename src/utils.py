"""Functions and shared between files."""

import shutil

from pathlib import Path
from collections.abc import Callable
from errno import *
from typing import BinaryIO, Final, Any

import pygame as pg
import numpy as np
from numpy import uint8
from numpy.typing import NDArray

from src.lock_utils import FileError
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


def get_pixels(img: pg.Surface) -> NDArray[uint8]:
    """
    Gets the rgba values of the pixels in an image.

    Args:
        image
    Returns:
        pixels
    """

    return np.dstack((
        pg.surfarray.pixels3d(img),
        pg.surfarray.pixels_alpha(img)
    ))


def add_border(img: pg.Surface, border_color: pg.Color) -> pg.Surface:
    """
    Adds a border to an image.

    Args:
        image, border color
    Returns:
        image
    """

    new_img: pg.Surface = img.copy()
    smallest_dim: int = min(new_img.get_size())
    pg.draw.rect(new_img, border_color, new_img.get_rect(), width=round(smallest_dim / 10))
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
    rect.center = (
        round(img_arr.shape[0] / 2),
        round(img_arr.shape[1] / 2),
    )

    img: pg.Surface = pg.surfarray.make_surface(img_arr)
    pg.draw.rect(img, BLACK, rect)
    return pg.transform.scale_by(img, 4).convert(), f"{dim}px\n(CTRL+{dim})"


def prettify_path(path_str: str) -> str:
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
        if start == "":
            # Represent start as /home or similar if there's something between root and element
            start = parts[0]
            if num_extra_parts >= 2:
                start += "/" + parts[1]
                num_extra_parts -= 1

        def _shorten_str(string: str, max_len: int) -> str:
            """
            Shortens a string by replacing the middle with ...

            Args:
                string, max length
            Returns:
                string
            """

            section_len: int = max_len // 4
            return (
                f"{string[:section_len]}...{string[-section_len:]}" if len(string) > max_len else
                string
            )
        path_str = _shorten_str(start, 10)
        if num_extra_parts >= 3:  # There's something between root and parent so add dots
            path_str += "/..."
        if num_extra_parts >= 2:  # There's something between root and element so add parent
            path_str += "/" + _shorten_str(path_obj.parent.name, 16)
        if num_extra_parts >= 1:  # Root and element are different so add element
            path_str += "/" + _shorten_str(path_obj.name       , 16)
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
        FileError: on failure
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

            raise FileError(str(e) + ".") from e

    return content


def try_write_file(f: BinaryIO, content: bytes) -> None:
    """
    Writes to a file with retries.

    Args:
        file, content
    Raises:
        FileError: on failure
    """

    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            f.truncate(0)
            num_written_bytes: int = f.write(content)
            if num_written_bytes == len(content):
                break

            raise FileError("Failed to write full file.")
        except OSError as e:
            if attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            raise FileError(str(e) + ".") from e


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


def try_get_paths(dir_path: Path) -> tuple[tuple[Path, ...], str | None]:
    """
    Gets all the palettes data files with retries.

    Args:
        directory path
    Returns:
        files, error string (can be None)
    """

    attempt_i: int
    should_retry: bool

    paths: tuple[Path, ...] = ()
    error_str: str | None = None
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            paths = tuple(dir_path.iterdir())
            break
        except (FileNotFoundError, PermissionError) as e:
            if isinstance(e, PermissionError):
                error_str = "Permission denied."
            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            break

    return paths, error_str


def try_remove_element(element_path: Path) -> None:
    """
    Tries to remove a file or directory with retries.

    Args:
        path
    """

    attempt_i: int
    _error_str: str
    should_retry: bool

    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            if element_path.is_file():
                element_path.unlink()
            else:
                shutil.rmtree(element_path)
            break
        except (FileNotFoundError, PermissionError):
            break
        except OSError as e:
            _error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            break


def try_create_dir(dir_path: Path, creation_attempt_i: int) -> str | None:
    """
    Creates a directory with retries.

    Args:
        path, attempt index
    Returns:
        error string (can be None)
    """

    system_attempt_i: int
    should_retry: bool

    if creation_attempt_i == FILE_ATTEMPT_STOP_I:
        return f"{dir_path.name}: repeated failure in creation."

    base_error_str: str
    error_str: str | None = None
    for system_attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            break
        except (PermissionError, FileExistsError) as e:
            base_error_str = (
                "permission denied." if isinstance(e, PermissionError) else
                "file with the same name exists."
            )

            error_str = f"{dir_path.name}: {base_error_str}"
            break
        except OSError as e:
            base_error_str, should_retry = handle_file_os_error(e)
            if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** system_attempt_i)
                continue

            error_str = f"{dir_path.name}: {base_error_str}"
            break

    return error_str
