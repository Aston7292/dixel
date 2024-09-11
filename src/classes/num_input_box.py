"""
Class to choose a number in range with an input box
"""

import pygame as pg
from typing import Any

from src.classes.text import Text
from src.utils import MouseInfo, RectPos, Size
from src.type_utils import ObjsInfo, LayeredBlitSequence, LayerSequence
from src.consts import WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER


class NumInputBox:
    """
    Class to choose a number in range with an input box
    """

    __slots__ = (
        '_box_init_pos', '_box_img', 'box_rect', '_box_init_size', 'hovering', '_selected',
        '_layer', '_hoovering_layer', 'text', '_text_i', '_cursor_img', '_cursor_rect',
        '_cursor_init_size', 'sub_objs'
    )

    def __init__(
            self, pos: RectPos, img: pg.SurfaceType, text: str, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the input box and text
        Args:
            position, image, text, base layer (default = BG_LAYER)
        """

        self._box_init_pos: RectPos = pos

        self._box_img: pg.SurfaceType = img
        self.box_rect: pg.FRect = self._box_img.get_frect(
            **{pos.coord: pos.xy}
        )

        self._box_init_size: Size = Size(int(self.box_rect.w), int(self.box_rect.h))

        self.hovering: bool = False
        self._selected: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._hoovering_layer: int = base_layer + TOP_LAYER

        self.text = Text(RectPos(*self.box_rect.center, 'center'), text, base_layer)
        self._text_i: int = 0

        self._cursor_img: pg.SurfaceType = pg.Surface((1, int(self.text.rect.h)))
        self._cursor_img.fill(WHITE)
        self._cursor_rect: pg.FRect = self._cursor_img.get_frect(
            topleft=(self.text.get_pos_at(self._text_i), self.text.rect.y)
        )

        self._cursor_init_size: Size = Size(int(self._cursor_rect.w), int(self._cursor_rect.h))

        self.sub_objs: ObjsInfo = [
            ('text', self.text)
        ]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._box_img, self.box_rect.topleft, self._layer)]
        if self._selected:
            sequence.append((self._cursor_img, self._cursor_rect.topleft, self._hoovering_layer))

        return sequence

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
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

        self.hovering = self._selected = False
        self._text_i = 0

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes objects
        Args:
            window width ratio, window height ratio
        """

        box_size: tuple[int, int] = (
            int(self._box_init_size.w * win_ratio_w), int(self._box_init_size.h * win_ratio_h)
        )
        box_pos: tuple[float, float] = (
            self._box_init_pos.x * win_ratio_w, self._box_init_pos.y * win_ratio_h
        )

        self._box_img = pg.transform.scale(self._box_img, box_size)
        self.box_rect = self._box_img.get_frect(**{self._box_init_pos.coord: box_pos})

        cursor_size: tuple[int, int] = (
            int(self._cursor_init_size.w * win_ratio_w),
            int(self._cursor_init_size.h * win_ratio_h)
        )

        self._cursor_img = pg.transform.scale(self._cursor_img, cursor_size)

    def post_resize(self) -> None:
        """
        Handles post resizing behavior
        """

        self.get_cursor_pos()

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [
            (name, self._layer, depth_counter),
            ('cursor', self._hoovering_layer, depth_counter + 1)
        ]

    def get_cursor_pos(self) -> None:
        """
        Gets the cursor position based on the text index
        """

        self._cursor_rect.x = self.text.get_pos_at(self._text_i)
        self._cursor_rect.y = self.text.rect.y

    def set_text(self, text: str, text_i: int = -1) -> None:
        """
        Sets the text and adjusts the text index
        Args:
            text, text index (doesn't change if -1) (default = -1)
        """

        self.text.set_text(text)
        if text_i != -1:
            self._text_i = text_i
        self._text_i = min(self._text_i, len(self.text.text))

        self.get_cursor_pos()

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: list[int], limits: tuple[int, int],
            selected: bool
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

        text: str = self.text.text

        if self != hover_obj:
            if self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.hovering = False
        else:
            if not self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_IBEAM)
                self.hovering = True

            if mouse_info.released[0]:
                self._text_i = self.text.get_closest_to(mouse_info.x)
                self.get_cursor_pos()

                return True, text

        self._selected = selected
        if self._selected and keys:
            prev_text_i: int = self._text_i
            if pg.K_LEFT in keys:
                self._text_i = max(self._text_i - 1, 0)
            if pg.K_RIGHT in keys:
                self._text_i = min(self._text_i + 1, len(text))
            if pg.K_HOME in keys:
                self._text_i = 0
            if pg.K_END in keys:
                self._text_i = len(text)

            if self._text_i == prev_text_i:
                k: int = keys[-1]
                chr_limit: int = 1_114_111
                if k in (pg.K_BACKSPACE, pg.K_DELETE):
                    if k == pg.K_BACKSPACE:
                        if self._text_i:
                            text = text[:self._text_i - 1] + text[self._text_i:]
                            self._text_i -= 1
                    else:
                        text = text[:self._text_i] + text[self._text_i + 1:]

                    if text:
                        text = text.lstrip('0')
                        if not text or int(text) < limits[0]:
                            text = str(limits[0])
                elif k <= chr_limit:
                    char: str = chr(k)
                    if char.isdigit():
                        text = text[:self._text_i] + char + text[self._text_i:]
                        change_text_i: bool = True

                        if text.startswith('0'):
                            text = text.lstrip('0')
                            change_text_i = not bool(text)
                            if not text:
                                text = str(limits[0])

                        max_length: int = len(str(limits[1]))
                        if len(text) > max_length:
                            text = text[:max_length]

                        if int(text) < limits[0]:
                            text = str(limits[0])
                        elif int(text) > limits[1]:
                            text = str(limits[1])
                            change_text_i = self.text.text != str(limits[1])

                        if change_text_i:
                            self._text_i = min(self._text_i + 1, len(text))
            self.get_cursor_pos()

        return False, text
