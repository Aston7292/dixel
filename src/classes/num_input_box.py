"""Class to choose a number in a range with an input box."""

from typing import Final

import pygame as pg
from pygame.locals import *

from src.classes.clickable import SpammableButton
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import UIElement, RectPos, ObjInfo, resize_obj
from src.type_utils import XY, BlitInfo
import src.vars as VARS
from src.consts import MOUSE_LEFT, WHITE, BG_LAYER, ELEMENT_LAYER
from src.imgs import ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG, ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG

_INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((64, 40))


class NumInputBox:
    """Class to choose a number in range with an input box."""

    __slots__ = (
        "_init_pos", "_img", "rect", "_init_w", "_init_h",
        "value", "min_limit", "max_limit",
        "_cursor_i", "_is_selected", "_last_cursor_blink_time", "_should_show_cursor",
        "text_label", "_prev_text", "_prev_cursor_i",
        "_cursor_img", "cursor_rect",
        "_increase", "_decrease",
        "hover_rects", "layer", "blit_sequence", "objs_info",
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
        self._last_cursor_blink_time: int = VARS.ticks
        self._should_show_cursor: bool = True

        self.text_label: TextLabel = TextLabel(
            RectPos(self.rect.centerx, self.rect.centery, "center"),
            "", base_layer
        )

        self._prev_text: str = self.text_label.text
        self._prev_cursor_i: int = self._cursor_i

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_rect: pg.Rect = pg.Rect(0, 0, *self._cursor_img.get_size())
        self.cursor_rect.topleft = (
            self.text_label.get_x_at(self._cursor_i),
            self.text_label.rect.y
        )

        self._increase: SpammableButton = SpammableButton(
            RectPos(self.rect.right + 5, self.rect.centery - 3, "bottomleft"),
            [ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG],     "(CTRL +)\n(CTRL SHIFT +)", base_layer
        )
        self._decrease: SpammableButton = SpammableButton(
            RectPos(self.rect.right + 5, self.rect.centery + 3, "topleft"),
            [ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG], "(CTRL -)\n(CTRL SHIFT -)", base_layer
        )
        self._increase.set_hover_extra_size(5, 10, 10, 3 )
        self._decrease.set_hover_extra_size(5, 10, 3 , 10)

        self.hover_rects: list[pg.Rect] = [self.rect]
        self.layer: int = base_layer + ELEMENT_LAYER
        self.blit_sequence: list[BlitInfo] = [(self._img, self.rect, self.layer)]
        self.objs_info: list[ObjInfo] = [
            ObjInfo(self.text_label), ObjInfo(self._increase), ObjInfo(self._decrease),
        ]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._last_cursor_blink_time = VARS.ticks
        self._should_show_cursor = True

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._is_selected = False
        if len(self.blit_sequence) == 2:
            self.blit_sequence.pop()  # Remove cursor

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY

        xy, self.rect.size = resize_obj(
            self._init_pos, self._init_w, self._init_h,
            win_w_ratio, win_h_ratio
        )

        self._img = pg.transform.scale(self._img, self.rect.size).convert()
        setattr(self.rect, self._init_pos.coord_type, xy)

        self._cursor_img = pg.transform.scale(self._cursor_img, (1, self.text_label.rect.h))
        self.cursor_rect.topleft = (
            self.text_label.get_x_at(self._cursor_i),
            self.text_label.rect.y
        )

        self.blit_sequence[0] = (self._img, self.rect, self.layer)
        if len(self.blit_sequence) == 2:
            self.blit_sequence[1] = (self._cursor_img, self.cursor_rect, self.layer)

    def set_cursor_i(self, cursor_i: int) -> None:
        """
        Sets the cursor index and resets blinking.

        Args:
            cursor index
        """

        self._cursor_i = cursor_i
        self._last_cursor_blink_time = VARS.ticks
        self._should_show_cursor = True

    def set_value(self, value: int) -> None:
        """
        Sets the value and resets the cursor.

        Args:
            value
        """

        self.value = value
        self.text_label.set_text(str(self.value))
        self.cursor_rect.x = self.text_label.rect.x
        self.set_cursor_i(0)
        # Updating blit_sequence is unnecessary

    def _move_with_keys(self) -> None:
        """Moves the cursor with the keyboard."""

        if K_LEFT  in KEYBOARD.timed:
            self._cursor_i = 0        if KEYBOARD.is_ctrl_on else max(self._cursor_i - 1, 0)
        if K_RIGHT in KEYBOARD.timed:
            text_len: int  = len(self.text_label.text)
            self._cursor_i = text_len if KEYBOARD.is_ctrl_on else min(self._cursor_i + 1, text_len)
        if K_HOME  in KEYBOARD.pressed:
            self._cursor_i = 0
        if K_END   in KEYBOARD.pressed:
            self._cursor_i = len(self.text_label.text)

    def _handle_deletion(self) -> None:
        """Handles backspace and delete and moves the cursor."""

        k: int = KEYBOARD.timed[-1]
        if   k == K_DELETE:
            delete_first_part: str  = self.text_label.text[:self._cursor_i]
            delete_second_part: str = self.text_label.text[self._cursor_i + 1:]
            self.text_label.text = delete_first_part + delete_second_part
        elif k == K_BACKSPACE:
            backspace_first_part: str  = self.text_label.text[:self._cursor_i - 1]
            backspace_second_part: str = self.text_label.text[self._cursor_i:]
            self.text_label.text = backspace_first_part + backspace_second_part
            self._cursor_i = max(self._cursor_i - 1, 0)

        if self.text_label.text.startswith("0"):  # If it's empty keep it empty
            self.text_label.text = self.text_label.text.lstrip("0") or str(self.min_limit)

        self.value = int(self.text_label.text or self.min_limit)
        if self.value < self.min_limit:
            self.value = self.min_limit
            self.text_label.text = str(self.value)

    def _insert_char(self) -> None:
        """Inserts a character at the cursor position and moves the cursor."""

        prev_text: str = self.text_label.text

        first_half: str  = self.text_label.text[:self._cursor_i]
        second_half: str = self.text_label.text[self._cursor_i:]
        self.text_label.text = first_half + chr(KEYBOARD.timed[-1]) + second_half
        self.text_label.text = self.text_label.text.lstrip("0") or str(self.min_limit)

        max_len: int = len(str(self.max_limit))
        self.text_label.text = self.text_label.text[:max_len]

        if   int(self.text_label.text) < self.min_limit:
            self.text_label.text = str(self.min_limit)
        elif int(self.text_label.text) > self.max_limit:
            self.text_label.text = str(self.max_limit)

        self.value = int(self.text_label.text)
        if self.text_label.text != prev_text:
            self._cursor_i = min(self._cursor_i + 1, len(self.text_label.text))

    def refresh(self) -> None:
        """Refreshes text label and cursor position."""

        if   self.text_label.text != self._prev_text:
            self.text_label.set_text(self.text_label.text)
            self.cursor_rect.x = self.text_label.get_x_at(self._cursor_i)
            self._last_cursor_blink_time = VARS.ticks
            self._should_show_cursor = True

            self._prev_text = self.text_label.text
            self._prev_cursor_i = self._cursor_i
        elif self._cursor_i != self._prev_cursor_i:
            self.cursor_rect.x = self.text_label.get_x_at(self._cursor_i)
            self._last_cursor_blink_time = VARS.ticks
            self._should_show_cursor = True

            self._prev_cursor_i = self._cursor_i

        self.blit_sequence = [(self._img, self.rect, self.layer)]
        if self._is_selected:
            if VARS.ticks - self._last_cursor_blink_time >= 500:
                self._last_cursor_blink_time = VARS.ticks
                self._should_show_cursor = not self._should_show_cursor

            if self._should_show_cursor:
                self.blit_sequence.append((self._cursor_img, self.cursor_rect, self.layer))

    def upt(self, selected_obj: UIElement) -> UIElement:
        """
        Allows typing numbers, moving the cursor and deleting a specific character.

        Refresh should be called when everything is updated.

        Args:
            selected object
        Returns:
            selected object
        """

        # Text may be modified externally
        if self.text_label.text != "" :
            self.text_label.text = str(self.value)
        self._cursor_i = min(self._cursor_i, len(self.text_label.text))

        if MOUSE.hovered_obj == self and MOUSE.released[MOUSE_LEFT]:
            self._cursor_i = self.text_label.get_closest_to(MOUSE.x)
            selected_obj = self

        self._is_selected = selected_obj == self
        if self._is_selected:
            if KEYBOARD.pressed != []:
                self._move_with_keys()
            if KEYBOARD.timed != []:
                if KEYBOARD.timed[-1] == K_BACKSPACE or KEYBOARD.timed[-1] == K_DELETE:
                    self._handle_deletion()
                elif K_0 <= KEYBOARD.timed[-1] <= K_9:
                    self._insert_char()


        is_increase_clicked: bool = self._increase.upt()
        if is_increase_clicked or (selected_obj == self and K_PLUS in KEYBOARD.timed):
            self.value = (
                self.max_limit if KEYBOARD.is_ctrl_on and K_PLUS  in KEYBOARD.timed else
                min(self.value + 1, self.max_limit)
            )
            self.text_label.text = str(self.value)

        is_decrease_clicked: bool = self._decrease.upt()
        if is_decrease_clicked or (selected_obj == self and K_MINUS in KEYBOARD.timed):
            self.value = (
                self.min_limit if KEYBOARD.is_ctrl_on and K_MINUS in KEYBOARD.timed else
                max(self.value - 1, self.min_limit)
            )
            self.text_label.text = str(self.value)
            self._cursor_i = min(self._cursor_i, len(self.text_label.text))

        return selected_obj
