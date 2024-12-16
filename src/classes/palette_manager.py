"""Class to manage color palettes, includes a drop-down menu."""

from typing import Final, Optional, Any

import pygame as pg

from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Button

from src.utils import RectPos, Ratio, ObjInfo, MouseInfo, add_border
from src.type_utils import Color, CheckboxInfo
from src.consts import MOUSE_RIGHT, BLACK, LIGHT_GRAY, SPECIAL_LAYER

OptionsInfo = tuple[tuple[str, str], ...]
OPTIONS: Final[OptionsInfo] = (
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


class PaletteManager:
    """Class to manage color palettes, includes a drop-down menu."""

    __slots__ = (
        "values", "colors_grid", "_dropdown_options", "_dropdown_i", "_is_dropdown_visible",
        "_is_editing_color", "_win_ratio", "objs_info",
        "_dropdown_info_start", "_dropdown_info_end"
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
            Button(RectPos(0, 0, "topleft"), imgs, *option, SPECIAL_LAYER, 20)
            for option in OPTIONS
        )
        self._dropdown_i: int = 0
        self._is_dropdown_visible: bool = False

        self._is_editing_color: bool = False
        self._win_ratio: Ratio = Ratio(1.0, 1.0)
        self.objs_info: list[ObjInfo] = [ObjInfo(self.colors_grid)]

        self._dropdown_info_start: int = len(self.objs_info)
        self.objs_info.extend(ObjInfo(option) for option in self._dropdown_options)
        self._dropdown_info_end: int = len(self.objs_info)

        for i in range(self._dropdown_info_start, self._dropdown_info_end):
            self.objs_info[i].set_active(self._is_dropdown_visible)

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        self._win_ratio = win_ratio

    def add(self, color: Optional[Color]) -> None:
        """
        Adds a color to the palette or edits one based on the editing color flag.

        Args:
            color (if None it sets editing color to False)
        """

        if not color:
            self._is_editing_color = False

            return

        # The insert method uses the window size ratio to adjust the initial position

        if self._is_editing_color:
            self.values[self._dropdown_i] = color
            self.colors_grid.replace(self._dropdown_i, *_get_color_info(color), self._win_ratio)
            self._is_editing_color = False
        elif color not in self.values:
            self.values.append(color)
            self.colors_grid.replace(None, *_get_color_info(color), self._win_ratio)
        self.colors_grid.check(self.values.index(color))

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
        self.colors_grid.set_grid(checkboxes_info, self._win_ratio)

    def _move_option(self, option_init_x: int, option_init_y: int, option: Button) -> None:
        """
        Moves an option of the drop-down menu.

        Args:
            option x, option y, option
        """

        change_x: int = 0
        change_y: int = 0
        option_objs: list[Any] = [option]
        is_first: bool = True
        while option_objs:
            obj: Any = option_objs.pop()
            if hasattr(obj, "move_rect"):
                if not is_first:
                    x: int = obj.init_pos.x + change_x
                    y: int = obj.init_pos.y + change_y
                    obj.move_rect(x, y, self._win_ratio)
                else:
                    prev_init_x: int = obj.init_pos.x
                    prev_init_y: int = obj.init_pos.y
                    obj.move_rect(option_init_x, option_init_y, self._win_ratio)

                    change_x = obj.init_pos.x - prev_init_x
                    change_y = obj.init_pos.y - prev_init_y
                    is_first = False

            if hasattr(obj, "objs_info"):
                option_objs.extend(obj_info.obj for obj_info in obj.objs_info)

    def _leave_dropdown(self) -> None:
        """Clears all the drop-down menu data."""

        dropdown_objs_info: list[ObjInfo] = (
            self.objs_info[self._dropdown_info_start:self._dropdown_info_end]
        )

        dropdown_sub_objs: list[Any] = [obj_info.obj for obj_info in dropdown_objs_info]
        while dropdown_sub_objs:
            obj: Any = dropdown_sub_objs.pop()
            if hasattr(obj, "leave"):
                obj.leave()
            if hasattr(obj, "objs_info"):
                dropdown_sub_objs.extend(obj_info.obj for obj_info in obj.objs_info)

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
                self._move_option(option_init_x, option_init_y, option)
                option_init_y += int(option.rect.h / self._win_ratio.h)

    def _check_dropdown_toggle(self, mouse_info: MouseInfo) -> None:
        """
        Opens or closes the dropdown menu if the mouse right clicks a checkbox.

        Args:
            mouse info
        """

        for i, checkbox in enumerate(self.colors_grid.checkboxes):
            if checkbox.rect.collidepoint((mouse_info.x, mouse_info.y)):
                self._is_dropdown_visible = (
                    not self._is_dropdown_visible if self._dropdown_i == i else True
                )
                self._dropdown_i = i
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
            self.colors_grid.remove(copy_clicked_i, fallback_info, self._win_ratio)

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
            self.colors_grid.remove(self._dropdown_i, fallback_info, self._win_ratio)

            self._dropdown_i = min(self._dropdown_i, len(self.colors_grid.checkboxes) - 1)
            self._refresh_dropdown(*self.colors_grid.checkboxes[self._dropdown_i].rect.center)

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]
    ) -> tuple[Color, Optional[Color]]:
        """
        Allows selecting a color and making a drop-down menu appear on right click.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            selected color, color to edit (can be None)
        """

        was_dropdown_visible: bool = self._is_dropdown_visible

        if mouse_info.released[MOUSE_RIGHT]:
            self._check_dropdown_toggle(mouse_info)

        if pg.key.get_mods() & pg.KMOD_CTRL:
            self._handle_dropdown_shortcuts(keys)
        if self._is_dropdown_visible:
            self._upt_dropdown_menu(hovered_obj, mouse_info)

        if self._is_dropdown_visible != was_dropdown_visible:
            self._refresh_dropdown(mouse_info.x, mouse_info.y)
        else:
            self.colors_grid.upt(hovered_obj, mouse_info, keys)

        selected_color: Color = self.values[self.colors_grid.clicked_i]

        return selected_color, self.values[self._dropdown_i] if self._is_editing_color else None
