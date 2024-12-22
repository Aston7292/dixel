"""Interface for choosing a color."""

from typing import TypeAlias, Final, Optional, Any

import pygame as pg

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI
from src.classes.text_label import TextLabel

from src.utils import Point, RectPos, Ratio, Size, ObjInfo, MouseInfo, resize_obj
from src.type_utils import PosPair, SizePair, Color, LayeredBlitInfo
from src.consts import MOUSE_LEFT, BG_LAYER, ELEMENT_LAYER

SelectionType: TypeAlias = "ColorScrollbar | NumInputBox"
RGBChannels: TypeAlias = tuple["ColorScrollbar", "ColorScrollbar", "ColorScrollbar"]

SLIDER_IMG_OFF: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_IMG_OFF.fill((40, 40, 40))
SLIDER_IMG_ON: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_IMG_ON.fill((10, 10, 10))


class ColorScrollbar:
    """Class to create a scrollbar to pick an r, g or b value of a color."""

    __slots__ = (
        "_bar_init_pos", "_bar_img", "bar_rect", "_bar_init_size", "_channel_i", "value",
        "_slider_init_pos", "_slider_init_imgs", "_slider_imgs", "_slider_rect",
        "_slider_img_i", "_is_hovering", "_is_scrolling", "_layer", "input_box", "objs_info"
    )

    def __init__(
            self, pos: RectPos, channel_i: int, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the bar, slider and text.

        Args:
            position, channel index, base layer (default = BG_LAYER)
        """

        self._bar_init_pos: RectPos = pos

        self._bar_img: pg.Surface
        self.bar_rect: pg.Rect = pg.Rect(0, 0, 255, 25)
        bar_xy: PosPair = (self._bar_init_pos.x, self._bar_init_pos.y)
        setattr(self.bar_rect, self._bar_init_pos.coord_type, bar_xy)

        self._bar_init_size: Size = Size(*self.bar_rect.size)

        self._channel_i: int = channel_i
        self.value: int

        # Not used for resizing slider_x
        self._slider_init_pos: RectPos = RectPos(*self.bar_rect.midleft, "midleft")
        self._slider_init_imgs: tuple[pg.Surface, ...] = (SLIDER_IMG_OFF, SLIDER_IMG_ON)

        self._slider_imgs: tuple[pg.Surface, ...] = self._slider_init_imgs
        slider_xy: PosPair = (self._slider_init_pos.x, self._slider_init_pos.y)
        self._slider_rect: pg.Rect = self._slider_imgs[0].get_rect(
            **{self._slider_init_pos.coord_type: slider_xy}
        )

        self._slider_img_i: int = 0

        self._is_hovering: bool = False
        self._is_scrolling: bool = False
        self._layer: int = base_layer + ELEMENT_LAYER

        input_box_x: int = self.bar_rect.right + self._slider_rect.w + 10

        channel_text_label: TextLabel = TextLabel(
            RectPos(self.bar_rect.x - 10, self.bar_rect.centery, "midright"),
            ("R", "G", "B")[self._channel_i], base_layer
        )
        self.input_box: NumInputBox = NumInputBox(
            RectPos(input_box_x, self.bar_rect.centery, "midleft"), base_layer
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(channel_text_label), ObjInfo(self.input_box)]

    def blit(self) -> list[LayeredBlitInfo]:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._bar_img, self.bar_rect.topleft, self._layer),
            (self._slider_imgs[self._slider_img_i], self._slider_rect.topleft, self._layer)
        ]

    def get_hovering_info(self, mouse_xy: PosPair) -> tuple[bool, int]:
        """
        Gets the hovering info.

        Args:
            mouse position
        Returns:
            True if the object is being hovered else False, hovered object layer
        """

        is_hovering: bool = (
            self.bar_rect.collidepoint(mouse_xy) or self._slider_rect.collidepoint(mouse_xy)
        )

        return is_hovering, self._layer

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

        bar_xy: PosPair
        bar_wh: SizePair
        bar_xy, bar_wh = resize_obj(
            self._bar_init_pos, self._bar_init_size.w, self._bar_init_size.h, win_ratio
        )

        self._bar_img = pg.transform.scale(self._bar_img, bar_wh)
        self.bar_rect = self._bar_img.get_rect(**{self._bar_init_pos.coord_type: bar_xy})

        slider_y: int
        slider_wh: SizePair
        (_, slider_y), slider_wh = resize_obj(
            self._slider_init_pos, *self._slider_init_imgs[0].get_size(), win_ratio
        )

        # Calculating slider_x like this is more accurate
        unit_w: float = bar_wh[0] / 255
        slider_xy: PosPair = (self.bar_rect.x + round(self.value * unit_w), slider_y)

        self._slider_imgs = tuple(
            pg.transform.scale(img, slider_wh) for img in self._slider_init_imgs
        )
        self._slider_rect = self._slider_imgs[0].get_rect(
            **{self._slider_init_pos.coord_type: slider_xy}
        )

    def set_value(self, color: Color, is_external_change: bool) -> None:
        """
        Sets the bar on a specif value.

        Args:
            color, external change flag
        """

        small_bar_img: pg.Surface = pg.Surface((255, 1))  # More accurate
        px_color: list[int] = list(color)
        for i in range(256):
            px_color[self._channel_i] = i
            small_bar_img.set_at((i, 0), px_color)
        self._bar_img = pg.transform.scale(small_bar_img, self.bar_rect.size)

        if is_external_change:
            self.value = color[self._channel_i]
            self.input_box.text_label.set_text(str(self.value))
            self.input_box.bounded_set_cursor_i(0)
        unit_w: float = self.bar_rect.w / 255
        self._slider_rect.x = self.bar_rect.x + round(self.value * unit_w)

    def _handle_hover(self, hovered_obj: Any, mouse_info: MouseInfo) -> None:
        """
        Handles the hovering behavior.

        Args:
            hovered object, mouse info
        """

        if self != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False

            if not mouse_info.pressed[MOUSE_LEFT]:
                self._is_scrolling = False
        else:
            if not self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
                self._is_hovering = True

            self._is_scrolling = mouse_info.pressed[MOUSE_LEFT]

    def _scroll_with_keys(self, keys: list[int]) -> str:
        """
        Scrolls with keys.

        Args:
            keys
        Returns:
            text
        """

        copy_value: int = self.value
        if pg.K_LEFT in keys:
            copy_value = max(copy_value - 1, 0)
        if pg.K_RIGHT in keys:
            copy_value = min(copy_value + 1, 255)
        if pg.K_PAGEDOWN in keys:
            copy_value = max(copy_value - 25, 0)
        if pg.K_PAGEUP in keys:
            copy_value = min(copy_value + 25, 255)
        if pg.K_HOME in keys:
            copy_value = 0
        if pg.K_END in keys:
            copy_value = 255

        return str(copy_value)

    def scroll(self, mouse_info: MouseInfo, keys: list[int], temp_input_box_text: str) -> str:
        """
        Changes the color with mouse and keyboard.

        Args:
            mouse info, keys, input box text
        """

        local_temp_input_box_text: str = temp_input_box_text

        if self._is_scrolling:
            unit_w: float = self.bar_rect.w / 255
            value: int = int((mouse_info.x - self.bar_rect.x) / unit_w)
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
            self.input_box.text_label.set_text(future_input_box_text)
            self.input_box.bounded_set_cursor_i()

        clicked_i: Optional[int] = None
        if self._is_hovering and mouse_info.released[MOUSE_LEFT]:
            clicked_i = 0
        if is_input_box_clicked:
            clicked_i = 1

        return clicked_i


class ColorPicker(UI):
    """Class to create an interface that allows picking a color, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_img", "_preview_rect", "_preview_init_size",
        "_preview_layer", "_channels", "_objs", "_selection_i", "_hex_text_label"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Initializes the interface.

        Args:
            position
        """

        super().__init__(pos, "CHOOSE A COLOR")

        self._preview_init_pos: RectPos = RectPos(*self._rect.center, "midtop")

        self._preview_img: pg.Surface = pg.Surface((100, 100))
        preview_xy: PosPair = (self._preview_init_pos.x, self._preview_init_pos.y)
        self._preview_rect: pg.Rect = self._preview_img.get_rect(
            **{self._preview_init_pos.coord_type: preview_xy}
        )

        self._preview_init_size: Size = Size(*self._preview_rect.size)

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        b_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, self._preview_rect.top - 50, "center"), 2, self._base_layer
        )
        g_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, b_bar.bar_rect.top - 50, "center"), 1, self._base_layer
        )
        r_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, g_bar.bar_rect.top - 50, "center"), 0, self._base_layer
        )

        self._channels: RGBChannels = (r_bar, g_bar, b_bar)
        self._objs: tuple[tuple[ColorScrollbar, NumInputBox], ...] = (
            (r_bar, r_bar.input_box), (g_bar, g_bar.input_box), (b_bar, b_bar.input_box)
        )
        self._selection_i: Point = Point(0, 0)

        self._hex_text_label: TextLabel = TextLabel(
            RectPos(*self._preview_rect.midtop, "midbottom"), "", self._base_layer
        )

        self.objs_info.extend(ObjInfo(channel) for channel in self._channels)
        self.objs_info.append(ObjInfo(self._hex_text_label))

    def blit(self) -> list[LayeredBlitInfo]:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: list[LayeredBlitInfo] = super().blit()
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

        preview_init_wh: SizePair = (self._preview_init_size.w, self._preview_init_size.h)

        preview_xy: PosPair
        preview_wh: SizePair
        preview_xy, preview_wh = resize_obj(self._preview_init_pos, *preview_init_wh, win_ratio)

        self._preview_img = pg.transform.scale(self._preview_img, preview_wh)
        self._preview_rect = self._preview_img.get_rect(
            **{self._preview_init_pos.coord_type: preview_xy}
        )

    def set_color(self, color: Color, is_external_change: bool = True) -> None:
        """
        Sets the UI on a specific color.

        Args:
            color, external change flag (default = True)
        """

        for channel in self._channels:
            channel.set_value(color, is_external_change)
        self._preview_img.fill(color)

        hex_text: str = "#" + "".join(f"{channel:02x}" for channel in color)
        self._hex_text_label.set_text(hex_text)

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
            prev_cursor_x: int = prev_input_box._cursor_rect.x

            input_box: NumInputBox = self._objs[self._selection_i.y][1]
            closest_char_i: int = input_box.text_label.get_closest_to(prev_cursor_x)
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
    ) -> tuple[bool, Optional[Color]]:
        """
        Allows to select a color with 3 scrollbars and view its preview.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            True if interface was closed else False, color (can be None)
        """

        should_upt_scrollbars: bool = True  # Prevents scrolling when changing selection
        if keys:
            should_upt_scrollbars = self._move_with_keys(keys)

        color: Color = tuple(channel.value for channel in self._channels)
        if should_upt_scrollbars:
            prev_color: Color = color
            self._upt_scrollbars(hovered_obj, mouse_info, keys)
            color = tuple(channel.value for channel in self._channels)

            if color != prev_color:
                self.set_color(color, False)

        is_confirming: bool
        is_exiting: bool
        is_confirming, is_exiting = self._base_upt(hovered_obj, mouse_info, keys)

        return is_confirming or is_exiting, color if is_confirming else None
