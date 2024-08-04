"""
interface for choosing a color
"""

import pygame as pg
from typing import Tuple, Final

from src.classes.button import Button
from src.classes.text import Text
from src.utils import Point, RectPos, Size, MouseInfo
from src.const import BlitSequence

INTERFACE: Final[pg.SurfaceType] = pg.Surface((500, 700))
INTERFACE.fill((44, 44, 44))

BAR: Final[pg.SurfaceType] = pg.Surface((255, 25))
BAR.fill((31, 31, 31))
SLIDER: Final[pg.SurfaceType] = pg.Surface((10, 35))
SLIDER.fill((61, 61, 61))

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
        '_value', '_slider_init_pos', '_slider_img', '_slider_rect', '_slider_init_size',
        '_hovering', '_scrolling', '_text'
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

        self._value: int = 0
        self._slider_init_pos: Point = Point(
            int(self._bar_rect.x + self._value), int(self._bar_rect.centery)
        )

        self._slider_img: pg.SurfaceType = SLIDER
        self._slider_rect: pg.FRect = self._slider_img.get_frect(midleft=self._slider_init_pos.xy)

        self._slider_init_size: Size = Size(int(self._slider_rect.w), int(self._slider_rect.h))

        self._hovering: bool = False
        self._scrolling: bool = False

        self._text: Text = Text(
            RectPos(int(self._bar_rect.x), int(self._bar_rect.centery), 'midright'),
            32, str(self._value)
        )

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = (
            (self._bar_img, self._bar_rect.topleft), (self._slider_img, self._slider_rect.topleft)
        )
        sequence += self._text.blit()

        return sequence

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
            (self._slider_init_pos.x + self._value) * win_ratio_w,
            self._slider_init_pos.y * win_ratio_h
        )

        self._slider_img = pg.transform.scale(self._slider_img, slider_size)
        self._slider_rect = self._slider_img.get_frect(midleft=slider_pos)

        self._text.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo) -> None:
        """
        Makes the object interactable.
        Takes mouse info.
        """

        if (
            not (self._bar_rect.collidepoint(mouse_info.xy) or
            self._slider_rect.collidepoint(mouse_info.xy))
        ):
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = True

            if not mouse_info.buttons[0]:
                self._scrolling = False
        else:
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
                self._hovering = False

            self._scrolling = bool(mouse_info.buttons[0])

        if self._scrolling:
            self._slider_rect.x = max(
                min(mouse_info.x, self._bar_rect.right), self._bar_rect.left
            )
            self._value = int(self._slider_rect.x - self._bar_rect.x)
            self._text.modify_text(str(self._value))


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

    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        makes the object interactable
        takes mouse info
        return whatever the interface was closed or not
        """

        self._r.upt(mouse_info)

        if self._close.upt(mouse_info, True):
            return True

        return False
