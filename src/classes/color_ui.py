"""Interface to choose a color, scrollbars and preview are refreshed automatically."""

from typing import Literal, Final

import pygame as pg
from pygame.locals import *

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import UIElement, RectPos, ObjInfo, resize_obj
from src.type_utils import XY, RGBColor, HexColor, BlitInfo
from src.consts import MOUSE_LEFT, BLACK, ELEMENT_LAYER, UI_LAYER

_SLIDER_OFF_IMG: Final[pg.Surface] = pg.Surface((10, 32))
_SLIDER_ON_IMG: Final[pg.Surface]  = _SLIDER_OFF_IMG.copy()
_SLIDER_OFF_IMG.fill((25, 25, 25))
_SLIDER_ON_IMG. fill(BLACK)

INPUT_BOXES_COL: Final[Literal[1]] = 1


class _ColorScrollbar:
    """Class to create a scrollbar to pick an r, g or b value of a color."""

    __slots__ = (
        "_bar_init_pos", "_bar_img", "bar_rect", "_bar_init_w", "_bar_init_h",
        "_slider_init_pos", "_slider_imgs", "_slider_rect", "_slider_init_w", "_slider_init_h",
        "_is_scrolling", "_channel_i",
        "input_box",
        "hover_rects", "layer", "blit_sequence", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_HAND

    def __init__(self, pos: RectPos, channel_i: Literal[0, 1, 2], base_layer: int = UI_LAYER) -> None:
        """
        Creates the bar, slider, text and input box.

        Args:
            position, channel index, base layer (default = UI_LAYER)
        """

        self._bar_init_pos: RectPos = pos

        self._bar_img: pg.Surface = pg.Surface((256, 25))
        self.bar_rect: pg.Rect = pg.Rect(0, 0, *self._bar_img.get_size())
        bar_init_xy: XY = (self._bar_init_pos.x, self._bar_init_pos.y)
        setattr(self.bar_rect, self._bar_init_pos.coord_type, bar_init_xy)

        self._bar_init_w: int = self.bar_rect.w
        self._bar_init_h: int = self.bar_rect.h

        self._slider_init_pos: RectPos = RectPos(0, self.bar_rect.centery, "midleft")

        self._slider_imgs: list[pg.Surface] = [_SLIDER_OFF_IMG, _SLIDER_ON_IMG]
        self._slider_rect: pg.Rect = pg.Rect(0, 0, *self._slider_imgs[0].get_size())
        slider_init_xy: XY = (self.bar_rect.x, self._slider_init_pos.y)
        setattr(self._slider_rect, self._slider_init_pos.coord_type, slider_init_xy)

        self._slider_init_w: int = self._slider_rect.w
        self._slider_init_h: int = self._slider_rect.h

        self._is_scrolling: bool = False
        self._channel_i: Literal[0, 1, 2] = channel_i

        channel_text_label: TextLabel = TextLabel(
            RectPos(self.bar_rect.x - 4, self.bar_rect.centery, "midright"),
            ("R", "G", "B")[self._channel_i], base_layer
        )
        self.input_box: NumInputBox = NumInputBox(
            RectPos(self.bar_rect.right + 16, self.bar_rect.centery, "midleft"),
            0, 255, base_layer
        )

        self.hover_rects: list[pg.Rect] = [self.bar_rect, self._slider_rect]
        self.layer: int = base_layer + ELEMENT_LAYER
        self.blit_sequence: list[BlitInfo] = [
            (self._bar_img       , self.bar_rect    , self.layer),
            (self._slider_imgs[0], self._slider_rect, self.layer),
        ]
        self.objs_info: list[ObjInfo] = [ObjInfo(channel_text_label), ObjInfo(self.input_box),]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._is_scrolling = False
        self.blit_sequence[1] = (self._slider_imgs[0], self._slider_rect, self.layer)

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        bar_xy: XY
        _slider_x: int
        slider_y: int

        bar_xy, self.bar_rect.size = resize_obj(
            self._bar_init_pos, self._bar_init_w, self._bar_init_h,
            win_w_ratio, win_h_ratio
        )

        self._bar_img = pg.transform.scale(self._bar_img, self.bar_rect.size).convert()
        setattr(self.bar_rect, self._bar_init_pos.coord_type, bar_xy)

        (_slider_x, slider_y), self._slider_rect.size = resize_obj(
            self._slider_init_pos, self._slider_init_w, self._slider_init_h,
            win_w_ratio, win_h_ratio
        )

        # More accurate
        unit_w: float = self.bar_rect.w / self._bar_init_w
        slider_xy: XY = (self.bar_rect.x + round(self.input_box.value * unit_w), slider_y)

        slider_img_i: int = self._slider_imgs.index(self.blit_sequence[1][0])
        self._slider_imgs = [
            pg.transform.scale(img, self._slider_rect.size).convert() for img in self._slider_imgs
        ]
        setattr(self._slider_rect, self._slider_init_pos.coord_type, slider_xy)

        self.blit_sequence[0] = (self._bar_img                  , self.bar_rect    , self.layer)
        self.blit_sequence[1] = (self._slider_imgs[slider_img_i], self._slider_rect, self.layer)

    def set_value(self, color: pg.Color, is_external_change: bool) -> None:
        """
        Sets the bar on a specif value.

        Args:
            color, external change flag
        """

        value: int

        if is_external_change:
            self.input_box.set_value(color[self._channel_i])

        px_color: pg.Color = pg.Color(color)
        unscaled_bar_img: pg.Surface = pg.Surface((self._bar_init_w, 1))  # More accurate

        unscaled_bar_img.lock()
        for value in range(self._bar_init_w):
            px_color[self._channel_i] = value
            unscaled_bar_img.set_at((value, 0), px_color)
        unscaled_bar_img.unlock()

        unit_w: float = self.bar_rect.w / self._bar_init_w
        self._bar_img = pg.transform.scale(unscaled_bar_img, self.bar_rect.size).convert()
        # More accurate
        self._slider_rect.x = self.bar_rect.x + round(self.input_box.value * unit_w)

        self.blit_sequence[0] = (self._bar_img, self.bar_rect, self.layer)

    def _scroll(self) -> None:
        """Changes the color with the mouse."""

        unit_w: float = self.bar_rect.w / self._bar_init_w
        min_limit: int = self.input_box.min_limit
        max_limit: int = self.input_box.max_limit

        self.input_box.value = int((MOUSE.x - self.bar_rect.x) / unit_w)
        self.input_box.value = min(max(self.input_box.value, min_limit), max_limit)

    def _scroll_with_keys(self) -> None:
        """Changes the color with the keyboard."""

        if K_LEFT     in KEYBOARD.timed:
            self.input_box.value = max(self.input_box.value - 1,  self.input_box.min_limit)
        if K_RIGHT    in KEYBOARD.timed:
            self.input_box.value = min(self.input_box.value + 1,  self.input_box.max_limit)
        if K_PAGEDOWN in KEYBOARD.timed:
            self.input_box.value = max(self.input_box.value - 25, self.input_box.min_limit)
        if K_PAGEUP   in KEYBOARD.timed:
            self.input_box.value = min(self.input_box.value + 25, self.input_box.max_limit)
        if K_HOME     in KEYBOARD.pressed:
            self.input_box.value = self.input_box.min_limit
        if K_END      in KEYBOARD.pressed:
            self.input_box.value = self.input_box.max_limit

        if K_MINUS in KEYBOARD.timed:
            self.input_box.value = (
                self.input_box.min_limit if KEYBOARD.is_ctrl_on else
                max(self.input_box.value - 1, self.input_box.min_limit)
            )
        if K_PLUS in KEYBOARD.timed:
            self.input_box.value = (
                self.input_box.max_limit if KEYBOARD.is_ctrl_on else
                min(self.input_box.value + 1, self.input_box.max_limit)
            )

    def upt(self, selected_obj: UIElement) -> UIElement:
        """
        Allows to choose a channel value either with a scrollbar or an input box.

        Args:
            selected object
        Returns:
            selected object
        """

        if not MOUSE.pressed[MOUSE_LEFT]:
            self._is_scrolling = False
        elif MOUSE.hovered_obj == self:
            self._is_scrolling = True
            selected_obj = self

        if self._is_scrolling:
            self._scroll()
        if selected_obj == self and KEYBOARD.pressed != []:
            self._scroll_with_keys()

        selected_obj = self.input_box.upt(selected_obj)

        slider_img: pg.Surface = self._slider_imgs[int(selected_obj == self)]
        self.blit_sequence[1] = (slider_img, self._slider_rect, self.layer)

        return selected_obj


class ColorPicker(UI):
    """Class to create an interface that allows picking a color, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_img", "_preview_rect", "_preview_init_w", "_preview_init_h",
        "_hex_text_label",
        "_b_bar", "_g_bar", "_r_bar", "_objs", "_selection_x", "_selection_y",
    )

    def __init__(self) -> None:
        """Creates the interface, scrollbars and preview."""

        super().__init__("CHOOSE A COLOR", True)

        self._preview_init_pos: RectPos = RectPos(self._rect.centerx, self._rect.centery, "midtop")

        self._preview_img: pg.Surface = pg.Surface((256, 256))
        self._preview_rect: pg.Rect = pg.Rect(0, 0, *self._preview_img.get_size())
        preview_init_xy: XY = (self._preview_init_pos.x, self._preview_init_pos.y)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_init_xy)

        self._preview_init_w: int = self._preview_rect.w
        self._preview_init_h: int = self._preview_rect.h

        self._hex_text_label: TextLabel = TextLabel(
            RectPos(self._preview_rect.centerx, self._preview_rect.y - 32, "midbottom"),
            "", self.layer
        )

        self._b_bar: _ColorScrollbar = _ColorScrollbar(
            RectPos(self._rect.centerx, self._hex_text_label.rect.y - 50, "center"),
            2
        )
        self._g_bar: _ColorScrollbar = _ColorScrollbar(
            RectPos(self._rect.centerx, self._b_bar.bar_rect.y      - 50, "center"),
            1
        )
        self._r_bar: _ColorScrollbar = _ColorScrollbar(
            RectPos(self._rect.centerx, self._g_bar.bar_rect.y      - 50, "center"),
            0
        )

        self._objs: tuple[tuple[_ColorScrollbar, NumInputBox], ...] = (
            (self._r_bar, self._r_bar.input_box),
            (self._g_bar, self._g_bar.input_box),
            (self._b_bar, self._b_bar.input_box),
        )
        self._selection_x: int = 0
        self._selection_y: int = 0

        self.blit_sequence.append((self._preview_img, self._preview_rect, self.layer))
        self.objs_info.extend((
            ObjInfo(self._hex_text_label),
            ObjInfo(self._r_bar), ObjInfo(self._b_bar), ObjInfo(self._g_bar),
        ))


    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        super().enter()
        self._selection_x = self._selection_y = 0

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        preview_xy: XY

        super().resize(win_w_ratio, win_h_ratio)

        preview_xy, self._preview_rect.size = resize_obj(
            self._preview_init_pos, self._preview_init_w, self._preview_init_h,
            win_w_ratio, win_h_ratio
        )

        self._preview_img = pg.transform.scale(
            self._preview_img, self._preview_rect.size
        ).convert()
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_xy)

        self.blit_sequence[1] = (self._preview_img, self._preview_rect, self.layer)

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

    def _move_with_keys(self) -> None:
        """Moves the selection with the keyboard."""

        if K_TAB in KEYBOARD.timed:
            if KEYBOARD.is_shift_on:
                self._selection_x = max(self._selection_x - 1, 0)
            else:
                last_col_i: int = len(self._objs[0]) - 1
                self._selection_x = min(self._selection_x + 1, last_col_i)

        prev_selection_i_y: int = self._selection_y
        if K_UP   in KEYBOARD.timed:
            self._selection_y = max(self._selection_y - 1, 0)
        if K_DOWN in KEYBOARD.timed:
            self._selection_y = min(self._selection_y + 1, len(self._objs) - 1)

        if self._selection_x == INPUT_BOXES_COL and self._selection_y != prev_selection_i_y:
            prev_input_box: NumInputBox = self._objs[prev_selection_i_y][INPUT_BOXES_COL]
            input_box: NumInputBox      = self._objs[self._selection_y ][INPUT_BOXES_COL]
            input_box.cursor_i = input_box.text_label.get_closest_to(prev_input_box.cursor_rect.x)

    def _upt_scrollbars(self) -> None:
        """Updates scrollbars and selection."""

        i: int
        channel: _ColorScrollbar

        selected_obj: UIElement = self._objs[self._selection_y][self._selection_x]
        for i, channel in enumerate((self._r_bar, self._g_bar, self._b_bar)):
            prev_selected_obj: UIElement = selected_obj
            selected_obj = channel.upt(selected_obj)

            if selected_obj != prev_selected_obj:
                prev_selected_obj.leave()
                self._selection_y = i
                self._selection_x = self._objs[self._selection_y].index(selected_obj)

    def upt(self) -> tuple[bool, bool, RGBColor]:
        """
        Allows to select a color with 3 scrollbars and view its preview.

        Returns:
            exiting flag, confirming flag, rgb color
        """

        is_exiting: bool
        is_confirming: bool

        if KEYBOARD.timed != []:
            self._move_with_keys()

        prev_rgb_color: RGBColor = (
            self._r_bar.input_box.value, self._g_bar.input_box.value, self._b_bar.input_box.value
        )
        self._upt_scrollbars()
        rgb_color: RGBColor = (
            self._r_bar.input_box.value, self._g_bar.input_box.value, self._b_bar.input_box.value
        )

        if rgb_color != prev_rgb_color:
            self.set_color("{:02x}{:02x}{:02x}".format(*rgb_color), False)

        self._r_bar.input_box.refresh()
        self._b_bar.input_box.refresh()
        self._g_bar.input_box.refresh()
        is_exiting, is_confirming = self._base_upt()
        return is_exiting, is_confirming, rgb_color
