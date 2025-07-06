"""
Drawing program for pixel art.

----------INFO----------
There are 5 states, the main interface and 4 extra UI windows,
they can be opened by clicking their respective buttons,
they're for colors, grid, grid history and settings.

Mouse info:
    the MOUSE object contains current and previous coordinates, pressed and released buttons,
    scroll amount, hovered object and cursor type.

Keyboard input:
    The KEYBOARD object contains 3 lists and the flags for control, shift, alt and numpad.
    There's a list for every currently pressed and released key and
    a temporary list that holds the pressed keys for one frame every 150ms,
    used for key repeat, has acceleration.

Objects info:
    Objects have an objs_info attribute, a list of sub objects, stored in the dataclass ObjInfo,
    sub objects can also be inactive, the active flag can be changed with ObjInfo.set_active.
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
        background: background elements (e.g. grid, palette manager, unsaved icon)
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

    Only the objects of the main and current state are resized,
    when changing state the state's objects are immediately resized.

Interacting with elements:
    Interaction is possible with an upt method,
    it contains a high level implementation of it's behavior.

----------TODO----------
- better grid transition?
- split Dixel
- more extensions
- option to change the palette to match the current colors/multiple palettes
- UI to view grid history
- option to make drawing only affect the visible_area?
- way to close without auto saving?
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
    - add option to change visible_area?
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
    - better memory usage in PaletteManager
"""

import queue
import json

from tkinter import filedialog, messagebox
from threading import Thread
from queue import Queue
from pathlib import Path
from json import JSONDecodeError
from sys import argv
from contextlib import suppress
from typing import TypeAlias, Final, Any

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
    UIElement, RectPos, ObjInfo,
    get_pixels, get_brush_dim_checkbox_info,
    prettify_path_str, handle_file_os_error, try_create_dir, rec_move_rect,
    print_funcs_profiles,
)
from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import XY, WH, RGBColor, HexColor, BlitInfo
from src.consts import (
    BLACK, WHITE, HEX_BLACK,
    WIN_INIT_W, WIN_INIT_H,
    FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I,
    TIME, ANIMATION_I_GROW, ANIMATION_I_SHRINK,
)

_i: int
for _i in range(5):
    pg.init()
pg.key.stop_text_input()

# Window is focused before starting, so it doesn't appear when exiting early
_WIN: Final[pg.Window] = pg.Window(
    "Dixel", (WIN_INIT_W, WIN_INIT_H),
    hidden=True, resizable=True, allow_high_dpi=True
)
_WIN_SURF: Final[pg.Surface] = _WIN.get_surface()
_WIN.minimum_size = (900, 550)

# These files load images at the start which requires a window
from src.imgs import (
    ICON_IMG,
    BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG, BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG,
    X_MIRROR_OFF_IMG, X_MIRROR_ON_IMG, Y_MIRROR_OFF_IMG, Y_MIRROR_ON_IMG,
    SETTINGS_OFF_IMG, SETTINGS_ON_IMG,
)
from src.classes.grid_ui import GridUI
from src.classes.color_ui import ColorPicker
from src.classes.grid_manager import Grid, GridManager
from src.classes.settings_ui import (
    SettingsUI, SETTINGS_EVENTS, FPS_TOGGLE, CRASH_SAVE_DIR_CHANGE
)
from src.classes.tools_manager import ToolsManager, ToolInfo
from src.classes.palette_manager import PaletteManager

_StatesObjInfo: TypeAlias = tuple[list[ObjInfo], ...]
_AskedFilesQueue: TypeAlias = Queue[tuple[str, int]]
_IgnoredExceptions: TypeAlias = list[type[Exception]] | None

_WIN.set_icon(ICON_IMG)

_SAVE: Final[Button] = Button(
    RectPos(0                  , 0              , "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Save"   , "CTRL+S"      , text_h=16
)
_SAVE_AS: Final[Button] = Button(
    RectPos(_SAVE.rect.right   , _SAVE.rect.y   , "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Save As", "CTRL+SHIFT+S", text_h=16
)
_OPEN: Final[Button] = Button(
    RectPos(_SAVE_AS.rect.right, _SAVE_AS.rect.y, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Open"   , "CTRL+O"      , text_h=16
)
_CLOSE: Final[Button] = Button(
    RectPos(_OPEN.rect.right   , _OPEN.rect.y   , "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Close"  , "CTRL+W"      , text_h=16
)

_GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center"),
    RectPos(WIN_INIT_W - 10, 10, "topright")
)

_BRUSH_DIMS: Final[CheckboxGrid] = CheckboxGrid(
    RectPos(10, _SAVE_AS.rect.bottom + 10, "topleft"),
    [get_brush_dim_checkbox_info(i) for i in range(1, 6)],
    5, False, False
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
    RectPos(WIN_INIT_W       - 10 , WIN_INIT_H - 10, "bottomright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Add Color", "CTRL+A"
)
_EDIT_GRID: Final[Button] = Button(
    RectPos(_ADD_COLOR.rect.x - 10, WIN_INIT_H - 10, "bottomright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Edit Grid", "CTRL+G"
)
# TODO: fix imgs resize
_OPEN_SETTINGS: Final[Button] = Button(
    RectPos(_GRID_MANAGER.grid.minimap_rect.x - 16, _GRID_MANAGER.grid.minimap_rect.y, "topright"),
    [SETTINGS_OFF_IMG, SETTINGS_ON_IMG], "", "(CTRL+COMMA)"
)

_PALETTE_MANAGER: Final[PaletteManager] = PaletteManager(
    RectPos(_ADD_COLOR.rect.centerx, _ADD_COLOR.rect.y - 25, "bottomright")
)
_TOOLS_MANAGER: Final[ToolsManager] = ToolsManager(
    RectPos(_BRUSH_DIMS.rect.x, WIN_INIT_H - 10, "bottomleft")
)

_FPS_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(WIN_INIT_W / 2), 0                          , "midtop"),
    "FPS: 0"
)
_FPS_TEXT_LABEL_OBJ_INFO: Final[ObjInfo] = ObjInfo(_FPS_TEXT_LABEL)
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
_STATES_MAIN_OBJS_INFO: Final[_StatesObjInfo] = (
    [
        ObjInfo(_SAVE), ObjInfo(_SAVE_AS), ObjInfo(_OPEN), ObjInfo(_CLOSE),
        ObjInfo(_GRID_MANAGER), ObjInfo(_BRUSH_DIMS), ObjInfo(_X_MIRROR), ObjInfo(_Y_MIRROR),
        ObjInfo(_ADD_COLOR), ObjInfo(_EDIT_GRID), ObjInfo(_OPEN_SETTINGS),
        ObjInfo(_PALETTE_MANAGER), ObjInfo(_TOOLS_MANAGER),
        _FPS_TEXT_LABEL_OBJ_INFO, ObjInfo(_FILE_TEXT_LABEL), ObjInfo(_UNSAVED_ICON),
    ],
    [ObjInfo(_COLOR_PICKER)],
    [ObjInfo(_GRID_UI     )],
    [],
    [ObjInfo(_SETTINGS_UI )],
)

_TIMEDUPDATE1000: Final[int] = pg.event.custom_type()
_CLOCK: Final[pg.Clock] = pg.Clock()

_FILE_DIALOG_SAVE_AS: Final[int]        = 0
_FILE_DIALOG_OPEN: Final[int]           = 1
_FILE_DIALOG_CRASH_SAVE_DIR: Final[int] = 2
_ASKED_FILES_QUEUE: Final[_AskedFilesQueue] = Queue()


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
    sections: list[str] = file_path.name.rsplit(".", 1)
    if len(sections) == 1:
        sections.append("png")
    elif sections[1] not in ("png", "bmp"):
        sections[1] = "png"

    file_path = file_path.parent / f"{sections[0]}.{sections[1]}"
    return str(file_path)


def _try_get_grid_img(file_str: str, ignored_exceptions: _IgnoredExceptions) -> pg.Surface | None:
    """
    Loads a grid image.

    Args:
        file string, ignored exceptions ([None] = all)
    Returns:
        image (can be None)
    """

    attempt_i: int
    should_retry: bool

    file_path: Path = Path(file_str)
    img: pg.Surface | None = None

    error_str: str = ""
    exception: type[Exception] | None = None
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            with file_path.open("rb") as f:
                try_lock_file(f, True)
                img = pg.image.load(f, file_path.name).convert_alpha()
            break
        except FileNotFoundError as e:
            error_str = "File missing."
            exception = type(e)
            break
        except PermissionError as e:
            error_str = "Permission denied."
            exception = type(e)
            break
        except LockException as e:
            error_str = "File locked."
            exception = type(e)
            break
        except FileException as e:
            error_str = e.error_str
            exception = type(e)
            break
        except pg.error as e:
            error_str = str(e)
            exception = type(e)
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


def _ask_save_to_file() -> None:
    """Asks a file to save to with tkinter."""

    file_str: str = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[
            ("png Files"   , "*.png"),
            ("Bitmap Files", "*.bmp"),
        ],
        title="Save As"
    )
    if not isinstance(file_str, str):  # On some explorers closing won't return an empty string
        file_str = ""

    _ASKED_FILES_QUEUE.put((file_str, _FILE_DIALOG_SAVE_AS))


def _ask_open_file() -> None:
    """Asks a file to open with tkinter."""

    file_str: str = filedialog.askopenfilename(
        defaultextension=".png",
        filetypes=[
            ("png Files"   , "*.png"),
            ("Bitmap Files", "*.bmp"),
        ],
        title="Open"
    )
    if not isinstance(file_str, str):  # On some explorers closing won't return an empty string
        file_str = ""

    _ASKED_FILES_QUEUE.put((file_str, _FILE_DIALOG_OPEN))


def _ask_crash_save_dir() -> None:
    """Asks a directory to save uncreated files to on crash with tkinter."""

    dir_str: str = filedialog.askdirectory(title="Choose Directory")
    if not isinstance(dir_str, str):  # On some explorers closing won't return an empty string
        dir_str = ""

    _ASKED_FILES_QUEUE.put((dir_str, _FILE_DIALOG_CRASH_SAVE_DIR))


class _Dixel:
    """Drawing program for pixel art."""

    __slots__ = (
        "_win_xy", "_win_wh", "_is_maximized", "_is_fullscreen",
        "_state_i", "_states_objs_info", "_state_active_objs",
        "_file_str", "_new_file_str", "_is_saved",
        "_is_asking_file_save_as", "_is_asking_file_open", "_is_asking_crash_save_dir",
    )

    def __init__(self) -> None:
        """Loads the data, handles argv and gets the full objects list."""

        obj: UIElement

        self._win_xy: XY = _WIN.position
        self._win_wh: WH = _WIN.size
        self._is_maximized: bool  = False
        self._is_fullscreen: bool = False

        self._state_i: int = _STATE_I_MAIN
        self._states_objs_info: list[list[ObjInfo]] = []
        self._state_active_objs: list[UIElement]    = []

        self._file_str: str     = ""
        self._new_file_str: str = ""
        self._is_saved: bool = False

        self._is_asking_file_save_as: bool   = False
        self._is_asking_file_open: bool      = False
        self._is_asking_crash_save_dir: bool = False

        self._load_data_from_file()

        grid_img: pg.Surface | None = None
        if len(argv) > 1:
            grid_img = self._handle_path_from_argv()
        elif self._file_str != "":
            grid_img = _try_get_grid_img(self._file_str, [FileNotFoundError])

        if grid_img is None:
            self._file_str = ""
            _GRID_MANAGER.grid.refresh_full()
        else:
            _GRID_MANAGER.grid.set_tiles(grid_img)
            _UNSAVED_ICON.set_radius(0)
            self._is_saved = True
        self._set_file_text_label()

        self._refresh_objs(False)
        state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
        self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]
        for obj in self._state_active_objs:
            obj.enter()

        _WIN.show()
        # It's better to modify the window after show
        if self._is_maximized:
            _WIN.maximize()
        if self._is_fullscreen:
            _WIN.set_fullscreen(True)
        _WIN.focus()

        pg.time.set_timer(_TIMEDUPDATE1000, 1_000)

    def _try_get_data(self) -> dict[str, Any] | None:
        """
        Gets the data from the data file.

        Returns:
            data (can be None)
        """

        attempt_i: int
        error_str: str
        should_retry: bool

        data: dict[str, Any] | None = None
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                data_path: Path = Path("assets", "data", "data.json")
                with data_path.open(encoding="utf-8", errors="replace") as f:
                    try_lock_file(f, True)
                    data = json.load(f)
                break
            except FileNotFoundError:
                break
            except PermissionError:
                messagebox.showerror("Data Load Failed", "Permission denied.")
                break
            except JSONDecodeError:
                messagebox.showerror("Data Load Failed", "Invalid json.")
                break
            except LockException:
                messagebox.showerror("Data Load Failed", "File locked.")
                break
            except FileException as e:
                messagebox.showerror("Data Load Failed", e.error_str)
                break
            except OSError as e:
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                messagebox.showerror("Data Load Failed", error_str)
                break

        return data

    def _try_get_palette_data(self) -> dict[str, Any] | None:
        """
        Gets the palette data from the palette data file.

        Returns:
            data (can be None)
        """

        attempt_i: int
        error_str: str
        should_retry: bool

        data: dict[str, Any] | None = None
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                data_path: Path = Path("assets", "data", "palette.json")
                with data_path.open(encoding="utf-8", errors="replace") as f:
                    try_lock_file(f, True)
                    data = json.load(f)
                break
            except FileNotFoundError:
                break
            except PermissionError:
                messagebox.showerror("Palette Data Load Failed", "Permission denied.")
                break
            except JSONDecodeError:
                messagebox.showerror("Palette Data Load Failed", "Invalid json.")
                break
            except LockException:
                messagebox.showerror("Palette Data Load Failed", "File locked.")
                break
            except FileException as e:
                messagebox.showerror("Palette Data Load Failed", e.error_str)
                break
            except OSError as e:
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                messagebox.showerror("Palette Data Load Failed", error_str)
                break

        return data

    def _load_data_from_file(self) -> None:
        """Loads the data from the data file."""

        data: dict[str, Any] | None = self._try_get_data()
        if data is not None:
            if data["file"] != "":
                self._file_str = _ensure_valid_img_format(data["file"])

            if data["brush_dim_i"] != _BRUSH_DIMS.clicked_i:
                _BRUSH_DIMS.check(data["brush_dim_i"])
            if data["tool_i"] != _TOOLS_MANAGER.tools_grid.clicked_i:
                _TOOLS_MANAGER.tools_grid.check(data["tool_i"])
                _TOOLS_MANAGER.refresh_tools(0)

            # refresh_full is called later
            _GRID_MANAGER.grid.set_info(
                np.zeros((data["grid_cols"], data["grid_rows"], 4), uint8),
                data["grid_visible_cols"], data["grid_visible_rows"],
                data["grid_offset_x"], data["grid_offset_y"],
                True,
            )
            _GRID_MANAGER.grid.brush_dim = _BRUSH_DIMS.clicked_i + 1

            if data["is_x_mirror_on"]:
                _X_MIRROR.img_i, _X_MIRROR.is_checked = 1, True
                _GRID_MANAGER.is_x_mirror_on = True
            if data["is_y_mirror_on"]:
                _Y_MIRROR.img_i, _Y_MIRROR.is_checked = 1, True
                _GRID_MANAGER.is_y_mirror_on = True

            if data["grid_ratio"] is not None:
                _GRID_UI.checkbox.img_i, _GRID_UI.checkbox.is_checked = 1, True
                _GRID_UI.w_ratio, _GRID_UI.h_ratio = data["grid_ratio"]

            # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
            _WIN.position = self._win_xy = data["win_xy"]
            _WIN.size     = self._win_wh = data["win_wh"]
            self._is_maximized           = data["is_maximized"]
            self._is_fullscreen          = data["is_fullscreen"]

            if data["is_fps_counter_active"] != _FPS_TEXT_LABEL_OBJ_INFO.is_active:
                _SETTINGS_UI.show_fps.img_i = int(data["is_fps_counter_active"])
                _SETTINGS_UI.show_fps.is_checked = data["is_fps_counter_active"]
                SETTINGS_EVENTS.append(FPS_TOGGLE)
            if data["fps_cap_drop-down_i"] != _SETTINGS_UI.fps_dropdown.option_i:
                _SETTINGS_UI.fps_dropdown.set_option_i(data["fps_cap_drop-down_i"])
            if data["crash_save_dir"] != _SETTINGS_UI.crash_save_dir_str:
                _SETTINGS_UI.crash_save_dir_str = data["crash_save_dir"]
                pretty_path_str: str = prettify_path_str(_SETTINGS_UI.crash_save_dir_str)
                _SETTINGS_UI.crash_save_dir_text_label.set_text(pretty_path_str)

        palette_data: dict[str, Any] | None = self._try_get_palette_data()
        if palette_data is not None:
            _PALETTE_MANAGER.set_info(
                palette_data["colors"], palette_data["color_i"], palette_data["offset_y"],
                palette_data["drop-down_i"],
            )

    def _parse_argv(self) -> list[str]:
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

    def _try_create_argv(self, flags: list[str]) -> pg.Surface | None:
        """
        Creates a file if --mk-file is in the flags and a directory if --mk-dir is in the flags.

        Args:
            flags
        Returns:
            grid image (can be None)
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

        grid_img: pg.Surface | None = None
        if should_create:
            grid_img = _GRID_MANAGER.grid.try_save_to_file(self._file_str, False)
        return grid_img

    def _handle_path_from_argv(self) -> pg.Surface:
        """
        Handles file opening with cmd args.

        Returns:
            grid image
        Raises:
            SystemExit
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
            raise SystemExit

        self._file_str = _ensure_valid_img_format(self._file_str)

        file_path: Path = Path(self._file_str)
        grid_img: pg.Surface | None = None
        for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
            try:
                with file_path.open("rb") as f:
                    try_lock_file(f, True)
                    grid_img = pg.image.load(f, file_path.name).convert_alpha()
                break
            except FileNotFoundError:
                grid_img = self._try_create_argv(flags)
                break
            except PermissionError:
                print(f"Image Load Failed.\n{file_path.name}\nPermission denied.")
                break
            except LockException:
                print(f"Image Load Failed.\n{file_path.name}\nFile Locked.")
                break
            except FileException as e:
                print(f"Image Load Failed.\n{file_path.name}\n{e.error_str}")
                break
            except pg.error as e:
                print(f"Image Load Failed.\n{file_path.name}\n{e}")
                break
            except OSError as e:
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** attempt_i)
                    continue

                print(f"Image Load Failed.\n{file_path.name}\n{error_str}")
                break

        if grid_img is None:
            raise SystemExit
        return grid_img

    def _set_file_text_label(self) -> None:
        """Sets the file text label with the first 25 chars of the path or with New File."""

        if self._file_str == "":
            _FILE_TEXT_LABEL.set_text("New File")
        else:
            _FILE_TEXT_LABEL.set_text(prettify_path_str(self._file_str))

        _UNSAVED_ICON.rect.x       = _FILE_TEXT_LABEL.rect.right + 5
        _UNSAVED_ICON.rect.centery = _FILE_TEXT_LABEL.rect.centery
        _UNSAVED_ICON.frame_rect.center = _UNSAVED_ICON.rect.center

    def _refresh_objs(self, should_refresh_only_current: bool = True) -> None:
        """
        Gets every object with an objs_info attribute from either the current or all states.

        Args:
            refresh only current state flag (default = False)
        """

        state_info: list[ObjInfo]
        info: ObjInfo

        if should_refresh_only_current:
            full_current_state_objs_info: list[ObjInfo] = _STATES_MAIN_OBJS_INFO[self._state_i]
            for info in full_current_state_objs_info:
                full_current_state_objs_info.extend(info.obj.objs_info)

            # Reverse to have sub objects before the main one
            # When resizing the main object can use their resized attributes
            full_current_state_objs_info.reverse()
            self._states_objs_info[self._state_i] = full_current_state_objs_info
        else:
            self._states_objs_info = []
            for state_info in _STATES_MAIN_OBJS_INFO:
                full_state_objs_info: list[ObjInfo] = state_info.copy()
                for info in full_state_objs_info:
                    full_state_objs_info.extend(info.obj.objs_info)

                # Reverse to have sub objects before the main one
                # When resizing the main object can use their resized attributes
                full_state_objs_info.reverse()
                self._states_objs_info.append(full_state_objs_info)

    def _draw(self) -> None:
        """Gets every blit_sequence attribute and draws it to the screen."""

        obj: UIElement

        blittable_objs: list[UIElement] = self._state_active_objs.copy()
        if self._state_i != _STATE_I_MAIN:
            home_objs_info: list[ObjInfo] = self._states_objs_info[_STATE_I_MAIN]
            blittable_objs.extend([info.obj for info in home_objs_info if info.is_active])

        main_sequence: list[BlitInfo] = []
        for obj in blittable_objs:
            main_sequence.extend(obj.blit_sequence)
        main_sequence.sort(key=lambda blit_info: blit_info[2])

        _WIN_SURF.fill(BLACK)
        _WIN_SURF.fblits([(img, rect) for img, rect, _layer in main_sequence], BLEND_ALPHA_SDL2)
        _WIN.flip()

    def _change_state(self, prev_state_active_objs: list[UIElement]) -> None:
        """
        Calls the leave method of every state active object, refreshes and resizes them.

        Args:
            previous state active objects
        """

        obj: UIElement

        for obj in prev_state_active_objs:
            obj.leave()

        for obj in self._state_active_objs:
            obj.enter()
        self._resize_objs()

    def _resize_objs(self) -> None:
        """Resizes every object of the main and current state with a resize method."""

        win_w: int
        win_h: int
        obj: UIElement

        state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
        resizable_objs: list[UIElement] = [info.obj for info in state_objs_info]
        if self._state_i != _STATE_I_MAIN:
            home_objs_info: list[ObjInfo] = self._states_objs_info[_STATE_I_MAIN]
            resizable_objs.extend(        [info.obj for info in home_objs_info])

        win_w, win_h = _WIN_SURF.get_size()
        win_w_ratio: float = win_w / WIN_INIT_W
        win_h_ratio: float = win_h / WIN_INIT_H
        for obj in resizable_objs:
            obj.resize(win_w_ratio, win_h_ratio)

        _UNSAVED_ICON.rect.x       = _FILE_TEXT_LABEL.rect.right + 5
        _UNSAVED_ICON.rect.centery = _FILE_TEXT_LABEL.rect.centery
        _UNSAVED_ICON.frame_rect.center = _UNSAVED_ICON.rect.center

        rec_move_rect(
            _OPEN_SETTINGS,
            _GRID_MANAGER.grid.minimap_rect.x - 16, _GRID_MANAGER.grid.minimap_rect.y,
            1, 1
        )

    def _handle_key_press(self, k: int) -> None:
        """
        Adds keys to the keyboard and checks for esc, F1 and F11.

        Args:
            key
        """

        if k == K_ESCAPE and self._state_i == _STATE_I_MAIN:
            raise KeyboardInterrupt

        # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
        if   k == K_F1:
            if self._is_fullscreen:
                _WIN.set_windowed()
            if self._is_maximized:
                _WIN.restore()

            self._is_maximized = self._is_fullscreen = False
            _WIN.position = self._win_xy
            _WIN.size = (WIN_INIT_W, WIN_INIT_H)
        elif k == K_F11:
            self._is_fullscreen = not self._is_fullscreen
            if self._is_fullscreen:
                _WIN.set_fullscreen(True)
            else:
                _WIN.set_windowed()

        KEYBOARD.add(k)

    def _refresh_unsaved_icon(self, unsaved_color: pg.Color) -> None:
        """
        Checks if the image is unsaved and refreshes the unsaved icon.

        Args:
            unsaved color
        """

        img: pg.Surface | None = _try_get_grid_img(self._file_str, None)
        if img is None:
            if self._is_saved:
                _UNSAVED_ICON.set_animation(ANIMATION_I_GROW,   pg.Color(255, 255, 0), False)
                self._is_saved = False
        elif np.array_equal(_GRID_MANAGER.grid.tiles, get_pixels(img)):
            if not self._is_saved:
                _UNSAVED_ICON.set_animation(ANIMATION_I_SHRINK, WHITE,                 True)
                self._is_saved = True
        elif self._is_saved:
                _UNSAVED_ICON.set_animation(ANIMATION_I_GROW,   unsaved_color,         False)
                self._is_saved = False

    def _handle_events(self) -> None:
        """Handles the events."""

        event: pg.Event

        did_restore: bool       = False
        did_maximize: bool      = False
        did_win_move: bool      = False
        did_win_change_wh: bool = False
        for event in pg.event.get():
            if event.type == WINDOWCLOSE:
                raise KeyboardInterrupt

            # Handled after everything is processed
            if   event.type == WINDOWRESTORED:
                did_restore       = True
            elif event.type == WINDOWMAXIMIZED:
                did_maximize      = True
            elif event.type == WINDOWMOVED:
                did_win_move      = True
            elif event.type == WINDOWSIZECHANGED:
                did_win_change_wh = True

            elif event.type == MOUSEWHEEL:
                MOUSE.scroll_amount = event.y
            elif event.type == KEYDOWN:
                self._handle_key_press(event.key)
            elif event.type == KEYUP:
                KEYBOARD.remove(event.key)
            elif event.type == KEYMAPCHANGED:
                KEYBOARD.clear()

            elif event.type == _TIMEDUPDATE1000:
                _FPS_TEXT_LABEL.set_text(f"FPS: {_CLOCK.get_fps():.2f}")
                if self._file_str != "":
                    self._refresh_unsaved_icon(pg.Color(255, 255, 0))

        if   did_restore:
            if self._is_fullscreen:
                self._is_maximized = False
        elif did_maximize:
                self._is_maximized = True

        if did_win_move and not (self._is_maximized or self._is_fullscreen):
                self._win_xy = _WIN.position
        if did_win_change_wh:
            if not (self._is_maximized or self._is_fullscreen):
                self._win_xy = _WIN.position
                self._win_wh = _WIN.size
            self._resize_objs()

    def _resize_with_keys(self) -> None:
        """Resizes the window with the keyboard."""

        win_w: int
        win_h: int

        win_w, win_h = self._win_wh
        if K_F5 in KEYBOARD.timed:
            win_w -= 1
        if K_F6 in KEYBOARD.timed:
            win_w += 1
        if K_F7 in KEYBOARD.timed:
            win_h -= 1
        if K_F8 in KEYBOARD.timed:
            win_h += 1

        if (win_w, win_h) != self._win_wh:
            # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
            _WIN.size = (win_w, win_h)

    def _save_palette(self) -> None:
        """Saves the palette to a separate file."""

        error_str: str
        should_retry: bool

        dropdown_i: int | None = (
            _PALETTE_MANAGER.dropdown_i if _PALETTE_MANAGER.is_dropdown_on else None
        )

        data: dict[str, Any] = {
            "color_i"    : _PALETTE_MANAGER.colors_grid.clicked_i,
            "offset_y"   : _PALETTE_MANAGER.colors_grid.offset_y,
            "drop-down_i": dropdown_i,
            "colors"     : _PALETTE_MANAGER.colors,
        }

        palette_path: Path = Path("assets", "data", "palette.json")
        palette_str: str = json.dumps(data, ensure_ascii=False, indent=4)

        dir_creation_attempt_i: int = FILE_ATTEMPT_START_I
        system_attempt_i: int       = FILE_ATTEMPT_START_I
        while (
            dir_creation_attempt_i <= FILE_ATTEMPT_STOP_I and
            system_attempt_i       <= FILE_ATTEMPT_STOP_I
        ):
            try:
                # If you open in write mode it will clear the file even if it's locked
                with palette_path.open("ab") as f:
                    try_lock_file(f, False)
                    f.truncate(0)
                    f.write(palette_str.encode("utf-8", "ignore"))
                break
            except FileNotFoundError:
                dir_creation_attempt_i += 1
                did_fail: bool = try_create_dir(palette_path.parent, False, dir_creation_attempt_i)
                if did_fail:
                    break
            except PermissionError:
                messagebox.showerror("Palette Save Failed", "Permission denied.")
                break
            except LockException:
                messagebox.showerror("Palette Save Failed", "File locked.")
                break
            except FileException as e:
                messagebox.showerror("Palette Save Failed", e.error_str)
                break
            except OSError as e:
                system_attempt_i += 1
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** system_attempt_i)
                    continue

                messagebox.showerror("Palette Save Failed", error_str)
                break

    def _save_to_file(self, should_ask_create_img_dir: bool) -> None:
        """
        Saves the data file, palette and image.

        Args:
            ask create image directory flag
        """

        error_str: str
        should_retry: bool

        tool_i: int = (
            _TOOLS_MANAGER.tools_grid.clicked_i if _TOOLS_MANAGER.saved_clicked_i is None else
            _TOOLS_MANAGER.saved_clicked_i
        )
        grid_ratio: tuple[float, float] | None = (
            (_GRID_UI.w_ratio, _GRID_UI.h_ratio) if _GRID_UI.checkbox.is_checked else None
        )

        data: dict[str, Any] = {
            "file": self._file_str,

            "grid_cols"        : _GRID_MANAGER.grid.area.w,
            "grid_rows"        : _GRID_MANAGER.grid.area.h,
            "grid_visible_cols": _GRID_MANAGER.grid.visible_area.w,
            "grid_visible_rows": _GRID_MANAGER.grid.visible_area.h,
            "grid_offset_x"    : _GRID_MANAGER.grid.offset.x,
            "grid_offset_y"    : _GRID_MANAGER.grid.offset.y,

            "is_x_mirror_on": _GRID_MANAGER.is_x_mirror_on,
            "is_y_mirror_on": _GRID_MANAGER.is_y_mirror_on,

            "brush_dim_i": _BRUSH_DIMS.clicked_i,
            "tool_i"     : tool_i,

            "grid_ratio": grid_ratio,

            "win_xy": self._win_xy,
            "win_wh": self._win_wh,
            "is_maximized":  self._is_maximized,
            "is_fullscreen": self._is_fullscreen,

            "is_fps_counter_active": _FPS_TEXT_LABEL_OBJ_INFO.is_active,
            "fps_cap_drop-down_i": _SETTINGS_UI.fps_dropdown.option_i,
            "crash_save_dir": _SETTINGS_UI.crash_save_dir_str,
        }

        data_path: Path = Path("assets", "data", "data.json")
        data_str:str = json.dumps(data, ensure_ascii=False, indent=4)

        dir_creation_attempt_i: int = FILE_ATTEMPT_START_I
        system_attempt_i: int       = FILE_ATTEMPT_START_I
        while (
            dir_creation_attempt_i <= FILE_ATTEMPT_STOP_I and
            system_attempt_i       <= FILE_ATTEMPT_STOP_I
        ):
            try:
                # If you open in write mode it will clear the file even if it's locked
                with data_path.open("ab") as f:
                    try_lock_file(f, False)
                    f.truncate(0)
                    f.write(data_str.encode("utf-8", "ignore"))
                break
            except FileNotFoundError:
                dir_creation_attempt_i += 1
                did_fail: bool = try_create_dir(data_path.parent, False, dir_creation_attempt_i)
                if did_fail:
                    break
            except PermissionError:
                messagebox.showerror("Data Save Failed", "Permission denied.")
                break
            except LockException:
                messagebox.showerror("Data Save Failed", "File locked.")
                break
            except FileException as e:
                messagebox.showerror("Data Save Failed", e.error_str)
                break
            except OSError as e:
                system_attempt_i += 1
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** system_attempt_i)
                    continue

                messagebox.showerror("Data Save Failed", error_str)
                break

        self._save_palette()

        grid_img: pg.Surface | None = _GRID_MANAGER.grid.try_save_to_file(
            self._file_str, should_ask_create_img_dir
        )
        if grid_img is None:
            _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, pg.Color(255, 0, 0), False)
            self._is_saved = False
        elif not self._is_saved:
            _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, pg.Color(0, 255, 0), True)
            self._is_saved = True

    def _handle_brush_dim_shortcuts(self) -> None:
        """Selects a brush dimension if the user presses ctrl+b+dimension."""

        num_shortcuts: int = min(len(_BRUSH_DIMS.checkboxes), 9)
        keys: list[int] = KEYBOARD.pressed
        brush_dims: CheckboxGrid = _BRUSH_DIMS
        grid: Grid = _GRID_MANAGER.grid

        for k in range(K_1, K_1 + num_shortcuts):
            if k in keys:
                brush_dims.clicked_i = k - K_1
                grid.brush_dim       = k - K_1 + 1

    def _upt_file_saving(self) -> None:
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
            self._save_to_file(True)

        is_save_as_clicked: bool = _SAVE_AS.upt()
        if (is_save_as_clicked or is_ctrl_shift_s_pressed) and not self._is_asking_file_save_as:
            Thread(target=_ask_save_to_file, daemon=True).start()
            self._is_asking_file_save_as = True

    def _upt_file_opening(self) -> None:
        """Updates the open file button."""

        is_open_clicked: bool = _OPEN.upt()
        is_ctrl_o_pressed: bool = KEYBOARD.is_ctrl_on and K_o in KEYBOARD.pressed
        if (is_open_clicked or is_ctrl_o_pressed) and not self._is_asking_file_open:
            Thread(target=_ask_open_file, daemon=True).start()
            self._is_asking_file_open = True

    def _upt_file_closing(self) -> None:
        """Updates the close file button."""

        is_close_clicked: bool = _CLOSE.upt()
        is_ctrl_w_pressed: bool = KEYBOARD.is_ctrl_on and K_w in KEYBOARD.pressed
        if (is_close_clicked or is_ctrl_w_pressed) and self._file_str != "":
            _GRID_MANAGER.grid.try_save_to_file(self._file_str, True)

            self._file_str = ""
            self._is_saved = False
            _GRID_MANAGER.grid.set_tiles(None)
            _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, WHITE, False)
            self._set_file_text_label()

    def _upt_ui_openers(self) -> None:
        """Updates the buttons that open UIs."""

        is_add_color_clicked: bool = _ADD_COLOR.upt()
        is_ctrl_a_pressed: bool = KEYBOARD.is_ctrl_on and K_a in KEYBOARD.pressed
        if is_add_color_clicked or is_ctrl_a_pressed:
            self._state_i = _STATE_I_COLOR
            _COLOR_PICKER.set_color(HEX_BLACK, True)

        is_edit_grid_clicked: bool = _EDIT_GRID.upt()
        is_ctrl_g_pressed: bool = KEYBOARD.is_ctrl_on and K_g in KEYBOARD.pressed
        if is_edit_grid_clicked or is_ctrl_g_pressed:
            self._state_i = _STATE_I_GRID
            _GRID_UI.set_info(_GRID_MANAGER.grid.area, _GRID_MANAGER.grid.tiles)

        is_open_settings_clicked: bool = _OPEN_SETTINGS.upt()
        is_ctrl_comma_pressed: bool = KEYBOARD.is_ctrl_on and K_COMMA in KEYBOARD.pressed
        if is_open_settings_clicked or is_ctrl_comma_pressed:
            self._state_i = _STATE_I_SETTINGS

    def _main_interface(self) -> None:
        """Handles the main interface."""

        hex_color: HexColor
        did_palette_change: bool
        hex_color_to_edit: HexColor | None

        if KEYBOARD.is_ctrl_on and K_b in KEYBOARD.pressed:
            self._handle_brush_dim_shortcuts()

        _BRUSH_DIMS.upt()
        did_brush_i_change: bool = _BRUSH_DIMS.refresh()
        if did_brush_i_change:
            _GRID_MANAGER.grid.brush_dim = _BRUSH_DIMS.clicked_i + 1

        is_shift_h_pressed: bool = KEYBOARD.is_shift_on and K_h in KEYBOARD.timed
        _X_MIRROR.upt(is_shift_h_pressed)
        _GRID_MANAGER.is_x_mirror_on = _X_MIRROR.is_checked

        is_shift_v_pressed: bool = KEYBOARD.is_shift_on and K_v in KEYBOARD.timed
        _Y_MIRROR.upt(is_shift_v_pressed)
        _GRID_MANAGER.is_y_mirror_on = _Y_MIRROR.is_checked

        hex_color, did_palette_change, hex_color_to_edit = _PALETTE_MANAGER.upt()
        if did_palette_change:
            # TODO?
            # Refreshes the hovered checkbox immediately
            self._refresh_objs()
            state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
            self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]
            MOUSE.refresh_hovered_obj(self._state_active_objs)

            # Hovered checkbox won't be clicked immediately if the drop-down menu moves
            prev_mouse_released: list[bool] = MOUSE.released
            MOUSE.released = [False, False, False, False, False]
            _PALETTE_MANAGER.colors_grid.upt_checkboxes()
            MOUSE.released = prev_mouse_released

        tool_info: ToolInfo = _TOOLS_MANAGER.upt()

        did_grid_change: bool = _GRID_MANAGER.upt(hex_color, tool_info)
        if did_grid_change and self._file_str != "":
            self._refresh_unsaved_icon(WHITE)
        if _GRID_MANAGER.eye_dropped_color is not None:
            should_refresh_objs: bool = _PALETTE_MANAGER.add(_GRID_MANAGER.eye_dropped_color)
            if should_refresh_objs:
                # Refreshing state_active_objects and hovered object is unnecessary
                self._refresh_objs()

        self._upt_file_saving()
        self._upt_file_opening()
        self._upt_file_closing()

        self._upt_ui_openers()
        if hex_color_to_edit is not None:
            self._state_i = _STATE_I_COLOR
            _COLOR_PICKER.set_color(hex_color_to_edit, True)

    def _color_ui(self) -> None:
        """Handles the color UI."""

        did_exit: bool
        did_confirm: bool
        rgb_color: RGBColor

        did_exit, did_confirm, rgb_color = _COLOR_PICKER.upt()
        if did_exit:
            _PALETTE_MANAGER.is_editing_color = False
            self._state_i = _STATE_I_MAIN
        elif did_confirm:
            self._state_i = _STATE_I_MAIN

            should_refresh_objs: bool = _PALETTE_MANAGER.add(rgb_color)
            if should_refresh_objs:
                # Refreshing state_active_objects and hovered object is unnecessary
                self._refresh_objs()

    def _grid_ui(self) -> None:
        """Handles the grid UI."""

        did_exit: bool
        did_confirm: bool
        tiles: NDArray[uint8]

        did_exit, did_confirm, tiles = _GRID_UI.upt()
        if did_exit:
            self._state_i = _STATE_I_MAIN
            self._new_file_str = ""
        elif did_confirm:
            if self._new_file_str != "":  # Save before setting info
                _GRID_MANAGER.grid.try_save_to_file(self._file_str, True)
                self._file_str = self._new_file_str
                self._new_file_str = ""
                self._set_file_text_label()

            should_reset_grid_history: bool = self._new_file_str != ""
            _GRID_MANAGER.grid.set_info(
                tiles,
                _GRID_MANAGER.grid.visible_area.w, _GRID_MANAGER.grid.visible_area.h,
                _GRID_MANAGER.grid.offset.x, _GRID_MANAGER.grid.offset.y,
                should_reset_grid_history,
            )
            _GRID_MANAGER.grid.refresh_full()
            if not should_reset_grid_history:
                _GRID_MANAGER.grid.add_to_history()

            if self._file_str != "":
                self._refresh_unsaved_icon(WHITE)

            self._state_i = _STATE_I_MAIN

    def _settings_ui(self) -> None:
        """Handles the settings UI."""

        did_exit: bool
        did_confirm: bool

        did_exit, did_confirm = _SETTINGS_UI.upt()
        if did_exit or did_confirm:
            self._state_i = _STATE_I_MAIN

    def _handle_settings_events(self) -> None:
        """Handles all the events in the SETTINGS_EVENTS queue."""

        event: int

        for event in SETTINGS_EVENTS:
            if   event == FPS_TOGGLE:
                _FPS_TEXT_LABEL_OBJ_INFO.rec_set_active(not _FPS_TEXT_LABEL_OBJ_INFO.is_active)
            elif event == CRASH_SAVE_DIR_CHANGE:
                Thread(target=_ask_crash_save_dir, daemon=True).start()
                self._is_asking_crash_save_dir = True

        SETTINGS_EVENTS.clear()

    def _finish_ask_save_to_file(self, file_str: str) -> None:
        """
        Saves the file after the user chooses it with tkinter.

        Args:
            file string
        """

        file_str = _ensure_valid_img_format(file_str)
        grid_img: pg.Surface | None = _GRID_MANAGER.grid.try_save_to_file(file_str, True)
        if grid_img is None:
                _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, pg.Color(255, 0, 0), False)
                self._is_saved = False
        else:
            self._file_str = file_str
            if not self._is_saved:
                _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, pg.Color(0, 255, 0), True)
                self._is_saved = True
            self._set_file_text_label()

    def _finish_ask_open_file(self, file_str: str) -> None:
        """
        Opens a file and loads it into the grid UI after the user chooses it with tkinter.

        Args:
            file string
        """

        file_str = _ensure_valid_img_format(file_str)
        new_file_img: pg.Surface | None = _try_get_grid_img(file_str, [])
        if new_file_img is None:
            self._new_file_str = ""
        else:
            if self._state_i == _STATE_I_GRID:
                self._change_state(self._state_active_objs)  # Refreshes

            self._new_file_str = file_str
            self._state_i = _STATE_I_GRID
            _GRID_UI.set_info(_GRID_MANAGER.grid.area, get_pixels(new_file_img))

    def _handle_asked_files_queue(self) -> None:
        """Processes every item in the asked files queue."""

        path_str: str
        dialog_type: int

        with suppress(queue.Empty):
            while True:
                path_str, dialog_type = _ASKED_FILES_QUEUE.get_nowait()

                if   dialog_type == _FILE_DIALOG_SAVE_AS:
                    if path_str != "":
                        self._finish_ask_save_to_file(path_str)
                    self._is_asking_file_save_as   = False
                elif dialog_type == _FILE_DIALOG_OPEN:
                    if path_str != "":
                        self._finish_ask_open_file(   path_str)
                    self._is_asking_file_open      = False
                elif dialog_type == _FILE_DIALOG_CRASH_SAVE_DIR:
                    if path_str != "":
                        _SETTINGS_UI.crash_save_dir_str = path_str
                        pretty_path_str: str = prettify_path_str(_SETTINGS_UI.crash_save_dir_str)
                        _SETTINGS_UI.crash_save_dir_text_label.set_text(pretty_path_str)
                    self._is_asking_crash_save_dir = False

    def _handle_states(self) -> None:
        """Handles updating and changing states."""

        prev_state_i: int = self._state_i
        prev_state_active_objs: list[Any] = self._state_active_objs  # Copying is unnecessary

        if   self._state_i == _STATE_I_MAIN:
            self._main_interface()
        elif self._state_i == _STATE_I_COLOR:
            self._color_ui()
        elif self._state_i == _STATE_I_GRID:
            self._grid_ui()
        elif self._state_i == _STATE_I_SETTINGS:
            self._settings_ui()

        state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
        self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]
        self._handle_settings_events()
        self._handle_asked_files_queue()

        if self._state_i != prev_state_i:
            self._change_state(prev_state_active_objs)

    def _handle_crash(self) -> None:
        """Saves before crashing."""

        if self._file_str == "":
            crash_save_dir_path: Path = Path(_SETTINGS_UI.crash_save_dir_str)
            file_path: Path = crash_save_dir_path / "new_file.png"
            duplicate_name_counter: int = 0
            while file_path.exists():
                duplicate_name_counter += 1
                file_path   = crash_save_dir_path / f"new_file_{duplicate_name_counter}.png"

            self._file_str = str(file_path)

        self._save_to_file(False)

    def run(self) -> None:
        """App loop."""

        MOUSE.prev_x, MOUSE.prev_y = pg.mouse.get_pos()
        try:
            while True:
                fps_cap: int = _SETTINGS_UI.fps_dropdown.values[_SETTINGS_UI.fps_dropdown.option_i]
                last_frame_elapsed_time: float = _CLOCK.tick(fps_cap)
                TIME.ticks = pg.time.get_ticks()
                TIME.delta = (last_frame_elapsed_time / 1_000) * 60

                state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
                self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]

                MOUSE.refresh_pos()
                MOUSE.pressed  = pg.mouse.get_pressed()
                MOUSE.released = list(pg.mouse.get_just_released())
                MOUSE.scroll_amount = 0
                MOUSE.refresh_hovered_obj(self._state_active_objs)
                MOUSE.refresh_type()

                KEYBOARD.released = []
                KEYBOARD.refresh_timed()

                self._handle_events()
                if KEYBOARD.timed != [] and not (self._is_maximized or self._is_fullscreen):
                    self._resize_with_keys()

                self._handle_states()

                _UNSAVED_ICON.animate()
                self._draw()

                MOUSE.prev_x, MOUSE.prev_y = MOUSE.x, MOUSE.y
        except KeyboardInterrupt:
            self._save_to_file(False)
        except Exception:
            self._handle_crash()

            raise


if __name__ == "__main__":
    _Dixel().run()
    print_funcs_profiles()
