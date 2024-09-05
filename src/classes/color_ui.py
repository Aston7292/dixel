"""
interface for choosing a color
"""

import pygame as pg
from math import ceil
from typing import Final, Optional, Any

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, INPUT_BOX
from src.classes.text import Text
from src.utils import (
    Point, RectPos, Size, MouseInfo, ColorType, BlitSequence, LayeredBlitSequence, LayersInfo
)
from src.const import BG_LAYER, ELEMENT_LAYER

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
        'slider_img_i', 'hovering', 'scrolling', '_layer', '_channel_text', 'value_input_box'
    )

    def __init__(
            self, pos: RectPos, channel: int, color: ColorType, base_layer: int = BG_LAYER
    ) -> None:
        """
        creates a bar, a slider and text
        takes position, the channel the scroll bar uses and starting color
        """

        self._bar_init_pos: RectPos = pos

        self._channel: int = channel
        self._unit_w: float = 1.0

        self._bar_img = pg.Surface((int(255 * self._unit_w), 25))
        self.bar_rect: pg.FRect = self._bar_img.get_frect(
            **{self._bar_init_pos.coord: self._bar_init_pos.xy}
        )

        self._bar_init_size: Size = Size(int(self.bar_rect.w), int(self.bar_rect.h))

        self.value: int = color[self._channel]
        self._slider_init_pos: RectPos = RectPos(*self.bar_rect.midleft, 'midleft')

        slider_x: float = self._slider_init_pos.x + self._unit_w * self.value
        self._slider_imgs: tuple[pg.SurfaceType, ...] = (SLIDER_1, SLIDER_2)
        self._slider_rect: pg.FRect = self._slider_imgs[0].get_frect(
            **{self._slider_init_pos.coord: (slider_x, self._slider_init_pos.y)}
        )

        self._slider_init_size: Size = Size(int(self._slider_rect.w), int(self._slider_rect.h))

        self.slider_img_i: int = 0
        self.hovering: bool = False
        self.scrolling: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER

        self._channel_text: Text = Text(
            RectPos(*self.bar_rect.midleft, 'midright'), ('r', 'g', 'b')[self._channel], base_layer
        )
        self.value_input_box: NumInputBox = NumInputBox(
            RectPos(
                self.bar_rect.right + self._slider_rect.w + 10.0, self.bar_rect.centery, 'midleft'
            ), INPUT_BOX, str(self.value), base_layer
        )

        self.get_bar(color)

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [
            (self._bar_img, self.bar_rect.topleft, self._layer),
            (self._slider_imgs[self.slider_img_i], self._slider_rect.topleft, self._layer)
        ]
        sequence += self._channel_text.blit()
        sequence += self.value_input_box.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes surfaces
        takes window size ratio
        """

        bar_size: tuple[int, int] = (
            int(self._bar_init_size.w * win_ratio_w), int(self._bar_init_size.h * win_ratio_h)
        )
        bar_pos: tuple[float, float] = (
            self._bar_init_pos.x * win_ratio_w, self._bar_init_pos.y * win_ratio_h
        )
        self._unit_w = self._bar_init_size.w * win_ratio_w / 255.0

        self._bar_img = pg.transform.scale(self._bar_img, bar_size)
        self.bar_rect = self._bar_img.get_frect(center=bar_pos)

        slider_size: tuple[int, int] = (
            int(self._slider_init_size.w * win_ratio_w),
            int(self._slider_init_size.h * win_ratio_h)
        )
        slider_pos: tuple[float, float] = (
            self._slider_init_pos.x * win_ratio_w + self._unit_w * self.value,
            self._slider_init_pos.y * win_ratio_h
        )

        self._slider_imgs = tuple(pg.transform.scale(img, slider_size) for img in self._slider_imgs)
        self._slider_rect = self._slider_imgs[0].get_frect(
            **{self._slider_init_pos.coord: slider_pos}
        )

        self._channel_text.handle_resize(win_ratio_w, win_ratio_h)
        self.value_input_box.handle_resize(win_ratio_w, win_ratio_h)

    def leave(self) -> None:
        """
        clears everything that needs to be cleared when the object is leaved
        """

        self.slider_img_i = 0
        self.hovering = self.scrolling = False
        self.value_input_box.leave()

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = [(name, -1, counter)]
        layers_info += [('bar', self._layer, counter + 1), ('slider', self._layer, counter + 1)]
        layers_info += self._channel_text.print_layers('text', counter + 1)
        layers_info += self.value_input_box.print_layers('input box', counter + 1)

        return layers_info

    def get_bar(self, color: ColorType) -> None:
        """
        draws a gradient on the bar
        takes color
        """

        sequence: BlitSequence = []

        original_size: tuple[int, int] = self._bar_img.get_size()
        #  drawing on the normal-sized bar is inaccurate
        self._bar_img = pg.Surface((255, self._bar_init_size.h))
        sect_surf: pg.SurfaceType = pg.Surface((1, self._bar_init_size.h))

        current_color: list[int] = list(color)
        for i in range(256):
            current_color[self._channel] = i
            sect_surf.fill(current_color)
            sequence.append((sect_surf.copy(), (i, 0)))
        self._bar_img.fblits(sequence)

        self._bar_img = pg.transform.scale(self._bar_img, original_size)

    def set_value(self, color: ColorType) -> None:
        """
        sets the bar on a specif value
        takes color
        """

        self.value = color[self._channel]
        self._slider_rect.x = self.bar_rect.x + self._unit_w * self.value
        self.value_input_box.text.set_text(str(self.value))
        self.value_input_box.text_i = 0

        self.get_bar(color)
        self.value_input_box.get_cursor_pos()

    def upt(self, mouse_info: MouseInfo, keys: list[int], selection: Any) -> int:
        """
        makes the object interactable
        takes mouse info, keys and the selection
        returns what was clicked: -1 = nothing, 0 = scroll bar, 1 = input box
        """

        if self.hovering and mouse_info.released[0]:
            return 0

        clicked: bool
        text: str
        clicked, text = self.value_input_box.upt(
            mouse_info, keys, (0, 255), selection == self.value_input_box
        )

        if clicked:
            return 1

        hovering: bool = (
            self.bar_rect.collidepoint(mouse_info.xy) or
            self._slider_rect.collidepoint(mouse_info.xy)
        )
        if not hovering:
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

        value: int
        if self.scrolling:
            value = ceil((mouse_info.x - self.bar_rect.x) / self._unit_w)
            value = max(min(value, 255), 0)
            text = str(value)

        if selection == self:
            self.slider_img_i = 1

            if keys:
                value = self.value
                if pg.K_LEFT in keys:
                    value = max(value - 1, 0)
                if pg.K_RIGHT in keys:
                    value = min(value + 1, 255)
                if pg.K_PAGEDOWN in keys:
                    value = max(value - 25, 0)
                if pg.K_PAGEUP in keys:
                    value = min(value + 25, 255)
                if pg.K_HOME in keys:
                    value = 0
                if pg.K_END in keys:
                    value = 255
                text = str(value)

        if text != prev_text:
            self.value = int(text) if text else 0
            self._slider_rect.x = self.bar_rect.x + self._unit_w * self.value

            self.value_input_box.text.set_text(text)
            self.value_input_box.text_i = min(
                self.value_input_box.text_i, len(self.value_input_box.text.text)
            )

            self.value_input_box.get_cursor_pos()

        return -1


class ColorPicker(UI):
    """
    class to create an interface that allows the user to pick a color trough 3 scroll bars,
    includes a preview
    """

    __slots__ = (
        '_color', '_preview_init_pos', '_preview_img', '_preview_rect', '_preview_init_size',
        '_preview_layer', '_channels', '_objs', '_selection_i', '_hex_text'
    )

    def __init__(self, pos: RectPos, color: ColorType) -> None:
        """
        initializes the interface
        takes position and starting color
        """

        super().__init__(pos, 'CHOOSE A COLOR')

        self._color: ColorType = color

        self._preview_init_pos: RectPos = RectPos(*self._ui_rect.center, 'midtop')

        self._preview_img: pg.SurfaceType = pg.Surface((100, 100))
        self._preview_img.fill(self._color)
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: self._preview_init_pos.xy}
        )

        self._preview_init_size: Size = Size(int(self._preview_rect.w), int(self._preview_rect.h))

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        b: ScrollBar = ScrollBar(
            RectPos(self._ui_rect.centerx, self._preview_rect.top - 50.0, 'center'), 2, self._color,
            self._base_layer
        )
        g: ScrollBar = ScrollBar(
            RectPos(self._ui_rect.centerx, b.bar_rect.top - 50.0, 'center'), 1, self._color,
            self._base_layer
        )
        r: ScrollBar = ScrollBar(
            RectPos(self._ui_rect.centerx, g.bar_rect.top - 50.0, 'center'), 0, self._color,
            self._base_layer
        )

        self._channels: tuple[ScrollBar, ...] = (r, g, b)
        self._objs: tuple[tuple[Any, ...], ...] = (
            (r, r.value_input_box), (g, g.value_input_box), (b, b.value_input_box)
        )
        self._selection_i: Point = Point(0, 0)

        hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
        self._hex_text: Text = Text(
            RectPos(*self._preview_rect.midtop, 'midbottom'), hex_string, self._base_layer
        )

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = super().blit()
        for channel in self._channels:
            sequence += channel.blit()
        sequence += [(self._preview_img, self._preview_rect.topleft, self._preview_layer)]
        sequence += self._hex_text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        super().handle_resize(win_ratio_w, win_ratio_h)

        preview_size: tuple[int, int] = (
            int(self._preview_init_size.w * win_ratio_w),
            int(self._preview_init_size.h * win_ratio_h)
        )
        preview_pos: tuple[float, float] = (
            self._preview_init_pos.x * win_ratio_w, self._preview_init_pos.y * win_ratio_h
        )

        self._preview_img = pg.transform.scale(self._preview_img, preview_size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: preview_pos}
        )

        for channel in self._channels:
            channel.handle_resize(win_ratio_w, win_ratio_h)
        self._hex_text.handle_resize(win_ratio_w, win_ratio_h)

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = super().print_layers(name, counter)
        for channel in self._channels:
            layers_info += channel.print_layers('scroll bar', counter + 1)
        layers_info += self._hex_text.print_layers('text hex', counter + 1)
        layers_info += [('preview', self._preview_layer, counter + 1)]

        return layers_info

    def set_color(self, color: ColorType) -> None:
        """
        sets the ui on a specific color
        takes color
        """

        self._color = color
        self._preview_img.fill(self._color)

        for channel in self._channels:
            channel.set_value(self._color)

        hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
        self._hex_text.set_text(hex_string)

    def upt(
            self, mouse_info: MouseInfo, keys: list[int], ctrl: int
    ) -> tuple[bool, Optional[ColorType]]:
        """
        makes the object interactable
        takes mouse info, keys and ctrl
        returns whatever the interface was closed or not and the color (can be None)
        """

        if keys:
            if pg.K_UP in keys:
                self._selection_i.y = max(self._selection_i.y - 1, 0)
            if pg.K_DOWN in keys:
                self._selection_i.y = min(self._selection_i.y + 1, len(self._objs) - 1)
            if ctrl:
                prev_selection_x: int = self._selection_i.x
                if pg.K_LEFT in keys:
                    self._selection_i.x = max(self._selection_i.x - 1, 0)
                if pg.K_RIGHT in keys:
                    self._selection_i.x = min(self._selection_i.x + 1, len(self._objs[0]) - 1)

                if self._selection_i.x != prev_selection_x:
                    keys = []  # prevents extra movement after switching selection

        prev_color: ColorType = self._color
        selection: Any = self._objs[self._selection_i.y][self._selection_i.x]

        for i, channel in enumerate(self._channels):
            selection_i: int = channel.upt(mouse_info, keys, selection)
            if selection_i != -1:
                self._selection_i.x, self._selection_i.y = selection_i, i
        self._color = tuple(channel.value for channel in self._channels)

        if self._color != prev_color:
            for channel in self._channels:
                channel.get_bar(self._color)
            self._preview_img.fill(self._color)

            hex_string: str = '#' + ''.join((f'{channel:02x}' for channel in self._color))
            self._hex_text.set_text(hex_string)

        confirmed: bool
        exited: bool
        confirmed, exited = self._base_upt(mouse_info, keys, ctrl)

        if confirmed or exited:
            self._selection_i.x = self._selection_i.y = 0
            for channel in self._channels:
                channel.leave()

        return confirmed or exited, self._color if confirmed else None
