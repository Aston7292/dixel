"""Classes to store devices info."""

from typing import Final

import pygame as pg
from pygame.locals import *

from src.utils import UIElement
import src.vars as VARS

_NUMPAD_FIRST_K: Final[int] = K_KP_1
_NUMPAD_LAST_K: Final[int]  = K_KP_PERIOD
_NUMPAD_MAP: Final[list[int]] = [
    K_END     , K_1,
    K_DOWN    , K_2,
    K_PAGEDOWN, K_3,
    K_LEFT    , K_4,
    K_UNKNOWN , K_5,
    K_RIGHT   , K_6,
    K_HOME    , K_7,
    K_UP      , K_8,
    K_PAGEUP  , K_9,
    K_INSERT  , K_0,
    K_DELETE  , K_PERIOD,
]


class _Mouse:
    """Class to store mouse info."""

    __slots__ = (
        "x", "y", "prev_x", "prev_y",
        "pressed", "released", "scroll_amount",
        "hovered_obj", "_cursor_type",
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

        self.hovered_obj: UIElement | None = None
        self._cursor_type: int = SYSTEM_CURSOR_ARROW

    def refresh_pos(self) -> None:
        """Refreshes the position, if a coordinate is outside the window it will be -1."""

        self.x, self.y = pg.mouse.get_pos()
        if not pg.mouse.get_focused():
            if self.x == 0:
                self.x = -1
            if self.y == 0:
                self.y = -1

    def refresh_hovered_obj(self, state_active_objs: list[UIElement]) -> None:
        """
        Refreshes the hovered object with the get_hovering method of the active objects.

        Args:
            state active objects
        """

        hovered_objs: list[UIElement] = [
            obj
            for obj in state_active_objs
            for rect in obj.hover_rects
            if rect.x <= self.x < (rect.x + rect.w) and rect.y <= self.y < (rect.y + rect.h)
        ]

        if hovered_objs == []:
            self.hovered_obj = None
        else:
            hovered_objs.sort(key=lambda obj: obj.layer)
            self.hovered_obj = hovered_objs[-1]

    def refresh_type(self) -> None:
        """Refreshes the cursor type using the cursor_type attribute of the hovered object."""

        new_cursor_type: int = (
            SYSTEM_CURSOR_ARROW if self.hovered_obj is None else self.hovered_obj.cursor_type
        )

        if self._cursor_type != new_cursor_type:
            self._cursor_type = new_cursor_type
            pg.mouse.set_cursor(self._cursor_type)


class _Keyboard:
    """Class to store keyboard info."""

    __slots__ = (
        "_raws", "pressed", "released", "timed",
        "is_ctrl_on", "is_shift_on", "is_alt_on", "is_numpad_on",
        "_timed_interval", "_prev_timed_refresh", "_alt_k",
    )

    def __init__(self) -> None:
        """Initializes the info."""

        self._raws: list[int]    = []
        self.pressed: list[int]  = []
        self.released: list[int] = []
        self.timed: list[int]    = []

        self.is_ctrl_on: bool   = False
        self.is_shift_on: bool  = False
        self.is_alt_on: bool    = False
        self.is_numpad_on: bool = False

        self._timed_interval: int = 150
        self._prev_timed_refresh: int = -self._timed_interval
        self._alt_k: str = ""

    def refresh_timed(self) -> None:
        """Fills the timed keys once every 150ms + acceleration and adds the alt_k if needed."""

        if self.pressed == [] or (VARS.ticks - self._prev_timed_refresh < self._timed_interval):
            self.timed = []
        else:
            self.timed = self.pressed.copy()
            self._timed_interval = max(self._timed_interval - 8, 50)
            self._prev_timed_refresh = VARS.ticks

        if self._alt_k != "" and not self.is_alt_on:
            self.timed.append(int(self._alt_k))
            self._alt_k = ""

    def add(self, k: int) -> None:
        """
        Adds a converted key to the pressed keys if it's not using alt.

        Args:
            key
        """

        self.is_ctrl_on   = (pg.key.get_mods() & KMOD_CTRL ) != 0
        self.is_shift_on  = (pg.key.get_mods() & KMOD_SHIFT) != 0
        self.is_alt_on    = (pg.key.get_mods() & KMOD_ALT  ) != 0
        self.is_numpad_on = (pg.key.get_mods() & KMOD_NUM  ) != 0

        converted_k: int = k
        numpad_offset: int = int(self.is_numpad_on)
        if _NUMPAD_FIRST_K <= k <= _NUMPAD_LAST_K:
            k_i: int = (k - _NUMPAD_FIRST_K) * 2
            converted_k = _NUMPAD_MAP[k_i + numpad_offset]

        if self.is_alt_on and K_0 <= converted_k <= K_9:
            self._alt_k += chr(converted_k)
            if int(self._alt_k) > 1_114_111:
                self._alt_k = self._alt_k[-1]

            self._alt_k = self._alt_k.lstrip("0")
        else:
            self._raws.append(k)
            self.pressed = [
                _NUMPAD_MAP[((k - _NUMPAD_FIRST_K) * 2) + numpad_offset]
                if _NUMPAD_FIRST_K <= k <= _NUMPAD_LAST_K else k
                for k in self._raws
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

        self.is_ctrl_on   = (pg.key.get_mods() & KMOD_CTRL ) != 0
        self.is_shift_on  = (pg.key.get_mods() & KMOD_SHIFT) != 0
        self.is_alt_on    = (pg.key.get_mods() & KMOD_ALT  ) != 0
        self.is_numpad_on = (pg.key.get_mods() & KMOD_NUM  ) != 0

        if k in self._raws:  # Numbers pressed with alt aren't inserted
            remove_i: int = self._raws.index(k)
            self._raws.pop(remove_i)
            self.pressed.pop(remove_i)

            numpad_offset: int = int(self.is_numpad_on)
            self.pressed = [
                _NUMPAD_MAP[((k - _NUMPAD_FIRST_K) * 2) + numpad_offset]
                if _NUMPAD_FIRST_K <= k <= _NUMPAD_LAST_K else k
                for k in self._raws
            ]

            if _NUMPAD_FIRST_K <= k <= _NUMPAD_LAST_K:
                k_i: int = (k - _NUMPAD_FIRST_K) * 2
                self.released.append(_NUMPAD_MAP[k_i + numpad_offset])
            else:
                self.released.append(k)

        self._timed_interval = 150

    def clear(self) -> None:
        """Clears the keyboard data."""

        self._raws = self.pressed = self.released = self.timed = []
        self.is_ctrl_on = self.is_shift_on = self.is_alt_on = self.is_numpad_on = False

MOUSE: Final[_Mouse] = _Mouse()
KEYBOARD: Final[_Keyboard] = _Keyboard()
