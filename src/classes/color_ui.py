"""Interface to choose a color, scrollbars and preview are refreshed automatically."""

from typing import Literal, Self, Final

from pygame import (
    Color, Surface, Rect, draw, transform,
    K_LEFT, K_RIGHT, K_PAGEDOWN, K_PAGEUP, K_HOME, K_END, K_MINUS, K_PLUS,
    K_TAB, K_DOWN, K_UP,
    SYSTEM_CURSOR_HAND,
)

from src.classes.ui import UI
from src.classes.input_box import NumInputBox, ColorInputBox
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE, KEYBOARD

from src.obj_utils import UIElement, resize_obj
from src.type_utils import XY, HexColor, RectPos
from src.consts import BLACK, MOUSE_LEFT, ELEMENT_LAYER, UI_LAYER

_BAR_INIT_W: Final[int] = 256
_BAR_INIT_H: Final[int] = 25
_SLIDER_INIT_W: Final[int] = 10
_SLIDER_INIT_H: Final[int] = 32


class _ColorScrollbar(UIElement):
    """Class to create a scrollbar to pick an r, g or b value of a color."""

    __slots__ = (
        "_bar_init_pos", "_unscaled_bar_img", "bar_rect",
        "_slider_init_pos", "_slider_imgs", "_slider_rect",
        "_channel_i", "_is_scrolling",
        "input_box",
    )

    def __init__(
            self: Self, pos: RectPos, channel_i: Literal[0, 1, 2],
            base_layer: int = UI_LAYER
    ) -> None:
        """
        Creates the bar, slider, text and input box.

        Args:
            position, channel index, base layer (default = UI_LAYER)
        """

        super().__init__()

        self._bar_init_pos: RectPos = pos

        self._unscaled_bar_img: Surface = Surface((_BAR_INIT_W, 1))
        self.bar_rect: Rect = Rect(0, 0, _BAR_INIT_W, _BAR_INIT_H)
        setattr(
            self.bar_rect, self._bar_init_pos.coord_type,
            (self._bar_init_pos.x, self._bar_init_pos.y)
        )

        self._slider_init_pos: RectPos = RectPos(0, self.bar_rect.centery, "midleft")

        slider_img_1: Surface = Surface((_SLIDER_INIT_W, _SLIDER_INIT_H))
        slider_img_2: Surface = Surface((_SLIDER_INIT_W, _SLIDER_INIT_H))
        slider_img_1.fill((25, 25, 25))
        slider_img_2.fill(BLACK)

        self._slider_imgs: tuple[Surface, ...] = (slider_img_1, slider_img_2)
        self._slider_rect: Rect = Rect(0, 0, *self._slider_imgs[0].get_size())
        setattr(
            self._slider_rect, self._slider_init_pos.coord_type,
            (self.bar_rect.x, self._slider_init_pos.y)
        )

        self._channel_i: Literal[0, 1, 2] = channel_i
        self._is_scrolling: bool = False

        channel_text_label: TextLabel = TextLabel(
            RectPos(self.bar_rect.x - 4, self.bar_rect.centery, "midright"),
            ("R", "G", "B")[self._channel_i], base_layer
        )
        self.input_box: NumInputBox = NumInputBox(
            RectPos(self.bar_rect.right + 16, self.bar_rect.centery, "midleft"),
            min_limit=0, max_limit=255, base_layer=base_layer
        )

        self.hover_rects = (self.bar_rect, self._slider_rect)
        self.layer = base_layer + ELEMENT_LAYER
        self.cursor_type = SYSTEM_CURSOR_HAND
        self.blit_sequence = [
            (self._unscaled_bar_img, self.bar_rect    , self.layer),
            (self._slider_imgs[0]  , self._slider_rect, self.layer),
        ]
        self.sub_objs = (channel_text_label, self.input_box)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._is_scrolling = False
        self.blit_sequence[1] = (self._slider_imgs[0], self._slider_rect, self.layer)

    def resize(self: Self) -> None:
        """Resizes the object."""

        bar_xy: XY
        _slider_x: int
        slider_y: int

        bar_xy, self.bar_rect.size = resize_obj(self._bar_init_pos, _BAR_INIT_W, _BAR_INIT_H)
        bar_img: Surface = transform.scale(self._unscaled_bar_img, self.bar_rect.size).convert()
        setattr(self.bar_rect, self._bar_init_pos.coord_type, bar_xy)

        (_slider_x, slider_y), self._slider_rect.size = resize_obj(
            self._slider_init_pos, _SLIDER_INIT_W, _SLIDER_INIT_H
        )
        slider_img_i: int = self._slider_imgs.index(self.blit_sequence[1][0])
        unit_w: float = self.bar_rect.w / _BAR_INIT_W

        self._slider_imgs = tuple([
            transform.scale(img, self._slider_rect.size).convert()
            for img in self._slider_imgs
        ])
        setattr(
            self._slider_rect, self._slider_init_pos.coord_type,
            (self.bar_rect.x + round(self.input_box.value * unit_w), slider_y)  # More accurate
        )

        self.blit_sequence[0] = (bar_img                        , self.bar_rect    , self.layer)
        self.blit_sequence[1] = (self._slider_imgs[slider_img_i], self._slider_rect, self.layer)

    def set_value(self: Self, color: Color) -> None:
        """
        Sets the bar on a specif value.

        Args:
            color
        """

        value: int

        px_color: Color = Color(color)

        self._unscaled_bar_img.lock()
        for value in range(_BAR_INIT_W):
            px_color[self._channel_i] = value
            self._unscaled_bar_img.set_at((value, 0), px_color)
        self._unscaled_bar_img.unlock()

        self.input_box.set_value(color[self._channel_i])

        unit_w: float = self.bar_rect.w / _BAR_INIT_W
        self._slider_rect.x = self.bar_rect.x + round(self.input_box.value * unit_w)

        bar_img: Surface = transform.scale(self._unscaled_bar_img, self.bar_rect.size).convert()
        self.blit_sequence[0] = (bar_img, self.bar_rect, self.layer)

    def _handle_scroll_with_keys(self: Self) -> None:
        """Handles changing the color with the keyboard."""

        if K_LEFT     in KEYBOARD.timed:
            self.input_box.set_value(max(self.input_box.value - 1 , self.input_box.min_limit))
        if K_RIGHT    in KEYBOARD.timed:
            self.input_box.set_value(min(self.input_box.value + 1 , self.input_box.max_limit))
        if K_PAGEDOWN in KEYBOARD.timed:
            self.input_box.set_value(max(self.input_box.value - 25, self.input_box.min_limit))
        if K_PAGEUP   in KEYBOARD.timed:
            self.input_box.set_value(min(self.input_box.value + 25, self.input_box.max_limit))
        if K_HOME in KEYBOARD.timed:
            self.input_box.set_value(self.input_box.min_limit)
        if K_END in KEYBOARD.timed:
            self.input_box.set_value(self.input_box.max_limit)

        if K_MINUS in KEYBOARD.timed:
            self.input_box.set_value((
                self.input_box.min_limit if KEYBOARD.is_ctrl_on else
                max(self.input_box.value - 1, self.input_box.min_limit)
            ))
        if K_PLUS in KEYBOARD.timed:
            self.input_box.set_value((
                self.input_box.max_limit if KEYBOARD.is_ctrl_on else
                min(self.input_box.value + 1, self.input_box.max_limit)
            ))

    def upt(self: Self, selected_obj: UIElement) -> UIElement:
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
            unit_w: float = self.bar_rect.w / _BAR_INIT_W
            self.input_box.set_value(min(max(
                int((MOUSE.x - self.bar_rect.x) / unit_w),
                self.input_box.min_limit), self.input_box.max_limit
            ))
        if selected_obj == self and KEYBOARD.timed != ():
            self._handle_scroll_with_keys()

        selected_obj = self.input_box.upt(selected_obj)

        slider_img_i: int = int(selected_obj == self)
        self.blit_sequence[1] = (self._slider_imgs[slider_img_i], self._slider_rect, self.layer)

        return selected_obj

class ColorPicker(UI):
    """Class to create an interface that allows picking a color, has a preview."""

    __slots__ = (
        "_b_bar", "_g_bar", "_r_bar", "_color_input_box", "_objs", "_selection_x", "_selection_y",
        "_preview_init_pos", "_preview_rect", "_preview_init_w", "_preview_init_h",
    )

    def __init__(self: Self) -> None:
        """Creates the interface, scrollbars and preview."""

        super().__init__("CHOOSE A COLOR", True)

        self._r_bar: _ColorScrollbar = _ColorScrollbar(
            RectPos(self._rect.centerx, self._title_text_label.rect.bottom + 40, "midtop"),
            channel_i=0
        )
        self._g_bar: _ColorScrollbar = _ColorScrollbar(
            RectPos(self._rect.centerx, self._r_bar.bar_rect.bottom        + 40, "midtop"),
            channel_i=1
        )
        self._b_bar: _ColorScrollbar = _ColorScrollbar(
            RectPos(self._rect.centerx, self._g_bar.bar_rect.bottom        + 40, "midtop"),
            channel_i=2
        )

        self._color_input_box: ColorInputBox = ColorInputBox(
            RectPos(self._rect.centerx, self._b_bar.bar_rect.bottom + 40, "midtop"),
            self.layer
        )

        self._objs: tuple[tuple[UIElement, UIElement], ...] = (
            (self._r_bar, self._r_bar.input_box),
            (self._g_bar, self._g_bar.input_box),
            (self._b_bar, self._b_bar.input_box),
            (self._color_input_box, self._color_input_box),
        )
        self._selection_x: int = 0
        self._selection_y: int = 0

        self._preview_init_pos: RectPos = RectPos(
            self._rect.centerx, self._color_input_box.rect.bottom + 16,
            "midtop"
        )

        preview_img: Surface = Surface((256, 256))
        self._preview_rect: Rect = Rect(0, 0, *preview_img.get_size())
        setattr(
            self._preview_rect, self._preview_init_pos.coord_type,
            (self._preview_init_pos.x, self._preview_init_pos.y)
        )

        self._preview_init_w: int = self._preview_rect.w
        self._preview_init_h: int = self._preview_rect.h

        self.blit_sequence.append((preview_img, self._preview_rect, self.layer))
        self.sub_objs += (self._r_bar, self._b_bar, self._g_bar, self._color_input_box)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self._selection_x = self._selection_y = 0

    def resize(self: Self) -> None:
        """Resizes the object."""

        preview_xy: XY

        super().resize()

        preview_xy, self._preview_rect.size = resize_obj(
            self._preview_init_pos, self._preview_init_w, self._preview_init_h
        )
        preview_img: Surface = Surface(self._preview_rect.size)
        preview_img.fill("#" + self._color_input_box.value)
        draw.rect(preview_img, BLACK, preview_img.get_rect(), width=8)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_xy)

        self.blit_sequence[1] = (preview_img, self._preview_rect, self.layer)

    def set_color(self: Self, hex_color: HexColor, is_external_update: bool) -> None:
        """
        Sets the UI on a specific color.

        Args:
            hexadecimal color, external update flag
        """

        color: Color = Color("#" + hex_color)

        self._r_bar.set_value(color)
        self._g_bar.set_value(color)
        self._b_bar.set_value(color)

        preview_img: Surface = Surface(self._preview_rect.size)
        preview_img.fill(color)
        draw.rect(preview_img, BLACK, preview_img.get_rect(), width=8)

        self.blit_sequence[1] = (preview_img, self._preview_rect, self.layer)

        if is_external_update:
            self._color_input_box.set_value(hex_color)

            self._r_bar.input_box.refresh()
            self._b_bar.input_box.refresh()
            self._g_bar.input_box.refresh()
            self._color_input_box.refresh()

    def _handle_move_with_keys(self: Self) -> None:
        """Handles moving the selection with the keyboard."""

        prev_selected_obj: UIElement = self._objs[self._selection_y][1]

        if K_TAB in KEYBOARD.timed:
            if KEYBOARD.is_shift_on:
                self._selection_x = max(self._selection_x - 1, 0)
            else:
                self._selection_x = min(self._selection_x + 1, len(self._objs[0]) - 1)

        if K_UP   in KEYBOARD.timed:
            self._selection_y = max(self._selection_y - 1, 0)
        if K_DOWN in KEYBOARD.timed:
            self._selection_y = min(self._selection_y + 1, len(self._objs) - 1)

        selected_obj: UIElement = self._objs[self._selection_y][1]
        if (
            selected_obj != prev_selected_obj and
            (isinstance(prev_selected_obj, NumInputBox) and isinstance(selected_obj, NumInputBox))
        ):
            prev_cursor_x: int = prev_selected_obj.cursor_rect.x
            selected_obj.cursor_i = selected_obj.text_label.get_closest_to(prev_cursor_x)

    def _upt_objs(self: Self) -> None:
        """Updates the scrollbars, input boxes and selection."""

        i: int
        obj: _ColorScrollbar | ColorInputBox

        main_objs: tuple[_ColorScrollbar | ColorInputBox, ...] = (
            self._r_bar, self._g_bar, self._b_bar,
            self._color_input_box,
        )
        selected_obj: UIElement = self._objs[self._selection_y][self._selection_x]

        for i, obj in enumerate(main_objs):
            prev_selected_obj: UIElement = selected_obj
            if obj == self._color_input_box:
                r: int = self._r_bar.input_box.value
                g: int = self._g_bar.input_box.value
                b: int = self._b_bar.input_box.value
                hex_color: HexColor = f"{r:02x}{g:02x}{b:02x}"
                if self._color_input_box.value != hex_color:
                    self._color_input_box.set_value(hex_color)

            selected_obj = obj.upt(selected_obj)
            if selected_obj != prev_selected_obj:
                prev_selected_obj.leave()
                self._selection_y = i
                self._selection_x = self._objs[self._selection_y].index(selected_obj)

    def upt(self: Self) -> tuple[bool, bool, HexColor]:
        """
        Allows to select a color with 3 scrollbars and view its preview.

        Returns:
            exiting flag, confirming flag, rgb color
        """

        is_exiting: bool
        is_confirming: bool

        prev_hex_color: HexColor = self._color_input_box.value

        if KEYBOARD.timed != ():
            self._handle_move_with_keys()

        self._upt_objs()

        if self._color_input_box.value != prev_hex_color:
            self.set_color(self._color_input_box.value, is_external_update=False)

        self._r_bar.input_box.refresh()
        self._b_bar.input_box.refresh()
        self._g_bar.input_box.refresh()
        self._color_input_box.refresh()
        is_exiting, is_confirming = self._base_upt()
        return is_exiting, is_confirming, self._color_input_box.value
