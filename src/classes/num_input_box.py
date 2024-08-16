"""
class to choose a number between some bounds via an input box
"""

import pygame as pg
from typing import Tuple

from src.classes.text import Text
from src.utils import MouseInfo, RectPos, Size
from src.const import BlitSequence

class NumInputBox:
    """
    class to choose a number between some bounds via an input box
    """

    __slots__ = (
        '_init_pos', '_img', '_rect', '_init_size', '_hovering', 'text'
    )

    def __init__(self, pos: RectPos, img: pg.SurfaceType, text: str):
        """
        creates surface, rect and text object
        takes position, image and text
        """

        self._init_pos: RectPos = pos

        self._img: pg.SurfaceType = img
        self._rect: pg.FRect = self._img.get_frect(
            **{pos.pos: pos.xy}
        )

        self._init_size: Size = Size(int(self._rect.w), int(self._rect.h))

        self._hovering: bool = False

        self.text = Text(RectPos(*self._rect.center, 'center'), 32, text)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return [(self._img, self._rect.topleft)] + self.text.blit()

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        size: Tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._img = pg.transform.scale(self._img, size)
        self._rect = self._img.get_frect(**{self._init_pos.pos: pos})

        self.text.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo) -> None:
        """
        makes the object interactable
        takes mouse info
        """

        if not self._rect.collidepoint(mouse_info.xy):
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
                self._hovering = True
