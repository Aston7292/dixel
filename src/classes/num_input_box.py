"""
class to choose a number between some bounds via an input box
"""

import pygame as pg
from typing import Tuple

from src.classes.text import Text
from src.utils import MouseInfo, RectPos, Size
from src.const import WHITE, BlitSequence


class NumInputBox:
    """
    class to choose a number between some bounds via an input box
    """

    __slots__ = (
        '_box_init_pos', '_box_img', '_box_rect', '_box_init_size', '_hovering', '_selected',
        'text', '_text_i', '_cursor_img', '_cursor_rect', '_cursor_init_size'
    )

    def __init__(self, pos: RectPos, img: pg.SurfaceType, text: str):
        """
        creates surface, rect and text object
        takes position, image and text
        """

        self._box_init_pos: RectPos = pos

        self._box_img: pg.SurfaceType = img
        self._box_rect: pg.FRect = self._box_img.get_frect(
            **{pos.pos: pos.xy}
        )

        self._box_init_size: Size = Size(int(self._box_rect.w), int(self._box_rect.h))

        self._hovering: bool = False
        self._selected: bool = False

        self.text = Text(RectPos(*self._box_rect.center, 'center'), 32, text)
        self._text_i: int = 0

        self._cursor_img: pg.SurfaceType = pg.Surface((1, self.text.rect.h))
        self._cursor_img.fill(WHITE)
        self._cursor_rect: pg.FRect = self._cursor_img.get_frect(
            topleft=(self.text.get_pos_at(self._text_i), self.text.rect.y)
        )

        self._cursor_init_size: Size = Size(int(self._cursor_rect.w), int(self._cursor_rect.h))

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(self._box_img, self._box_rect.topleft)]
        sequence += self.text.blit()
        if self._selected:
            sequence += [(self._cursor_img, self._cursor_rect.topleft)]

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        box_size: Tuple[int, int] = (
            int(self._box_init_size.w * win_ratio_w), int(self._box_init_size.h * win_ratio_h)
        )
        box_pos: Tuple[float, float] = (
            self._box_init_pos.x * win_ratio_w, self._box_init_pos.y * win_ratio_h
        )

        self._box_img = pg.transform.scale(self._box_img, box_size)
        self._box_rect = self._box_img.get_frect(**{self._box_init_pos.pos: box_pos})

        self.text.handle_resize(win_ratio_w, win_ratio_h)

        cursor_size: Tuple[int, int] = (
            int(self._cursor_init_size.w * win_ratio_w),
            int(self._cursor_init_size.h * win_ratio_h)
        )

        self._cursor_img = pg.transform.scale(self._cursor_img, cursor_size)
        self.get_cursor_pos()

    def get_cursor_pos(self) -> None:
        """
        calculates cursor position based on text index
        """

        self._cursor_rect.x = self.text.get_pos_at(self._text_i)
        self._cursor_rect.y = self.text.rect.y

    def upt(self, mouse_info: MouseInfo, selected: bool) -> bool:
        """
        makes the object interactable
        takes mouse info and selected bool
        returns whatever the input box was clicked or not
        """

        if not self._box_rect.collidepoint(mouse_info.xy):
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_IBEAM)
                self._hovering = True

            if mouse_info.released[0]:
                self._text_i = self.text.get_closest(mouse_info.x)
                self.get_cursor_pos()

                return True

        self._selected = selected

        return False
