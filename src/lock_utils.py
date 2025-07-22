"""Functions to lock files on different OSes either in an exclusive or shared way."""

from platform import system
from contextlib import suppress
from typing import BinaryIO, Final, Any

import pygame as pg

from src.consts import FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I


fcntl: Any = None
with suppress(ImportError):
    import fcntl


class LockException(Exception):
    """Exception raised when locking a file fails."""


class FileException(Exception):
    """Exception raised when a general file operation fails, like get_osfhandle."""

    __slots__ = (
        "error_str",
    )

    def __init__(self, error_str: str) -> None:
        """
        Initializes the exception.

        Args:
            error string
        """

        super().__init__()
        self.error_str: str = error_str


# Files are unlocked when closed
if system() == "Windows":
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
        ERROR_TOO_MANY_OPEN_FILES, ERROR_OPEN_FAILED, ERROR_BUSY, ERROR_OPERATION_ABORTED,
        ERROR_IO_PENDING, ERROR_NO_SYSTEM_RESOURCES,
    )

    def try_lock_file(file_obj: BinaryIO, shared: bool) -> None:
        """
        Locks a file either in an exclusive or shared way.

        Args:
            file, shared flag
        """

        attempt_i: int

        # file_handle is closed when the file is closed
        file_handle: int = 0
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                file_handle = win32file._get_osfhandle(file_obj.fileno())  # type: ignore
                break
            except OSError as e:
                if attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                raise FileException("Failed to get file handle.") from e

        flag: int = (0 if shared else LOCKFILE_EXCLUSIVE_LOCK) | LOCKFILE_FAIL_IMMEDIATELY

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
                    raise PermissionError from e

                if   e.winerror in _WINDOWS_SYSTEM_FAILURE_TRANSIENT_CODES:
                    system_attempt_i += 1
                    if system_attempt_i == FILE_ATTEMPT_STOP_I:
                        raise FileException(e.strerror) from e

                    pg.time.wait(2 ** system_attempt_i)
                elif e.winerror == ERROR_SHARING_VIOLATION or e.winerror == ERROR_LOCK_VIOLATION:
                    lock_attempt_i += 1
                    if lock_attempt_i == FILE_ATTEMPT_STOP_I:
                        raise LockException from e

                    pg.time.wait(2 ** lock_attempt_i)
                else:
                    raise FileException(e.strerror) from e
elif fcntl is not None:
    from errno import *

    _LINUX_SYSTEM_FAILURES_TRANSIENT_CODES: Final[tuple[int, ...]] = (
        EIO, EBUSY, ENFILE, EMFILE,
    )

    def try_lock_file(file_obj: BinaryIO, shared: bool) -> None:
        """
        Locks a file either in an exclusive or shared way.

        Args:
            file, shared flag
        """

        flag: int = (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB

        system_attempt_i: int = FILE_ATTEMPT_START_I
        lock_attempt_i: int   = FILE_ATTEMPT_START_I
        while (
            system_attempt_i <= FILE_ATTEMPT_STOP_I and
            lock_attempt_i   <= FILE_ATTEMPT_STOP_I
        ):
            try:
                fcntl.flock(file_obj, flag)
                break
            except OSError as e:
                if e.errno == ENOENT:
                    raise FileNotFoundError from e
                if e.errno == EPERM or e.errno == EROFS:
                    raise PermissionError from e

                if   e.errno in _LINUX_SYSTEM_FAILURES_TRANSIENT_CODES:
                    system_attempt_i += 1
                    if system_attempt_i == FILE_ATTEMPT_STOP_I:
                        raise FileException(str(e) + ".") from e

                    pg.time.wait(2 ** system_attempt_i)
                elif e.errno == EAGAIN or e.errno == EACCES:
                    lock_attempt_i += 1
                    if lock_attempt_i == FILE_ATTEMPT_STOP_I:
                        raise LockException from e

                    pg.time.wait(2 ** lock_attempt_i)
                else:
                    raise FileException(str(e) + ".") from e
else:
    print(f"File locking not implemented for this operating system: {system()}.")

    def try_lock_file(file_obj: BinaryIO, shared: bool) -> None:
        """
        Locks a file either in an exclusive or shared way.

        Args:
            file, shared flag
        """
