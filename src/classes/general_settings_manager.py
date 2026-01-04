"""Class to manage editing general settings."""

from pathlib import Path
from typing import Self, Final, Any

from pygame import Rect, Event, event, K_1, K_a, K_c, K_f, K_s

from src.classes.dropdown import Dropdown
from src.classes.clickable import Checkbox, Button
from src.classes.devices import KEYBOARD
from src.classes.text_label import HoverableTextLabel

from src.obj_utils import UIElement
from src.file_utils import prettify_path
from src.type_utils import DropdownOptionsInfo, RectPos
from src.consts import (
    SPECIAL_LAYER, UI_LAYER,
    SETTINGS_FPS_ACTIVENESS_CHANGE, SETTINGS_CRASH_SAVE_DIR_CHOICE,
)
from src.imgs import CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG, BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG

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
    ("Always"           , "(CTRL+A+1)", -1),
    ("Never"            , "(CTRL+A+2)", AUTOSAVE_MODE_NEVER),
    ("On Crash"         , "(CTRL+A+3)", AUTOSAVE_MODE_CRASH),
    ("Not on\nInterrupt", "(CTRL+A+4)", AUTOSAVE_MODE_INTERRUPT),
)

class GeneralSettingsManager(UIElement):
    """Class to manage editing general settings."""

    __slots__ = (
        "fps_dropdown", "show_fps",
        "autosave_dropdown",
        "crash_save_dir_str", "_crash_save_dir_text_label", "_crash_save_dir",
    )

    def __init__(self: Self, rect: Rect) -> None:
        """Creates the elements to edit general settings."""

        super().__init__()
        first_x: int  = rect.x + round(rect.w / 4 * 1)
        second_x: int = rect.x + round(rect.w / 4 * 2)

        self.fps_dropdown: Dropdown = Dropdown(
            RectPos(first_x - 8, rect.y + 200, "midright"),
            _FPS_DROPDOWN_OPTIONS, "FPS Cap", UI_LAYER + SPECIAL_LAYER
        )
        self.show_fps: Checkbox = Checkbox(
            RectPos(first_x + 8, rect.y + 200, "midleft"),
            (CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG), "Show fps", "(CTRL+F)", UI_LAYER
        )

        self.autosave_dropdown: Dropdown = Dropdown(
            RectPos(first_x + 8, self.show_fps.rect.bottom + 75, "topleft"),
            _AUTOSAVE_DROPDOWN_OPTIONS, "Autosave:", UI_LAYER + SPECIAL_LAYER,
            text_h=18, is_text_above=False
        )

        self.crash_save_dir_str: str = str(Path().resolve())

        crash_save_dir_text_label_y: int = (
            self.autosave_dropdown.init_pos.y + self.autosave_dropdown.rect.h + 75
        )
        self._crash_save_dir_text_label: HoverableTextLabel = HoverableTextLabel(
            RectPos(second_x, crash_save_dir_text_label_y, "midtop"),
            prettify_path(self.crash_save_dir_str), self.crash_save_dir_str, UI_LAYER, h=16
        )
        self._crash_save_dir: Button = Button(
            RectPos(second_x, self._crash_save_dir_text_label.rect.bottom + 4, "midtop"),
            (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "Crash Save\nDirectory", "(CTRL+S)",
            UI_LAYER, text_h=20
        )

        self.layer = UI_LAYER
        self.sub_objs = (
            self.fps_dropdown, self.show_fps,
            self.autosave_dropdown,
            self._crash_save_dir_text_label, self._crash_save_dir,
        )

    def set_crash_save_dir(self: Self, dir_str: str) -> None:
        """
        Sets the crash save directory and refreshes the text labels.

        Args:
            directory string
        """

        self.crash_save_dir_str = dir_str
        self._crash_save_dir_text_label.set_text(prettify_path(self.crash_save_dir_str))
        self._crash_save_dir_text_label.hovering_text_label.set_text(self.crash_save_dir_str)

    def set_info(self: Self, data: dict[str, Any]) -> None:
        """
        Sets all the settings from the data.

        Args:
            data
        """

        self.fps_dropdown.set_option_i(data["fps_cap_i"])

        self.show_fps.set_checked(data["is_fps_counter_active"])
        event.post(Event(SETTINGS_FPS_ACTIVENESS_CHANGE, {"value": self.show_fps.is_checked}))

        self.autosave_dropdown.set_option_i(data["autosave_mode_i"])

        self.set_crash_save_dir(data["crash_save_dir"])

    def _handle_fps_dropdown_shortcuts(self: Self) -> None:
        """Selects a fps cap if the user presses ctrl+f+1-9."""

        k: int

        num_shortcuts: int = min(len(self.fps_dropdown.values) - 1, 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                # Offsets by 1 because of placeholder option
                self.fps_dropdown.set_option_i(k - K_1 + 1)

    def _handle_autosave_dropdown_shortcuts(self: Self) -> None:
        """Selects an autosave mode if the user presses ctrl+a+1-9."""

        k: int

        num_shortcuts: int = min(len(self.autosave_dropdown.values) - 1, 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                # Offsets by 1 because of placeholder option
                self.autosave_dropdown.set_option_i(k - K_1 + 1)

    def _handle_fps_dropdown_shortcuts(self: Self) -> None:
        """Selects a fps cap if the user presses ctrl+f+1-9."""

        k: int

        num_shortcuts: int = min(len(self.fps_dropdown.values) - 1, 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                # Offsets by 1 because of placeholder option
                self.fps_dropdown.set_option_i(k - K_1 + 1)

    def _handle_autosave_dropdown_shortcuts(self: Self) -> None:
        """Selects an autosave mode if the user presses ctrl+a+1-9."""

        k: int

        num_shortcuts: int = min(len(self.autosave_dropdown.values) - 1, 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                # Offsets by 1 because of placeholder option
                self.autosave_dropdown.set_option_i(k - K_1 + 1)

    def upt(self: Self) -> None:
        """Allows editing general settings."""


        if KEYBOARD.is_ctrl_on and K_c in KEYBOARD.pressed:
            self._handle_fps_dropdown_shortcuts()
        self.fps_dropdown.upt()

        is_ctrl_f_pressed: bool = KEYBOARD.is_ctrl_on and K_f in KEYBOARD.timed
        did_toggle_show_fps: bool = self.show_fps.upt(is_ctrl_f_pressed)
        if did_toggle_show_fps:
            event.post(Event(
                SETTINGS_FPS_ACTIVENESS_CHANGE,
                {"value": self.show_fps.is_checked}
            ))

        if KEYBOARD.is_ctrl_on and K_a in KEYBOARD.pressed:
            self._handle_autosave_dropdown_shortcuts()
        self.autosave_dropdown.upt()

        self._crash_save_dir_text_label.upt()
        is_crash_save_dir_clicked: bool = self._crash_save_dir.upt()
        is_ctrl_s_pressed: bool = KEYBOARD.is_ctrl_on and K_s in KEYBOARD.timed
        if is_crash_save_dir_clicked or is_ctrl_s_pressed:
            event.post(Event(SETTINGS_CRASH_SAVE_DIR_CHOICE))
