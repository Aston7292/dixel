"""Interface for choosing a color, scrollbars are refreshed automatically."""

from typing import TypeAlias, Final, Optional

import pygame as pg

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI
from src.classes.text_label import TextLabel

from src.utils import Point, RectPos, ObjInfo, Mouse, Keyboard, resize_obj
from src.type_utils import PosPair, SizePair, Color, LayeredBlitInfo
from src.consts import MOUSE_LEFT, ELEMENT_LAYER, UI_LAYER

SelectionType: TypeAlias = "ColorScrollbar | NumInputBox"
RGBChannels: TypeAlias = tuple["ColorScrollbar", "ColorScrollbar", "ColorScrollbar"]

SLIDER_IMG_OFF: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_IMG_OFF.fill((40, 40, 40))
SLIDER_IMG_ON: Final[pg.Surface] = pg.Surface((10, 35))
SLIDER_IMG_ON.fill((10, 10, 10))


def _scroll_with_keys(timed_keys: list[int], value: int) -> str:
    """
    Scrolls with keys.

    Args:
        timed keys, value
    Returns:
        text
    """

    new_value: int = value
    if pg.K_LEFT in timed_keys:
        new_value = max(new_value - 1, 0)
    if pg.K_RIGHT in timed_keys:
        new_value = min(new_value + 1, 255)
    if pg.K_PAGEDOWN in timed_keys:
        new_value = max(new_value - 25, 0)
    if pg.K_PAGEUP in timed_keys:
        new_value = min(new_value + 25, 255)
    if pg.K_HOME in timed_keys:
        new_value = 0
    if pg.K_END in timed_keys:
        new_value = 255

    return str(new_value)


class ColorScrollbar:
    """Class to create a scrollbar to pick an r, g or b value of a color."""

    __slots__ = (
        "_bar_init_pos", "_bar_img", "bar_rect", "_bar_init_w", "_bar_init_h", "_channel_i",
        "value", "_slider_init_pos", "_slider_imgs", "_slider_rect", "_slider_init_w",
        "_slider_init_h", "_slider_img_i", "_is_scrolling", "layer", "cursor_type", "input_box",
        "objs_info"
    )

    def __init__(self, pos: RectPos, channel_i: int, base_layer: int = UI_LAYER) -> None:
        """
        Creates the bar, slider and text.

        Args:
            position, channel index, base layer (default = UI_LAYER)
        """

        self._bar_init_w: int
        self._bar_init_h: int
        self._slider_init_w: int
        self._slider_init_h: int

        self._bar_init_pos: RectPos = pos

        self._bar_img: pg.Surface
        self.bar_rect: pg.Rect = pg.Rect(0, 0, 255, 25)
        bar_init_xy: PosPair = (self._bar_init_pos.x, self._bar_init_pos.y)
        setattr(self.bar_rect, self._bar_init_pos.coord_type, bar_init_xy)

        self._bar_init_w, self._bar_init_h = self.bar_rect.size

        self._channel_i: int = channel_i
        self.value: int

        self._slider_init_pos: RectPos = RectPos(*self.bar_rect.midright, "midleft")

        self._slider_imgs: list[pg.Surface] = [SLIDER_IMG_OFF, SLIDER_IMG_ON]
        self._slider_rect: pg.Rect = pg.Rect(0, 0, *self._slider_imgs[0].get_size())
        slider_init_xy: PosPair = (self._slider_init_pos.x, self._slider_init_pos.y)
        setattr(self._slider_rect, self._slider_init_pos.coord_type, slider_init_xy)

        self._slider_init_w, self._slider_init_h = self._slider_rect.size

        self._slider_img_i: int = 0
        self._is_scrolling: bool = False

        self.layer: int = base_layer + ELEMENT_LAYER
        self.cursor_type: int = pg.SYSTEM_CURSOR_HAND

        input_box_x: int = self.bar_rect.right + self._slider_rect.w + 10

        channel_text_label: TextLabel = TextLabel(
            RectPos(self.bar_rect.x - 10, self.bar_rect.centery, "midright"),
            ("R", "G", "B")[self._channel_i], base_layer
        )
        self.input_box: NumInputBox = NumInputBox(
            RectPos(input_box_x, self.bar_rect.centery, "midleft"), base_layer
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(channel_text_label), ObjInfo(self.input_box)]

    @property
    def blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._bar_img, self.bar_rect.topleft, self.layer),
            (self._slider_imgs[self._slider_img_i], self._slider_rect.topleft, self.layer)
        ]

    def get_hovering(self, mouse_xy: PosPair) -> bool:
        """
        Gets the hovering flag.

        Args:
            mouse xy
        Returns:
            hovering flag
        """

        return self.bar_rect.collidepoint(mouse_xy) or self._slider_rect.collidepoint(mouse_xy)

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self._slider_img_i = 0
        self._is_scrolling = False

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        bar_xy: PosPair
        bar_wh: SizePair
        _: int
        slider_y: int
        slider_wh: SizePair

        bar_xy, bar_wh = resize_obj(
            self._bar_init_pos, self._bar_init_w, self._bar_init_h, win_w_ratio, win_h_ratio
        )
        self._bar_img = pg.transform.scale(self._bar_img, bar_wh)
        self.bar_rect.size = bar_wh
        setattr(self.bar_rect, self._bar_init_pos.coord_type, bar_xy)

        (_, slider_y), slider_wh = resize_obj(
            self._slider_init_pos, self._slider_init_w, self._slider_init_h,
            win_w_ratio, win_h_ratio
        )

        # More accurate
        unit_w: float = self.bar_rect.w / 255
        slider_xy: PosPair = (self.bar_rect.x + round(self.value * unit_w), slider_y)

        self._slider_imgs = [pg.transform.scale(img, slider_wh) for img in self._slider_imgs]
        self._slider_rect.size = slider_wh
        setattr(self._slider_rect, self._slider_init_pos.coord_type, slider_xy)

    def set_value(self, color: Color, is_external_change: bool) -> None:
        """
        Sets the bar on a specif value.

        Args:
            color, external change flag
        """

        i: int

        if is_external_change:
            self.value = color[self._channel_i]
            self.input_box.text_label.set_text(str(self.value))
            self.input_box.bounded_set_cursor_i(0)

        small_bar_img: pg.Surface = pg.Surface((255, 1))  # More accurate
        px_color: list[int] = color.copy()
        for i in range(256):
            px_color[self._channel_i] = i
            small_bar_img.set_at((i, 0), px_color)
        self._bar_img = pg.transform.scale(small_bar_img, self.bar_rect.size)

        unit_w: float = self.bar_rect.w / 255
        self._slider_rect.x = self.bar_rect.x + round(self.value * unit_w)

    def _scroll(self, mouse_x: int, timed_keys: list[int], input_box_text: str) -> str:
        """
        Changes the color with mouse and keyboard.

        Args:
            mouse x, timed keys, input box text
        """

        new_value: int = self.value
        new_input_box_text: str = input_box_text

        if self._is_scrolling:
            unit_w: float = self.bar_rect.w / 255
            new_value = int((mouse_x - self.bar_rect.x) / unit_w)
            new_value = max(min(new_value, 255), 0)
            new_input_box_text = str(new_value)

        is_selected: bool = self._slider_img_i == 1
        if is_selected and timed_keys:
            new_input_box_text = _scroll_with_keys(timed_keys, new_value)

        return new_input_box_text

    def upt(self, mouse: Mouse, keyboard: Keyboard, selected_obj: SelectionType) -> Optional[int]:
        """
        Allows to pick a value for a channel in a color either with a scrollbar or an input box.

        Args:
            mouse, keyboard, selected object
        Returns:
            clicked object index (None = nothing, 0 = scrollbar, 1 = input box)
        """

        is_input_box_clicked: bool
        new_input_box_text: str

        is_hovering: bool = mouse.hovered_obj == self
        if not mouse.pressed[MOUSE_LEFT]:
            self._is_scrolling = False
        elif is_hovering:
            self._is_scrolling = True
        self._slider_img_i = int(selected_obj == self)

        is_input_box_clicked, new_input_box_text = self.input_box.upt(
            mouse, keyboard, 0, 255, selected_obj == self.input_box
        )
        new_input_box_text = self._scroll(mouse.x, keyboard.timed, new_input_box_text)

        if new_input_box_text != self.input_box.text_label.text:
            self.value = int(new_input_box_text or 0)
            self.input_box.text_label.set_text(new_input_box_text)
            self.input_box.bounded_set_cursor_i(None)

        clicked_i: Optional[int] = None
        if is_hovering and mouse.released[MOUSE_LEFT]:
            clicked_i = 0
        if is_input_box_clicked:
            clicked_i = 1

        return clicked_i


class ColorPicker(UI):
    """Class to create an interface that allows picking a color, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_img", "_preview_rect", "_preview_init_w", "_preview_init_h",
        "_channels", "_objs", "_selection_i", "_hex_text_label"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Initializes the interface.

        Args:
            position
        """

        self._preview_init_w: int
        self._preview_init_h: int

        super().__init__(pos, "CHOOSE A COLOR")

        self._preview_init_pos: RectPos = RectPos(*self._rect.center, "midtop")

        self._preview_img: pg.Surface = pg.Surface((200, 200))
        self._preview_rect: pg.Rect = pg.Rect(0, 0, *self._preview_img.get_size())
        preview_init_xy: PosPair = (self._preview_init_pos.x, self._preview_init_pos.y)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_init_xy)

        self._preview_init_w, self._preview_init_h = self._preview_rect.size

        b_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, self._preview_rect.y - 50, "center"), 2
        )
        g_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, b_bar.bar_rect.y - 50, "center"), 1
        )
        r_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, g_bar.bar_rect.y - 50, "center"), 0
        )

        self._channels: RGBChannels = (r_bar, g_bar, b_bar)
        self._objs: tuple[tuple[ColorScrollbar, NumInputBox], ...] = (
            (r_bar, r_bar.input_box), (g_bar, g_bar.input_box), (b_bar, b_bar.input_box)
        )
        self._selection_i: Point = Point(0, 0)

        self._hex_text_label: TextLabel = TextLabel(
            RectPos(*self._preview_rect.midtop, "midbottom"), "", UI_LAYER
        )

        self.blit_sequence.append((self._preview_img, self._preview_rect.topleft, UI_LAYER))
        self.objs_info.extend([ObjInfo(channel) for channel in self._channels])
        self.objs_info.append(ObjInfo(self._hex_text_label))

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._selection_i.x = self._selection_i.y = 0

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        preview_xy: PosPair
        preview_wh: SizePair

        super().resize(win_w_ratio, win_h_ratio)

        preview_xy, preview_wh = resize_obj(
            self._preview_init_pos, self._preview_init_w, self._preview_init_h,
            win_w_ratio, win_h_ratio
        )
        self._preview_img = pg.transform.scale(self._preview_img, preview_wh)
        self._preview_rect.size = preview_wh
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_xy)

        self.blit_sequence[1] = (self._preview_img, self._preview_rect.topleft, UI_LAYER)

    def set_color(self, color: Color, is_external_change: bool) -> None:
        """
        Sets the UI on a specific color.

        Args:
            color, external change flag
        """

        channel: ColorScrollbar

        for channel in self._channels:
            channel.set_value(color, is_external_change)
        self._preview_img.fill(color)

        hex_text: str = "#{:02x}{:02x}{:02x}".format(*color)
        self._hex_text_label.set_text(hex_text)

        self.blit_sequence[1] = (self._preview_img, self._preview_rect.topleft, UI_LAYER)

    def _move_with_keys(self, keyboard: Keyboard) -> None:
        """
        Moves the selected object with keys.

        Args:
            keyboard
        """

        if pg.K_TAB in keyboard.timed:
            if keyboard.is_shift_on:
                self._selection_i.x = max(self._selection_i.x - 1, 0)
            else:
                self._selection_i.x = min(self._selection_i.x + 1, len(self._objs[0]) - 1)

        prev_selection_i_y: int = self._selection_i.y
        if pg.K_UP in keyboard.timed:
            self._selection_i.y = max(self._selection_i.y - 1, 0)
        if pg.K_DOWN in keyboard.timed:
            self._selection_i.y = min(self._selection_i.y + 1, len(self._objs) - 1)

        if self._selection_i.x == 1 and self._selection_i.y != prev_selection_i_y:
            prev_input_box: NumInputBox = self._objs[prev_selection_i_y][1]
            prev_cursor_x: int = prev_input_box.cursor_x

            input_box: NumInputBox = self._objs[self._selection_i.y][1]
            closest_char_i: int = input_box.text_label.get_closest_to(prev_cursor_x)
            input_box.bounded_set_cursor_i(closest_char_i)

    def _upt_scrollbars(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Updates scrollbars and selection.

        Args:
            mouse, keyboard
        """

        i: int
        channel: ColorScrollbar

        selected_obj: SelectionType = self._objs[self._selection_i.y][self._selection_i.x]
        for i, channel in enumerate(self._channels):
            channel_selection_i: Optional[int] = channel.upt(mouse, keyboard, selected_obj)
            if channel_selection_i is not None:
                self._selection_i.x, self._selection_i.y = channel_selection_i, i

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[bool, bool, Color]:
        """
        Allows to select a color with 3 scrollbars and view its preview.

        Args:
            mouse, keyboard
        Returns:
            exiting flag, confirming flag, color
        """

        is_exiting: bool
        is_confirming: bool

        if keyboard.timed:
            self._move_with_keys(keyboard)

        prev_color: Color = [channel.value for channel in self._channels]
        self._upt_scrollbars(mouse, keyboard)
        color: Color = [channel.value for channel in self._channels]
        if color != prev_color:
            self.set_color(color, False)

        is_exiting, is_confirming = self._base_upt(mouse, keyboard.pressed)

        return is_exiting, is_confirming, color
