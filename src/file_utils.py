"""Functions to operate with files."""

from tkinter import filedialog
from pathlib import Path

from portalocker import lock, unlock, LOCK_EX, LOCK_NB, LockException

from src.consts import ACCESS_SUCCESS, ACCESS_MISSING, ACCESS_DENIED, ACCESS_LOCKED


def check_file_access(file_obj: Path, create: bool = False) -> int:
    """
    Checks if a file is accessible.

    Args:
        file object, create flag (default = False)
    Returns:
        exit code
    """

    exit_code: int = ACCESS_SUCCESS
    try:
        mode: str = "a+" if create else "r+"
        with file_obj.open(mode, encoding="utf-8") as f:
            lock(f, LOCK_EX | LOCK_NB)
            unlock(f)
    except FileNotFoundError:
        exit_code = ACCESS_MISSING
    except PermissionError:
        exit_code = ACCESS_DENIED
    except LockException:
        exit_code = ACCESS_LOCKED

    return exit_code


def create_file_argv(file_path: str, flag: str) -> bool:
    """
    Creates a file if the flag is --mk-file.

    Args:
        file path, flag
    Returns:
        should exit flag
    """

    should_exit: bool = False
    if flag != "--mk-file":
        print(
            "The file doesn't exist, to create it add --mk-file.\n"
            f"\"{file_path}\" --mk-file"
        )
        should_exit = True
    else:
        try:
            Path(file_path).touch()
        except PermissionError:
            print("Permission denied.")
            should_exit = True

    return should_exit


def create_dir_argv(dir_path: str, flag: str) -> bool:
    """
    Creates a directory if the flag is --mk-dir.

    Args:
        directory path, flag
    Returns:
        should exit flag
    """

    should_exit: bool = False
    if flag != "--mk-dir":
        print(
            "The directory doesn't exist, to create it add --mk-dir.\n"
            f"\"{dir_path}\" --mk-dir"
        )
        should_exit = True
    else:
        try:
            Path(dir_path).parent.mkdir(parents=True)
        except PermissionError:
            print("Permission denied.")
            should_exit = True

    return should_exit


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

        if not file_path:
            return file_path

        file_obj: Path = Path(file_path)
        file_exit_code: int = check_file_access(file_obj)
        if file_exit_code == ACCESS_SUCCESS and file_obj.suffix == ".png":
            return file_path
