"""
Drawing program for pixel art.

----------INFO----------
There are three states, the main interface and 2 extra UI windows,
they can be opened by clicking their respective buttons, they're for colors and grid.

Mouse info:
    Mouse info is contained in the class Mouse that tracks:
    x and y coordinates, pressed buttons, released ones (for clicking elements), scroll amount,
    hovered object and cursor type.

Keyboard input:
    There's a list for every currently pressed key, one for every released one and
    one that is empty and filled with the pressed keys for one frame every 150ms for key repeat,
    the normal key list is used to check shortcuts instantly.
    The Keyboard class contains these lists and the flags for control, shift, alt and numpad.

Objects info:
    Objects may have a objs_info attribute, a list of sub objects, stored in the dataclass ObjInfo,
    sub objects can also be inactive, the active flag can be changed with ObjInfo.set_active.
    Every object is in the states_objs attribute of the Dixel class,
    the attributes/methods below are automatically called.

Blitting:
    The blit_sequence attribute is a list with tuples of image, rect and layer,
    objects with an higher layer will be blitted on top of objects with a lower one.
    Every object must have a blit_sequence

    There are 4 layer types:
        background: background elements and grid
        element: UI elements that can be interacted with
        text: normal text labels
        top: elements that aren't always present like hovering text or a cursor in an input box

    Layers can also be extended into the special group,
    they will still keep their hierarchy so special top goes on top of special text and so on
    but every special layer goes on top of any normal one, used for stuff like drop-down menus.

    The UI group extends the special group in a similar way,
    used for the UI windows of other states.

Hovering info:
    The get_hovering method takes the mouse position and
    returns whatever the object is being hovered, only one object can be hovered at a time,
    if there's more than one it will be chosen the one with the highest layer.
    The layer attribute of an object must be called layer.

Cursor type:
    Objects may have a cursor type attribute, when they're hovered the cursor will be of that type.

Leaving a state:
    The leave method gets called when leaving the object's state or the object goes inactive,
    it clears the relevant data, like the selected tiles of the grid
    or the hovering flag of clickables that shows hovering text.

Window resizing:
    The resize method scales positions and images manually
    because blitting everything on an image, scaling it to match the window size and blitting it
    removes text anti-aliasing, causes 1 pixel offsets on some elements at specific sizes, is slow
    and doesn't allow for custom behavior on some objects
    pygame.SCALED doesn't scale position and images well.
    Only the objects of the main and current state are resized,
    when changing state the state's objects are immediately resized.

Interacting with elements:
    Interaction is possible with an upt method,
    it contains a high level implementation of it's behavior.

----------TODO----------
- better grid transition?
- split Dixel
- option to change the palette to match the current colors/multiple palettes
- UI to view grid history
- option to make drawing only affect the visible_area?
- way to close without auto saving?
- have multiple files open
- handle old data files
- UIs as separate windows?
- touch and pen support

- COLOR_PICKER:
    - hex_text as input box

- GRID_UI:
    - add option to flip sizes
    - separate minimap from grid and place minimap in grid UI
    - add option to change visible_area?
    - move image before resizing?

- TOOLS_MANAGER:
    - brush (different shapes?, smooth edges?)
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
from os import path
from pathlib import Path
from json import JSONDecodeError
from sys import argv
from contextlib import suppress
from typing import TypeAlias, Final, Optional, Any

import pygame as pg
from pygame.locals import *
import numpy as np
from numpy import uint8
from numpy.typing import NDArray

from src.classes.grid_manager import GridManager
from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Button
from src.classes.text_label import TextLabel
from src.classes.unsaved_icon import UnsavedIcon
from src.classes.devices import Mouse, Keyboard

from src.utils import (
    RectPos, ObjInfo, get_pixels, get_brush_dim_checkbox_info, try_create_dir, print_funcs_profiles
)
from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import XY, WH, RGBColor, HexColor, ToolInfo, BlitInfo
from src.consts import (
    BLACK, WHITE, HEX_BLACK, NUM_MAX_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY, BG_LAYER,
    TIME, ANIMATION_I_GROW, ANIMATION_I_SHRINK
)

_i: int
for _i in range(5):
    pg.init()
pg.key.stop_text_input()

_WIN_INIT_W: Final[int] = 1_250
_WIN_INIT_H: Final[int] = 900
# Window is focused before starting, so it doesn't appear when exiting early
_WIN: Final[pg.Window] = pg.Window(
    "Dixel", (_WIN_INIT_W, _WIN_INIT_H),
    hidden=True, resizable=True, allow_high_dpi=True
)
_WIN_SURF: Final[pg.Surface] = _WIN.get_surface()
_WIN.minimum_size = (900, 550)

# These files load images at the start which requires a window
from src.imgs import (
    ICON_IMG, BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG, BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG
)
from src.classes.grid_ui import GridUI
from src.classes.color_ui import ColorPicker
from src.classes.tools_manager import ToolsManager
from src.classes.palette_manager import PaletteManager

_StatesObjInfo: TypeAlias = tuple[list[ObjInfo], ...]
_AskedFilesQueue: TypeAlias = Queue[tuple[str, int]]
_ExceptionType: TypeAlias = type[Exception]

_WIN.set_icon(ICON_IMG)

_MOUSE: Final[Mouse] = Mouse()
_KEYBOARD: Final[Keyboard] = Keyboard()

_ADD_COLOR: Final[Button] = Button(
    RectPos(_WIN_INIT_W - 10, _WIN_INIT_H - 10, "bottomright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Add Color", "CTRL+A"
)
_EDIT_GRID: Final[Button] = Button(
    RectPos(_ADD_COLOR.rect.x - 10, _ADD_COLOR.rect.y, "topright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Edit Grid", "CTRL+G"
)

_SAVE: Final[Button] = Button(
    RectPos(0, 0, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Save", "CTRL+S", text_h=16
)
_SAVE_AS: Final[Button] = Button(
    RectPos(_SAVE.rect.right, _SAVE.rect.y, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Save As", "CTRL+SHIFT+S", text_h=16
)
_OPEN: Final[Button] = Button(
    RectPos(_SAVE_AS.rect.right, _SAVE_AS.rect.y, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Open", "CTRL+O", text_h=16
)
_CLOSE: Final[Button] = Button(
    RectPos(_OPEN.rect.right, _OPEN.rect.y, "topleft"),
    [BUTTON_XS_OFF_IMG, BUTTON_XS_ON_IMG], "Close", "CTRL+W", text_h=16
)

_GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(round(_WIN_INIT_W / 2), round(_WIN_INIT_H / 2), "center"),
    RectPos(_WIN_INIT_W - 10, 10, "topright")
)

_BRUSH_DIMS: Final[CheckboxGrid] = CheckboxGrid(
    RectPos(10, _SAVE_AS.rect.bottom + 10, "topleft"),
    [get_brush_dim_checkbox_info(i) for i in range(1, 6)],
    5, False, False
)

_PALETTE_MANAGER: Final[PaletteManager] = PaletteManager(
    RectPos(_ADD_COLOR.rect.centerx, _ADD_COLOR.rect.y - 25, "bottomright")
)
_TOOLS_MANAGER: Final[ToolsManager] = ToolsManager(
    RectPos(_BRUSH_DIMS.rect.x, _WIN_INIT_H - 10, "bottomleft")
)

_FPS_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(_WIN_INIT_W / 2), 0, "midtop"),
    "FPS: 0"
)
_FILE_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(_WIN_INIT_W / 2), _FPS_TEXT_LABEL.rect.bottom, "midtop"),
    ""
)
_UNSAVED_ICON: Final[UnsavedIcon] = UnsavedIcon()

_COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(round(_WIN_INIT_W / 2), round(_WIN_INIT_H / 2), "center")
)
_GRID_UI: Final[GridUI] = GridUI(
    RectPos(round(_WIN_INIT_W / 2), round(_WIN_INIT_H / 2), "center")
)

_STATE_I_MAIN: Final[int] = 0
_STATE_I_COLOR: Final[int] = 1
_STATE_I_GRID: Final[int] = 2
_MAIN_STATES_OBJS_INFO: Final[_StatesObjInfo] = (
    [
        ObjInfo(_ADD_COLOR), ObjInfo(_EDIT_GRID),
        ObjInfo(_SAVE), ObjInfo(_SAVE_AS), ObjInfo(_OPEN), ObjInfo(_CLOSE),
        ObjInfo(_GRID_MANAGER),
        ObjInfo(_BRUSH_DIMS), ObjInfo(_PALETTE_MANAGER), ObjInfo(_TOOLS_MANAGER),
        ObjInfo(_FPS_TEXT_LABEL), ObjInfo(_FILE_TEXT_LABEL),
        ObjInfo(_UNSAVED_ICON),
    ],
    [ObjInfo(_COLOR_PICKER)],
    [ObjInfo(_GRID_UI)],
)

_CLOCK: Final[pg.Clock] = pg.Clock()

_TIMEDUPDATE1000: Final[int] = pg.event.custom_type()
pg.time.set_timer(_TIMEDUPDATE1000, 1_000)

_FILE_DIALOG_SAVE_AS: Final[int] = 0
_FILE_DIALOG_OPEN: Final[int] = 1
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

    file_path: Path = Path(file_str).resolve().absolute()
    sections: list[str] = file_path.name.rsplit(".", 1)

    if  len(sections) == 1:
         sections.append("png")
    elif sections[-1] not in ("png", "bmp"):
         sections[-1] = "png"
    file_name: str = sections[0] + "." + sections[1]

    return str(file_path.parent / file_name)


def _try_get_grid_img(
        file_str: str, ignored_exceptions: list[Optional[_ExceptionType]]
) -> Optional[pg.Surface]:
    """
    Loads a grid image.

    Args:
        file string, ignored exceptions ([None] = all)
    Returns:
        image (can be None)
    """

    num_attempts: int

    file_path: Path = Path(file_str)
    img: Optional[pg.Surface] = None
    error_str: str = ""
    exception: Optional[_ExceptionType] = None
    for num_attempts in range(1, NUM_MAX_FILE_ATTEMPTS + 1):
        try:
            with file_path.open("rb") as f:
                try_lock_file(f, True)
                img = pg.image.load(f, file_path.name).convert_alpha()
            break
        except FileNotFoundError:
            error_str = "File missing."
            exception = FileNotFoundError
            break
        except PermissionError:
            error_str = "Permission denied."
            exception = PermissionError
            break
        except LockException:
            error_str = "File locked."
            exception = LockException
            break
        except FileException as e:
            error_str = e.error_str
            exception = FileException
            break
        except pg.error as e:
            error_str = str(e)
            exception = pg.error
            break
        except OSError as e:
            if num_attempts == NUM_MAX_FILE_ATTEMPTS:
                error_str = e.strerror
                exception = OSError
                break

            pg.time.wait(FILE_ATTEMPT_DELAY * num_attempts)

    if img is None and exception not in ignored_exceptions and ignored_exceptions != [None]:
        messagebox.showerror("Image Load Failed", f"{file_path.name}: {error_str}")
    return img


def _get_blit_info_layer(blit_info: BlitInfo) -> int:
    """
    Gets the layer from a blit info.

    Args:
        blit info
    Returns:
        layer
    """

    return blit_info[2]


def _ask_save_to_file() -> None:
    """Asks a file to save to with tkinter."""

    file_str: Any = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("png Files", "*.png"), ("Bitmap Files", "*.bmp")],
        title="Save As"
    )
    if not isinstance(file_str, str):  # On some explorers closing won't return an empty string
        file_str = ""

    _ASKED_FILES_QUEUE.put((file_str, _FILE_DIALOG_SAVE_AS))


def _ask_open_file() -> None:
    """Asks a file to open with tkinter."""

    file_str: Any = filedialog.askopenfilename(
        defaultextension=".png",
        filetypes=[("png Files", "*.png"), ("Bitmap Files", "*.bmp")],
        title="Open"
    )
    if not isinstance(file_str, str):  # On some explorers closing won't return an empty string
        file_str = ""

    _ASKED_FILES_QUEUE.put((file_str, _FILE_DIALOG_OPEN))


class Dixel:
    """Drawing program for pixel art."""

    __slots__ = (
        "_win_xy", "_win_wh", "_is_maximized", "_is_fullscreen", "_state_i", "_states_objs_info",
        "_state_active_objs", "_file_str", "_is_asking_file_save_as", "_is_asking_file_open",
        "_new_file_str", "_is_saved"
    )

    def __init__(self) -> None:
        """Loads the data, handles argv and gets the full objects list."""

        self._win_xy: XY = _WIN.position
        self._win_wh: WH = _WIN.size
        self._is_maximized: bool = False
        self._is_fullscreen: bool = False

        self._state_i: int = _STATE_I_MAIN
        self._states_objs_info: list[list[ObjInfo]] = []
        self._state_active_objs: list[Any] = []

        self._file_str: str = ""
        self._is_asking_file_save_as: bool = False
        self._is_asking_file_open: bool = False
        self._new_file_str: Optional[str] = None
        self._is_saved: bool = False

        self._load_data_from_file()

        grid_img: Optional[pg.Surface] = None
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

        self._refresh_objs()

        _WIN.show()
        # It's better to modify the window after show
        if self._is_maximized:
            _WIN.maximize()
        if self._is_fullscreen:
            _WIN.set_fullscreen(True)

    def _try_get_data(self) -> Optional[dict[str, Any]]:
        """
        Gets the data from the data file.

        Returns:
            data (can be None)
        """

        num_attempts: int

        data: Optional[dict[str, Any]] = None
        for num_attempts in range(1, NUM_MAX_FILE_ATTEMPTS + 1):
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
                if num_attempts == NUM_MAX_FILE_ATTEMPTS:
                    messagebox.showerror("Data Load Failed", e.strerror)
                    break

                pg.time.wait(FILE_ATTEMPT_DELAY * num_attempts)

        return data

    def _load_data_from_file(self) -> None:
        """Loads the data from the data file."""

        data: Optional[dict[str, Any]] = self._try_get_data()
        if data is not None:
            self._file_str = data["file"]
            if self._file_str != "":
                self._file_str = _ensure_valid_img_format(self._file_str)

            _BRUSH_DIMS.check(data["brush_dim_i"])
            _PALETTE_MANAGER.set_info(
                data["colors"], data["color_i"], data["color_offset"],
                data["palette_drop-down_i"]
            )
            _TOOLS_MANAGER.tools_grid.check(data["tool_i"])
            _TOOLS_MANAGER.refresh_tools(0)

            # refresh_full is called later
            _GRID_MANAGER.grid.set_info(
                np.zeros((data["grid_cols"], data["grid_rows"], 4), uint8),
                data["grid_visible_cols"], data["grid_visible_rows"],
                data["grid_offset_x"], data["grid_offset_y"],
                True
            )
            _GRID_MANAGER.grid.brush_dim = _BRUSH_DIMS.clicked_i + 1

            if data["grid_ratio"] is not None:
                _GRID_UI.checkbox.img_i = 1
                _GRID_UI.checkbox.is_checked = True
                _GRID_UI.w_ratio, _GRID_UI.h_ratio = data["grid_ratio"]

            # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
            _WIN.position = self._win_xy = data["win_xy"]
            _WIN.size = self._win_wh = data["win_wh"]
            self._is_maximized = data["is_maximized"]
            self._is_fullscreen = data["is_fullscreen"]

    def _refine_argv(self, flag: str) -> bool:
        """
        Ensures the file and flag are valid, displays the help message if the flag is help.

        Args:
            flag
        Returns:
            invalid argv flag
        """

        are_argv_invalid: bool = True
        if argv[1].lower() == "help" or flag not in ("", "--mk-file", "--mk-dir"):
            print(
                f"Usage: {argv[0]} <file path> <optional flag>\n"
                f"Example: {argv[0]} test (.png is default)\n"

                "FLAGS:\n"
                f"\t--mk-file: create file ({argv[0]} new_file --mk-file)\n"
                f"\t--mk-dir: create directory ({argv[0]} new_dir/new_file --mk-dir)"
            )

            self._file_str = ""
        else:
            self._file_str = _ensure_valid_img_format(argv[1])

            are_argv_invalid = (
                path.isreserved(self._file_str) if hasattr(path, "isreserved") else  # 3.13.0+
                Path(self._file_str).is_reserved()
            )
            if are_argv_invalid:
                print("Reserved path.")

        return are_argv_invalid

    def _try_create_argv(self, flag: str) -> Optional[pg.Surface]:
        """
        Creates a file if the flag is --mk-file and a directory if the flag is --mk-dir.

        Args:
            flag
        Returns:
            grid image (can be None)
        """

        file_path: Path = Path(self._file_str)
        should_create: bool = True
        if file_path.parent.is_dir():
            if flag != "--mk-file":
                print(
                    "The file doesn't exist, to create it add --mk-file.\n"
                    f'"{file_path}" --mk-file'
                )
                should_create = False
        elif   flag != "--mk-dir":
                print(
                    "The directory doesn't exist, to create it add --mk-dir.\n"
                    f'"{file_path}" --mk-dir'
                )
                should_create = False

        grid_img: Optional[pg.Surface] = None
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

        num_attempts: int

        flag: str = argv[2].lower() if len(argv) > 2 else ""
        are_argv_invalid: bool = self._refine_argv(flag)
        if are_argv_invalid:
            raise SystemExit

        file_path: Path = Path(self._file_str)
        grid_img: Optional[pg.Surface] = None
        for num_attempts in range(1, NUM_MAX_FILE_ATTEMPTS + 1):
            try:
                with file_path.open("rb") as f:
                    try_lock_file(f, True)
                    grid_img = pg.image.load(f, file_path.name).convert_alpha()
                break
            except FileNotFoundError:
                grid_img = self._try_create_argv(flag)
                break
            except PermissionError:
                messagebox.showerror("Image Load Failed", f"{file_path.name}\nPermission denied.")
                break
            except LockException:
                messagebox.showerror("Image Load Failed", f"{file_path.name}\nFile Locked.")
                break
            except FileException as e:
                messagebox.showerror("Image Load Failed", f"{file_path.name}\n{e.error_str}")
                break
            except pg.error as e:
                messagebox.showerror("Image Load Failed", f"{file_path.name}\n{e}")
                break
            except OSError as e:
                if num_attempts == NUM_MAX_FILE_ATTEMPTS:
                    messagebox.showerror("Image Load Failed", f"{file_path.name}\n{e}")
                    break

                pg.time.wait(FILE_ATTEMPT_DELAY * num_attempts)

        if grid_img is None:
            raise SystemExit
        return grid_img

    def _set_file_text_label(self) -> None:
        """Sets the file text label with the first 25 chars of the path or with New File."""

        if self._file_str == "":
            _FILE_TEXT_LABEL.set_text("New File")
        elif len(self._file_str) <= 25:
            _FILE_TEXT_LABEL.set_text(self._file_str)
        else:
            _FILE_TEXT_LABEL.set_text("..." + self._file_str[-25:])

        _UNSAVED_ICON.rect.midleft = _FILE_TEXT_LABEL.rect.right + 5, _FILE_TEXT_LABEL.rect.centery
        _UNSAVED_ICON.frame_rect.center = _UNSAVED_ICON.rect.center

    def _draw(self) -> None:
        """Gets every blit_sequence attribute and draws it to the screen."""

        obj: Any

        blittable_objs: list[Any] = self._state_active_objs.copy()
        if self._state_i != _STATE_I_MAIN:
            home_objs_info: list[ObjInfo] = self._states_objs_info[_STATE_I_MAIN]
            blittable_objs.extend([info.obj for info in home_objs_info if info.is_active])

        main_sequence: list[BlitInfo] = []
        for obj in blittable_objs:
            main_sequence.extend(obj.blit_sequence)
        main_sequence.sort(key=_get_blit_info_layer)

        _WIN_SURF.fill(BLACK)
        _WIN_SURF.fblits([(img, rect) for img, rect, _layer in main_sequence], BLEND_ALPHA_SDL2)
        _WIN.flip()

    def _refresh_objs(self) -> None:
        """Gets every object with an objs_info attribute and gets the active ones."""

        state_info: list[ObjInfo]
        info: ObjInfo

        self._states_objs_info = []
        for state_info in _MAIN_STATES_OBJS_INFO:
            full_state_objs_info: list[ObjInfo] = state_info.copy()
            for info in full_state_objs_info:
                if hasattr(info.obj, "objs_info"):
                    full_state_objs_info.extend(info.obj.objs_info)

            # Reverse to have sub objects before the main one
            # When resizing the main object can use their resized attributes
            full_state_objs_info.reverse()
            self._states_objs_info.append(full_state_objs_info)

        state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
        self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]

    def _change_state(self) -> None:
        """Calls the leave method of every state active object, refreshes and resizes them."""

        obj: Any

        for obj in self._state_active_objs:
            if hasattr(obj, "leave"):
                obj.leave()

        state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
        self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]
        self._resize_objs()

    def _resize_objs(self) -> None:
        """Resizes every object of the main and current state with a resize method."""

        win_w: int
        win_h: int
        obj: Any

        resizable_objs: list[Any] = [info.obj for info in self._states_objs_info[self._state_i]]
        if self._state_i != _STATE_I_MAIN:
            resizable_objs.extend([info.obj for info in self._states_objs_info[_STATE_I_MAIN]])

        win_w, win_h = _WIN_SURF.get_size()
        win_w_ratio: float = win_w / _WIN_INIT_W
        win_h_ratio: float = win_h / _WIN_INIT_H
        for obj in resizable_objs:
            if hasattr(obj, "resize"):
                obj.resize(win_w_ratio, win_h_ratio)

        _UNSAVED_ICON.rect.midleft = _FILE_TEXT_LABEL.rect.right + 5, _FILE_TEXT_LABEL.rect.centery
        _UNSAVED_ICON.frame_rect.center = _UNSAVED_ICON.rect.center

    def _handle_key_press(self, k: int) -> None:
        """
        Adds keys to the keyboard and checks for esc, F1 and F11.

        Args:
            key
        """

        if k == K_ESCAPE and self._state_i == _STATE_I_MAIN:
            raise KeyboardInterrupt

        # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
        if k == K_F1:
            self._is_maximized = self._is_fullscreen = False
            _WIN.set_windowed()
            _WIN.size = (_WIN_INIT_W, _WIN_INIT_H)
        elif k == K_F11:
            self._is_fullscreen = not self._is_fullscreen
            if self._is_fullscreen:
                _WIN.set_fullscreen(True)
            else:
                _WIN.set_windowed()

        _KEYBOARD.add(k)

    def _refresh_unsaved_icon(self, unsaved_color: pg.Color) -> None:
        """
        Checks if the image is unsaved and refreshes the unsaved icon.

        Args:
            unsaved color
        """

        img: Optional[pg.Surface] = _try_get_grid_img(self._file_str, [None])
        if img is None:
            if self._is_saved:
                _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, pg.Color(255, 255, 0), False)
                self._is_saved = False
        else:
            if np.array_equal(_GRID_MANAGER.grid.tiles, get_pixels(img)):
                if not self._is_saved:
                    _UNSAVED_ICON.set_animation(ANIMATION_I_SHRINK, WHITE, True)
                    self._is_saved = True
            elif self._is_saved:
                _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, unsaved_color, False)
                self._is_saved = False

    def _handle_events(self) -> None:
        """Handles the events."""

        event: pg.Event

        should_move: bool = False
        should_resize: bool = False
        for event in pg.event.get():
            if event.type == WINDOWCLOSE:
                raise KeyboardInterrupt

            if event.type == WINDOWMAXIMIZED:
                self._is_maximized = True
            elif event.type == WINDOWRESTORED:
                if not self._is_fullscreen:
                    self._is_maximized = False
            elif event.type == WINDOWMOVED:
                should_move = True  # Handle after is_maximized is refreshed
            elif event.type == WINDOWSIZECHANGED:
                should_resize = True  # Handle after is_maximized is refreshed

            elif event.type == MOUSEWHEEL:
                _MOUSE.scroll_amount = event.y
            elif event.type == KEYDOWN:
                self._handle_key_press(event.key)
            elif event.type == KEYUP:
                _KEYBOARD.remove(event.key)
            elif event.type == KEYMAPCHANGED:
                _KEYBOARD.clear()

            elif event.type == _TIMEDUPDATE1000:
                _FPS_TEXT_LABEL.set_text(f"FPS: {_CLOCK.get_fps():.2f}")
                if self._file_str != "":
                    self._refresh_unsaved_icon(pg.Color(255, 255, 0))

        if should_move and not (self._is_maximized or self._is_fullscreen):
            self._win_xy = _WIN.position
        if should_resize:
            if not (self._is_maximized or self._is_fullscreen):
                self._win_xy = _WIN.position
                self._win_wh = _WIN.size
            self._resize_objs()

    def _finish_ask_save_to_file(self, file_str: str) -> None:
        """
        Saves the file after the user chooses it with tkinter.

        Args:
            file string
        """

        file_str = _ensure_valid_img_format(file_str)
        grid_img: Optional[pg.Surface] = _GRID_MANAGER.grid.try_save_to_file(file_str, True)
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
        new_file_img: Optional[pg.Surface] = _try_get_grid_img(file_str, [])
        if new_file_img is None:
            self._new_file_str = None
        else:
            if self._state_i == _STATE_I_GRID:
                self._change_state()  # Refreshes

            self._new_file_str = file_str
            self._state_i = _STATE_I_GRID
            _GRID_UI.set_info(_GRID_MANAGER.grid.area, get_pixels(new_file_img))

    def _handle_asked_files_queue(self) -> None:
        """Processes every item in the asked files queue."""

        file_str: str
        dialog_type: int

        with suppress(queue.Empty):
            while True:
                file_str, dialog_type = _ASKED_FILES_QUEUE.get_nowait()

                if dialog_type == _FILE_DIALOG_SAVE_AS:
                    if file_str != "":
                        self._finish_ask_save_to_file(file_str)
                    self._is_asking_file_save_as = False
                elif dialog_type == _FILE_DIALOG_OPEN:
                    if file_str != "":
                        self._finish_ask_open_file(file_str)
                    self._is_asking_file_open = False

    def _resize_with_keys(self) -> None:
        """Resizes the window with the keyboard."""

        win_w: int
        win_h: int

        win_w, win_h = self._win_wh
        if K_F5 in _KEYBOARD.timed:
            win_w -= 1
        if K_F6 in _KEYBOARD.timed:
            win_w += 1
        if K_F7 in _KEYBOARD.timed:
            win_h -= 1
        if K_F8 in _KEYBOARD.timed:
            win_h += 1

        if (win_w, win_h) != self._win_wh:
            # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs is unnecessary
            _WIN.size = (win_w, win_h)

    def _save_to_file(self, should_ask_create_img_dir: bool) -> None:
        """
        Saves the data file and image.

        Args:
            ask create image directory flag
        """

        grid_ratio: tuple[float, float]
        grid_img: Optional[pg.Surface]

        is_dropdown_on: bool = _PALETTE_MANAGER.is_dropdown_on
        grid_ratio = (_GRID_UI.w_ratio, _GRID_UI.h_ratio) if _GRID_UI.checkbox.is_checked else None
        palette_dropdown_i: Optional[int] = _PALETTE_MANAGER.dropdown_i if is_dropdown_on else None

        data: dict[str, Any] = {
            "file": self._file_str,

            "grid_cols": _GRID_MANAGER.grid.area.w,
            "grid_rows": _GRID_MANAGER.grid.area.h,
            "grid_visible_cols": _GRID_MANAGER.grid.visible_area.w,
            "grid_visible_rows": _GRID_MANAGER.grid.visible_area.h,
            "grid_offset_x": _GRID_MANAGER.grid.offset.x,
            "grid_offset_y": _GRID_MANAGER.grid.offset.y,

            "brush_dim_i": _BRUSH_DIMS.clicked_i,
            "color_i": _PALETTE_MANAGER.colors_grid.clicked_i,
            "color_offset": _PALETTE_MANAGER.colors_grid.offset_y,
            "palette_drop-down_i": palette_dropdown_i,
            "tool_i": _TOOLS_MANAGER.tools_grid.clicked_i,

            "grid_ratio": grid_ratio,

            "win_xy": self._win_xy,
            "win_wh": self._win_wh,
            "is_maximized": self._is_maximized,
            "is_fullscreen": self._is_fullscreen,

            "colors": _PALETTE_MANAGER.colors  # TODO: save to other file
        }

        data_path: Path = Path("assets", "data", "data.json")
        json_bytes: bytes = json.dumps(
            data, ensure_ascii=False, indent=4
        ).encode("utf-8", "ignore")

        num_dir_creation_attempts: int = 0
        num_system_attempts: int = 0
        while True:
            try:
                # If you open in write mode it will clear the file even if it's locked
                with data_path.open("ab") as f:
                    try_lock_file(f, False)
                    f.truncate(0)
                    f.write(json_bytes)
                break
            except FileNotFoundError:
                num_dir_creation_attempts += 1
                did_fail: bool = try_create_dir(data_path.parent, False, num_dir_creation_attempts)
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
                num_system_attempts += 1
                if num_system_attempts == NUM_MAX_FILE_ATTEMPTS:
                    messagebox.showerror("Data Save Failed", e.strerror)
                    break

                pg.time.wait(FILE_ATTEMPT_DELAY * num_system_attempts)

        grid_img = _GRID_MANAGER.grid.try_save_to_file(self._file_str, should_ask_create_img_dir)
        if grid_img is None:
            _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, pg.Color(255, 0, 0), False)
            self._is_saved = False
        elif not self._is_saved:
            _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, pg.Color(0, 255, 0), True)
            self._is_saved = True

    def _upt_ui_openers(self) -> None:
        """Updates the buttons that open UIs."""

        is_add_color_clicked: bool = _ADD_COLOR.upt(_MOUSE)
        is_ctrl_a_pressed: bool = _KEYBOARD.is_ctrl_on and K_a in _KEYBOARD.pressed
        if is_add_color_clicked or is_ctrl_a_pressed:
            self._state_i = _STATE_I_COLOR
            _COLOR_PICKER.set_color(HEX_BLACK, True)

        is_edit_grid_clicked: bool = _EDIT_GRID.upt(_MOUSE)
        is_ctrl_g_pressed: bool = _KEYBOARD.is_ctrl_on and K_g in _KEYBOARD.pressed
        if is_edit_grid_clicked or is_ctrl_g_pressed:
            self._state_i = _STATE_I_GRID
            _GRID_UI.set_info(_GRID_MANAGER.grid.area, _GRID_MANAGER.grid.tiles)

    def _upt_file_saving(self) -> None:
        """Updates the save and save as button."""

        is_ctrl_s_pressed: bool = False
        is_ctrl_shift_s_pressed: bool = False
        if _KEYBOARD.is_ctrl_on and K_s in _KEYBOARD.pressed:
            if _KEYBOARD.is_shift_on:
                is_ctrl_shift_s_pressed = True
            else:
                is_ctrl_s_pressed = True

        is_save_clicked: bool = _SAVE.upt(_MOUSE)
        if is_save_clicked or is_ctrl_s_pressed:
            self._save_to_file(True)

        is_save_as_clicked: bool = _SAVE_AS.upt(_MOUSE)
        if (is_save_as_clicked or is_ctrl_shift_s_pressed) and not self._is_asking_file_save_as:
            Thread(target=_ask_save_to_file, daemon=True).start()
            self._is_asking_file_save_as = True

    def _upt_file_opening(self) -> None:
        """Updates the open file button."""

        is_open_clicked: bool = _OPEN.upt(_MOUSE)
        is_ctrl_o_pressed: bool = _KEYBOARD.is_ctrl_on and K_o in _KEYBOARD.pressed
        if (is_open_clicked or is_ctrl_o_pressed) and not self._is_asking_file_open:
            Thread(target=_ask_open_file, daemon=True).start()
            self._is_asking_file_open = True

    def _upt_file_closing(self) -> None:
        """Updates the close file button."""

        is_close_clicked: bool = _CLOSE.upt(_MOUSE)
        is_ctrl_w_pressed: bool = _KEYBOARD.is_ctrl_on and K_w in _KEYBOARD.pressed
        if (is_close_clicked or is_ctrl_w_pressed) and self._file_str != "":
            _GRID_MANAGER.grid.try_save_to_file(self._file_str, True)

            self._file_str = ""
            self._is_saved = False
            _GRID_MANAGER.grid.set_tiles(None)
            _UNSAVED_ICON.set_animation(ANIMATION_I_GROW, WHITE, False)
            self._set_file_text_label()

    def _main_interface(self) -> None:
        """Handles the main interface."""

        k: int
        hex_color: HexColor
        did_palette_change: bool
        hex_color_to_edit: Optional[HexColor]

        if _KEYBOARD.is_ctrl_on:  # Independent shortcuts
            max_brush_dim_ctrl_shortcut: int = min(len(_BRUSH_DIMS.checkboxes), 9)
            for k in range(K_1, K_1 + max_brush_dim_ctrl_shortcut):
                if k in _KEYBOARD.pressed:
                    _BRUSH_DIMS.clicked_i = k - K_1
                    _GRID_MANAGER.grid.brush_dim = _BRUSH_DIMS.clicked_i + 1

        _BRUSH_DIMS.upt(_MOUSE, _KEYBOARD)
        did_brush_i_change: bool = _BRUSH_DIMS.refresh()
        if did_brush_i_change:
            _GRID_MANAGER.grid.brush_dim = _BRUSH_DIMS.clicked_i + 1

        hex_color, did_palette_change, hex_color_to_edit = _PALETTE_MANAGER.upt(_MOUSE, _KEYBOARD)
        if did_palette_change: 
            # Refreshes the hovered checkbox immediately
            self._refresh_objs()
            _MOUSE.refresh_hovered_obj(self._state_active_objs)

            # Hovered checkbox won't be clicked immediately if the drop-down menu moves
            blank_mouse: Mouse = Mouse()
            blank_mouse.hovered_obj = _MOUSE.hovered_obj
            _PALETTE_MANAGER.colors_grid.upt_checkboxes(blank_mouse)

        tool_info: ToolInfo = _TOOLS_MANAGER.upt(_MOUSE, _KEYBOARD)

        did_grid_change: bool = _GRID_MANAGER.upt(_MOUSE, _KEYBOARD, hex_color, tool_info)
        if did_grid_change and self._file_str != "":
            self._refresh_unsaved_icon(WHITE)
        if _GRID_MANAGER.eye_dropped_color is not None:
            should_refresh_objs: bool = _PALETTE_MANAGER.add(_GRID_MANAGER.eye_dropped_color)
            if should_refresh_objs:
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

        did_exit, did_confirm, rgb_color = _COLOR_PICKER.upt(_MOUSE, _KEYBOARD)
        if did_exit:
            _PALETTE_MANAGER.is_editing_color = False
            self._state_i = _STATE_I_MAIN
        elif did_confirm:
            should_refresh_objs: bool = _PALETTE_MANAGER.add(rgb_color)
            if should_refresh_objs:
                self._refresh_objs()

            self._state_i = _STATE_I_MAIN

    def _grid_ui(self) -> None:
        """Handles the grid UI."""

        did_exit: bool
        did_confirm: bool
        tiles: NDArray[uint8]

        did_exit, did_confirm, tiles = _GRID_UI.upt(_MOUSE, _KEYBOARD)
        if did_exit:
            self._state_i = _STATE_I_MAIN
            self._new_file_str = None
        elif did_confirm:
            if self._new_file_str is not None:  # Save before setting info
                _GRID_MANAGER.grid.try_save_to_file(self._file_str, True)
                self._file_str = self._new_file_str
                self._new_file_str = None
                self._set_file_text_label()

            should_reset_grid_history: bool = self._new_file_str is not None
            _GRID_MANAGER.grid.set_info(
                tiles,
                _GRID_MANAGER.grid.visible_area.w, _GRID_MANAGER.grid.visible_area.h,
                _GRID_MANAGER.grid.offset.x, _GRID_MANAGER.grid.offset.y,
                should_reset_grid_history
            )
            _GRID_MANAGER.grid.refresh_full()
            if not should_reset_grid_history:
                _GRID_MANAGER.grid.add_to_history()

            if self._file_str != "":
                self._refresh_unsaved_icon(WHITE)

            self._state_i = _STATE_I_MAIN

    def _handle_states(self) -> None:
        """Handles updating and changing states."""

        prev_state_i: int = self._state_i
        if self._state_i == _STATE_I_MAIN:
            self._main_interface()
        elif self._state_i == _STATE_I_COLOR:
            self._color_ui()
        elif self._state_i == _STATE_I_GRID:
            self._grid_ui()

        self._handle_asked_files_queue()
        if self._state_i != prev_state_i:
            self._change_state()

    def _handle_crash(self) -> None:
        """Saves before crashing."""

        if self._file_str == "":
            file_path: Path = Path("new_file.png")
            duplicate_name_counter: int = 0
            while file_path.exists():
                duplicate_name_counter += 1
                file_path = Path(f"new_file_{duplicate_name_counter}.png")
            self._file_str = str(file_path.absolute())

        self._save_to_file(False)

    def run(self) -> None:
        """App loop."""

        _WIN.focus()
        _MOUSE.prev_x, _MOUSE.prev_y = pg.mouse.get_pos()
        try:
            while True:
                last_frame_elapsed_time: float = _CLOCK.tick(60)
                TIME.ticks = pg.time.get_ticks()
                TIME.delta = last_frame_elapsed_time / 1_000 * 60

                _MOUSE.hovered_obj = None
                _MOUSE.scroll_amount = 0
                _KEYBOARD.released = []

                self._handle_events()
                state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
                self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]

                _MOUSE.x, _MOUSE.y = pg.mouse.get_pos()
                if not pg.mouse.get_focused():
                    if _MOUSE.x == 0:
                        _MOUSE.x = -1
                    if _MOUSE.y == 0:
                        _MOUSE.y = -1
                _MOUSE.pressed = pg.mouse.get_pressed()
                _MOUSE.released = list(pg.mouse.get_just_released())
                _MOUSE.refresh_hovered_obj(self._state_active_objs)
                _MOUSE.refresh_type()

                _KEYBOARD.refresh_timed()

                if _KEYBOARD.timed != [] and not (self._is_maximized or self._is_fullscreen):
                    self._resize_with_keys()
                self._handle_states()

                _UNSAVED_ICON.animate()
                self._draw()

                _MOUSE.prev_x, _MOUSE.prev_y = _MOUSE.x, _MOUSE.y
        except KeyboardInterrupt:
            self._save_to_file(False)
        except Exception:
            self._handle_crash()

            raise


if __name__ == "__main__":
    Dixel().run()
    print_funcs_profiles()
