"""
Classes to manage the color palettes with a drop-down menu and a scrollbar.

Everything is refreshed automatically.
"""

from math import ceil
from typing import Self, Final

from pygame import (
    Surface, Rect, draw,
    K_DOWN, K_UP, K_PAGEDOWN, K_PAGEUP, K_HOME, K_END, K_MINUS, K_PLUS,
    K_DELETE, K_1, K_e, K_p,
    SYSTEM_CURSOR_HAND,
)

from src.classes.colors_grid import ColorsGrid, NUM_COLS, NUM_VISIBLE_ROWS
from src.classes.dropdown import Dropdown
from src.classes.clickable import Button, LockedCheckbox, SpammableButton
from src.classes.devices import MOUSE, KEYBOARD

import src.vars as my_vars
from src.obj_utils import UIElement, resize_obj
from src.type_utils import XY, HexColor, RectPos
from src.consts import (
    WHITE, HEX_BLACK,
    MOUSE_LEFT, MOUSE_RIGHT,
    BG_LAYER, ELEMENT_LAYER, SPECIAL_LAYER,
)
from src.imgs import (
    BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG,
    ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG, ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG,
    ADD_OFF_IMG, ADD_ON_IMG, INFO_OFF_IMG, INFO_ON_IMG,
)

_SCROLLBAR_INIT_W: Final[int] = 16
_SCROLLBAR_INIT_H: Final[int] = 128
_SCROLLBAR_BORDER_DIM: Final[int] = 2


class _VerScrollbar(UIElement):
    """Class to create a vertical scrollbar."""

    __slots__ = (
        "_bar_init_pos", "_bar_rect",
        "num_values", "value", "selected_value", "_selected_hex_color", "_unit_h",
        "_slider_rect", "_selected_value_rect",
        "_traveled_y", "_is_scrolling",
        "down", "up",
        "prev_num_values", "prev_value",
    )

    def __init__(self: Self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the bar and slider.

        Args:
            position, base layer (default = BG_LAYER)
        """

        super().__init__()

        self._bar_init_pos: RectPos = pos

        self._bar_rect: Rect = Rect(0, 0, 16, 128)
        setattr(
            self._bar_rect, self._bar_init_pos.coord_type,
            (self._bar_init_pos.x, self._bar_init_pos.y)
        )

        self.num_values: int = NUM_VISIBLE_ROWS
        self.value: int = 0
        self.selected_value: int = 0
        self._selected_hex_color: HexColor = "#" + HEX_BLACK
        self._unit_h: float = (self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2)) / self.num_values

        self._slider_rect: Rect = Rect(
            0, 0,
            self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2),
            self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2),
        )
        self._slider_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM,
        )

        self._selected_value_rect: Rect = Rect(
            0, 0,
            self._bar_rect.w - (_SCROLLBAR_BORDER_DIM * 2),
            self._unit_h,
        )
        self._selected_value_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM,
        )

        self._traveled_y: float = 0
        self._is_scrolling: bool = False

        self.down: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.bottom + 5, "midtop"),
            (ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG), " - \n(CTRL -)", base_layer
        )
        self.up: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.y - 5, "midbottom"),
            (ARROW_UP_OFF_IMG  , ARROW_UP_ON_IMG  ), " + \n(CTRL +)", base_layer
        )
        self.down.set_hover_extra_size(16, 16, 5 , 16)
        self.up.set_hover_extra_size(  16, 16, 16, 5)

        self.prev_num_values: int = self.num_values
        self.prev_value: int = self.value

        self.hover_rects = (self._bar_rect,)
        self.layer = base_layer + ELEMENT_LAYER
        self.cursor_type = SYSTEM_CURSOR_HAND
        self.blit_sequence = [(self._get_bar_img(), self._bar_rect, self.layer)]
        self.sub_objs = (self.down, self.up)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._traveled_y = 0
        self._is_scrolling = False

    def resize(self: Self) -> None:
        """Resizes the object."""

        bar_xy: XY

        bar_xy, self._bar_rect.size = resize_obj(
            self._bar_init_pos, _SCROLLBAR_INIT_W, _SCROLLBAR_INIT_H
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
            max(round(self._unit_h), 3),
        )
        self._selected_value_rect.bottomleft = (
            _SCROLLBAR_BORDER_DIM,
            self._bar_rect.h - _SCROLLBAR_BORDER_DIM - round(self.selected_value * self._unit_h),
        )

        self.blit_sequence[0] = (self._get_bar_img(), self._bar_rect, self.layer)

    def _get_bar_img(self: Self) -> Surface:
        """
        Creates the image for the scrollbar.

        Returns:
            scrollbar image
        """

        bar_img: Surface = Surface(self._bar_rect.size)
        draw.rect(bar_img, WHITE, bar_img.get_rect(), width=_SCROLLBAR_BORDER_DIM)
        draw.rect(bar_img, (100, 100, 100), self._slider_rect)
        draw.rect(bar_img, self._selected_hex_color, self._selected_value_rect)

        if self.selected_value != 0:
            draw.line(
                bar_img, WHITE,
                (self._selected_value_rect.left , self._selected_value_rect.bottom - 1),
                (self._selected_value_rect.right, self._selected_value_rect.bottom - 1),
                width=1
            )
        if self.selected_value != self.num_values - 1:
            draw.line(
                bar_img, WHITE,
                (self._selected_value_rect.left , self._selected_value_rect.top),
                (self._selected_value_rect.right, self._selected_value_rect.top),
                width=1
            )

        return bar_img

    def set_info(
            self: Self, num_values: int, value: int,
            selected_value: int, selected_hex_color: HexColor
    ) -> None:
        """
        Sets the value, selected value and values.

        Args:
            number of values, value, selected value
        """

        self.num_values = self.prev_num_values = max(num_values, NUM_VISIBLE_ROWS)
        self.value = self.prev_value = value
        self.selected_value = selected_value
        self._selected_hex_color = "#" + selected_hex_color
        self._unit_h = (self._bar_rect.h - (_SCROLLBAR_BORDER_DIM * 2)) / self.num_values

        usable_bottom: int = self._bar_rect.h - _SCROLLBAR_BORDER_DIM

        self._slider_rect.h = max(round(self._unit_h * NUM_VISIBLE_ROWS), 1)
        self._slider_rect.bottom = usable_bottom - round(self.value * self._unit_h)

        self._selected_value_rect.h = max(round(self._unit_h), 3)
        selected_value_offset_y: int = round(self.selected_value * self._unit_h)
        self._selected_value_rect.bottom = usable_bottom - selected_value_offset_y

        self.blit_sequence[0] = (self._get_bar_img(), self._bar_rect, self.layer)

    def _start_scroll(self: Self) -> None:
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

    def _handle_scroll(self: Self) -> None:
        """Handles changing the value depending on the mouse traveled distance."""

        self._traveled_y += MOUSE.prev_y - MOUSE.y
        if abs(self._traveled_y) >= self._unit_h:
            units_traveled: int = int(self._traveled_y / self._unit_h)
            self.value = min(max(
                self.value + units_traveled,
                0), self.num_values - NUM_VISIBLE_ROWS
            )
            self._traveled_y -= units_traveled * self._unit_h

    def _handle_scroll_with_keys(self: Self) -> None:
        """Handles changing the value with the keyboard."""

        if MOUSE.hovered_obj == self:
            if K_DOWN     in KEYBOARD.timed:
                self.value = max(self.value - 1               , 0)
            if K_UP       in KEYBOARD.timed:
                self.value = min(self.value + 1               , self.num_values - NUM_VISIBLE_ROWS)
            if K_PAGEDOWN in KEYBOARD.timed:
                self.value = max(self.value - NUM_VISIBLE_ROWS, 0)
            if K_PAGEUP   in KEYBOARD.timed:
                self.value = min(self.value + NUM_VISIBLE_ROWS, self.num_values - NUM_VISIBLE_ROWS)
            if K_HOME in KEYBOARD.timed:
                self.value = 0
            if K_END  in KEYBOARD.timed:
                self.value = self.num_values - NUM_VISIBLE_ROWS

        if MOUSE.hovered_obj in (self, self.down, self.up):
            if K_MINUS in KEYBOARD.timed:
                self.value = 0         if KEYBOARD.is_ctrl_on else max(self.value - 1, 0)
            if K_PLUS in KEYBOARD.timed:
                max_limit: int = self.num_values - NUM_VISIBLE_ROWS
                self.value = max_limit if KEYBOARD.is_ctrl_on else min(self.value + 1, max_limit)

    def upt(self: Self) -> None:
        """Allows to pick a value via scrolling, keyboard or arrow buttons."""

        if not MOUSE.pressed[MOUSE_LEFT]:
            self._is_scrolling = False
        elif MOUSE.hovered_obj == self and not self._is_scrolling:
            self._start_scroll()

        if self._is_scrolling:
            self._handle_scroll()
        if KEYBOARD.timed != ():
            self._handle_scroll_with_keys()

        is_down_clicked: bool = self.down.upt()
        if is_down_clicked:
            self.value = max(self.value - 1, 0)

        is_up_clicked: bool = self.up.upt()
        if is_up_clicked:
            self.value = min(self.value + 1, self.num_values - NUM_VISIBLE_ROWS)


class PalettesManager(UIElement):
    """Class to manage the color palettes with a drop-down menu and a scrollbar."""

    __slots__ = (
        "palettes", "clicked_indexes", "offsets_y", "colors_grid",
        "dropdown_indexes", "_dropdown_i", "_dropdown_offset_x", "_dropdown_offset_y",
        "_saved_hovered_checkbox", "_edit_i",
        "_scrollbar", "_add_palette_btn", "palette_dropdown",
        "_open_dropdown", "_dropdown_options",
        "_prev_palette_i", "_prev_offset_y", "_prev_dropdown_i",
    )

    def __init__(self: Self, pos: RectPos) -> None:
        """
        Creates the colors grid, a scrollbar, the add palette button and two dropdown-menus.

        Args:
            position
        """

        super().__init__()

        option: Button

        self.palettes: list[list[HexColor]] = []
        self.clicked_indexes: list[int] = []
        self.offsets_y: list[int] = []
        self.colors_grid: ColorsGrid = ColorsGrid(pos)

        self.dropdown_indexes: list[int] = []
        self._dropdown_i: int = -1
        self._dropdown_offset_x: int = 0
        self._dropdown_offset_y: int = 0

        self._saved_hovered_checkbox: LockedCheckbox | None = self.colors_grid.hovered_checkbox
        self._edit_i: int | None = None

        add_palette_btn_y: int = self.colors_grid.rect.y - 10

        self._scrollbar: _VerScrollbar = _VerScrollbar(
            RectPos(self.colors_grid.rect.right + 10, self.colors_grid.rect.bottom, "bottomleft")
        )
        self._add_palette_btn: Button = Button(
            RectPos(self.colors_grid.rect.right, add_palette_btn_y, "bottomright"),
            (ADD_OFF_IMG, ADD_ON_IMG), None, "(CTRL+SHIFT+P)"
        )
        self.palette_dropdown: Dropdown = Dropdown(
            RectPos(self._add_palette_btn.rect.x - 10, add_palette_btn_y, "bottomright"),
            (), "Palettes", text_h=18
        )

        self._open_dropdown: Button = Button(
            RectPos(0, 0, "topright"),
            (INFO_OFF_IMG, INFO_ON_IMG), None, "More Options",
            SPECIAL_LAYER - ELEMENT_LAYER, should_animate=False
        )
        self._open_dropdown.rec_set_active(False)

        options_texts: tuple[tuple[str, str], ...] = (
            ("edit"  , "(CTRL+E)"),
            ("delete", "(CTRL+DEL)"),
        )
        self._dropdown_options: tuple[Button, ...] = tuple([
            Button(
                RectPos(0, 0, "topleft"),
                (BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG), text, hovering_text,
                SPECIAL_LAYER, should_animate=False, text_h=20
            )
            for text, hovering_text in options_texts
        ])

        self._prev_palette_i: int = self.palette_dropdown.option_i
        self._prev_offset_y: int = self.colors_grid.offset_y
        self._prev_dropdown_i: int = self._dropdown_i

        self.sub_objs = (
            self.colors_grid, self._scrollbar,
            self._add_palette_btn, self.palette_dropdown,
            self._open_dropdown,
        ) + self._dropdown_options

        for option in self._dropdown_options:
            option.rec_set_active(False)
            option.should_follow_parent = False

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._edit_i = None

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._saved_hovered_checkbox = self.colors_grid.hovered_checkbox

    def _snap_objs(self: Self) -> None:
        """Snaps sub objects to the right position after the grid changes."""

        self._add_palette_btn.rec_move_to(
            round(self.colors_grid.rect.right    / my_vars.win_w_ratio),
            round((self.colors_grid.rect.y - 10) / my_vars.win_h_ratio),
        )
        self.palette_dropdown.rec_move_to(
            round((self._add_palette_btn.rect.x - 10) / my_vars.win_w_ratio),
            round((self.colors_grid.rect.y - 10)      / my_vars.win_h_ratio),
        )

    def try_add_color(self: Self, hex_color: HexColor) -> bool:
        """
        Adds or edits a color if it's not present then checks it.

        Args:
            jex color
        Returns:
            changed flag
        """

        prev_num_colors: int = len(self.colors_grid.colors)
        prev_offset_y: int = self.colors_grid.offset_y
        prev_colors_grid_y: int = self.colors_grid.rect.y

        if self._edit_i is None:
            self.colors_grid.try_add(hex_color)
        else:
            self.colors_grid.edit(self._edit_i, hex_color)
        self.colors_grid.check(self.colors_grid.colors.index(hex_color))

        self._scrollbar.set_info(
            num_values=ceil(len(self.colors_grid.colors) / NUM_COLS),
            value=self._scrollbar.value,
            selected_value=self.colors_grid.clicked_i // NUM_COLS,
            selected_hex_color=self.colors_grid.colors[self.colors_grid.clicked_i],
        )

        did_change: bool = (
            len(self.colors_grid.colors) != prev_num_colors or
            self.colors_grid.offset_y != prev_offset_y
        )

        if did_change:
            self.refresh_dropdown()
        if self.colors_grid.rect.y != prev_colors_grid_y:
            self._snap_objs()

        return did_change

    def add_palette(
            self: Self, colors: list[HexColor], color_i: int, offset_y: int,
            dropdown_i: int
    ) -> None:
        """
        Adds a palette to the info lists and the palette drop-down menu.

        Args:
            colors, clicked index, y offset,
            drop-down menu index
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

    def refresh_palettes_info(self: Self, palette_i: int) -> None:
        """
        Refreshes the stored palette info from the current info.

        Args:
            palette index
        """

        # Offsets by 1 because of placeholder option
        self.clicked_indexes[ palette_i - 1] = self.colors_grid.clicked_i
        self.offsets_y[       palette_i - 1] = self.colors_grid.offset_y
        self.dropdown_indexes[palette_i - 1] = self._dropdown_i

    def refresh_palette(self: Self) -> None:
        """Sets the grid, drop-down menus, scrollbar and button for the active palette."""

        prev_colors_grid_y: int = self.colors_grid.rect.y

        # Offsets by 1 because of placeholder option
        self.colors_grid.set_info(
            self.palettes[self.palette_dropdown.option_i - 1],
            self.clicked_indexes[self.palette_dropdown.option_i - 1],
            self.offsets_y[self.palette_dropdown.option_i - 1],
        )
        self._dropdown_i = self.dropdown_indexes[self.palette_dropdown.option_i - 1]
        checkbox_rect: Rect = self.colors_grid.visible_checkboxes[0].rect
        self._dropdown_offset_x = round(checkbox_rect.w / 2)
        self._dropdown_offset_y = round(checkbox_rect.h / 2)

        self._scrollbar.set_info(
            num_values=ceil(len(self.colors_grid.colors) / NUM_COLS),
            value=self.colors_grid.offset_y,
            selected_value=self.colors_grid.clicked_i // NUM_COLS,
            selected_hex_color=self.colors_grid.colors[self.colors_grid.clicked_i],
        )
        self.palette_dropdown.set_option_i(self.palette_dropdown.option_i)

        if self.colors_grid.rect.y != prev_colors_grid_y:
            self._snap_objs()
        self._prev_offset_y = self.colors_grid.offset_y
        self._prev_dropdown_i = self._dropdown_i

    def refresh_dropdown(self: Self) -> None:
        """Refreshes the drop-down menu position and activeness."""

        i: int
        option: Button

        colors_grid_visible_start_i: int = self.colors_grid.offset_y * NUM_COLS
        visible_checkboxes_len: int = len(self.colors_grid.visible_checkboxes)
        colors_grid_visible_end_i: int = colors_grid_visible_start_i + visible_checkboxes_len

        is_dropdown_on: bool = (
            colors_grid_visible_start_i <= self._dropdown_i < colors_grid_visible_end_i
        )
        if is_dropdown_on:
            dropdown_rel_i: int = self._dropdown_i - colors_grid_visible_start_i
            dropdown_checkbox: LockedCheckbox = self.colors_grid.visible_checkboxes[dropdown_rel_i]

            x: int = dropdown_checkbox.rect.x + self._dropdown_offset_x
            y: int = dropdown_checkbox.rect.y + self._dropdown_offset_y
            init_x: int = round(x / my_vars.win_w_ratio)
            init_y: int = round(y / my_vars.win_h_ratio)
            option_init_h: int = self._dropdown_options[0].init_imgs[0].get_height()
            for i, option in enumerate(self._dropdown_options):
                option.rec_move_to(init_x, init_y + (i * option_init_h))

        for option in self._dropdown_options:
            option.rec_set_active(is_dropdown_on)

    def _handle_scroll(self: Self) -> None:
        """Scrolls if the mouse is hovering a scrollable part."""

        if (
            MOUSE.hovered_obj in self.colors_grid.visible_checkboxes or
            MOUSE.hovered_obj == self.colors_grid or
            MOUSE.hovered_obj == self._scrollbar or
            MOUSE.hovered_obj == self._scrollbar.down or
            MOUSE.hovered_obj == self._scrollbar.up or
            MOUSE.hovered_obj == self._open_dropdown
        ):
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

        if K_e in KEYBOARD.timed:
            self._edit_i = self.colors_grid.clicked_i
        if K_DELETE in KEYBOARD.timed:
            prev_colors_grid_y: int = self.colors_grid.rect.y

            self.colors_grid.remove(self.colors_grid.clicked_i)
            self._scrollbar.num_values = ceil(len(self.colors_grid.colors) / NUM_COLS)
            if self._dropdown_i > self.colors_grid.clicked_i:
                self._dropdown_i -= 1

            if self.colors_grid.rect.y != prev_colors_grid_y:
                self._snap_objs()

    def _toggle_dropdown(
            self: Self, hovered_checkbox: LockedCheckbox | None, offset_x: int
    ) -> None:
        """
        Toggles the drop-down menu if clicking the same checkbox, moves it to the new one if not.

        Args:
            hovered checkbox, x offset
        """

        visible_checkboxes: tuple[LockedCheckbox, ...] = self.colors_grid.visible_checkboxes
        visible_start_i: int = self.colors_grid.offset_y * NUM_COLS
        visible_end_i: int = visible_start_i + len(visible_checkboxes)

        is_hovering_dropdown_checkbox: bool = (
            visible_start_i <= self._dropdown_i < visible_end_i and
            hovered_checkbox == visible_checkboxes[self._dropdown_i - visible_start_i]
        )
        if hovered_checkbox is None or is_hovering_dropdown_checkbox:
            self._dropdown_i = -1
        else:
            self._dropdown_i = visible_start_i + visible_checkboxes.index(hovered_checkbox)
            self._dropdown_offset_x = MOUSE.x - hovered_checkbox.rect.x + offset_x
            self._dropdown_offset_y = MOUSE.y - hovered_checkbox.rect.y

    def _upt_dropdown(self: Self) -> None:
        """Updates the drop-down menu."""

        is_edit_clicked: bool = self._dropdown_options[0].upt()
        if is_edit_clicked:
            self._edit_i = self._dropdown_i

        is_remove_clicked: bool = self._dropdown_options[1].upt()
        if is_remove_clicked:
            prev_colors_grid_y: int = self.colors_grid.rect.y

            self.colors_grid.remove(self._dropdown_i)
            self._scrollbar.num_values = ceil(len(self.colors_grid.colors) / NUM_COLS)
            self._dropdown_i = min(self._dropdown_i, len(self.colors_grid.colors) - 1)

            if self.colors_grid.rect.y != prev_colors_grid_y:
                self._snap_objs()

    def _refresh_grid(self: Self, prev_num_colors: int) -> bool:
        """
        Refreshes the grid before any external refreshes happens.

        Args:
            previous number of colors
        Returns:
            changed flag
        """

        if self.palette_dropdown.option_i != self._prev_palette_i:
            self.refresh_palettes_info(self._prev_palette_i)
            self.refresh_palette()  # Also refreshes offset_y
        elif self.colors_grid.offset_y != self._prev_offset_y:
            self.colors_grid.set_offset_y(self.colors_grid.offset_y)

        return (
            self.palette_dropdown.option_i != self._prev_palette_i or
            len(self.colors_grid.colors) != prev_num_colors or
            self.colors_grid.offset_y != self._prev_offset_y
        )

    def refresh(self: Self) -> None:
        """Refreshes the grid, scrollbar, drop-down menu and open drop-down menu button."""

        if self.colors_grid.clicked_i != self.colors_grid.prev_clicked_i:
            self.colors_grid.check(self.colors_grid.clicked_i)

        selected_hex_color: HexColor = "#" + self.colors_grid.colors[self.colors_grid.clicked_i]
        if (
            self._scrollbar.num_values != self._scrollbar.prev_num_values or
            self._scrollbar.value != self._scrollbar.prev_value or
            self._scrollbar._selected_hex_color != selected_hex_color
        ):
            self._scrollbar.set_info(
                self._scrollbar.num_values,
                self._scrollbar.value,
                selected_value=self.colors_grid.clicked_i // NUM_COLS,
                selected_hex_color=self.colors_grid.colors[self.colors_grid.clicked_i],
            )

        if (
            self.palette_dropdown.option_i != self._prev_palette_i or
            self.colors_grid.offset_y != self._prev_offset_y or
            self._dropdown_i != self._prev_dropdown_i
        ):
            self.refresh_dropdown()
            MOUSE.released[MOUSE_LEFT] = False  # Doesn't click objects below

        if (
            self.colors_grid.hovered_checkbox != self._saved_hovered_checkbox and
            MOUSE.hovered_obj != self._open_dropdown
        ):
            if self.colors_grid.hovered_checkbox is not None:
                self._open_dropdown.rec_move_to(
                    self.colors_grid.hovered_checkbox.rect.right - 4,
                    self.colors_grid.hovered_checkbox.rect.y + 4,
                )
            self._saved_hovered_checkbox = self.colors_grid.hovered_checkbox
            self._open_dropdown.rec_set_active(self.colors_grid.hovered_checkbox is not None)

        self._prev_palette_i = self.palette_dropdown.option_i
        self._prev_offset_y = self.colors_grid.offset_y
        self._prev_dropdown_i = self._dropdown_i

    def upt(self: Self) -> tuple[HexColor, bool, HexColor | None]:
        """
        Allows selecting a color, using a dropdown, a scrollbar and handling palettes.

        Returns:
            selected color, changed flag, color to edit (can be None)
        """

        prev_num_colors: int = len(self.colors_grid.colors)

        if MOUSE.scroll_amount != 0:
            self._handle_scroll()

        self.colors_grid.upt()
        self._scrollbar.value = self.colors_grid.offset_y

        self._scrollbar.upt()
        self.colors_grid.offset_y = self._scrollbar.value

        is_add_palette_btn_clicked: bool = self._add_palette_btn.upt()
        is_ctrl_shift_p_pressed: bool = (
            KEYBOARD.is_ctrl_on and KEYBOARD.is_shift_on and
            K_p in KEYBOARD.timed
        )
        if is_add_palette_btn_clicked or is_ctrl_shift_p_pressed:
            self.add_palette([HEX_BLACK], color_i=0, offset_y=0, dropdown_i=-1)
            # Offsets by 1 because of placeholder option
            self.palette_dropdown.option_i = len(self.palettes)

        if KEYBOARD.is_ctrl_on and K_p in KEYBOARD.pressed:
            self._handle_palette_shortcuts()

        self.palette_dropdown.upt()

        if KEYBOARD.is_ctrl_on:
            self._handle_dropdown_shortcuts()
        if MOUSE.released[MOUSE_RIGHT]:
            self._toggle_dropdown(self.colors_grid.hovered_checkbox, offset_x=4)
        if self._open_dropdown.is_active:
            is_open_dropdown_clicked: bool = self._open_dropdown.upt()
            if is_open_dropdown_clicked:
                self._toggle_dropdown(self._saved_hovered_checkbox, offset_x=2)

        if self._dropdown_i != -1:
            self._upt_dropdown()

        did_change: bool = self._refresh_grid(prev_num_colors)
        return (
            self.colors_grid.colors[self.colors_grid.clicked_i],
            did_change,
            None if self._edit_i is None else self.colors_grid.colors[self._edit_i],
        )
