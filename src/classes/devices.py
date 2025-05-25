"""Classes to store devices info."""

from typing import TypeAlias, Final, Any

import pygame as pg
from pygame.locals import *

from src.type_utils import XY
from src.consts import CHR_LIMIT, BG_LAYER, TIME

_NumPadMap: TypeAlias = dict[int, tuple[int, int]]

_NUMPAD_MAP: Final[_NumPadMap] = {
    K_KP_0: (K_INSERT, K_0),
    K_KP_1: (K_END, K_1),
    K_KP_2: (K_DOWN, K_2),
    K_KP_3: (K_PAGEDOWN, K_3),
    K_KP_4: (K_LEFT, K_4),
    K_KP_5: (0, K_5),
    K_KP_6: (K_RIGHT, K_6),
    K_KP_7: (K_HOME, K_7),
    K_KP_8: (K_UP, K_8),
    K_KP_9: (K_PAGEUP, K_9),
    K_KP_PERIOD: (K_DELETE, K_PERIOD)
}


class Mouse:
    """Class for storing mouse info."""

    __slots__ = (
        "x", "y", "prev_x", "prev_y", "pressed", "released", "scroll_amount", "hovered_obj",
        "_cursor_type"
    )

    def __init__(self) -> None:
        """Initializes the info."""

        self.x: int = 0
        self.y: int = 0
        self.prev_x: int = self.x
        self.prev_y: int = self.y

        self.pressed: tuple[bool, bool, bool] = (False, False, False)
        self.released: list[bool] = [False, False, False, False, False]
        self.scroll_amount: int = 0

        self.hovered_obj: Any = None
        self._cursor_type: int = SYSTEM_CURSOR_ARROW

    def refresh_hovered_obj(self, state_active_objs: list[any]) -> None:
        """
            Refreshes the hovered object with the get_hovering method of the active objects.

            Args:
                state active objects
        """

        obj: Any

        xy: XY = (self.x, self.y)
        max_layer: int = BG_LAYER
        for obj in state_active_objs:
            if hasattr(obj, "get_hovering") and obj.get_hovering(xy) and obj.layer >= max_layer:
                self.hovered_obj = obj
                max_layer = obj.layer

    def refresh_type(self) -> None:
        """Refreshes the cursor type using the cursor_type attribute of the hovered object."""

        prev_cursor_type: int = self._cursor_type

        if hasattr(self.hovered_obj, "cursor_type"):
            self._cursor_type = self.hovered_obj.cursor_type
        else:
            self._cursor_type = SYSTEM_CURSOR_ARROW

        if self._cursor_type != prev_cursor_type:
            pg.mouse.set_cursor(self._cursor_type)


class Keyboard:
    """Class for storing keyboard info."""

    __slots__ = (
        "_raws", "pressed", "released", "timed", "is_ctrl_on", "is_shift_on", "is_alt_on",
        "is_numpad_on", "_timed_interval", "_prev_timed_refresh", "_alt_k"
    )

    def __init__(self) -> None:
        """Initializes the info."""

        self._raws: list[int] = []
        self.pressed: list[int] = []
        self.released: list[int] = []
        self.timed: list[int] = []

        self.is_ctrl_on: bool = False
        self.is_shift_on: bool = False
        self.is_alt_on: bool = False
        self.is_numpad_on: bool = False

        self._timed_interval: int = 150
        self._prev_timed_refresh: int = -self._timed_interval
        self._alt_k: str = ""

    def refresh_timed(self) -> None:
        """Fills the timed keys once every 150ms + acceleration and adds the alt_k if needed."""

        if self.pressed == [] or TIME.ticks - self._prev_timed_refresh < self._timed_interval:
            self.timed = []
        else:
            self.timed = self.pressed.copy()
            self._timed_interval = max(self._timed_interval - 7, 50)
            self._prev_timed_refresh = TIME.ticks

        if self._alt_k != "" and not self.is_alt_on:
            self.timed.append(int(self._alt_k))
            self._alt_k = ""

    def add(self, k: int) -> None:
        """
        Adds a converted key to the pressed keys if it's not using alt.

        Args:
            key
        """

        self.is_ctrl_on = pg.key.get_mods() & KMOD_CTRL != 0
        self.is_shift_on = pg.key.get_mods() & KMOD_SHIFT != 0
        self.is_alt_on = pg.key.get_mods() & KMOD_ALT != 0
        self.is_numpad_on = pg.key.get_mods() & KMOD_NUM != 0

        numpad_map_i: int = int(self.is_numpad_on)
        converted_k: int = _NUMPAD_MAP[k][numpad_map_i] if k in _NUMPAD_MAP else k

        if self.is_alt_on and (K_0 <= converted_k <= K_9):
            self._alt_k += chr(converted_k)
            if int(self._alt_k) > CHR_LIMIT:
                self._alt_k = self._alt_k[-1]

            self._alt_k = self._alt_k.lstrip("0")
        else:
            self._raws.append(k)
            self.pressed = [
                _NUMPAD_MAP[k][numpad_map_i] if k in _NUMPAD_MAP else k for k in self._raws
            ]
            self._alt_k = ""

        self._timed_interval = 150
        self._prev_timed_refresh = -self._timed_interval

    def remove(self, k: int) -> None:
        """
        Removes a converted key from the pressed keys and adds it to released ones.

        Args:
            key
        """

        self.is_ctrl_on = pg.key.get_mods() & KMOD_CTRL != 0
        self.is_shift_on = pg.key.get_mods() & KMOD_SHIFT != 0
        self.is_alt_on = pg.key.get_mods() & KMOD_ALT != 0
        self.is_numpad_on = pg.key.get_mods() & KMOD_NUM != 0

        if k in self._raws:  # Numbers pressed with alt aren't inserted
            remove_i: int = self._raws.index(k)
            self._raws.pop(remove_i)
            self.pressed.pop(remove_i)

            numpad_map_i: int = int(self.is_numpad_on)
            self.pressed = [
                _NUMPAD_MAP[k][numpad_map_i] if k in _NUMPAD_MAP else k for k in self._raws
            ]
            self.released.append(_NUMPAD_MAP[k][numpad_map_i] if k in _NUMPAD_MAP else k)

        self._timed_interval = 150

    def clear(self) -> None:
        """Clears the keyboard data."""

        self._raws = self.pressed = self.released = self.timed = []
        self.is_ctrl_on = pg.key.get_mods() & KMOD_CTRL != 0
        self.is_shift_on = pg.key.get_mods() & KMOD_SHIFT != 0
        self.is_alt_on = pg.key.get_mods() & KMOD_ALT != 0
        self.is_numpad_on = pg.key.get_mods() & KMOD_NUM != 0
