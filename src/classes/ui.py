"""
class to create a simple and easily customizable ui
"""

import pygame as pg
from typing import Tuple, Final

from src.classes.button import Button
from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo
from src.const import BlitSequence

INTERFACE: Final[pg.SurfaceType] = pg.Surface((500, 700))
INTERFACE.fill((44, 44, 44))

CONFIRM_1: Final[pg.SurfaceType] = pg.Surface((100, 100))
CONFIRM_1.fill('yellow')
CONFIRM_2: Final[pg.SurfaceType] = pg.Surface((100, 100))
CONFIRM_2.fill('darkgoldenrod4')

CLOSE_1: Final[pg.SurfaceType] = pg.Surface((100, 100))
CLOSE_1.fill('red')
CLOSE_2: Final[pg.SurfaceType] = pg.Surface((100, 100))
CLOSE_2.fill('darkred')


class UI:
    """
    class for rendering a ui with a title close and confirm button
    """

    __slots__ = (
        '_init_pos', '_img', 'rect', '_init_size', '_title', '_confirm', '_close'
    )

    def __init__(self, pos: RectPos, title: str) -> None:
        """
        initializes the interface
        takes position and title
        """

        self._init_pos: RectPos = pos

        self._img: pg.SurfaceType = INTERFACE
        self.rect: pg.FRect = self._img.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self._title: Text = Text(
            RectPos(self.rect.centerx, self.rect.top + 10, 'midtop'), 40, title
        )

        self._confirm: Button = Button(
            RectPos(*self.rect.bottomright, 'bottomright'), (CONFIRM_1, CONFIRM_2), 'confirm'
        )
        self._close: Button = Button(
            RectPos(*self.rect.topright, 'topright'), (CLOSE_1, CLOSE_2), 'close'
        )

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(self._img, self.rect.topleft)]
        sequence += self._title.blit()
        sequence += self._confirm.blit()
        sequence += self._close.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size
        """

        size: Tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._img = pg.transform.scale(self._img, size)
        self.rect = self._img.get_frect(**{self._init_pos.pos: pos})

        self._title.handle_resize(win_ratio_w, win_ratio_h)
        self._confirm.handle_resize(win_ratio_w, win_ratio_h)
        self._close.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo) -> Tuple[bool, bool]:
        """
        makes the object interactable
        takes mouse info
        return the buttons that were clicked
        """

        confirmed: bool = self._confirm.upt(mouse_info, True)
        exited: bool = self._close.upt(mouse_info, True)

        return confirmed, exited
