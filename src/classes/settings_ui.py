"""Interface to edit different types of settings."""

from typing import Self, TypeAlias, Any

from pygame import K_1

from src.classes.grid_settings_manager import GridSettingsManager
from src.classes.general_settings_manager import GeneralSettingsManager
from src.classes.ui import UI
from src.classes.devices import KEYBOARD

from src.obj_utils import UIElement

_SettingsManager: TypeAlias = GeneralSettingsManager | GridSettingsManager


class SettingsUI(UI):
    """Class to create an interface that allows editing different types of settings."""

    __slots__ = (
        "_managers", "selected_manager",
        "_orig_sub_objs",
    )

    def __init__(self: Self) -> None:
        """Creates the interface and the managers to edit different types of settings."""

        super().__init__("EDIT SETTING", False)

        self._managers: list[_SettingsManager] = [
            GeneralSettingsManager(self._rect),
            GridSettingsManager(self._rect)
        ]
        self.selected_manager: _SettingsManager = self._managers[0]

        self._orig_sub_objs: tuple[UIElement, ...] = self.sub_objs

        self.sub_objs = self._orig_sub_objs + (self.selected_manager,)

    def set_info(self: Self, data: dict[str, Any]) -> None:
        """
        Sets all the settings from the data.

        Args:
            data
        """

        manager: _SettingsManager

        for manager in self._managers:
            manager.set_info(data)

    def _handle_type_switching_shortcuts(self: Self) -> None:
        """Selects a color if the user presses ctrl+1-9."""

        k: int

        num_shortcuts: int = min(len(self._managers), 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                self.selected_manager = self._managers[k - K_1]
                self.sub_objs = self._orig_sub_objs + (self.selected_manager,)

    def upt(self: Self) -> tuple[bool, bool]:
        """
        Allows editing a type of settings and changing type.

        Returns:
            exiting flag, confirming flag, changed flag
        """

        prev_selected_manager: _SettingsManager = self.selected_manager

        if KEYBOARD.is_ctrl_on:
            self._handle_type_switching_shortcuts()

        self.selected_manager.upt()
        is_exiting, is_confirming = self._base_upt()

        return is_exiting, is_confirming, self.selected_manager != prev_selected_manager

    # TODO:  remove
    @property
    def general_settings_manager(self):
        return self._managers[0]
    @property
    def grid_settings_manager(self):
        return self._managers[1]
