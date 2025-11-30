"""Class to choose a number in a range with an input box."""

from typing import Self

import pygame as pg
from pygame.locals import *

from src.classes.clickable import SpammableButton
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE, KEYBOARD

import src.vars as my_vars
from src.obj_utils import UIElement, ObjInfo, resize_obj
from src.type_utils import XY, WH, BlitInfo, RectPos
from src.consts import WHITE, MOUSE_LEFT, CHR_LIMIT, BG_LAYER, ELEMENT_LAYER
from src.imgs import ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG, ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG



class InputBox:
    """Class to create a text, single-line input box"""

    __slots__ = (
        "_init_pos", "_img", "rect",
        "_init_w", "_init_h",
        "_max_len", "cursor_i", "_is_selected", "_last_cursor_blink_time", "_should_show_cursor",
        "text_label", "_cursor_img", "cursor_rect",
        "_prev_selected_obj", "prev_text", "_prev_cursor_i",
        "hover_rects", "layer", "blit_sequence", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_IBEAM

    def __init__(
            self: Self, pos: RectPos, wh: WH, max_len: int,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the input box, text and cursor.

        Args:
            position, size, max length, base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos

        self._img: pg.Surface = pg.Surface(wh)
        self.rect: pg.Rect = pg.Rect(0, 0, *self._img.get_size())
        setattr(self.rect, self._init_pos.coord_type, (self._init_pos.x, self._init_pos.y))

        self._init_w: int = self.rect.w
        self._init_h: int = self.rect.h

        self._max_len: int = max_len
        self.cursor_i: int = 0
        self._is_selected: bool = False
        self._last_cursor_blink_time: int = my_vars.ticks
        self._should_show_cursor: bool = True

        self.text_label: TextLabel = TextLabel(
            RectPos(self.rect.centerx, self.rect.centery, "center"),
            "0", base_layer
        )
        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_rect: pg.Rect = pg.Rect(0, 0, *self._cursor_img.get_size())
        self.cursor_rect.topleft = (
            self.text_label.get_x_at(self.cursor_i),
            self.text_label.rect.y,
        )

        self._prev_selected_obj: UIElement | None = None
        self.prev_text: str = self.text_label.text
        self._prev_cursor_i: int = self.cursor_i

        self.hover_rects: tuple[pg.Rect, ...] = (self.rect,)
        self.layer: int = base_layer + ELEMENT_LAYER
        self.blit_sequence: list[BlitInfo] = [(self._img, self.rect, self.layer)]
        self.objs_info: tuple[ObjInfo, ...] = (ObjInfo(self.text_label),)

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._last_cursor_blink_time = my_vars.ticks
        self._should_show_cursor = True

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self.cursor_i = self._prev_cursor_i = 0
        self._is_selected = False
        self._prev_selected_obj = None

        self.cursor_rect.x = self.text_label.get_x_at(self.cursor_i)

    def resize(self: Self) -> None:
        """Resizes the object."""

        xy: XY

        xy, self.rect.size = resize_obj(self._init_pos, self._init_w, self._init_h)
        self._img = pg.Surface(self.rect.size)
        setattr(self.rect, self._init_pos.coord_type, xy)

        cursor_wh: WH = (1, self.text_label.rect.h)
        self._cursor_img = pg.transform.scale(self._cursor_img, cursor_wh).convert()
        self.cursor_rect.topleft = (
            self.text_label.get_x_at(self.cursor_i),
            self.text_label.rect.y,
        )

        self.blit_sequence[0] = (self._img, self.rect, self.layer)

    def _handle_move_with_keys(self: Self) -> None:
        """Handles moving the cursor with the keyboard."""

        if K_LEFT  in KEYBOARD.timed:
            self.cursor_i = 0        if KEYBOARD.is_ctrl_on else max(self.cursor_i - 1, 0)
        if K_RIGHT in KEYBOARD.timed:
            text_len: int = len(self.text_label.text)
            self.cursor_i = text_len if KEYBOARD.is_ctrl_on else min(self.cursor_i + 1, text_len)
        if K_HOME in KEYBOARD.pressed:
            self.cursor_i = 0
        if K_END  in KEYBOARD.pressed:
            self.cursor_i = len(self.text_label.text)

    def _filter_char(self: Self, char: str) -> str:
        """
        Returns the character if it's valid.

        Args:
            char
        Returns:
            char if it's valid, empty string if not
        """

        return char if char.isprintable() else ""

    def _handle_paste(self: Self) -> None:
        """Handles pasting from the clipboard with the keyboard."""

        prev_text: str = self.text_label.text

        text: str = "".join(map(self._filter_char, pg.scrap.get_text()))
        self._handle_insertion(text)
        if self.text_label.text != prev_text:
            self.cursor_i = min(self.cursor_i + len(text), self._max_len)

    def _handle_post_insertion(self: Self) -> None:
        """Normalizes the text after it was inserted."""

    def _handle_deletion(self: Self) -> None:
        """Handles backspace and delete and moves the cursor."""

        if   KEYBOARD.timed[-1] == K_DELETE:
            self.text_label.text = (
                self.text_label.text[:self.cursor_i] +
                self.text_label.text[self.cursor_i + 1:]
            )
        elif KEYBOARD.timed[-1] == K_BACKSPACE:
            self.text_label.text = (
                self.text_label.text[:max(self.cursor_i - 1, 0)] +
                self.text_label.text[self.cursor_i:]
            )
            self.cursor_i = max(self.cursor_i - 1, 0)

    def _handle_insertion(self: Self, added_text: str) -> None:
        """
        Inserts a character at the cursor position and moves the cursor.

        Args:
            text to add
        """

        if added_text != "":
            first_half: str = self.text_label.text[:self.cursor_i]
            second_half: str = self.text_label.text[self.cursor_i:]
            self.text_label.text = (first_half + added_text + second_half)
            self._handle_post_insertion()

    def _handle_timed_keys(self: Self) -> None:
        """Handles copying, pasting, deleting and inserting with the keyboard."""

        if KEYBOARD.is_ctrl_on:
            if K_c in KEYBOARD.timed:
                pg.scrap.put_text("")
            elif K_v in KEYBOARD.timed:
                self._handle_paste()

        is_ctrl_c_pressed: bool = KEYBOARD.is_ctrl_on and K_c in KEYBOARD.timed
        if KEYBOARD.timed[-1] in (K_BACKSPACE, K_DELETE):
            self._handle_deletion()
        elif not is_ctrl_c_pressed and KEYBOARD.timed[-1] <= CHR_LIMIT:
            prev_text: str = self.text_label.text

            char: str = self._filter_char(chr(KEYBOARD.timed[-1]))
            self._handle_insertion(char)
            if self.text_label.text != prev_text:
                self.cursor_i = min(self.cursor_i + 1, len(self.text_label.text))

    def refresh(self: Self) -> None:
        """Refreshes the text label and cursor position."""

        if self.text_label.text != self.prev_text:
            self.text_label.set_text(self.text_label.text)
            self.prev_text = self.text_label.text
            self._prev_cursor_i = -1
        if self.cursor_i != self._prev_cursor_i:
            self.cursor_rect.x = self.text_label.get_x_at(self.cursor_i)
            self._last_cursor_blink_time = my_vars.ticks
            self._should_show_cursor = True

            self._prev_cursor_i = self.cursor_i

        self.blit_sequence = [(self._img, self.rect, self.layer)]
        if self._is_selected:
            if my_vars.ticks - self._last_cursor_blink_time >= 512:
                self._last_cursor_blink_time = my_vars.ticks
                self._should_show_cursor = not self._should_show_cursor

            if self._should_show_cursor:
                self.blit_sequence.append((self._cursor_img, self.cursor_rect, self.layer))

    def upt(self: Self, selected_obj: UIElement) -> UIElement:
        """
        Allows typing numbers, moving the cursor and deleting a specific character.

        Refresh should be called when everything is updated.

        Args:
            selected object
        Returns:
            selected object
        """

        if MOUSE.hovered_obj == self and MOUSE.released[MOUSE_LEFT]:
            self.cursor_i = self.text_label.get_closest_to(MOUSE.x)
            selected_obj = self

        self._is_selected = selected_obj == self
        if self._is_selected:
            if selected_obj != self._prev_selected_obj:
                self._last_cursor_blink_time = my_vars.ticks
                self._should_show_cursor = True

            if KEYBOARD.pressed != ():
                self._handle_move_with_keys()
            if KEYBOARD.timed != ():
                self._handle_timed_keys()

        self._prev_selected_obj = selected_obj

        return selected_obj


class NumInputBox(InputBox):
    """Class to choose a number in range with an input box."""

    __slots__ = (
        "value", "min_limit", "max_limit",
        "_decrease", "_increase",
    )

    half_w: int = round((64 + ARROW_UP_OFF_IMG.get_width() + 5) / 2)

    def __init__(
            self: Self, pos: RectPos, min_limit: int, max_limit: int,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the input box, text and cursor.

        Args:
            position, minimum limit, maximum limit, base layer (default = BG_LAYER)
        """

        max_len: int = len(str(max_limit))
        super().__init__(pos, (64, 40), max_len, base_layer)

        self.value: int = min_limit
        self.min_limit: int = min_limit
        self.max_limit: int = max_limit

        self._decrease: SpammableButton = SpammableButton(
            RectPos(self.rect.right + 5, self.rect.centery + 3, "topleft"),
            (ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG), " - \n(CTRL -)", base_layer
        )
        self._increase: SpammableButton = SpammableButton(
            RectPos(self.rect.right + 5, self.rect.centery - 3, "bottomleft"),
            (ARROW_UP_OFF_IMG  , ARROW_UP_ON_IMG  ), " + \n(CTRL +)", base_layer
        )
        self._decrease.set_hover_extra_size(5, 10, 3 , 10)
        self._increase.set_hover_extra_size(5, 10, 10, 3)

        self.objs_info += (ObjInfo(self._decrease), ObjInfo(self._increase))

    def set_value(self: Self, value: int) -> None:
        """
        Sets the value and resets the cursor.

        Args:
            value
        """

        self.value = value
        self.text_label.text = (
            "" if self.text_label.text == "" and self.value == self.min_limit else
            str(self.value)
        )
        self.cursor_i = min(self.cursor_i, len(self.text_label.text))

    def _filter_char(self: Self, char: str) -> str:
        """
        Returns the character if it's valid.

        Args:
            char
        Returns:
            char if it's valid, empty string if not
        """

        return char if char.isdigit() else ""

    def _handle_deletion(self: Self) -> None:
        """Handles backspace and delete and moves the cursor."""

        super()._handle_deletion()

        uncapped_value: int = (
            self.min_limit if self.text_label.text == "" else
            int(self.text_label.text)
        )
        self.set_value(max(uncapped_value, self.min_limit))

    def _handle_post_insertion(self: Self) -> None:
        """Normalizes the text after it was inserted."""

        if self.text_label.text != "":
            self.text_label.text = self.text_label.text.lstrip("0") or str(self.min_limit)
            self.text_label.text = self.text_label.text[:self._max_len]

        if   int(self.text_label.text) < self.min_limit:
            self.text_label.text = str(self.min_limit)
        elif int(self.text_label.text) > self.max_limit:
            self.text_label.text = str(self.max_limit)
        self.value = int(self.text_label.text)

    def _handle_timed_keys(self: Self) -> None:
        """
        Handles copying, pasting, deleting, inserting, decrementing and incrementing with the keyboard.
        """

        super()._handle_timed_keys()

        if K_MINUS in KEYBOARD.timed:
            self.set_value(
                self.min_limit if KEYBOARD.is_ctrl_on else
                max(self.value - 1, self.min_limit)
            )
        if K_PLUS in KEYBOARD.timed:
            self.set_value(
                self.max_limit if KEYBOARD.is_ctrl_on else
                min(self.value + 1, self.max_limit)
            )

    def upt(self: Self, selected_obj: UIElement) -> UIElement:
        """
        Allows typing numbers, moving the cursor and deleting a specific character.

        Refresh should be called when everything is updated.

        Args:
            selected object
        Returns:
            selected object
        """

        selected_obj = super().upt(selected_obj)

        is_decrease_clicked: bool = self._decrease.upt()
        if is_decrease_clicked:
            self.set_value(max(self.value - 1, self.min_limit))
            self.cursor_i = min(self.cursor_i, len(self.text_label.text))

        is_increase_clicked: bool = self._increase.upt()
        if is_increase_clicked:
            self.set_value(min(self.value + 1, self.max_limit))

        return selected_obj

class ColorInputBox(InputBox):
    """Class to choose an hex color with an input box."""

    __slots__ = (
        "value",
    )

    cursor_type: int = SYSTEM_CURSOR_IBEAM

    def __init__(self: Self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the input box, text and cursor.

        Args:
            position, base layer (default = BG_LAYER)
        """

        super().__init__(pos, (100, 40), 6, base_layer)

        self.value: str = "000000"

        hashtag_text_label: TextLabel = TextLabel(
            RectPos(self.rect.x - 4, self.rect.centery, "midright"),
            "#", base_layer
        )
        self.objs_info += (ObjInfo(hashtag_text_label),)

    def set_value(self: Self, value: str) -> None:
        """
        Sets the value and resets the cursor.

        Args:
            value
        """

        self.value = value
        self.text_label.text = self.value
        # Clamping cursor_i is unnecessary

    def _filter_char(self: Self, char: str) -> str:
        """
        Returns the character if it's valid.

        Args:
            char
        Returns:
            char if it's valid, empty string if not
        """

        return char.lower() if char in "1234567890abcdefABCDEF" else ""

    def _handle_deletion(self: Self) -> None:
        """Handles backspace and delete and moves the cursor."""

        super()._handle_deletion()

        text: str = self.text_label.text
        self.value = (
            text[0] * 2 + text[1] * 2 + text[2] * 2 if len(text) == 3 else
            text.ljust(6, "0")
        )

    def _handle_post_insertion(self: Self) -> None:
        """Normalizes the text after it was inserted."""

        self.text_label.text = self.text_label.text[:self._max_len]

        text: str = self.text_label.text
        self.value = (
            text[0] * 2 + text[1] * 2 + text[2] * 2 if len(text) == 3 else
            text.ljust(6, "0")
        )
