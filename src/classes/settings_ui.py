"""Interface to edit the settings."""

from pathlib import Path
from typing import Final, Any

from pygame.locals import *

from src.classes.ui import UI
from src.classes.dropdown import Dropdown
from src.classes.clickable import Checkbox, Button
from src.classes.text_label import TextLabel
from src.classes.devices import KEYBOARD

from src.utils import RectPos, ObjInfo, prettify_path_str
from src.imgs import BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG, CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG


SETTINGS_EVENTS: list[int] = []
FPS_TOGGLE: Final[int]            = 0
CRASH_SAVE_DIR_CHANGE: Final[int] = 1


class SettingsUI(UI):
    """Class to create an interface that allows editing the setting."""

    __slots__ = (
        "show_fps", "fps_dropdown",
        "crash_save_dir_str", "_crash_save_dir", "crash_save_dir_text_label",
    )

    def __init__(self) -> None:
        """Creates the interface and the elements to edit general settings."""

        super().__init__("EDIT SETTING", False)

        self.show_fps: Checkbox = Checkbox(
            RectPos(self._rect.centerx + 16, self._rect.centery, "midleft"),
            [CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG], "Show fps", "(CTRL+F)", self.layer
        )
        self.show_fps.img_i = 1
        self.show_fps.is_checked = True

        self.fps_dropdown: Dropdown = Dropdown(
            RectPos(self._rect.centerx - 16, self._rect.centery, "midright"),
            [
                ("30"  , "(CTRL+C+1)", 30 ),
                ("60"  , "(CTRL+C+2)", 60 ),
                ("120" , "(CTRL+C+3)", 120),
                ("240" , "(CTRL+C+4)", 240),
                ("None", "(CTRL+C+5)", 0  ),
            ],
            "FPS Cap", self.layer
        )
        self.fps_dropdown.set_option_i(2)  # Offset by 1 because of placeholder option

        self.crash_save_dir_str: str = str(Path().resolve())
        self._crash_save_dir: Button = Button(
            RectPos(self._rect.centerx, self._rect.bottom - 100, "midbottom"),
            [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Crash Save\nDirectory", "(CTRL+S)",
            self.layer, 20
        )
        self.crash_save_dir_text_label: TextLabel = TextLabel(
            RectPos(self._crash_save_dir.rect.centerx, self._crash_save_dir.rect.y - 5, "midbottom"),
            prettify_path_str(self.crash_save_dir_str), self.layer
        )

        self.objs_info.extend((
            ObjInfo(self.show_fps), ObjInfo(self.fps_dropdown),
            ObjInfo(self._crash_save_dir), ObjInfo(self.crash_save_dir_text_label),
        ))

    def _handle_fps_dropdown_shortcuts(self) -> None:
        """Selects a fps cap if the user presses ctrl+f+option_number."""

        k: int

        num_shortcuts: int = min(len(self.fps_dropdown.values), 9)
        keys: list[int] = KEYBOARD.pressed
        for k in range(K_1, K_1 + num_shortcuts):
            if k in keys:
                self.fps_dropdown.set_option_i(k - K_1 + 1)  # Offset by 1 because of placeholder option

    def upt(self) -> tuple[bool, bool, Any]:
        """
        Allows editing generic settings and going to more specific menus.

        Returns:
            exiting flag, confirming flag
        """

        is_exiting: bool
        is_confirming: bool

        is_ctrl_f_pressed: bool = KEYBOARD.is_ctrl_on and K_f in KEYBOARD.timed
        did_toggle_show_fps: bool = self.show_fps.upt(is_ctrl_f_pressed)
        if did_toggle_show_fps:
            SETTINGS_EVENTS.append(FPS_TOGGLE)

        if KEYBOARD.is_ctrl_on and K_c in KEYBOARD.pressed:
            self._handle_fps_dropdown_shortcuts()
        self.fps_dropdown.upt()

        is_crash_save_dir_clicked: bool = self._crash_save_dir.upt()
        if is_crash_save_dir_clicked:
            SETTINGS_EVENTS.append(CRASH_SAVE_DIR_CHANGE)

        is_exiting, is_confirming = self._base_upt()
        return is_exiting, is_confirming
