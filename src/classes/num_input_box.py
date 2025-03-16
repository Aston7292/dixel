"""
Class to choose a number in range with an input box.

Text and cursor position are refreshed automatically.
"""

from typing import Final, Optional, Any

import pygame as pg

from src.classes.text_label import TextLabel

from src.utils import RectPos, ObjInfo, Mouse, Keyboard, resize_obj
from src.type_utils import XY, WH, LayeredBlitInfo
from src.consts import MOUSE_LEFT, CHR_LIMIT, WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER

INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((60, 40))


class NumInputBox:
    """Class to choose a number in range with an input box."""

    __slots__ = (
        "_init_pos", "_img", "rect", "_init_w", "_init_h", "min_limit", "max_limit",
        "_is_selected", "_cursor_i", "layer", "_cursor_layer", "cursor_type", "text_label",
        "_cursor_img", "cursor_rect", "objs_info"
    )

    def __init__(
            self, pos: RectPos, min_limit: int, max_limit: int, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the input box and text.

        Args:
            position, minimum limit, maximum limit, base layer (default = BG_LAYER)
        """

        self.layer: int
        self._cursor_layer: int

        self._init_w: int
        self._init_h: int

        self._init_pos: RectPos = pos

        self._img: pg.Surface = INPUT_BOX_IMG
        self.rect: pg.Rect = pg.Rect(0, 0, *self._img.get_size())
        setattr(self.rect, self._init_pos.coord_type, (self._init_pos.x, self._init_pos.y))

        self._init_w, self._init_h = self.rect.size

        self.min_limit: int = min_limit
        self.max_limit: int = max_limit

        self._is_selected: bool = False
        self._cursor_i: int = 0

        self.layer, self._cursor_layer = base_layer + ELEMENT_LAYER, base_layer + TOP_LAYER
        self.cursor_type: int = pg.SYSTEM_CURSOR_IBEAM

        self.text_label = TextLabel(
            RectPos(self.rect.centerx, self.rect.centery, "center"),
            "", base_layer
        )

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_rect: pg.Rect = pg.Rect(
            self.text_label.rect.topleft, self._cursor_img.get_size()
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(self.text_label)]

    @property
    def blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: list[LayeredBlitInfo] = [(self._img, self.rect, self.layer)]
        if self._is_selected:
            sequence.append((self._cursor_img, self.cursor_rect, self._cursor_layer))

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

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._is_selected = False

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY
        wh: WH

        xy, wh = resize_obj(self._init_pos, self._init_w, self._init_h, win_w_ratio, win_h_ratio)
        self._img = pg.transform.scale(self._img, wh)
        self.rect.size = wh
        setattr(self.rect, self._init_pos.coord_type, xy)

        self._cursor_img = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_rect.topleft = (
            self.text_label.get_x_at(self._cursor_i), self.text_label.rect.y
        )

    def bounded_set_cursor_i(self, i: Optional[int]) -> None:
        """
        Sets the cursor index making sure it doesn't exceed the text length.

        Args:
            index (normal index if None)
        """

        if i is not None:
            self._cursor_i = i
        self._cursor_i = min(self._cursor_i, len(self.text_label.text))
        self.cursor_rect.x = self.text_label.get_x_at(self._cursor_i)

    def _move_with_keys(self, keyboard: Keyboard) -> None:
        """
        Moves the cursor index with keys.

        Args:
            keyboard
        """

        if pg.K_LEFT in keyboard.timed:
            self._cursor_i = 0 if keyboard.is_ctrl_on else max(self._cursor_i - 1, 0)
        if pg.K_RIGHT in keyboard.timed:
            text_len: int = len(self.text_label.text)
            self._cursor_i = text_len if keyboard.is_ctrl_on else min(self._cursor_i + 1, text_len)
        if pg.K_HOME in keyboard.timed:
            self._cursor_i = 0
        if pg.K_END in keyboard.timed:
            self._cursor_i = len(self.text_label.text)

    def _handle_deletion(self, k: int) -> None:
        """
        Handles backspace and delete.

        Args:
            key
        """

        first_part: str
        second_part: str

        if k == pg.K_DELETE:
            first_part = self.text_label.text[:self._cursor_i]
            second_part = self.text_label.text[self._cursor_i + 1:]
            self.text_label.text = first_part + second_part
        elif k == pg.K_BACKSPACE and self._cursor_i != 0:
            first_part = self.text_label.text[:self._cursor_i - 1]
            second_part = self.text_label.text[self._cursor_i:]
            self.text_label.text = first_part + second_part
            self._cursor_i -= 1

        if self.text_label.text.startswith("0"):  # If it's empty keep it empty
            self.text_label.text = self.text_label.text.lstrip("0") or str(self.min_limit)

    def _insert_char(self, char: str) -> None:
        """
        Inserts a character at the cursor position.

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

        should_change_cursor_i: bool = True  # Better UX on edge cases
        if int(self.text_label.text) < self.min_limit:
            self.text_label.text = str(self.min_limit)
        elif int(self.text_label.text) > self.max_limit:
            self.text_label.text = str(self.max_limit)
            should_change_cursor_i = prev_text != str(self.max_limit)

        if should_change_cursor_i:
            self._cursor_i = min(self._cursor_i + 1, len(self.text_label.text))

    def _handle_k(self, k: int) -> None:
        """
        Handles input.

        Args:
            key
        """

        if k == pg.K_BACKSPACE or k == pg.K_DELETE:
            self._handle_deletion(k)
        elif k <= CHR_LIMIT:
            char: str = chr(k)
            is_trailing_zero: bool = (
                self._cursor_i == 0 and char == "0" and self.text_label.text != ""
            )
            if char.isdigit() and not is_trailing_zero:
                self._insert_char(char)

    def upt(self, mouse: Mouse, keyboard: Keyboard, selected_obj: Any, prev_text: str) -> bool:
        """
        Allows typing numbers, moving the cursor and deleting a specific character.

        Args:
            mouse, keyboard, minimum limit, maximum limit, selected obj, previous text
        Returns:
            clicked flag, text
        """

        prev_cursor_i: int = self._cursor_i

        is_clicked: bool = mouse.hovered_obj == self and mouse.released[MOUSE_LEFT]
        if is_clicked:
            self._cursor_i = self.text_label.get_closest_to(mouse.x)
            selected_obj = self

        self._is_selected = selected_obj == self
        if self._is_selected and keyboard.timed != []:
            self._move_with_keys(keyboard)
            self._handle_k(keyboard.timed[-1])

        if self.text_label.text != prev_text:
            self.text_label.set_text(self.text_label.text)
            self.cursor_rect.x = self.text_label.get_x_at(self._cursor_i)

        if self._cursor_i != prev_cursor_i:
            self.cursor_rect.x = self.text_label.get_x_at(self._cursor_i)

        return is_clicked
