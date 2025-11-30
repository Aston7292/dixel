"""Functions shared between files to manage files."""

import os
from pathlib import Path
from errno import *
from typing import BinaryIO, Self, Final

import pygame as pg

from src.consts import FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I


OS_ERROR_TRANSIENT_CODES: Final[tuple[int, ...]] = (EINTR, EIO, EBUSY, ENFILE, EMFILE, EDEADLK)


class FileError(Exception):
    """Exception raised when a general file operation fails, like writing."""

    __slots__ = (
        "error_str",
    )

    def __init__(self: Self, error_str: str) -> None:
        """
        Initializes the exception.

        Args:
            error string
        """

        super().__init__()
        self.error_str: str = error_str


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


def handle_file_os_error(e: OSError) -> tuple[str, bool]:
    """
    Handles an OSError from a file operation, deciding if it should be retried or not.

    Args:
        error
    Returns:
        message, retry flag
    """

    error_str: str = e.strerror + "." if e.strerror is not None else ""
    if e.errno == EINVAL:
        error_str = "Reserved path."

    return error_str, e.errno in OS_ERROR_TRANSIENT_CODES


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

    attempt_i: int
    error_str: str
    should_retry: bool

    content: bytes = b""
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            f.seek(0)
            content = f.read()
            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            raise FileError(error_str) from e

    return content


def try_write_file(f: BinaryIO, content: bytes) -> None:
    """
    Writes to a file with retries.

    Args:
        file, content
    Raises:
        FileError: on failure
    """

    attempt_i: int
    error_str: str
    should_retry: bool

    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            f.truncate(0)
            num_written_bytes: int = f.write(content)
            if num_written_bytes != len(content):
                raise FileError("Failed to write full file.")

            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            raise FileError(error_str) from e

    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            f.flush()
            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            raise FileError(error_str) from e

    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            os.fsync(f.fileno())
            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            raise FileError(error_str) from e

def try_replace_file(file_path: Path, new_file_path: Path) -> None:
    """
    Replaces a file with a new one.

    Args:
        file, new file
    """

    attempt_i: int
    error_str: str
    should_retry: bool

    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            os.replace(file_path, new_file_path)
            break
        except FileNotFoundError, PermissionError:
            raise
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            raise FileError(error_str) from e

def try_remove_file(file_path: Path) -> None:
    """
    Tries to remove a file with retries.

    Args:
        path
    """

    attempt_i: int
    _error_str: str
    should_retry: bool

    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            file_path.unlink(missing_ok=True)
            break
        except PermissionError:
            break
        except OSError as e:
            _error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            break


def try_get_paths(dir_path: Path, pattern: str) -> tuple[tuple[Path, ...], str | None]:
    """
    Gets all the palettes data files matching a pattern with retries.

    Args:
        directory path, search pattern
    Returns:
        files, error string (can be None)
    """

    attempt_i: int
    should_retry: bool

    paths: tuple[Path, ...] = ()
    error_str: str | None = None
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            paths = tuple(dir_path.glob(pattern))
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


def try_create_dir(dir_path: Path, creation_attempt_i: int) -> str | None:
    """
    Creates a directory with retries.

    Args:
        path, attempt index
    Returns:
        error string (can be None)
    """

    system_attempt_i: int
    base_error_str: str
    should_retry: bool

    if creation_attempt_i == FILE_ATTEMPT_STOP_I:
        return f"Directory {dir_path.name}: repeated failure in creation."

    error_str: str | None = None
    for system_attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            break
        except (PermissionError, FileExistsError) as e:
            base_error_str = (
                "Permission denied." if isinstance(e, PermissionError) else
                "File with the same name exists."
            )

            error_str = f"Directory {dir_path.name}: {base_error_str}"
            break
        except OSError as e:
            base_error_str, should_retry = handle_file_os_error(e)
            if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** system_attempt_i)
                continue

            error_str = f"Directory {dir_path.name}: {base_error_str}"
            break

    return error_str
