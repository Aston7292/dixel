"""Class to choose a number in a range with an input box."""

from typing import Final, Any

import pygame as pg
from pygame.locals import *

from src.classes.clickable import SpammableButton
from src.classes.text_label import TextLabel
from src.classes.devices import Mouse, Keyboard

from src.utils import RectPos, ObjInfo, resize_obj
from src.type_utils import XY, BlitInfo
from src.consts import MOUSE_LEFT, CHR_LIMIT, WHITE, BG_LAYER, ELEMENT_LAYER, TIME
from src.imgs import ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG, ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG

_INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((64, 40))


class NumInputBox:
    """Class to choose a number in range with an input box."""

    __slots__ = (
        "_init_pos", "_img", "rect", "_init_w", "_init_h", "value", "min_limit", "max_limit",
        "_cursor_i", "_is_selected", "_last_cursor_blink_time", "_should_show_cursor", "layer",
        "text_label", "_prev_text", "_prev_cursor_i", "_cursor_img", "cursor_rect", "_increase",
        "_decrease", "objs_info"
    )

    cursor_type: int = SYSTEM_CURSOR_IBEAM

    def __init__(
            self, pos: RectPos, min_limit: int, max_limit: int, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the input box, text and cursor.

        Args:
            position, minimum limit, maximum limit, base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos

        self._img: pg.Surface = _INPUT_BOX_IMG
        self.rect: pg.Rect = pg.Rect(0, 0, *self._img.get_size())
        setattr(self.rect, self._init_pos.coord_type, (self._init_pos.x, self._init_pos.y))

        self._init_w: int = self.rect.w
        self._init_h: int = self.rect.h

        self.value: int = min_limit
        self.min_limit: int = min_limit
        self.max_limit: int = max_limit

        self._cursor_i: int = 0
        self._is_selected: bool = False
        self._last_cursor_blink_time: int = TIME.ticks
        self._should_show_cursor: bool = True

        self.layer: int = base_layer + ELEMENT_LAYER

        self.text_label = TextLabel(
            RectPos(self.rect.centerx, self.rect.centery, "center"),
            "", base_layer
        )

        self._prev_text: int = self.text_label.text
        self._prev_cursor_i: int = self._cursor_i

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_rect: pg.Rect = pg.Rect(
            self.text_label.rect.topleft, self._cursor_img.get_size()
        )

        self._increase: SpammableButton = SpammableButton(
            RectPos(self.rect.right + 5, self.rect.centery - 5, "bottomleft"),
            [ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG], "Increase", base_layer
        )
        self._decrease: SpammableButton = SpammableButton(
            RectPos(self.rect.right + 5, self.rect.centery + 5, "topleft"),
            [ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG], "Decrease", base_layer
        )
        self._increase.set_hover_extra_size(5, 10, 10, 5)
        self._decrease.set_hover_extra_size(5, 10, 5, 10)

        self.objs_info: list[ObjInfo] = [
            ObjInfo(self.text_label), ObjInfo(self._increase), ObjInfo(self._decrease)
        ]

    @property
    def blit_sequence(self) -> list[BlitInfo]:
        """
        Gets the blit sequence and handles the blinking cursor.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: list[BlitInfo] = [(self._img, self.rect, self.layer)]
        if self._is_selected:
            if TIME.ticks - self._last_cursor_blink_time >= 500:
                self._should_show_cursor = not self._should_show_cursor
                self._last_cursor_blink_time = TIME.ticks
            if self._should_show_cursor:
                sequence.append((self._cursor_img, self.cursor_rect, self.layer))

        return sequence

    def get_hovering(self, mouse_xy: XY) -> bool:
        """
        Gets the hovering flag.

        Args:
            mouse xy
        Returns:
            hovering flag
        """

        return self.rect.collidepoint(mouse_xy)

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._is_selected = False

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY

        xy, self.rect.size = resize_obj(
            self._init_pos, self._init_w, self._init_h, win_w_ratio, win_h_ratio
        )
        self._img = pg.transform.scale(self._img, self.rect.size).convert()
        setattr(self.rect, self._init_pos.coord_type, xy)

        self._cursor_img = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_rect.topleft = (
            self.text_label.get_x_at(self._cursor_i), self.text_label.rect.y
        )

    def set_cursor_i(self, cursor_i: int) -> None:
        """
        Sets the cursor index and resets blinking.

        Args:
            cursor index
        """

        self._cursor_i = cursor_i
        self._last_cursor_blink_time = TIME.ticks
        self._should_show_cursor = True

    def _move_with_keys(self, keyboard: Keyboard) -> None:
        """
        Moves the cursor with the keyboard.

        Args:
            keyboard
        """

        if K_LEFT in keyboard.timed:
            self._cursor_i = 0 if keyboard.is_ctrl_on else max(self._cursor_i - 1, 0)
        if K_RIGHT in keyboard.timed:
            text_len: int = len(self.text_label.text)
            self._cursor_i = text_len if keyboard.is_ctrl_on else min(self._cursor_i + 1, text_len)
        if K_HOME in keyboard.pressed:
            self._cursor_i = 0
        if K_END in keyboard.pressed:
            self._cursor_i = len(self.text_label.text)

    def _handle_deletion(self, k: int) -> None:
        """
        Handles backspace and delete and moves the cursor.

        Args:
            key
        """

        first_part: str
        second_part: str

        if k == K_DELETE:
            first_part = self.text_label.text[:self._cursor_i]
            second_part = self.text_label.text[self._cursor_i + 1:]
            self.text_label.text = first_part + second_part
        elif k == K_BACKSPACE:
            first_part = self.text_label.text[:self._cursor_i - 1]
            second_part = self.text_label.text[self._cursor_i:]
            self.text_label.text = first_part + second_part
            self._cursor_i = max(self._cursor_i - 1, 0)

        if self.text_label.text.startswith("0"):  # If it's empty keep it empty
            self.text_label.text = self.text_label.text.lstrip("0") or str(self.min_limit)
        self.value = int(self.text_label.text or self.min_limit)

    def _insert_char(self, char: str) -> None:
        """
        Inserts a character at the cursor position and moves the cursor.

        Args:
            character
        """

        prev_text: str = self.text_label.text

        first_half: str = self.text_label.text[:self._cursor_i]
        second_half: str = self.text_label.text[self._cursor_i:]
        self.text_label.text = first_half + char + second_half
        self.text_label.text = self.text_label.text.lstrip("0") or str(self.min_limit)

        max_len: int = len(str(self.max_limit))
        self.text_label.text = self.text_label.text[:max_len]

        if int(self.text_label.text) < self.min_limit:
            self.text_label.text = str(self.min_limit)
        elif int(self.text_label.text) > self.max_limit:
            self.text_label.text = str(self.max_limit)

        self.value = int(self.text_label.text)
        if self.text_label.text != prev_text:
            self._cursor_i = min(self._cursor_i + 1, len(self.text_label.text))

    def _handle_k(self, k: int) -> None:
        """
        Handles a key.

        Args:
            key
        """

        if k == K_BACKSPACE or k == K_DELETE:
            self._handle_deletion(k)
        elif k <= CHR_LIMIT:
            char: str = chr(k)
            if char.isdigit():
                self._insert_char(char)

    def refresh(self) -> None:
        """Refreshes text label and cursor position."""

        if self.text_label.text != self._prev_text:
            self.text_label.set_text(self.text_label.text)
            self.cursor_rect.x = self.text_label.get_x_at(self._cursor_i)
            self._should_show_cursor = True
            self._last_cursor_blink_time = TIME.ticks
        elif self._cursor_i != self._prev_cursor_i:
            self.cursor_rect.x = self.text_label.get_x_at(self._cursor_i)
            self._should_show_cursor = True
            self._last_cursor_blink_time = TIME.ticks

        self._prev_text = self.text_label.text
        self._prev_cursor_i = self._cursor_i

    def upt(self, mouse: Mouse, keyboard: Keyboard, selected_obj: Any) -> bool:
        """
        Allows typing numbers, moving the cursor and deleting a specific character.

        Refresh should be called when everything is updated.

        Args:
            mouse, keyboard, selected obj
        Returns:
            clicked flag
        """

        is_clicked: bool = mouse.hovered_obj == self and mouse.released[MOUSE_LEFT]
        if is_clicked:
            self._cursor_i = self.text_label.get_closest_to(mouse.x)
            selected_obj = self

        self._is_selected = selected_obj == self
        if self._is_selected:
            if keyboard.pressed != []:
                self._move_with_keys(keyboard)
            if keyboard.timed != []:
                self._handle_k(keyboard.timed[-1])

        is_increase_clicked: bool = self._increase.upt(mouse)
        if is_increase_clicked:
            self.value = min(self.value + 1, self.max_limit)
            self.text_label.text = str(self.value)
        is_decrease_clicked: bool = self._decrease.upt(mouse)
        if is_decrease_clicked:
            self.value = max(self.value - 1, self.min_limit)
            self.text_label.text = str(self.value)

        return is_clicked
