"""Classes to store devices info."""

from typing import TypeAlias, Final, Any

import pygame as pg
from pygame.locals import *

from src.consts import CHR_LIMIT

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
        "x", "y", "pressed", "released", "scroll_amount", "hovered_obj", "_cursor_type"
    )

    def __init__(self) -> None:
        """Initializes the info."""

        self.x: int = -1
        self.y: int = -1
        self.pressed: tuple[bool, bool, bool] = (False, False, False)
        self.released: list[bool] = [False, False, False, False, False]
        self.scroll_amount: int = 0

        self.hovered_obj: Any = None
        self._cursor_type: int = SYSTEM_CURSOR_ARROW

    def refresh_type(self) -> None:
        """Refreshes the cursor type using the cursor_type attribute of the hovered object."""

        prev_cursor_type: int = self._cursor_type
        has_type: bool = hasattr(self.hovered_obj, "cursor_type")
        self._cursor_type = self.hovered_obj.cursor_type if has_type else SYSTEM_CURSOR_ARROW

        if self._cursor_type != prev_cursor_type:
            pg.mouse.set_cursor(self._cursor_type)


class Keyboard:
    """Class for storing keyboard info."""

    __slots__ = (
        "pressed", "timed", "is_ctrl_on", "is_shift_on", "is_alt_on", "is_numpad_on",
        "_timed_keys_interval", "_prev_timed_keys_update", "_alt_k"
    )

    def __init__(self) -> None:
        """Initializes the info."""

        self.pressed: list[int] = []
        self.timed: list[int] = []
        self.is_ctrl_on: bool = False
        self.is_shift_on: bool = False
        self.is_alt_on: bool = False
        self.is_numpad_on: bool = False

        self._timed_keys_interval: int = 150
        self._prev_timed_keys_update: int = -self._timed_keys_interval
        self._alt_k: str = ""

    def refresh_timed(self) -> None:
        """Refreshes the timed keys once every 150ms and adds the alt key if present."""

        self.timed = []
        if (
            self.pressed != [] and
            pg.time.get_ticks() - self._prev_timed_keys_update >= self._timed_keys_interval
        ):
            numpad_map_i: int = int(self.is_numpad_on)
            self.timed = [
                _NUMPAD_MAP[k][numpad_map_i] if k in _NUMPAD_MAP else k
                for k in self.pressed
            ]

            self._timed_keys_interval = max(self._timed_keys_interval - 7, 50)
            self._prev_timed_keys_update = pg.time.get_ticks()

        if self._alt_k != "" and not self.is_alt_on:
            self.timed.append(int(self._alt_k))
            self._alt_k = ""

    def add(self, k: int) -> None:
        """
        Adds a key to the pressed_keys if it's not using alt.

        Args:
            key
        """

        converted_k: int = k
        if converted_k in _NUMPAD_MAP:
            numpad_map_i: int = int(self.is_numpad_on)
            converted_k = _NUMPAD_MAP[converted_k][numpad_map_i]

        if self.is_alt_on and (K_0 <= converted_k <= K_9):
            self._alt_k += chr(converted_k)
            if int(self._alt_k) > CHR_LIMIT:
                self._alt_k = self._alt_k[-1]

            self._alt_k = self._alt_k.lstrip("0")
        else:
            self.pressed.append(k)

        self.is_ctrl_on = pg.key.get_mods() & KMOD_CTRL != 0
        self.is_shift_on = pg.key.get_mods() & KMOD_SHIFT != 0
        self.is_alt_on = pg.key.get_mods() & KMOD_ALT != 0
        self.is_numpad_on = pg.key.get_mods() & KMOD_NUM != 0
        self._timed_keys_interval = 150
        self._prev_timed_keys_update = -self._timed_keys_interval

    def remove(self, k: int) -> None:
        """
        Handles key releases.

        Args:
            key
        """

        if k in self.pressed:  # Numbers pressed with alt aren't inserted
            self.pressed.remove(k)

        self.is_ctrl_on = pg.key.get_mods() & KMOD_CTRL != 0
        self.is_shift_on = pg.key.get_mods() & KMOD_SHIFT != 0
        self.is_alt_on = pg.key.get_mods() & KMOD_ALT != 0
        self.is_numpad_on = pg.key.get_mods() & KMOD_NUM != 0
        self._timed_keys_interval = 150
