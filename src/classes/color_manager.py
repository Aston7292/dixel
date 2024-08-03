"""
interface for choosing a color
"""

import pygame as pg
from typing import Tuple, Final

from src.classes.button import Button
from src.utils import Point, RectPos, Size
from src.const import BlitSequence

INTERFACE: Final[pg.SurfaceType] = pg.Surface((500, 700))
INTERFACE.fill('lightgray')

BAR: Final[pg.SurfaceType] = pg.Surface((255, 25))
BAR.fill('darkgray')
SLIDER: Final[pg.SurfaceType] = pg.Surface((10, 35))

CLOSE_1: Final[pg.SurfaceType] = pg.Surface((100, 100))
CLOSE_1.fill('red')
CLOSE_2: Final[pg.SurfaceType] = pg.Surface((100, 100))
CLOSE_2.fill('darkred')

class ScrollBar:
    """
    class to create a scroll bar to pick a r, g or b value of a color
    """

    __slots__ = (
        '_bar_init_pos', '_bar_img', '_bar_rect', '_bar_init_size',
        '_slider_init_pos', '_slider_img', '_slider_rect', '_slider_init_size'
    )

    def __init__(self, pos: Point) -> None:
        """
        creates two surfaces and rects, one for the scroller and one for the movable part
        takes position
        """

        self._bar_init_pos: Point = pos

        self._bar_img: pg.SurfaceType = BAR
        self._bar_rect: pg.FRect = self._bar_img.get_frect(center=self._bar_init_pos.xy)

        self._bar_init_size: Size = Size(int(self._bar_rect.w), int(self._bar_rect.h))

        self._slider_init_pos: Point = Point(int(self._bar_rect.x), int(self._bar_rect.centery))

        self._slider_img: pg.SurfaceType = SLIDER
        self._slider_rect: pg.FRect = self._slider_img.get_frect(midleft=self._slider_init_pos.xy)

        self._slider_init_size: Size = Size(int(self._slider_rect.w), int(self._slider_rect.h))

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return (
            (self._bar_img, self._bar_rect.topleft), (self._slider_img, self._slider_rect.topleft)
        )

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes surfaces
        takes window size ratio
        """

        bar_size: Tuple[int, int] = (
            int(self._bar_init_size.w * win_ratio_w), int(self._bar_init_size.h * win_ratio_h)
        )
        bar_pos: Tuple[float, float] = (
            self._bar_init_pos.x * win_ratio_w, self._bar_init_pos.y * win_ratio_h
        )

        self._bar_img = pg.transform.scale(self._bar_img, bar_size)
        self._bar_rect = self._bar_img.get_frect(center=bar_pos)

        slider_size: Tuple[int, int] = (
            int(self._slider_init_size.w * win_ratio_w), int(self._slider_init_size.h * win_ratio_h)
        )
        slider_pos: Tuple[float, float] = (
            self._slider_init_pos.x * win_ratio_w, self._slider_init_pos.y * win_ratio_h
        )

        self._slider_img = pg.transform.scale(self._slider_img, slider_size)
        self._slider_rect = self._slider_img.get_frect(midleft=slider_pos)

    def upt(self, mouse_pos: Point, mouse_buttons: Tuple[bool, bool, bool]) -> None:
        """
        makes the object interactable
        takes mouse position and buttons state
        """


class ColorPicker:
    """
    class to create an interface that allows the user to pick a color trough 3 scroll bars
    """

    __slots__ = (
        '_init_pos', '_img', '_rect', '_init_size', '_r', '_close'
    )

    def __init__(self, pos: RectPos) -> None:
        """
        initializes the interface
        takes position
        """

        self._init_pos: RectPos = pos

        self._img: pg.SurfaceType = INTERFACE
        self._rect: pg.FRect = self._img.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self._rect.w), int(self._rect.h))

        self._r: ScrollBar = ScrollBar(Point(int(self._rect.centerx), int(self._rect.top + 100)))

        self._close: Button = Button(
            RectPos(int(self._rect.right), int(self._rect.y), 'topright'),
            (CLOSE_1, CLOSE_2), 'close'
        )

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = ((self._img, self._rect.topleft),)
        sequence += self._r.blit()
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
        self._rect = self._img.get_frect(**{self._init_pos.pos: pos})

        self._r.handle_resize(win_ratio_w, win_ratio_h)
        self._close.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_pos: Point, released_left: bool) -> bool:
        """
        makes the object interactable
        takes mouse position and left button state
        return whatever the interface was closed or not
        """

        if self._close.upt(mouse_pos, released_left, True):
            return True

        return False
