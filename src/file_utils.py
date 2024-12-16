"""Functions to operate with files."""

from tkinter import filedialog
from os import path
from pathlib import Path

import pygame as pg
from portalocker import lock, unlock, LOCK_EX, LOCK_NB, LockException

from src.utils import get_img
from src.consts import (
    IMG_STATE_OK, IMG_STATE_MISSING, IMG_STATE_DENIED, IMG_STATE_LOCKED, IMG_STATE_CORRUPTED
)


def get_img_state(img_file_path: str, should_create: bool = False) -> int:
    """
    Gest the state of an image.

    Args:
        image file path, create flag (default = False)
    Returns:
        state
    """

    state: int = IMG_STATE_OK
    mode: str = "a+b" if should_create else "r+b"
    try:
        with Path(img_file_path).open(mode) as f:
            lock(f, LOCK_EX | LOCK_NB)  # Fails if already locked
            unlock(f)

        if not should_create:
            get_img(img_file_path)  # Fails if corrupted
    except FileNotFoundError:
        state = IMG_STATE_MISSING
    except PermissionError:
        state = IMG_STATE_DENIED
    except LockException:
        state = IMG_STATE_LOCKED
    except pg.error:
        state = IMG_STATE_CORRUPTED

    return state


def try_create_file_argv(img_file_obj: Path, flag: str) -> bool:
    """
    Creates a file if the flag is --mk-file.

    Args:
        image file object, flag
    Returns:
        True if creation succeeded else False
    """

    has_succeeded: bool = False
    if flag != "--mk-file":
        print(
            "The file doesn't exist, to create it add --mk-file.\n"
            f"\"{img_file_obj}\" --mk-file"
        )
    else:
        try:
            img_file_obj.touch()
            has_succeeded = True
        except PermissionError:
            print("Permission denied.")

    return has_succeeded


def try_create_dir_argv(img_file_obj: Path, flag: str) -> bool:
    """
    Creates a directory if the flag is --mk-dir.

    Args:
        image file object, flag
    Returns:
        True if creation succeeded else False
    """

    has_succeeded: bool = False
    if flag != "--mk-dir":
        print(
            "The directory doesn't exist, to create it add --mk-dir.\n"
            f"\"{img_file_obj}\" --mk-dir"
        )
    else:
        try:
            img_file_obj.parent.mkdir(parents=True)
            has_succeeded = True
        except PermissionError:
            print("Permission denied.")

    return has_succeeded


def handle_cmd_args(argv: list[str]) -> tuple[str, str]:
    """
    Handles info from cmd arguments.

    Args:
        argv
    Returns:
        image file path, flag
    Raises:
        SystemExit
    """

    img_file_path: str
    file_path: str = argv[1]
    flag: str = argv[2].lower() if len(argv) > 2 else ""

    should_continue: bool = False
    if file_path.lower() == "help" or flag not in ("", "--mk-file", "--mk-dir"):
        program_name: str = argv[0]
        print(
            f"Usage: {program_name} <file path> <optional flag>\n"
            f"Example: {program_name} test (.png is not required)\n"
            "FLAGS:\n"
            f"\t--mk-file: create file ({program_name} new_file --mk-file)\n"
            f"\t--mk-dir: create directory ({program_name} new_dir/new_file --mk-dir)"
        )
    else:
        try:
            img_file_obj: Path = Path(file_path).with_suffix(".png")
            img_file_path = str(img_file_obj)
            if path.isreserved(img_file_path):
                print("Invalid name.")
            else:
                should_continue = True
        except ValueError:
            print("Invalid path.")

    if not should_continue:
        raise SystemExit
    return img_file_path, flag


def ask_save_to_file() -> str:
    """
    Asks the user to save a file with a GUI.

    Returns:
        file path
    """

    while True:
        file_path: str = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=(("png Files", "*.png"),), title="Save as"
        )

        if not file_path or Path(file_path).suffix == ".png":
            return file_path


def ask_open_file() -> str:
    """
    Asks the user to open a file with a GUI.

    Returns:
        file path
    """

    while True:
        file_path: str = filedialog.askopenfilename(
            defaultextension=".png", filetypes=(("png Files", "*.png"),), title="Open"
        )

        if not file_path or get_img_state(file_path) == IMG_STATE_OK:
            return file_path
