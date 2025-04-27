"""Class to choose a number in range with an input box."""

from typing import Final, Optional, Any

import pygame as pg
from pygame.locals import *

from src.classes.text_label import TextLabel

from src.utils import RectPos, ObjInfo, Mouse, Keyboard, resize_obj
from src.type_utils import XY, WH, LayeredBlitInfo
from src.consts import MOUSE_LEFT, CHR_LIMIT, WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER

INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((64, 40)).convert()


class NumInputBox:
    """Class to choose a number in range with an input box."""

    __slots__ = (
        "_init_pos", "_img", "rect", "_init_w", "_init_h", "min_limit", "max_limit",
        "_is_selected", "cursor_i", "layer", "_cursor_layer", "cursor_type", "text_label",
        "_prev_text", "_prev_cursor_i", "_cursor_img", "cursor_rect", "objs_info"
    )

    def __init__(
            self, pos: RectPos, min_limit: int, max_limit: int, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the input box and text.

        Args:
            position, minimum limit, maximum limit, base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos

        self._img: pg.Surface = INPUT_BOX_IMG
        self.rect: pg.Rect = pg.Rect(0, 0, *self._img.get_size())
        setattr(self.rect, self._init_pos.coord_type, (self._init_pos.x, self._init_pos.y))

        self._init_w: int = self.rect.w
        self._init_h: int = self.rect.h

        self.min_limit: int = min_limit
        self.max_limit: int = max_limit

        self._is_selected: bool = False
        self.cursor_i: int = 0

        self.layer: int = base_layer + ELEMENT_LAYER
        self._cursor_layer: int = base_layer + TOP_LAYER
        self.cursor_type: int = SYSTEM_CURSOR_IBEAM

        self.text_label = TextLabel(
            RectPos(self.rect.centerx, self.rect.centery, "center"),
            "", base_layer
        )

        self._prev_text: str = self.text_label.text
        self._prev_cursor_i: int = self.cursor_i

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h)).convert()
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
        self._img = pg.transform.scale(self._img, wh).convert()
        self.rect.size = wh
        setattr(self.rect, self._init_pos.coord_type, xy)

        self._cursor_img = pg.Surface((1, self.text_label.rect.h)).convert()
        self._cursor_img.fill(WHITE)
        self.cursor_rect.topleft = (
            self.text_label.get_x_at(self.cursor_i), self.text_label.rect.y
        )

    def _move_with_keys(self, keyboard: Keyboard) -> None:
        """
        Moves the cursor index with keys.

        Args:
            keyboard
        """

        if K_LEFT in keyboard.timed:
            self.cursor_i = 0 if keyboard.is_ctrl_on else max(self.cursor_i - 1, 0)
        if K_RIGHT in keyboard.timed:
            text_len: int = len(self.text_label.text)
            self.cursor_i = text_len if keyboard.is_ctrl_on else min(self.cursor_i + 1, text_len)
        if K_HOME in keyboard.timed:
            self.cursor_i = 0
        if K_END in keyboard.timed:
            self.cursor_i = len(self.text_label.text)

    def _handle_deletion(self, k: int) -> None:
        """
        Handles backspace and delete.

        Args:
            key
        """

        first_part: str
        second_part: str

        if k == K_DELETE:
            first_part = self.text_label.text[:self.cursor_i]
            second_part = self.text_label.text[self.cursor_i + 1:]
            self.text_label.text = first_part + second_part
        elif k == K_BACKSPACE:
            first_part = self.text_label.text[:self.cursor_i - 1]
            second_part = self.text_label.text[self.cursor_i:]
            self.text_label.text = first_part + second_part
            self.cursor_i = max(self.cursor_i - 1, 0)

        if self.text_label.text.startswith("0"):  # If it's empty keep it empty
            self.text_label.text = self.text_label.text.lstrip("0") or str(self.min_limit)

    def _insert_char(self, char: str) -> None:
        """
        Inserts a character at the cursor position.

        Args:
            character
        """

        prev_text: str = self.text_label.text

        first_half: str = self.text_label.text[:self.cursor_i]
        second_half: str = self.text_label.text[self.cursor_i:]
        self.text_label.text = first_half + char + second_half
        self.text_label.text = self.text_label.text.lstrip("0") or str(self.min_limit)

        max_len: int = len(str(self.max_limit))
        self.text_label.text = self.text_label.text[:max_len]

        if int(self.text_label.text) < self.min_limit:
            self.text_label.text = str(self.min_limit)
        elif int(self.text_label.text) > self.max_limit:
            self.text_label.text = str(self.max_limit)

        if self.text_label.text != prev_text:
            self.cursor_i = min(self.cursor_i + 1, len(self.text_label.text))

    def _handle_k(self, k: int) -> None:
        """
        Handles input.

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
        """Refreshes text label and mouse position."""

        if self.text_label.text != self._prev_text:
            self.text_label.set_text(self.text_label.text)
            self.cursor_rect.x = self.text_label.get_x_at(self.cursor_i)
        elif self.cursor_i != self._prev_cursor_i:
            self.cursor_rect.x = self.text_label.get_x_at(self.cursor_i)

        self._prev_text = self.text_label.text
        self._prev_cursor_i = self.cursor_i

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
            self.cursor_i = self.text_label.get_closest_to(mouse.x)
            selected_obj = self

        self._is_selected = selected_obj == self
        if self._is_selected and keyboard.timed != []:
            self._move_with_keys(keyboard)
            self._handle_k(keyboard.timed[-1])

        return is_clicked
