"""
Class to choose a number in range with an input box
"""

import pygame as pg
from typing import Final, Optional, Any

from src.classes.text_label import TextLabel

from src.utils import RectPos, Size, ObjInfo, MouseInfo, resize_obj
from src.type_utils import LayeredBlitSequence
from src.consts import WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER


CHR_LIMIT: Final[int] = 1_114_111


class NumInputBox:
    """
    Class to choose a number in range with an input box
    """

    __slots__ = (
        '_box_init_pos', '_box_init_img', '_box_img', 'box_rect', 'is_hovering', '_is_selected',
        '_layer', '_hovering_layer', 'text_label', '_cursor_i', '_cursor_img', '_cursor_rect',
        '_cursor_init_size', 'objs_info'
    )

    def __init__(
            self, pos: RectPos, img: pg.Surface, text: str, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the input box and text
        Args:
            position, image, text, base layer (default = BG_LAYER)
        """

        self._box_init_pos: RectPos = pos
        self._box_init_img: pg.Surface = img

        self._box_img: pg.Surface = self._box_init_img
        self.box_rect: pg.Rect = self._box_img.get_rect(**{pos.coord_type: pos.xy})

        self.is_hovering: bool = False
        self._is_selected: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._hovering_layer: int = base_layer + TOP_LAYER

        self.text_label = TextLabel(RectPos(*self.box_rect.center, 'center'), text, base_layer)
        self._cursor_i: int = 0

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self._cursor_rect: pg.Rect = self._cursor_img.get_rect(
            topleft=(self.text_label.get_pos_at(self._cursor_i), self.text_label.rect.y)
        )

        self._cursor_init_size: Size = Size(*self._cursor_rect.size)

        self.objs_info: list[ObjInfo] = [ObjInfo("text", self.text_label)]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._box_img, self.box_rect.topleft, self._layer)]
        if self._is_selected:
            sequence.append((self._cursor_img, self._cursor_rect.topleft, self._hovering_layer))

        return sequence

    def check_hovering(self, mouse_pos: tuple[int, int]) -> tuple[Optional["NumInputBox"], int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object's layer
        """

        return self if self.box_rect.collidepoint(mouse_pos) else None, self._layer

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self.is_hovering = self._is_selected = False
        self._cursor_i = 0

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
        Args:
            window width ratio, window height ratio
        """

        box_pos: tuple[int, int]
        box_size: tuple[int, int]
        box_pos, box_size = resize_obj(
            self._box_init_pos, *self._box_init_img.get_size(), win_ratio_w, win_ratio_h
        )

        self._box_img = pg.transform.scale(self._box_init_img, box_size)
        self.box_rect = self._box_img.get_rect(**{self._box_init_pos.coord_type: box_pos})

        cursor_size: tuple[int, int] = (
            round(self._cursor_init_size.w * win_ratio_w),
            round(self._cursor_init_size.h * win_ratio_h)
        )

        self._cursor_img = pg.transform.scale(self._cursor_img, cursor_size)

    def post_resize(self) -> None:
        """
        Handles post resizing behavior
        """

        self.get_cursor_pos()

    def get_cursor_pos(self) -> None:
        """
        Gets the cursor position based on the cursor index
        """

        self._cursor_rect.x = self.text_label.get_pos_at(self._cursor_i)
        self._cursor_rect.y = self.text_label.rect.y

    def set_text(self, text: str, cursor_i: Optional[int]) -> None:
        """
        Sets the text and adjusts the cursor index
        Args:
            text, cursor index (doesn't change if None)
        """

        self.text_label.set_text(text)
        if cursor_i is not None:
            self._cursor_i = cursor_i
        self._cursor_i = min(self._cursor_i, len(self.text_label.text))

        self.get_cursor_pos()

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...],
            limits: tuple[int, int], is_selected: bool
    ) -> tuple[bool, str]:
        """
        Allows typing numbers, moving the cursor and deleting a specific character
        Args:
            hovered object (can be None), mouse info, keys, limits, selected boolean
        Returns:
            True if input box was clicked else False, text
        """

        '''
        The text object isn't updated here because it can be also changed by other classes
        that use the input box
        '''

        new_text: str = self.text_label.text

        if self != hovered_obj:
            if self.is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.is_hovering = False
        else:
            if not self.is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_IBEAM)
                self.is_hovering = True

            if mouse_info.released[0]:
                self._cursor_i = self.text_label.get_closest_to(mouse_info.x)
                self.get_cursor_pos()

                return True, new_text

        self._is_selected = is_selected
        if self._is_selected and keys:
            prev_cursor_i: int = self._cursor_i
            if pg.K_LEFT in keys:
                self._cursor_i = max(self._cursor_i - 1, 0)
            if pg.K_RIGHT in keys:
                self._cursor_i = min(self._cursor_i + 1, len(new_text))
            if pg.K_HOME in keys:
                self._cursor_i = 0
            if pg.K_END in keys:
                self._cursor_i = len(new_text)

            if self._cursor_i == prev_cursor_i:
                k: int = keys[-1]
                if k in (pg.K_BACKSPACE, pg.K_DELETE):
                    if k == pg.K_BACKSPACE:
                        if self._cursor_i:
                            new_text = new_text[:self._cursor_i - 1] + new_text[self._cursor_i:]
                            self._cursor_i -= 1
                    else:
                        new_text = new_text[:self._cursor_i] + new_text[self._cursor_i + 1:]

                    if new_text.startswith('0'):
                        new_text = new_text.lstrip('0')
                        if not new_text or int(new_text) < limits[0]:
                            new_text = str(limits[0])
                elif k <= CHR_LIMIT:
                    char: str = chr(k)
                    if char.isdigit():
                        change_cursor_i: bool  # Better user experience on edge cases
                        inserted_useless_zero: bool = bool(
                            (char == '0' and not self._cursor_i) and new_text
                        )
                        if inserted_useless_zero:
                            change_cursor_i = False
                        else:
                            new_text = new_text[:self._cursor_i] + char + new_text[self._cursor_i:]
                            change_cursor_i = True

                            max_length: int = len(str(limits[1]))
                            if len(new_text) > max_length:
                                new_text = new_text[:max_length]

                            if int(new_text) < limits[0]:
                                new_text = str(limits[0])
                            elif int(new_text) > limits[1]:
                                new_text = str(limits[1])
                                change_cursor_i = self.text_label.text != str(limits[1])

                            if new_text.startswith('0'):
                                new_text = new_text.lstrip('0')
                                if not new_text or int(new_text) < limits[0]:
                                    new_text = str(limits[0])

                        if change_cursor_i:
                            self._cursor_i = min(self._cursor_i + 1, len(new_text))
            self.get_cursor_pos()

        return False, new_text
