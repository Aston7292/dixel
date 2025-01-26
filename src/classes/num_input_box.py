"""Class to choose a number in range with an input box."""

from typing import Final, Optional

import pygame as pg

from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio, ObjInfo, Mouse, Keyboard, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import MOUSE_LEFT, CHR_LIMIT, WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER

INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((60, 40))


class NumInputBox:
    """Class to choose a number in range with an input box."""

    __slots__ = (
        "_init_pos", "_init_img", "_img", "rect", "_is_selected", "_layer", "_cursor_layer",
        "cursor_type", "text_label", "_cursor_i", "_cursor_img", "cursor_rect", "objs_info"
    )

    def __init__(self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the input box and text.

        Args:
            position, image, base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos
        self._init_img: pg.Surface = INPUT_BOX_IMG

        self._img: pg.Surface = self._init_img
        self.rect: pg.Rect = self._img.get_rect(**{pos.coord_type: pos.xy})

        self._is_selected: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._cursor_layer: int = base_layer + TOP_LAYER
        self.cursor_type: int = pg.SYSTEM_CURSOR_IBEAM

        self.text_label = TextLabel(RectPos(*self.rect.center, "center"), "", base_layer)
        self._cursor_i: int

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self.cursor_rect: pg.Rect = self._cursor_img.get_rect(topleft=(0, 0))

        self.objs_info: list[ObjInfo] = [ObjInfo(self.text_label)]

    def get_blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: list[LayeredBlitInfo] = [(self._img, self.rect.topleft, self._layer)]
        if self._is_selected:
            sequence.append((self._cursor_img, self.cursor_rect.topleft, self._cursor_layer))

        return sequence

    def get_hovering_info(self, mouse_xy: PosPair) -> tuple[bool, int]:
        """
        Gets the hovering info.

        Args:
            mouse xy
        Returns:
            hovered flag, hovered object layer
        """

        return self.rect.collidepoint(mouse_xy), self._layer

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self._is_selected = False
        self._cursor_i = 0

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        box_xy: PosPair
        box_wh: SizePair
        box_xy, box_wh = resize_obj(self._init_pos, *self._init_img.get_size(), win_ratio)

        self._img = pg.transform.scale(self._init_img, box_wh)
        self.rect = self._img.get_rect(**{self._init_pos.coord_type: box_xy})

        self._cursor_img = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)

        self.cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)
        self.cursor_rect.y = self.text_label.rect.y

    def bounded_set_cursor_i(self, i: Optional[int]) -> None:
        """
        Sets the cursor index making sure it doesn't exceed the text length.

        Args:
            index (normal cursor index if None)
        """

        if i is not None:
            self._cursor_i = i
        self._cursor_i = min(self._cursor_i, len(self.text_label.text))
        self.cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)

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

        copy_text: str = self.text_label.text

        if k == pg.K_DELETE:
            copy_text = copy_text[:self._cursor_i] + copy_text[self._cursor_i + 1:]
        elif k == pg.K_BACKSPACE and self._cursor_i:
            copy_text = copy_text[:self._cursor_i - 1] + copy_text[self._cursor_i:]
            self._cursor_i -= 1

        if copy_text.startswith("0"):  # If empty keep it empty
            copy_text = copy_text.lstrip("0") or str(min_limit)

        return copy_text

    def _insert_char(self, char: str, min_limit: int, max_limit: int) -> str:
        """
        Inserts a character at the cursor position.

        Args:
            character, minimum limit, maximum limit
        Returns:
            text
        """

        copy_text: str = self.text_label.text

        copy_text = copy_text[:self._cursor_i] + char + copy_text[self._cursor_i:]
        max_len: int = len(str(max_limit))
        copy_text = copy_text[:max_len]

        should_change_cursor_i: bool = True  # Better UX on edge cases
        if int(copy_text) < min_limit:
            copy_text = str(min_limit)
        elif int(copy_text) > max_limit:
            copy_text = str(max_limit)
            should_change_cursor_i = copy_text != self.text_label.text

        if copy_text.startswith("0"):  # If empty keep it empty
            copy_text = copy_text.lstrip("0") or str(min_limit)

        if should_change_cursor_i:
            self._cursor_i = min(self._cursor_i + 1, len(copy_text))

        return copy_text

    def _handle_k(self, k: int, min_limit: int, max_limit: int) -> str:
        """
        Handles input.

        Args:
            key, minimum limit, maximum limit
        Returns:
            text
        """

        copy_text: str = self.text_label.text

        if k == pg.K_BACKSPACE or k == pg.K_DELETE:
            copy_text = self._handle_deletion(k, min_limit)
        elif k <= CHR_LIMIT:
            char: str = chr(k)
            is_trailing_zero: bool = (char == "0" and not self._cursor_i) and bool(copy_text)
            if char.isdigit() and not is_trailing_zero:
                copy_text = self._insert_char(char, min_limit, max_limit)

        return copy_text

    def upt(
            self, mouse: Mouse, keyboard: Keyboard, limits: tuple[int, int], is_selected: bool
    ) -> tuple[bool, str]:
        """
        Allows typing numbers, moving the cursor and deleting a specific character.

        Args:
            mouse, keyboard, limits, selected flag
        Returns:
            clicked flag, text
        """

        # The text label isn't updated here because it's also changed by other classes

        self._is_selected = is_selected
        copy_text: str = self.text_label.text
        if self._is_selected and keyboard.timed:
            self._move_with_keys(keyboard)
            copy_text = self._handle_k(keyboard.timed[-1], *limits)
            self.cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)

        is_clicked: bool = mouse.hovered_obj == self and mouse.released[MOUSE_LEFT]
        if is_clicked:
            self._cursor_i = self.text_label.get_closest_to(mouse.x)
            self.cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)

        return is_clicked, copy_text
