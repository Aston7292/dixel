"""
Class to choose a number in range with an input box
"""

import pygame as pg
from typing import Final, Optional, Any

from src.classes.text import Text
from src.utils import RectPos, Size, ObjInfo, MouseInfo
from src.type_utils import LayeredBlitSequence, LayerSequence
from src.consts import WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER


CHR_LIMIT: Final[int] = 1_114_111


class NumInputBox:
    """
    Class to choose a number in range with an input box
    """

    __slots__ = (
        '_box_init_pos', '_box_img', 'box_rect', '_box_init_size', 'is_hovering', '_is_selected',
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

        self._box_img: pg.Surface = img
        self.box_rect: pg.FRect = self._box_img.get_frect(
            **{pos.coord_type: pos.xy}
        )

        self._box_init_size: Size = Size(int(self.box_rect.w), int(self.box_rect.h))

        self.is_hovering: bool = False
        self._is_selected: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._hovering_layer: int = base_layer + TOP_LAYER

        self.text_label = Text(RectPos(*self.box_rect.center, 'center'), text, base_layer)
        self._cursor_i: int = 0

        self._cursor_img: pg.Surface = pg.Surface((1, int(self.text_label.rect.h)))
        self._cursor_img.fill(WHITE)
        self._cursor_rect: pg.FRect = self._cursor_img.get_frect(
            topleft=(self.text_label.get_pos_at(self._cursor_i), self.text_label.rect.y)
        )

        self._cursor_init_size: Size = Size(int(self._cursor_rect.w), int(self._cursor_rect.h))

        self.objs_info: list[ObjInfo] = [ObjInfo('text', self.text_label)]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._box_img, self.box_rect.topleft, self._layer)]
        if self._is_selected:
            sequence.append((self._cursor_img, self._cursor_rect.topleft, self._hovering_layer))

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

        self.is_hovering = self._is_selected = False
        self._cursor_i = 0

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
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
        self.box_rect = self._box_img.get_frect(**{self._box_init_pos.coord_type: box_pos})

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
            ('cursor', self._hovering_layer, depth_counter + 1)
        ]

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

        text: str = self.text_label.text

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

                return True, text

        self._is_selected = is_selected
        if self._is_selected and keys:
            prev_cursor_i: int = self._cursor_i
            if pg.K_LEFT in keys:
                self._cursor_i = max(self._cursor_i - 1, 0)
            if pg.K_RIGHT in keys:
                self._cursor_i = min(self._cursor_i + 1, len(text))
            if pg.K_HOME in keys:
                self._cursor_i = 0
            if pg.K_END in keys:
                self._cursor_i = len(text)

            if self._cursor_i == prev_cursor_i:
                k: int = keys[-1]
                if k in (pg.K_BACKSPACE, pg.K_DELETE):
                    if k == pg.K_BACKSPACE:
                        if self._cursor_i:
                            text = text[:self._cursor_i - 1] + text[self._cursor_i:]
                            self._cursor_i -= 1
                    else:
                        text = text[:self._cursor_i] + text[self._cursor_i + 1:]

                    if text:
                        text = text.lstrip('0')
                        if not text or int(text) < limits[0]:
                            text = str(limits[0])
                elif k <= CHR_LIMIT:
                    char: str = chr(k)
                    if char.isdigit():
                        text = text[:self._cursor_i] + char + text[self._cursor_i:]
                        change_cursor_i: bool = True

                        if text.startswith('0'):
                            text = text.lstrip('0')
                            change_cursor_i = not bool(text)
                            if not text:
                                text = str(limits[0])

                        max_length: int = len(str(limits[1]))
                        if len(text) > max_length:
                            text = text[:max_length]

                        if int(text) < limits[0]:
                            text = str(limits[0])
                        elif int(text) > limits[1]:
                            text = str(limits[1])
                            change_cursor_i = self.text_label.text != str(limits[1])

                        if change_cursor_i:
                            self._cursor_i = min(self._cursor_i + 1, len(text))
            self.get_cursor_pos()

        return False, text
