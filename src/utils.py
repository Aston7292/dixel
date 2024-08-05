"""
collections of shared funcs/dataclasses
"""

from dataclasses import dataclass
from pygetwindow import getWindowsWithTitle, BaseWindow  # type: ignore
from screeninfo import get_monitors, Monitor
from typing import Tuple


@dataclass
class Point:
    """
    dataclass for representing the coordinates of a point
    takes x and y
    """

    x: int
    y: int

    @property
    def xy(self) -> Tuple[int, int]:
        """
        returns x and y as a tuple
        """

        return self.x, self.y


@dataclass
class RectPos:
    """
    dataclass for representing the position of a rect
    takes x and y as tuple and the value they represent (e.g. topleft)
    """

    x: float
    y: float
    pos: str

    @property
    def xy(self) -> Tuple[float, float]:
        """
        returns x and y as a tuple
        """

        return self.x, self.y


@dataclass
class Size:
    """
    dataclass for representing the size of an object
    takes width and height
    """

    w: int
    h: int

    @property
    def wh(self) -> Tuple[int, int]:
        """
        returns w and h as a tuple
        """

        return self.w, self.h


@dataclass
class MouseInfo:
    """
    dataclass for storing every info needed about the mouse
    """

    x: int
    y: int
    buttons: Tuple[bool, ...]
    released: Tuple[bool, ...]

    @property
    def xy(self) -> Tuple[int, int]:
        """
        returns x and y as a tuple
        """

        return self.x, self.y


def get_monitor_size() -> tuple[int, int]:
    """
    returns the size of the monitor in which the window is in
    raises ValueError if the monitor isn't found
    """

    win_handler: BaseWindow = getWindowsWithTitle('Dixel')[0]

    monitors: Tuple[Monitor, ...] = tuple(get_monitors())
    for monitor in monitors:
        if (
                win_handler.right >= monitor.x and
                win_handler.left <= monitor.x + monitor.width and
                win_handler.bottom >= monitor.y and
                win_handler.top <= monitor.y + monitor.height
        ):
            return monitor.width, monitor.height

    raise ValueError("Couldn't find the monitor of the window.")
