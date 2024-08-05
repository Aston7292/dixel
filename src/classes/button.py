"""
class to create a button, when hovered changes image and text appears on top of it
"""

import pygame as pg
from typing import Tuple

from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo
from src.const import BlitSequence


class Button:
    """
    class to create a button, when hovered changes image and text appears on top of it
    """

    __slots__ = (
        '_init_pos', '_imgs', '_init_size', '_rect', '_img_i', '_hovering', '_text'
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, ...], text: str) -> None:
        """
        creates button surface, rect and text object
        takes position, two images and text
        """

        self._init_pos: RectPos = pos

        self._imgs: Tuple[pg.SurfaceType, ...] = imgs
        self._rect: pg.FRect = self._imgs[0].get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self._rect.w), int(self._rect.h))

        self._img_i: int = 0
        self._hovering: bool = False

        self._text: Text = Text(RectPos(*self._rect.midtop, 'midbottom'), 32, text)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(self._imgs[self._img_i], self._rect.topleft)]
        if self._img_i == 1:
            sequence += self._text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        size: Tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._imgs = tuple(pg.transform.scale(img, size) for img in self._imgs)
        self._rect = self._imgs[0].get_frect(**{self._init_pos.pos: pos})

        self._text.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo, toggle_on_press: bool = False) -> bool:
        """
        updates the button image if the mouse is _hovering it
        takes mouse info and the toggle_on_press flag
        returns whatever the button was clicked or not
        """

        if not self._rect.collidepoint(mouse_info.xy):
            if self._hovering:
                self._img_i = 0
                self._hovering = False
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

            return False

        if not self._hovering:
            self._img_i = 1
            self._hovering = True
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)

        if toggle_on_press and mouse_info.released[0]:
            self._img_i = 0
            self._hovering = False
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

        return mouse_info.released[0]
