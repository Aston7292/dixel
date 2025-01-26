"""Class to manage color palettes, includes a drop-down menu."""

from math import ceil
from typing import Final, Optional

import pygame as pg

from src.classes.ui import BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG
from src.classes.checkbox_grid import LockedCheckbox, CheckboxGrid
from src.classes.clickable import Button, SpammableButton

from src.utils import (
    RectPos, Size, Ratio, ObjInfo, Mouse, Keyboard, get_img, add_border, resize_obj, rec_move_rect
)
from src.type_utils import PosPair, SizePair, Color, CheckboxInfo, LayeredBlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_RIGHT, BLACK, WHITE, LIGHT_GRAY, NUM_VISIBLE_CHECKBOX_GRID_ROWS,
    BG_LAYER, ELEMENT_LAYER, SPECIAL_LAYER
)

OptionsInfo = tuple[tuple[str, str], ...]

SCROLLBAR_BORDER_DIM: Final[int] = 2

BUTTON_S_OFF_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_OFF_IMG, (64, 32))
BUTTON_S_ON_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_ON_IMG, (64, 32))
# Have larger hitboxes
ARROW_UP_IMG_OFF: Final[pg.Surface] = get_img("sprites", "arrow_up_button_off.png")
ARROW_UP_IMG_ON: Final[pg.Surface] = get_img("sprites", "arrow_up_button_on.png")
ARROW_DOWN_IMG_OFF: Final[pg.Surface] = pg.transform.rotate(ARROW_UP_IMG_OFF, 180)
ARROW_DOWN_IMG_ON: Final[pg.Surface] = pg.transform.rotate(ARROW_UP_IMG_ON, 180)

OPTIONS_TEXTS: Final[OptionsInfo] = (
    ("edit", "(CTRL+E)"),
    ("delete", "(CTRL+DEL)")
)


def _get_color_info(color: Color) -> tuple[pg.Surface, str]:
    """
    Creates the checkbox info for a color.

    Args:
        color
    Returns:
        info
    """

    img: pg.Surface = pg.Surface((32, 32))
    img.fill(color)
    img = add_border(img, LIGHT_GRAY)

    rgb_text: str = "({}, {}, {})".format(*color)
    hex_text: str = "(#{:02x}{:02x}{:02x})".format(*color)
    text: str = f"{rgb_text}\n{hex_text}"

    return img, text


class VerScrollbar:
    """Class to create a vertical scrollbar."""

    __slots__ = (
        "_bar_init_pos", "_bar_img", "_bar_rect", "_bar_init_size", "value", "_clicked_value",
        "num_values", "_unit_h", "_slider_img", "_slider_rect", "_clicked_value_img",
        "_clicked_value_rect", "_is_scrolling", "_prev_mouse_y", "_traveled_y",
        "_layer", "_hovering_layer", "cursor_type", "_arrow_up", "_arrow_down", "objs_info"
    )

    def __init__(self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the bar and slider.

        Args:
            position, base layer (default = BG_LAYER)
        """

        self._bar_init_pos: RectPos = pos

        self._bar_img: pg.Surface = pg.Surface((15, 100))
        pg.draw.rect(self._bar_img, WHITE, self._bar_img.get_rect(), SCROLLBAR_BORDER_DIM)
        bar_xy: PosPair = self._bar_init_pos.xy
        self._bar_rect: pg.Rect = self._bar_img.get_rect(**{self._bar_init_pos.coord_type: bar_xy})

        self._bar_init_size: Size = Size(*self._bar_rect.size)
        usable_bar_w: int = self._bar_init_size.w - (SCROLLBAR_BORDER_DIM * 2)
        usable_bar_h: int = self._bar_init_size.h - (SCROLLBAR_BORDER_DIM * 2)

        usable_bar_x: int = self._bar_rect.x + SCROLLBAR_BORDER_DIM
        usable_bar_bottom: int = self._bar_rect.bottom - SCROLLBAR_BORDER_DIM
        usable_bar_bottomleft: PosPair = (usable_bar_x, usable_bar_bottom)

        self.value: int = 0
        self._clicked_value: int = 0
        self.num_values: int = NUM_VISIBLE_CHECKBOX_GRID_ROWS
        self._unit_h: float = usable_bar_h / self.num_values

        self._slider_img: pg.Surface = pg.Surface((usable_bar_w, usable_bar_h))
        self._slider_img.fill(LIGHT_GRAY)
        self._slider_rect: pg.Rect = self._slider_img.get_rect(bottomleft=usable_bar_bottomleft)

        self._clicked_value_img: pg.Surface = pg.Surface((usable_bar_w, self._unit_h))
        darker_gray: Color = [50, 50, 50]
        self._clicked_value_img.fill(darker_gray)
        self._clicked_value_rect: pg.Rect = self._clicked_value_img.get_rect(
            bottomleft=usable_bar_bottomleft
        )

        self._prev_mouse_y: int = pg.mouse.get_pos()[1]
        self._traveled_y: int = 0
        self._is_scrolling: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self.cursor_type: int = pg.SYSTEM_CURSOR_HAND

        arrow_up_imgs: list[pg.Surface] = [ARROW_UP_IMG_OFF, ARROW_UP_IMG_ON]
        arrow_down_imgs: list[pg.Surface] = [ARROW_DOWN_IMG_OFF, ARROW_DOWN_IMG_ON]

        self._arrow_up: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.y - 5, "midbottom"), arrow_up_imgs
        )
        self._arrow_down: SpammableButton = SpammableButton(
            RectPos(self._bar_rect.centerx, self._bar_rect.bottom + 5, "midtop"), arrow_down_imgs
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(self._arrow_up), ObjInfo(self._arrow_down)]

    def get_blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._bar_img, self._bar_rect.topleft, self._layer),
            (self._slider_img, self._slider_rect.topleft, self._layer),
            (self._clicked_value_img, self._clicked_value_rect.topleft, self._layer)
        ]

    def get_hovering_info(self, mouse_xy: PosPair) -> tuple[bool, int]:
        """
        Gets the hovering info.

        Args:
            mouse xy
        Returns:
            hovered flag, hovered object layer
        """

        return self._bar_rect.collidepoint(mouse_xy), self._layer

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._prev_mouse_y = pg.mouse.get_pos()[1]

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self._traveled_y = 0
        self._is_scrolling = False

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        bar_xy: PosPair
        bar_wh: SizePair
        bar_xy, bar_wh = resize_obj(self._bar_init_pos, *self._bar_init_size.wh, win_ratio)

        self._bar_img = pg.Surface(bar_wh)
        pg.draw.rect(self._bar_img, WHITE, self._bar_img.get_rect(), SCROLLBAR_BORDER_DIM)
        self._bar_rect = self._bar_img.get_rect(**{self._bar_init_pos.coord_type: bar_xy})

        # Calculating elements info like this is more accurate
        self._unit_h = (self._bar_rect.h - (SCROLLBAR_BORDER_DIM * 2)) / self.num_values
        usable_bar_w: int = self._bar_rect.w - (SCROLLBAR_BORDER_DIM * 2)
        usable_bar_x: int = self._bar_rect.x + SCROLLBAR_BORDER_DIM
        usable_bar_bottom: int = self._bar_rect.bottom - SCROLLBAR_BORDER_DIM

        slider_y: int = usable_bar_bottom - round(self.value * self._unit_h)
        slider_h: int = max(round(self._unit_h * NUM_VISIBLE_CHECKBOX_GRID_ROWS), 1)

        self._slider_img = pg.transform.scale(self._slider_img, (usable_bar_w, slider_h))
        self._slider_rect = self._slider_img.get_rect(bottomleft=(usable_bar_x, slider_y))

        clicked_value_wh: SizePair = (usable_bar_w, max(round(self._unit_h), 1))
        clicked_value_y: int = usable_bar_bottom - round(self._clicked_value * self._unit_h)
        clicked_value_xy: PosPair = (usable_bar_x, clicked_value_y)

        self._clicked_value_img = pg.transform.scale(self._clicked_value_img, clicked_value_wh)
        self._clicked_value_rect = self._clicked_value_img.get_rect(bottomleft=clicked_value_xy)

    def set_value(self, value: int) -> None:
        """
        Sets the bar on a specif value.

        Args:
            value
        """

        self.value = value
        usable_bar_bottom: int = self._bar_rect.bottom - SCROLLBAR_BORDER_DIM
        self._slider_rect.bottom = usable_bar_bottom - round(self.value * self._unit_h)

    def set_clicked_value(self, clicked_row: int) -> None:
        """
        Sets the value of the clicked color row.

        Args:
            clicked row
        """

        self._clicked_value = clicked_row
        usable_bar_bottom: int = self._bar_rect.bottom - SCROLLBAR_BORDER_DIM
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

        usable_bar_bottom: int = self._bar_rect.bottom - SCROLLBAR_BORDER_DIM

        self._unit_h = (self._bar_rect.h - (SCROLLBAR_BORDER_DIM * 2)) / self.num_values
        self._slider_rect.h = max(round(self._unit_h * NUM_VISIBLE_CHECKBOX_GRID_ROWS), 1)
        self._slider_rect.bottom = usable_bar_bottom - round(self.value * self._unit_h)

        slider_wh: SizePair = (self._slider_img.get_width(), self._slider_rect.h)
        self._slider_img = pg.transform.scale(self._slider_img, slider_wh)

        self._clicked_value_rect.h = max(round(self._unit_h), 1)
        clicked_value_offset_y: int = round(self._clicked_value * self._unit_h)
        self._clicked_value_rect.bottom = usable_bar_bottom - clicked_value_offset_y

        clicked_value_w: int = self._clicked_value_img.get_width()
        clicked_value_wh: SizePair = (clicked_value_w, self._clicked_value_rect.h)
        self._clicked_value_img = pg.transform.scale(self._clicked_value_img, clicked_value_wh)

    def _start_scrolling(self, mouse_y: int) -> None:
        """
        Changes the value depending on the mouse position and sets the scrolling flag to True.

        Args:
            mouse y
        """

        if mouse_y < self._slider_rect.top or mouse_y > self._slider_rect.bottom:
            value: int = int((self._bar_rect.bottom - mouse_y) / self._unit_h)
            if mouse_y < self._slider_rect.y:
                value -= NUM_VISIBLE_CHECKBOX_GRID_ROWS

            value = max(min(value, self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS), 0)
            self.set_value(value)

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
            self._traveled_y -= int(units_traveled * self._unit_h)

            max_value: int = self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS
            value: int = max(min(self.value + units_traveled, max_value), 0)
            self.set_value(value)

    def _scroll_with_keys(self, timed_keys: list[int]) -> None:
        """
        Scrolls with keys.

        Args:
            timed keys
        """

        max_value: int = self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS
        if pg.K_DOWN in timed_keys:
            self.set_value(max(self.value - 1, 0))
        if pg.K_UP in timed_keys:
            self.set_value(min(self.value + 1, max_value))
        if pg.K_PAGEDOWN in timed_keys:
            self.set_value(max(self.value - NUM_VISIBLE_CHECKBOX_GRID_ROWS, 0))
        if pg.K_PAGEUP in timed_keys:
            self.set_value(min(self.value + NUM_VISIBLE_CHECKBOX_GRID_ROWS, max_value))
        if pg.K_HOME in timed_keys:
            self.set_value(0)
        if pg.K_END in timed_keys:
            self.set_value(max_value)

    def _scroll_with_buttons(self, mouse: Mouse) -> None:
        """
        Changes the value depending on up and down buttons.

        Args:
            mouse
        """

        is_arrow_up_clicked: bool = self._arrow_up.upt(mouse)
        if is_arrow_up_clicked:
            max_value: int = self.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS
            self.set_value(min(self.value + 1, max_value))
        is_arrow_down_clicked: bool = self._arrow_down.upt(mouse)
        if is_arrow_down_clicked:
            self.set_value(max(self.value - 1, 0))

    def upt(self, mouse: Mouse, timed_keys: list[int]) -> None:
        """
        Allows to pick a value via scrolling, keys, mouse wheel or arrow buttons.

        Args:
            mouse, timed keys
        """

        if not mouse.pressed[MOUSE_LEFT]:
            self._is_scrolling = False
        elif mouse.hovered_obj == self and not self._is_scrolling:
            self._start_scrolling(mouse.y)

        if self._is_scrolling:
            self._scroll(mouse.y)
        if mouse.hovered_obj == self and timed_keys:
            self._scroll_with_keys(timed_keys)
        self._scroll_with_buttons(mouse)

        self._prev_mouse_y = mouse.y


class PaletteManager:
    """Class to manage color palettes, includes a drop-down menu."""

    __slots__ = (
        "values", "colors_grid", "_dropdown_options", "dropdown_i", "_dropdown_offset_x",
        "_dropdown_offset_y", "is_dropdown_active", "_edit_i", "is_editing_color", "_win_ratio",
        "objs_info", "_dropdown_info_start_i", "_dropdown_info_end_i", "_scrollbar"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of colors and the drop-down menu to modify it.

        Args:
            position
        """

        self.values: list[Color] = [BLACK]
        checkboxes_info: list[CheckboxInfo] = [_get_color_info(self.values[0])]
        self.colors_grid: CheckboxGrid = CheckboxGrid(pos, checkboxes_info, 5, (True, True))

        button_imgs: list[pg.Surface] = [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG]
        self._dropdown_options: list[Button] = [
            Button(RectPos(0, 0, "topleft"), button_imgs, *option_texts, SPECIAL_LAYER, 20)
            for option_texts in OPTIONS_TEXTS
        ]
        self.dropdown_i: int = 0
        self._dropdown_offset_x: int
        self._dropdown_offset_y: int
        self.is_dropdown_active: bool = False

        self._edit_i: int
        self.is_editing_color: bool = False
        self._win_ratio: Ratio = Ratio(1, 1)
        self.objs_info: list[ObjInfo] = [ObjInfo(self.colors_grid)]

        self._dropdown_info_start_i: int = len(self.objs_info)
        self.objs_info.extend([ObjInfo(option) for option in self._dropdown_options])
        self._dropdown_info_end_i: int = len(self.objs_info)

        self._scrollbar: VerScrollbar = VerScrollbar(
            RectPos(self.colors_grid.rect.right + 10, self.colors_grid.rect.bottom, "bottomleft")
        )
        self.objs_info.append(ObjInfo(self._scrollbar))

        for i in range(self._dropdown_info_start_i, self._dropdown_info_end_i):
            self.objs_info[i].set_active(False)

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        self._win_ratio = win_ratio

    def _handle_dropdown_movement(self) -> None:
        """Sets the dropdown visibility and if it's visible moves it to the correct position."""

        checkbox: LockedCheckbox = self.colors_grid.checkboxes[self.dropdown_i]
        is_visible: bool = self.objs_info[self._dropdown_info_start_i].is_active
        should_be_visible: bool = checkbox in self.colors_grid.visible_checkboxes
        if is_visible != should_be_visible:
            for i in range(self._dropdown_info_start_i, self._dropdown_info_end_i):
                self.objs_info[i].set_active(should_be_visible)

        if should_be_visible:
            start_x: int = checkbox.rect.x + self._dropdown_offset_x
            start_y: int = checkbox.rect.y + self._dropdown_offset_y
            option_init_x: int = round(start_x / self._win_ratio.w)
            option_init_y: int = round(start_y / self._win_ratio.h)
            for option in self._dropdown_options:
                rec_move_rect(option, option_init_x, option_init_y, self._win_ratio)
                option_init_y += int(option.rect.h / self._win_ratio.h)

    def set_info(
            self, colors: list[Color], color_i: int, offset_y: int, dropdown_i: Optional[int]
    ) -> None:
        """
        Sets the colors, offset, clicked color and dropdown.

        Args:
            colors, color index, grid y offset, dropdown index (can be None)
        """

        self.values = colors

        checkboxes_info: list[CheckboxInfo] = [_get_color_info(value) for value in self.values]
        self.colors_grid.set_grid(checkboxes_info, color_i, offset_y)

        if dropdown_i is not None:
            self.dropdown_i = dropdown_i
            dropdown_checkbox: LockedCheckbox = self.colors_grid.checkboxes[self.dropdown_i]
            self._dropdown_offset_x = round(dropdown_checkbox.rect.w / 2)
            self._dropdown_offset_y = round(dropdown_checkbox.rect.h / 2)
            self.is_dropdown_active = True
            self._handle_dropdown_movement()

        self._scrollbar.set_num_values(ceil(len(self.values) / self.colors_grid.num_cols))
        self._scrollbar.set_value(self.colors_grid.offset_y)
        self._scrollbar.set_clicked_value(self.colors_grid.clicked_i // self.colors_grid.num_cols)

    def add(self, color: Color) -> bool:
        """
        Adds a color to the palette or edits one based on the editing color flag.

        Args:
            color
        Returns
            refresh objects flag
        """

        # The insert method uses the window size ratio to adjust the initial position

        prev_objs_info: list[ObjInfo] = self.colors_grid.objs_info
        if color not in self.values:
            if self.is_editing_color:
                self.values[self._edit_i] = color
                self.colors_grid.edit(self._edit_i, *_get_color_info(color))
            else:
                self.values.append(color)
                self.colors_grid.append(*_get_color_info(color))
                self._scrollbar.set_num_values(ceil(len(self.values) / self.colors_grid.num_cols))
        self.colors_grid.check(self.values.index(color))

        if self.is_dropdown_active:
            self._handle_dropdown_movement()
        self._scrollbar.set_clicked_value(self.colors_grid.clicked_i // self.colors_grid.num_cols)
        self.is_editing_color = False

        return self.colors_grid.objs_info != prev_objs_info

    def _toggle_dropdown(self, mouse: Mouse, i: int, checkbox: LockedCheckbox) -> None:
        """
        Toggles the dropdown menu.

        Args:
            mouse, index, checkbox.
        """

        self.is_dropdown_active = not self.is_dropdown_active if self.dropdown_i == i else True
        if not self.is_dropdown_active:
            for i in range(self._dropdown_info_start_i, self._dropdown_info_end_i):
                self.objs_info[i].set_active(self.is_dropdown_active)
        else:
            self.dropdown_i = i
            self._dropdown_offset_x = mouse.x - checkbox.rect.x
            self._dropdown_offset_y = mouse.y - checkbox.rect.y
            self._handle_dropdown_movement()

    def _check_dropdown_toggle(self, mouse: Mouse) -> None:
        """
        Opens or closes the dropdown menu if the mouse right-clicks a checkbox.

        Args:
            mouse
        """

        visible_start_i: int = self.colors_grid.offset_y * self.colors_grid.num_cols
        mouse_xy: PosPair = mouse.xy
        for i, checkbox in enumerate(self.colors_grid.visible_checkboxes, visible_start_i):
            if checkbox.rect.collidepoint(mouse_xy):
                self._toggle_dropdown(mouse, i, checkbox)

                return

        if self.is_dropdown_active:
            self.is_dropdown_active = False
            for i in range(self._dropdown_info_start_i, self._dropdown_info_end_i):
                self.objs_info[i].set_active(self.is_dropdown_active)

    def _upt_dropdown_menu(self, mouse: Mouse) -> None:
        """
        Updates the drop-down menu options.

        Args:
            mouse
        """

        # The remove method uses the window size ratio to adjust the initial position

        is_edit_clicked: bool = self._dropdown_options[0].upt(mouse)
        if is_edit_clicked:
            self._edit_i = self.dropdown_i
            self.is_editing_color = True

        is_remove_clicked: bool = self._dropdown_options[1].upt(mouse)
        if is_remove_clicked:
            self.values.pop(self.dropdown_i)
            self.values = self.values or [BLACK]
            fallback_info: CheckboxInfo = _get_color_info(self.values[0])
            self.colors_grid.remove(self.dropdown_i, fallback_info)
            self.dropdown_i = min(self.dropdown_i, len(self.colors_grid.checkboxes) - 1)

    def _handle_dropdown_shortcuts(self, timed_keys: list[int]) -> None:
        """Handles the drop-down menu shortcuts.

        Args:
            timed keys
        """

        # The remove method uses the window size ratio to adjust the initial position

        if pg.K_e in timed_keys:
            self._edit_i = self.colors_grid.clicked_i
            self.is_editing_color = True

        if pg.K_DELETE in timed_keys:
            self.values.pop(self.colors_grid.clicked_i)
            self.values = self.values or [BLACK]
            fallback_info: CheckboxInfo = _get_color_info(self.values[0])
            self.colors_grid.remove(self.colors_grid.clicked_i, fallback_info)
            if self.dropdown_i > self.colors_grid.clicked_i:
                self.dropdown_i -= 1

    def _scroll_with_wheel(self, mouse: Mouse) -> None:
        """
        Scrolls with the mouse wheel if the grid or scrollbar are hovered.

        Args:
            mouse
        """

        is_hovering_colors_grid: bool = self.colors_grid.rect.collidepoint(mouse.xy)
        is_hovering_scrollbar: bool = mouse.hovered_obj == self._scrollbar
        if mouse.scroll_amount and (is_hovering_colors_grid or is_hovering_scrollbar):
            scrollbar_value: int = self._scrollbar.value + mouse.scroll_amount
            scrollbar_max_limit: int = self._scrollbar.num_values - NUM_VISIBLE_CHECKBOX_GRID_ROWS
            scrollbar_value = max(min(scrollbar_value, scrollbar_max_limit), 0)
            self._scrollbar.set_value(scrollbar_value)

    def _adjust_scrollbar(self, prev_num_values: int, prev_clicked_i: int) -> None:
        """
        Adjusts the scrollbar if any of its values changed.

        Args:
            previous number of values, previous clicked checkbox index
        """

        if len(self.values) != prev_num_values:
            self._scrollbar.set_num_values(ceil(len(self.values) / self.colors_grid.num_cols))

        if self.colors_grid.offset_y != self._scrollbar.value:
            self._scrollbar.set_value(self.colors_grid.offset_y)

        if self.colors_grid.clicked_i != prev_clicked_i:
            clicked_row: int = self.colors_grid.clicked_i // self.colors_grid.num_cols
            self._scrollbar.set_clicked_value(clicked_row)

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[Color, bool, Optional[Color]]:
        """
        Allows selecting a color and making a drop-down menu appear on right click.

        Args:
            mouse, keyboard
        Returns:
            selected color, refresh objects flag, color to edit (can be None)
        """

        if mouse.released[MOUSE_RIGHT]:
            self._check_dropdown_toggle(mouse)

        prev_num_values: int = len(self.values)
        prev_clicked_i: int = self.colors_grid.clicked_i
        prev_offset_y: int = self.colors_grid.offset_y
        prev_dropdown_i: int = self.dropdown_i
        prev_objs_info: list[ObjInfo] = self.colors_grid.objs_info

        if self.is_dropdown_active:
            self._upt_dropdown_menu(mouse)
        if keyboard.is_ctrl_on:
            self._handle_dropdown_shortcuts(keyboard.timed)

        prev_scrollbar_value: int = self._scrollbar.value
        self._scrollbar.upt(mouse, keyboard.timed)
        self._scroll_with_wheel(mouse)

        if self._scrollbar.value != prev_scrollbar_value:
            self.colors_grid.set_offset_y(self._scrollbar.value)

        self.colors_grid.upt(mouse, keyboard)
        self._adjust_scrollbar(prev_num_values, prev_clicked_i)

        has_offset_y_changed: bool = self.colors_grid.offset_y != prev_offset_y
        has_dropdown_i_changed: bool = self.dropdown_i != prev_dropdown_i
        if self.is_dropdown_active and (has_offset_y_changed or has_dropdown_i_changed):
            self._handle_dropdown_movement()

        selected_color: Color = self.values[self.colors_grid.clicked_i]
        should_refresh_objs: bool = prev_objs_info != self.colors_grid.objs_info
        color_to_edit: Optional[Color] = (
            self.values[self._edit_i] if self.is_editing_color else None
        )

        return selected_color, should_refresh_objs, color_to_edit
