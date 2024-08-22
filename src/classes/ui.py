"""
class to create a simple and easily customizable ui
"""

import pygame as pg
from os import path
from typing import Tuple, List, Final

from src.classes.clickable import Button
from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo, BlitSequence

INTERFACE: Final[pg.SurfaceType] = pg.Surface((500, 700))
INTERFACE.fill((60, 60, 60))

BUTTON_M_OFF: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'button_m_off.png')
).convert_alpha()
BUTTON_M_ON: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'button_m_on.png')
).convert_alpha()

CLOSE_1: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'close_button_off.png')
).convert_alpha()
CLOSE_2: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'close_button_on.png')
).convert_alpha()

INPUT_BOX: Final[pg.Surface] = pg.Surface((60, 40))


class UI:
    """
    class for rendering an ui with a title, confirm and exit button
    """

    __slots__ = (
        '_init_pos', '_img', 'rect', '_init_size', '_title', '_confirm', '_exit',
        'prev_mouse_cursor'
    )

    def __init__(self, pos: RectPos, title: str) -> None:
        """
        initializes the interface
        takes position and title
        """

        self._init_pos: RectPos = pos

        self._img: pg.SurfaceType = INTERFACE
        self.rect: pg.FRect = self._img.get_frect(**{self._init_pos.coord: self._init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self._title: Text = Text(
            RectPos(self.rect.centerx, self.rect.top + 10, 'midtop'), title, 40
        )

        self._confirm: Button = Button(
            RectPos(self.rect.right - 10, self.rect.bottom - 10, 'bottomright'),
            (BUTTON_M_OFF, BUTTON_M_ON), 'confirm'
        )
        self._exit: Button = Button(
            RectPos(self.rect.right - 10, self.rect.y + 10, 'topright'), (CLOSE_1, CLOSE_2), ''
        )

        self.prev_mouse_cursor: pg.Cursor = pg.mouse.get_cursor()

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(self._img, self.rect.topleft)]
        sequence += self._title.blit()
        sequence += self._confirm.blit()
        sequence += self._exit.blit()

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

        self._img = pg.transform.scale(self._img, size)
        self.rect = self._img.get_frect(**{self._init_pos.coord: pos})

        self._title.handle_resize(win_ratio_w, win_ratio_h)
        self._confirm.handle_resize(win_ratio_w, win_ratio_h)
        self._exit.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo, keys: List[int], ctrl: int) -> Tuple[bool, bool]:
        """
        makes the object interactable
        takes mouse info, keys and ctrl
        returns the buttons that were clicked
        """

        confirmed: bool = self._confirm.upt(mouse_info) or bool(ctrl and pg.K_RETURN in keys)
        exited: bool = self._exit.upt(mouse_info) or bool(ctrl and pg.K_BACKSPACE in keys)

        if confirmed or exited:
            self._confirm.img_i = self._exit.img_i = 0
            self._confirm.hovering = self._exit.hovering = False
            pg.mouse.set_cursor(self.prev_mouse_cursor)

        return confirmed, exited
