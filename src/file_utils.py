"""Functions to operate with files."""

from os import path
from pathlib import Path
from typing import Literal, TextIO, BinaryIO, Final, Optional, overload

import pygame as pg
import portalocker

from src.utils import get_img
from src.type_utils import WH
from src.consts import (
    WHITE, IMG_STATE_OK, IMG_STATE_MISSING, IMG_STATE_DENIED, IMG_STATE_LOCKED, IMG_STATE_CORRUPTED
)

SUPPORTED_IMG_TYPES: Final[tuple[str, ...]] = (".png", ".bmp")
MISSING_IMG: Final[pg.Surface] = pg.Surface((50, 50))
MISSING_IMG.fill((255, 0, 0))
pg.draw.rect(MISSING_IMG, WHITE, MISSING_IMG.get_rect(), 2)


def ensure_valid_img_format(file_str: str) -> str:
    """
    Changes the extensions of a path if it's not a supported format.

    Path.with_suffix doesn't always produce the intended result,
    for example Path(".txt").with_suffix(".png") is Path(".txt.png"),
    it also raises ValueError on empty names.

    Args:
        file string
    Returns:
        file string
    """

    file_obj: Path = Path(file_str)
    sections: list[str] = file_obj.name.rsplit(".", 1)

    if len(sections) == 1:
        sections.append("png")
    elif sections[-1] not in ("png", "bmp"):
        sections[-1] = "png"
    file_name: str = f"{sections[0]}.{sections[1]}"

    return str(file_obj.parent / file_name)


def try_lock_file(file_obj: TextIO | BinaryIO, flag: int) -> None:
    """
    Locks a file.

    Args:
        file object, flag (portalocker.LOCK_NB is added)
    """

    failed_attempts: int = 0
    while failed_attempts < 5:
        try:
            portalocker.lock(file_obj, flag | portalocker.LOCK_NB)
        except portalocker.LockException:
            failed_attempts += 1
            pg.time.wait(50 * failed_attempts)
        else:
            return

    raise portalocker.LockException


@overload
def try_get_img(
        *path_sections: str, missing_img_wh: WH = (64, 64), is_grid_img: Literal[False] = False
) -> pg.Surface:
    ...


@overload
def try_get_img(
        *path_sections: str, missing_img_wh: WH = (64, 64), is_grid_img: Literal[True]
) -> Optional[pg.Surface]:
    ...


def try_get_img(
        *path_sections: str, missing_img_wh: WH = (64, 64), is_grid_img: bool = False
) -> Optional[pg.Surface]:
    """
    Loads an image with transparency.

    Args:
        path section (args), missing image size (default = 64x64),
        grid image flag (default = False),
    Returns:
        image (if it fails and the grid image flag is True it returns None else MISSING_IMG)
    """

    img: Optional[pg.Surface] = None
    file_obj: Path = Path(*path_sections)
    failed_open_attempts: int = 0
    while True:
        try:
            with file_obj.open("rb") as f:
                try_lock_file(f, portalocker.LOCK_SH)
                img = pg.image.load(f, file_obj.name).convert_alpha()
            break
        except FileNotFoundError:
            print(f'Failed to load image "{file_obj.name}". File is missing')
            break
        except PermissionError:
            print(f'Failed to load image "{file_obj.name}". Permission denied.')
            break
        except portalocker.LockException:
            print(f'Failed to load image "{file_obj.name}". File is locked.')
            break
        except pg.error as e:
            print(f'Failed to load image "{file_obj.name}". {e}.')
            break
        except OSError as e:
            failed_open_attempts += 1
            if failed_open_attempts == 5:
                print(f'Failed to load image "{file_obj.name}". {e}.')
                break

            pg.time.wait(50 * failed_open_attempts)

    if img is None and not is_grid_img:
        img = pg.transform.scale(MISSING_IMG, missing_img_wh)

    return img


def get_img_state(file_str: str, should_create: bool) -> int:
    """
    Gest the state of an image.

    Args:
        file string, create flag
    Returns:
        state
    """

    state: int = IMG_STATE_OK
    try:
        mode: str = "ab+" if should_create else "rb+"
        with Path(file_str).open(mode) as f:
            portalocker.lock(f, portalocker.LOCK_EX | portalocker.LOCK_NB)  # Fails if locked
            portalocker.unlock(f)

        if not should_create:
            get_img(file_str)  # Fails if corrupted
    except FileNotFoundError:
        state = IMG_STATE_MISSING
    except PermissionError:
        state = IMG_STATE_DENIED
    except portalocker.LockException:
        state = IMG_STATE_LOCKED
    except pg.error:
        state = IMG_STATE_CORRUPTED

    return state


def try_create_file_argv(file_obj: Path, flag: str) -> bool:
    """
    Creates a file if the flag is --mk-file.

    Args:
        file, flag
    Returns:
        failed flag
    """

    has_failed: bool = True
    if flag != "--mk-file":
        print(
            "The file doesn't exist, to create it add --mk-file.\n"
            f'"{file_obj}" --mk-file'
        )
    else:
        try:
            file_obj.touch()
            has_failed = False
        except PermissionError:
            print("Permission denied.")

    return has_failed


def try_create_dir_argv(file_obj: Path, flag: str) -> bool:
    """
    Creates a directory if the flag is --mk-dir.

    Args:
        file, flag
    Returns:
        failed flag
    """

    has_failed: bool = True
    if flag != "--mk-dir":
        print(
            "The directory doesn't exist, to create it add --mk-dir.\n"
            f'"{file_obj}" --mk-dir'
        )
    else:
        try:
            file_obj.parent.mkdir(parents=True)
            has_failed = False
        except PermissionError:
            print("Permission denied.")

    return has_failed


def handle_cmd_args(argv: list[str]) -> tuple[str, str, bool]:
    """
    Handles info from cmd arguments.

    Args:
        argv
    Returns:
        file string, flag, invalid argv flag
    """

    file_str: str = argv[1]
    flag: str = argv[2].lower() if len(argv) > 2 else ""
    if file_str.lower() == "help" or flag not in ("", "--mk-file", "--mk-dir"):
        program_name: str = argv[0]
        print(
            f"Usage: {program_name} <file path> <optional flag>\n"
            f"Example: {program_name} test (.png is default)\n"
            "FLAGS:\n"
            f"\t--mk-file: create file ({program_name} new_file --mk-file)\n"
            f"\t--mk-dir: create directory ({program_name} new_dir/new_file --mk-dir)"
        )

        return "", "", True

    are_argv_invalid: bool = True
    file_obj: Path = Path(file_str)
    if file_obj.name == "":
        print("Invalid name.")
    else:
        if file_obj.suffix not in SUPPORTED_IMG_TYPES:
            file_obj = file_obj.with_suffix(".png")

        if not path.isreserved(file_obj):
            file_str = str(file_obj)
            are_argv_invalid = False
        else:
            print("Invalid name.")

    return file_str, flag, are_argv_invalid
