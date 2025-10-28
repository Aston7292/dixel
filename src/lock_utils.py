"""Functions to lock files on different OSes either in an exclusive or shared way."""

from sys import platform
from collections.abc import Callable
from errno import *
from typing import BinaryIO, Final
from types import ModuleType

import pygame as pg

from src.file_utils import FileError, handle_file_os_error
from src.consts import FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I

fcntl: ModuleType | None = None
try:
    import fcntl
except ImportError:
    pass


class LockError(Exception):
    """Exception raised when locking a file fails."""


# Files are unlocked when closed
if platform == "win32":
    import win32file
    import pywintypes
    from win32con import LOCKFILE_EXCLUSIVE_LOCK, LOCKFILE_FAIL_IMMEDIATELY
    from winerror import *

    _WINDOWS_FILE_MISSING_CODES: Final[tuple[int, ...]] = (
        ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND, ERROR_DIRECTORY, ERROR_NOT_FOUND,
    )
    _WINDOWS_PERMISSION_DENIED_CODES: Final[tuple[int, ...]] = (
        ERROR_ACCESS_DENIED, ERROR_USER_MAPPED_FILE, ERROR_NO_SUCH_PRIVILEGE,
        ERROR_PRIVILEGE_NOT_HELD, ERROR_BAD_IMPERSONATION_LEVEL, ERROR_CANT_OPEN_ANONYMOUS,
        ERROR_CANT_ACCESS_FILE,
    )
    _WINDOWS_SYSTEM_FAILURE_TRANSIENT_CODES: Final[tuple[int, ...]] = (
        ERROR_TOO_MANY_OPEN_FILES, ERROR_SHARING_BUFFER_EXCEEDED, ERROR_OPEN_FAILED, ERROR_BUSY,
        ERROR_OPERATION_ABORTED, ERROR_IO_PENDING, ERROR_NO_SYSTEM_RESOURCES,
    )

    def _try_get_file_handle(f: BinaryIO) -> int:
        """
        Gets a file handle with retries.

        Args:
            file
        Returns:
            handle
        Raises:
            FileError: on failure
        """

        attempt_i: int
        error_str: str
        should_retry: bool

        file_handle: int = 0
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                assert hasattr(win32file, "_get_osfhandle")
                get_osfhandle: Callable[[int], int] = win32file._get_osfhandle
                file_handle = get_osfhandle(f.fileno())
                break
            except OSError as e:
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                raise FileError(f"Failed to get file handle, {error_str}") from e

        return file_handle

    def try_lock_file(f: BinaryIO, is_shared: bool) -> None:
        """
        Locks a file either in an exclusive or shared way.

        Args:
            file, shared flag
        Raises:
            FileNotFoundError, PermissionError, FileError, LockError: on failure
        """

        # file_handle is closed when the file is closed
        file_handle: int = _try_get_file_handle(f)
        flag: int = (0 if is_shared else LOCKFILE_EXCLUSIVE_LOCK) | LOCKFILE_FAIL_IMMEDIATELY

        system_attempt_i: int = FILE_ATTEMPT_START_I
        lock_attempt_i: int   = FILE_ATTEMPT_START_I
        while (
            system_attempt_i <= FILE_ATTEMPT_STOP_I and
            lock_attempt_i   <= FILE_ATTEMPT_STOP_I
        ):
            try:
                win32file.LockFileEx(file_handle, flag, 0, 0xffffffff, win32file.OVERLAPPED())
                break
            except pywintypes.error as e:
                if e.winerror in _WINDOWS_FILE_MISSING_CODES:
                    raise FileNotFoundError from e
                if e.winerror in _WINDOWS_PERMISSION_DENIED_CODES:
                    raise PermissionError   from e

                if e.winerror in _WINDOWS_SYSTEM_FAILURE_TRANSIENT_CODES:
                    system_attempt_i += 1
                    if system_attempt_i == FILE_ATTEMPT_STOP_I:
                        raise FileError(e.strerror) from e

                    pg.time.wait(2 ** system_attempt_i)
                    continue
                if e.winerror in (ERROR_SHARING_VIOLATION, ERROR_LOCK_VIOLATION):
                    lock_attempt_i += 1
                    if lock_attempt_i == FILE_ATTEMPT_STOP_I:
                        raise LockError from e

                    pg.time.wait(2 ** lock_attempt_i)
                    continue

                raise FileError(e.strerror) from e
elif fcntl is not None:
    def try_lock_file(f: BinaryIO, is_shared: bool) -> None:
        """
        Locks a file either in an exclusive or shared way.

        Args:
            file, shared flag
        Raises:
            FileNotFoundError, PermissionError, FileError, LockError: on failure
        """

        error_str: str
        is_transient_system_failure: bool

        assert fcntl is not None
        flag: int = (fcntl.LOCK_SH if is_shared else fcntl.LOCK_EX) | fcntl.LOCK_NB

        system_attempt_i: int = FILE_ATTEMPT_START_I
        lock_attempt_i: int   = FILE_ATTEMPT_START_I
        while (
            system_attempt_i <= FILE_ATTEMPT_STOP_I and
            lock_attempt_i   <= FILE_ATTEMPT_STOP_I
        ):
            try:
                flock: Callable[[int, int], None] = fcntl.flock
                flock(f.fileno(), flag)
                break
            except OSError as e:
                if e.errno == ENOENT:
                    raise FileNotFoundError from e
                if e.errno in (EPERM, EROFS):
                    raise PermissionError   from e

                error_str, is_transient_system_failure = handle_file_os_error(e)
                if is_transient_system_failure:
                    system_attempt_i += 1
                    if system_attempt_i == FILE_ATTEMPT_STOP_I:
                        raise FileError(error_str) from e

                    pg.time.wait(2 ** system_attempt_i)
                    continue
                if e.errno in (EAGAIN, EACCES):
                    lock_attempt_i += 1
                    if lock_attempt_i == FILE_ATTEMPT_STOP_I:
                        raise LockError from e

                    pg.time.wait(2 ** lock_attempt_i)
                    continue

                raise FileError(error_str) from e
else:
    print(f"File locking not implemented for this operating system: {platform}.")

    def try_lock_file(f: BinaryIO, is_shared: bool) -> None:
        """
        Locks a file either in an exclusive or shared way.

        Args:
            file, shared flag
        """
