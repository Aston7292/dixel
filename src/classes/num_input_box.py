"""
Class to choose a number in range with an input box.

Cursor position is refreshed automatically.
"""

from typing import Final, Optional

import pygame as pg

from src.classes.text_label import TextLabel

from src.utils import RectPos, ObjInfo, Mouse, Keyboard, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import MOUSE_LEFT, CHR_LIMIT, WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER

INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((60, 40))


class NumInputBox:
    """Class to choose a number in range with an input box."""

    __slots__ = (
        "_init_pos", "_img", "rect", "_init_w", "_init_h", "_is_selected", "_cursor_i", "layer",
        "_cursor_layer", "cursor_type", "text_label", "_cursor_img", "cursor_x", "objs_info"
    )

    def __init__(self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the input box and text.

        Args:
            position, image, base layer (default = BG_LAYER)
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

        self._is_selected: bool = False
        self._cursor_i: int

        self.layer, self._cursor_layer = base_layer + ELEMENT_LAYER, base_layer + TOP_LAYER
        self.cursor_type: int = pg.SYSTEM_CURSOR_IBEAM

        self.text_label = TextLabel(RectPos(*self.rect.center, "center"), "", base_layer)

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_x: int = 0

        self.objs_info: list[ObjInfo] = [ObjInfo(self.text_label)]

    @property
    def blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: list[LayeredBlitInfo] = [(self._img, self.rect.topleft, self.layer)]
        if self._is_selected:
            cursor_y: int = self.text_label.rect.y
            sequence.append((self._cursor_img, (self.cursor_x, cursor_y), self._cursor_layer))

        return sequence

    def get_hovering(self, mouse_xy: PosPair) -> bool:
        """
        Gets the hovering flag.

        Args:
            mouse xy
        Returns:
            hovering flag
        """

        return self.rect.collidepoint(mouse_xy)

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self._is_selected = False
        self._cursor_i = 0
        self.cursor_x = self.text_label.get_x_at(self._cursor_i)

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: PosPair
        wh: SizePair

        xy, wh = resize_obj(self._init_pos, self._init_w, self._init_h, win_w_ratio, win_h_ratio)
        self._img = pg.transform.scale(self._img, wh)
        self.rect.size = wh
        setattr(self.rect, self._init_pos.coord_type, xy)

        self._cursor_img = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_x = self.text_label.get_x_at(self._cursor_i)

    def bounded_set_cursor_i(self, i: Optional[int]) -> None:
        """
        Sets the cursor index making sure it doesn't exceed the text length.

        Args:
            index (normal cursor index if None)
        """

        if i is not None:
            self._cursor_i = i
        self._cursor_i = min(self._cursor_i, len(self.text_label.text))
        self.cursor_x = self.text_label.get_x_at(self._cursor_i)

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

    def _handle_deletion(self, k: int, min_limit: int) -> str:
        """
        Handles backspace and delete.

        Args:
            key, minimum limit
        Returns:
            text
        """

        new_text: str = self.text_label.text

        if k == pg.K_DELETE:
            new_text = new_text[:self._cursor_i] + new_text[self._cursor_i + 1:]
        elif k == pg.K_BACKSPACE and self._cursor_i:
            new_text = new_text[:self._cursor_i - 1] + new_text[self._cursor_i:]
            self._cursor_i -= 1

        if new_text.startswith("0"):  # If empty keep it empty
            new_text = new_text.lstrip("0") or str(min_limit)

        return new_text

    def _insert_char(self, char: str, min_limit: int, max_limit: int) -> str:
        """
        Inserts a character at the cursor position.

        Args:
            character, minimum limit, maximum limit
        Returns:
            text
        """

        new_text: str = self.text_label.text

        new_text = new_text[:self._cursor_i] + char + new_text[self._cursor_i:]
        max_len: int = len(str(max_limit))
        new_text = new_text[:max_len]

        should_change_cursor_i: bool = True  # Better UX on edge cases
        if int(new_text) < min_limit:
            new_text = str(min_limit)
        elif int(new_text) > max_limit:
            new_text = str(max_limit)
            should_change_cursor_i = new_text != self.text_label.text

        if should_change_cursor_i:
            self._cursor_i = min(self._cursor_i + 1, len(new_text))

        return new_text

    def _handle_k(self, k: int, min_limit: int, max_limit: int) -> str:
        """
        Handles input.

        Args:
            key, minimum limit, maximum limit
        Returns:
            text
        """

        new_text: str = self.text_label.text

        if k == pg.K_BACKSPACE or k == pg.K_DELETE:
            new_text = self._handle_deletion(k, min_limit)
        elif k <= CHR_LIMIT:
            char: str = chr(k)
            is_trailing_zero: bool = (char == "0" and not self._cursor_i) and bool(new_text)
            if char.isdigit() and not is_trailing_zero:
                new_text = self._insert_char(char, min_limit, max_limit)

        return new_text

    def upt(
            self, mouse: Mouse, keyboard: Keyboard, min_limit: int, max_limit: int,
            is_selected: bool
    ) -> tuple[bool, str]:
        """
        Allows typing numbers, moving the cursor and deleting a specific character.

        Args:
            mouse, keyboard, minimum limit, maximum limit, selected flag
        Returns:
            clicked flag, text
        """

        # The text label isn't updated here because it's also changed by other classes

        prev_cursor_i: int = self._cursor_i

        self._is_selected = is_selected
        new_text: str = self.text_label.text
        if self._is_selected and keyboard.timed:
            self._move_with_keys(keyboard)
            new_text = self._handle_k(keyboard.timed[-1], min_limit, max_limit)

        is_clicked: bool = mouse.hovered_obj == self and mouse.released[MOUSE_LEFT]
        if is_clicked:
            self._cursor_i = self.text_label.get_closest_to(mouse.x)

        if self._cursor_i != prev_cursor_i:
            self.cursor_x = self.text_label.get_x_at(self._cursor_i)

        return is_clicked, new_text
