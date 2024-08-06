"""
interface for choosing a color
"""

import pygame as pg
from math import ceil
from typing import Tuple, List, Final, Optional

from src.classes.button import Button
from src.classes.text import Text
from src.utils import Point, RectPos, Size, MouseInfo
from src.const import ColorType, BlitSequence

INTERFACE: Final[pg.SurfaceType] = pg.Surface((500, 700))
INTERFACE.fill((44, 44, 44))

SLIDER: Final[pg.SurfaceType] = pg.Surface((10, 35))
SLIDER.fill((61, 61, 61))

CONFIRM_1: Final[pg.SurfaceType] = pg.Surface((100, 100))
CONFIRM_1.fill('yellow')
CONFIRM_2: Final[pg.SurfaceType] = pg.Surface((100, 100))
CONFIRM_2.fill('darkgoldenrod4')

CLOSE_1: Final[pg.SurfaceType] = pg.Surface((100, 100))
CLOSE_1.fill('red')
CLOSE_2: Final[pg.SurfaceType] = pg.Surface((100, 100))
CLOSE_2.fill('darkred')


class ScrollBar:
    """
    class to create a scroll bar to pick an r, g or b value of a color
    """

    __slots__ = (
        '_bar_init_pos', '_unit_w', '_channel', '_bar_img', '_bar_rect', '_bar_init_size',
        'value', '_slider_init_pos', '_slider_img', '_slider_rect', '_slider_init_size',
        '_hovering', '_scrolling', '_channel_text', '_value_text'
    )

    def __init__(self, pos: Point, channel: int, color: ColorType) -> None:
        """
        creates a bar and a slider
        takes position, the channel this scroll bar uses and starting color
        """

        self._bar_init_pos: Point = pos

        self._channel: int = channel
        self._unit_w: float = 1

        self._bar_img = pg.Surface((int(255 * self._unit_w), 25))
        self._bar_rect: pg.FRect = self._bar_img.get_frect(center=self._bar_init_pos.xy)

        self._bar_init_size: Size = Size(int(self._bar_rect.w), int(self._bar_rect.h))

        self.value: int = color[self._channel]
        self._slider_init_pos: RectPos = RectPos(*self._bar_rect.midleft, 'midleft')
        slider_x: float = self._slider_init_pos.x + self._unit_w * self.value

        self._slider_img: pg.SurfaceType = SLIDER
        self._slider_rect: pg.FRect = self._slider_img.get_frect(
            **{self._slider_init_pos.pos: (slider_x, self._slider_init_pos.y)}
        )

        self._slider_init_size: Size = Size(int(self._slider_rect.w), int(self._slider_rect.h))

        self._hovering: bool = False
        self._scrolling: bool = False

        self._channel_text: Text = Text(
            RectPos(*self._bar_rect.midleft, 'midright'), 32, ('r', 'g', 'b')[self._channel]
        )
        self._value_text: Text = Text(
            RectPos(self._bar_rect.right + self._slider_rect.w, self._bar_rect.centery, 'midleft'),
            32, str(self.value)
        )

        self.get_bar(color)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [
            (self._bar_img, self._bar_rect.topleft), (self._slider_img, self._slider_rect.topleft)
        ]
        sequence += self._channel_text.blit()
        sequence += self._value_text.blit()

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
        self._unit_w = self._bar_init_size.w * win_ratio_w / 255

        self._bar_img = pg.transform.scale(self._bar_img, bar_size)
        self._bar_rect = self._bar_img.get_frect(center=bar_pos)

        slider_size: Tuple[int, int] = (
            int(self._slider_init_size.w * win_ratio_w),
            int(self._slider_init_size.h * win_ratio_h)
        )
        slider_pos: Tuple[float, float] = (
            self._slider_init_pos.x * win_ratio_w + self._unit_w * self.value,
            self._slider_init_pos.y * win_ratio_h
        )

        self._slider_img = pg.transform.scale(self._slider_img, slider_size)
        self._slider_rect = self._slider_img.get_frect(**{self._slider_init_pos.pos: slider_pos})

        self._channel_text.handle_resize(win_ratio_w, win_ratio_h)
        self._value_text.handle_resize(win_ratio_w, win_ratio_h)

    def get_bar(self, current_color: ColorType) -> None:
        """
        draws a gradient on the bar
        takes color
        """

        sequence: BlitSequence = []

        original_size: Tuple[int, int] = self._bar_img.get_size()
        self._bar_img = pg.Surface((255, self._bar_init_size.h))
        sect_surf: pg.SurfaceType = pg.Surface((1, self._bar_init_size.h))

        color: List[int] = list(current_color)
        for i in range(256):
            color[self._channel] = i
            sect_surf.fill(color)
            sequence.append((sect_surf.copy(), (i, 0)))

        self._bar_img.fblits(sequence)
        #  drawing on the normal size bar is inaccurate
        self._bar_img = pg.transform.scale(self._bar_img, original_size)

    def set(self, color: ColorType) -> None:
        """
        sets the bar on a specif value
        takes color
        """

        self.value = color[self._channel]
        self._slider_rect.x = self._bar_rect.x + self._unit_w * self.value
        self._value_text.modify_text(str(self.value))

        self.get_bar(color)

    def upt(self, mouse_info: MouseInfo) -> None:
        """
        Makes the object interactable.
        Takes mouse info.
        """

        if (
                not (
                        self._bar_rect.collidepoint(mouse_info.xy) or
                        self._slider_rect.collidepoint(mouse_info.xy)
                )
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
            self.value = ceil((self._slider_rect.x - self._bar_rect.x) / self._unit_w)
            self._value_text.modify_text(str(self.value))


class ColorPicker:
    """
    class to create an interface that allows the user to pick a color trough 3 scroll bars
    """

    __slots__ = (
        '_init_pos', '_img', '_rect', '_init_size', '_color', '_preview_init_pos',
        '_preview_img', '_preview_rect', '_preview_init_size', '_r', '_g', '_b',
        '_title', '_hex_text', '_confirm', '_close'
    )

    def __init__(self, pos: RectPos, color: ColorType) -> None:
        """
        initializes the interface
        takes position and starting color
        """

        self._init_pos: RectPos = pos

        self._img: pg.SurfaceType = INTERFACE
        self._rect: pg.FRect = self._img.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self._rect.w), int(self._rect.h))

        self._color: ColorType = color

        self._preview_init_pos: RectPos = RectPos(*self._rect.center, 'center')

        self._preview_img: pg.SurfaceType = pg.Surface((100, 100))
        self._preview_img.fill(self._color)
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.pos: self._preview_init_pos.xy}
        )

        self._preview_init_size: Size = Size(int(self._preview_rect.w), int(self._preview_rect.h))

        self._r: ScrollBar = ScrollBar(
            Point(int(self._rect.centerx), int(self._preview_rect.top - 150)), 0, self._color
        )
        self._g: ScrollBar = ScrollBar(
            Point(int(self._rect.centerx), int(self._preview_rect.top - 100)), 1, self._color
        )
        self._b: ScrollBar = ScrollBar(
            Point(int(self._rect.centerx), int(self._preview_rect.top - 50)), 2, self._color
        )

        self._title: Text = Text(
            RectPos(self._rect.centerx, self._rect.top + 10, 'midtop'), 40, 'CHOOSE A COLOR'
        )
        hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
        self._hex_text: Text = Text(
            RectPos(*self._preview_rect.midtop, 'midbottom'), 32, hex_string
        )

        self._confirm: Button = Button(
            RectPos(*self._rect.bottomright, 'bottomright'), (CONFIRM_1, CONFIRM_2), 'confirm'
        )
        self._close: Button = Button(
            RectPos(*self._rect.topright, 'topright'), (CLOSE_1, CLOSE_2), 'close'
        )

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(self._img, self._rect.topleft)]
        sequence += self._r.blit()
        sequence += self._g.blit()
        sequence += self._b.blit()
        sequence += [(self._preview_img, self._preview_rect.topleft)]
        sequence += self._title.blit()
        sequence += self._hex_text.blit()
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
        self._rect = self._img.get_frect(**{self._init_pos.pos: pos})

        preview_size: Tuple[int, int] = (
            int(self._preview_init_size.w * win_ratio_w),
            int(self._preview_init_size.h * win_ratio_h)
        )
        preview_pos: Tuple[float, float] = (
            self._preview_init_pos.x * win_ratio_w, self._preview_init_pos.y * win_ratio_h
        )

        self._preview_img = pg.transform.scale(self._preview_img, preview_size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.pos: preview_pos}
        )

        self._r.handle_resize(win_ratio_w, win_ratio_h)
        self._g.handle_resize(win_ratio_w, win_ratio_h)
        self._b.handle_resize(win_ratio_w, win_ratio_h)

        self._title.handle_resize(win_ratio_w, win_ratio_h)
        self._hex_text.handle_resize(win_ratio_w, win_ratio_h)
        self._confirm.handle_resize(win_ratio_w, win_ratio_h)
        self._close.handle_resize(win_ratio_w, win_ratio_h)

    def set(self, color: ColorType) -> None:
        """
        set the ui on a specific color
        takes color
        """

        self._color = color
        self._preview_img.fill(self._color)

        self._r.set(self._color)
        self._g.set(self._color)
        self._b.set(self._color)

        hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
        self._hex_text.modify_text(hex_string)

    def upt(self, mouse_info: MouseInfo) -> Tuple[bool, Optional[ColorType]]:
        """
        makes the object interactable
        takes mouse info
        return whatever the interface was closed or not and the new color
        """

        prev_color: ColorType = self._color

        self._r.upt(mouse_info)
        self._g.upt(mouse_info)
        self._b.upt(mouse_info)
        self._color = (self._r.value, self._g.value, self._b.value)

        if prev_color != self._color:
            self._r.get_bar(self._color)
            self._g.get_bar(self._color)
            self._b.get_bar(self._color)
            self._preview_img.fill(self._color)

            hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
            self._hex_text.modify_text(hex_string)

        if self._confirm.upt(mouse_info, True):
            return True, self._color

        if self._close.upt(mouse_info, True):
            return True, None

        return False, None
