"""Interface for choosing a color."""

from typing import Union, Final, Optional, Any

import pygame as pg

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI
from src.classes.text_label import TextLabel

from src.utils import Point, RectPos, Ratio, Size, ObjInfo, MouseInfo, resize_obj
from src.type_utils import ColorType, BlitSequence, LayeredBlitSequence
from src.consts import BG_LAYER, ELEMENT_LAYER

SelectionType = Union["Scrollbar", NumInputBox]

SLIDER_1_IMG: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_1_IMG.fill((40, 40, 40))
SLIDER_2_IMG: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_2_IMG.fill((10, 10, 10))


class Scrollbar:
    """Class to create a scrollbar to pick an r, g or b value of a color."""

    __slots__ = (
        '_bar_init_pos', '_unit_w', '_bar_img', 'bar_rect', '_bar_init_size', '_channel', 'value',
        '_slider_init_pos', '_slider_init_imgs', '_slider_imgs', '_slider_rect',
        '_slider_img_i', '_is_hovering', '_is_scrolling', '_layer', 'input_box', 'objs_info'
    )

    def __init__(
            self, pos: RectPos, channel: int, color: ColorType, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the bar, slider and text.

        Args:
            position, channel, starting color, base layer (default = BG_LAYER)
        """

        self._bar_init_pos: RectPos = pos

        self._unit_w: float = 1.0

        self._bar_img: pg.Surface = pg.Surface((round(255.0 * self._unit_w), 25))
        self.bar_rect: pg.Rect = self._bar_img.get_rect(
            **{self._bar_init_pos.coord_type: (self._bar_init_pos.x, self._bar_init_pos.y)}
        )

        self._bar_init_size: Size = Size(*self.bar_rect.size)

        self._channel: int = channel
        self.value: int = color[self._channel]

        self._slider_init_pos: RectPos = RectPos(*self.bar_rect.midleft, 'midleft')
        self._slider_init_imgs: tuple[pg.Surface, ...] = (SLIDER_1_IMG, SLIDER_2_IMG)
        slider_x: int = self._slider_init_pos.x + round(self.value * self._unit_w)

        self._slider_imgs: tuple[pg.Surface, ...] = self._slider_init_imgs
        self._slider_rect: pg.Rect = self._slider_imgs[0].get_rect(
            **{self._slider_init_pos.coord_type: (slider_x, self._slider_init_pos.y)}
        )

        self._slider_img_i: int = 0
        self._is_hovering: bool = False
        self._is_scrolling: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER

        input_box_x: int = self.bar_rect.right + self._slider_rect.w + 10

        channel_text_label: TextLabel = TextLabel(
            RectPos(*self.bar_rect.midleft, 'midright'), ("r", "g", "b")[self._channel], base_layer
        )
        self.input_box: NumInputBox = NumInputBox(
            RectPos(input_box_x, self.bar_rect.centery, 'midleft'), str(self.value), base_layer
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(channel_text_label), ObjInfo(self.input_box)]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._bar_img, self.bar_rect.topleft, self._layer),
            (self._slider_imgs[self._slider_img_i], self._slider_rect.topleft, self._layer)
        ]

    def check_hovering(self, mouse_xy: tuple[int, int]) -> tuple[Optional["Scrollbar"], int]:
        """
        Checks if the mouse is hovering any interactable part of the object.

        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object layer
        """

        is_hovering: bool = (
            self.bar_rect.collidepoint(mouse_xy) or self._slider_rect.collidepoint(mouse_xy)
        )

        return self if is_hovering else None, self._layer

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self._slider_img_i = 0
        self._is_hovering = self._is_scrolling = False

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        bar_xy: tuple[int, int]
        bar_wh: tuple[int, int]
        bar_xy, bar_wh = resize_obj(
            self._bar_init_pos, self._bar_init_size.w, self._bar_init_size.h, win_ratio
        )

        self._unit_w = bar_wh[0] / 255.0

        self._bar_img = pg.transform.scale(self._bar_img, bar_wh)
        self.bar_rect = self._bar_img.get_rect(**{self._bar_init_pos.coord_type: bar_xy})

        slider_y: int
        slider_wh: tuple[int, int]
        (_, slider_y), slider_wh = resize_obj(
            self._slider_init_pos, *self._slider_init_imgs[0].get_size(), win_ratio
        )

        # Calculating slider_x like this is more accurate
        slider_xy: tuple[int, int] = (
            self.bar_rect.x + round(self.value * self._unit_w), slider_y
        )

        self._slider_imgs = tuple(
            pg.transform.scale(img, slider_wh) for img in self._slider_init_imgs
        )
        self._slider_rect = self._slider_imgs[0].get_rect(
            **{self._slider_init_pos.coord_type: slider_xy}
        )

    def set_bar(self, color: ColorType) -> None:
        """
        Draws a gradient on the bar.

        Args:
            color
        """

        blit_sequence: BlitSequence = []

        bar_wh: tuple[int, int] = self._bar_img.get_size()
        self._bar_img = pg.Surface((255, self._bar_init_size.h))  # A smaller one is more accurate
        unit_img: pg.Surface = pg.Surface((1, self._bar_init_size.h))

        unit_color: list[int] = list(color)
        for i in range(256):
            unit_color[self._channel] = i
            unit_img.fill(unit_color)
            blit_sequence.append((unit_img.copy(), (i, 0)))
        self._bar_img.fblits(blit_sequence)

        self._bar_img = pg.transform.scale(self._bar_img, bar_wh)

    def set_value(self, color: ColorType) -> None:
        """
        Sets the bar on a specif value.

        Args:
            color
        """

        self.value = color[self._channel]
        self._slider_rect.x = self.bar_rect.x + round(self.value * self._unit_w)
        self.input_box.text_label.set_text(str(self.value))
        self.input_box.bounded_set_cursor_i(0)

    def _handle_hover(self, hovered_obj: Any, mouse_info: MouseInfo) -> None:
        """
        Handles hovering behavior.

        Args:
            hovered object, mouse info
        """

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

            self._is_scrolling = mouse_info.pressed[0]

    def _scroll_with_keys(self, keys: list[int]) -> str:
        """
        Scrolls with keys.

        Args:
            keys
        Returns:
            text
        """

        local_value: int = self.value
        if pg.K_LEFT in keys:
            local_value = max(local_value - 1, 0)
        if pg.K_RIGHT in keys:
            local_value = min(local_value + 1, 255)
        if pg.K_PAGEDOWN in keys:
            local_value = max(local_value - 25, 0)
        if pg.K_PAGEUP in keys:
            local_value = min(local_value + 25, 255)
        if pg.K_HOME in keys:
            local_value = 0
        if pg.K_END in keys:
            local_value = 255

        return str(local_value)

    def scroll(self, mouse_info: MouseInfo, keys: list[int], temp_input_box_text: str) -> str:
        """
        Changes the color with mouse and keyboard.

        Args:
            mouse info, keys, input box text
        """

        local_temp_input_box_text: str = temp_input_box_text

        if self._is_scrolling:
            value: int = int((mouse_info.x - self.bar_rect.x) / self._unit_w)
            value = max(min(value, 255), 0)
            local_temp_input_box_text = str(value)

        is_selected: bool = self._slider_img_i == 1
        if is_selected and keys:
            local_temp_input_box_text = self._scroll_with_keys(keys)

        return local_temp_input_box_text

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int],
            selection: SelectionType
    ) -> Optional[int]:
        """
        Allows to pick a value for a channel in a color either with a scrollbar or an input box.

        Args:
            hovered object (can be None), mouse info, keys, selected object
        Returns:
            clicked object index (None = nothing, 0 = scrollbar, 1 = input box)
        """

        self._handle_hover(hovered_obj, mouse_info)
        self._slider_img_i = int(selection == self)

        is_input_box_clicked: bool
        temp_input_box_text: str
        is_input_box_clicked, temp_input_box_text = self.input_box.upt(
            hovered_obj, mouse_info, keys, (0, 255), selection == self.input_box
        )

        future_input_box_text: str = self.scroll(mouse_info, keys, temp_input_box_text)
        if self.input_box.text_label.text != future_input_box_text:
            self.value = int(future_input_box_text or 0)
            self._slider_rect.x = self.bar_rect.x + round(self.value * self._unit_w)
            self.input_box.text_label.set_text(future_input_box_text)
            self.input_box.bounded_set_cursor_i()

        clicked_i: Optional[int] = None
        if self == hovered_obj and mouse_info.released[0]:
            clicked_i = 0
        if is_input_box_clicked:
            clicked_i = 1

        return clicked_i


class ColorPicker(UI):
    """Class to create an interface that allows picking a color, has a preview."""

    __slots__ = (
        '_color', '_preview_init_pos', '_preview_img', '_preview_rect', '_preview_init_size',
        '_preview_layer', '_channels', '_objs', '_selection_i', '_hex_text_label'
    )

    def __init__(self, pos: RectPos, color: ColorType) -> None:
        """
        Initializes the interface.

        Args:
            position, starting color
        """

        super().__init__(pos, "CHOOSE A COLOR")

        self._color: ColorType = color

        self._preview_init_pos: RectPos = RectPos(*self._rect.center, 'midtop')

        self._preview_img: pg.Surface = pg.Surface((100, 100))
        self._preview_img.fill(self._color)
        preview_xy: tuple[int, int] = (self._preview_init_pos.x, self._preview_init_pos.y)
        self._preview_rect: pg.Rect = self._preview_img.get_rect(
            **{self._preview_init_pos.coord_type: preview_xy}
        )

        self._preview_init_size: Size = Size(*self._preview_rect.size)

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        b_bar: Scrollbar = Scrollbar(
            RectPos(self._rect.centerx, self._preview_rect.top - 50, 'center'), 2,
            self._color, self._base_layer
        )
        g_bar: Scrollbar = Scrollbar(
            RectPos(self._rect.centerx, b_bar.bar_rect.top - 50, 'center'), 1,
            self._color, self._base_layer
        )
        r_bar: Scrollbar = Scrollbar(
            RectPos(self._rect.centerx, g_bar.bar_rect.top - 50, 'center'), 0,
            self._color, self._base_layer
        )

        self._channels: tuple[Scrollbar, Scrollbar, Scrollbar] = (r_bar, g_bar, b_bar)
        self._objs: tuple[tuple[Scrollbar, NumInputBox], ...] = (
            (r_bar, r_bar.input_box), (g_bar, g_bar.input_box), (b_bar, b_bar.input_box)
        )
        self._selection_i: Point = Point(0, 0)

        hex_text: str = "#" + ''.join(f"{channel:02x}" for channel in self._color)
        self._hex_text_label: TextLabel = TextLabel(
            RectPos(*self._preview_rect.midtop, 'midbottom'), hex_text, self._base_layer
        )

        self.objs_info.extend(ObjInfo(channel) for channel in self._channels)
        self.objs_info.append(ObjInfo(self._hex_text_label))

    def blit(self) -> LayeredBlitSequence:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = super().blit()
        sequence.append((self._preview_img, self._preview_rect.topleft, self._preview_layer))

        return sequence

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self._selection_i.x = self._selection_i.y = 0

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        super().resize(win_ratio)

        preview_init_wh: tuple[int, int] = (self._preview_init_size.w, self._preview_init_size.h)

        preview_xy: tuple[int, int]
        preview_wh: tuple[int, int]
        preview_xy, preview_wh = resize_obj(self._preview_init_pos, *preview_init_wh, win_ratio)

        self._preview_img = pg.transform.scale(self._preview_img, preview_wh)
        self._preview_rect = self._preview_img.get_rect(
            **{self._preview_init_pos.coord_type: preview_xy}
        )

    def _upt_info(self) -> None:
        """Updates the scrollbars, preview and hex text with the current color."""

        for channel in self._channels:
            channel.set_bar(self._color)
        self._preview_img.fill(self._color)

        hex_text: str = "#" + ''.join(f"{channel:02x}" for channel in self._color)
        self._hex_text_label.set_text(hex_text)

    def set_color(self, color: ColorType) -> None:
        """
        Sets the UI on a specific color.

        Args:
            color
        """

        self._color = color

        for channel in self._channels:
            channel.set_value(self._color)
        self._upt_info()

    def _move_with_keys(self, keys: list[int]) -> bool:
        """
        Moves the selected object with keys.

        Args:
            keys
        Returns:
            True if the scrollbars should be updated else False
        """

        prev_selection_i_x: int = self._selection_i.x
        if (pg.key.get_mods() & pg.KMOD_CTRL) and (pg.key.get_mods() & pg.KMOD_SHIFT):
            if pg.K_LEFT in keys:
                self._selection_i.x = max(self._selection_i.x - 1, 0)
            if pg.K_RIGHT in keys:
                self._selection_i.x = min(self._selection_i.x + 1, len(self._objs[0]) - 1)

        prev_selection_i_y: int = self._selection_i.y
        if pg.K_UP in keys:
            self._selection_i.y = max(self._selection_i.y - 1, 0)
        if pg.K_DOWN in keys:
            self._selection_i.y = min(self._selection_i.y + 1, len(self._objs) - 1)

        if self._selection_i.y != prev_selection_i_y and self._selection_i.x == 1:
            prev_input_box: NumInputBox = self._objs[prev_selection_i_y][1]
            cursor_x: int = prev_input_box._cursor_rect.x

            input_box: NumInputBox = self._objs[self._selection_i.y][1]
            closest_char_i: int = input_box.text_label.get_closest_to(cursor_x)
            input_box.bounded_set_cursor_i(closest_char_i)

        return self._selection_i.x == prev_selection_i_x

    def _upt_scrollbars(self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]) -> None:
        """
        Updates scrollbars and selection.

        Args:
            hovered object, mouse info, keys
        """

        selection: SelectionType = self._objs[self._selection_i.y][self._selection_i.x]
        for i, channel in enumerate(self._channels):
            channel_selection_i: Optional[int] = channel.upt(
                hovered_obj, mouse_info, keys, selection
            )
            if channel_selection_i is not None:
                self._selection_i.x, self._selection_i.y = channel_selection_i, i

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]
    ) -> tuple[bool, Optional[ColorType]]:
        """
        Allows to select a color with 3 scrollbars and view its preview.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            True if interface was closed else False, color (can be None)
        """

        upt_scrollbars: bool = True  # Prevents movement when moving the selection horizontally
        if keys:
            upt_scrollbars = self._move_with_keys(keys)

        if upt_scrollbars:
            prev_color: ColorType = self._color
            self._upt_scrollbars(hovered_obj, mouse_info, keys)
            self._color = tuple(channel.value for channel in self._channels)

            if self._color != prev_color:
                self._upt_info()

        confirmed: bool
        exited: bool
        confirmed, exited = self._base_upt(hovered_obj, mouse_info, keys)

        return confirmed or exited, self._color if confirmed else None
