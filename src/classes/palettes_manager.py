"""
Classes to manage the color palettes with a drop-down menu and a scrollbar.

Everything is refreshed automatically.
"""

from math import ceil
from typing import Self, Final

import pygame as pg
from pygame.locals import *

from src.classes.colors_grid import ColorsGrid, NUM_COLS, NUM_VISIBLE_ROWS
from src.classes.dropdown import Dropdown
from src.classes.clickable import Button, LockedCheckbox, SpammableButton
from src.classes.devices import MOUSE, KEYBOARD

from src.obj_utils import UIElement, ObjInfo, resize_obj, rec_move_rect
from src.type_utils import XY, RGBColor, HexColor, BlitInfo, RectPos
from src.consts import (
    MOUSE_LEFT, MOUSE_RIGHT,
    WHITE, DARKER_GRAY, HEX_BLACK,
    BG_LAYER, ELEMENT_LAYER, SPECIAL_LAYER,
)
from src.imgs import (
    BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG,
    ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG, ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG,
    ADD_OFF_IMG, ADD_ON_IMG,
)

_SCROLLBAR_BORDER_DIM: Final[int] = 2


class _VerScrollbar:
    """Class to create a vertical scrollbar."""

    __slots__ = (
        "_bar_init_pos", "_bar_rect", "_bar_init_w", "_bar_init_h",
        "num_values", "value", "selected_value", "_unit_h",
        "_slider_rect", "_selected_value_rect",
        "_traveled_y", "_is_scrolling", "_prev_num_values", "_prev_value", "_prev_selected_value",
        "_down", "_up",
        "hover_rects", "layer", "blit_sequence", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_HAND

    def __init__(self: Self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the bar and slider.

        Args:
            position, base layer (default = BG_LAYER)
        """

        self._bar_init_pos: RectPos = pos

        self._bar_rect: pg.Rect = pg.Rect(0, 0, 16, 128)
        setattr(
            self._bar_rect, self._bar_init_pos.coord_type,
            (self._bar_init_pos.x, self._bar_init_pos.y)
        )

        self._bar_init_w: int = self._bar_rect.w
        self._bar_init_h: int = self._bar_rect.h

        self.num_values: int = NUM_VISIBLE_ROWS
        self.value: int = 0
        self.selected_value: int = 0
        self._unit_h: float = (self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2)) / self.num_values

        self._slider_rect: pg.Rect = pg.Rect(
            0, 0,
            self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2),
            self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2)
        )
        self._slider_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM,
        )

        self._selected_value_rect: pg.Rect = pg.Rect(
            0, 0,
            self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2),
            self._unit_h
        )
        self._selected_value_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM,
        )

        self._traveled_y: float = 0
        self._is_scrolling: bool = False
        self._prev_num_values: int = self.num_values
        self._prev_value: int = self.value
        self._prev_selected_value: int = self.selected_value

        self._down: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.bottom + 5, "midtop"),
            [ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG], " - \n(CTRL -)"
        )
        self._up: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.y - 5, "midbottom"),
            [ARROW_UP_OFF_IMG  , ARROW_UP_ON_IMG  ], " + \n(CTRL +)"
        )
        self._down.set_hover_extra_size(16, 16, 5 , 16)
        self._up.set_hover_extra_size(  16, 16, 16, 5)

        self.hover_rects: tuple[pg.Rect, ...] = (self._bar_rect,)
        self.layer: int = base_layer + ELEMENT_LAYER
        self.blit_sequence: list[BlitInfo] = [(self._get_bar_img(), self._bar_rect, self.layer)]
        self.objs_info: list[ObjInfo] = [ObjInfo(self._down), ObjInfo(self._up)]

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._traveled_y = 0
        self._is_scrolling = False

    def resize(self: Self, win_w_ratio: float, win_h_ratio: float) -> None:
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

        self._slider_rect.size = (
            self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2),
            max(round(self._unit_h * NUM_VISIBLE_ROWS), 1),
        )
        self._slider_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM - round(self.value * self._unit_h),
        )

        self._selected_value_rect.size = (
            self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2),
            max(round(self._unit_h), 1),
        )
        self._selected_value_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM - round(self.selected_value * self._unit_h),
        )

        self.blit_sequence[0] = (self._get_bar_img(), self._bar_rect, self.layer)

    def _get_bar_img(self: Self) -> pg.Surface:
        """
        Creates the image for the scrollbar.

        Returns:
            scrollbar image
        """

        bar_img: pg.Surface = pg.Surface(self._bar_rect.size)
        pg.draw.rect(bar_img, WHITE, bar_img.get_rect(), _SCROLLBAR_BORDER_DIM)
        pg.draw.rect(bar_img, (100, 100, 100), self._slider_rect)
        pg.draw.rect(bar_img, DARKER_GRAY, self._selected_value_rect)
        return bar_img

    def set_info(self: Self, num_values: int, value: int, selected_value: int) -> None:
        """
        Sets the value, selected value and values.

        Args:
            values, value, selected value
        """

        self.num_values = self._prev_num_values = max(num_values, NUM_VISIBLE_ROWS)
        self.value = self._prev_value = value
        self.selected_value = self._prev_selected_value = selected_value
        self._unit_h = (self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2)) / self.num_values

        usable_bottom: int = self._bar_rect.h - _SCROLLBAR_BORDER_DIM

        self._slider_rect.h = max(round(self._unit_h * NUM_VISIBLE_ROWS), 1)
        self._slider_rect.bottom = usable_bottom - round(self.value * self._unit_h)

        self._selected_value_rect.h = max(round(self._unit_h), 1)
        selected_value_offset_y: int = round(self.selected_value * self._unit_h)
        self._selected_value_rect.bottom = usable_bottom - selected_value_offset_y

        self.blit_sequence[0] = (self._get_bar_img(), self._bar_rect, self.layer)

    def _start_scrolling(self: Self) -> None:
        """Changes the value depending on the mouse position and starts scrolling."""

        rel_mouse_y: int = MOUSE.y - self._bar_rect.y
        if rel_mouse_y < self._slider_rect.y or rel_mouse_y > self._slider_rect.bottom:
            value: int = int((self._bar_rect.h - rel_mouse_y) / self._unit_h)
            # If the mouse is above the slider, the top of the slider goes to the mouse value
            if rel_mouse_y < self._slider_rect.y:
                value -= NUM_VISIBLE_ROWS
            self.value = min(max(value, 0), self.num_values - NUM_VISIBLE_ROWS)

        self._traveled_y = 0
        self._is_scrolling = True

    def _scroll(self: Self) -> None:
        """Changes the value depending on the mouse traveled distance."""

        self._traveled_y += MOUSE.prev_y - MOUSE.y
        if abs(self._traveled_y) >= self._unit_h:
            units_traveled: int = int(self._traveled_y / self._unit_h)
            self.value = min(max(
                self.value + units_traveled,
                0), self.num_values - NUM_VISIBLE_ROWS
            )
            self._traveled_y -= units_traveled * self._unit_h

    def _scroll_with_keys(self: Self) -> None:
        """Changes the value with the keyboard."""

        if MOUSE.hovered_obj == self:
            if K_DOWN     in KEYBOARD.timed:
                self.value = max(self.value - 1               , 0)
            if K_UP       in KEYBOARD.timed:
                self.value = min(self.value + 1               , self.num_values - NUM_VISIBLE_ROWS)
            if K_PAGEDOWN in KEYBOARD.timed:
                self.value = max(self.value - NUM_VISIBLE_ROWS, 0)
            if K_PAGEUP   in KEYBOARD.timed:
                self.value = min(self.value + NUM_VISIBLE_ROWS, self.num_values - NUM_VISIBLE_ROWS)
            if K_HOME in KEYBOARD.pressed:
                self.value = 0
            if K_END  in KEYBOARD.pressed:
                self.value = self.num_values - NUM_VISIBLE_ROWS

        if MOUSE.hovered_obj in (self, self._down, self._up):
            if K_MINUS in KEYBOARD.timed:
                self.value = 0         if KEYBOARD.is_ctrl_on else max(self.value - 1, 0)
            if K_PLUS in KEYBOARD.timed:
                max_limit: int = self.num_values - NUM_VISIBLE_ROWS
                self.value = max_limit if KEYBOARD.is_ctrl_on else min(self.value + 1, max_limit)

    def refresh(self: Self) -> None:
        """Refreshes the scrollbar if the values, value or selected value changed."""

        if (
            self.num_values != self._prev_num_values or
            self.value != self._prev_value or
            self.selected_value != self._prev_selected_value
        ):
            self.set_info(self.num_values, self.value, self.selected_value)

    def upt(self: Self) -> None:
        """Allows to pick a value via scrolling, keyboard or arrow buttons."""

        if not MOUSE.pressed[MOUSE_LEFT]:
            self._is_scrolling = False
        elif MOUSE.hovered_obj == self and not self._is_scrolling:
            self._start_scrolling()

        if self._is_scrolling:
            self._scroll()
        if KEYBOARD.pressed != []:
            self._scroll_with_keys()

        is_down_clicked: bool = self._down.upt()
        if is_down_clicked:
            self.value = max(self.value - 1, 0)

        is_up_clicked: bool = self._up.upt()
        if is_up_clicked:
            self.value = min(self.value + 1, self.num_values - NUM_VISIBLE_ROWS)


class PalettesManager:
    """Class to manage the color palettes with a drop-down menu and a scrollbar."""

    __slots__ = (
        "palettes", "clicked_indexes", "offsets_y", "colors_grid",
        "dropdown_indexes", "dropdown_i", "_dropdown_offset_x", "_dropdown_offset_y", "_edit_i",
        "_scrollbar", "_add_palette_btn", "palette_dropdown", "_dropdown_options",
        "hover_rects", "layer", "blit_sequence", "_win_w_ratio", "_win_h_ratio", "objs_info",
        "_dropdown_objs_info_start_i", "_dropdown_objs_info_end_i",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(self: Self, pos: RectPos) -> None:
        """
        Creates the colors grid, a scrollbar, the add palette button and two dropdown-menus.

        Args:
            position
        """

        self.palettes: list[list[HexColor]] = []
        self.clicked_indexes: list[int] = []
        self.offsets_y: list[int] = []
        self.colors_grid: ColorsGrid = ColorsGrid(pos, BG_LAYER)

        self.dropdown_indexes: list[int | None] = []
        self.dropdown_i: int | None = None
        self._dropdown_offset_x: int = 0
        self._dropdown_offset_y: int = 0
        self._edit_i: int | None = None

        add_palette_btn_y: int = self.colors_grid.rect.y - 10

        self._scrollbar: _VerScrollbar = _VerScrollbar(
            RectPos(self.colors_grid.rect.right + 10, self.colors_grid.rect.bottom, "bottomleft")
        )
        self._add_palette_btn: Button = Button(
            RectPos(self.colors_grid.rect.right, add_palette_btn_y, "bottomright"),
            [ADD_OFF_IMG, ADD_ON_IMG], None, "(CTRL+SHIFT+P)"
        )
        self.palette_dropdown: Dropdown = Dropdown(
            RectPos(self._add_palette_btn.rect.x - 10, add_palette_btn_y, "bottomright"),
            [], "Palettes", SPECIAL_LAYER, text_h=18
        )

        options_texts: tuple[tuple[str, str], ...] = (
            ("edit"  , "(CTRL+E)"),
            ("delete", "(CTRL+DEL)"),
        )
        self._dropdown_options: list[Button] = [
            Button(
                RectPos(0, 0, "topleft"),
                [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], text, hovering_text,
                SPECIAL_LAYER, text_h=20
            )
            for text, hovering_text in options_texts
        ]

        self.hover_rects: tuple[pg.Rect, ...] = ()
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = []
        self._win_w_ratio: float = 1
        self._win_h_ratio: float = 1
        self.objs_info: list[ObjInfo] = [
            ObjInfo(self.colors_grid), ObjInfo(self._scrollbar),
            ObjInfo(self._add_palette_btn), ObjInfo(self.palette_dropdown),
        ]

        self._dropdown_objs_info_start_i: int = len(self.objs_info)
        self.objs_info.extend([ObjInfo(option) for option in self._dropdown_options])
        self._dropdown_objs_info_end_i: int   = len(self.objs_info)

        dropdown_objs_info: list[ObjInfo] = self.objs_info[
            self._dropdown_objs_info_start_i:self._dropdown_objs_info_end_i
        ]
        for obj_info in dropdown_objs_info:
            obj_info.rec_set_active(False)

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._edit_i = None

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self: Self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio

    def try_add_color(self: Self, rgb_color: RGBColor) -> bool:
        """
        Adds or edits a color if it's not present then checks it.

        Args:
            rgb color
        Returns:
            changed flag
        """

        did_change: bool = False
        prev_colors_grid_y: int = self.colors_grid.rect.y
        hex_color: HexColor = "{:02x}{:02x}{:02x}".format(*rgb_color)

        if self._edit_i is not None:
            self.colors_grid.edit(self._edit_i, hex_color)
        else:
            did_change = self.colors_grid.try_add(hex_color)
        self.colors_grid.check(self.colors_grid.colors.index(hex_color))

        self._scrollbar.set_info(
            num_values=ceil(len(self.colors_grid.colors) / NUM_COLS),
            value=self._scrollbar.value,
            selected_value=self.colors_grid.clicked_i // NUM_COLS,
        )

        if self.colors_grid.rect.y != prev_colors_grid_y:
            rec_move_rect(
                self._add_palette_btn,
                round(self.colors_grid.rect.right    / self._win_w_ratio),
                round((self.colors_grid.rect.y - 10) / self._win_h_ratio),
                self._win_w_ratio, self._win_h_ratio
            )
            rec_move_rect(
                self.palette_dropdown,
                round((self._add_palette_btn.rect.x - 10) / self._win_w_ratio),
                round((self.colors_grid.rect.y - 10)      / self._win_h_ratio),
                self._win_w_ratio, self._win_h_ratio
            )

        return did_change

    def add_palette(
            self: Self, colors: list[HexColor], color_i: int, offset_y: int, dropdown_i: int | None
    ) -> None:
        """
        Adds a palette to the info arrays and the palette drop-down menu.

        Args:
            colors, clicked index, y offset, drop-down menu index (can be None)
        """

        self.palettes.append(colors)
        self.clicked_indexes.append(color_i)
        self.offsets_y.append(offset_y)
        self.dropdown_indexes.append(dropdown_i)

        self.palette_dropdown.add(
            f"Palette\n{len(self.palettes)}",
            f"CTRL+P+{len(self.palettes)}",
            value=None,
        )

    def refresh_palette(self: Self) -> None:
        """Sets the grid, drop-down menus, scrollbar and button for the active palette."""

        prev_colors_grid_y: int = self.colors_grid.rect.y

        # Offsets by 1 because of placeholder option
        self.colors_grid.set_info(
            self.palettes[self.palette_dropdown.option_i - 1],
            self.clicked_indexes[self.palette_dropdown.option_i - 1],
            self.offsets_y[self.palette_dropdown.option_i - 1],
        )
        self.dropdown_i = self.dropdown_indexes[self.palette_dropdown.option_i - 1]
        checkbox_rect: pg.Rect = self.colors_grid.visible_checkboxes[0].rect
        self._dropdown_offset_x = round(checkbox_rect.w / 2)
        self._dropdown_offset_y = round(checkbox_rect.h / 2)

        self._scrollbar.set_info(
            num_values=ceil(len(self.colors_grid.colors) / NUM_COLS),
            value=self.colors_grid.offset_y,
            selected_value=self.colors_grid.clicked_i // NUM_COLS,
        )
        self.palette_dropdown.set_option_i(self.palette_dropdown.option_i)

        if self.colors_grid.rect.y != prev_colors_grid_y:
            rec_move_rect(
                self._add_palette_btn,
                round(self.colors_grid.rect.right    / self._win_w_ratio),
                round((self.colors_grid.rect.y - 10) / self._win_h_ratio),
                self._win_w_ratio, self._win_h_ratio
            )
            rec_move_rect(
                self.palette_dropdown,
                round((self._add_palette_btn.rect.x - 10) / self._win_w_ratio),
                round((self.colors_grid.rect.y - 10)      / self._win_h_ratio),
                self._win_w_ratio, self._win_h_ratio
            )

    def refresh_dropdown(self: Self) -> None:
        """Refreshes the drop-down menu position and activeness."""

        colors_grid_visible_start_i: int = self.colors_grid.offset_y * NUM_COLS
        visible_checkboxes_len: int = len(self.colors_grid.visible_checkboxes)
        colors_grid_visible_end_i: int = colors_grid_visible_start_i + visible_checkboxes_len

        is_dropdown_on: bool = (
            self.dropdown_i is not None and
            colors_grid_visible_start_i <= self.dropdown_i < colors_grid_visible_end_i
        )
        if is_dropdown_on:
            assert self.dropdown_i is not None
            dropdown_rel_i: int = self.dropdown_i - colors_grid_visible_start_i
            dropdown_checkbox: LockedCheckbox = self.colors_grid.visible_checkboxes[dropdown_rel_i]

            option_x: int = dropdown_checkbox.rect.x + self._dropdown_offset_x
            option_y: int = dropdown_checkbox.rect.y + self._dropdown_offset_y
            option_init_x: int = round(option_x / self._win_w_ratio)
            option_init_y: int = round(option_y / self._win_h_ratio)
            for option in self._dropdown_options:
                rec_move_rect(
                    option, option_init_x, option_init_y,
                    self._win_w_ratio, self._win_h_ratio
                )
                option_init_y += option.init_imgs[0].get_height()

        dropdown_objs_info: list[ObjInfo] = self.objs_info[
            self._dropdown_objs_info_start_i:self._dropdown_objs_info_end_i
        ]
        for obj_info in dropdown_objs_info:
            obj_info.rec_set_active(is_dropdown_on)

    def _handle_scroll(self: Self) -> None:
        """Scrolls if the mouse is hovering a scrollable part."""

        parts: list[UIElement] = (
            self.colors_grid.visible_checkboxes +
            self._dropdown_options +
            [
                self.colors_grid,
                self._scrollbar,
                self._scrollbar._down,
                self._scrollbar._up,
            ]
        )

        if MOUSE.hovered_obj in parts:
            self.colors_grid.offset_y = min(max(
                self.colors_grid.offset_y + MOUSE.scroll_amount,
                0), self._scrollbar.num_values - NUM_VISIBLE_ROWS
            )

    def _handle_palette_shortcuts(self: Self) -> None:
        """Selects a color if the user presses ctrl+p+1-9."""

        k: int

        num_shortcuts: int = min(len(self.palettes), 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                # Offsets by 1 because of placeholder option
                self.palette_dropdown.option_i = k - K_1 + 1

    def _handle_dropdown_shortcuts(self: Self) -> None:
        """Handles the drop-down menu options with the keyboard."""

        if K_e in KEYBOARD.pressed:
            self._edit_i = self.colors_grid.clicked_i
        if K_DELETE in KEYBOARD.timed:
            prev_colors_grid_y: int = self.colors_grid.rect.y

            self.colors_grid.remove(self.colors_grid.clicked_i)
            self._scrollbar.num_values = ceil(len(self.colors_grid.colors) / NUM_COLS)
            if self.dropdown_i is not None and self.dropdown_i > self.colors_grid.clicked_i:
                self.dropdown_i -= 1

            if self.colors_grid.rect.y != prev_colors_grid_y:
                rec_move_rect(
                    self._add_palette_btn,
                    round(self.colors_grid.rect.right    / self._win_w_ratio),
                    round((self.colors_grid.rect.y - 10) / self._win_h_ratio),
                    self._win_w_ratio, self._win_h_ratio
                )
                rec_move_rect(
                    self.palette_dropdown,
                    round((self._add_palette_btn.rect.x - 10) / self._win_w_ratio),
                    round((self.colors_grid.rect.y - 10)      / self._win_h_ratio),
                    self._win_w_ratio, self._win_h_ratio
                )

    def _handle_dropdown_toggle(self: Self) -> None:
        """Toggles the drop-down menu if clicking the same checkboxes, it removes it if not."""

        hovered_checkbox: LockedCheckbox | None = self.colors_grid._hovered_checkbox
        visible_checkboxes: list[LockedCheckbox] = self.colors_grid.visible_checkboxes
        visible_start_i: int = self.colors_grid.offset_y * NUM_COLS

        is_hovering_dropdown_checkbox: bool = (
            self.dropdown_i is not None and
            hovered_checkbox == visible_checkboxes[self.dropdown_i - visible_start_i]
        )
        if hovered_checkbox is None or is_hovering_dropdown_checkbox:
            self.dropdown_i = None
        else:
            self.dropdown_i = visible_start_i + visible_checkboxes.index(hovered_checkbox)
            self._dropdown_offset_x = MOUSE.x - hovered_checkbox.rect.x + 8
            self._dropdown_offset_y = MOUSE.y - hovered_checkbox.rect.y

    def _upt_dropdown(self: Self) -> None:
        """Updates the drop-down menu."""

        is_edit_clicked: bool = self._dropdown_options[0].upt()
        if is_edit_clicked:
            self._edit_i = self.dropdown_i

        is_remove_clicked: bool = self._dropdown_options[1].upt()
        if is_remove_clicked:
            prev_colors_grid_y: int = self.colors_grid.rect.y

            assert self.dropdown_i is not None
            self.colors_grid.remove(self.dropdown_i)
            self._scrollbar.num_values = ceil(len(self.colors_grid.colors) / NUM_COLS)
            self.dropdown_i = min(self.dropdown_i, len(self.colors_grid.colors) - 1)

            if self.colors_grid.rect.y != prev_colors_grid_y:
                rec_move_rect(
                    self._add_palette_btn,
                    round(self.colors_grid.rect.right    / self._win_w_ratio),
                    round((self.colors_grid.rect.y - 10) / self._win_h_ratio),
                    self._win_w_ratio, self._win_h_ratio
                )
                rec_move_rect(
                    self.palette_dropdown,
                    round((self._add_palette_btn.rect.x - 10) / self._win_w_ratio),
                    round((self.colors_grid.rect.y - 10)      / self._win_h_ratio),
                    self._win_w_ratio, self._win_h_ratio
                )

    def refresh(
            self: Self, prev_palette_i: int, prev_num_colors: int, prev_offset_y: int,
            prev_dropdown_i: int | None
    ) -> bool:
        """
        Refreshes the grid, scrollbar and drop-down menu.

        Args:
            previous palette index, previous number of colors, previous y offset,
            previous dropdown index
        Returns:
            changed flag
        """

        did_palette_i_change: bool = self.palette_dropdown.option_i != prev_palette_i
        did_num_colors_change: bool = len(self.colors_grid.colors) != prev_num_colors
        did_offset_y_change: bool = self.colors_grid.offset_y != prev_offset_y

        if did_palette_i_change:
            # Offsets by 1 because of placeholder option
            self.clicked_indexes[ prev_palette_i - 1] = self.colors_grid.clicked_i
            self.offsets_y[       prev_palette_i - 1] = self.colors_grid.offset_y
            self.dropdown_indexes[prev_palette_i - 1] = self.dropdown_i
            self.refresh_palette()

        if self.colors_grid.offset_y != self.colors_grid.prev_offset_y:
            self.colors_grid.set_offset_y(self.colors_grid.offset_y)

        self._scrollbar.refresh()

        if did_offset_y_change or self.dropdown_i != prev_dropdown_i:
            self.refresh_dropdown()
            MOUSE.released[MOUSE_LEFT] = False  # Doesn't click objects below

        return did_palette_i_change or did_num_colors_change or did_offset_y_change

    def upt(self: Self) -> tuple[HexColor, bool, HexColor | None]:
        """
        Allows selecting a color, using a dropdown, a scrollbar and handling palettes.

        Returns:
            selected color, changed flag, color to edit (can be None)
        """

        prev_palette_i: int = self.palette_dropdown.option_i
        prev_num_colors: int = len(self.colors_grid.colors)
        prev_offset_y: int = self.colors_grid.offset_y
        prev_dropdown_i: int | None = self.dropdown_i

        if MOUSE.scroll_amount != 0:
            self._handle_scroll()

        self.colors_grid.upt()
        self._scrollbar.value = self.colors_grid.offset_y
        self._scrollbar.selected_value = self.colors_grid.clicked_i // NUM_COLS

        self._scrollbar.upt()
        self.colors_grid.offset_y = self._scrollbar.value

        is_add_palette_btn_clicked: bool = self._add_palette_btn.upt()
        is_ctrl_shift_p_pressed: bool = (
            KEYBOARD.is_ctrl_on and KEYBOARD.is_shift_on and
            K_p in KEYBOARD.timed
        )
        if is_add_palette_btn_clicked or is_ctrl_shift_p_pressed:
            self.add_palette([HEX_BLACK], color_i=0, offset_y=0, dropdown_i=None)
            self.palette_dropdown.option_i = len(self.palettes)

        if KEYBOARD.is_ctrl_on and K_p in KEYBOARD.pressed:
            self._handle_palette_shortcuts()

        self.palette_dropdown.upt()

        if KEYBOARD.is_ctrl_on:
            self._handle_dropdown_shortcuts()
        if MOUSE.released[MOUSE_RIGHT]:
            self._handle_dropdown_toggle()
        if self.dropdown_i is not None:
            self._upt_dropdown()

        did_change: bool = self.refresh(
            prev_palette_i, prev_num_colors, prev_offset_y,
            prev_dropdown_i
        )

        return (
            self.colors_grid.colors[self.colors_grid.clicked_i],
            did_change,
            None if self._edit_i is None else self.colors_grid.colors[self._edit_i],
        )
