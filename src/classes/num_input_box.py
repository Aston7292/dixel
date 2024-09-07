"""
class to choose a number in range with an input box
"""

import pygame as pg
from typing import Any

from src.classes.text import Text
from src.utils import MouseInfo, RectPos, Size
from src.type_utils import LayeredBlitSequence, LayerSequence
from src.const import WHITE, BG_LAYER, ELEMENT_LAYER, TOP_LAYER


class NumInputBox:
    """
    class to choose a number in range with an input box
    """

    __slots__ = (
        '_box_init_pos', '_box_img', 'box_rect', '_box_init_size', 'hovering', '_selected',
        '_layer', '_hoovering_layer', 'text', 'text_i', '_cursor_img', '_cursor_rect',
        '_cursor_init_size'
    )

    def __init__(
            self, pos: RectPos, img: pg.SurfaceType, text: str, base_layer: int = BG_LAYER
    ) -> None:
        """
        creates the input box and text
        takes the position, image, text and base layer (default = BG_LAYER)
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
        self.text_i: int = 0

        self._cursor_img: pg.SurfaceType = pg.Surface((1, int(self.text.rect.h)))
        self._cursor_img.fill(WHITE)
        self._cursor_rect: pg.FRect = self._cursor_img.get_frect(
            topleft=(self.text.get_pos_at(self.text_i), self.text.rect.y)
        )

        self._cursor_init_size: Size = Size(int(self._cursor_rect.w), int(self._cursor_rect.h))

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._box_img, self.box_rect.topleft, self._layer)]
        sequence += self.text.blit()
        if self._selected:
            sequence += [(self._cursor_img, self._cursor_rect.topleft, self._hoovering_layer)]

        return sequence

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
        '''
        checks if the mouse is hovering any interactable part of the object
        takes mouse position
        returns the object that's being hovered (can be None) and the layer
        '''

        hover_obj: Any = self if self.box_rect.collidepoint(mouse_pos) else None

        return hover_obj, self._layer

    def leave(self) -> None:
        """
        clears relevant data when a state is leaved
        """

        self.hovering = self._selected = False
        self.text_i = 0

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        box_size: tuple[int, int] = (
            int(self._box_init_size.w * win_ratio_w), int(self._box_init_size.h * win_ratio_h)
        )
        box_pos: tuple[float, float] = (
            self._box_init_pos.x * win_ratio_w, self._box_init_pos.y * win_ratio_h
        )

        self._box_img = pg.transform.scale(self._box_img, box_size)
        self.box_rect = self._box_img.get_frect(**{self._box_init_pos.coord: box_pos})

        self.text.handle_resize(win_ratio_w, win_ratio_h)

        cursor_size: tuple[int, int] = (
            int(self._cursor_init_size.w * win_ratio_w),
            int(self._cursor_init_size.h * win_ratio_h)
        )

        self._cursor_img = pg.transform.scale(self._cursor_img, cursor_size)
        self.get_cursor_pos()

    def print_layers(self, name: str, counter: int) -> LayerSequence:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns a sequence to add in the main layer sequence
        """

        layer_sequence: LayerSequence = [(name, self._layer, counter)]
        layer_sequence += [('cursor', self._hoovering_layer, counter + 1)]
        layer_sequence += self.text.print_layers('text', counter + 1)

        return layer_sequence

    def get_cursor_pos(self) -> None:
        """
        gets the cursor position based on text index
        """

        self._cursor_rect.x = self.text.get_pos_at(self.text_i)
        self._cursor_rect.y = self.text.rect.y

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: list[int], limits: tuple[int, int],
            selected: bool
    ) -> tuple[bool, str]:
        """
        allows typing numbers, moving the cursor and deleting a character
        takes hovered object (can be None), mouse info, keys, limits and selected bool
        returns whatever the input box was clicked or not and the text
        """

        '''
        the text object isn't updated here because it can be also changed by other classes
        that use the NumInputBox
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
                self.text_i = self.text.get_closest_to(mouse_info.x)
                self.get_cursor_pos()

                return True, text

        self._selected = selected
        if self._selected and keys:
            prev_text_i: int = self.text_i
            if pg.K_LEFT in keys:
                self.text_i = max(self.text_i - 1, 0)
            if pg.K_RIGHT in keys:
                self.text_i = min(self.text_i + 1, len(text))
            if pg.K_HOME in keys:
                self.text_i = 0
            if pg.K_END in keys:
                self.text_i = len(text)

            if self.text_i == prev_text_i:
                k: int = keys[-1]
                chr_limit: int = 1_114_111
                if k == pg.K_BACKSPACE:
                    if self.text_i:
                        text = text[:self.text_i - 1] + text[self.text_i:]
                        self.text_i = max(self.text_i - 1, 0)
                elif k == pg.K_DELETE:
                    text = text[:self.text_i] + text[self.text_i + 1:]
                elif k <= chr_limit:
                    char: str = chr(k)
                    if char.isdigit():
                        text = text[:self.text_i] + char + text[self.text_i:]

                        max_length: int = len(str(limits[1]))
                        if len(text) > max_length:
                            text = text[:max_length]

                        self.text_i = min(self.text_i + 1, len(text))

                        if int(text) < limits[0]:
                            text = str(limits[0])
                        elif int(text) > limits[1]:
                            text = str(limits[1])

                if text:  # if text is already empty (backspace/delete) it doesn't become 0
                    text = text.lstrip('0')
                    if not text:
                        text = '0'
            self.get_cursor_pos()

        return False, text
