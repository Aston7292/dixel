"""
Drawing program for pixel art.

----------INFO----------
There are 5 states, the main interface and 4 extra UI windows,
they can be opened by clicking their respective buttons,
they're for colors, grid, grid history and settings.

Mouse info:
    the MOUSE object contains current and previous coordinates, pressed and released buttons,
    scrolling amount, hovered object and cursor type.

Keyboard input:
    The KEYBOARD object contains 3 lists and the flags for control, shift, alt and numpad.
    There's a list for every currently pressed and released key and
    a temporary list that holds the pressed keys for one frame every 128ms,
    used for key repeat, has acceleration.

Objects info:
    Objects have an objs_info attribute, a list of sub objects, stored in the dataclass ObjInfo,
    sub objects can also be inactive, the active flag can be changed with ObjInfo.rec_set_active.
    Every object info is in the _states_objs_info attribute of the Dixel class,
    the attributes/methods below are automatically used and are required by every object.

Hovering info:
    The hover_rects attribute is a list of rects to determine the hovered object,
    the layer attribute is used to choose an object when more the one is hovered,
    the hovered object is the one with the highest layer.

Cursor type:
    The cursor_type attribute indicates the type the cursor will have when hovering that object.

Blitting:
    The blit_sequence attribute is a list with tuples of image, rect and layer,
    objects with an higher layer will be blitted on top of objects with a lower one.

    There are 4 layer types:
        background: background elements (e.g. grid, palettes manager, unsaved icon)
        element: UI elements (e.g. buttons, scrollbars)
        text: normal text labels
        top: special cases (e.g. tooltips)

    Layers can also be extended into the special group,
    they will still keep their hierarchy so special_top goes on top of special_text and so on
    but every special layer goes on top of any normal one, used for stuff like drop-down menus.

    The UI group extends the special group in a similar way,
    used for the UI windows of other states.

Entering a state:
    The enter method gets called when entering the object's state or when the object goes active,
    it initializes the relevant data, like the show_cursor flag of input boxes.

Leaving a state:
    The leave method gets called when leaving the object's state or when the object goes inactive,
    it clears the relevant data, like the selected tiles of the grid.

Window resizing:
    The resize method scales positions and images manually
    because blitting everything on an image, scaling it to match the window size and blitting it
    cause blurring and 1 pixel offsets at specific sizes, is slow
    and doesn't allow for custom behavior on some objects.

    Only the objects of the main and active state are resized,
    when changing state the state's objects are immediately resized.

Interacting with elements:
    Interaction is possible with an upt method,
    it contains a high level implementation of it's behavior.

----------TODO----------
- text with hovering text
- split Dixel
- more extensions
- option to change the palette to match the active colors
- UI to view grid history
- option to make drawing only affect the visible_area?
- custom utility wins
- have multiple files open
- handle old data files
- UIs as separate windows?
- gif?
- touch and pen support

- COLOR_PICKER:
    - hex_text as input box

- GRID_UI:
    - separate minimap from grid and place minimap in grid UI
    - add option to change offset and visible_area?
    - move image before resizing?

- TOOLS_MANAGER:
    - pencil (different shapes?, smooth edges?)
    - draw line (pixelated?)
    - draw rectangle (auto fill)
    - draw circle, semi circle and ellipse (auto fill, pixelated?)
    - copy and paste (flip and rotate?)
    - move, flip or rotate section (affects all grid)
    - change brightness of tile/area
    - scale section

optimizations:
    - profile
"""

import os
import json

from tkinter import filedialog, messagebox
from threading import Thread
from pathlib import Path
from json import JSONDecodeError
from collections import deque
from sys import argv, stderr
from io import BytesIO
from traceback import format_exc
from typing import Self, TypeAlias, Final, Any

os.environ["PYGAME_BLEND_ALPHA_SDL2"]    = "1"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame as pg
from pygame.locals import *
import numpy as np
from numpy import uint8
from numpy.typing import NDArray

from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Checkbox, Button
from src.classes.text_label import TextLabel
from src.classes.unsaved_icon import UnsavedIcon
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import (
    get_pixels, get_brush_dim_checkbox_info,
    prettify_path, try_read_file, try_write_file, handle_file_os_error,
    try_get_paths, try_create_dir, try_remove_element,
    print_funcs_profiles,
)
from src.obj_utils import UIElement, ObjInfo, rec_move_rect
import src.obj_utils as objs
from src.lock_utils import LockError, FileError, try_lock_file
from src.type_utils import XY, WH, RGBColor, HexColor, BlitInfo, RectPos
import src.vars as my_vars
from src.consts import (
    BLACK, WHITE, HEX_BLACK,
    WIN_INIT_W, WIN_INIT_H,
    FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I,
    ANIMATION_GROW, ANIMATION_SHRINK,
    SETTINGS_FPS_ACTIVENESS_CHANGE, SETTINGS_CRASH_SAVE_DIR_CHOICE,
    SETTINGS_ZOOM_DIRECTION_CHANGE, SETTINGS_HISTORY_MAX_SIZE_CHANGE,
)

# TODO: screenshots
_i: int
for _i in range(5):
    pg.font.init()  # Others aren't used
pg.key.stop_text_input()

# Window gets focused before starting, so it doesn't appear when exiting early
_WIN: Final[pg.Window] = pg.Window(
    "Dixel", (WIN_INIT_W, WIN_INIT_H),
    hidden=True, resizable=True, allow_high_dpi=True
)
_WIN_SURF: Final[pg.Surface] = _WIN.get_surface()
_WIN.minimum_size = (950, 600)

# These files load images at the start which requires a window
from src.imgs import (
    ICON_IMG,
    BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG, BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG,
    X_MIRROR_OFF_IMG, X_MIRROR_ON_IMG, Y_MIRROR_OFF_IMG, Y_MIRROR_ON_IMG,
    SETTINGS_OFF_IMG, SETTINGS_ON_IMG,
)
from src.classes.grid_ui import GridUI
from src.classes.color_ui import ColorPicker
from src.classes.grid_manager import GridManager
from src.classes.settings_ui import (
    SettingsUI,
    AUTOSAVE_BEHAVIOR_NEVER, AUTOSAVE_BEHAVIOR_CRASH, AUTOSAVE_BEHAVIOR_INTERRUPT,
)
from src.classes.tools_manager import ToolsManager, ToolInfo
from src.classes.palettes_manager import PalettesManager

_StatesObjInfo: TypeAlias = tuple[tuple[ObjInfo, ...], ...]
_IgnoredExceptions: TypeAlias = tuple[type[Exception], ...] | None

_WIN.set_icon(ICON_IMG)

_SAVE: Final[Button] = Button(
    RectPos(0, 0, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Save"   , "(CTRL+S)"      , text_h=16
)
_SAVE_AS: Final[Button] = Button(
    RectPos(_SAVE.rect.right, _SAVE.rect.y, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Save As", "(CTRL+SHIFT+S)", text_h=16
)
_OPEN: Final[Button] = Button(
    RectPos(_SAVE_AS.rect.right, _SAVE_AS.rect.y, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Open"   , "(CTRL+O)"      , text_h=16
)
_CLOSE: Final[Button] = Button(
    RectPos(_OPEN.rect.right, _OPEN.rect.y, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Close"  , "(CTRL+W)"      , text_h=16
)

_GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center"),
    RectPos(WIN_INIT_W - 10, 10, "topright")
)

_BRUSH_DIMS: Final[CheckboxGrid] = CheckboxGrid(
    RectPos(10, _SAVE_AS.rect.bottom + 10, "topleft"),
    [get_brush_dim_checkbox_info(dim) for dim in range(1, 6)],
    num_cols=5, should_invert_cols=False, should_invert_rows=False
)
_X_MIRROR: Final[Checkbox] = Checkbox(
    RectPos(_BRUSH_DIMS.rect.x       , _BRUSH_DIMS.rect.bottom + 10, "topleft"),
    [X_MIRROR_OFF_IMG, X_MIRROR_ON_IMG], None, "Mirror Horizontally\n(SHIFT+H)"
)
_Y_MIRROR: Final[Checkbox] = Checkbox(
    RectPos(_X_MIRROR.rect.right + 10, _BRUSH_DIMS.rect.bottom + 10, "topleft"),
    [Y_MIRROR_OFF_IMG, Y_MIRROR_ON_IMG], None, "Mirror Vertically\n(SHIFT+V)"
)

_ADD_COLOR: Final[Button] = Button(
    RectPos(WIN_INIT_W        - 10, WIN_INIT_H - 10, "bottomright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Add\nColor", "(CTRL+A)"
)
_EDIT_GRID: Final[Button] = Button(
    RectPos(_ADD_COLOR.rect.x - 10, WIN_INIT_H - 10, "bottomright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Edit Grid" , "(CTRL+G)"
)
_OPEN_SETTINGS: Final[Button] = Button(
    RectPos(_GRID_MANAGER.grid.minimap_rect.x - 16, _GRID_MANAGER.grid.minimap_rect.y, "topright"),
    [SETTINGS_OFF_IMG, SETTINGS_ON_IMG], None, "(CTRL+COMMA)"
)

_PALETTES_MANAGER: Final[PalettesManager] = PalettesManager(
    RectPos(_ADD_COLOR.rect.centerx, _ADD_COLOR.rect.y - 25, "bottomright")
)
_TOOLS_MANAGER: Final[ToolsManager] = ToolsManager(
    RectPos(_BRUSH_DIMS.rect.x, WIN_INIT_H - 10, "bottomleft")
)

_FPS_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(WIN_INIT_W / 2), 0 , "midtop"),
    "FPS: 0"
)
_FILE_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(WIN_INIT_W / 2), _FPS_TEXT_LABEL.rect.bottom, "midtop"),
    "New File"
)
_UNSAVED_ICON: Final[UnsavedIcon] = UnsavedIcon()

_COLOR_PICKER: Final[ColorPicker] = ColorPicker()
_GRID_UI: Final[GridUI]           = GridUI()
_SETTINGS_UI: Final[SettingsUI]   = SettingsUI()

_STATE_I_MAIN: Final[int]     = 0
_STATE_I_COLOR: Final[int]    = 1
_STATE_I_GRID: Final[int]     = 2
_STATE_I_SETTINGS: Final[int] = 4
_FPS_TEXT_LABEL_OBJ_INFO: Final[ObjInfo] = ObjInfo(_FPS_TEXT_LABEL)
_STATES_MAIN_OBJS_INFO: Final[_StatesObjInfo] = (
    (
        ObjInfo(_SAVE), ObjInfo(_SAVE_AS), ObjInfo(_OPEN), ObjInfo(_CLOSE),
        ObjInfo(_GRID_MANAGER), ObjInfo(_BRUSH_DIMS), ObjInfo(_X_MIRROR), ObjInfo(_Y_MIRROR),
        ObjInfo(_ADD_COLOR), ObjInfo(_EDIT_GRID), ObjInfo(_OPEN_SETTINGS),
        ObjInfo(_PALETTES_MANAGER), ObjInfo(_TOOLS_MANAGER),
        _FPS_TEXT_LABEL_OBJ_INFO, ObjInfo(_FILE_TEXT_LABEL), ObjInfo(_UNSAVED_ICON),
    ),
    (ObjInfo(_COLOR_PICKER),),
    (ObjInfo(_GRID_UI),),
    (),
    (ObjInfo(_SETTINGS_UI),),
)

_EXIT_NO: Final[int]        = 0
_EXIT_OK: Final[int]        = 1
_EXIT_CRASH: Final[int]     = 2
_EXIT_INTERRUPT: Final[int] = 3

_WIN_EVENTS: Final[tuple[int, ...]] = (
    WINDOWRESTORED,
    WINDOWMINIMIZED, WINDOWMAXIMIZED,
    WINDOWMOVED, WINDOWSIZECHANGED,
    WINDOWFOCUSLOST,
)
_DEVICE_EVENTS: Final[tuple[int, ...]] = (
    MOUSEWHEEL,
    KEYDOWN, KEYUP, KEYMAPCHANGED,
)

_FILE_SAVE_AS_REQUEST: Final[int]       = pg.event.custom_type()
_FILE_OPEN_REQUEST: Final[int]          = pg.event.custom_type()
_FILE_CRASH_SAVE_DIR_CHANGE: Final[int] = pg.event.custom_type()
_TIMED_UPDATE_1000: Final[int]          = pg.event.custom_type()
_CLOCK: Final[pg.Clock] = pg.Clock()


def _ensure_valid_img_format(file_str: str) -> str:
    """
    Changes a path to a png if it's not a supported format.

    Path.with_suffix() doesn't always produce the wanted result,
    for example Path(".txt").with_suffix(".png") is Path(".txt.png"),
    it also raises ValueError on empty names.

    Args:
        file string
    Returns:
        file string
    """

    file_path: Path = Path(file_str)
    sections: list[str] = file_path.name.rsplit(".", maxsplit=1)
    if len(sections) == 1:
        sections.append("png")
    elif sections[1] not in ("png", "bmp"):
        sections[1] = "png"

    return str(file_path.parent / f"{sections[0]}.{sections[1]}")


def _try_get_grid_img(file_str: str, ignored_exceptions: _IgnoredExceptions) -> pg.Surface | None:
    """
    Loads a grid image with retries.

    Args:
        file string, ignored exceptions (None = all)
    Returns:
        image (can be None)
    """

    attempt_i: int
    should_retry: bool

    file_path: Path = Path(file_str)
    img: pg.Surface | None = None

    exception: type[Exception] | None = None
    error_str: str = ""
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            with file_path.open("rb") as f:
                try_lock_file(f, is_shared=True)
                img_bytes: BytesIO = BytesIO(try_read_file(f))
                img = pg.image.load(img_bytes, namehint=file_path.name).convert_alpha()
            break
        except (FileNotFoundError, PermissionError, LockError, FileError, pg.error) as e:
            errors_str: dict[type[Exception], str] = {
                FileNotFoundError: "File missing.",
                PermissionError: "Permission denied.",
                LockError: "File locked.",
                FileError: e.error_str if isinstance(e, FileError) else "",
                pg.error: str(e),
            }

            exception = type(e)
            error_str = errors_str[exception]
            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            exception = type(e)
            break

    if img is None and (ignored_exceptions is not None and exception not in ignored_exceptions):
        messagebox.showerror("Image Load Failed", f"{file_path.name}: {error_str}")
    return img


class _Dixel:
    """Drawing program for pixel art."""

    __slots__ = (
        "_orig_win_xy", "_orig_win_wh", "_is_minimized", "_is_maximized", "_is_fullscreen",
        "_file_str", "_new_file_str", "_is_saved",
        "_is_asking_file_save_as", "_is_asking_file_open", "_is_asking_crash_save_dir",
        "_state_i",
    )

    def __init__(self: Self) -> None:
        """Loads the data, handles argv and gets the full objects list."""

        obj: UIElement

        self._orig_win_xy: XY = _WIN.position
        self._orig_win_wh: WH = _WIN.size
        self._is_minimized: bool  = False
        self._is_maximized: bool  = False
        self._is_fullscreen: bool = False

        self._file_str: str     = ""
        self._new_file_str: str = ""
        self._is_saved: bool = False

        self._is_asking_file_save_as: bool   = False
        self._is_asking_file_open: bool      = False
        self._is_asking_crash_save_dir: bool = False

        self._state_i: int = _STATE_I_MAIN

        self._load_data()
        self._load_palettes()

        img: pg.Surface | None = None
        if len(argv) > 1:
            img = self._handle_argv_path()
        elif self._file_str != "":
            img = _try_get_grid_img(self._file_str, ignored_exceptions=(FileNotFoundError,))

        self._is_saved = img is not None
        if self._is_saved:
            _GRID_MANAGER.grid.set_tiles(img)
            _UNSAVED_ICON.set_radius(0)
        else:
            self._file_str = ""
            _GRID_MANAGER.grid.refresh_full()
            _UNSAVED_ICON.set_radius(_UNSAVED_ICON.init_radius)
        self._refresh_file_text_label()

        self._refresh_objs(should_refresh_only_active_state=False)
        for obj in objs.state_active_objs:
            obj.enter()

        _WIN.show()
        # It's better to modify the window after show
        if self._is_maximized:
            _WIN.maximize()
        if self._is_fullscreen:
            _WIN.set_fullscreen(desktop=True)
        _WIN.focus()

        pg.time.set_timer(_TIMED_UPDATE_1000, 1_000)

    def _try_get_data(self: Self) -> dict[str, Any]:
        """
        Gets the data from the data file with retries.

        Returns:
            data (if it fails returns the default data)
        """

        attempt_i: int
        error_str: str
        should_retry: bool

        data: dict[str, Any] = {
            "file": "",

            "grid_cols"        : 64,
            "grid_rows"        : 64,
            "grid_visible_cols": 32,
            "grid_visible_rows": 32,
            "grid_offset_x"    : 0,
            "grid_offset_y"    : 0,

            "is_x_mirror_on": False,
            "is_y_mirror_on": False,

            "brush_dim_i"    : 0,
            "tool_i"         : 0,
            "active_palette" : 1,

            "grid_ratio": None,

            "orig_win_xy": self._orig_win_xy,
            "orig_win_wh": self._orig_win_wh,
            "is_maximized" : False,
            "is_fullscreen": False,

            "fps_cap_i": 2,  # 60 FPS
            "is_fps_counter_active": True,
            "autosave_behavior_i": 1,  # Always
            "crash_save_dir": str(Path().resolve()),
            "is_zooming_inverted": False,
            "grid_history_max_size_i": 5,  # 512
        }
        data_path: Path = Path("assets", "data", "data.json")
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                with data_path.open("rb") as f:
                    try_lock_file(f, is_shared=True)
                    data = json.loads(try_read_file(f))
                break
            except FileNotFoundError:
                break
            except (PermissionError, JSONDecodeError, LockError, FileError) as e:
                errors_str: dict[type[Exception], str] = {
                    PermissionError: "Permission denied.",
                    JSONDecodeError: "Invalid json.",
                    LockError: "File locked.",
                    FileError: e.error_str if isinstance(e, FileError) else "",
                }

                error_str = errors_str[type(e)]
                messagebox.showerror("Data Load Failed", error_str)
                break
            except OSError as e:
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                messagebox.showerror("Data Load Failed", error_str)
                break

        return data

    def _load_data(self: Self) -> None:
        """Loads the data from the data file."""

        data: dict[str, Any] = self._try_get_data()
        if data["file"] != "":
            self._file_str = _ensure_valid_img_format(data["file"])

        _BRUSH_DIMS.check(data["brush_dim_i"])
        _TOOLS_MANAGER.check(data["tool_i"])
        _PALETTES_MANAGER.palette_dropdown.option_i = data["active_palette"]
        _GRID_MANAGER.grid.brush_dim = _BRUSH_DIMS.clicked_i + 1

        # refresh_full is called later
        _GRID_MANAGER.grid.set_info(
            np.zeros((data["grid_cols"], data["grid_rows"], 4), uint8),
            data["grid_visible_cols"], data["grid_visible_rows"],
            data["grid_offset_x"], data["grid_offset_y"],
            should_reset_history=True
        )

        if data["is_x_mirror_on"]:
            _X_MIRROR.set_checked(True)
            _GRID_MANAGER.is_x_mirror_on = True
        if data["is_y_mirror_on"]:
            _Y_MIRROR.set_checked(True)
            _GRID_MANAGER.is_y_mirror_on = True

        if data["grid_ratio"] is not None:
            _GRID_UI.w_ratio, _GRID_UI.h_ratio = data["grid_ratio"]
            _GRID_UI.checkbox.set_checked(True)

        if data["orig_win_xy"] != self._orig_win_xy:
            _WIN.position = self._orig_win_xy = data["orig_win_xy"]
        if data["orig_win_wh"] != self._orig_win_wh:
            # Triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
            _WIN.size     = self._orig_win_wh = data["orig_win_wh"]
        self._is_maximized  = data["is_maximized"]
        self._is_fullscreen = data["is_fullscreen"]

        _SETTINGS_UI.set_info(data)

    def _try_get_palette_data(
            self: Self, data_path: Path, errors_list: list[str]
    ) -> dict[str, Any] | None:
        """
        Gets the palette data from a file with retries.

        Args:
            palette path, errors list
        Returns:
            data (can be None)
        """

        attempt_i: int
        error_str: str
        should_retry: bool

        data: dict[str, Any] | None = None
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                with data_path.open("rb") as f:
                    try_lock_file(f, is_shared=True)
                    data = json.loads(try_read_file(f))
                break
            except FileNotFoundError:
                break
            except (PermissionError, JSONDecodeError, LockError, FileError) as e:
                errors_str: dict[type[Exception], str] = {
                    PermissionError: "Permission denied.",
                    JSONDecodeError: "Invalid json.",
                    LockError: "File locked.",
                    FileError: e.error_str if isinstance(e, FileError) else "",
                }

                error_str = errors_str[type(e)]
                errors_list.append(f"{data_path}: {error_str}")
                break
            except OSError as e:
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                errors_list.append(f"{data_path}: {error_str}")
                break

        return data

    def _load_palettes(self: Self) -> None:
        """Loads the palettes from the palettes files."""

        palettes_paths: tuple[Path, ...]
        error_str: str | None
        data: dict[str, Any]

        palettes_paths, error_str = try_get_paths(Path("assets", "data", "palettes"))
        if error_str is not None:
            messagebox.showerror("Palettes Folder Load Failed", error_str)

        errors_list: list[str] = []
        all_data: list[dict[str, Any] | None] = [
            self._try_get_palette_data(palette_path, errors_list)
            for palette_path in palettes_paths
        ]
        if errors_list != []:
            messagebox.showerror("Palettes Data Load Failed", "\n".join(errors_list))

        # Offsets by 1 because of placeholder option
        palette_i: int = min(max(_PALETTES_MANAGER.palette_dropdown.option_i, 1), len(all_data))
        valid_data: list[dict[str, Any]] = [data for data in all_data if data is not None]
        if valid_data == []:
            valid_data = [{
                "color_i": 0,
                "offset_y": 0,
                "drop-down_i": None,
                "colors": ["000000"],
            }]

            _PALETTES_MANAGER.palette_dropdown.option_i = 1
        elif all_data[palette_i - 1] is None:
            _PALETTES_MANAGER.palette_dropdown.option_i = 1
        else:
            palette_i_offset: int = all_data[:palette_i].count(None)
            _PALETTES_MANAGER.palette_dropdown.option_i = palette_i - palette_i_offset

        for data in valid_data:
            _PALETTES_MANAGER.add_palette(
                data["colors"], data["color_i"], data["offset_y"],
                data["drop-down_i"],
            )
        _PALETTES_MANAGER.refresh_palette()
        _PALETTES_MANAGER.refresh_dropdown()

    def _parse_argv(self: Self) -> list[str]:
        """
        Gets the file path and flags from cmd args.

        Returns:
            flags
        """

        self._file_str = ""

        flags: list[str] = []
        should_parse_flags: bool = True
        for arg in argv[1:]:
            if arg == "--":
                should_parse_flags = False
            elif should_parse_flags and arg.startswith("--"):
                flags.append(arg.lower())
            elif self._file_str == "":
                self._file_str = arg

        return flags

    def _try_create_argv(self: Self, flags: list[str]) -> pg.Surface | None:
        """
        Creates a file if --mk-file is in the flags and a directory if --mk-dir is in the flags.

        Args:
            flags
        Returns:
            image (can be None)
        """

        file_path: Path = Path(self._file_str)
        should_create: bool = True
        if file_path.parent.is_dir():
            if "--mk-file" not in flags:
                print(
                    "The file doesn't exist, to create it add --mk-file.\n"
                    f'"{file_path}" --mk-file'
                )
                should_create = False
        elif   "--mk-dir" not in flags:
                print(
                    "The directory doesn't exist, to create it add --mk-dir.\n"
                    f'"{file_path}" --mk-dir'
                )
                should_create = False

        img: pg.Surface | None = None
        if should_create:
            img = _GRID_MANAGER.grid.try_save(self._file_str, should_ask_create_dir=False)
        return img

    def _handle_argv_path(self: Self) -> pg.Surface:
        """
        Handles file opening with cmd args with retries.

        Returns:
            grid image
        Raises:
            SystemExit: on --help or on failure
        """

        attempt_i: int
        error_str: str
        should_retry: bool

        flags: list[str] = self._parse_argv()
        if "--help" in flags:
            print(
                f"Usage: {argv[0]} <file path> <optional flag>\n"
                f"Example: {argv[0]} test (.png is default)\n"

                "FLAGS:\n"
                f"\t--mk-file: create file ({argv[0]} new_file --mk-file)\n"
                f"\t--mk-dir: create directory ({argv[0]} new_dir/new_file --mk-dir)"
            )
            pg.quit()
            raise SystemExit

        self._file_str = _ensure_valid_img_format(self._file_str)

        file_path: Path = Path(self._file_str)
        img: pg.Surface | None = None
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                with file_path.open("rb") as f:
                    try_lock_file(f, is_shared=True)
                    img_bytes: BytesIO = BytesIO(try_read_file(f))
                    img = pg.image.load(img_bytes, namehint=file_path.name).convert_alpha()
                break
            except FileNotFoundError:
                img = self._try_create_argv(flags)
                break
            except (PermissionError, LockError, FileError, pg.error) as e:
                errors_str: dict[type[Exception], str] = {
                    PermissionError: "Permission denied.",
                    LockError: "File locked.",
                    FileError: e.error_str if isinstance(e, FileError) else "",
                    pg.error: str(e),
                }

                error_str = errors_str[type(e)]
                print(f"Image Load Failed.\n{file_path.name}\n{error_str}", file=stderr)
                break
            except OSError as e:
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                print(f"Image Load Failed.\n{file_path.name}\n{error_str}" , file=stderr)
                break

        if img is None:
            pg.quit()
            raise SystemExit
        return img

    def _refresh_file_text_label(self: Self) -> None:
        """Refreshes the file text label with the shortened path or with New File."""

        if self._file_str == "":
            _FILE_TEXT_LABEL.set_text("New File")
        else:
            _FILE_TEXT_LABEL.set_text(prettify_path(self._file_str))

        _UNSAVED_ICON.rect.midleft = (
            _FILE_TEXT_LABEL.rect.right + 4,
            _FILE_TEXT_LABEL.rect.centery,
        )
        _UNSAVED_ICON.frame_rect.center = _UNSAVED_ICON.rect.center

    def _refresh_objs(self: Self, should_refresh_only_active_state: bool) -> None:
        """
        Gets every object with an objs_info attribute from either the active or all states.

        Args:
            refresh only active state flag
        """

        state_info: tuple[ObjInfo, ...]
        info: ObjInfo

        if should_refresh_only_active_state:
            full_active_state_info: list[ObjInfo] = list(_STATES_MAIN_OBJS_INFO[self._state_i])
            for info in full_active_state_info:
                full_active_state_info.extend(info.obj.objs_info)

            # Reverses to have sub objects before the main one
            # When resizing the main object can use their resized attributes
            full_active_state_info.reverse()
            objs.states_info[self._state_i] = full_active_state_info
        else:
            objs.states_info = []
            for state_info in _STATES_MAIN_OBJS_INFO:
                full_state_info: list[ObjInfo] = list(state_info)
                for info in full_state_info:
                    full_state_info.extend(info.obj.objs_info)

                # Reverses to have sub objects before the main one
                # When resizing the main object can use their resized attributes
                full_state_info.reverse()
                objs.states_info.append(full_state_info)

        objs.state_active_objs = [
            info.obj
            for info in objs.states_info[self._state_i] if info.is_active
        ]

    def _handle_draw(self: Self) -> None:
        """Gets every blit_sequence attribute and draws it to the screen."""

        blittable_objs: list[UIElement] = objs.state_active_objs.copy()
        if self._state_i != _STATE_I_MAIN:
            blittable_objs.extend([
                info.obj
                for info in objs.states_info[_STATE_I_MAIN] if info.is_active
            ])

        main_sequence: list[BlitInfo] = sorted(
            [blit_info for obj in blittable_objs for blit_info in obj.blit_sequence],
            key=lambda blit_info: blit_info[2]
        )

        _WIN_SURF.fill(BLACK)
        _WIN_SURF.fblits([(img, rect) for img, rect, _layer in main_sequence])
        _WIN.flip()

    def _change_state(self: Self) -> None:
        """Leaves, refreshes, enters and resizes every state active objects."""

        obj: UIElement

        for obj in objs.state_active_objs:
            obj.leave()

        objs.state_active_objs = [
            info.obj
            for info in objs.states_info[self._state_i] if info.is_active
        ]

        for obj in objs.state_active_objs:
            obj.enter()

        self._resize_objs()

    def _resize_objs(self: Self) -> None:
        """Resizes every object of the main and active state with a resize method."""

        info: ObjInfo

        resizable_objs_info: list[ObjInfo] = objs.states_info[self._state_i].copy()
        if self._state_i != _STATE_I_MAIN:
            resizable_objs_info.extend(objs.states_info[_STATE_I_MAIN])

        win_w_ratio: float = _WIN_SURF.get_width()  / WIN_INIT_W
        win_h_ratio: float = _WIN_SURF.get_height() / WIN_INIT_H
        for info in resizable_objs_info:
            info.obj.resize(win_w_ratio, win_h_ratio)

        _UNSAVED_ICON.rect.midleft = (
            _FILE_TEXT_LABEL.rect.right + 4,
            _FILE_TEXT_LABEL.rect.centery,
        )
        _UNSAVED_ICON.frame_rect.center = _UNSAVED_ICON.rect.center

        # Minimap keeps ratio
        rec_move_rect(
            _OPEN_SETTINGS,
            _GRID_MANAGER.grid.minimap_rect.x - 16, _GRID_MANAGER.grid.minimap_rect.y,
            win_w_ratio=1, win_h_ratio=1
        )

    def _handle_win_event(
            self: Self, event_type: int,
            did_restore: bool, did_move: bool, did_resize: bool
    ) -> tuple[bool, bool, bool]:
        """
        Handles window-related events.

        Args:
            event_type, did restore flag, did move flag, did resize flag
        Returns:
            did restore flag, did move flag, did resize flag
        """

        if   event_type == WINDOWRESTORED:
            did_restore = True
            self._is_minimized = False
        elif event_type == WINDOWMINIMIZED:
            self._is_minimized = True
        elif event_type == WINDOWMAXIMIZED:
            self._is_minimized, self._is_maximized = False, True
        elif event_type == WINDOWMOVED:
            did_move = True
        elif event_type == WINDOWSIZECHANGED:
            did_resize = True
            self._resize_objs()
        elif event_type == WINDOWFOCUSLOST:
            for obj in objs.state_active_objs:
                obj.leave()

        return did_restore, did_move, did_resize

    def _handle_key_press(self: Self, k: int) -> None:
        """
        Adds keys to the keyboard and checks for esc, F1 and F11.

        Args:
            key
        Raises:
            KeyboardInterrupt: on escape
        """

        if k == K_ESCAPE and self._state_i == _STATE_I_MAIN:
            raise KeyboardInterrupt

        # Modifying the size triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
        if   k == K_F1:
            if self._is_fullscreen:
                _WIN.set_windowed()
            if self._is_maximized:
                _WIN.restore()

            self._is_maximized = self._is_fullscreen = False
            _WIN.size = (WIN_INIT_W, WIN_INIT_H)
            _WIN.position = pg.WINDOWPOS_CENTERED
            self._orig_win_xy = _WIN.position
        elif k == K_F11:
            self._is_fullscreen = not self._is_fullscreen
            if self._is_fullscreen:
                _WIN.set_fullscreen(desktop=True)
            else:
                _WIN.set_windowed()

        KEYBOARD.add(k)

    def _handle_device_event(self: Self, event: pg.Event) -> None:
        """
        Handles device-related events.

        Args:
            event
        """

        if   event.type == MOUSEWHEEL:
            MOUSE.scroll_amount = event.y
        elif event.type == KEYDOWN:
            self._handle_key_press(event.key)
        elif event.type == KEYUP:
            KEYBOARD.remove(event.key)
        elif event.type == KEYMAPCHANGED:
            KEYBOARD.raws = KEYBOARD.pressed = KEYBOARD.released = KEYBOARD.timed = []
            KEYBOARD.is_ctrl_on   = False
            KEYBOARD.is_shift_on  = False
            KEYBOARD.is_alt_on    = False
            KEYBOARD.is_numpad_on = False

    def _refresh_unsaved_icon(self: Self, unsaved_color: pg.Color) -> None:
        """
        Checks if the image is unsaved and refreshes the unsaved icon.

        Args:
            unsaved color
        """

        img: pg.Surface | None = _try_get_grid_img(self._file_str, ignored_exceptions=None)
        if img is None:
            if self._is_saved:
                yellow: pg.Color = pg.Color(255, 255, 0)
                _UNSAVED_ICON.set_animation(ANIMATION_GROW  , yellow       , should_go_to_0=False)
                self._is_saved = False
        elif np.array_equal(_GRID_MANAGER.grid.tiles, get_pixels(img)):
            if not self._is_saved:
                _UNSAVED_ICON.set_animation(ANIMATION_SHRINK, WHITE        , should_go_to_0=True)
                self._is_saved = True
        elif self._is_saved:
                _UNSAVED_ICON.set_animation(ANIMATION_GROW  , unsaved_color, should_go_to_0=False)
                self._is_saved = False

    def _finish_ask_save_as(self: Self, file_str: str) -> None:
        """
        Saves the file after the user chooses it with tkinter.

        Args:
            file string
        """

        file_str = _ensure_valid_img_format(file_str)
        img: pg.Surface | None = _GRID_MANAGER.grid.try_save(file_str, should_ask_create_dir=True)
        if img is None:
                red: pg.Color = pg.Color(255, 0, 0)
                _UNSAVED_ICON.set_animation(ANIMATION_GROW, red  , should_go_to_0=False)
                self._is_saved = False
        else:
            self._file_str = file_str
            if not self._is_saved:
                green: pg.Color = pg.Color(0, 255, 0)
                _UNSAVED_ICON.set_animation(ANIMATION_GROW, green, should_go_to_0=True)
                self._is_saved = True
            self._refresh_file_text_label()

    def _finish_ask_open_file(self: Self, file_str: str) -> None:
        """
        Opens a file and loads it into the grid UI after the user chooses it with tkinter.

        Args:
            file string
        """

        file_str = _ensure_valid_img_format(file_str)
        new_file_img: pg.Surface | None = _try_get_grid_img(file_str, ignored_exceptions=())
        if new_file_img is None:
            self._new_file_str = ""
        else:
            self._new_file_str = file_str
            self._state_i = _STATE_I_GRID
            _GRID_UI.set_info(
                _GRID_MANAGER.grid.cols, _GRID_MANAGER.grid.rows,
                get_pixels(new_file_img)
            )

            self._change_state()

    def _handle_file_event(self: Self, event: pg.Event) -> None:
        """
        Handles the file-related events.

        Args:
            event
        """

        if event.type == _FILE_SAVE_AS_REQUEST:
            if event.path_str != "":
                self._finish_ask_save_as(event.path_str)
            self._is_asking_file_save_as = False

        elif event.type == _FILE_OPEN_REQUEST:
            if event.path_str != "":
                self._finish_ask_open_file(event.path_str)
            self._is_asking_file_open = False

        elif event.type == _FILE_CRASH_SAVE_DIR_CHANGE:
            if event.path_str != "":
                _SETTINGS_UI.crash_save_dir_str = event.path_str
                pretty_path_str: str = prettify_path(_SETTINGS_UI.crash_save_dir_str)
                _SETTINGS_UI.crash_save_dir_text_label.set_text(pretty_path_str)
            self._is_asking_crash_save_dir = False

    def _handle_settings_event(self: Self, event: pg.Event) -> None:
        """
        Handles the settings edit events.

        Args:
            event
        """

        if event.type == SETTINGS_FPS_ACTIVENESS_CHANGE:
            _FPS_TEXT_LABEL_OBJ_INFO.rec_set_active(event.value)
        elif event.type == SETTINGS_CRASH_SAVE_DIR_CHOICE and not self._is_asking_crash_save_dir:
            def _ask_crash_save_dir() -> None:
                """Asks a directory to save uncreated files to on crash with tkinter."""

                dir_str: str = filedialog.askdirectory(
                    title="Choose Directory",
                )
                # On some explorers closing doesn't return a string
                if not isinstance(dir_str, str):
                    dir_str = ""

                pg.event.post(pg.Event(_FILE_CRASH_SAVE_DIR_CHANGE, {"path_str": dir_str}))

            Thread(target=_ask_crash_save_dir, daemon=True).start()
            self._is_asking_crash_save_dir = True
        elif event.type == SETTINGS_ZOOM_DIRECTION_CHANGE:
            _GRID_MANAGER.grid.zoom_direction = event.value
        elif event.type == SETTINGS_HISTORY_MAX_SIZE_CHANGE:
            _GRID_MANAGER.grid.history = deque(_GRID_MANAGER.grid.history, event.value)
            max_history_i: int = len(_GRID_MANAGER.grid.history) - 1
            _GRID_MANAGER.grid.history_i = min(_GRID_MANAGER.grid.history_i, max_history_i)

    def _handle_events(self: Self) -> None:
        """
        Handles the events.

        Raises:
            SystemExit: on main window close
        """

        event: pg.Event

        prev_is_minimized: bool = self._is_minimized
        did_restore: bool    = False
        did_win_move: bool   = False
        did_win_resize: bool = False
        for event in pg.event.get():
            if event.type == WINDOWCLOSE:
                self._save(_EXIT_OK, should_ask_create_dir=False)
                pg.quit()
                raise SystemExit

            # Handled after everything is processed to have the updated flags
            if event.type in _WIN_EVENTS:
                did_restore, did_win_move, did_win_resize = self._handle_win_event(
                    event.type,
                    did_restore, did_win_move, did_win_resize
                )
            elif event.type in _DEVICE_EVENTS:
                self._handle_device_event(event)
            elif _FILE_SAVE_AS_REQUEST <= event.type <= _FILE_CRASH_SAVE_DIR_CHANGE:
                self._handle_file_event(event)
            elif SETTINGS_FPS_ACTIVENESS_CHANGE <= event.type <= SETTINGS_HISTORY_MAX_SIZE_CHANGE:
                self._handle_settings_event(event)
            elif event.type == _TIMED_UPDATE_1000:
                _FPS_TEXT_LABEL.set_text(f"FPS: {_CLOCK.get_fps():.2f}")
                if self._file_str != "":
                    self._refresh_unsaved_icon(pg.Color(255, 255, 0))

        if did_restore and not (self._is_minimized != prev_is_minimized or self._is_fullscreen):
            self._is_maximized = False

        if not (self._is_maximized or self._is_fullscreen):
            if did_win_move:
                self._orig_win_xy = _WIN.position
            if did_win_resize:
                self._orig_win_wh = _WIN.size

    def _handle_resize_with_keys(self: Self) -> None:
        """Handles resizing the window with the keyboard."""

        win_w: int = self._orig_win_wh[0]
        win_h: int = self._orig_win_wh[1]
        if K_F5 in KEYBOARD.timed:
            win_w -= 1
        if K_F6 in KEYBOARD.timed:
            win_w += 1
        if K_F7 in KEYBOARD.timed:
            win_h -= 1
        if K_F8 in KEYBOARD.timed:
            win_h += 1

        if win_w != self._orig_win_wh[0] or win_h != self._orig_win_wh[1]:
            # Triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
            _WIN.size = (win_w, win_h)

    def _save_palette(self: Self, i: int, errors_list: list[str]) -> None:
        """
        Saves a palette to a separate file with retries.

        Args:
            index, errors list
        """

        error_str: str | None
        should_retry: bool

        data: dict[str, Any] = {
            "color_i"    : _PALETTES_MANAGER.clicked_indexes[i],
            "offset_y"   : _PALETTES_MANAGER.offsets_y[i],
            "drop-down_i": _PALETTES_MANAGER.dropdown_indexes[i],
            "colors"     : _PALETTES_MANAGER.palettes[i],
        }

        palette_path: Path = Path("assets", "data", "palettes", f"palette_{i}.json")
        palette_json: str = json.dumps(data, ensure_ascii=False, indent=4)
        palette_bytes: bytes = palette_json.encode("utf-8", errors="ignore")

        dir_creation_attempt_i: int = FILE_ATTEMPT_START_I
        system_attempt_i: int       = FILE_ATTEMPT_START_I
        while (
            dir_creation_attempt_i <= FILE_ATTEMPT_STOP_I and
            system_attempt_i       <= FILE_ATTEMPT_STOP_I
        ):
            try:
                # If you open in write mode it will clear the file even if it's locked
                with palette_path.open("ab") as f:
                    try_lock_file(f, is_shared=False)
                    try_write_file(f, palette_bytes)
                break
            except FileNotFoundError:
                dir_creation_attempt_i += 1
                error_str = try_create_dir(palette_path.parent, dir_creation_attempt_i)
                if error_str is not None:
                    errors_list.append(f"Directory {palette_path.parent}: {error_str}")
                    break
            except (PermissionError, LockError, FileError) as e:
                errors_str: dict[type[Exception], str] = {
                    PermissionError: "Permission denied.",
                    LockError: "File locked.",
                    FileError: e.error_str if isinstance(e, FileError) else "",
                }

                error_str = errors_str[type(e)]
                errors_list.append(f"{palette_path}: {error_str}")
                break
            except OSError as e:
                system_attempt_i += 1
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** system_attempt_i)
                    continue

                errors_list.append(f"{palette_path}: {error_str}")
                break

    def _save_palettes(self: Self) -> None:
        """Refreshes the palettes data and saves them to files in the palettes directory."""

        palettes_paths: tuple[Path, ...]
        _error_str: str | None
        palette_path: Path
        palette_i: int

        # Offsets by 1 because of placeholder option
        active_palette_i: int = _PALETTES_MANAGER.palette_dropdown.option_i - 1
        clicked_i: int = _PALETTES_MANAGER.colors_grid.clicked_i
        offset_y: int = _PALETTES_MANAGER.colors_grid.offset_y
        _PALETTES_MANAGER.clicked_indexes[ active_palette_i] = clicked_i
        _PALETTES_MANAGER.offsets_y[       active_palette_i] = offset_y
        _PALETTES_MANAGER.dropdown_indexes[active_palette_i] = _PALETTES_MANAGER.dropdown_i

        palettes_paths, _error_str = try_get_paths(Path("assets", "data", "palettes"))
        for palette_path in palettes_paths:
            try_remove_element(palette_path)

        errors_list: list[str] = []
        for palette_i in range(len(_PALETTES_MANAGER.palettes)):
            self._save_palette(palette_i, errors_list)

        if errors_list != []:
            messagebox.showerror("Palettes Save Failed", "\n".join(errors_list))

    def _save_img(self: Self, exit_type: int, should_ask_create_dir: bool) -> None:
        """
        Saves the image if it should and updates the unsaved icon.

        Args:
            exit type, ask create directory flag
        """

        if exit_type != _EXIT_NO:
            autosave_behavior_i: int = _SETTINGS_UI.autosave_dropdown.option_i
            autosave_behavior: int = _SETTINGS_UI.autosave_dropdown.values[autosave_behavior_i]
            if (
                 autosave_behavior == AUTOSAVE_BEHAVIOR_NEVER or
                (autosave_behavior == AUTOSAVE_BEHAVIOR_CRASH     and exit_type != _EXIT_CRASH) or
                (autosave_behavior == AUTOSAVE_BEHAVIOR_INTERRUPT and exit_type == _EXIT_INTERRUPT)
            ):
                return

        img: pg.Surface | None = _GRID_MANAGER.grid.try_save(self._file_str, should_ask_create_dir)
        if img is None:
            red: pg.Color = pg.Color(255, 0, 0)
            _UNSAVED_ICON.set_animation(ANIMATION_GROW, red  , should_go_to_0=False)
            self._is_saved = False
        elif not self._is_saved:
            green: pg.Color = pg.Color(0, 255, 0)
            _UNSAVED_ICON.set_animation(ANIMATION_GROW, green, should_go_to_0=True)
            self._is_saved = True

    def _save(self: Self, exit_type: int, should_ask_create_dir: bool) -> None:
        """
        Saves the data, palettes and image with retries.

        Args:
            exit type, ask create image directory flag
        """

        error_str: str | None
        should_retry: bool

        tool_i: int = (
            _TOOLS_MANAGER.tools_grid.clicked_i if _TOOLS_MANAGER.saved_clicked_i is None else
            _TOOLS_MANAGER.saved_clicked_i
        )
        grid_ratio: tuple[float, float] | None = (
            (_GRID_UI.w_ratio, _GRID_UI.h_ratio) if _GRID_UI.checkbox.is_checked else
            None
        )

        data: dict[str, Any] =  {
            "file": self._file_str,

            "grid_cols"        : _GRID_MANAGER.grid.cols,
            "grid_rows"        : _GRID_MANAGER.grid.rows,
            "grid_visible_cols": _GRID_MANAGER.grid.visible_cols,
            "grid_visible_rows": _GRID_MANAGER.grid.visible_rows,
            "grid_offset_x"    : _GRID_MANAGER.grid.offset_x,
            "grid_offset_y"    : _GRID_MANAGER.grid.offset_y,

            "is_x_mirror_on": _GRID_MANAGER.is_x_mirror_on,
            "is_y_mirror_on": _GRID_MANAGER.is_y_mirror_on,

            "brush_dim_i"     : _BRUSH_DIMS.clicked_i,
            "tool_i"          : tool_i,
            "active_palette"  : _PALETTES_MANAGER.palette_dropdown.option_i,

            "grid_ratio": grid_ratio,

            "orig_win_xy": self._orig_win_xy,
            "orig_win_wh": self._orig_win_wh,
            "is_maximized" : self._is_maximized,
            "is_fullscreen": self._is_fullscreen,

            "fps_cap_i": _SETTINGS_UI.fps_dropdown.option_i,
            "is_fps_counter_active": _FPS_TEXT_LABEL_OBJ_INFO.is_active,
            "autosave_behavior_i": _SETTINGS_UI.autosave_dropdown.option_i,
            "crash_save_dir": _SETTINGS_UI.crash_save_dir_str,
            "is_zooming_inverted": _SETTINGS_UI.invert_zoom.is_checked,
            "grid_history_max_size_i": _SETTINGS_UI.history_dropdown.option_i,
        }
        data_path: Path = Path("assets", "data", "data.json")
        data_json: str = json.dumps(data, ensure_ascii=False, indent=4)
        data_bytes: bytes = data_json.encode("utf-8", errors="ignore")

        dir_creation_attempt_i: int = FILE_ATTEMPT_START_I
        system_attempt_i: int       = FILE_ATTEMPT_START_I
        while (
            dir_creation_attempt_i <= FILE_ATTEMPT_STOP_I and
            system_attempt_i       <= FILE_ATTEMPT_STOP_I
        ):
            try:
                # If you open in write mode it will clear the file even if it's locked
                with data_path.open("ab") as f:
                    try_lock_file(f, is_shared=False)
                    try_write_file(f, data_bytes)
                break
            except FileNotFoundError:
                dir_creation_attempt_i += 1
                error_str = try_create_dir(data_path.parent, dir_creation_attempt_i)
                if error_str is not None:
                    messagebox.showerror("Data Directory Creation Failed", error_str)
                    break
            except (PermissionError, LockError, FileError) as e:
                errors_str: dict[type[Exception], str] = {
                    PermissionError: "Permission denied.",
                    LockError: "File locked.",
                    FileError: e.error_str if isinstance(e, FileError) else "",
                }

                error_str = errors_str[type(e)]
                messagebox.showerror("Data Save Failed", error_str)
                break
            except OSError as e:
                system_attempt_i += 1
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** system_attempt_i)
                    continue

                messagebox.showerror("Data Save Failed", error_str)
                break

        self._save_palettes()
        self._save_img(exit_type, should_ask_create_dir)

    def _upt_file_saving(self: Self) -> None:
        """Updates the save and save as button."""

        is_ctrl_s_pressed: bool       = False
        is_ctrl_shift_s_pressed: bool = False
        if KEYBOARD.is_ctrl_on and K_s in KEYBOARD.pressed:
            if KEYBOARD.is_shift_on:
                is_ctrl_shift_s_pressed = True
            else:
                is_ctrl_s_pressed       = True

        is_save_clicked: bool = _SAVE.upt()
        if is_save_clicked or is_ctrl_s_pressed:
            self._save(_EXIT_NO, should_ask_create_dir=True)

        is_save_as_clicked: bool = _SAVE_AS.upt()
        if (is_save_as_clicked or is_ctrl_shift_s_pressed) and not self._is_asking_file_save_as:
            def _ask_save_as() -> None:
                """Asks a file to save to with tkinter."""

                file_str: str = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=(
                        ("png Files"   , "*.png"),
                        ("Bitmap Files", "*.bmp"),
                    ),
                    title="Save As",
                )
                # On some explorers closing doesn't return a string
                if not isinstance(file_str, str):
                    file_str = ""

                pg.event.post(pg.Event(_FILE_SAVE_AS_REQUEST, {"path_str": file_str}))

            Thread(target=_ask_save_as, daemon=True).start()
            self._is_asking_file_save_as = True

    def _upt_file_opening(self: Self) -> None:
        """Updates the open file button."""

        is_open_clicked: bool = _OPEN.upt()
        is_ctrl_o_pressed: bool = KEYBOARD.is_ctrl_on and K_o in KEYBOARD.pressed
        if (is_open_clicked or is_ctrl_o_pressed) and not self._is_asking_file_open:
            def _ask_open_file() -> None:
                """Asks a file to open with tkinter."""

                file_str: str = filedialog.askopenfilename(
                    defaultextension=".png",
                    filetypes=(
                        ("png Files"   , "*.png"),
                        ("Bitmap Files", "*.bmp"),
                    ),
                    title="Open",
                )
                # On some explorers closing doesn't return a string
                if not isinstance(file_str, str):
                    file_str = ""

                pg.event.post(pg.Event(_FILE_OPEN_REQUEST, {"path_str": file_str}))

            Thread(target=_ask_open_file, daemon=True).start()
            self._is_asking_file_open = True

    def _upt_file_closing(self: Self) -> None:
        """Updates the close file button."""

        is_close_clicked: bool = _CLOSE.upt()
        is_ctrl_w_pressed: bool = KEYBOARD.is_ctrl_on and K_w in KEYBOARD.pressed
        if (is_close_clicked or is_ctrl_w_pressed) and self._file_str != "":
            _GRID_MANAGER.grid.try_save(self._file_str, should_ask_create_dir=True)

            self._file_str = ""
            self._is_saved = False
            _GRID_MANAGER.grid.set_tiles(None)
            _UNSAVED_ICON.set_animation(ANIMATION_GROW, WHITE, should_go_to_0=False)
            self._refresh_file_text_label()

    def _upt_ui_openers(self: Self) -> None:
        """Updates the buttons that open UIs."""

        is_add_color_clicked: bool = _ADD_COLOR.upt()
        is_ctrl_a_pressed: bool = KEYBOARD.is_ctrl_on and K_a in KEYBOARD.pressed
        if is_add_color_clicked or is_ctrl_a_pressed:
            self._state_i = _STATE_I_COLOR
            _COLOR_PICKER.set_color(HEX_BLACK, is_external_change=True)

        is_edit_grid_clicked: bool = _EDIT_GRID.upt()
        is_ctrl_g_pressed: bool = KEYBOARD.is_ctrl_on and K_g in KEYBOARD.pressed
        if is_edit_grid_clicked or is_ctrl_g_pressed:
            self._state_i = _STATE_I_GRID
            _GRID_UI.set_info(
                _GRID_MANAGER.grid.cols, _GRID_MANAGER.grid.rows,
                _GRID_MANAGER.grid.tiles
            )

        is_open_settings_clicked: bool = _OPEN_SETTINGS.upt()
        is_ctrl_comma_pressed: bool = KEYBOARD.is_ctrl_on and K_COMMA in KEYBOARD.pressed
        if is_open_settings_clicked or is_ctrl_comma_pressed:
            self._state_i = _STATE_I_SETTINGS

    def _handle_brush_dim_shortcuts(self: Self) -> None:
        """Selects a brush dimension if the user presses ctrl+b+dimension."""

        k: int

        num_shortcuts: int = min(len(_BRUSH_DIMS.checkboxes), 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                _BRUSH_DIMS.clicked_i        = k - K_1
                _GRID_MANAGER.grid.brush_dim = k - K_1 + 1

    def _main_interface(self: Self) -> None:
        """Handles the main interface."""

        hex_color: HexColor
        did_palette_change: bool
        hex_color_to_edit: HexColor | None

        self._upt_file_saving()
        self._upt_file_opening()
        self._upt_file_closing()
        self._upt_ui_openers()

        if KEYBOARD.is_ctrl_on and K_b in KEYBOARD.pressed:
            self._handle_brush_dim_shortcuts()

        _BRUSH_DIMS.upt()
        if _BRUSH_DIMS.clicked_i != _BRUSH_DIMS.prev_clicked_i:
            _BRUSH_DIMS.check(_BRUSH_DIMS.clicked_i)
            _GRID_MANAGER.grid.brush_dim = _BRUSH_DIMS.clicked_i + 1

        is_shift_h_pressed: bool = KEYBOARD.is_shift_on and K_h in KEYBOARD.timed
        _X_MIRROR.upt(is_shift_h_pressed)
        _GRID_MANAGER.is_x_mirror_on = _X_MIRROR.is_checked

        is_shift_v_pressed: bool = KEYBOARD.is_shift_on and K_v in KEYBOARD.timed
        _Y_MIRROR.upt(is_shift_v_pressed)
        _GRID_MANAGER.is_y_mirror_on = _Y_MIRROR.is_checked

        hex_color, did_palette_change, hex_color_to_edit = _PALETTES_MANAGER.upt()
        if did_palette_change:
            # Refreshes the hovered checkbox immediately
            self._refresh_objs(should_refresh_only_active_state=True)
            MOUSE.refresh_hovered_obj()
            _PALETTES_MANAGER.colors_grid.upt_checkboxes()
        if hex_color_to_edit is not None:
            self._state_i = _STATE_I_COLOR
            _COLOR_PICKER.set_color(hex_color_to_edit, is_external_change=True)

        tool_info: ToolInfo = _TOOLS_MANAGER.upt()
        if _TOOLS_MANAGER.tools_grid.clicked_i != _TOOLS_MANAGER.tools_grid.prev_clicked_i:
            _TOOLS_MANAGER.check(_TOOLS_MANAGER.tools_grid.clicked_i)
            _GRID_MANAGER.saved_col = _GRID_MANAGER.saved_row = None

        did_grid_change: bool = _GRID_MANAGER.upt(hex_color, tool_info)
        if did_grid_change and self._file_str != "":
            self._refresh_unsaved_icon(WHITE)
        if _GRID_MANAGER.eye_dropped_color is not None:
            did_palette_change = _PALETTES_MANAGER.try_add_color(_GRID_MANAGER.eye_dropped_color)
            if did_palette_change:
                self._refresh_objs(should_refresh_only_active_state=True)

    def _color_ui(self: Self) -> None:
        """Handles the color UI."""

        did_exit: bool
        did_confirm: bool
        rgb_color: RGBColor

        did_exit, did_confirm, rgb_color = _COLOR_PICKER.upt()
        if did_exit:
            self._state_i = _STATE_I_MAIN
        elif did_confirm:
            self._state_i = _STATE_I_MAIN

            did_palette_change: bool = _PALETTES_MANAGER.try_add_color(rgb_color)
            if did_palette_change:
                self._refresh_objs(should_refresh_only_active_state=True)

    def _grid_ui(self: Self) -> None:
        """Handles the grid UI."""

        did_exit: bool
        did_confirm: bool
        tiles: NDArray[uint8]

        did_exit, did_confirm, tiles = _GRID_UI.upt()
        if did_exit:
            self._new_file_str = ""
            self._state_i = _STATE_I_MAIN
        elif did_confirm:
            self._state_i = _STATE_I_MAIN

            is_opening_new_img: bool = self._new_file_str != ""
            if is_opening_new_img:
                _GRID_MANAGER.grid.try_save(self._file_str, should_ask_create_dir=True)
                self._file_str = self._new_file_str
                self._new_file_str = ""
                self._refresh_file_text_label()

            _GRID_MANAGER.grid.set_info(
                tiles,
                _GRID_MANAGER.grid.visible_cols, _GRID_MANAGER.grid.visible_rows,
                _GRID_MANAGER.grid.offset_x, _GRID_MANAGER.grid.offset_y,
                should_reset_history=is_opening_new_img
            )
            _GRID_MANAGER.grid.refresh_full()
            if not is_opening_new_img:
                _GRID_MANAGER.grid.add_to_history()

            if self._file_str != "":
                self._refresh_unsaved_icon(WHITE)

    def _settings_ui(self: Self) -> None:
        """Handles the settings UI."""

        did_exit: bool
        did_confirm: bool
        _extra_info: None

        did_exit, did_confirm, _extra_info = _SETTINGS_UI.upt()
        if did_exit or did_confirm:
            self._state_i = _STATE_I_MAIN

    def _handle_states(self: Self) -> None:
        """Handles updating and changing states."""

        prev_state_i: int = self._state_i

        if   self._state_i == _STATE_I_MAIN:
            self._main_interface()
        elif self._state_i == _STATE_I_COLOR:
            self._color_ui()
        elif self._state_i == _STATE_I_GRID:
            self._grid_ui()
        elif self._state_i == _STATE_I_SETTINGS:
            self._settings_ui()

        if self._state_i != prev_state_i:
            self._change_state()

    def _handle_crash(self: Self) -> None:
        """Saves before crashing."""

        if self._file_str == "":
            crash_save_dir_path: Path = Path(_SETTINGS_UI.crash_save_dir_str)
            file_path: Path = crash_save_dir_path / "new_file.png"
            duplicate_name_counter: int = 0
            while file_path.exists():
                duplicate_name_counter += 1
                file_path = crash_save_dir_path / f"new_file_{duplicate_name_counter}.png"

            self._file_str = str(file_path)

        self._save(_EXIT_CRASH, should_ask_create_dir=False)

    def run(self: Self) -> None:
        """App loop."""

        MOUSE.refresh_pos()
        MOUSE.prev_x, MOUSE.prev_y = MOUSE.x, MOUSE.y
        try:
            while True:
                fps_cap: int = _SETTINGS_UI.fps_dropdown.values[_SETTINGS_UI.fps_dropdown.option_i]
                last_frame_elapsed_time: float = _CLOCK.tick(fps_cap)
                my_vars.ticks = pg.time.get_ticks()
                my_vars.dt = (last_frame_elapsed_time / 1_000) * 60

                MOUSE.refresh_pos()
                MOUSE.pressed = pg.mouse.get_pressed()
                MOUSE.released = list(pg.mouse.get_just_released())
                MOUSE.scroll_amount = 0
                KEYBOARD.released = []

                self._handle_events()

                MOUSE.refresh_hovered_obj()
                MOUSE.refresh_type()
                KEYBOARD.refresh_timed()

                if KEYBOARD.timed != [] and not (self._is_maximized or self._is_fullscreen):
                    self._handle_resize_with_keys()

                self._handle_states()

                _UNSAVED_ICON.animate()
                self._handle_draw()

                MOUSE.prev_x, MOUSE.prev_y = MOUSE.x, MOUSE.y
        except KeyboardInterrupt:
            self._save(_EXIT_INTERRUPT, should_ask_create_dir=False)
        except Exception:
            self._handle_crash()
            print(format_exc(), file=stderr)

        pg.quit()


if __name__ == "__main__":
    _Dixel().run()
    print_funcs_profiles()
