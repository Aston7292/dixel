"""
Interface for choosing a color
"""

import pygame as pg
from math import ceil
from typing import Final, Optional, Any

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, INPUT_BOX
from src.classes.text import Text
from src.utils import Point, RectPos, Size, ObjInfo, MouseInfo
from src.type_utils import ColorType, BlitSequence, LayeredBlitSequence, LayerSequence

from src.consts import BG_LAYER, ELEMENT_LAYER

SLIDER_1: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_1.fill((40, 40, 40))
SLIDER_2: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_2.fill((10, 10, 10))


class ScrollBar:
    """
    Class to create a scroll bar to pick an r, g or b value of a color
    """

    __slots__ = (
        '_bar_init_pos', '_channel', '_unit_w', '_bar_img', 'bar_rect', '_bar_init_size',
        'value', '_slider_init_pos', '_slider_imgs', '_slider_rect', '_slider_init_size',
        '_slider_img_i', '_hovering', '_scrolling', '_layer', 'value_input_box', 'objs_info'
    )

    def __init__(
            self, pos: RectPos, channel: int, color: ColorType, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the bar, slider and text
        Args:
            position, channel, starting color, base layer (default = BG_LAYER)
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
        self._slider_imgs: tuple[pg.Surface, ...] = (SLIDER_1, SLIDER_2)
        self._slider_rect: pg.FRect = self._slider_imgs[0].get_frect(
            **{self._slider_init_pos.coord: (slider_x, self._slider_init_pos.y)}
        )

        self._slider_init_size: Size = Size(int(self._slider_rect.w), int(self._slider_rect.h))

        self._slider_img_i: int = 0
        self._hovering: bool = False
        self._scrolling: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER

        channel_text: Text = Text(
            RectPos(*self.bar_rect.midleft, 'midright'), ('r', 'g', 'b')[self._channel], base_layer
        )
        self.value_input_box: NumInputBox = NumInputBox(
            RectPos(
                self.bar_rect.right + self._slider_rect.w + 10.0, self.bar_rect.centery, 'midleft'
            ), INPUT_BOX, str(self.value), base_layer
        )

        self.objs_info: list[ObjInfo] = [
            ObjInfo('text', channel_text),
            ObjInfo('input box', self.value_input_box)
        ]

        self.get_bar(color)

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._bar_img, self.bar_rect.topleft, self._layer),
            (self._slider_imgs[self._slider_img_i], self._slider_rect.topleft, self._layer)
        ]

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object's layer
        """

        hovering: bool = (
            self.bar_rect.collidepoint(mouse_pos) or self._slider_rect.collidepoint(mouse_pos)
        )

        return self if hovering else None, self._layer

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._slider_img_i = 0
        self._hovering = self._scrolling = False

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
        Args:
            window width ratio, window height ratio
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

        self._slider_imgs = tuple(
            pg.transform.scale(img, slider_size) for img in self._slider_imgs
        )
        self._slider_rect = self._slider_imgs[0].get_frect(
            **{self._slider_init_pos.coord: slider_pos}
        )

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [
            (name, -1, depth_counter),
            ('bar', self._layer, depth_counter + 1), ('slider', self._layer, depth_counter + 1)
        ]

    def get_bar(self, color: ColorType) -> None:
        """
        Draws a gradient on the bar
        Args:
            color
        """

        sequence: BlitSequence = []

        original_size: tuple[int, int] = self._bar_img.get_size()
        #  Drawing on the normal-sized bar is inaccurate
        self._bar_img = pg.Surface((255, self._bar_init_size.h))
        sect_surf: pg.Surface = pg.Surface((1, self._bar_init_size.h))

        current_color: list[int] = list(color)
        for i in range(256):
            current_color[self._channel] = i
            sect_surf.fill(current_color)
            sequence.append((sect_surf.copy(), (i, 0)))
        self._bar_img.fblits(sequence)

        self._bar_img = pg.transform.scale(self._bar_img, original_size)

    def set_value(self, color: ColorType) -> None:
        """
        Sets the bar on a specif value
        Args:
            color
        """

        self.value = color[self._channel]
        self._slider_rect.x = self.bar_rect.x + self._unit_w * self.value
        self.value_input_box.set_text(str(self.value), 0)

        self.get_bar(color)

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], selection: Any
    ) -> int:
        """
        Allows to pick a value for a channel in a color either with a scroll bar or an input box
        Args:
            hovered object (can be None), mouse info, keys, selection
        Returns:
            licked object (-1 = nothing, 0 = scroll bar, 1 = input box)
        """

        if self == hover_obj and mouse_info.released[0]:
            return 0

        clicked: bool
        text: str
        clicked, text = self.value_input_box.upt(
            hover_obj, mouse_info, keys, (0, 255), selection == self.value_input_box
        )

        if clicked:
            return 1

        if self != hover_obj:
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False

            if not mouse_info.buttons[0]:
                self._scrolling = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
                self._hovering = True

            self._scrolling = bool(mouse_info.buttons[0])

        self._slider_img_i = 0
        prev_text: str = self.value_input_box.text.text

        value: int
        if self._scrolling:
            value = ceil((mouse_info.x - self.bar_rect.x) / self._unit_w)
            value = max(min(value, 255), 0)
            text = str(value)

        if selection == self:
            self._slider_img_i = 1

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

            self.value_input_box.set_text(text)

        return -1


class ColorPicker(UI):
    """
    Class to create an interface that allows picking a color with 3 scroll bars,
    includes a preview
    """

    __slots__ = (
        '_color', '_preview_init_pos', '_preview_img', '_preview_rect', '_preview_init_size',
        '_preview_layer', '_channels', '_objs', '_selection_i', '_hex_text'
    )

    def __init__(self, pos: RectPos, color: ColorType) -> None:
        """
        Initializes the interface
        Args:
            position, starting color
        """

        super().__init__(pos, 'CHOOSE A COLOR')

        self._color: ColorType = color

        self._preview_init_pos: RectPos = RectPos(*self._rect.center, 'midtop')

        self._preview_img: pg.Surface = pg.Surface((100, 100))
        self._preview_img.fill(self._color)
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: self._preview_init_pos.xy}
        )

        self._preview_init_size: Size = Size(int(self._preview_rect.w), int(self._preview_rect.h))

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        b: ScrollBar = ScrollBar(
            RectPos(self._rect.centerx, self._preview_rect.top - 50.0, 'center'), 2,
            self._color, self._base_layer
        )
        g: ScrollBar = ScrollBar(
            RectPos(self._rect.centerx, b.bar_rect.top - 50.0, 'center'), 1,
            self._color, self._base_layer
        )
        r: ScrollBar = ScrollBar(
            RectPos(self._rect.centerx, g.bar_rect.top - 50.0, 'center'), 0,
            self._color, self._base_layer
        )

        self._channels: tuple[ScrollBar, ...] = (r, g, b)
        self._objs: tuple[tuple[Any, ...], ...] = (
            (r, r.value_input_box), (g, g.value_input_box), (b, b.value_input_box)
        )
        self._selection_i: Point = Point(0, 0)

        hex_string: str = '#' + ''.join(f'{channel:02x}' for channel in self._color)
        self._hex_text: Text = Text(
            RectPos(*self._preview_rect.midtop, 'midbottom'), hex_string, self._base_layer
        )

        self.objs_info.extend(
            ObjInfo(f'scroll bar {i}', channel) for i, channel in enumerate(self._channels)
        )
        self.objs_info.append(ObjInfo('hex text', self._hex_text))

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = super().blit()
        sequence.append((self._preview_img, self._preview_rect.topleft, self._preview_layer))

        return sequence

    def _leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._selection_i.x = self._selection_i.y = 0

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
        Args:
            window width ratio, window height ratio
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

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        sequence: LayerSequence = super().print_layer(name, depth_counter)
        sequence.append(('preview', self._preview_layer, depth_counter + 1))

        return sequence

    def set_color(self, color: ColorType) -> None:
        """
        Sets the ui on a specific color
        Args:
            color
        """

        self._color = color
        self._preview_img.fill(self._color)

        for channel in self._channels:
            channel.set_value(self._color)

        hex_string: str = '#' + ''.join(f'{channel:02x}' for channel in self._color)
        self._hex_text.set_text(hex_string)

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], ctrl: int
    ) -> tuple[bool, Optional[ColorType]]:
        """
        Allows to select a color with 3 scroll bars and view it's preview
        Args:
            hovered object (can be None), mouse info, keys, ctrl
        Returns:
            True if interface was closed else False, color (can be None)
        """

        scroll_bar_keys: tuple[int, ...] = keys  # Cleared when switching selection horizontally
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
                    scroll_bar_keys = ()

        prev_color: ColorType = self._color
        selection: Any = self._objs[self._selection_i.y][self._selection_i.x]

        for i, channel in enumerate(self._channels):
            selection_i: int = channel.upt(hover_obj, mouse_info, scroll_bar_keys, selection)
            if selection_i != -1:
                self._selection_i.x, self._selection_i.y = selection_i, i
        self._color = tuple(channel.value for channel in self._channels)

        if self._color != prev_color:
            for channel in self._channels:
                channel.get_bar(self._color)
            self._preview_img.fill(self._color)

            hex_string: str = '#' + ''.join(f'{channel:02x}' for channel in self._color)
            self._hex_text.set_text(hex_string)

        confirmed: bool
        exited: bool
        confirmed, exited = self._base_upt(hover_obj, mouse_info, keys, ctrl)

        return confirmed or exited, self._color if confirmed else None
