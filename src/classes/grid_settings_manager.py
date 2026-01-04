"""Class to manage editing grid settings."""

from typing import Self, Final, Any

from pygame import Rect, Event, event, K_1, K_g, K_h, K_t, K_z

from src.classes.dropdown import Dropdown
from src.classes.clickable import Checkbox
from src.classes.devices import KEYBOARD

from src.obj_utils import UIElement
from src.type_utils import DropdownOptionsInfo, RectPos
from src.consts import (
    SPECIAL_LAYER, UI_LAYER,
    SETTINGS_GRID_ZOOM_DIRECTION_CHANGE, SETTINGS_GRID_HISTORY_MAX_SIZE_CHANGE,
    SETTINGS_GRID_CENTER_ACTIVENESS_CHANGE, SETTINGS_GRID_TILE_MODE_SIZE_CHANGE,
)
from src.imgs import CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG

_HISTORY_DROPDOWN_OPTIONS: Final[DropdownOptionsInfo] = (
    ("32"   , "(CTRL+H+1)", 32),
    ("64"   , "(CTRL+H+2)", 64),
    ("128"  , "(CTRL+H+3)", 128),
    ("256"  , "(CTRL+H+4)", 256),
    ("512"  , "(CTRL+H+5)", 512),
    ("1'024", "(CTRL+H+6)", 1_024),
    ("None" , "(CTRL+H+7)", None),
)

class GridSettingsManager(UIElement):
    """Class to manage editing grid settings."""

    __slots__ = (
        "invert_zoom", "history_dropdown",
        "_show_center", "_enable_tile_mode",
    )

    def __init__(self: Self, rect: Rect) -> None:
        """Creates the elements to edit grid settings."""

        super().__init__()
        third_x: int  = rect.x + round(rect.w / 4 * 3)

        self.invert_zoom: Checkbox = Checkbox(
            RectPos(third_x, rect.y + 200, "center"),
            (CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG), "Invert Zoom", "(CTRL+Z)", UI_LAYER
        )
        self.history_dropdown: Dropdown = Dropdown(
            RectPos(third_x, self.invert_zoom.rect.bottom + 75, "midtop"),
            _HISTORY_DROPDOWN_OPTIONS, "History Max Size", UI_LAYER + SPECIAL_LAYER
        )
        self._show_center: Checkbox = Checkbox(
            RectPos(third_x, self.history_dropdown.rect.bottom + 75, "midtop"),
            (CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG), "Show Grid\nCenter", "(CTRL+G)", UI_LAYER
        )
        self._enable_tile_mode: Checkbox = Checkbox(
            RectPos(third_x, self._show_center.rect.bottom + 75, "midtop"),
            (CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG), "Enable\nTile Mode", "(CTRL+T)", UI_LAYER
        )

        self.layer = UI_LAYER
        self.sub_objs = (
            self.invert_zoom, self.history_dropdown, self._show_center, self._enable_tile_mode,
        )

    def set_info(self: Self, data: dict[str, Any]) -> None:
        """
        Sets all the settings from the data.

        Args:
            data
        """

        self.invert_zoom.set_checked(data["is_grid_zooming_inverted"])
        event.post(Event(
            SETTINGS_GRID_ZOOM_DIRECTION_CHANGE,
            {"value": -1 if self.invert_zoom.is_checked else 1}
        ))

        self.history_dropdown.set_option_i(data["grid_history_max_size_i"])
        event.post(Event(
            SETTINGS_GRID_HISTORY_MAX_SIZE_CHANGE,
            {"value": self.history_dropdown.values[self.history_dropdown.option_i]}
        ))

        self._show_center.set_checked(data["is_grid_center_active"])
        event.post(Event(
            SETTINGS_GRID_CENTER_ACTIVENESS_CHANGE,
            {"value": self._show_center.is_checked}
        ))

        self._enable_tile_mode.set_checked(data["grid_tile_mode_size"] is not None)
        event.post(Event(
            SETTINGS_GRID_TILE_MODE_SIZE_CHANGE,
            {"value": (50, 50) if self._enable_tile_mode.is_checked else None}
        ))

    def _handle_history_dropdown_shortcuts(self: Self) -> None:
        """Selects an history max size if the user presses ctrl+h+1-9."""

        k: int

        num_shortcuts: int = min(len(self.history_dropdown.values) - 1, 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                # Offsets by 1 because of placeholder option
                self.history_dropdown.set_option_i(k - K_1 + 1)

    def upt(self: Self) -> None:
        """Allows editing grid settings."""

        prev_history_dropdown_option_i: int = self.history_dropdown.option_i

        is_ctrl_z_pressed: bool = KEYBOARD.is_ctrl_on and K_z in KEYBOARD.timed
        did_toggle_invert_zoom: bool = self.invert_zoom.upt(is_ctrl_z_pressed)
        if did_toggle_invert_zoom:
            event.post(Event(
                SETTINGS_GRID_ZOOM_DIRECTION_CHANGE,
                {"value": -1 if self.invert_zoom.is_checked else 1}
            ))

        if KEYBOARD.is_ctrl_on and K_h in KEYBOARD.pressed:
            self._handle_history_dropdown_shortcuts()
        self.history_dropdown.upt()
        if self.history_dropdown.option_i != prev_history_dropdown_option_i:
            event.post(Event(
                SETTINGS_GRID_HISTORY_MAX_SIZE_CHANGE,
                {"value": self.history_dropdown.values[self.history_dropdown.option_i]}
            ))

        is_ctrl_g_pressed: bool = KEYBOARD.is_ctrl_on and K_g in KEYBOARD.timed
        did_toggle_show_center: bool = self._show_center.upt(is_ctrl_g_pressed)
        if did_toggle_show_center:
            event.post(Event(
                SETTINGS_GRID_CENTER_ACTIVENESS_CHANGE,
                {"value": self._show_center.is_checked}
            ))

        is_ctrl_t_pressed: bool = KEYBOARD.is_ctrl_on and K_t in KEYBOARD.timed
        did_toggle_tile_mode: bool = self._enable_tile_mode.upt(is_ctrl_t_pressed)
        if did_toggle_tile_mode:
            event.post(Event(
                SETTINGS_GRID_TILE_MODE_SIZE_CHANGE,
                {"value": (50, 50) if self._enable_tile_mode.is_checked else None}
            ))
