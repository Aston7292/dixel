"""Class to choose a number in range with an input box."""

from typing import Final, Optional, Any

import pygame as pg

from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio, ObjInfo, MouseInfo, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import MOUSE_LEFT, CHR_LIMIT, WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER

INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((60, 40))


class NumInputBox:
    """Class to choose a number in range with an input box."""

    __slots__ = (
        "_init_pos", "_init_img", "_img", "rect", "is_hovering", "_is_selected", "_layer",
        "_hovering_layer", "text_label", "_cursor_i", "_cursor_img", "_cursor_rect", "objs_info"
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
        self.rect: pg.Rect = self._img.get_rect(**{pos.coord_type: (pos.x, pos.y)})

        self.is_hovering: bool = False
        self._is_selected: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._hovering_layer: int = base_layer + TOP_LAYER

        self.text_label = TextLabel(RectPos(*self.rect.center, "center"), "", base_layer)
        self._cursor_i: int

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self._cursor_rect: pg.Rect = self._cursor_img.get_rect(
            topleft=self.text_label.rect.topleft
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(self.text_label)]

    def blit(self) -> list[LayeredBlitInfo]:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: list[LayeredBlitInfo] = [(self._img, self.rect.topleft, self._layer)]
        if self._is_selected:
            sequence.append((self._cursor_img, self._cursor_rect.topleft, self._hovering_layer))

        return sequence

    def get_hovering_info(self, mouse_xy: PosPair) -> tuple[bool, int]:
        """
        Gets the hovering info.

        Args:
            mouse position
        Returns:
            True if the object is being hovered else False, hovered object layer
        """

        return self.rect.collidepoint(mouse_xy), self._layer

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self.is_hovering = self._is_selected = False
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

    def post_resize(self) -> None:
        """Gets the cursor position after the text label was resized."""

        self._cursor_img = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)

        self._cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)
        self._cursor_rect.y = self.text_label.rect.y

    def bounded_set_cursor_i(self, cursor_i: Optional[int] = None) -> None:
        """
        Sets the cursor index making sure it doesn't exceed the text length.

        Args:
            cursor index (normal cursor index if None) (default = None)
        """

        if cursor_i is not None:
            self._cursor_i = cursor_i
        self._cursor_i = min(self._cursor_i, len(self.text_label.text))
        self._cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)

    def _move_cursor_with_keys(self, keys: list[int]) -> None:
        """
        Moves the cursor index with keys.

        Args:
            keys
        """

        if pg.K_LEFT in keys:
            self._cursor_i = 0 if pg.key.get_mods() & pg.KMOD_CTRL else max(self._cursor_i - 1, 0)
        if pg.K_RIGHT in keys:
            text_len: int = len(self.text_label.text)
            self._cursor_i = (
                text_len if pg.key.get_mods() & pg.KMOD_CTRL else min(self._cursor_i + 1, text_len)
            )
        if pg.K_HOME in keys:
            self._cursor_i = 0
        if pg.K_END in keys:
            self._cursor_i = len(self.text_label.text)

    def _handle_deletion(self, k: int, min_limit: int) -> str:
        """
        Handles backspace and delete.

        Args:
            key, minimum limit
        Returns:
            text
        """

        temp_text: str = self.text_label.text

        if k == pg.K_DELETE:
            temp_text = temp_text[:self._cursor_i] + temp_text[self._cursor_i + 1:]
        elif k == pg.K_BACKSPACE and self._cursor_i:
            temp_text = temp_text[:self._cursor_i - 1] + temp_text[self._cursor_i:]
            self._cursor_i -= 1

        if temp_text.startswith("0"):  # If empty keep it empty
            temp_text = temp_text.lstrip("0") or str(min_limit)

        return temp_text

    def _insert_char(self, char: str, min_limit: int, max_limit: int) -> str:
        """
        Inserts a character at the cursor position.

        Args:
            character, minimum limit, maximum limit
        Returns:
            text
        """

        temp_text: str = self.text_label.text

        temp_text = temp_text[:self._cursor_i] + char + temp_text[self._cursor_i:]
        max_len: int = len(str(max_limit))
        temp_text = temp_text[:max_len]

        should_change_cursor_i: bool = True  # Better UX on edge cases
        if int(temp_text) < min_limit:
            temp_text = str(min_limit)
        elif int(temp_text) > max_limit:
            temp_text = str(max_limit)
            should_change_cursor_i = self.text_label.text != temp_text

        if temp_text.startswith("0"):  # If empty keep it empty
            temp_text = temp_text.lstrip("0") or str(min_limit)

        if should_change_cursor_i:
            self._cursor_i = min(self._cursor_i + 1, len(temp_text))

        return temp_text

    def _handle_k(self, k: int, min_limit: int, max_limit: int) -> str:
        """
        Handles input.

        Args:
            key, minimum limit, maximum limit
        Returns:
            text
        """

        temp_text: str = self.text_label.text

        if k == pg.K_BACKSPACE or k == pg.K_DELETE:
            temp_text = self._handle_deletion(k, min_limit)
        elif k <= CHR_LIMIT:
            char: str = chr(k)
            is_inserting_trailing_zero: bool = bool(
                (char == "0" and not self._cursor_i) and temp_text
            )
            if char.isdigit() and not is_inserting_trailing_zero:
                temp_text = self._insert_char(char, min_limit, max_limit)

        return temp_text

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int],
            limits: tuple[int, int], is_selected: bool
    ) -> tuple[bool, str]:
        """
        Allows typing numbers, moving the cursor and deleting a specific character.

        Args:
            hovered object (can be None), mouse info, keys, limits, selected flag
        Returns:
            True if input box was clicked else False, text
        """

        # The text label isn't updated here because it's also changed by other classes

        if self != hovered_obj:
            if self.is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.is_hovering = False
        elif not self.is_hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_IBEAM)
            self.is_hovering = True

        self._is_selected = is_selected
        temp_text: str = self.text_label.text
        if self._is_selected and keys:
            self._move_cursor_with_keys(keys)
            temp_text = self._handle_k(keys[-1], *limits)
            self._cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)

        is_clicked: bool = mouse_info.released[MOUSE_LEFT] and self.is_hovering
        if is_clicked:
            self._cursor_i = self.text_label.get_closest_to(mouse_info.x)
            self._cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)

        return is_clicked, temp_text
