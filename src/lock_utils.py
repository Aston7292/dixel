"""Functions to lock files on different OSes."""

from platform import system
from contextlib import suppress
from typing import TextIO, BinaryIO, Final, Any

import pygame as pg

from src.consts import NUM_MAX_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY


fcntl: Any = None
with suppress(ImportError):
    import fcntl


class LockException(Exception):
    """Exception raised when locking a file fails."""


class FileException(Exception):
    """Exception raised when a general file operation fails, like get_osfhandle."""

    def __init__(self, error_str: str) -> None:
        """
        Initializes the exception.

        Args:
            error string
        """

        super().__init__()
        self.error_str = error_str


# Files are unlocked when closed
if system() == "Windows":
    import win32file
    import pywintypes
    from win32con import LOCKFILE_EXCLUSIVE_LOCK, LOCKFILE_FAIL_IMMEDIATELY
    from winerror import *

    _WINDOWS_FILE_MISSING_CODES: Final[tuple[int, ...]] = (
        ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND, ERROR_INVALID_NAME, ERROR_BAD_PATHNAME,
        ERROR_FILENAME_EXCED_RANGE, ERROR_DIRECTORY, ERROR_NOT_FOUND
    )
    _WINDOWS_PERMISSION_DENIED_CODES: Final[tuple[int, ...]] = (
        ERROR_ACCESS_DENIED, ERROR_INVALID_DATA, ERROR_WRITE_PROTECT, ERROR_FILE_SYSTEM_LIMITATION,
        ERROR_USER_MAPPED_FILE, ERROR_NO_SUCH_PRIVILEGE, ERROR_PRIVILEGE_NOT_HELD,
        ERROR_BAD_IMPERSONATION_LEVEL, ERROR_CANT_OPEN_ANONYMOUS, ERROR_CANT_ACCESS_FILE
    )
    _WINDOWS_SYSTEM_FAILURE_CODES: Final[tuple[int, ...]] = (
        ERROR_TOO_MANY_OPEN_FILES, ERROR_OPEN_FAILED, ERROR_BUSY, ERROR_OPERATION_ABORTED,
        ERROR_IO_PENDING, ERROR_NO_SYSTEM_RESOURCES
    )
    _WINDOWS_LOCKED_FILE_CODES: Final[tuple[int, ...]] = (
        ERROR_SHARING_VIOLATION, ERROR_LOCK_VIOLATION, ERROR_INVALID_BLOCK_LENGTH
    )

    def try_lock_file(file_obj: TextIO | BinaryIO, shared: bool) -> None:
        """
        Locks a file.

        Args:
            file, shared flag
        """

        num_attempts: int

        # file_handle is closed when the file is closed
        file_handle: int = 0
        for num_attempts in range(1, NUM_MAX_FILE_ATTEMPTS + 1):
            try:
                file_handle = win32file._get_osfhandle(file_obj.fileno())  # type: ignore
                break
            except OSError as e:
                if num_attempts == NUM_MAX_FILE_ATTEMPTS:
                    raise FileException("Failed to get file handle.") from e

                pg.time.wait(FILE_ATTEMPT_DELAY * num_attempts)

        num_system_attempts: int = 0
        num_lock_attempts: int = 0
        while True:
            try:
                flag: int = (0 if shared else LOCKFILE_EXCLUSIVE_LOCK) | LOCKFILE_FAIL_IMMEDIATELY
                win32file.LockFileEx(file_handle, flag, 0, 0xffffffff, win32file.OVERLAPPED())
                break
            except pywintypes.error as e:
                if e.winerror in _WINDOWS_FILE_MISSING_CODES:
                    raise FileNotFoundError from e
                if e.winerror in _WINDOWS_PERMISSION_DENIED_CODES:
                    raise PermissionError from e

                if e.winerror in _WINDOWS_SYSTEM_FAILURE_CODES:
                    num_system_attempts += 1
                    if num_system_attempts == NUM_MAX_FILE_ATTEMPTS:
                        raise FileException(e.strerror) from e

                    pg.time.wait(FILE_ATTEMPT_DELAY * num_system_attempts)
                elif e.winerror in _WINDOWS_LOCKED_FILE_CODES:
                    num_lock_attempts += 1
                    if num_lock_attempts == NUM_MAX_FILE_ATTEMPTS:
                        raise LockException from e

                    pg.time.wait(FILE_ATTEMPT_DELAY * num_lock_attempts)
                else:
                    raise FileException(e.strerror) from e
elif fcntl is not None:
    from errno import *

    _LINUX_SYSTEM_FAILURES_CODES: Final[tuple[int, ...]] = (
        EINTR, EIO, ENOMEM, EBUSY, ENFILE, EMFILE
    )

    def try_lock_file(file_obj: TextIO | BinaryIO, shared: bool) -> None:
        """
        Locks a file.

        Args:
            file, shared flag
        """

        num_system_attempts: int = 0
        num_lock_attempts: int = 0
        while True:
            try:
                flag: int = (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB
                fcntl.flock(file_obj, flag)
                break
            except EOFError as e:
                raise FileException("End of file reached.") from e
            except OSError as e:
                if e.errno == ENOENT:
                    raise FileNotFoundError from e
                if e.errno == EPERM or e.errno == EROFS:
                    raise PermissionError from e

                if e.errno in _LINUX_SYSTEM_FAILURES_CODES:
                    num_system_attempts += 1
                    if num_system_attempts == NUM_MAX_FILE_ATTEMPTS:
                        raise FileException(f"{e}.") from e

                    pg.time.wait(FILE_ATTEMPT_DELAY * num_system_attempts)
                elif e.errno == EAGAIN or e.errno == EACCES:
                    num_lock_attempts += 1
                    if num_lock_attempts == NUM_MAX_FILE_ATTEMPTS:
                        raise LockException from e

                    pg.time.wait(FILE_ATTEMPT_DELAY * num_lock_attempts)
                else:
                    raise FileException(f"{e}.") from e
else:
    print(f"File locking not implemented for this operating system: {system()}.")

    def try_lock_file(file_obj: TextIO | BinaryIO, shared: bool) -> None:
        """
        Locks a file.

        Args:
            file, shared flag
        """
