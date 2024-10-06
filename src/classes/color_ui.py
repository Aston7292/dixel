"""
Interface for choosing a color
"""

import pygame as pg
from math import ceil
from typing import Final, Optional, Any

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, INPUT_BOX_IMG
from src.classes.text_label import TextLabel

from src.utils import Point, RectPos, Size, ObjInfo, MouseInfo
from src.type_utils import ColorType, BlitSequence, LayeredBlitSequence, LayerSequence
from src.consts import BG_LAYER, ELEMENT_LAYER

SLIDER_1_IMG: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_1_IMG.fill((40, 40, 40))
SLIDER_2_IMG: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_2_IMG.fill((10, 10, 10))


class Scrollbar:
    """
    Class to create a scrollbar to pick an r, g or b value of a color
    """

    __slots__ = (
        '_bar_init_pos', '_unit_w', '_bar_img', 'bar_rect', '_bar_init_size', '_channel', 'value',
        '_slider_init_pos', '_slider_imgs', '_slider_rect', '_slider_init_size',
        '_slider_img_i', '_is_hovering', '_is_scrolling', '_layer', 'input_box', 'objs_info'
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

        self._unit_w: float = 1.0

        self._bar_img: pg.Surface = pg.Surface((int(255.0 * self._unit_w), 25))
        self.bar_rect: pg.FRect = self._bar_img.get_frect(
            **{self._bar_init_pos.coord_type: self._bar_init_pos.xy}
        )

        self._bar_init_size: Size = Size(int(self.bar_rect.w), int(self.bar_rect.h))

        self._channel: int = channel
        self.value: int = color[self._channel]

        self._slider_init_pos: RectPos = RectPos(*self.bar_rect.midleft, 'midleft')
        slider_x: float = self._slider_init_pos.x + self._unit_w * self.value

        self._slider_imgs: tuple[pg.Surface, ...] = (SLIDER_1_IMG, SLIDER_2_IMG)
        self._slider_rect: pg.FRect = self._slider_imgs[0].get_frect(
            **{self._slider_init_pos.coord_type: (slider_x, self._slider_init_pos.y)}
        )

        self._slider_init_size: Size = Size(int(self._slider_rect.w), int(self._slider_rect.h))

        self._slider_img_i: int = 0
        self._is_hovering: bool = False
        self._is_scrolling: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER

        channel_text_label: TextLabel = TextLabel(
            RectPos(*self.bar_rect.midleft, 'midright'), ("r", "g", "b")[self._channel], base_layer
        )
        self.input_box: NumInputBox = NumInputBox(
            RectPos(
                self.bar_rect.right + self._slider_rect.w + 10.0, self.bar_rect.centery, 'midleft'
            ),
            INPUT_BOX_IMG, str(self.value), base_layer
        )

        self.objs_info: list[ObjInfo] = [
            ObjInfo("text", channel_text_label),
            ObjInfo("input box", self.input_box)
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

    def check_hovering(self, mouse_pos: tuple[int, int]) -> tuple[Optional["Scrollbar"], int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object's layer
        """

        is_hovering: bool = (
            self.bar_rect.collidepoint(mouse_pos) or self._slider_rect.collidepoint(mouse_pos)
        )

        return self if is_hovering else None, self._layer

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._slider_img_i = 0
        self._is_hovering = self._is_scrolling = False

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

        self._unit_w = bar_size[0] / 255.0

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
            **{self._slider_init_pos.coord_type: slider_pos}
        )

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [
            (name, None, depth_counter),
            ("bar", self._layer, depth_counter + 1), ("slider", self._layer, depth_counter + 1)
        ]

    def get_bar(self, color: ColorType) -> None:
        """
        Draws a gradient on the bar
        Args:
            color
        """

        blit_sequence: BlitSequence = []

        original_size: tuple[int, int] = self._bar_img.get_size()
        #  Drawing on the normal-sized bar is inaccurate
        self._bar_img = pg.Surface((255, self._bar_init_size.h))
        unit_surf: pg.Surface = pg.Surface((1, self._bar_init_size.h))

        unit_color: list[int] = list(color)
        for i in range(256):
            unit_color[self._channel] = i
            unit_surf.fill(unit_color)
            blit_sequence.append((unit_surf.copy(), (i, 0)))
        self._bar_img.fblits(blit_sequence)

        self._bar_img = pg.transform.scale(self._bar_img, original_size)

    def set_value(self, color: ColorType) -> None:
        """
        Sets the bar on a specif value
        Args:
            color
        """

        self.value = color[self._channel]
        self._slider_rect.x = self.bar_rect.x + self._unit_w * self.value
        self.input_box.set_text(str(self.value), 0)

        self.get_bar(color)

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], selection: Any
    ) -> Optional[int]:
        """
        Allows to pick a value for a channel in a color either with a scrollbar or an input box
        Args:
            hovered object (can be None), mouse info, keys, selection
        Returns:
            clicked object (None = nothing, 0 = scrollbar, 1 = input box)
        """

        if self == hovered_obj and mouse_info.released[0]:
            return 0

        is_input_box_clicked: bool
        new_text: str
        is_input_box_clicked, new_text = self.input_box.upt(
            hovered_obj, mouse_info, keys, (0, 255), selection == self.input_box
        )

        if is_input_box_clicked:
            return 1

        if self != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False

            if not mouse_info.pressed[0]:
                self._is_scrolling = False
        else:
            if not self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
                self._is_hovering = True

            self._is_scrolling = bool(mouse_info.pressed[0])

        self._slider_img_i = 0
        prev_text: str = self.input_box.text_label.text

        new_value: int
        if self._is_scrolling:
            new_value = ceil((mouse_info.x - self.bar_rect.x) / self._unit_w)
            new_value = max(min(new_value, 255), 0)
            new_text = str(new_value)

        if selection == self:
            self._slider_img_i = 1

            if keys:
                new_value = self.value
                if pg.K_LEFT in keys:
                    new_value = max(new_value - 1, 0)
                if pg.K_RIGHT in keys:
                    new_value = min(new_value + 1, 255)
                if pg.K_PAGEDOWN in keys:
                    new_value = max(new_value - 25, 0)
                if pg.K_PAGEUP in keys:
                    new_value = min(new_value + 25, 255)
                if pg.K_HOME in keys:
                    new_value = 0
                if pg.K_END in keys:
                    new_value = 255
                new_text = str(new_value)

        if new_text != prev_text:
            self.value = int(new_text) if new_text else 0
            self._slider_rect.x = self.bar_rect.x + self._unit_w * self.value

            self.input_box.set_text(new_text, None)

        return None


class ColorPicker(UI):
    """
    Class to create an interface that allows picking a color with 3 scrollbars,
    includes a preview
    """

    __slots__ = (
        '_color', '_preview_init_pos', '_preview_img', '_preview_rect', '_preview_init_size',
        '_preview_layer', '_channels', '_objs', '_selection_i', '_hex_text_label'
    )

    def __init__(self, pos: RectPos, color: ColorType) -> None:
        """
        Initializes the interface
        Args:
            position, starting color
        """

        super().__init__(pos, "CHOOSE A COLOR")

        self._color: ColorType = color

        self._preview_init_pos: RectPos = RectPos(*self._rect.center, 'midtop')

        self._preview_img: pg.Surface = pg.Surface((100, 100))
        self._preview_img.fill(self._color)
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord_type: self._preview_init_pos.xy}
        )

        self._preview_init_size: Size = Size(int(self._preview_rect.w), int(self._preview_rect.h))

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        b_bar: Scrollbar = Scrollbar(
            RectPos(self._rect.centerx, self._preview_rect.top - 50.0, 'center'), 2,
            self._color, self._base_layer
        )
        g_bar: Scrollbar = Scrollbar(
            RectPos(self._rect.centerx, b_bar.bar_rect.top - 50.0, 'center'), 1,
            self._color, self._base_layer
        )
        r_bar: Scrollbar = Scrollbar(
            RectPos(self._rect.centerx, g_bar.bar_rect.top - 50.0, 'center'), 0,
            self._color, self._base_layer
        )

        self._channels: tuple[Scrollbar, Scrollbar, Scrollbar] = (r_bar, g_bar, b_bar)
        self._objs: tuple[tuple[Any, ...], ...] = (
            (r_bar, r_bar.input_box), (g_bar, g_bar.input_box), (b_bar, b_bar.input_box)
        )
        self._selection_i: Point = Point(0, 0)

        hex_text: str = "#" + ''.join(f"{channel:02x}" for channel in self._color)
        self._hex_text_label: TextLabel = TextLabel(
            RectPos(*self._preview_rect.midtop, 'midbottom'), hex_text, self._base_layer
        )

        self.objs_info.extend(
            ObjInfo(f"scrollbar {i}", channel) for i, channel in enumerate(self._channels)
        )
        self.objs_info.append(ObjInfo("hex text", self._hex_text_label))

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
            **{self._preview_init_pos.coord_type: preview_pos}
        )

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        sequence: LayerSequence = super().print_layer(name, depth_counter)
        sequence.append(("preview", self._preview_layer, depth_counter + 1))

        return sequence

    def set_color(self, color: ColorType) -> None:
        """
        Sets the UI on a specific color
        Args:
            color
        """

        self._color = color
        self._preview_img.fill(self._color)

        for channel in self._channels:
            channel.set_value(self._color)

        hex_text: str = "#" + ''.join(f"{channel:02x}" for channel in self._color)
        self._hex_text_label.set_text(hex_text)

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], kmod_ctrl: int
    ) -> tuple[bool, Optional[ColorType]]:
        """
        Allows to select a color with 3 scrollbars and view it's preview
        Args:
            hovered object (can be None), mouse info, keys, ctrl
        Returns:
            True if interface was closed else False, color (can be None)
        """

        upt_scrollbars: bool = True
        if keys:
            if pg.K_UP in keys:
                self._selection_i.y = max(self._selection_i.y - 1, 0)
            if pg.K_DOWN in keys:
                self._selection_i.y = min(self._selection_i.y + 1, len(self._objs) - 1)
            if kmod_ctrl:
                prev_selection_x: int = self._selection_i.x
                if pg.K_LEFT in keys:
                    self._selection_i.x = max(self._selection_i.x - 1, 0)
                if pg.K_RIGHT in keys:
                    self._selection_i.x = min(self._selection_i.x + 1, len(self._objs[0]) - 1)

                if self._selection_i.x != prev_selection_x:
                    upt_scrollbars = False

        if upt_scrollbars:
            prev_color: ColorType = self._color
            selection: Any = self._objs[self._selection_i.y][self._selection_i.x]

            for i, channel in enumerate(self._channels):
                new_selection_i: Optional[int] = channel.upt(
                    hovered_obj, mouse_info, keys, selection
                )
                if new_selection_i is not None:
                    self._selection_i.x, self._selection_i.y = new_selection_i, i
            self._color = tuple(channel.value for channel in self._channels)

            if self._color != prev_color:
                for channel in self._channels:
                    channel.get_bar(self._color)
                self._preview_img.fill(self._color)

                hex_text: str = "#" + ''.join(f"{channel:02x}" for channel in self._color)
                self._hex_text_label.set_text(hex_text)

        confirmed: bool
        exited: bool
        confirmed, exited = self._base_upt(hovered_obj, mouse_info, keys, kmod_ctrl)

        return confirmed or exited, self._color if confirmed else None
