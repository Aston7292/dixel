"""
Classes to manage the color palettes with a drop-down menu and a scrollbar.

Everything is refreshed automatically.
"""

from math import ceil
from typing import Final

import pygame as pg
from pygame.locals import *

from src.classes.colors_grid import ColorsGrid, NUM_COLS, NUM_VISIBLE_ROWS
from src.classes.clickable import Button, SpammableButton
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import RectPos, ObjInfo, resize_obj, rec_move_rect
from src.type_utils import XY, RGBColor, HexColor, BlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_RIGHT, WHITE, DARKER_GRAY, BG_LAYER, ELEMENT_LAYER, SPECIAL_LAYER
)
from src.imgs import (
    BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG,
    ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG, ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG
)

_SCROLLBAR_BORDER_DIM: Final[int] = 2


class _VerScrollbar:
    """Class to create a vertical scrollbar."""

    __slots__ = (
        "_bar_init_pos", "_bar_rect", "_bar_init_w", "_bar_init_h",
        "num_values", "value", "selected_value", "_unit_h",
        "_slider_rect", "_selected_value_rect",
        "_traveled_y", "_is_scrolling", "_prev_num_values", "_prev_value", "_prev_selected_value",
        "_up", "_down",
        "hover_rects", "layer", "blit_sequence", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_HAND

    def __init__(self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the bar and slider.

        Args:
            position, base layer (default = BG_LAYER)
        """

        self._bar_init_pos: RectPos = pos

        self._bar_rect: pg.Rect = pg.Rect(0, 0, 16, 128)
        bar_init_xy: XY = (self._bar_init_pos.x, self._bar_init_pos.y)
        setattr(self._bar_rect, self._bar_init_pos.coord_type, bar_init_xy)

        self._bar_init_w: int = self._bar_rect.w
        self._bar_init_h: int = self._bar_rect.h

        usable_bar_w: int = self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2)
        usable_bar_h: int = self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2)

        self.num_values: int = NUM_VISIBLE_ROWS
        self.value: int = 0
        self.selected_value: int = 0
        self._unit_h: float = usable_bar_h / self.num_values

        self._slider_rect: pg.Rect = pg.Rect(0, 0, usable_bar_w, usable_bar_h)
        self._slider_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM
        )

        self._selected_value_rect: pg.Rect = pg.Rect(0, 0, usable_bar_w, self._unit_h)
        self._selected_value_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM
        )

        self._traveled_y: float = 0
        self._is_scrolling: bool = False
        self._prev_num_values: int = self.num_values
        self._prev_value: int = self.value
        self._prev_selected_value: int = self.selected_value

        self._up: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.y - 5, "midbottom"),
            [ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG], "Up"
        )
        self._down: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.bottom + 5, "midtop"),
            [ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG], "Down"
        )
        self._up  .set_hover_extra_size(16, 16, 16, 5 )
        self._down.set_hover_extra_size(16, 16, 5 , 16)

        bar_img: pg.Surface = pg.Surface(self._bar_rect.size)
        pg.draw.rect(bar_img, WHITE, bar_img.get_rect(), _SCROLLBAR_BORDER_DIM)
        pg.draw.rect(bar_img, (100, 100, 100), self._slider_rect)
        pg.draw.rect(bar_img, DARKER_GRAY, self._selected_value_rect)

        self.hover_rects: list[pg.Rect] = [self._bar_rect]
        self.layer: int = base_layer + ELEMENT_LAYER
        self.blit_sequence: list[BlitInfo] = [(bar_img, self._bar_rect, self.layer)]
        self.objs_info: list[ObjInfo] = [ObjInfo(self._up), ObjInfo(self._down),]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._traveled_y = 0
        self._is_scrolling = False

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        bar_xy: XY

        bar_xy, self._bar_rect.size = resize_obj(
            self._bar_init_pos, self._bar_init_w, self._bar_init_h,
            win_w_ratio, win_h_ratio
        )
        setattr(self._bar_rect, self._bar_init_pos.coord_type, bar_xy)

        # More accurate
        self._unit_h = (self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2)) / self.num_values
        usable_bar_h: int = self._bar_rect.h - _SCROLLBAR_BORDER_DIM

        self._slider_rect.size = (
            self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2),
            max(round(self._unit_h * NUM_VISIBLE_ROWS), 1),
        )
        self._slider_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            usable_bar_h - round(self.value * self._unit_h),
        )

        self._selected_value_rect.size = (
            self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2),
            max(round(self._unit_h), 1),
        )
        self._selected_value_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            usable_bar_h - round(self.selected_value * self._unit_h),
        )

        bar_img: pg.Surface = pg.Surface(self._bar_rect.size)
        pg.draw.rect(bar_img, WHITE, bar_img.get_rect(), _SCROLLBAR_BORDER_DIM)
        pg.draw.rect(bar_img, (100, 100, 100), self._slider_rect)
        pg.draw.rect(bar_img, DARKER_GRAY, self._selected_value_rect)
        self.blit_sequence[0] = (bar_img, self._bar_rect, self.layer)

    def set_info(self, num_values: int, value: int, selected_value: int) -> None:
        """
        Sets the value, selected value and number of values.

        Args:
            number of values, value, selected value
        """

        self.num_values = self._prev_num_values = max(num_values, NUM_VISIBLE_ROWS)
        self.value = self._prev_value = value
        self.selected_value = self._prev_selected_value = selected_value
        self._unit_h = (self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2)) / self.num_values

        usable_bar_h: int = self._bar_rect.h - _SCROLLBAR_BORDER_DIM
        self._slider_rect.h = max(round(self._unit_h * NUM_VISIBLE_ROWS), 1)
        self._slider_rect.bottom = usable_bar_h - round(self.value * self._unit_h)
        self._selected_value_rect.h = max(round(self._unit_h), 1)
        self._selected_value_rect.bottom = usable_bar_h - round(self.selected_value * self._unit_h)

        bar_img: pg.Surface = pg.Surface(self._bar_rect.size)
        pg.draw.rect(bar_img, WHITE, bar_img.get_rect(), _SCROLLBAR_BORDER_DIM)
        pg.draw.rect(bar_img, (100, 100, 100), self._slider_rect)
        pg.draw.rect(bar_img, DARKER_GRAY, self._selected_value_rect)
        self.blit_sequence[0] = (bar_img, self._bar_rect, self.layer)

    def _start_scrolling(self) -> None:
        """Changes the value depending on the mouse position and starts scrolling."""

        rel_mouse_y: int = MOUSE.y - self._bar_rect.y
        if rel_mouse_y < self._slider_rect.y or rel_mouse_y > self._slider_rect.bottom:
            value: int = int((self._bar_rect.h - rel_mouse_y) / self._unit_h)
            # If the mouse is above the slider the top of the slider goes to the mouse value
            if rel_mouse_y < self._slider_rect.y:
                value -= NUM_VISIBLE_ROWS
            self.value = min(max(value, 0), self.num_values - NUM_VISIBLE_ROWS)

        self._traveled_y = 0
        self._is_scrolling = True

    def _scroll(self) -> None:
        """Changes the value depending on the mouse traveled distance."""

        self._traveled_y += MOUSE.prev_y - MOUSE.y
        if abs(self._traveled_y) >= self._unit_h:
            units_traveled: int = int(self._traveled_y / self._unit_h)
            max_value: int = self.num_values - NUM_VISIBLE_ROWS
            self.value = min(max(self.value + units_traveled, 0), max_value)
            self._traveled_y -= units_traveled * self._unit_h

    def _scroll_with_keys(self) -> None:
        """Changes the value with the keyboard."""

        if K_DOWN     in KEYBOARD.timed:
            self.value = max(self.value - 1, 0)
        if K_UP       in KEYBOARD.timed:
            self.value = min(self.value + 1, self.num_values - NUM_VISIBLE_ROWS)
        if K_PAGEDOWN in KEYBOARD.timed:
            self.value = max(self.value - NUM_VISIBLE_ROWS, 0)
        if K_PAGEUP   in KEYBOARD.timed:
            self.value = min(self.value + NUM_VISIBLE_ROWS, self.num_values - NUM_VISIBLE_ROWS)
        if K_HOME     in KEYBOARD.pressed:
            self.value = 0
        if K_END      in KEYBOARD.pressed:
            self.value = self.num_values - NUM_VISIBLE_ROWS

    def refresh(self) -> None:
        if (
            self.num_values != self._prev_num_values or
            self.value != self._prev_value or
            self.selected_value != self._prev_selected_value
        ):
            self.set_info(self.num_values, self.value, self.selected_value)

    def upt(self) -> None:
        """Allows to pick a value via scrolling, keyboard or arrow buttons."""

        if not MOUSE.pressed[MOUSE_LEFT]:
            self._is_scrolling = False
        elif MOUSE.hovered_obj == self and not self._is_scrolling:
            self._start_scrolling()

        if self._is_scrolling:
            self._scroll()
        if MOUSE.hovered_obj == self and KEYBOARD.pressed != []:
            self._scroll_with_keys()

        is_up_clicked: bool = self._up.upt()
        if is_up_clicked:
            self.value = min(self.value + 1, self.num_values - NUM_VISIBLE_ROWS)

        is_down_clicked: bool = self._down.upt()
        if is_down_clicked:
            self.value = max(self.value - 1, 0)

class PaletteManager:
    """Class to manage the color palettes with a drop-down menu and a scrollbar."""

    __slots__ = (
        "colors_grid",
        "dropdown_i", "_dropdown_offset_x", "_dropdown_offset_y", "edit_i",
        "_scrollbar", "_dropdown_options",
        "hover_rects", "layer", "blit_sequence", "_win_w_ratio", "_win_h_ratio", "objs_info",
        "_dropdown_objs_info_start_i", "_dropdown_objs_info_end_i",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(self, pos: RectPos) -> None:

        self.colors_grid: ColorsGrid = ColorsGrid(pos, BG_LAYER)

        self.dropdown_i: int | None = None
        self._dropdown_offset_x: int = 0
        self._dropdown_offset_y: int = 0
        self.edit_i: int | None = None

        self._scrollbar: _VerScrollbar = _VerScrollbar(
            RectPos(self.colors_grid.rect.right + 10, self.colors_grid.rect.bottom, "bottomleft")
        )

        options_texts: tuple[tuple[str, str], ...] = (
            ("edit"  , "CTRL+E"),
            ("delete", "CTRL+DEL"),
        )

        self._dropdown_options: list[Button] = [
            Button(
                RectPos(0, 0, "topleft"),
                [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], text, hovering_text, SPECIAL_LAYER, 20
            )
            for text, hovering_text in options_texts
        ]

        self.hover_rects: list[pg.Rect] = []
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = []
        self._win_w_ratio: float = 1
        self._win_h_ratio: float = 1
        self.objs_info: list[ObjInfo] = [ObjInfo(self.colors_grid), ObjInfo(self._scrollbar)]

        self._dropdown_objs_info_start_i: int = len(self.objs_info)
        self.objs_info.extend([ObjInfo(option) for option in self._dropdown_options])
        self._dropdown_objs_info_end_i: int   = len(self.objs_info)

        dropdown_objs_info: list[ObjInfo] = self.objs_info[
            self._dropdown_objs_info_start_i:self._dropdown_objs_info_end_i
        ]
        for obj_info in dropdown_objs_info:
            obj_info.rec_set_active(False)

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio

    def set_info(
            self, hex_colors: list[HexColor], color_i: int, offset_y: int, dropdown_i: int | None
    ) -> None:
        """
        Sets the colors, offset, clicked color and drop-down menu

        Args:
            hexadecimal colors, color index, grid y offset, drop-down index (can be None)
        """

        self.colors_grid.set_grid(hex_colors, color_i, offset_y)

        self.dropdown_i = dropdown_i

        self._scrollbar.set_info(
            ceil(len(self.colors_grid.colors) / NUM_COLS),
            self.colors_grid.offset_y,
            self.colors_grid.clicked_i // NUM_COLS,
        )

    def add(self, rgb_color: RGBColor) -> bool:
        """
        Adds or edits a color then checks it.

        Args:
            rgb color
        Returns:
            changed flag
        """

        did_change: bool = False
        hex_color: HexColor = "{:02x}{:02x}{:02x}".format(*rgb_color)

        if self.edit_i is not None:
            self.colors_grid.edit(self.edit_i, hex_color)
        else:
            did_change = self.colors_grid.add(hex_color)

        self.colors_grid.check(self.colors_grid.colors.index(hex_color))
        self.edit_i = None

        self._scrollbar.set_info(
            ceil(len(self.colors_grid.colors) / NUM_COLS),
            self._scrollbar.value,
            self.colors_grid.clicked_i // NUM_COLS,
        )

        return did_change

    def upt(self) -> tuple[HexColor, bool, HexColor | None]:
        """
        Allows selecting a color, using a dropdown and a scrollbar.

        Returns:
            selected color, changed flag, color to edit (can be None)
        """

        prev_colors_grid_offset_y: int = self.colors_grid.offset_y
        prev_dropdown_i: int | None = self.dropdown_i
        did_remove_color: bool = False

        if KEYBOARD.is_ctrl_on:
            if K_e in KEYBOARD.pressed:
                self.edit_i = self.colors_grid.clicked_i
            if K_DELETE in KEYBOARD.timed:
                self.colors_grid.remove(self.colors_grid.clicked_i)
                self._scrollbar.num_values = ceil(len(self.colors_grid.colors) / NUM_COLS)

                did_remove_color = True
                if self.dropdown_i is not None and self.dropdown_i > self.colors_grid.clicked_i:
                    self.dropdown_i -= 1

        if (
            MOUSE.scroll_amount != 0 and (
                MOUSE.hovered_obj == self.colors_grid or
                MOUSE.hovered_obj in self.colors_grid.visible_checkboxes or
                MOUSE.hovered_obj == self._scrollbar
            )
        ):
            max_offset_y: int = self._scrollbar.num_values - NUM_VISIBLE_ROWS
            self.colors_grid.offset_y += MOUSE.scroll_amount
            self.colors_grid.offset_y = min(max(self.colors_grid.offset_y, 0), max_offset_y)

        self.colors_grid.upt()
        self._scrollbar.value = self.colors_grid.offset_y
        self._scrollbar.selected_value = self.colors_grid.clicked_i // NUM_COLS

        self._scrollbar.upt()
        self.colors_grid.offset_y = self._scrollbar.value

        if MOUSE.released[MOUSE_RIGHT] and self.colors_grid._hovered_checkbox is not None:
            if self.dropdown_i is None:
                self.dropdown_i = self.colors_grid.visible_checkboxes.index(self.colors_grid._hovered_checkbox)
                self._dropdown_offset_x = MOUSE.x - self.colors_grid._hovered_checkbox.rect.x
                self._dropdown_offset_y = MOUSE.y - self.colors_grid._hovered_checkbox.rect.y
            else:
                self.dropdown_i = None

        if self.colors_grid.offset_y != prev_colors_grid_offset_y:
            self.colors_grid.set_offset_y(self.colors_grid.offset_y)
        self._scrollbar.refresh()
        if self.dropdown_i != prev_dropdown_i:
            if self.dropdown_i is not None:
                start_x: int = self.colors_grid._hovered_checkbox.rect.x + self._dropdown_offset_x
                start_y: int = self.colors_grid._hovered_checkbox.rect.y + self._dropdown_offset_y
                option_init_y: int = round(start_y / self._win_h_ratio)
                for option in self._dropdown_options:
                    rec_move_rect(
                        option, round(start_x / self._win_w_ratio), option_init_y,
                        self._win_w_ratio, self._win_h_ratio
                    )
                    option_init_y += option.init_imgs[0].get_height()

            dropdown_objs_info: list[ObjInfo] = self.objs_info[
                self._dropdown_objs_info_start_i:self._dropdown_objs_info_end_i
            ]
            is_dropdown_on: bool = self.dropdown_i is not None
            for obj_info in dropdown_objs_info:
                obj_info.rec_set_active(is_dropdown_on)

        return (
            self.colors_grid.colors[self.colors_grid.clicked_i],
            self.colors_grid.offset_y != prev_colors_grid_offset_y or did_remove_color,
            None if self.edit_i is None else self.colors_grid.colors[self.edit_i],
        )