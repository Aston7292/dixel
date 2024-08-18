"""
interface for choosing a color
"""

import pygame as pg
from math import ceil
from typing import Tuple, List, Final, Optional, Any

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, INPUT_BOX
from src.classes.text import Text
from src.utils import Point, RectPos, Size, MouseInfo
from src.const import ColorType, BlitSequence

SLIDER_1: Final[pg.SurfaceType] = pg.Surface((10, 35))
SLIDER_1.fill((40, 40, 40))
SLIDER_2: Final[pg.SurfaceType] = pg.Surface((10, 35))
SLIDER_2.fill((10, 10, 10))


class ScrollBar:
    """
    class to create a scroll bar to pick an r, g or b value of a color
    """

    __slots__ = (
        '_bar_init_pos', '_channel', '_unit_w', '_bar_img', 'bar_rect', '_bar_init_size',
        'value', '_slider_init_pos', '_slider_imgs', '_slider_rect', '_slider_init_size',
        'slider_img_i', 'hovering', 'scrolling', '_channel_text', 'value_input_box'
    )

    def __init__(self, pos: Point, channel: int, color: ColorType) -> None:
        """
        creates a bar and a slider
        takes position, the channel this scroll bar uses and starting color
        """

        self._bar_init_pos: RectPos = RectPos(*pos.xy, 'center')

        self._channel: int = channel
        self._unit_w: float = 1

        self._bar_img = pg.Surface((int(255 * self._unit_w), 25))
        self.bar_rect: pg.FRect = self._bar_img.get_frect(
            **{self._bar_init_pos.pos: self._bar_init_pos.xy}
        )

        self._bar_init_size: Size = Size(int(self.bar_rect.w), int(self.bar_rect.h))

        self.value: int = color[self._channel]
        self._slider_init_pos: RectPos = RectPos(*self.bar_rect.midleft, 'midleft')

        slider_x: float = self._slider_init_pos.x + self._unit_w * self.value
        self._slider_imgs: Tuple[pg.SurfaceType, ...] = (SLIDER_1, SLIDER_2)
        self._slider_rect: pg.FRect = self._slider_imgs[0].get_frect(
            **{self._slider_init_pos.pos: (slider_x, self._slider_init_pos.y)}
        )

        self._slider_init_size: Size = Size(int(self._slider_rect.w), int(self._slider_rect.h))

        self.slider_img_i: int = 0
        self.hovering: bool = False
        self.scrolling: bool = False

        self._channel_text: Text = Text(
            RectPos(*self.bar_rect.midleft, 'midright'), ('r', 'g', 'b')[self._channel]
        )
        self.value_input_box: NumInputBox = NumInputBox(
            RectPos(
                self.bar_rect.right + self._slider_rect.w + 10, self.bar_rect.centery, 'midleft'
            ), INPUT_BOX, str(self.value)
        )

        self.get_bar(color)

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [
            (self._bar_img, self.bar_rect.topleft),
            (self._slider_imgs[self.slider_img_i], self._slider_rect.topleft)
        ]
        sequence += self._channel_text.blit()
        sequence += self.value_input_box.blit()

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
        self.bar_rect = self._bar_img.get_frect(center=bar_pos)

        slider_size: Tuple[int, int] = (
            int(self._slider_init_size.w * win_ratio_w),
            int(self._slider_init_size.h * win_ratio_h)
        )
        slider_pos: Tuple[float, float] = (
            self._slider_init_pos.x * win_ratio_w + self._unit_w * self.value,
            self._slider_init_pos.y * win_ratio_h
        )

        self._slider_imgs = tuple(pg.transform.scale(img, slider_size) for img in self._slider_imgs)
        self._slider_rect = self._slider_imgs[0].get_frect(
            **{self._slider_init_pos.pos: slider_pos}
        )

        self._channel_text.handle_resize(win_ratio_w, win_ratio_h)
        self.value_input_box.handle_resize(win_ratio_w, win_ratio_h)

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
        self._slider_rect.x = self.bar_rect.x + self._unit_w * self.value
        self.value_input_box.text.modify_text(str(self.value))
        self.value_input_box.text_i = 0

        self.get_bar(color)
        self.value_input_box.get_cursor_pos()

    def upt(self, mouse_info: MouseInfo, keys: List[int], selection: Any) -> int:
        """
        Makes the object interactable
        takes mouse info, keys and the selected bool
        returns what was clicked: -1 = nothing, 0 = scroll bar, 1 = input box
        """

        if self.scrolling and mouse_info.released[0]:
            return 0

        if (
                not (
                        self.bar_rect.collidepoint(mouse_info.xy) or
                        self._slider_rect.collidepoint(mouse_info.xy)
                )
        ):
            if self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.hovering = False

            if not mouse_info.buttons[0]:
                self.scrolling = False
        else:
            if not self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
                self.hovering = True

            self.scrolling = bool(mouse_info.buttons[0])

        self.slider_img_i = 0
        prev_text: str = self.value_input_box.text.text

        clicked: bool
        new_text: str
        clicked, new_text = self.value_input_box.upt(
            mouse_info, keys, (0, 255), selection == self.value_input_box
        )

        if clicked:
            return 1

        value: int
        if self.scrolling:
            value = ceil((mouse_info.x - self.bar_rect.x) / self._unit_w)
            value = max(min(value, 255), 0)
            new_text = str(value)

        if selection == self:
            self.slider_img_i = 1

            if keys:
                value = self.value
                if pg.K_LEFT in keys:
                    value = max(value - 1, 0)
                elif pg.K_RIGHT in keys:
                    value = min(value + 1, 255)
                elif pg.K_PAGEDOWN in keys:
                    value = max(value - 25, 0)
                elif pg.K_PAGEUP in keys:
                    value = min(value + 25, 255)
                elif pg.K_HOME in keys:
                    value = 0
                elif pg.K_END in keys:
                    value = 255
                new_text = str(value)

        if new_text != prev_text:
            self.value = int(new_text) if new_text else 0
            self._slider_rect.x = self.bar_rect.x + self._unit_w * self.value

            self.value_input_box.text.modify_text(new_text)
            self.value_input_box.get_cursor_pos()

        return -1


class ColorPicker:
    """
    class to create an interface that allows the user to pick a color trough 3 scroll bars
    """

    __slots__ = (
        'ui', '_color', '_preview_init_pos', '_preview_img', '_preview_rect', '_preview_init_size',
        '_channels', '_objs', '_selection_i', '_hex_text'
    )

    def __init__(self, pos: RectPos, color: ColorType) -> None:
        """
        initializes the interface
        takes position and starting color
        """

        self.ui: UI = UI(pos, 'CHOOSE A COLOR')

        self._color: ColorType = color

        self._preview_init_pos: RectPos = RectPos(*self.ui.rect.center, 'midtop')

        self._preview_img: pg.SurfaceType = pg.Surface((100, 100))
        self._preview_img.fill(self._color)
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.pos: self._preview_init_pos.xy}
        )

        self._preview_init_size: Size = Size(int(self._preview_rect.w), int(self._preview_rect.h))

        b: ScrollBar = ScrollBar(
            Point(int(self.ui.rect.centerx), int(self._preview_rect.top - 50)), 2, self._color
        )
        g: ScrollBar = ScrollBar(
            Point(int(self.ui.rect.centerx), int(b.bar_rect.top - 50)), 1, self._color
        )
        r: ScrollBar = ScrollBar(
            Point(int(self.ui.rect.centerx), int(g.bar_rect.top - 50)), 0, self._color
        )

        self._channels: Tuple[ScrollBar, ...] = (r, g, b)
        self._objs: Tuple[Tuple[Any, ...], ...] = (
            (r, r.value_input_box), (g, g.value_input_box), (b, b.value_input_box)
        )
        self._selection_i: Point = Point(0, 0)

        hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
        self._hex_text: Text = Text(RectPos(*self._preview_rect.midtop, 'midbottom'), hex_string)

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = self.ui.blit()
        for channel in self._channels:
            sequence += channel.blit()
        sequence += [(self._preview_img, self._preview_rect.topleft)]
        sequence += self._hex_text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self.ui.handle_resize(win_ratio_w, win_ratio_h)

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

        for channel in self._channels:
            channel.handle_resize(win_ratio_w, win_ratio_h)
        self._hex_text.handle_resize(win_ratio_w, win_ratio_h)

    def set(self, color: ColorType) -> None:
        """
        sets the ui on a specific color
        takes color
        """

        self._color = color
        self._preview_img.fill(self._color)

        for channel in self._channels:
            channel.set(self._color)

        hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
        self._hex_text.modify_text(hex_string)

    def upt(
            self, mouse_info: MouseInfo, keys: List[int], ctrl: int
    ) -> Tuple[bool, Optional[ColorType]]:
        """
        makes the object interactable
        takes mouse info, keys and ctrl
        return whatever the interface was closed or not and the new color
        """

        if keys:
            if pg.K_UP in keys:
                self._selection_i.y = max(self._selection_i.y - 1, 0)
            elif pg.K_DOWN in keys:
                self._selection_i.y = min(self._selection_i.y + 1, len(self._objs) - 1)
            elif ctrl:
                prev_selection_x: int = self._selection_i.x
                if pg.K_LEFT in keys:
                    self._selection_i.x = max(self._selection_i.x - 1, 0)
                elif pg.K_RIGHT in keys:
                    self._selection_i.x = min(self._selection_i.x + 1, len(self._objs[0]) - 1)

                if self._selection_i.x != prev_selection_x:
                    keys = []  # prevents extra movement after switching selection

        prev_color: ColorType = self._color
        selection: Any = self._objs[self._selection_i.y][self._selection_i.x]

        for i, channel in enumerate(self._channels):
            new_selection: int = channel.upt(mouse_info, keys, selection)
            if new_selection != -1:
                self._selection_i.x, self._selection_i.y = new_selection, i
        self._color = tuple(channel.value for channel in self._channels)

        if self._color != prev_color:
            for channel in self._channels:
                channel.get_bar(self._color)
            self._preview_img.fill(self._color)

            hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
            self._hex_text.modify_text(hex_string)

        confirmed: bool
        exited: bool
        confirmed, exited = self.ui.upt(mouse_info, keys, ctrl)

        if confirmed or exited:
            self._selection_i.x = self._selection_i.y = 0
            for channel in self._channels:
                channel.slider_img_i = 0
                channel.hovering = channel.scrolling = False
                channel.value_input_box.hovering = channel.value_input_box.selected = False

        return confirmed or exited, self._color if confirmed else None
