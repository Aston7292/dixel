"""Functions to operate with files."""

from pathlib import Path


def has_file_access(file_obj: Path) -> bool:
    """
    Checks if a file is accessible.

    Args:
        file object
    Returns:
        True if the file is accessible else False
    """

    try:
        with file_obj.open('a', encoding='utf-8'):
            pass
    except PermissionError:
        return False

    return True


def create_file(file_path: str, flag: str) -> bool:
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
    elif not has_file_access(Path(file_path)):
        print("Permission denied.")
        should_exit = True

    return should_exit


def create_nested_file(file_path: str, flag: str) -> bool:
    """
    Creates a file and it's directories if the flag is --mk-dir.

    Args:
        file path, flag
    Returns:
        should exit flag
    """

    should_exit: bool = False
    if flag != "--mk-dir":
        print(
            "The directory doesn't exist, to create it add --mk-dir.\n"
            f"\"{file_path}\" --mk-dir"
        )
        should_exit = True
    else:
        try:
            Path(file_path).parent.mkdir(parents=True)
        except PermissionError:
            print("Permission denied.")
            should_exit = True

    return should_exit
