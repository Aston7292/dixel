"""Interface for choosing a color, color is refreshed automatically."""

from typing import TypeAlias, Final, Optional

import pygame as pg
from pygame.locals import *

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI
from src.classes.text_label import TextLabel

from src.utils import Point, RectPos, ObjInfo, Mouse, Keyboard, resize_obj
from src.type_utils import XY, WH, RGBColor, HexColor, LayeredBlitInfo
from src.consts import MOUSE_LEFT, BLACK, ELEMENT_LAYER, UI_LAYER

Selection: TypeAlias = "ColorScrollbar | NumInputBox"

MIN_RGB: Final[int] = 0
MAX_RGB: Final[int] = 256
SLIDER_IMG_OFF: Final[pg.Surface] = pg.Surface((10, 32)).convert()
SLIDER_IMG_OFF.fill((25, 25, 25))
SLIDER_IMG_ON: Final[pg.Surface] = SLIDER_IMG_OFF.copy()
SLIDER_IMG_ON.fill(BLACK)


class ColorScrollbar:
    """Class to create a scrollbar to pick an r, g or b value of a color."""

    __slots__ = (
        "_bar_init_pos", "_bar_img", "bar_rect", "_bar_init_w", "_bar_init_h", "_channel_i",
        "value", "_slider_init_pos", "_slider_imgs", "_slider_rect", "_slider_init_w",
        "_slider_init_h", "_slider_img_i", "_is_scrolling", "layer", "input_box", "objs_info"
    )

    cursor_type: int = SYSTEM_CURSOR_HAND

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

        self._bar_img: pg.Surface = pg.Surface((MAX_RGB, 25)).convert()
        self.bar_rect: pg.Rect = pg.Rect(0, 0, *self._bar_img.get_size())
        bar_init_xy: XY = (self._bar_init_pos.x, self._bar_init_pos.y)
        setattr(self.bar_rect, self._bar_init_pos.coord_type, bar_init_xy)

        self._bar_init_w, self._bar_init_h = self.bar_rect.size

        self._channel_i: int = channel_i
        self.value: int = 0

        self._slider_init_pos: RectPos = RectPos(
            self.bar_rect.right, self.bar_rect.centery, "midleft"
        )

        self._slider_imgs: list[pg.Surface] = [SLIDER_IMG_OFF, SLIDER_IMG_ON]
        self._slider_rect: pg.Rect = pg.Rect(0, 0, *self._slider_imgs[0].get_size())
        slider_init_xy: XY = (self._slider_init_pos.x, self._slider_init_pos.y)
        setattr(self._slider_rect, self._slider_init_pos.coord_type, slider_init_xy)

        self._slider_init_w, self._slider_init_h = self._slider_rect.size

        self._slider_img_i: int = 0
        self._is_scrolling: bool = False

        self.layer: int = base_layer + ELEMENT_LAYER

        input_box_x: int = self.bar_rect.right + self._slider_rect.w + 5

        channel_text_label: TextLabel = TextLabel(
            RectPos(self.bar_rect.x - 5, self.bar_rect.centery, "midright"),
            ("R", "G", "B")[self._channel_i], base_layer
        )
        self.input_box: NumInputBox = NumInputBox(
            RectPos(input_box_x, self.bar_rect.centery, "midleft"),
            MIN_RGB, MAX_RGB - 1, base_layer
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
            (self._bar_img, self.bar_rect, self.layer),
            (self._slider_imgs[self._slider_img_i], self._slider_rect, self.layer)
        ]

    def get_hovering(self, mouse_xy: XY) -> bool:
        """
        Gets the hovering flag.

        Args:
            mouse xy
        Returns:
            hovering flag
        """

        return self.bar_rect.collidepoint(mouse_xy) or self._slider_rect.collidepoint(mouse_xy)

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._slider_img_i = 0
        self._is_scrolling = False

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        bar_xy: XY
        bar_wh: WH
        _slider_x: int
        slider_y: int
        slider_wh: WH

        bar_xy, bar_wh = resize_obj(
            self._bar_init_pos, self._bar_init_w, self._bar_init_h, win_w_ratio, win_h_ratio
        )
        self._bar_img = pg.transform.scale(self._bar_img, bar_wh).convert()
        self.bar_rect.size = bar_wh
        setattr(self.bar_rect, self._bar_init_pos.coord_type, bar_xy)

        (_slider_x, slider_y), slider_wh = resize_obj(
            self._slider_init_pos, self._slider_init_w, self._slider_init_h,
            win_w_ratio, win_h_ratio
        )

        # More accurate
        unit_w: float = self.bar_rect.w / MAX_RGB
        slider_xy: XY = (self.bar_rect.x + round(self.value * unit_w), slider_y)

        self._slider_imgs = [
            pg.transform.scale(img, slider_wh).convert() for img in self._slider_imgs
        ]
        self._slider_rect.size = slider_wh
        setattr(self._slider_rect, self._slider_init_pos.coord_type, slider_xy)

    def set_value(self, color: pg.Color, is_external_change: bool) -> None:
        """
        Sets the bar on a specif value, modifies the original color.

        Args:
            color, external change flag
        """

        value: int

        if is_external_change:
            self.value = color[self._channel_i]
            self.input_box.text_label.set_text(str(self.value))
            self.input_box.bounded_set_cursor_i(0)

        small_bar_img: pg.Surface = pg.Surface((MAX_RGB, 1))  # More accurate
        px_color: pg.Color = pg.Color(color)
        small_bar_img.lock()
        for value in range(MAX_RGB):
            px_color[self._channel_i] = value
            small_bar_img.set_at((value, 0), px_color)
        small_bar_img.unlock()

        self._bar_img = pg.transform.scale(small_bar_img, self.bar_rect.size).convert()
        unit_w: float = self.bar_rect.w / MAX_RGB
        self._slider_rect.x = self.bar_rect.x + round(self.value * unit_w)

    def _scroll(self, mouse_x: int) -> None:
        """
        Changes the color with the mouse.

        Args:
            mouse x
        """

        unit_w: float = self.bar_rect.w / MAX_RGB
        self.value = int((mouse_x - self.bar_rect.x) / unit_w)
        self.value = min(max(self.value, MIN_RGB), MAX_RGB - 1)
        self.input_box.text_label.text = str(self.value)

    def _scroll_with_keys(self, timed_keys: list[int]) -> None:
        """
        Changes the color with the keyboard.

        Args:
            timed keys
        """

        if K_LEFT in timed_keys:
            self.value = max(self.value - 1, MIN_RGB)
            self.input_box.text_label.text = str(self.value)
        if K_RIGHT in timed_keys:
            self.value = min(self.value + 1, MAX_RGB - 1)
            self.input_box.text_label.text = str(self.value)
        if K_PAGEDOWN in timed_keys:
            self.value = max(self.value - 25, MIN_RGB)
            self.input_box.text_label.text = str(self.value)
        if K_PAGEUP in timed_keys:
            self.value = min(self.value + 25, MAX_RGB - 1)
            self.input_box.text_label.text = str(self.value)
        if K_HOME in timed_keys:
            self.value = MIN_RGB
            self.input_box.text_label.text = str(self.value)
        if K_END in timed_keys:
            self.value = MAX_RGB - 1
            self.input_box.text_label.text = str(self.value)

    def upt(self, mouse: Mouse, keyboard: Keyboard, selected_obj: Selection) -> Optional[int]:
        """
        Allows to pick a value for a channel in a color either with a scrollbar or an input box.

        Args:
            mouse, keyboard, selected object
        Returns:
            clicked object index (None = nothing, 0 = scrollbar, 1 = input box)
        """

        clicked_i: Optional[int] = None
        if not mouse.pressed[MOUSE_LEFT]:
            self._is_scrolling = False
        elif mouse.hovered_obj == self:
            self._is_scrolling = True
            clicked_i = 0
            selected_obj = self
        self._slider_img_i = int(selected_obj == self)

        prev_input_box_text: str = self.input_box.text_label.text

        if self._is_scrolling:
            self._scroll(mouse.x)
        if selected_obj == self and keyboard.timed != []:
            self._scroll_with_keys(keyboard.timed)
        is_input_box_clicked: bool = self.input_box.upt(
            mouse, keyboard, selected_obj, prev_input_box_text
        )

        self.value = int(self.input_box.text_label.text or MIN_RGB)
        if is_input_box_clicked:
            clicked_i = 1
            selected_obj = self.input_box

        return clicked_i


class ColorPicker(UI):
    """Class to create an interface that allows picking a color, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_img", "_preview_rect", "_preview_init_w", "_preview_init_h",
        "_hex_text_label", "_b_bar", "_g_bar", "_r_bar", "_objs", "_selection_i"
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

        self._preview_init_pos: RectPos = RectPos(self._rect.centerx, self._rect.centery, "midtop")

        self._preview_img: pg.Surface = pg.Surface((256, 256)).convert()
        self._preview_rect: pg.Rect = pg.Rect(0, 0, *self._preview_img.get_size())
        preview_init_xy: XY = (self._preview_init_pos.x, self._preview_init_pos.y)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_init_xy)

        self._preview_init_w, self._preview_init_h = self._preview_rect.size

        self._hex_text_label: TextLabel = TextLabel(
            RectPos(self._preview_rect.centerx, self._preview_rect.y - 25, "midbottom"),
            "#000000", UI_LAYER
        )

        self._b_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, self._hex_text_label.rect.y - 50, "center"),
            2
        )
        self._g_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, self._b_bar.bar_rect.y - 50, "center"),
            1
        )
        self._r_bar: ColorScrollbar = ColorScrollbar(
            RectPos(self._rect.centerx, self._g_bar.bar_rect.y - 50, "center"),
            0
        )

        self._objs: tuple[tuple[ColorScrollbar, NumInputBox], ...] = (
            (self._r_bar, self._r_bar.input_box),
            (self._g_bar, self._g_bar.input_box),
            (self._b_bar, self._b_bar.input_box)
        )
        self._selection_i: Point = Point(0, 0)

        self.blit_sequence.append((self._preview_img, self._preview_rect, UI_LAYER))
        self.objs_info.append(ObjInfo(self._hex_text_label))
        self.objs_info.append(ObjInfo(self._r_bar))
        self.objs_info.append(ObjInfo(self._b_bar))
        self.objs_info.append(ObjInfo(self._g_bar))

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._selection_i.x = self._selection_i.y = 0

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        preview_xy: XY
        preview_wh: WH

        super().resize(win_w_ratio, win_h_ratio)

        preview_xy, preview_wh = resize_obj(
            self._preview_init_pos, self._preview_init_w, self._preview_init_h,
            win_w_ratio, win_h_ratio
        )
        self._preview_img = pg.transform.scale(self._preview_img, preview_wh).convert()
        self._preview_rect.size = preview_wh
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_xy)

        self.blit_sequence[1] = (self._preview_img, self._preview_rect, UI_LAYER)

    def set_color(self, hex_color: HexColor, is_external_change: bool) -> None:
        """
        Sets the UI on a specific color.

        Args:
            hexadecimal color, external change flag
        """

        hex_color = "#" + hex_color
        color: pg.Color = pg.Color(hex_color)

        self._r_bar.set_value(color, is_external_change)
        self._g_bar.set_value(color, is_external_change)
        self._b_bar.set_value(color, is_external_change)
        self._preview_img.fill(color)
        self._hex_text_label.set_text(hex_color)

        self.blit_sequence[1] = (self._preview_img, self._preview_rect, UI_LAYER)

    def _move_with_keys(self, keyboard: Keyboard) -> None:
        """
        Moves the selected object with keys.

        Args:
            keyboard
        """

        if K_TAB in keyboard.timed:
            if keyboard.is_shift_on:
                self._selection_i.x = max(self._selection_i.x - 1, 0)
            else:
                last_column_i: int = len(self._objs[0]) - 1
                self._selection_i.x = min(self._selection_i.x + 1, last_column_i)

        prev_selection_i_y: int = self._selection_i.y
        if K_UP in keyboard.timed:
            self._selection_i.y = max(self._selection_i.y - 1, 0)
        if K_DOWN in keyboard.timed:
            self._selection_i.y = min(self._selection_i.y + 1, len(self._objs) - 1)

        if self._selection_i.x == 1 and self._selection_i.y != prev_selection_i_y:
            prev_input_box: NumInputBox = self._objs[prev_selection_i_y][1]
            input_box: NumInputBox = self._objs[self._selection_i.y][1]
            closest_char_i: int = input_box.text_label.get_closest_to(prev_input_box.cursor_rect.x)
            input_box.bounded_set_cursor_i(closest_char_i)

    def _upt_scrollbars(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Updates scrollbars and selection.

        Args:
            mouse, keyboard
        """

        i: int
        channel: ColorScrollbar

        selected_obj: Selection = self._objs[self._selection_i.y][self._selection_i.x]
        for i, channel in enumerate((self._r_bar, self._g_bar, self._b_bar)):
            channel_selection_i: Optional[int] = channel.upt(mouse, keyboard, selected_obj)
            if channel_selection_i is not None:
                self._selection_i.x, self._selection_i.y = channel_selection_i, i
                selected_obj = self._objs[self._selection_i.y][self._selection_i.x]

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[bool, bool, RGBColor]:
        """
        Allows to select a color with 3 scrollbars and view its preview.

        Args:
            mouse, keyboard
        Returns:
            exiting flag, confirming flag, rgb color
        """

        is_exiting: bool
        is_confirming: bool

        if keyboard.timed != []:
            self._move_with_keys(keyboard)

        prev_rgb_color: RGBColor = (self._r_bar.value, self._g_bar.value, self._b_bar.value)
        self._upt_scrollbars(mouse, keyboard)
        rgb_color: RGBColor = (self._r_bar.value, self._g_bar.value, self._b_bar.value)
        if rgb_color != prev_rgb_color:
            hex_color: HexColor = "{:02x}{:02x}{:02x}".format(*rgb_color)
            self.set_color(hex_color, False)

        is_exiting, is_confirming = self._base_upt(mouse, keyboard.pressed)

        return is_exiting, is_confirming, rgb_color
