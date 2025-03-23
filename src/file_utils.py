"""Functions to operate with files."""

from os import path
from pathlib import Path
from typing import Literal, TextIO, BinaryIO, Final, Optional, overload

import pygame as pg
import portalocker

from src.type_utils import WH
from src.consts import WHITE, NUM_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY

MISSING_IMG: Final[pg.Surface] = pg.Surface((50, 50))
MISSING_IMG.fill((255, 0, 0))
pg.draw.rect(MISSING_IMG, WHITE, MISSING_IMG.get_rect(), 2)


def ensure_valid_img_format(file_str: str) -> str:
    """
    Changes the extensions of a path if it's not a supported format.

    Path.with_suffix() doesn't always produce the intended result,
    for example Path(".txt").with_suffix(".png") is Path(".txt.png"),
    it also raises ValueError on empty names.

    Args:
        file string
    Returns:
        file string
    """

    file_path: Path = Path(file_str)
    sections: list[str] = file_path.name.rsplit(".", 1)

    if len(sections) == 1:
        sections.append("png")
    elif sections[-1] not in ("png", "bmp"):
        sections[-1] = "png"
    file_name: str = f"{sections[0]}.{sections[1]}"

    return str(file_path.parent / file_name)


def try_lock_file(file_obj: TextIO | BinaryIO, flag: int) -> None:
    """
    Locks a file.

    Args:
        file, flag (portalocker.LOCK_NB is added)
    """

    for num_failed_attempts in range(1, NUM_FILE_ATTEMPTS + 1):
        try:
            portalocker.lock(file_obj, flag | portalocker.LOCK_NB)
            break
        except portalocker.LockException:
            if num_failed_attempts == NUM_FILE_ATTEMPTS:
                raise

            pg.time.wait(FILE_ATTEMPT_DELAY * num_failed_attempts)


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
        grid image flag (default = False)
    Returns:
        image (if it fails and the grid image flag is True it returns None else MISSING_IMG)
    """

    failed_open_attempts: int

    img: Optional[pg.Surface] = None
    file_path: Path = Path(*path_sections)
    for failed_open_attempts in range(1, NUM_FILE_ATTEMPTS + 1):
        try:
            with file_path.open("rb") as f:
                try_lock_file(f, portalocker.LOCK_SH)
                img = pg.image.load(f, file_path.name).convert_alpha()
            break
        except FileNotFoundError:
            print(f'Failed to load image "{file_path.name}". File is missing')
            break
        except PermissionError:
            print(f'Failed to load image "{file_path.name}". Permission denied.')
            break
        except portalocker.LockException:
            print(f'Failed to load image "{file_path.name}". File is locked.')
            break
        except pg.error as e:
            print(f'Failed to load image "{file_path.name}". {e}.')
            break
        except OSError as e:
            if failed_open_attempts == NUM_FILE_ATTEMPTS:
                print(f'Failed to load image "{file_path.name}". {e}.')
                break

            pg.time.wait(FILE_ATTEMPT_DELAY * failed_open_attempts)

    if img is None and not is_grid_img:
        img = pg.transform.scale(MISSING_IMG, missing_img_wh)

    return img


def try_create_file_argv(file_path: Path, flag: str) -> bool:
    """
    Creates a file if the flag is --mk-file.

    Args:
        file path, flag
    Returns:
        failed flag
    """

    num_failed_attempts: int

    if flag != "--mk-file":
        print(
            "The file doesn't exist, to create it add --mk-file.\n"
            f'"{file_path}" --mk-file'
        )

        return True

    has_failed: bool = True
    for num_failed_attempts in range(1, NUM_FILE_ATTEMPTS + 1):
        try:
            file_path.touch()
            has_failed = False
            break
        except PermissionError:
            print("Permission denied.")
            break
        except OSError as e:
            if num_failed_attempts == NUM_FILE_ATTEMPTS:
                print(e)
                break

            pg.time.wait(FILE_ATTEMPT_DELAY * num_failed_attempts)

    return has_failed


def try_create_dir_argv(file_path: Path, flag: str) -> bool:
    """
    Creates a directory if the flag is --mk-dir.

    Args:
        file path, flag
    Returns:
        failed flag
    """

    num_failed_attempts: int

    if flag != "--mk-dir":
        print(
            "The directory doesn't exist, to create it add --mk-dir.\n"
            f'"{file_path}" --mk-dir'
        )

        return True

    has_failed: bool = True
    for num_failed_attempts in range(1, NUM_FILE_ATTEMPTS + 1):
        try:
            file_path.parent.mkdir(parents=True)
            has_failed = False
            break
        except PermissionError:
            print("Permission denied.")
            break
        except FileExistsError:
            print("You can't create a directory with the same name of a file.")
            break
        except OSError as e:
            if num_failed_attempts == NUM_FILE_ATTEMPTS:
                print(e)
                break

            pg.time.wait(FILE_ATTEMPT_DELAY * num_failed_attempts)

    return has_failed


def handle_cmd_args(argv: list[str]) -> tuple[str, str, bool]:
    """
    Handles info from cmd arguments.

    Args:
        argv
    Returns:
        file string, flag, invalid argv flag
    """

    are_argv_invalid: bool

    flag: str = argv[2].lower() if len(argv) > 2 else ""
    if argv[1].lower() == "help" or flag not in ("", "--mk-file", "--mk-dir"):
        program_name: str = argv[0]
        print(
            f"Usage: {program_name} <file path> <optional flag>\n"
            f"Example: {program_name} test (.png is default)\n"
            "FLAGS:\n"
            f"\t--mk-file: create file ({program_name} new_file --mk-file)\n"
            f"\t--mk-dir: create directory ({program_name} new_dir/new_file --mk-dir)"
        )

        return "", "", True

    file_str:str = ensure_valid_img_format(argv[1])
    if hasattr(path, "isreserved"):  # 3.13.0+
        are_argv_invalid = path.isreserved(file_str)
    else:
        are_argv_invalid = Path(file_str).is_reserved()

    if are_argv_invalid:
        print("Reserved path.")
    return file_str, flag, are_argv_invalid
