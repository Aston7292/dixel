"""
Drawing program for pixel art.

----------INFO----------
There are three states, the main interface and 2 extra UI windows
that can be opened by clicking their respective button, they're for colors and grid.

Mouse info:
    Mouse info is contained in the dataclass Mouse that tracks:
    x and y coordinates, pressed buttons, released ones (for clicking elements), scroll amount
    and hovered object.

Keyboard input:
    Every key that's currently pressed is in a list, accidental spamming is prevented
    by having another empty list and filling it with the pressed keys for one frame every 150ms,
    the normal key list is used to check shortcuts instantly.
    The Keyboard dataclass contains these lists and the flags for control, shift, alt and numpad.

Objects info:
    Objects may have a objs_info attribute, a list of sub objects, stored in the dataclass ObjInfo,
    Objects can also be inactive, the active flag can be changed through ObjInfo.set_active.
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
    but every special layer goes on top of any normal one,
    used for stuff like drop-down menus that appear on right click.

    The UI group extends the special group in a similar way,
    used for the UI windows of other states.

Hovering info:
    The get_hovering method takes the mouse position and
    returns whatever the object is being hovered, only one object can be hovered at a time,
    if there's more than one it will be chose the one with the highest layer.
    The layer of an object must be called layer.

Cursor type:
    Objects may have a cursor type attribute, when they're hovered the cursor will be of that type.

Entering a state:
    The enter method gets called when entering the object's state or when the object goes active,
    it initializes all the relevant data.

Leaving a state:
    The leave method gets called when leaving the object's state or the object goes inactive,
    it clears all the relevant data, like the selected tiles of the grid
    or the hovering flag of clickables that shows hovering text.

Window resizing:
    The resize method scales positions and images manually because
    blitting everything on an image, scaling it to match the window size and blitting it
    removes text anti-aliasing, causes 1 pixel offsets on some elements at specific sizes, is slow
    and doesn't allow for custom behavior on some objects
    pygame.SCALED doesn't scale position and images well.
    Only the objects of the main and current state are resized,
    when changing state the state's objects are immediately resized.

Interacting with elements:
    Interaction is possible with an upt method,
    it contains a high level implementation of it's behavior.

----------TODO----------
- mouse.set_pos on wayland
- better grid transition?
- split Dixel
- support more file types
- fix resized arrows
- hovering text appears when standing still (more stuff with hovering text)
- option to change the palette to match the current colors/multiple palettes
- CTRL Z/Y (UI to view history)
- Save window info
- option to make drawing only affect the visible_area?
- way to close without auto saving?
- have multiple files open
- handle old data files
- UIs as separate windows?
- touch and pen support

- COLOR_PICKER:
    - hex_text as input box

- GRID_UI:
    - add option to resize in order to fit image
    - add option to flip sizes
    - separate minimap from grid and place minimap in grid UI
    - add option to change visible_area?
    - move image before resizing?

- TOOLS_MANAGER:
    - brush (different shapes?, smooth edges?)
    - fill (change all tiles of the same color to the one in use)
    - pick color
    - draw line (pixelated?)
    - draw rectangle (auto fill)
    - draw circle, semi circle and ellipse (auto fill, pixelated?)
    - copy and paste (flip and rotate?)
    - move, flip or rotate section (affects all grid)
    - change brightness of tile/area
    - scale section

optimizations:
    - profile
    - GRID_MANAGER.grid.upt_section for large selected_tiles
    - better memory usage in PaletteManager
"""

import queue
import json
import sys

from tkinter import filedialog, messagebox
from threading import Thread
from queue import Queue
from os import path
from pathlib import Path
from json import JSONDecodeError
from contextlib import suppress
from typing import TypeAlias, Final, Optional, Any

import pygame as pg
from pygame.locals import *
import numpy as np
from numpy.typing import NDArray

from src.classes.grid_manager import GridManager
from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Button
from src.classes.text_label import TextLabel

from src.utils import (
    RectPos, Size, ObjInfo, Mouse, Keyboard, get_pixels, get_brush_dim_img, try_create_dir,
    resize_obj, print_funcs_profiles
)
from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import XY, WH, RGBColor, HexColor, CheckboxInfo, ToolInfo, LayeredBlitInfo
from src.consts import (
    CHR_LIMIT, BLACK, WHITE, HEX_BLACK, NUM_MAX_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY, BG_LAYER
)

for _i in range(5):
    pg.init()
pg.key.stop_text_input()

WIN_INIT_W: Final[int] = 1_200
WIN_INIT_H: Final[int] = 900
# Window is focused before starting, so it doesn't appear when exiting early
WIN: Final[pg.Window] = pg.Window(
    "Dixel", (WIN_INIT_W, WIN_INIT_H),
    hidden=True, resizable=True, allow_high_dpi=True
)
WIN_SURF: Final[pg.Surface] = WIN.get_surface()
WIN.minimum_size = (WIN_INIT_W, WIN_INIT_H)

# These files load images at the start which requires a window
from src.imgs import ICON_IMG, BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG, BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG
from src.classes.grid_ui import GridUI
from src.classes.color_ui import ColorPicker
from src.classes.tools_manager import ToolsManager
from src.classes.palette_manager import PaletteManager

NumPadMap: TypeAlias = dict[int, tuple[int, int]]
StatesObjInfo: TypeAlias = tuple[list[ObjInfo], ...]
AskedFilesQueue: TypeAlias = Queue[tuple[str, int]]
ExceptionType = type[Exception]

WIN.set_icon(ICON_IMG)
NUMPAD_MAP: Final[NumPadMap] = {
    K_KP_0: (K_INSERT, K_0),
    K_KP_1: (K_END, K_1),
    K_KP_2: (K_DOWN, K_2),
    K_KP_3: (K_PAGEDOWN, K_3),
    K_KP_4: (K_LEFT, K_4),
    K_KP_5: (0, K_5),
    K_KP_6: (K_RIGHT, K_6),
    K_KP_7: (K_HOME, K_7),
    K_KP_8: (K_UP, K_8),
    K_KP_9: (K_PAGEUP, K_9),
    K_KP_PERIOD: (K_DELETE, K_PERIOD)
}
MOUSE: Final[Mouse] = Mouse(-1, -1, (False,) * 3, (False,) * 5, 0, None)
KEYBOARD: Final[Keyboard] = Keyboard([], [], False, False, False, False)

ADD_COLOR: Final[Button] = Button(
    RectPos(WIN_INIT_W - 10, WIN_INIT_H - 10, "bottomright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Add Color", "CTRL+A"
)
EDIT_GRID: Final[Button] = Button(
    RectPos(ADD_COLOR.rect.x - 10, ADD_COLOR.rect.y, "topright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Edit Grid", "CTRL+G"
)

SAVE: Final[Button] = Button(
    RectPos(0, 0, "topleft"),
    [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Save", "CTRL+S", text_h=16
)
SAVE_AS: Final[Button] = Button(
    RectPos(SAVE.rect.right, SAVE.rect.y, "topleft"),
    [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Save As", "CTRL+SHIFT+S", text_h=16
)
OPEN: Final[Button] = Button(
    RectPos(SAVE_AS.rect.right, SAVE_AS.rect.y, "topleft"),
    [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Open", "CTRL+O", text_h=16
)
CLOSE: Final[Button] = Button(
    RectPos(OPEN.rect.right, OPEN.rect.y, "topleft"),
    [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Close", "CTRL+Q", text_h=16
)

GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center"),
    RectPos(WIN_INIT_W - 10, 10, "topright")
)

brush_dims_info: list[CheckboxInfo] = [
    (get_brush_dim_img(i), f"{i}px\nCTRL+{i}") for i in range(1, 6)
]
BRUSH_DIMS: Final[CheckboxGrid] = CheckboxGrid(
    RectPos(10, SAVE_AS.rect.bottom + 10, "topleft"),
    brush_dims_info, len(brush_dims_info), False, False
)

PALETTE_MANAGER: Final[PaletteManager] = PaletteManager(
    RectPos(ADD_COLOR.rect.centerx, ADD_COLOR.rect.y - 25, "bottomright")
)
TOOLS_MANAGER: Final[ToolsManager] = ToolsManager(
    RectPos(BRUSH_DIMS.rect.x, WIN_INIT_H - 10, "bottomleft")
)

FPS_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(WIN_INIT_W / 2), 0, "midtop"),
    "FPS: 0"
)
FILE_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(WIN_INIT_W / 2), FPS_TEXT_LABEL.rect.bottom, "midtop"),
    ""
)

COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center")
)
GRID_UI: Final[GridUI] = GridUI(
    RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center")
)

STATE_I_MAIN: Final[int] = 0
STATE_I_COLOR: Final[int] = 1
STATE_I_GRID: Final[int] = 2
MAIN_STATES_OBJS_INFO: Final[StatesObjInfo] = (
    [
        ObjInfo(ADD_COLOR), ObjInfo(EDIT_GRID),
        ObjInfo(SAVE), ObjInfo(SAVE_AS), ObjInfo(OPEN), ObjInfo(CLOSE),
        ObjInfo(GRID_MANAGER),
        ObjInfo(BRUSH_DIMS), ObjInfo(PALETTE_MANAGER), ObjInfo(TOOLS_MANAGER),
        ObjInfo(FPS_TEXT_LABEL), ObjInfo(FILE_TEXT_LABEL)
    ],
    [ObjInfo(COLOR_PICKER)],
    [ObjInfo(GRID_UI)]
)

CLOCK: Final[pg.Clock] = pg.Clock()

TIMEDUPDATE1000: Final[int] = pg.event.custom_type()
pg.time.set_timer(TIMEDUPDATE1000, 1_000)

DATA_PATH: Final[Path] = Path("assets", "data", "data.json")
FILE_DIALOG_SAVE_AS: Final[int] = 0
FILE_DIALOG_OPEN: Final[int] = 1
ASKED_FILES_QUEUE: Final[AskedFilesQueue] = Queue()


def _ensure_valid_img_format(file_str: str) -> str:
    """
    Changes the extensions of a path if it's not a supported format.

    Path.with_suffix() doesn't always produce the intended result,
    for example Path(".txt").with_suffix(".png") is Path(".txt.png"),
    it also raises ValueError on empty names.

    Args:
        file string
    Returns:
        file string
    """

    file_path: Path = Path(file_str).resolve().absolute()
    sections: list[str] = file_path.name.rsplit(".", 1)

    if len(sections) == 1:
        sections.append("png")
    elif sections[-1] not in ("png", "bmp"):
        sections[-1] = "png"
    file_name: str = sections[0] + "." + sections[1]

    return str(file_path.parent / file_name)


def _try_get_grid_img(
        file_str: str, ignored_exceptions: list[Optional[ExceptionType]]
) -> Optional[pg.Surface]:
    """
    Loads the grid image.

    Args:
        file string, ignored exceptions ([None] = all)
    Returns:
        image (can be None)
    """

    num_attempts: int

    img: Optional[pg.Surface] = None
    error_str: str = ""
    exception: Optional[ExceptionType] = None
    file_path: Path = Path(file_str)
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
                error_str = str(e)
                exception = OSError
                break

            pg.time.wait(FILE_ATTEMPT_DELAY * num_attempts)

    if img is None and exception not in ignored_exceptions and ignored_exceptions is not None:
        messagebox.showerror("Image Load Failed", f"{file_path.name}: {error_str}")
    return img


def _get_blit_info_layer(blit_info: LayeredBlitInfo) -> int:
    """
    Gets the layer from a layered blit info.

    Args:
        blit info
    Returns:
        layer
    """

    return blit_info[2]


def _ask_save_to_file() -> None:
    """Asks a file to save with tkinter."""

    file_str: Any = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("Png Files", "*.png"), ("Bitmap Files", "*.bmp")],
        title="Save As"
    )
    if not isinstance(file_str, str):  # On some explorers closing won't return an empty string
        file_str = ""

    ASKED_FILES_QUEUE.put((file_str, FILE_DIALOG_SAVE_AS))


def _ask_open_file() -> None:
    """Asks a file to open with tkinter."""

    file_str: Any = filedialog.askopenfilename(
        defaultextension=".png",
        filetypes=[("Png Files", "*.png"), ("Bitmap Files", "*.bmp")],
        title="Open"
    )
    if not isinstance(file_str, str):  # On some explorers closing won't return an empty string
        file_str = ""

    ASKED_FILES_QUEUE.put((file_str, FILE_DIALOG_OPEN))


class Dixel:
    """Drawing program for pixel art."""

    __slots__ = (
        "_is_fullscreen", "_cursor_type", "_timed_keys_interval", "_prev_timed_keys_update",
        "_alt_k", "_state_i", "_states_objs_info", "_state_active_objs", "_file_str",
        "_is_unsaved", "_is_asking_file_save_as", "_is_asking_file_open", "_new_file_str",
        "_new_file_img", "_unsaved_icon_img", "_unsaved_icon_rect", "_unsaved_icon_blit_info"
    )

    def __init__(self) -> None:
        """Initializes the window."""

        self._unsaved_icon_blit_info: LayeredBlitInfo

        self._is_fullscreen: bool = False

        self._cursor_type: int = SYSTEM_CURSOR_ARROW
        self._timed_keys_interval: int = 150
        self._prev_timed_keys_update: int = -self._timed_keys_interval
        self._alt_k: str = ""

        self._state_i: int = STATE_I_MAIN
        self._states_objs_info: list[list[ObjInfo]] = []
        self._state_active_objs: list[Any] = []

        self._file_str: str = ""
        self._is_unsaved: bool = True
        self._is_asking_file_save_as: bool = False
        self._is_asking_file_open: bool = False
        self._new_file_str: str = ""
        self._new_file_img: Optional[pg.Surface] = None

        self._unsaved_icon_img: pg.Surface = pg.Surface((16, 16)).convert()
        self._unsaved_icon_rect: pg.Rect = pg.Rect(0, 0, *self._unsaved_icon_img.get_size())
        # Decrease radius to make sure it's not cut off
        unsaved_icon_radius: float = min(self._unsaved_icon_rect.size) // 2 - 1
        pg.draw.aacircle(
            self._unsaved_icon_img, WHITE, self._unsaved_icon_rect.center, unsaved_icon_radius
        )
        self._unsaved_icon_blit_info = (self._unsaved_icon_img, self._unsaved_icon_rect, BG_LAYER)

        self._load_data_from_file()

        grid_img: Optional[pg.Surface] = None
        if len(sys.argv) > 1:
            grid_img = self._handle_path_from_argv()
        elif self._file_str != "":
            grid_img = _try_get_grid_img(self._file_str, [FileNotFoundError])

        if grid_img is None:
            self._file_str = ""
            GRID_MANAGER.grid.refresh_full()
        else:
            self._is_unsaved = False
            GRID_MANAGER.grid.set_tiles(grid_img)
        # Calls GRID_MANAGER.grid.refresh_grid_img so it must be called after grid.set_tiles
        GRID_MANAGER.grid.set_selected_tile_dim(BRUSH_DIMS.clicked_i + 1)

        self._set_file_text_label()
        self._refresh_objs()

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
                with DATA_PATH.open(encoding="utf-8", errors="replace") as f:
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
                    messagebox.showerror("Data Load Failed", str(e))
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

            BRUSH_DIMS.check(data["brush_dim_i"])
            PALETTE_MANAGER.set_info(
                data["colors"], data["color_i"], data["color_offset"],
                data["dropdown_i"]
            )
            TOOLS_MANAGER.tools_grid.check(data["tool_i"])
            TOOLS_MANAGER.refresh_tools(0)

            # GRID_MANAGER.grid.set_tiles is called later
            GRID_MANAGER.grid.set_info(
                Size(data["grid_cols"], data["grid_rows"]),
                data["grid_vis_cols"], data["grid_vis_rows"],
                data["grid_offset_x"], data["grid_offset_y"]
            )

            if data["grid_w_ratio"] is not None and data["grid_h_ratio"] is not None:
                GRID_UI.checkbox.img_i = 1
                GRID_UI.checkbox.is_checked = True
                GRID_UI.w_ratio, GRID_UI.h_ratio = data["grid_w_ratio"], data["grid_h_ratio"]

    def _check_argv(self) -> tuple[str, bool]:
        """
        Checks info from cmd arguments.

        Returns:
            flag, invalid argv flag
        """

        flag: str = sys.argv[2].lower() if len(sys.argv) > 2 else ""
        are_argv_invalid: bool = True
        if sys.argv[1].lower() == "help" or flag not in ("", "--mk-file", "--mk-dir"):
            program_name: str = sys.argv[0]
            print(
                f"Usage: {program_name} <file path> <optional flag>\n"
                f"Example: {program_name} test (.png is default)\n"
                "FLAGS:\n"
                f"\t--mk-file: create file ({program_name} new_file --mk-file)\n"
                f"\t--mk-dir: create directory ({program_name} new_dir/new_file --mk-dir)"
            )

            self._file_str = ""
        else:
            self._file_str = _ensure_valid_img_format(sys.argv[1])
            if hasattr(path, "isreserved"):  # 3.13.0+
                are_argv_invalid = path.isreserved(self._file_str)
            else:
                are_argv_invalid = Path(self._file_str).is_reserved()

            if are_argv_invalid:
                print("Reserved path.")

        return flag, are_argv_invalid

    def _try_create_argv(self, flag: str) -> Optional[pg.Surface]:
        """
        Creates a file if the flag is --mk-file and a directory if the flag is --mk-dir.

        Args:
            flag
        Returns:
            grid image (can be None)
        """

        file_path: Path = Path(self._file_str)
        did_succeed: bool = True
        if file_path.parent.is_dir():
            if flag != "--mk-file":
                print(
                    "The file doesn't exist, to create it add --mk-file.\n"
                    f'"{file_path}" --mk-file'
                )
                did_succeed = False
        elif flag != "--mk-dir":
            print(
                "The directory doesn't exist, to create it add --mk-dir.\n"
                f'"{file_path}" --mk-dir'
            )
            did_succeed = False

        grid_img: Optional[pg.Surface] = None
        if did_succeed:
            grid_img = GRID_MANAGER.grid.try_save_to_file(self._file_str, False)

        return grid_img

    def _handle_path_from_argv(self) -> pg.Surface:
        """
        Handles file opening with cmd args.

        Returns:
            grid image
        Raises:
            SystemExit
        """

        flag: str
        are_argv_invalid: bool
        num_attempts: int

        flag, are_argv_invalid = self._check_argv()
        if are_argv_invalid:
            raise SystemExit

        grid_img: Optional[pg.Surface] = None
        file_path: Path = Path(self._file_str)
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
            FILE_TEXT_LABEL.set_text("New File")
        elif len(self._file_str) <= 25:
            FILE_TEXT_LABEL.set_text(self._file_str)
        else:
            file_text = "..." + self._file_str[-25:]
            FILE_TEXT_LABEL.set_text(file_text)

        self._unsaved_icon_rect.midleft = (
            FILE_TEXT_LABEL.rect.right + 5, FILE_TEXT_LABEL.rect.centery
        )

    def _draw(self) -> None:
        """Gets every blit_sequence attribute and draws it to the screen."""

        obj: Any

        blittable_objs: list[Any] = self._state_active_objs.copy()
        if self._state_i != STATE_I_MAIN:
            home_objs_info: list[ObjInfo] = self._states_objs_info[STATE_I_MAIN]
            blittable_objs.extend([info.obj for info in home_objs_info if info.is_active])

        main_sequence: list[LayeredBlitInfo] = []
        if self._is_unsaved:
            main_sequence.append(self._unsaved_icon_blit_info)

        for obj in blittable_objs:
            main_sequence.extend(obj.blit_sequence)
        main_sequence.sort(key=_get_blit_info_layer)

        WIN_SURF.fill(BLACK)
        WIN_SURF.fblits([(img, rect) for img, rect, _layer in main_sequence])
        WIN.flip()

    def _refresh_objs(self) -> None:
        """Refreshes the objects info and state active objects using their objs_info attribute."""

        state_info: list[ObjInfo]
        info: ObjInfo

        self._states_objs_info = []
        for state_info in MAIN_STATES_OBJS_INFO:
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

    def _refresh_hovered_obj(self) -> None:
        """Refreshes the hovered object using their get_hovering method."""

        obj: Any

        MOUSE.hovered_obj = None
        max_layer: int = BG_LAYER
        mouse_xy: XY = (MOUSE.x, MOUSE.y)
        for obj in self._state_active_objs:
            can_get_hovering: bool = hasattr(obj, "get_hovering")
            if can_get_hovering and obj.get_hovering(mouse_xy) and obj.layer >= max_layer:
                MOUSE.hovered_obj = obj
                max_layer = obj.layer

    def _set_cursor_type(self) -> None:
        """Sets the cursor type using the cursor_type attribute of the hovered object."""

        prev_cursor_type: int = self._cursor_type
        has_type: bool = hasattr(MOUSE.hovered_obj, "cursor_type")
        self._cursor_type = MOUSE.hovered_obj.cursor_type if has_type else SYSTEM_CURSOR_ARROW

        if self._cursor_type != prev_cursor_type:
            pg.mouse.set_cursor(self._cursor_type)

    def _change_state(self) -> None:
        """Calls the leave and enter method of every object with them and resizes the objects."""

        obj: Any

        for obj in self._state_active_objs:
            if hasattr(obj, "leave"):
                obj.leave()

        state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
        self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]

        for obj in self._state_active_objs:
            if hasattr(obj, "enter"):
                obj.enter()

        self._resize_objs()
        pg.mouse.set_cursor(SYSTEM_CURSOR_ARROW)

    def _resize_objs(self) -> None:
        """Resizes every object of the main and current state with a resize method."""

        win_w: int
        win_h: int
        obj: Any
        _xy: XY
        wh: WH

        resizable_objs: list[Any] = [info.obj for info in self._states_objs_info[self._state_i]]
        if self._state_i != STATE_I_MAIN:
            resizable_objs.extend([info.obj for info in self._states_objs_info[STATE_I_MAIN]])

        win_w, win_h = WIN_SURF.get_size()
        win_w_ratio: float = win_w / WIN_INIT_W
        win_h_ratio: float = win_h / WIN_INIT_H
        for obj in resizable_objs:
            if hasattr(obj, "resize"):
                obj.resize(win_w_ratio, win_h_ratio)

        _xy, wh = resize_obj(RectPos(0, 0, ""), 16, 16, win_w_ratio, win_h_ratio)
        self._unsaved_icon_img = pg.Surface(wh).convert()
        self._unsaved_icon_rect.size = wh
        self._unsaved_icon_rect.midleft = (
            FILE_TEXT_LABEL.rect.right + 5, FILE_TEXT_LABEL.rect.centery
        )

        unsaved_icon_center: XY = (self._unsaved_icon_rect.w // 2, self._unsaved_icon_rect.h // 2)
        # Decrease radius to make sure it's not cut off
        unsaved_icon_radius: int = min(self._unsaved_icon_rect.size) // 2 - 1
        pg.draw.aacircle(self._unsaved_icon_img, WHITE, unsaved_icon_center, unsaved_icon_radius)
        self._unsaved_icon_blit_info = (self._unsaved_icon_img, self._unsaved_icon_rect, BG_LAYER)

    def _add_to_keys(self, k: int) -> None:
        """
        Adds a key to the pressed_keys if it's not using alt.

        Args:
            key
        """

        if k in NUMPAD_MAP:
            numpad_map_i: int = int(KEYBOARD.is_numpad_on)
            k = NUMPAD_MAP[k][numpad_map_i]

        if KEYBOARD.is_alt_on and (K_0 <= k <= K_9):
            self._alt_k += chr(k)
            if int(self._alt_k) > CHR_LIMIT:
                self._alt_k = self._alt_k[-1]

            self._alt_k = self._alt_k.lstrip("0")
        else:
            KEYBOARD.pressed.append(k)

    def _handle_key_press(self, k: int) -> None:
        """
        Handles key presses.

        Args:
            key
        """

        if k == K_ESCAPE and self._state_i == STATE_I_MAIN:
            raise KeyboardInterrupt

        # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs isn't necessary
        if k == K_F1:
            self._is_fullscreen = False
            WIN.size = WIN.minimum_size
            WIN.set_windowed()
        elif k == K_F11:
            self._is_fullscreen = not self._is_fullscreen
            if self._is_fullscreen:
                WIN.set_fullscreen(True)
            else:
                WIN.set_windowed()

        KEYBOARD.is_ctrl_on = pg.key.get_mods() & KMOD_CTRL != 0
        KEYBOARD.is_shift_on = pg.key.get_mods() & KMOD_SHIFT != 0
        KEYBOARD.is_alt_on = pg.key.get_mods() & KMOD_ALT != 0
        KEYBOARD.is_numpad_on = pg.key.get_mods() & KMOD_NUM != 0
        self._add_to_keys(k)

        self._timed_keys_interval = 150
        self._prev_timed_keys_update = -self._timed_keys_interval

    def _handle_key_release(self, k: int) -> None:
        """
        Handles key releases.

        Args:
            key
        """

        KEYBOARD.is_ctrl_on = pg.key.get_mods() & KMOD_CTRL != 0
        KEYBOARD.is_shift_on = pg.key.get_mods() & KMOD_SHIFT != 0
        KEYBOARD.is_alt_on = pg.key.get_mods() & KMOD_ALT != 0
        KEYBOARD.is_numpad_on = pg.key.get_mods() & KMOD_NUM != 0
        if k in KEYBOARD.pressed:
            KEYBOARD.pressed.remove(k)

        self._timed_keys_interval = 150

    def _refresh_is_unsaved(self) -> None:
        """Checks if the image is unsaved."""

        img: Optional[pg.Surface] = _try_get_grid_img(self._file_str, [None])
        if img is None:
            self._is_unsaved = True
        else:
            tiles: NDArray[np.uint8] = get_pixels(img)
            self._is_unsaved = not np.array_equal(GRID_MANAGER.grid.tiles, tiles)

    def _handle_events(self) -> None:
        """Handles events."""

        event: pg.Event

        for event in pg.event.get():
            if event.type == WINDOWCLOSE:
                raise KeyboardInterrupt

            if event.type == WINDOWSIZECHANGED:
                self._resize_objs()

            elif event.type == MOUSEWHEEL:
                MOUSE.scroll_amount = event.y
            elif event.type == KEYDOWN:
                self._handle_key_press(event.key)
            elif event.type == KEYUP:
                self._handle_key_release(event.key)
            elif event.type == KEYMAPCHANGED:
                KEYBOARD.pressed = KEYBOARD.timed = []
                KEYBOARD.is_ctrl_on = pg.key.get_mods() & KMOD_CTRL != 0
                KEYBOARD.is_shift_on = pg.key.get_mods() & KMOD_SHIFT != 0
                KEYBOARD.is_alt_on = pg.key.get_mods() & KMOD_ALT != 0
                KEYBOARD.is_numpad_on = pg.key.get_mods() & KMOD_NUM != 0

            elif event.type == TIMEDUPDATE1000:
                FPS_TEXT_LABEL.set_text(f"FPS: {CLOCK.get_fps():.2f}")
                if self._file_str != "":
                    self._refresh_is_unsaved()

    def _finish_ask_save_to_file(self, file_str: str) -> None:
        """
        Saves the file after the user chooses it with tkinter.

        Args:
            file string
        """

        file_str = _ensure_valid_img_format(file_str)
        grid_img: Optional[pg.Surface] = GRID_MANAGER.grid.try_save_to_file(file_str, True)
        if grid_img is not None:
            self._file_str = file_str
            self._is_unsaved = False
            self._set_file_text_label()

    def _finish_ask_open_file(self, file_str: str) -> None:
        """
        Opens a file and loads it into the grid UI after the user chooses it with tkinter.

        Args:
            file string
        """

        file_str = _ensure_valid_img_format(file_str)
        self._new_file_img = _try_get_grid_img(file_str, [])
        if self._new_file_img is not None:
            if self._state_i == STATE_I_GRID:
                self._change_state()  # Refreshes

            self._new_file_str = file_str
            self._state_i = STATE_I_GRID
            img_pixels: NDArray[np.uint8] = get_pixels(self._new_file_img)
            GRID_UI.set_info(GRID_MANAGER.grid.area, img_pixels)

    def _handle_asked_files_queue(self) -> None:
        """Processes every item in the asked files queue."""

        file_str: str
        dialog_type: int

        with suppress(queue.Empty):
            while True:
                file_str, dialog_type = ASKED_FILES_QUEUE.get_nowait()

                if dialog_type == FILE_DIALOG_SAVE_AS:
                    if file_str != "":
                        self._finish_ask_save_to_file(file_str)
                    self._is_asking_file_save_as = False
                elif dialog_type == FILE_DIALOG_OPEN:
                    if file_str != "":
                        self._finish_ask_open_file(file_str)
                    self._is_asking_file_open = False

    def _refresh_timed_keys(self) -> None:
        """Refreshes the timed keys once every 150ms and adds the alt key if present."""

        KEYBOARD.timed = []
        if (
            KEYBOARD.pressed != [] and
            pg.time.get_ticks() - self._prev_timed_keys_update >= self._timed_keys_interval
        ):
            numpad_map_i: int = int(KEYBOARD.is_numpad_on)
            KEYBOARD.timed = [
                NUMPAD_MAP[k][numpad_map_i] if k in NUMPAD_MAP else k
                for k in KEYBOARD.pressed
            ]

            self._timed_keys_interval = max(self._timed_keys_interval - 7, 50)
            self._prev_timed_keys_update = pg.time.get_ticks()

        if self._alt_k != "" and not KEYBOARD.is_alt_on:
            KEYBOARD.timed.append(int(self._alt_k))
            self._alt_k = ""

    def _resize_with_keys(self) -> None:
        """Resizes the window trough keys."""

        win_w: int
        win_h: int

        win_w, win_h = WIN_SURF.get_size()
        timed_keys: list[int] = KEYBOARD.timed
        if K_F5 in timed_keys:
            win_w -= 1
        if K_F6 in timed_keys:
            win_w += 1
        if K_F7 in timed_keys:
            win_h -= 1
        if K_F8 in timed_keys:
            win_h += 1

        if win_w != WIN_SURF.get_width() or win_h != WIN_SURF.get_height():
            # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs isn't necessary
            WIN.size = (win_w, win_h)

    def _save_to_file(self, should_ask_create_img_dir: bool) -> None:
        """
        Saves the file.

        Args:
            ask create image directory flag
        """

        palette_dropdown_i: Optional[int]
        grid_img: Optional[pg.Surface]

        grid_w_ratio: Optional[float] = GRID_UI.w_ratio if GRID_UI.checkbox.is_checked else None
        grid_h_ratio: Optional[float] = GRID_UI.h_ratio if GRID_UI.checkbox.is_checked else None
        palette_dropdown_i = PALETTE_MANAGER.dropdown_i if PALETTE_MANAGER.is_dropdown_on else None

        data: dict[str, Any] = {
            "file": self._file_str,
            "grid_cols": GRID_MANAGER.grid.area.w,
            "grid_rows": GRID_MANAGER.grid.area.h,
            "grid_vis_cols": GRID_MANAGER.grid.visible_area.w,
            "grid_vis_rows": GRID_MANAGER.grid.visible_area.h,
            "grid_offset_x": GRID_MANAGER.grid.offset.x,
            "grid_offset_y": GRID_MANAGER.grid.offset.y,
            "brush_dim_i": BRUSH_DIMS.clicked_i,
            "color_i": PALETTE_MANAGER.colors_grid.clicked_i,
            "color_offset": PALETTE_MANAGER.colors_grid.offset_y,
            "dropdown_i": palette_dropdown_i,
            "tool_i": TOOLS_MANAGER.tools_grid.clicked_i,
            "grid_w_ratio": grid_w_ratio,
            "grid_h_ratio": grid_h_ratio,
            "colors": PALETTE_MANAGER.colors
        }

        json_data: str = json.dumps(data, ensure_ascii=False, indent=4)
        json_bytes: bytes = json_data.encode("utf-8")
        num_dir_creation_attempts: int = 0
        num_system_attempts: int = 0
        while True:
            try:
                # If you open in write mode it will empty the file even if it's locked
                with DATA_PATH.open("ab") as f:
                    try_lock_file(f, False)
                    f.truncate(0)
                    f.write(json_bytes)
                break
            except FileNotFoundError:
                num_dir_creation_attempts += 1
                did_fail: bool = try_create_dir(DATA_PATH.parent, False, num_dir_creation_attempts)
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
                    messagebox.showerror("Data Save Failed", str(e))
                    break

                pg.time.wait(FILE_ATTEMPT_DELAY * num_system_attempts)

        grid_img = GRID_MANAGER.grid.try_save_to_file(self._file_str, should_ask_create_img_dir)
        if grid_img is not None:
            self._is_unsaved = False

    def _upt_ui_openers(self) -> None:
        """Updates the buttons that open UIs."""

        keyboard: Keyboard = KEYBOARD

        is_add_color_clicked: bool = ADD_COLOR.upt(MOUSE)
        is_ctrl_a_pressed: bool = keyboard.is_ctrl_on and K_a in keyboard.pressed
        if is_add_color_clicked or is_ctrl_a_pressed:
            self._state_i = STATE_I_COLOR
            COLOR_PICKER.set_color(HEX_BLACK, True)

        is_edit_grid_clicked: bool = EDIT_GRID.upt(MOUSE)
        is_ctrl_g_pressed: bool = keyboard.is_ctrl_on and K_g in keyboard.pressed
        if is_edit_grid_clicked or is_ctrl_g_pressed:
            self._state_i = STATE_I_GRID
            GRID_UI.set_info(GRID_MANAGER.grid.area, GRID_MANAGER.grid.tiles)

    def _upt_file_saving(self) -> None:
        """Updates the save as button."""

        is_ctrl_s_pressed: bool = False
        is_ctrl_shift_s_pressed: bool = False
        if KEYBOARD.is_ctrl_on and K_s in KEYBOARD.pressed:
            if KEYBOARD.is_shift_on:
                is_ctrl_shift_s_pressed = True
            else:
                is_ctrl_s_pressed = True

        is_save_clicked: bool = SAVE.upt(MOUSE)
        if is_save_clicked or is_ctrl_s_pressed:
            self._save_to_file(True)

        is_save_as_clicked: bool = SAVE_AS.upt(MOUSE)
        if (is_save_as_clicked or is_ctrl_shift_s_pressed) and not self._is_asking_file_save_as:
            self._is_asking_file_save_as = True
            Thread(target=_ask_save_to_file, daemon=True).start()

    def _upt_file_opening(self) -> None:
        """Updates the open file button."""

        is_open_clicked: bool = OPEN.upt(MOUSE)
        is_ctrl_o_pressed: bool = KEYBOARD.is_ctrl_on and K_o in KEYBOARD.pressed
        if (is_open_clicked or is_ctrl_o_pressed) and not self._is_asking_file_open:
            self._is_asking_file_open = True
            Thread(target=_ask_open_file, daemon=True).start()

    def _upt_file_closing(self) -> None:
        """Updates the close file button."""

        is_close_clicked: bool = CLOSE.upt(MOUSE)
        is_ctrl_q_pressed: bool = KEYBOARD.is_ctrl_on and K_q in KEYBOARD.pressed
        if (is_close_clicked or is_ctrl_q_pressed) and self._file_str != "":
            GRID_MANAGER.grid.try_save_to_file(self._file_str, True)

            self._file_str = ""
            self._is_unsaved = True
            GRID_MANAGER.grid.set_tiles(None)
            self._set_file_text_label()

    def _main_interface(self) -> None:
        """Handles the main interface."""

        k: int
        hex_color: HexColor
        did_palette_change: bool
        hex_color_to_edit: Optional[HexColor]

        if KEYBOARD.is_ctrl_on:  # Independent shortcuts
            max_brush_dim_ctrl_shortcut: int = min(len(BRUSH_DIMS.checkboxes), 9)
            for k in range(K_1, K_1 + max_brush_dim_ctrl_shortcut):
                if k in KEYBOARD.pressed:
                    BRUSH_DIMS.check(k - K_1)
                    GRID_MANAGER.grid.set_selected_tile_dim(BRUSH_DIMS.clicked_i + 1)

        prev_brush_i: int = BRUSH_DIMS.clicked_i
        brush_i: int = BRUSH_DIMS.upt(MOUSE, KEYBOARD)
        if brush_i != prev_brush_i:
            GRID_MANAGER.grid.set_selected_tile_dim(brush_i + 1)

        hex_color, did_palette_change, hex_color_to_edit = PALETTE_MANAGER.upt(MOUSE, KEYBOARD)
        tool_info: ToolInfo = TOOLS_MANAGER.upt(MOUSE, KEYBOARD)
        did_grid_change: bool = GRID_MANAGER.upt(MOUSE, KEYBOARD, hex_color, tool_info)
        if did_grid_change and self._file_str != "":
            self._refresh_is_unsaved()

        self._upt_file_saving()
        self._upt_file_opening()
        self._upt_file_closing()

        self._upt_ui_openers()
        if hex_color_to_edit is not None:
            self._state_i = STATE_I_COLOR
            COLOR_PICKER.set_color(hex_color_to_edit, True)

        if did_palette_change:  # Changes the hovered checkbox image immediately
            self._refresh_objs()
            self._refresh_hovered_obj()
            # Checkbox won't be clicked immediately if the dropdown menu moves
            PALETTE_MANAGER.colors_grid.upt_checkboxes(
                Mouse(-1, -1, (False,) * 3, (False,) * 5, 0, MOUSE.hovered_obj),
            )

    def _color_ui(self) -> None:
        """Handles the color UI."""

        did_exit: bool
        did_confirm: bool
        rgb_color: RGBColor

        did_exit, did_confirm, rgb_color = COLOR_PICKER.upt(MOUSE, KEYBOARD)
        if did_exit:
            PALETTE_MANAGER.is_editing_color = False
            self._state_i = STATE_I_MAIN
        elif did_confirm:
            should_refresh_objs: bool = PALETTE_MANAGER.add(rgb_color)
            if should_refresh_objs:
                self._refresh_objs()

            self._state_i = STATE_I_MAIN

    def _grid_ui(self) -> None:
        """Handles the grid UI."""

        did_exit: bool
        did_confirm: bool
        cols: int
        rows: int

        did_exit, did_confirm, cols, rows = GRID_UI.upt(MOUSE, KEYBOARD)
        if did_exit:
            self._state_i = STATE_I_MAIN
            self._new_file_img = None
        elif did_confirm:
            if self._new_file_img is not None:
                # Save before setting info
                GRID_MANAGER.grid.try_save_to_file(self._file_str, True)

            GRID_MANAGER.grid.set_info(
                Size(cols, rows),
                GRID_MANAGER.grid.visible_area.w, GRID_MANAGER.grid.visible_area.h,
                GRID_MANAGER.grid.offset.x, GRID_MANAGER.grid.offset.y
            )

            if self._new_file_img is None:
                GRID_MANAGER.grid.refresh_full()
            else:
                GRID_MANAGER.grid.set_tiles(self._new_file_img)
                self._file_str = self._new_file_str
                self._new_file_img = None
                self._set_file_text_label()
            if self._file_str != "":
                self._refresh_is_unsaved()

            self._state_i = STATE_I_MAIN

    def _handle_states(self) -> None:
        """Handles updating and leaving states."""

        prev_state_i: int = self._state_i
        if self._state_i == STATE_I_MAIN:
            self._main_interface()
        elif self._state_i == STATE_I_COLOR:
            self._color_ui()
        elif self._state_i == STATE_I_GRID:
            self._grid_ui()

        if self._state_i != prev_state_i:
            self._change_state()

    def _handle_crash(self) -> None:
        """Saves the file before crashing."""

        if self._file_str == "":
            duplicate_name_counter: int = 0
            file_path: Path = Path("new_file.png")
            while file_path.exists():
                duplicate_name_counter += 1
                file_path = Path(f"new_file_{duplicate_name_counter}.png")
            self._file_str = str(file_path.absolute())

        self._save_to_file(False)

    def run(self) -> None:
        """Game loop."""

        WIN.show()
        WIN.focus()
        try:
            while True:
                CLOCK.tick(0)

                MOUSE.x, MOUSE.y = pg.mouse.get_pos() if pg.mouse.get_focused() else (-1, -1)
                MOUSE.pressed = pg.mouse.get_pressed()
                MOUSE.released = pg.mouse.get_just_released()
                MOUSE.scroll_amount = 0

                self._handle_events()
                self._handle_asked_files_queue()
                state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
                self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]

                self._refresh_timed_keys()
                self._refresh_hovered_obj()
                self._set_cursor_type()

                if KEYBOARD.timed != [] and not self._is_fullscreen:
                    self._resize_with_keys()
                self._handle_states()

                self._draw()
        except KeyboardInterrupt:
            self._save_to_file(False)
        except Exception:
            self._handle_crash()

            raise


if __name__ == "__main__":
    Dixel().run()
    print_funcs_profiles()
