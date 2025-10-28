"""Interface to edit the settings."""

from pathlib import Path
from typing import Self, Final, Any

from pygame import event
from pygame.locals import *

from src.classes.ui import UI
from src.classes.dropdown import Dropdown
from src.classes.clickable import Checkbox, Button
from src.classes.text_label import TextLabel
from src.classes.devices import KEYBOARD

from src.obj_utils import ObjInfo
from src.file_utils import prettify_path
from src.type_utils import DropdownOptionsInfo, RectPos
from src.consts import (
    STATE_I_MAIN, STATE_I_SETTINGS,
    SPECIAL_LAYER,
    SETTINGS_FPS_ACTIVENESS_CHANGE, SETTINGS_CRASH_SAVE_DIR_CHOICE,
    SETTINGS_ZOOM_DIRECTION_CHANGE, SETTINGS_HISTORY_MAX_SIZE_CHANGE,
)
from src.imgs import BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG, CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG


AUTOSAVE_MODE_NEVER: Final[int]     = 0
AUTOSAVE_MODE_CRASH: Final[int]     = 1
AUTOSAVE_MODE_INTERRUPT: Final[int] = 2

_FPS_DROPDOWN_OPTIONS: Final[DropdownOptionsInfo] = (
    ("30"  , "(CTRL+C+1)", 30),
    ("60"  , "(CTRL+C+2)", 60),
    ("120" , "(CTRL+C+3)", 120),
    ("240" , "(CTRL+C+4)", 240),
    ("None", "(CTRL+C+5)", 0),
)
_AUTOSAVE_DROPDOWN_OPTIONS: Final[DropdownOptionsInfo] = (
    ("Always"           , "(CTRL+A+1)", -1),  # Unused
    ("Never"            , "(CTRL+A+2)", AUTOSAVE_MODE_NEVER),
    ("On Crash"         , "(CTRL+A+3)", AUTOSAVE_MODE_CRASH),
    ("Not on\nInterrupt", "(CTRL+A+4)", AUTOSAVE_MODE_INTERRUPT),
)
_HISTORY_DROPDOWN_OPTIONS: Final[DropdownOptionsInfo] = (
    ("32"   , "(CTRL+1)", 32),
    ("64"   , "(CTRL+2)", 64),
    ("128"  , "(CTRL+3)", 128),
    ("256"  , "(CTRL+4)", 256),
    ("512"  , "(CTRL+5)", 512),
    ("1'024", "(CTRL+6)", 1_024),
    ("None" , "(CTRL+7)", None),
)


class SettingsUI(UI):
    """Class to create an interface that allows editing the setting."""

    __slots__ = (
        "fps_dropdown", "show_fps",
        "autosave_dropdown",
        "crash_save_dir_str", "crash_save_dir_text_label", "_crash_save_dir",
        "invert_zoom", "history_dropdown",
    )

    def __init__(self: Self) -> None:
        """Creates the interface and the elements to edit general settings."""

        super().__init__("EDIT SETTING", False)

        first_x: int  = self._rect.x + round(self._rect.w / 4 * 1)
        second_x: int = self._rect.x + round(self._rect.w / 4 * 3)

        self.fps_dropdown: Dropdown = Dropdown(
            RectPos(first_x - 8, self._rect.y + 200, "midright"),
            _FPS_DROPDOWN_OPTIONS, "FPS Cap", self.layer + SPECIAL_LAYER
        )
        self.show_fps: Checkbox = Checkbox(
            RectPos(first_x + 8, self._rect.y + 200, "midleft"),
            (CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG), "Show fps", "(CTRL+F)", self.layer
        )

        self.autosave_dropdown: Dropdown = Dropdown(
            RectPos(first_x + 8, self.show_fps.rect.bottom + 75, "topleft"),
            _AUTOSAVE_DROPDOWN_OPTIONS, "Autosave:", self.layer + SPECIAL_LAYER,
            text_h=18, is_text_above=False
        )

        self.crash_save_dir_str: str = str(Path().resolve())

        dropdown_option_h: int = self.autosave_dropdown._options[0].rect.h
        self.crash_save_dir_text_label: TextLabel = TextLabel(
            RectPos(first_x, self.autosave_dropdown.init_pos.y + dropdown_option_h + 75, "midtop"),
            prettify_path(self.crash_save_dir_str), self.layer
        )
        self._crash_save_dir: Button = Button(
            RectPos(first_x, self.crash_save_dir_text_label.rect.bottom + 4, "midtop"),
            (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "Crash Save\nDirectory", "(CTRL+S)",
            self.layer, text_h=20
        )

        self.invert_zoom: Checkbox = Checkbox(
            RectPos(second_x, self._rect.y + 200, "center"),
            (CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG), "Invert Zoom", "(CTRL+Z)", self.layer
        )
        self.history_dropdown: Dropdown = Dropdown(
            RectPos(second_x, self.invert_zoom.rect.bottom + 75, "midtop"),
            _HISTORY_DROPDOWN_OPTIONS, "History Max Size", self.layer + SPECIAL_LAYER
        )

        self.objs_info += (
            ObjInfo(self.show_fps), ObjInfo(self.fps_dropdown),
            ObjInfo(self.autosave_dropdown),
            ObjInfo(self.crash_save_dir_text_label), ObjInfo(self._crash_save_dir),
    
            ObjInfo(self.invert_zoom), ObjInfo(self.history_dropdown)
        )

    def set_info(self: Self, data: dict[str, Any]) -> None:
        """
        Sets all the settings from the data.

        Args:
            data
        """

        self.fps_dropdown.set_option_i(data["fps_cap_i"])

        if data["is_fps_counter_active"] != self.show_fps.is_checked:
            self.show_fps.set_checked(data["is_fps_counter_active"])
        event.post(event.Event(
            SETTINGS_FPS_ACTIVENESS_CHANGE,
            {"value": self.show_fps.is_checked}
        ))

        self.autosave_dropdown.set_option_i(data["autosave_mode_i"])

        self.crash_save_dir_str = data["crash_save_dir"]
        self.crash_save_dir_text_label.set_text(prettify_path(self.crash_save_dir_str))

        if data["is_zooming_inverted"] != self.invert_zoom.is_checked:
            self.invert_zoom.set_checked(data["is_zooming_inverted"])
        event.post(event.Event(
            SETTINGS_ZOOM_DIRECTION_CHANGE,
            {"value": -1 if self.invert_zoom.is_checked else 1}
        ))

        if data["grid_history_max_size_i"] != self.history_dropdown.option_i:
            self.history_dropdown.set_option_i(data["grid_history_max_size_i"])
        event.post(event.Event(
            SETTINGS_HISTORY_MAX_SIZE_CHANGE,
            {"value": self.history_dropdown.values[self.history_dropdown.option_i]}
        ))

    def _handle_fps_dropdown_shortcuts(self: Self) -> None:
        """Selects a fps cap if the user presses ctrl+f+1-9."""

        k: int

        # Offsets by 1 because of placeholder option
        num_shortcuts: int = min(len(self.fps_dropdown.values) - 1, 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                self.fps_dropdown.set_option_i(k - K_1 + 1)

    def _handle_autosave_dropdown_shortcuts(self: Self) -> None:
        """Selects an autosave mode if the user presses ctrl+a+1-9."""

        k: int

        # Offsets by 1 because of placeholder option
        num_shortcuts: int = min(len(self.autosave_dropdown.values) - 1, 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                self.autosave_dropdown.set_option_i(k - K_1 + 1)

    def _handle_history_dropdown_shortcuts(self: Self) -> None:
        """Selects an history max size if the user presses ctrl+h+1-9."""

        k: int

        # Offsets by 1 because of placeholder option
        num_shortcuts: int = min(len(self.history_dropdown.values) - 1, 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                self.history_dropdown.set_option_i(k - K_1 + 1)

    def upt(self: Self) -> tuple[bool, bool, Any]:
        """
        Allows editing generic settings and going to more specific menus.

        Returns:
            False, False, state index
        """

        is_exiting: bool
        _is_confirming: bool

        state_i: int = STATE_I_SETTINGS

        if KEYBOARD.is_ctrl_on and K_c in KEYBOARD.pressed:
            self._handle_fps_dropdown_shortcuts()
        self.fps_dropdown.upt()

        is_ctrl_f_pressed: bool = KEYBOARD.is_ctrl_on and K_f in KEYBOARD.timed
        did_toggle_show_fps: bool = self.show_fps.upt(is_ctrl_f_pressed)
        if did_toggle_show_fps:
            event.post(event.Event(
                SETTINGS_FPS_ACTIVENESS_CHANGE,
                {"value": self.show_fps.is_checked}
            ))

        if KEYBOARD.is_ctrl_on and K_a in KEYBOARD.pressed:
            self._handle_autosave_dropdown_shortcuts()
        self.autosave_dropdown.upt()

        is_crash_save_dir_clicked: bool = self._crash_save_dir.upt()
        is_ctrl_s_pressed: bool = KEYBOARD.is_ctrl_on and K_s in KEYBOARD.timed
        if is_crash_save_dir_clicked or is_ctrl_s_pressed:
            event.post(event.Event(SETTINGS_CRASH_SAVE_DIR_CHOICE))

        is_ctrl_z_pressed: bool = KEYBOARD.is_ctrl_on and K_z in KEYBOARD.timed
        did_toggle_invert_zoom: bool = self.invert_zoom.upt(is_ctrl_z_pressed)
        if did_toggle_invert_zoom:
            event.post(event.Event(
                SETTINGS_ZOOM_DIRECTION_CHANGE,
                {"value": -1 if self.invert_zoom.is_checked else 1}
            ))

        prev_history_dropdown_option_i: int = self.history_dropdown.option_i

        if KEYBOARD.is_ctrl_on and K_h in KEYBOARD.pressed:
            self._handle_history_dropdown_shortcuts()
        self.history_dropdown.upt()

        if self.history_dropdown.option_i != prev_history_dropdown_option_i:
            event.post(event.Event(
                SETTINGS_HISTORY_MAX_SIZE_CHANGE,
                {"value": self.history_dropdown.values[self.history_dropdown.option_i]}
            ))

        is_exiting, _is_confirming = self._base_upt()
        if is_exiting:
            state_i = STATE_I_MAIN

        return False, False, state_i
