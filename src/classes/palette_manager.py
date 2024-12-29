"""Class to manage color palettes, includes a drop-down menu."""

from math import ceil
from typing import Final, Optional, Any

import pygame as pg

from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Button

from src.utils import (
    RectPos, Size, Ratio, ObjInfo, MouseInfo, get_img, add_border, resize_obj, rec_move_rect
)
from src.type_utils import PosPair, SizePair, Color, CheckboxInfo, LayeredBlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_RIGHT, BLACK, WHITE, LIGHT_GRAY, VISIBLE_CHECKBOX_GRID_ROWS,
    BG_LAYER, ELEMENT_LAYER, SPECIAL_LAYER
)

OptionsInfo = tuple[tuple[str, str], ...]

SCROLLBAR_BORDER_DIM: Final[int] = 2

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

    rgb_text: str = f"({color[0]}, {color[1]}, {color[2]})"
    hex_text: str = f"(#{"".join(f"{channel:02x}" for channel in color)})"
    text: str = f"{rgb_text}\n{hex_text}"

    return img, text


class VerScrollbar:
    """Class to create a vertical scrollbar."""

    __slots__ = (
        "_bar_init_pos", "_bar_img", "_bar_rect", "_bar_init_size", "_value", "_num_values",
        "_slider_coord_type", "_slider_img", "_slider_rect", "_is_hovering", "_is_scrolling",
        "_layer", "_arrow_up", "_arrow_down", "objs_info"
    )

    def __init__(self, pos: RectPos, num_values: int, base_layer: int = BG_LAYER) -> None:
        """
        Creates the bar and slider.

        Args:
            position, number of values, base layer (default = BG_LAYER)
        """

        self._bar_init_pos: RectPos = pos

        self._bar_img: pg.Surface = pg.Surface((15, 100))
        pg.draw.rect(self._bar_img, WHITE, self._bar_img.get_rect(), SCROLLBAR_BORDER_DIM)
        self._bar_rect: pg.Rect = self._bar_img.get_rect(
            **{self._bar_init_pos.coord_type: (self._bar_init_pos.x, self._bar_init_pos.y)}
        )

        self._bar_init_size: Size = Size(*self._bar_rect.size)

        self._value: int = 0
        self._num_values: int = num_values

        self._slider_coord_type: str = "bottomleft"

        slider_w: int = self._bar_init_size.w - (SCROLLBAR_BORDER_DIM * 2)
        usable_bar_height: int = self._bar_init_size.h - (SCROLLBAR_BORDER_DIM * 2)
        slider_h: int = max(round(usable_bar_height / self._num_values), 1)
        self._slider_img: pg.Surface = pg.Surface((slider_w, slider_h))
        self._slider_img.fill(LIGHT_GRAY)

        slider_xy: PosPair = (
            self._bar_rect.x + SCROLLBAR_BORDER_DIM, self._bar_rect.bottom - SCROLLBAR_BORDER_DIM
        )
        self._slider_rect: pg.Rect = self._slider_img.get_rect(
            **{self._slider_coord_type: slider_xy}
        )

        self._is_hovering: bool = False
        self._is_scrolling: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER

        self._arrow_up: Button = Button(
            RectPos(self._bar_rect.centerx, self._bar_rect.y - 5, "midbottom"),
            (ARROW_UP_IMG_OFF, ARROW_UP_IMG_ON), None, None
        )
        self._arrow_down: Button = Button(
            RectPos(self._bar_rect.centerx, self._bar_rect.bottom + 5, "midtop"),
            (ARROW_DOWN_IMG_OFF, ARROW_DOWN_IMG_ON), None, None
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(self._arrow_up), ObjInfo(self._arrow_down)]

    def blit(self) -> list[LayeredBlitInfo]:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._bar_img, self._bar_rect.topleft, self._layer),
            (self._slider_img, self._slider_rect.topleft, self._layer)
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
            self._bar_rect.collidepoint(mouse_xy) or self._slider_rect.collidepoint(mouse_xy)
        )

        return is_hovering, self._layer

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

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

        self._bar_img = pg.Surface(bar_wh)
        pg.draw.rect(self._bar_img, WHITE, self._bar_img.get_rect(), SCROLLBAR_BORDER_DIM)
        self._bar_rect = self._bar_img.get_rect(**{self._bar_init_pos.coord_type: bar_xy})

        # Calculating slider info like this is more accurate
        unit_h: float = (self._bar_rect.h - (SCROLLBAR_BORDER_DIM * 2)) / self._num_values
        slider_xy: PosPair = (
            self._bar_rect.x + SCROLLBAR_BORDER_DIM,
            self._bar_rect.bottom - SCROLLBAR_BORDER_DIM - round(self._value * unit_h)
        )
        slider_wh: SizePair = (
            self._bar_rect.w - (SCROLLBAR_BORDER_DIM * 2), max(round(unit_h), 1)
        )

        self._slider_img = pg.transform.scale(self._slider_img, slider_wh)
        self._slider_rect = self._slider_img.get_rect(
            **{self._slider_coord_type: slider_xy}
        )

    def set_num_values(self, num_values: int) -> None:
        """
        Sets the number of values the scrollbar can have.

        Args:
            number of values
        """

        self._num_values = num_values
        unit_h: float = (self._bar_rect.h - (SCROLLBAR_BORDER_DIM * 2)) / self._num_values

        self._slider_rect.bottom = (
            self._bar_rect.bottom - SCROLLBAR_BORDER_DIM - round(self._value * unit_h)
        )
        self._slider_rect.h = max(round(unit_h), 1)
        self._slider_img = pg.transform.scale(
            self._slider_img, (self._slider_img.get_width(), self._slider_rect.h)
        )

    def _scroll_with_keys(self, keys: list[int]) -> None:
        """
        Scrolls with keys.

        Args:
            keys
        """

        if pg.K_DOWN in keys:
            self._value = max(self._value - 1, 0)
        if pg.K_UP in keys:
            self._value = min(self._value + 1, self._num_values - 1)
        if pg.K_PAGEDOWN in keys:
            self._value = max(self._value - VISIBLE_CHECKBOX_GRID_ROWS, 0)
        if pg.K_PAGEUP in keys:
            self._value = min(self._value + VISIBLE_CHECKBOX_GRID_ROWS, self._num_values - 1)
        if pg.K_HOME in keys:
            self._value = 0
        if pg.K_END in keys:
            self._value = self._num_values - 1

    def _scroll(self, mouse_info: MouseInfo) -> None:
        """
        Changes the value depending on the mouse position.

        Args:
            mouse info
        """

        unit_h: float = (self._bar_rect.h - (SCROLLBAR_BORDER_DIM * 2)) / self._num_values
        self._value = int((self._bar_rect.bottom - mouse_info.y) / unit_h)
        self._value = max(min(self._value, self._num_values - 1), 0)

    def _scroll_with_buttons(self, hovered_obj: Any, mouse_info: MouseInfo) -> None:
        """
        Changes the value depending on up and down buttons.

        Args:
            hovered object, mouse info
        """

        is_arrow_up_clicked: bool = self._arrow_up.upt(hovered_obj, mouse_info)
        if is_arrow_up_clicked:
            self._value = min(self._value + 1, self._num_values - 1)
        is_arrow_down_clicked: bool = self._arrow_down.upt(hovered_obj, mouse_info)
        if is_arrow_down_clicked:
            self._value = max(self._value - 1, 0)

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

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]) -> int:
        """
        Allows to pick a value via scrolling, keys, mouse wheel or arrow buttons.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            value
        """

        self._handle_hover(hovered_obj, mouse_info)

        prev_value: int = self._value
        if self._is_scrolling:
            self._scroll(mouse_info)
        if self._is_hovering:
            self._value = max(min(self._value + mouse_info.scroll_amount, self._num_values - 1), 0)
            if keys:
                self._scroll_with_keys(keys)
        self._scroll_with_buttons(hovered_obj, mouse_info)

        if prev_value != self._value:
            unit_h: float = (self._bar_rect.h - (SCROLLBAR_BORDER_DIM * 2)) / self._num_values
            self._slider_rect.bottom = (
                self._bar_rect.bottom - SCROLLBAR_BORDER_DIM - round(self._value * unit_h)
            )

        return self._value


class PaletteManager:
    """Class to manage color palettes, includes a drop-down menu."""

    # TODO: dropdown edge cases
    __slots__ = (
        "values", "colors_grid", "_dropdown_options", "_dropdown_i", "_is_dropdown_visible",
        "_is_editing_color", "_win_ratio", "objs_info",
        "_dropdown_info_start", "_dropdown_info_end", "_scrollbar"
    )

    def __init__(self, pos: RectPos, imgs: tuple[pg.Surface, ...]) -> None:
        """
        Creates the grid of colors and the drop-down menu to modify it.

        Args:
            position and drop-down menu image pair
        """

        self.values: list[Color] = [BLACK]
        self.colors_grid: CheckboxGrid = CheckboxGrid(
            pos, (_get_color_info(self.values[0]),), 5, (True, True)
        )

        self._dropdown_options: tuple[Button, ...] = tuple(
            Button(RectPos(0, 0, "topleft"), imgs, *option_texts, SPECIAL_LAYER, 20)
            for option_texts in OPTIONS_TEXTS
        )
        self._dropdown_i: int = 0
        self._is_dropdown_visible: bool = False

        self._is_editing_color: bool = False
        self._win_ratio: Ratio = Ratio(1, 1)
        self.objs_info: list[ObjInfo] = [ObjInfo(self.colors_grid)]

        self._dropdown_info_start: int = len(self.objs_info)
        self.objs_info.extend(ObjInfo(option) for option in self._dropdown_options)
        self._dropdown_info_end: int = len(self.objs_info)

        scrollbar_num_values: int = ceil(len(self.values) / VISIBLE_CHECKBOX_GRID_ROWS)

        self._scrollbar: VerScrollbar = VerScrollbar(
            RectPos(self.colors_grid.rect.right + 10, self.colors_grid.rect.bottom, "bottomleft"),
            scrollbar_num_values
        )
        self.objs_info.append(ObjInfo(self._scrollbar))

        for i in range(self._dropdown_info_start, self._dropdown_info_end):
            self.objs_info[i].set_active(self._is_dropdown_visible)

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        self._win_ratio = win_ratio

    def add(self, color: Optional[Color]) -> bool:
        """
        Adds a color to the palette or edits one based on the editing color flag.

        Args:
            color (if None it sets editing color to False)
        Returns
            refresh objects flag
            
        """

        if not color:
            self._is_editing_color = False

            return False

        # The insert method uses the window size ratio to adjust the initial position

        prev_colors_grid_objs_info: list[ObjInfo] = self.colors_grid.objs_info
        if color not in self.values:
            if self._is_editing_color:
                self.values[self._dropdown_i] = color
                self.colors_grid.replace(self._dropdown_i, *_get_color_info(color))
            else:
                self.values.append(color)
                self.colors_grid.replace(None, *_get_color_info(color))
        self.colors_grid.check(self.values.index(color))
        self._is_editing_color = False

        return self.colors_grid.objs_info != prev_colors_grid_objs_info

    def set_colors(self, colors: list[Color]) -> None:
        """
        Sets the palette.

        Args:
            colors
        """

        self.values = colors

        checkboxes_info: tuple[CheckboxInfo, ...] = tuple(
            _get_color_info(value) for value in self.values
        )
        self.colors_grid.set_grid(checkboxes_info)

        self._scrollbar.set_num_values(ceil(len(self.values) / VISIBLE_CHECKBOX_GRID_ROWS))

    def _leave_dropdown(self) -> None:
        """Clears all the drop-down menu data."""

        dropdown_objs_info: list[ObjInfo] = (
            self.objs_info[self._dropdown_info_start:self._dropdown_info_end]
        )

        dropdown_objs: list[Any] = [obj_info.obj for obj_info in dropdown_objs_info]
        while dropdown_objs:
            obj: Any = dropdown_objs.pop()
            if hasattr(obj, "leave"):
                obj.leave()
            if hasattr(obj, "objs_info"):
                dropdown_objs.extend(info.obj for info in obj.objs_info)

    def _refresh_dropdown(self, x: int, y: int) -> None:
        """
        Refreshes the drop-down menu.

        Args:
            x position, y position
        """

        for i in range(self._dropdown_info_start, self._dropdown_info_end):
            self.objs_info[i].set_active(self._is_dropdown_visible)

        if not self._is_dropdown_visible:
            self._leave_dropdown()
        else:
            option_init_x: int = round(x / self._win_ratio.w)
            option_init_y: int = round(y / self._win_ratio.h)
            for option in self._dropdown_options:
                rec_move_rect(option, option_init_x, option_init_y, self._win_ratio)
                option_init_y += int(option.rect.h / self._win_ratio.h)

    def _check_dropdown_toggle(self, mouse_info: MouseInfo) -> None:
        """
        Opens or closes the dropdown menu if the mouse right clicks a checkbox.

        Args:
            mouse info
        """

        for i, checkbox in enumerate(self.colors_grid.visible_checkboxes):
            if checkbox.rect.collidepoint((mouse_info.x, mouse_info.y)):
                checkbox_i: int = self.colors_grid.offset_y * self.colors_grid.cols + i
                self._is_dropdown_visible = (
                    not self._is_dropdown_visible if self._dropdown_i == checkbox_i else True
                )
                self._dropdown_i = checkbox_i
                self._refresh_dropdown(mouse_info.x, mouse_info.y)

                return

        self._is_dropdown_visible = False

    def _handle_dropdown_shortcuts(self, keys: list[int]) -> None:
        """Handles the drop-down menu shortcuts.

        Args:
            keys
        """

        # The remove method uses the window size ratio to adjust the initial position

        copy_clicked_i: int = self.colors_grid.clicked_i  # Modified in CheckboxGrid.remove
        if pg.K_e in keys:
            self._is_editing_color = True
            if self._dropdown_i != copy_clicked_i:
                self._dropdown_i = copy_clicked_i
                self._refresh_dropdown(*self.colors_grid.checkboxes[copy_clicked_i].rect.center)

        if pg.K_DELETE in keys:
            self.values.pop(copy_clicked_i)
            self.values = self.values or [BLACK]
            fallback_info: CheckboxInfo = _get_color_info(self.values[0])
            self.colors_grid.remove(copy_clicked_i, fallback_info)

            if self._dropdown_i >= copy_clicked_i:
                self._dropdown_i = min(self._dropdown_i, len(self.colors_grid.checkboxes) - 1)
                self._refresh_dropdown(*self.colors_grid.checkboxes[self._dropdown_i].rect.center)

    def _upt_dropdown_menu(self, hovered_obj: Any, mouse_info: MouseInfo) -> None:
        """
        Updates the drop-down menu options.

        Args:
            hovered object, mouse info
        """

        # The remove method uses the window size ratio to adjust the initial position

        is_edit_clicked: bool = self._dropdown_options[0].upt(hovered_obj, mouse_info)
        if is_edit_clicked:
            self._is_editing_color = True

        is_remove_clicked: bool = self._dropdown_options[1].upt(hovered_obj, mouse_info)
        if is_remove_clicked:
            self.values.pop(self._dropdown_i)
            self.values = self.values or [BLACK]
            fallback_info: CheckboxInfo = _get_color_info(self.values[0])
            self.colors_grid.remove(self._dropdown_i, fallback_info)

            self._dropdown_i = min(self._dropdown_i, len(self.colors_grid.checkboxes) - 1)
            self._refresh_dropdown(*self.colors_grid.checkboxes[self._dropdown_i].rect.center)

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]
    ) -> tuple[Color, bool, Optional[Color]]:
        """
        Allows selecting a color and making a drop-down menu appear on right click.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            selected color, refresh objects flag, color to edit (can be None)
        """

        was_dropdown_visible: bool = self._is_dropdown_visible

        if mouse_info.released[MOUSE_RIGHT]:
            self._check_dropdown_toggle(mouse_info)

        prev_colors_grid_objs_info: list[ObjInfo] = self.colors_grid.objs_info
        if pg.key.get_mods() & pg.KMOD_CTRL:
            self._handle_dropdown_shortcuts(keys)
        if self._is_dropdown_visible:
            self._upt_dropdown_menu(hovered_obj, mouse_info)

        if self._is_dropdown_visible != was_dropdown_visible:
            self._refresh_dropdown(mouse_info.x, mouse_info.y)
        else:
            self.colors_grid.upt(hovered_obj, mouse_info, keys)

        self._scrollbar.upt(hovered_obj, mouse_info, keys)

        selected_color: Color = self.values[self.colors_grid.clicked_i]
        should_refresh_objs: bool = prev_colors_grid_objs_info != self.colors_grid.objs_info
        color_to_edit: Optional[Color] = (
            self.values[self._dropdown_i] if self._is_editing_color else None
        )

        return selected_color, should_refresh_objs, color_to_edit
