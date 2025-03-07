"""Functions to operate with files."""

from tkinter import filedialog
from os import path
from pathlib import Path

from pygame import error as pg_error
import portalocker

from src.utils import get_img
from src.consts import (
    IMG_STATE_OK, IMG_STATE_MISSING, IMG_STATE_DENIED, IMG_STATE_LOCKED, IMG_STATE_CORRUPTED
)


def get_img_state(file_path: str, should_create: bool) -> int:
    """
    Gest the state of an image.

    Args:
        path, create flag
    Returns:
        state
    """

    state: int = IMG_STATE_OK
    try:
        mode: str = "ab+" if should_create else "rb+"
        with Path(file_path).open(mode) as f:
            portalocker.lock(f, portalocker.LOCK_EX | portalocker.LOCK_NB)  # Fails if locked
            portalocker.unlock(f)

        if not should_create:
            get_img(file_path)  # Fails if corrupted
    except FileNotFoundError:
        state = IMG_STATE_MISSING
    except PermissionError:
        state = IMG_STATE_DENIED
    except portalocker.LockException:
        state = IMG_STATE_LOCKED
    except pg_error:
        state = IMG_STATE_CORRUPTED

    return state


def try_create_file_argv(img_file_obj: Path, flag: str) -> bool:
    """
    Creates a file if the flag is --mk-file.

    Args:
        image file object, flag
    Returns:
        failed flag
    """

    has_failed: bool = True
    if flag != "--mk-file":
        print(
            "The file doesn't exist, to create it add --mk-file.\n"
            f'"{img_file_obj}" --mk-file'
        )
    else:
        try:
            img_file_obj.touch()
            has_failed = False
        except PermissionError:
            print("Permission denied.")

    return has_failed


def try_create_dir_argv(img_file_obj: Path, flag: str) -> bool:
    """
    Creates a directory if the flag is --mk-dir.

    Args:
        image file object, flag
    Returns:
        failed flag
    """

    has_failed: bool = True
    if flag != "--mk-dir":
        print(
            "The directory doesn't exist, to create it add --mk-dir.\n"
            f'"{img_file_obj}" --mk-dir'
        )
    else:
        try:
            img_file_obj.parent.mkdir(parents=True)
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
        image file path, flag, invalid argv flag
    """

    file_path: str = argv[1]
    flag: str = argv[2].lower() if len(argv) > 2 else ""
    if file_path.lower() == "help" or flag not in ("", "--mk-file", "--mk-dir"):
        program_name: str = argv[0]
        print(
            f"Usage: {program_name} <file path> <optional flag>\n"
            f"Example: {program_name} test (.png isn't required)\n"
            "FLAGS:\n"
            f"\t--mk-file: create file ({program_name} new_file --mk-file)\n"
            f"\t--mk-dir: create directory ({program_name} new_dir/new_file --mk-dir)"
        )

        return "", "", True

    img_file_path: str = ""
    are_argv_invalid: bool = True
    try:
        img_file_obj: Path = Path(file_path).with_suffix(".png")
        if not path.isreserved(img_file_obj):
            img_file_path = str(img_file_obj)
            are_argv_invalid = False
        else:
            print("Invalid name.")
    except ValueError:
        print("Invalid path.")

    return img_file_path, flag, are_argv_invalid


def ask_save_to_file() -> str:
    """
    Asks the user to save a file with a GUI.

    Returns:
        file path
    """

    while True:
        file_path: str = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("Png Files", "*.png")],
            title="Save As"
        )

        if file_path == "":
            return file_path

        file_path = str(Path(file_path).with_suffix(".png"))
        if get_img_state(file_path, True) == IMG_STATE_OK:
            return file_path


def ask_open_file() -> str:
    """
    Asks the user to open a file with a GUI.

    Returns:
        file path
    """

    while True:
        file_path: str = filedialog.askopenfilename(
            defaultextension=".png", filetypes=[("Png Files", "*.png")],
            title="Open"
        )

        if file_path == "" or get_img_state(file_path, False) == IMG_STATE_OK:
            return file_path
