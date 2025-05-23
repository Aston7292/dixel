"""
Class to manage color palettes, includes a drop-down menu and a scrollbar.

Everything is refreshed automatically.
"""

from math import ceil
from typing import Final, Optional

import pygame as pg
from pygame.locals import *

from src.classes.checkbox_grid import LockedCheckbox, CheckboxGrid
from src.classes.clickable import Button, SpammableButton
from src.classes.devices import Mouse, Keyboard

from src.utils import RectPos, ObjInfo, add_border, resize_obj, rec_move_rect
from src.type_utils import XY, WH, RGBColor, HexColor, CheckboxInfo, BlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_RIGHT, WHITE, DARKER_GRAY, HEX_BLACK, NUM_VISIBLE_CHECKBOX_GRID_ROWS,
    BG_LAYER, ELEMENT_LAYER, SPECIAL_LAYER
)
from src.imgs import (
    BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG,
    ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG, ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG
)


_SCROLLBAR_BORDER_DIM: Final[int] = 2
_COLOR_IMG: Final[pg.Surface] = pg.Surface((32, 32)).convert()


def _get_color_info(hex_color: HexColor) -> tuple[pg.Surface, str]:
    """
    Creates the checkbox info for a color.

    Args:
        hexadecimal color
    Returns:
        image, text
    """

    color: pg.Color = pg.Color("#" + hex_color)
    _COLOR_IMG.fill(color)
    img: pg.Surface = add_border(_COLOR_IMG, DARKER_GRAY)

    rgb_text: str = str(color[:3])
    hex_text: str = "#" + hex_color

    return img, rgb_text + "\n" + hex_text


class VerScrollbar:
    """Class to create a vertical scrollbar."""

    __slots__ = (
        "_bar_init_pos", "_bar_img", "_bar_rect", "_bar_init_w", "_bar_init_h", "value",
        "_clicked_value", "num_values", "_unit_h", "_slider_img", "_slider_rect",
        "_clicked_value_img", "_clicked_value_rect", "_prev_mouse_y", "_traveled_y",
        "_is_scrolling", "layer", "_arrow_up", "_arrow_down", "objs_info"
    )

    cursor_type: int = SYSTEM_CURSOR_HAND

    def __init__(self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the bar and slider.

        Args:
            position, base layer (default = BG_LAYER)
        """

        self.value: int
        self._clicked_value: int

        self._bar_init_w: int
        self._bar_init_h: int

        self._bar_init_pos: RectPos = pos

        self._bar_img: pg.Surface = pg.Surface((16, 128)).convert()
        pg.draw.rect(self._bar_img, WHITE, self._bar_img.get_rect(), _SCROLLBAR_BORDER_DIM)
        self._bar_rect: pg.Rect = pg.Rect(0, 0, *self._bar_img.get_size())
        bar_init_xy: XY = (self._bar_init_pos.x, self._bar_init_pos.y)
        setattr(self._bar_rect, self._bar_init_pos.coord_type, bar_init_xy)

        self._bar_init_w, self._bar_init_h = self._bar_rect.size

        usable_bar_w: int = self._bar_rect.w - _SCROLLBAR_BORDER_DIM * 2
        usable_bar_h: int = self._bar_rect.h - _SCROLLBAR_BORDER_DIM * 2

        self.value = self._clicked_value = 0
        self.num_values: int = NUM_VISIBLE_CHECKBOX_GRID_ROWS
        self._unit_h: float = usable_bar_h / self.num_values

        self._slider_img: pg.Surface = pg.Surface((usable_bar_w, usable_bar_h)).convert()
        self._slider_img.fill((100, 100, 100))
        self._slider_rect: pg.Rect = pg.Rect(0, 0, *self._slider_img.get_size())
        self._slider_rect.bottomleft = (
            self._bar_rect.x + _SCROLLBAR_BORDER_DIM, self._bar_rect.bottom - _SCROLLBAR_BORDER_DIM
        )

        self._clicked_value_img: pg.Surface = pg.Surface((usable_bar_w, self._unit_h)).convert()
        self._clicked_value_img.fill(DARKER_GRAY)
        self._clicked_value_rect: pg.Rect = pg.Rect(0, 0, *self._clicked_value_img.get_size())
        self._clicked_value_rect.bottomleft = (
            self._bar_rect.x + _SCROLLBAR_BORDER_DIM, self._bar_rect.bottom - _SCROLLBAR_BORDER_DIM
        )

        self._prev_mouse_y: int = pg.mouse.get_pos()[1]
        self._traveled_y: float = 0
        self._is_scrolling: bool = False

        self.layer: int = base_layer + ELEMENT_LAYER

        self._arrow_up: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.y - 5, "midbottom"),
            [ARROW_UP_OFF_IMG, ARROW_UP_ON_IMG], "Up"
        )
        self._arrow_down: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.bottom + 5, "midtop"),
            [ARROW_DOWN_OFF_IMG, ARROW_DOWN_ON_IMG], "Down"
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(self._arrow_up), ObjInfo(self._arrow_down)]

    @property
    def blit_sequence(self) -> list[BlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._bar_img, self._bar_rect, self.layer),
            (self._slider_img, self._slider_rect, self.layer),
            (self._clicked_value_img, self._clicked_value_rect, self.layer)
        ]

    def get_hovering(self, mouse_xy: XY) -> bool:
        """
        Gets the hovering flag.

        Args:
            mouse xy
        Returns:
            hovering flag
        """

        return self._bar_rect.collidepoint(mouse_xy)

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._prev_mouse_y = pg.mouse.get_pos()[1]
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
            self._bar_init_pos, self._bar_init_w, self._bar_init_h, win_w_ratio, win_h_ratio
        )
        self._bar_img = pg.Surface(self._bar_rect.size).convert()
        pg.draw.rect(self._bar_img, WHITE, self._bar_img.get_rect(), _SCROLLBAR_BORDER_DIM)
        setattr(self._bar_rect, self._bar_init_pos.coord_type, bar_xy)

        # More accurate
        self._unit_h = (self._bar_rect.h - _SCROLLBAR_BORDER_DIM * 2) / self.num_values
        usable_bar_w: int = self._bar_rect.w - _SCROLLBAR_BORDER_DIM * 2
        usable_bar_bottom: int = self._bar_rect.bottom - _SCROLLBAR_BORDER_DIM

        slider_h: int = max(round(self._unit_h * NUM_VISIBLE_CHECKBOX_GRID_ROWS), 1)

        self._slider_img = pg.transform.scale(self._slider_img, (usable_bar_w, slider_h)).convert()
        self._slider_rect.size = (usable_bar_w, slider_h)
        self._slider_rect.bottomleft = (
            self._bar_rect.x + _SCROLLBAR_BORDER_DIM,
            usable_bar_bottom - round(self.value * self._unit_h)
        )

        clicked_value_wh: WH = (usable_bar_w, max(round(self._unit_h), 1))

        self._clicked_value_img = pg.transform.scale(
            self._clicked_value_img, clicked_value_wh
        ).convert()
        self._clicked_value_rect.size = clicked_value_wh
        self._clicked_value_rect.bottomleft = (
            self._bar_rect.x + _SCROLLBAR_BORDER_DIM,
            usable_bar_bottom - round(self._clicked_value * self._unit_h)
        )

    def set_value(self, value: int) -> None:
        """
        Sets the bar on a specif value.

        Args:
            value
        """

        self.value = value
        usable_bar_bottom: int = self._bar_rect.bottom - _SCROLLBAR_BORDER_DIM
        self._slider_rect.bottom = usable_bar_bottom - round(self.value * self._unit_h)

    def set_clicked_value(self, clicked_row: int) -> None:
        """
        Sets the value of the clicked color row.

        Args:
            clicked row
        """

        self._clicked_value = clicked_row
        usable_bar_bottom: int = self._bar_rect.bottom - _SCROLLBAR_BORDER_DIM
        clicked_value_offset_y: int = round(self._clicked_value * self._unit_h)
        self._clicked_value_rect.bottom = usable_bar_bottom - clicked_value_offset_y

    def set_num_values(self, num_values: int) -> None:
        """
        Sets the number of values the scrollbar can have.

        Args:
            number of values
        """

        self.num_values = max(num_values, NUM_VISIBLE_CHECKBOX_GRID_ROWS)
        self.value = min(self.value, self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS)
        self._unit_h = (self._bar_rect.h - _SCROLLBAR_BORDER_DIM * 2) / self.num_values

        usable_bar_bottom: int = self._bar_rect.bottom - _SCROLLBAR_BORDER_DIM

        self._slider_rect.h = max(round(self._unit_h * NUM_VISIBLE_CHECKBOX_GRID_ROWS), 1)
        self._slider_rect.bottom = usable_bar_bottom - round(self.value * self._unit_h)

        self._slider_img = pg.transform.scale(
            self._slider_img, (self._slider_img.get_width(), self._slider_rect.h)
        ).convert()

        self._clicked_value_rect.h = max(round(self._unit_h), 1)
        clicked_value_offset_y: int = round(self._clicked_value * self._unit_h)
        self._clicked_value_rect.bottom = usable_bar_bottom - clicked_value_offset_y

        clicked_value_w: int = self._clicked_value_img.get_width()
        self._clicked_value_img = pg.transform.scale(
            self._clicked_value_img, (clicked_value_w, self._clicked_value_rect.h)
        ).convert()

    def _start_scrolling(self, mouse_y: int) -> None:
        """
        Changes the value depending on the mouse position and sets the scrolling flag to True.

        Args:
            mouse y
        """

        if mouse_y < self._slider_rect.top or mouse_y > self._slider_rect.bottom:
            value: int = int((self._bar_rect.bottom - mouse_y) / self._unit_h)
            if mouse_y < self._slider_rect.top:
                value -= NUM_VISIBLE_CHECKBOX_GRID_ROWS
            self.value = min(max(value, 0), self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS)

        self._traveled_y = 0
        self._is_scrolling = True

    def _scroll(self, mouse_y: int) -> None:
        """
        Changes the value depending on the mouse traveled distance.

        Args:
            mouse y
        """

        self._traveled_y += self._prev_mouse_y - mouse_y
        if abs(self._traveled_y) >= self._unit_h:
            units_traveled: int = int(self._traveled_y / self._unit_h)
            max_value: int = self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS
            self.value = min(max(self.value + units_traveled, 0), max_value)
            self._traveled_y -= units_traveled * self._unit_h

    def _scroll_with_keys(self, timed_keys: list[int]) -> None:
        """
        Scrolls with the keyboard.

        Args:
            timed keys
        """

        max_value: int = self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS
        if K_DOWN in timed_keys:
            self.value = max(self.value - 1, 0)
        if K_UP in timed_keys:
            self.value = min(self.value + 1, max_value)
        if K_PAGEDOWN in timed_keys:
            self.value = max(self.value - NUM_VISIBLE_CHECKBOX_GRID_ROWS, 0)
        if K_PAGEUP in timed_keys:
            self.value = min(self.value + NUM_VISIBLE_CHECKBOX_GRID_ROWS, max_value)
        if K_HOME in timed_keys:
            self.value = 0
        if K_END in timed_keys:
            self.value = max_value

    def _scroll_with_buttons(self, mouse: Mouse) -> None:
        """
        Changes the value depending on up and down buttons.

        Args:
            mouse
        """

        is_arrow_up_clicked: bool = self._arrow_up.upt(mouse)
        if is_arrow_up_clicked:
            self.value = min(self.value + 1, self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS)

        is_arrow_down_clicked: bool = self._arrow_down.upt(mouse)
        if is_arrow_down_clicked:
            self.value = max(self.value - 1, 0)

    def upt(self, mouse: Mouse, timed_keys: list[int]) -> None:
        """
        Allows to pick a value via scrolling, keys, mouse wheel or arrow buttons.

        Args:
            mouse, timed keys
        """

        prev_value: int = self.value

        if not mouse.pressed[MOUSE_LEFT]:
            self._is_scrolling = False
        elif mouse.hovered_obj == self and not self._is_scrolling:
            self._start_scrolling(mouse.y)

        if self._is_scrolling:
            self._scroll(mouse.y)
        if mouse.hovered_obj == self and timed_keys != []:
            self._scroll_with_keys(timed_keys)
        self._scroll_with_buttons(mouse)

        if self.value != prev_value:
            self.set_value(self.value)

        self._prev_mouse_y = mouse.y


class PaletteManager:
    """Class to manage color palettes, includes a drop-down menu."""

    __slots__ = (
        "colors", "colors_grid", "_dropdown_options", "dropdown_i", "_dropdown_offset_x",
        "_dropdown_offset_y", "is_dropdown_on", "_edit_i", "is_editing_color", "blit_sequence",
        "_win_w_ratio", "_win_h_ratio", "objs_info", "_dropdown_info_start_i",
        "_dropdown_info_end_i", "_scrollbar"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of colors and the drop-down menu to modify it.

        Args:
            position
        """

        self._dropdown_offset_x: int
        self._dropdown_offset_y: int
        self._win_w_ratio: float
        self._win_h_ratio: float
        obj_info: ObjInfo

        self.colors: list[HexColor] = [HEX_BLACK]

        colors_grid_info: list[CheckboxInfo] = [_get_color_info(HEX_BLACK)]
        self.colors_grid: CheckboxGrid = CheckboxGrid(pos, colors_grid_info, 5, True, True)

        options_texts: tuple[tuple[str, str], ...] = (
            ("edit", "CTRL+E"),
            ("delete", "CTRL+DEL")
        )

        button_imgs: list[pg.Surface] = [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG]
        self._dropdown_options: list[Button] = [
            Button(RectPos(0, 0, "topleft"), button_imgs, text, hovering_text, SPECIAL_LAYER, 20)
            for text, hovering_text in options_texts
        ]
        self.dropdown_i: int = 0
        self._dropdown_offset_x = self._dropdown_offset_y = 0
        self.is_dropdown_on: bool = False

        self._edit_i: int = 0
        self.is_editing_color: bool = False

        self.blit_sequence: list[BlitInfo] = []
        self._win_w_ratio = self._win_h_ratio = 1
        self.objs_info: list[ObjInfo] = [ObjInfo(self.colors_grid)]

        self._dropdown_info_start_i: int = len(self.objs_info)
        self.objs_info.extend([ObjInfo(option) for option in self._dropdown_options])
        self._dropdown_info_end_i: int = len(self.objs_info)

        self._scrollbar: VerScrollbar = VerScrollbar(
            RectPos(self.colors_grid.rect.right + 10, self.colors_grid.rect.bottom, "bottomleft")
        )
        self.objs_info.append(ObjInfo(self._scrollbar))

        for obj_info in self.objs_info[self._dropdown_info_start_i:self._dropdown_info_end_i]:
            obj_info.set_active(False)

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio

    def _handle_dropdown_movement(self) -> None:
        """Sets the dropdown visibility and if it's visible moves it to the correct position."""

        obj_info: ObjInfo
        option: Button

        checkbox: LockedCheckbox = self.colors_grid.checkboxes[self.dropdown_i]
        is_visible: bool = self.objs_info[self._dropdown_info_start_i].is_active
        should_be_visible: bool = checkbox in self.colors_grid.visible_checkboxes
        if is_visible != should_be_visible:
            for obj_info in self.objs_info[self._dropdown_info_start_i:self._dropdown_info_end_i]:
                obj_info.set_active(should_be_visible)

        if should_be_visible:
            start_x: int = checkbox.rect.x + self._dropdown_offset_x
            start_y: int = checkbox.rect.y + self._dropdown_offset_y
            option_init_x: int = round(start_x / self._win_w_ratio)
            option_init_y: int = round(start_y / self._win_h_ratio)
            for option in self._dropdown_options:
                rec_move_rect(
                    option, option_init_x, option_init_y, self._win_w_ratio, self._win_h_ratio
                )
                option_init_y += int(option.rect.h / self._win_h_ratio)

    def set_info(
            self, hex_colors: list[HexColor], color_i: int, offset_y: int,
            dropdown_i: Optional[int]
    ) -> None:
        """
        Sets the colors, offset, clicked color and dropdown.

        Args:
            hexadecimal colors, color index, grid y offset, dropdown index (can be None)
        """

        checkbox_w: int
        checkbox_h: int

        self.colors = hex_colors

        colors_grid_info: list[CheckboxInfo] = [_get_color_info(color) for color in self.colors]
        self.colors_grid.set_grid(colors_grid_info, color_i, offset_y)

        if dropdown_i is not None:
            self.dropdown_i = dropdown_i
            checkbox_w, checkbox_h = self.colors_grid.checkboxes[0].rect.size
            self._dropdown_offset_x = round(checkbox_w / 2)
            self._dropdown_offset_y = round(checkbox_h / 2)
            self.is_dropdown_on = True
            self._handle_dropdown_movement()

        self._scrollbar.set_num_values(ceil(len(self.colors) / self.colors_grid.num_cols))
        self._scrollbar.set_value(self.colors_grid.offset_y)
        self._scrollbar.set_clicked_value(self.colors_grid.clicked_i // self.colors_grid.num_cols)

    def add(self, rgb_color: RGBColor) -> bool:
        """
        Adds a color to the palette or edits one based on the editing color flag.

        Args:
            rgb color
        Returns
            refresh objects flag
        """

        hex_color: HexColor = "{:02x}{:02x}{:02x}".format(*rgb_color)
        should_refresh_objs: bool = False
        if hex_color not in self.colors:
            if self.is_editing_color:
                self.colors[self._edit_i] = hex_color
                self.colors_grid.edit(self._edit_i, *_get_color_info(hex_color))
            else:
                self.colors.append(hex_color)
                self.colors_grid.add(*_get_color_info(hex_color))
                self._scrollbar.set_num_values(ceil(len(self.colors) / self.colors_grid.num_cols))
                should_refresh_objs = True
        self.colors_grid.check(self.colors.index(hex_color))

        if self.is_dropdown_on:
            self._handle_dropdown_movement()
        self._scrollbar.set_clicked_value(self.colors_grid.clicked_i // self.colors_grid.num_cols)
        self.is_editing_color = False

        return should_refresh_objs

    def _toggle_dropdown(self, mouse: Mouse, checkbox: LockedCheckbox) -> None:
        """
        Toggles the dropdown menu.

        Args:
            mouse, checkbox.
        """

        obj_info: ObjInfo

        visible_start_i: int = self.colors_grid.offset_y * self.colors_grid.num_cols
        checkbox_i: int = visible_start_i + self.colors_grid.visible_checkboxes.index(checkbox)
        self.is_dropdown_on = not self.is_dropdown_on if self.dropdown_i == checkbox_i else True
        if not self.is_dropdown_on:
            for obj_info in self.objs_info[self._dropdown_info_start_i:self._dropdown_info_end_i]:
                obj_info.set_active(self.is_dropdown_on)
        else:
            self.dropdown_i = checkbox_i
            self._dropdown_offset_x = mouse.x - checkbox.rect.x
            self._dropdown_offset_y = mouse.y - checkbox.rect.y + 1
            self._handle_dropdown_movement()

    def _check_dropdown_toggle(self, mouse: Mouse) -> None:
        """
        Opens or closes the dropdown menu if the mouse right-clicks a checkbox.

        Args:
            mouse
        """

        checkbox: LockedCheckbox
        obj_info: ObjInfo

        for checkbox in self.colors_grid.visible_checkboxes:
            if mouse.hovered_obj == checkbox:
                self._toggle_dropdown(mouse, checkbox)

                return

        if self.is_dropdown_on:
            self.is_dropdown_on = False
            for obj_info in self.objs_info[self._dropdown_info_start_i:self._dropdown_info_end_i]:
                obj_info.set_active(self.is_dropdown_on)

    def _handle_dropdown_shortcuts(self, keyboard: Keyboard) -> None:
        """
        Handles the drop-down menu shortcuts.

        Args:
            keyboard
        """

        if K_e in keyboard.pressed:
            self._edit_i = self.colors_grid.clicked_i
            self.is_editing_color = True

        if K_DELETE in keyboard.timed:
            self.colors.pop(self.colors_grid.clicked_i)
            self.colors = self.colors or [HEX_BLACK]
            fallback_info: CheckboxInfo = _get_color_info(HEX_BLACK)
            self.colors_grid.remove(self.colors_grid.clicked_i, *fallback_info)
            if self.dropdown_i > self.colors_grid.clicked_i:
                self.dropdown_i -= 1

    def _handle_grid_shortcuts(self, keys: list[int]) -> None:
        """
        Handles the colors grid shortcuts.

        Args:
            keyboard
        """

        max_color_i_shift_shortcut: int = min(len(self.colors_grid.checkboxes), 9)
        for k in range(K_1, K_1 + max_color_i_shift_shortcut):
            if k in keys:
                self.colors_grid.clicked_i = k - K_1

    def _upt_dropdown_menu(self, mouse: Mouse) -> None:
        """
        Updates the drop-down menu options.

        Args:
            mouse
        """

        is_edit_clicked: bool = self._dropdown_options[0].upt(mouse)
        if is_edit_clicked:
            self._edit_i = self.dropdown_i
            self.is_editing_color = True
            mouse.released[MOUSE_LEFT] = False  # Don't click objects below

        is_remove_clicked: bool = self._dropdown_options[1].upt(mouse)
        if is_remove_clicked:
            self.colors.pop(self.dropdown_i)
            self.colors = self.colors or [HEX_BLACK]
            fallback_info: CheckboxInfo = _get_color_info(HEX_BLACK)
            self.colors_grid.remove(self.dropdown_i, *fallback_info)
            self.dropdown_i = min(self.dropdown_i, len(self.colors_grid.checkboxes) - 1)
            mouse.released[MOUSE_LEFT] = False  # Don't click objects below

    def _scroll_with_wheel(self, mouse: Mouse) -> None:
        """
        Scrolls with the mouse wheel if the grid or scrollbar are hovered.

        Args:
            mouse
        """

        is_hovering_grid: bool = (
            mouse.hovered_obj == self.colors_grid or self.colors_grid.hovered_checkbox is not None
        )

        if is_hovering_grid or mouse.hovered_obj == self._scrollbar:
            scrollbar_value: int = self._scrollbar.value + mouse.scroll_amount
            scrollbar_max_limit: int = self._scrollbar.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS
            self._scrollbar.set_value(min(max(scrollbar_value, 0), scrollbar_max_limit))

    def _adjust_scrollbar(self, prev_num_colors: int, prev_clicked_i: int) -> None:
        """
        Adjusts the scrollbar if any of its values changed.

        Args:
            previous number of colors, previous clicked checkbox index
        """

        if len(self.colors) != prev_num_colors:
            self._scrollbar.set_num_values(ceil(len(self.colors) / self.colors_grid.num_cols))

        if self.colors_grid.offset_y != self._scrollbar.value:
            self._scrollbar.set_value(self.colors_grid.offset_y)

        if self.colors_grid.clicked_i != prev_clicked_i:
            clicked_row: int = self.colors_grid.clicked_i // self.colors_grid.num_cols
            self._scrollbar.set_clicked_value(clicked_row)

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[HexColor, bool, Optional[HexColor]]:
        """
        Allows selecting a color and making a drop-down menu appear on right click.

        Args:
            mouse, keyboard
        Returns:
            hexadecimal selected color, changed flag, hexadecimal color to edit (can be None)
        """

        # TODO: refactor this
        if mouse.released[MOUSE_RIGHT]:
            self._check_dropdown_toggle(mouse)

        prev_num_colors: int = len(self.colors)
        prev_clicked_i: int = self.colors_grid.clicked_i
        prev_offset_y: int = self.colors_grid.offset_y
        prev_dropdown_i: int = self.dropdown_i

        if keyboard.is_ctrl_on:
            self._handle_dropdown_shortcuts(keyboard)
        if keyboard.is_shift_on:
            self._handle_grid_shortcuts(keyboard.pressed)
        if self.objs_info[self._dropdown_info_start_i].is_active:
            self._upt_dropdown_menu(mouse)

        prev_scrollbar_value: int = self._scrollbar.value
        self._scrollbar.upt(mouse, keyboard.timed)
        if mouse.scroll_amount != 0:
            self._scroll_with_wheel(mouse)

        if self._scrollbar.value != prev_scrollbar_value:
            self.colors_grid.set_offset_y(self._scrollbar.value)

        self.colors_grid.upt(mouse, keyboard)
        self.colors_grid.refresh()
        self._adjust_scrollbar(prev_num_colors, prev_clicked_i)

        did_offset_y_change: bool = self.colors_grid.offset_y != prev_offset_y
        did_dropdown_i_change: bool = self.dropdown_i != prev_dropdown_i
        if self.is_dropdown_on and (did_offset_y_change or did_dropdown_i_change):
            self._handle_dropdown_movement()

        did_change: bool = did_offset_y_change or len(self.colors) != prev_num_colors
        color_to_edit: Optional[HexColor] = None
        if self.is_editing_color:
            color_to_edit = self.colors[self._edit_i]

        return self.colors[self.colors_grid.clicked_i], did_change, color_to_edit
