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
- indicate file
- remove portalocker
- acceleration in grid movement and zoom
- better grid transition?
- hovering text appears when standing still (more stuff with hovering text)
- option to change the palette to match the current colors/multiple palettes
- CTRL Z/Y (UI to view history)
- Save window info
- option to make drawing only affect the visible_area?
- way to close without auto saving?
- have multiple files open
- handle old data files
- refresh file when modified externally
- UIs as separate windows?
- asking before closing unsaved file?
- error messages as windows?
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
    - better memory use in PaletteManager
"""

from tkinter import filedialog
from threading import Thread
from queue import Queue, Empty as QueueEmpty
from pathlib import Path
from json import load as json_load, dumps as json_dumps, JSONDecodeError
from sys import argv
from contextlib import suppress
from typing import TypeAlias, Final, Optional, Any

import pygame as pg
from numpy import uint8
from numpy.typing import NDArray
from portalocker import LOCK_SH, LOCK_EX, LockException

from src.classes.grid_manager import GridManager
from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Button
from src.classes.text_label import TextLabel

from src.utils import (
    RectPos, Size, ObjInfo, Mouse, Keyboard, get_pixels, get_brush_dim_img, print_funcs_profiles
)
from src.file_utils import (
    ensure_valid_img_format, try_lock_file, try_get_img, try_create_file_argv, try_create_dir_argv,
    handle_cmd_args
)
from src.type_utils import XY, RGBColor, HexColor, CheckboxInfo, ToolInfo, LayeredBlitInfo
from src.consts import (
    CHR_LIMIT, BLACK, HEX_BLACK, NUM_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY, BG_LAYER,
    STATE_I_MAIN, STATE_I_COLOR, STATE_I_GRID
)

pg.init()

WIN_INIT_W: Final[int] = 1_200
WIN_INIT_H: Final[int] = 900
WIN: Final[pg.Window] = pg.Window(
    "Dixel", (WIN_INIT_W, WIN_INIT_H),
    hidden=True, resizable=True, allow_high_dpi=True
)
WIN_SURF: Final[pg.Surface] = WIN.get_surface()

WIN.minimum_size = (WIN_INIT_W, WIN_INIT_H)
WIN.set_icon(try_get_img("sprites", "icon.png", missing_img_wh=(32, 32)))

# These files load images at the start which requires a window
from src.classes.grid_ui import GridUI
from src.classes.color_ui import ColorPicker
from src.classes.ui import BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG
from src.classes.tools_manager import ToolsManager
from src.classes.palette_manager import PaletteManager, BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG

NumPadMap: TypeAlias = dict[int, tuple[int, int]]
StatesObjInfo: TypeAlias = tuple[list[ObjInfo], ...]

NUMPAD_MAP: Final[NumPadMap] = {
    pg.K_KP_0: (pg.K_INSERT, pg.K_0),
    pg.K_KP_1: (pg.K_END, pg.K_1),
    pg.K_KP_2: (pg.K_DOWN, pg.K_2),
    pg.K_KP_3: (pg.K_PAGEDOWN, pg.K_3),
    pg.K_KP_4: (pg.K_LEFT, pg.K_4),
    pg.K_KP_5: (0, pg.K_5),
    pg.K_KP_6: (pg.K_RIGHT, pg.K_6),
    pg.K_KP_7: (pg.K_HOME, pg.K_7),
    pg.K_KP_8: (pg.K_UP, pg.K_8),
    pg.K_KP_9: (pg.K_PAGEUP, pg.K_9),
    pg.K_KP_PERIOD: (pg.K_DELETE, pg.K_PERIOD)
}

ADD_COLOR: Final[Button] = Button(
    RectPos(WIN_INIT_W - 10, WIN_INIT_H - 10, "bottomright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Add Color", "(CTRL+A)"
)
EDIT_GRID: Final[Button] = Button(
    RectPos(ADD_COLOR.rect.x - 10, ADD_COLOR.rect.y, "topright"),
    [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Edit Grid", "(CTRL+G)"
)

SAVE: Final[Button] = Button(
    RectPos(0, 0, "topleft"),
    [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Save", "(CTRL+S)", text_h=15
)
SAVE_AS: Final[Button] = Button(
    RectPos(SAVE.rect.right, SAVE.rect.y, "topleft"),
    [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Save as", "(CTRL+SHIFT+S)", text_h=15
)
OPEN: Final[Button] = Button(
    RectPos(SAVE_AS.rect.right, SAVE_AS.rect.y, "topleft"),
    [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Open", "(CTRL+O)", text_h=15
)
CLOSE: Final[Button] = Button(
    RectPos(OPEN.rect.right, OPEN.rect.y, "topleft"),
    [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Close", "(CTRL+Q)", text_h=15
)

GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center"),
    RectPos(WIN_INIT_W - 10, 10, "topright")
)

brush_dims_info: list[CheckboxInfo] = [
    (get_brush_dim_img(i), f"{i}px\n(CTRL+{i})") for i in range(1, 6)
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

COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center")
)
GRID_UI: Final[GridUI] = GridUI(
    RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center")
)

MAIN_STATES_OBJS_INFO: Final[StatesObjInfo] = (
    [
        ObjInfo(ADD_COLOR), ObjInfo(EDIT_GRID),
        ObjInfo(SAVE), ObjInfo(SAVE_AS), ObjInfo(OPEN), ObjInfo(CLOSE),
        ObjInfo(GRID_MANAGER),
        ObjInfo(BRUSH_DIMS), ObjInfo(PALETTE_MANAGER), ObjInfo(TOOLS_MANAGER),
        ObjInfo(FPS_TEXT_LABEL)
    ],
    [ObjInfo(COLOR_PICKER)],
    [ObjInfo(GRID_UI)]
)

CLOCK: Final[pg.Clock] = pg.Clock()

FPSUPDATE: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPSUPDATE, 1_000)

FILE_DIALOG_SAVE_AS: Final[int] = 0
FILE_DIALOG_OPEN: Final[int] = 1


def _try_create_argv(file_path: Path, flag: str) -> Optional[pg.Surface]:
    """
    Creates a file if the flag is --mk-file and a directory if the flag is --mk-dir.

    Args:
        file path, flag
    Returns:
        grid image (can be None)
    """

    has_failed: bool
    grid_img: Optional[pg.Surface]

    if file_path.parent.is_dir():
        has_failed = try_create_file_argv(file_path, flag)
    else:
        has_failed = try_create_dir_argv(file_path, flag)

    if has_failed:
        grid_img = None
    else:
        grid_img = GRID_MANAGER.grid.try_save_to_file(str(file_path))

    return grid_img


class Dixel:
    """Drawing program for pixel art."""

    __slots__ = (
        "_is_fullscreen", "_cursor_arrow", "_mouse", "_cursor_type", "_keyboard",
        "_timed_keys_interval", "_prev_timed_keys_update", "_alt_k", "_state_i",
        "_states_objs_info", "_state_active_objs", "_data_file_str", "_file_str", "_new_file_str",
        "_new_file_img", "_asked_files_queue", "_is_asking_file_save_as", "_is_asking_file_open"
    )

    def __init__(self) -> None:
        """Initializes the window."""

        self._is_fullscreen: bool = False

        self._cursor_arrow: int = pg.SYSTEM_CURSOR_ARROW
        self._mouse: Mouse = Mouse(-1, -1, [False] * 5, [False] * 5, 0, None)
        self._cursor_type: int = self._cursor_arrow
        self._keyboard: Keyboard = Keyboard([], [], False, False, False, False)

        self._timed_keys_interval: int = 150
        self._prev_timed_keys_update: int = -self._timed_keys_interval
        self._alt_k: str = ""

        self._state_i: int = STATE_I_MAIN
        self._states_objs_info: list[list[ObjInfo]] = []
        self._state_active_objs: list[Any] = []

        self._data_file_str = "data.json"
        self._file_str: str = ""
        self._new_file_str: str = ""
        self._new_file_img: Optional[pg.Surface] = None

        self._asked_files_queue: Queue[tuple[str, int]] = Queue()
        self._is_asking_file_save_as: bool = False
        self._is_asking_file_open: bool = False

        self._load_data_from_file()

        grid_img: Optional[pg.Surface] = None
        if len(argv) > 1:
            grid_img = self._handle_path_from_argv()
        elif self._file_str != "":
            grid_img = try_get_img(self._file_str, is_grid_img=True)

        if grid_img is None:
            self._file_str = ""
            GRID_MANAGER.grid.refresh_full()
        else:
            GRID_MANAGER.grid.set_tiles(grid_img)
        # Calls GRID_MANAGER.grid.refresh_grid_img so it must be called after grid.set_tiles
        GRID_MANAGER.grid.set_selected_tile_dim(BRUSH_DIMS.clicked_i + 1)

        self._refresh_objs()

    def _try_get_data(self) -> Optional[dict[str, Any]]:
        """
        Gets the data from the data file.

        Returns:
            data
        """

        num_failed_open_attempts: int

        data: Optional[dict[str, Any]] = None
        data_file: Path = Path(self._data_file_str)
        for num_failed_open_attempts in range(1, NUM_FILE_ATTEMPTS + 1):
            try:
                with data_file.open(encoding="utf-8", errors="replace") as f:
                    try_lock_file(f, LOCK_SH)
                    data = json_load(f)
                break
            except FileNotFoundError:
                break
            except PermissionError:
                print("Failed to load data. Permission denied.")
                break
            except JSONDecodeError:
                print("Failed to load data. Invalid json.")
                break
            except LockException:
                print("Failed to load data. File is locked.")
                break
            except OSError as e:
                if num_failed_open_attempts == NUM_FILE_ATTEMPTS:
                    print(f"Failed to load data. {e}.")
                    break

                pg.time.wait(FILE_ATTEMPT_DELAY * num_failed_open_attempts)

        return data

    def _load_data_from_file(self) -> None:
        """Loads the data from the data file."""

        data: Optional[dict[str, Any]] = self._try_get_data()
        if data is None:
            return

        self._file_str = data["file"]
        if self._file_str != "":
            self._file_str = ensure_valid_img_format(self._file_str)

        BRUSH_DIMS.check(data["brush_dim_i"])
        PALETTE_MANAGER.set_info(
            data["colors"], data["color_i"], data["color_offset"], data["dropdown_i"]
        )
        TOOLS_MANAGER.tools_grid.check(data["tool_i"])
        TOOLS_MANAGER.refresh_tools(0)

        # GRID_MANAGER.grid.set_tiles is called later
        GRID_MANAGER.grid.set_info(
            Size(data["grid_cols"], data["grid_rows"]),
            data["grid_vis_cols"], data["grid_vis_rows"],
            data["grid_offset_x"], data["grid_offset_y"]
        )

        if data["grid_ratio"] is not None:
            GRID_UI.checkbox.img_i = 1
            GRID_UI.checkbox.is_checked = True
            GRID_UI.w_ratio, GRID_UI.h_ratio = data["grid_ratio"]

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
        num_failed_open_attempts: int

        self._file_str, flag, are_argv_invalid = handle_cmd_args(argv)
        if are_argv_invalid:
            raise SystemExit

        grid_img: Optional[pg.Surface] = None
        file_path: Path = Path(self._file_str)
        for num_failed_open_attempts in range(1, NUM_FILE_ATTEMPTS + 1):
            try:
                with file_path.open("rb") as f:
                    try_lock_file(f, LOCK_SH)
                    grid_img = pg.image.load(f, file_path.name).convert_alpha()
                break
            except FileNotFoundError:
                grid_img = _try_create_argv(file_path, flag)
                break
            except PermissionError:
                print(f'Failed to load image "{file_path.name}". Permission denied.')
                break
            except LockException:
                print(f'Failed to load image "{file_path.name}". File is locked.')
                break
            except pg.error as e:
                print(f'Failed to load image "{file_path.name}". {e}.')
                break
            except OSError as e:
                if num_failed_open_attempts == NUM_FILE_ATTEMPTS:
                    print(f'Failed to load image "{file_path.name}". {e}.')
                    break

                pg.time.wait(FILE_ATTEMPT_DELAY * num_failed_open_attempts)

        if grid_img is None:
            raise SystemExit
        return grid_img

    def _draw(self) -> None:
        """Gets every blit_sequence attribute and draws it to the screen."""

        obj: Any

        def _get_layer(blit_info: LayeredBlitInfo) -> int:
            """
            Gets the layer from a layered blit info.

            Args:
                blit info
            Returns:
                layer
            """

            return blit_info[2]

        blittable_objs: list[Any] = self._state_active_objs.copy()
        if self._state_i != STATE_I_MAIN:
            home_objs_info: list[ObjInfo] = self._states_objs_info[STATE_I_MAIN]
            blittable_objs.extend([info.obj for info in home_objs_info if info.is_active])

        main_sequence: list[LayeredBlitInfo] = []
        for obj in blittable_objs:
            main_sequence.extend(obj.blit_sequence)
        main_sequence.sort(key=_get_layer)

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

        max_layer: int = BG_LAYER
        mouse_xy: XY = (self._mouse.x, self._mouse.y)
        for obj in self._state_active_objs:
            can_get_hovering: bool = hasattr(obj, "get_hovering")
            if can_get_hovering and obj.get_hovering(mouse_xy) and obj.layer >= max_layer:
                self._mouse.hovered_obj = obj
                max_layer = obj.layer

    def _set_cursor_type(self) -> None:
        """Sets the cursor type using the cursor_type attribute of the hovered object."""

        prev_cursor_type: int = self._cursor_type

        has_type: bool = hasattr(self._mouse.hovered_obj, "cursor_type")
        self._cursor_type = self._mouse.hovered_obj.cursor_type if has_type else self._cursor_arrow
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
        pg.mouse.set_cursor(self._cursor_arrow)

    def _resize_objs(self) -> None:
        """Resizes every object of the main and current state with a resize method."""

        win_w: int
        win_h: int
        obj: Any

        resizable_objs: list[Any] = [info.obj for info in self._states_objs_info[self._state_i]]
        if self._state_i != STATE_I_MAIN:
            resizable_objs.extend([info.obj for info in self._states_objs_info[STATE_I_MAIN]])

        win_w, win_h = WIN_SURF.get_size()
        win_w_ratio: float = win_w / WIN_INIT_W
        win_h_ratio: float = win_h / WIN_INIT_H
        for obj in resizable_objs:
            if hasattr(obj, "resize"):
                obj.resize(win_w_ratio, win_h_ratio)

    def _add_to_keys(self, k: int) -> None:
        """
        Adds a key to the pressed_keys if it's not using alt.

        Args:
            key
        """

        if k in NUMPAD_MAP:
            numpad_map_i: int = int(self._keyboard.is_numpad_on)
            k = NUMPAD_MAP[k][numpad_map_i]

        if self._keyboard.is_alt_on and (pg.K_0 <= k <= pg.K_9):
            self._alt_k += chr(k)
            if int(self._alt_k) > CHR_LIMIT:
                self._alt_k = self._alt_k[-1]
            self._alt_k = self._alt_k.lstrip("0")
        else:
            self._keyboard.pressed.append(k)

    def _handle_key_press(self, k: int) -> None:
        """
        Handles key presses.

        Args:
            key
        """

        if k == pg.K_ESCAPE and self._state_i == STATE_I_MAIN:
            raise KeyboardInterrupt

        # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs isn't necessary
        if k == pg.K_F1:
            self._is_fullscreen = False
            WIN.size = WIN.minimum_size
            WIN.set_windowed()
        elif k == pg.K_F11:
            self._is_fullscreen = not self._is_fullscreen
            if self._is_fullscreen:
                WIN.set_fullscreen(True)
            else:
                WIN.set_windowed()

        self._keyboard.is_ctrl_on = pg.key.get_mods() & pg.KMOD_CTRL != 0
        self._keyboard.is_shift_on = pg.key.get_mods() & pg.KMOD_SHIFT != 0
        self._keyboard.is_alt_on = pg.key.get_mods() & pg.KMOD_ALT != 0
        self._keyboard.is_numpad_on = pg.key.get_mods() & pg.KMOD_NUM != 0
        self._add_to_keys(k)

        self._prev_timed_keys_update = -self._timed_keys_interval

    def _handle_key_release(self, k: int) -> None:
        """
        Handles key releases.

        Args:
            key
        """

        self._keyboard.is_ctrl_on = pg.key.get_mods() & pg.KMOD_CTRL != 0
        self._keyboard.is_shift_on = pg.key.get_mods() & pg.KMOD_SHIFT != 0
        self._keyboard.is_alt_on = pg.key.get_mods() & pg.KMOD_ALT != 0
        self._keyboard.is_numpad_on = pg.key.get_mods() & pg.KMOD_NUM != 0

        if k in self._keyboard.pressed:
            self._keyboard.pressed.remove(k)

    def _handle_events(self) -> None:
        """Handles events."""

        event: pg.Event

        self._mouse.released = [False] * 5
        self._mouse.scroll_amount = 0
        self._mouse.hovered_obj = None
        self._keyboard.timed = []

        for event in pg.event.get():
            if event.type == pg.WINDOWCLOSE:
                raise KeyboardInterrupt

            if event.type == pg.WINDOWSIZECHANGED:
                self._resize_objs()

            elif event.type == pg.MOUSEMOTION:
                self._mouse.x, self._mouse.y = event.pos
            elif event.type == pg.WINDOWLEAVE:
                self._mouse.x = self._mouse.y = -1
            elif event.type == pg.MOUSEBUTTONDOWN:
                self._mouse.pressed[event.button - 1] = True
            elif event.type == pg.MOUSEBUTTONUP:
                self._mouse.pressed[event.button - 1] = False
                self._mouse.released[event.button - 1] = True
            elif event.type == pg.MOUSEWHEEL:
                self._mouse.scroll_amount = event.y

            elif event.type == pg.KEYDOWN:
                self._handle_key_press(event.key)
            elif event.type == pg.KEYUP:
                self._handle_key_release(event.key)
            elif event.type == FPSUPDATE:
                FPS_TEXT_LABEL.set_text(f"FPS: {CLOCK.get_fps():.2f}")

    def _ask_save_to_file(self) -> None:
        """Asks a file to save with tkinter."""

        file_str: Any = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("Png Files", "*.png"), ("Bitmap Files", "*.bmp")],
            title="Save As"
        )
        # On some explorers closing won't return an empty string
        file_str = file_str if isinstance(file_str, str) else ""

        self._asked_files_queue.put((file_str, FILE_DIALOG_SAVE_AS))

    def _ask_open_file(self) -> None:
        """Asks a file to open with tkinter."""

        file_str: Any = filedialog.askopenfilename(
            defaultextension=".png",
            filetypes=[("Png Files", "*.png"), ("Bitmap Files", "*.bmp")],
            title="Open"
        )
        # On some explorers closing won't return an empty string
        file_str = file_str if isinstance(file_str, str) else ""

        self._asked_files_queue.put((file_str, FILE_DIALOG_OPEN))

    def _finish_ask_save_to_file(self, file_str: str) -> None:
        """
        Saves the file after the user chooses it with tkinter.

        Args:
            file string
        """

        if file_str == "":
            return

        file_str = ensure_valid_img_format(file_str)
        grid_img: Optional[pg.Surface] = GRID_MANAGER.grid.try_save_to_file(file_str)
        if grid_img is not None:
            self._file_str = file_str

    def _finish_ask_open_file(self, file_str: str) -> None:
        """
        Opens a file and loads it into the grid UI after the user chooses it with tkinter.

        Args:
            file string
        """

        if file_str == "":
            return

        file_str = ensure_valid_img_format(file_str)
        self._new_file_img = try_get_img(file_str, is_grid_img=True)
        if self._new_file_img is not None:
            if self._state_i == STATE_I_GRID:
                self._change_state()  # Refreshes

            self._new_file_str = file_str
            self._state_i = STATE_I_GRID
            img_pixels: NDArray[uint8] = get_pixels(self._new_file_img)
            GRID_UI.set_info(GRID_MANAGER.grid.area, img_pixels)

    def _handle_asked_files_queue(self) -> None:
        """Processes every item in the asked files queue."""

        file_str: str
        dialog_type: int

        with suppress(QueueEmpty):
            while True:
                # QueueEmpty is suppressed
                file_str, dialog_type = self._asked_files_queue.get_nowait()

                if dialog_type == FILE_DIALOG_SAVE_AS:
                    self._finish_ask_save_to_file(file_str)
                    self._is_asking_file_save_as = False
                elif dialog_type == FILE_DIALOG_OPEN:
                    self._finish_ask_open_file(file_str)
                    self._is_asking_file_open = False

    def _refresh_timed_keys(self) -> None:
        """Refreshes the timed keys once every 150ms and adds the alt key if present."""

        if pg.time.get_ticks() - self._prev_timed_keys_update >= self._timed_keys_interval:
            numpad_map_i: int = int(self._keyboard.is_numpad_on)
            self._keyboard.timed = [
                NUMPAD_MAP[k][numpad_map_i] if k in NUMPAD_MAP else k
                for k in self._keyboard.pressed
            ]

            self._prev_timed_keys_update = pg.time.get_ticks()

        if self._alt_k != "" and not self._keyboard.is_alt_on:
            self._keyboard.timed.append(int(self._alt_k))
            self._alt_k = ""

    def _resize_with_keys(self) -> None:
        """Resizes the window trough keys."""

        win_w: int
        win_h: int

        win_w, win_h = WIN_SURF.get_size()
        if pg.K_F5 in self._keyboard.timed:
            win_w -= 1
        if pg.K_F6 in self._keyboard.timed:
            win_w += 1
        if pg.K_F7 in self._keyboard.timed:
            win_h -= 1
        if pg.K_F8 in self._keyboard.timed:
            win_h += 1

        if win_w != WIN_SURF.get_width() or win_h != WIN_SURF.get_height():
            # Resizing triggers a WINDOWSIZECHANGED event, calling resize_objs isn't necessary
            WIN.size = (win_w, win_h)

    def _save_to_file(self) -> None:
        """Saves the file."""

        grid_ratio: Optional[tuple[float, float]]
        palette_dropdown_i: Optional[int]
        num_failed_open_attempts: int

        grid_ratio = (GRID_UI.w_ratio, GRID_UI.h_ratio) if GRID_UI.checkbox.is_checked else None
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
            "grid_ratio": grid_ratio,
            "colors": PALETTE_MANAGER.colors
        }

        json_data: str = json_dumps(data, ensure_ascii=False, indent=4)
        json_bytes: bytes = json_data.encode("utf-8")
        for num_failed_open_attempts in range(1, NUM_FILE_ATTEMPTS + 1):
            try:
                # If you open in write mode it will empty the file even if it's locked
                with Path(self._data_file_str).open("ab") as f:
                    try_lock_file(f, LOCK_EX)
                    f.truncate(0)
                    f.write(json_bytes)
                break
            except PermissionError:
                print("Failed to save data. Permission denied.")
                break
            except LockException:
                print("Failed to save data. File is locked.")
                break
            except OSError as e:
                if num_failed_open_attempts == NUM_FILE_ATTEMPTS:
                    print(f"Failed to save data. {e}.")
                    break

                pg.time.wait(FILE_ATTEMPT_DELAY * num_failed_open_attempts)

        GRID_MANAGER.grid.try_save_to_file(self._file_str)

    def _upt_ui_openers(self) -> None:
        """Updates the buttons that open UIs."""

        is_add_color_clicked: bool = ADD_COLOR.upt(self._mouse)
        is_ctrl_a_pressed: bool = self._keyboard.is_ctrl_on and pg.K_a in self._keyboard.pressed
        if is_add_color_clicked or is_ctrl_a_pressed:
            self._state_i = STATE_I_COLOR
            COLOR_PICKER.set_color(HEX_BLACK, True)

        is_edit_grid_clicked: bool = EDIT_GRID.upt(self._mouse)
        is_ctrl_g_pressed: bool = self._keyboard.is_ctrl_on and pg.K_g in self._keyboard.pressed
        if is_edit_grid_clicked or is_ctrl_g_pressed:
            self._state_i = STATE_I_GRID
            GRID_UI.set_info(GRID_MANAGER.grid.area, GRID_MANAGER.grid.tiles)

    def _upt_file_saving(self) -> None:
        """Updates the save as button."""

        is_ctrl_s_pressed: bool = False
        is_ctrl_shift_s_pressed: bool = False
        if self._keyboard.is_ctrl_on and pg.K_s in self._keyboard.pressed:
            if self._keyboard.is_shift_on:
                is_ctrl_shift_s_pressed = True
            else:
                is_ctrl_s_pressed = True

        is_save_clicked: bool = SAVE.upt(self._mouse)
        if is_save_clicked or is_ctrl_s_pressed:
            self._save_to_file()

        is_save_as_clicked: bool = SAVE_AS.upt(self._mouse)
        if (is_save_as_clicked or is_ctrl_shift_s_pressed) and not self._is_asking_file_save_as:
            self._is_asking_file_save_as = True
            Thread(target=self._ask_save_to_file, daemon=True).start()

    def _upt_file_opening(self) -> None:
        """Updates the open file button."""

        is_open_clicked: bool = OPEN.upt(self._mouse)
        is_ctrl_o_pressed: bool = self._keyboard.is_ctrl_on and pg.K_o in self._keyboard.pressed
        if (is_open_clicked or is_ctrl_o_pressed) and not self._is_asking_file_open:
            self._is_asking_file_open = True
            Thread(target=self._ask_open_file, daemon=True).start()

    def _upt_file_closing(self) -> None:
        """Updates the close file button."""

        is_close_clicked: bool = CLOSE.upt(self._mouse)
        is_ctrl_q_pressed: bool = self._keyboard.is_ctrl_on and pg.K_q in self._keyboard.pressed
        if (is_close_clicked or is_ctrl_q_pressed) and self._file_str != "":
            GRID_MANAGER.grid.try_save_to_file(self._file_str)
            self._file_str = ""
            GRID_MANAGER.grid.set_tiles(None)

    def _main_interface(self) -> None:
        """Handles the main interface."""

        key: int
        hex_color: HexColor
        did_colors_change: bool
        hex_color_to_edit: Optional[HexColor]

        mouse: Mouse = self._mouse
        keyboard: Keyboard = self._keyboard

        if keyboard.is_ctrl_on:  # Independent shortcuts
            max_brush_dim_ctrl_shortcut: int = min(len(BRUSH_DIMS.checkboxes), 9)
            for key in range(pg.K_1, pg.K_1 + max_brush_dim_ctrl_shortcut):
                if key in keyboard.pressed:
                    BRUSH_DIMS.check(key - pg.K_1)
                    GRID_MANAGER.grid.set_selected_tile_dim(BRUSH_DIMS.clicked_i + 1)

        prev_brush_i: int = BRUSH_DIMS.clicked_i
        brush_i: int = BRUSH_DIMS.upt(mouse, keyboard)
        if brush_i != prev_brush_i:
            GRID_MANAGER.grid.set_selected_tile_dim(brush_i + 1)

        hex_color, did_colors_change, hex_color_to_edit = PALETTE_MANAGER.upt(mouse, keyboard)
        tool_info: ToolInfo = TOOLS_MANAGER.upt(mouse, keyboard)
        GRID_MANAGER.upt(mouse, keyboard, hex_color, tool_info)

        self._upt_file_saving()
        self._upt_file_opening()
        self._upt_file_closing()

        self._upt_ui_openers()
        if hex_color_to_edit is not None:
            self._state_i = STATE_I_COLOR
            COLOR_PICKER.set_color(hex_color_to_edit, True)

        if did_colors_change:  # Changes the hovered checkbox image immediately
            mouse.hovered_obj = None
            self._refresh_objs()
            self._refresh_hovered_obj()

            # Checkbox won't be clicked immediately if the dropdown menu moves
            PALETTE_MANAGER.colors_grid.upt_checkboxes(
                Mouse(-1, -1, [False] * 3, [False] * 3, 0, mouse.hovered_obj),
            )

    def _color_ui(self) -> None:
        """Handles the color UI."""

        has_exited: bool
        has_confirmed: bool
        rgb_color: RGBColor

        has_exited, has_confirmed, rgb_color = COLOR_PICKER.upt(self._mouse, self._keyboard)
        if has_exited:
            PALETTE_MANAGER.is_editing_color = False
            self._state_i = STATE_I_MAIN
        elif has_confirmed:
            should_refresh_objs: bool = PALETTE_MANAGER.add(rgb_color)
            if should_refresh_objs:
                self._refresh_objs()
            self._state_i = STATE_I_MAIN

    def _grid_ui(self) -> None:
        """Handles the grid UI."""

        has_exited: bool
        has_confirmed: bool
        cols: int
        rows: int

        has_exited, has_confirmed, cols, rows = GRID_UI.upt(self._mouse, self._keyboard)
        if has_exited:
            self._state_i = STATE_I_MAIN
            self._new_file_img = None
        elif has_confirmed:
            if self._new_file_img is not None:
                # Save before setting info
                GRID_MANAGER.grid.try_save_to_file(self._file_str)

            GRID_MANAGER.grid.set_info(
                Size(cols, rows),
                GRID_MANAGER.grid.visible_area.w, GRID_MANAGER.grid.visible_area.h,
                GRID_MANAGER.grid.offset.x, GRID_MANAGER.grid.offset.y
            )

            if self._new_file_img is not None:
                GRID_MANAGER.grid.set_tiles(self._new_file_img)
                self._file_str = self._new_file_str
                self._new_file_img = None
            else:
                GRID_MANAGER.grid.refresh_full()
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
            self._file_str = str(file_path)

        self._save_to_file()

    def run(self) -> None:
        """Game loop."""

        WIN.show()
        try:
            while True:
                CLOCK.tick(60)

                self._handle_events()
                self._handle_asked_files_queue()
                state_objs_info: list[ObjInfo] = self._states_objs_info[self._state_i]
                self._state_active_objs = [info.obj for info in state_objs_info if info.is_active]

                self._refresh_timed_keys()
                self._refresh_hovered_obj()
                self._set_cursor_type()

                if self._keyboard.timed != [] and not self._is_fullscreen:
                    self._resize_with_keys()
                self._handle_states()

                self._draw()
        except KeyboardInterrupt:
            self._save_to_file()
        except Exception:
            self._handle_crash()

            raise


if __name__ == "__main__":
    Dixel().run()
    print_funcs_profiles()
