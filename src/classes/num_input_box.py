"""
Class to choose a number in range with an input box
"""

import pygame as pg
from typing import Final, Optional, Any

from src.classes.text_label import TextLabel

from src.utils import RectPos, ObjInfo, MouseInfo, resize_obj
from src.type_utils import LayeredBlitSequence
from src.consts import WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER


INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((60, 40))

CHR_LIMIT: Final[int] = 1_114_111


class NumInputBox:
    """
    Class to choose a number in range with an input box
    """

    __slots__ = (
        '_init_pos', '_init_img', '_img', 'rect', 'is_hovering', '_is_selected',
        '_layer', '_hovering_layer', 'text_label', '_cursor_i', '_cursor_img', '_cursor_rect',
        'objs_info'
    )

    def __init__(self, pos: RectPos, text: str, base_layer: int = BG_LAYER) -> None:
        """
        Creates the input box and text
        Args:
            position, image, text, base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos
        self._init_img: pg.Surface = INPUT_BOX_IMG

        self._img: pg.Surface = self._init_img
        self.rect: pg.Rect = self._img.get_rect(**{pos.coord_type: pos.xy})

        self.is_hovering: bool = False
        self._is_selected: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._hovering_layer: int = base_layer + TOP_LAYER

        self.text_label = TextLabel(RectPos(*self.rect.center, 'center'), text, base_layer)
        self._cursor_i: int = 0

        self._cursor_img: pg.Surface = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
        self._cursor_rect: pg.Rect = self._cursor_img.get_rect(
            topleft=(self.text_label.get_pos_at(self._cursor_i), self.text_label.rect.y)
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(self.text_label)]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._img, self.rect.topleft, self._layer)]
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

        return self if self.rect.collidepoint(mouse_pos) else None, self._layer

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self.is_hovering = self._is_selected = False
        self._cursor_i = 0

    def handle_resize(self, win_ratio: tuple[float, float]) -> None:
        """
        Resizes the object
        Args:
            window size ratio
        """

        box_pos: tuple[int, int]
        box_size: tuple[int, int]
        box_pos, box_size = resize_obj(self._init_pos, *self._init_img.get_size(), *win_ratio)

        self._img = pg.transform.scale(self._init_img, box_size)
        self.rect = self._img.get_rect(**{self._init_pos.coord_type: box_pos})

    def post_resize(self) -> None:
        """
        Handles post resizing behavior
        """

        self._cursor_img = pg.Surface((1, self.text_label.rect.h))
        self._cursor_img.fill(WHITE)
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
                        inserted_trailing_zero: bool = bool(
                            (char == '0' and not self._cursor_i) and new_text
                        )

                        # Better user experience on edge cases
                        change_cursor_i: bool = not inserted_trailing_zero
                        if not inserted_trailing_zero:
                            new_text = new_text[:self._cursor_i] + char + new_text[self._cursor_i:]
                            change_cursor_i = True

                            max_length: int = len(str(limits[1]))
                            if len(new_text) > max_length:
                                new_text = new_text[:max_length]

                            if int(new_text) < limits[0]:
                                new_text = str(limits[0])
                            elif int(new_text) > limits[1]:
                                new_text = str(limits[1])
                                change_cursor_i = self.text_label.text != new_text

                            if new_text.startswith('0'):
                                new_text = new_text.lstrip('0')
                                if not new_text or int(new_text) < limits[0]:
                                    new_text = str(limits[0])

                        if change_cursor_i:
                            self._cursor_i = min(self._cursor_i + 1, len(new_text))
            self.get_cursor_pos()

        return False, new_text
