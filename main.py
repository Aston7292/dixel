"""
Drawing program for pixel art.

----------INFO----------
There are three states, the main interface and 2 extra UI windows
that can be opened by clicking their respective button, they're for colors and grid.

Keyboard input:
    Every key that's currently pressed is in a list, accidental spamming is prevented
    by temporarily clearing this list when a key is held and reverting it back for
    one frame every 100ms.

Mouse info:
    Mouse info is contained in the dataclass MouseInfo that tracks:
    x and y position, pressed buttons and recently released ones (for clicking elements).

Sub objects:
    Objects may have a objs_info attribute, a list of sub objects, stored in the dataclass ObjInfo
    retrieved at the start of each frame and automatically call the methods below.

Blitting:
    The blit method returns a list with one or more groups of image, position and layer,
    objects with an higher layer will be blitted on top of objects with a lower one.

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
    The get_hovering_info method takes the mouse info and
    returns whatever the object is being hovered or not and its layer,
    only one object can be hovered at a time,
    if there's more than one it will be chose the one with the highest layer.

Leaving a state:
    The leave method gets called when the state changes or file explorer is opened
    and clears all the relevant data, like the selected tiles of the grid or
    the hovering flag for clickables, responsible for showing hovering text.

Window resizing:
    The resize method scales positions and images manually because
    blitting everything on an image, scaling it to match the window size and blitting it
    removes text anti aliasing , causes 1 pixel offsets on some elements at specific sizes, is slow
    and doesn't allow for custom behavior on some objects
    pygame.SCALED doesn't scale position and images.

Interacting with elements:
    Interaction is possible with the upt method,
    it contains a high level implementation of it's behavior.

----------TODO----------
- draw only part of the palette if too big
- indicate unsaved file
- simplify Dixel
- option to change the palette to match the current colors/multiple palettes
- CTRL Z/Y (store without alpha channel, UI to view history)
- option to make drawing only affect the visible_area?
- save button (indicate unsaved file)
- way to close without auto saving?
- have multiple files open
- handle old data files
- refresh file when modified externally
- better mouse sprite handling (if switching objects between frames it won't always be right)
- UIs as separate windows?
- Error messages as windows?

- COLOR_PICKER:
    - hex_text as NumInputBox

- GRID_UI:
    - add option to resize in order to fit image
    - add option to flip sizes
    - separate minimap from grid and place minimap in grid UI
    - add option to change visible_area?
    - move image before resizing?
    - change mouse sprite when using a slider?
    - if checkbox is on, the current slider text is empty and the opp_slider value is 1
    the opp_slider text should be empty

- TOOLS_MANAGER:
    - brush (different shapes?)
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
    - GRID_UI: get_preview
    - GRID_MANAGER: update_section (precalculate section_indicator?)
"""

from pathlib import Path
from sys import argv
from typing import Final, Optional, Any, NoReturn

import json
import pygame as pg

from src.classes.grid_manager import GridManager
from src.classes.palette_manager import PaletteManager
from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Button
from src.classes.text_label import TextLabel

from src.utils import Point, RectPos, Size, Ratio, ObjInfo, MouseInfo, get_img, get_pixels
from src.file_utils import (
    get_img_state, try_create_file_argv, try_create_dir_argv, handle_cmd_args,
    ask_save_to_file, ask_open_file
)
from src.type_utils import PosPair, Color, CheckboxInfo, ToolInfo, BlitSequence, LayeredBlitInfo
from src.consts import (
    CHR_LIMIT, INIT_WIN_SIZE, BLACK, BG_LAYER, STATE_MAIN, STATE_COLOR, STATE_GRID,
    IMG_STATE_OK, IMG_STATE_MISSING, IMG_STATE_DENIED, IMG_STATE_LOCKED, IMG_STATE_CORRUPTED
)

pg.font.init()

WIN: Final[pg.Window] = pg.window.Window("Dixel", (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h))
WIN_SURF: Final[pg.Surface] = WIN.get_surface()

WIN.resizable = True
WIN.minimum_size = (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h)
WIN.set_icon(get_img("sprites", "icon.png"))

# These files load images at the start which requires a window
from src.classes.grid_ui import GridUI
from src.classes.color_ui import ColorPicker
from src.classes.ui import BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG
from src.classes.tools_manager import ToolsManager

BUTTON_S_OFF_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_OFF_IMG, (64, 32))
BUTTON_S_ON_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_ON_IMG, (64, 32))

NumPadMap = dict[int, tuple[int, int]]
NUMPAD_MAP: Final[NumPadMap] = {
    pg.K_KP_0: (pg.K_INSERT, pg.K_0), pg.K_KP_1: (pg.K_END, pg.K_1),
    pg.K_KP_2: (pg.K_DOWN, pg.K_2), pg.K_KP_3: (pg.K_PAGEDOWN, pg.K_3),
    pg.K_KP_4: (pg.K_LEFT, pg.K_4), pg.K_KP_5: (0, pg.K_5),
    pg.K_KP_6: (pg.K_RIGHT, pg.K_6), pg.K_KP_7: (pg.K_HOME, pg.K_7),
    pg.K_KP_8: (pg.K_UP, pg.K_8), pg.K_KP_9: (pg.K_PAGEUP, pg.K_9),
    pg.K_KP_PERIOD: (pg.K_DELETE, pg.K_PERIOD)
}

ADD_COLOR: Final[Button] = Button(
    RectPos(INIT_WIN_SIZE.w - 25, INIT_WIN_SIZE.h - 25, "bottomright"),
    (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "add color", "(CTRL+A)"
)
MODIFY_GRID: Final[Button] = Button(
    RectPos(ADD_COLOR.rect.x - 10, ADD_COLOR.rect.y, "topright"),
    (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "modify grid", "(CTRL+M)"
)

SAVE_AS: Final[Button] = Button(
    RectPos(0, 0, "topleft"), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    "save as", "(CTRL+S)", text_h=15
)
OPEN: Final[Button] = Button(
    RectPos(SAVE_AS.rect.right, 0, "topleft"), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    "open file", "(CTRL+O)", text_h=15
)
CLOSE: Final[Button] = Button(
    RectPos(OPEN.rect.right, 0, "topleft"), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    "close file", "(CTRL+Q)", text_h=15
)

GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(round(INIT_WIN_SIZE.w / 2.0), round(INIT_WIN_SIZE.h / 2.0), "center"),
    RectPos(INIT_WIN_SIZE.w - 10, 10, "topright")
)

BRUSH_SIZES_INFO: Final[tuple[CheckboxInfo, ...]] = tuple(
    (get_img("sprites", f"size_{n}_off.png"), f"{n}px\n(CTRL+{n})") for n in range(1, 6)
)
BRUSH_SIZES: Final[CheckboxGrid] = CheckboxGrid(
    RectPos(10, SAVE_AS.rect.bottom + 10, "topleft"), BRUSH_SIZES_INFO,
    len(BRUSH_SIZES_INFO), (False, False)
)

PALETTE_MANAGER: Final[PaletteManager] = PaletteManager(
    RectPos(INIT_WIN_SIZE.w - 75, ADD_COLOR.rect.y - 25, "bottomright"),
    (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG)
)

TOOLS_MANAGER: Final[ToolsManager] = ToolsManager(
    RectPos(10, INIT_WIN_SIZE.h - 10, "bottomleft")
)

FPS_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(INIT_WIN_SIZE.w / 2.0), 0, "midtop"), "FPS: 0"
)

COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(round(INIT_WIN_SIZE.w / 2.0), round(INIT_WIN_SIZE.h / 2.0), "center")
)
GRID_UI: Final[GridUI] = GridUI(
    RectPos(round(INIT_WIN_SIZE.w / 2.0), round(INIT_WIN_SIZE.h / 2.0), "center")
)

MultiStateObjInfo = tuple[list[ObjInfo], ...]
MAIN_STATES_OBJS_INFO: Final[MultiStateObjInfo] = (
    [
        ObjInfo(ADD_COLOR), ObjInfo(MODIFY_GRID),
        ObjInfo(SAVE_AS), ObjInfo(OPEN), ObjInfo(CLOSE),
        ObjInfo(GRID_MANAGER),
        ObjInfo(BRUSH_SIZES), ObjInfo(PALETTE_MANAGER), ObjInfo(TOOLS_MANAGER),
        ObjInfo(FPS_TEXT_LABEL)
    ],
    [ObjInfo(COLOR_PICKER)],
    [ObjInfo(GRID_UI)]
)

CLOCK: Final[pg.Clock] = pg.time.Clock()

FPSUPDATE: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPSUPDATE, 1_000)

pg.event.set_blocked(None)
pg.event.set_allowed((pg.QUIT, pg.VIDEORESIZE, pg.MOUSEWHEEL, pg.KEYDOWN, pg.KEYUP, FPSUPDATE))


def _get_hex_colors() -> list[str]:
    """
    Gets the used colors as hexadecimal.

    Returns:
        colors
    """

    return [
        "".join(hex(channel)[2:].zfill(2) for channel in color) for color in PALETTE_MANAGER.values
    ]


class Dixel:
    """Drawing program for pixel art."""

    __slots__ = (
        "_is_fullscreen", "_mouse_info", "_pressed_keys", "_timed_keys", "_last_k_input_time",
        "_alt_k", "_kmod_ctrl", "_state", "_active_objs", "_inactive_objs", "_hovered_obj",
        "_data_file_obj", "_file_path", "_is_opening_file"
    )

    def __init__(self) -> None:
        """Initializes the window."""

        self._is_fullscreen: bool = False

        self._mouse_info: MouseInfo = MouseInfo(
            *pg.mouse.get_pos(), pg.mouse.get_pressed(), pg.mouse.get_just_released()
        )
        self._pressed_keys: list[int] = []
        self._timed_keys: list[int] = self._pressed_keys.copy()
        self._last_k_input_time: int = pg.time.get_ticks()

        self._alt_k: str = ""
        self._kmod_ctrl: int = 0
        self._state: int = STATE_MAIN  # Also used as index for object groups

        self._active_objs: list[list[Any]] = []
        self._inactive_objs: list[list[Any]] = []
        self._hovered_obj: Any = None

        self._data_file_obj: Path = Path("data.json")
        self._file_path: str = ""
        self._is_opening_file: bool = False

        if self._data_file_obj.exists():
            self._load_data_from_file()

        if len(argv) > 1:
            self._handle_path_from_argv()
        elif self._file_path:
            self._check_file_path_state()
        grid_img: Optional[pg.Surface] = get_img(self._file_path) if self._file_path else None
        GRID_MANAGER.grid.set_tiles(grid_img)

    def _load_data_from_file(self) -> None:
        """Loads the data from the data file."""

        with self._data_file_obj.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        self._file_path = data["file"]

        rgb_colors: list[Color] = [
            tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) for color in data["colors"]
        ]
        prev_tool_i: int = TOOLS_MANAGER.tools_grid.clicked_i

        PALETTE_MANAGER.set_colors(rgb_colors)
        BRUSH_SIZES.check(data["brush_size_i"])
        PALETTE_MANAGER.colors_grid.check(data["color_i"])
        TOOLS_MANAGER.tools_grid.check(data["tool_i"])
        TOOLS_MANAGER.refresh_tools(prev_tool_i)
        if data["grid_ratio"]:
            GRID_UI.checkbox.is_checked = True
            GRID_UI.values_ratio.w, GRID_UI.values_ratio.h = data["grid_ratio"]

        # Grid.set_tiles is called later
        offset: Point = Point(*data["grid_offset"])
        area: Size = Size(*data["grid_area"])
        visible_area: Size = Size(*data["grid_vis_area"])
        GRID_MANAGER.set_info(offset, area, visible_area)

    def _handle_path_from_argv(self) -> None:
        """
        Handles file opening with cmd args.

        Raises:
            SystemExit
        """

        img_file_path: str
        flag: str
        img_file_path, flag = handle_cmd_args(argv)

        img_state: int = get_img_state(img_file_path)
        should_continue: bool = img_state == IMG_STATE_OK
        if img_state == IMG_STATE_DENIED:
            print("Permission denied.")
        elif img_state == IMG_STATE_LOCKED:
            print("File locked.")
        elif img_state == IMG_STATE_CORRUPTED:
            print("Failed to load file. Might be corrupted.")
        elif img_state == IMG_STATE_MISSING:
            img_file_obj: Path = Path(img_file_path)
            if img_file_obj.parent.is_dir():
                should_continue = try_create_file_argv(img_file_obj, flag)
            else:
                should_continue = try_create_dir_argv(img_file_obj, flag)

            if should_continue:
                GRID_MANAGER.save_to_file(img_file_path)

        if not should_continue:
            raise SystemExit

        self._file_path = img_file_path

    def _check_file_path_state(self) -> None:
        """Checks if the file path is in an invalid state and if so closes it."""

        img_state: int = get_img_state(self._file_path)
        if img_state != IMG_STATE_OK:
            if img_state == IMG_STATE_DENIED:
                print("Permission denied.")
            elif img_state == IMG_STATE_LOCKED:
                print("File locked.")
            elif img_state == IMG_STATE_CORRUPTED:
                print("Failed to load file. Might be corrupted.")

            self._file_path = ""

    def _draw(self) -> None:
        """Draws every object with the blit method to the screen."""

        def _get_layer(blit_info: LayeredBlitInfo) -> int:
            """
            Gets the layer from a layered blit info.

            Args:
                blit info
            Returns:
                layer
            """

            return blit_info[2]

        blittable_objs: list[Any] = self._active_objs[STATE_MAIN].copy()
        if self._state != STATE_MAIN:
            blittable_objs.extend(self._active_objs[self._state])

        main_sequence: list[LayeredBlitInfo] = [
            info for obj in blittable_objs if hasattr(obj, "blit") for info in obj.blit()
        ]

        sorted_main_sequence: list[LayeredBlitInfo] = sorted(main_sequence, key=_get_layer)
        blit_sequence: BlitSequence = [(img, pos) for img, pos, _ in sorted_main_sequence]

        WIN_SURF.fill(BLACK)
        WIN_SURF.fblits(blit_sequence)
        WIN.flip()

    def _get_objs(self) -> None:
        """Gets objects and sub objects."""

        objs_info: list[list[ObjInfo]] = []
        for state_info in MAIN_STATES_OBJS_INFO:
            copy_state_info: list[ObjInfo] = state_info.copy()
            for info in copy_state_info:
                if hasattr(info.obj, "objs_info"):
                    copy_state_info.extend(info.obj.objs_info)
            objs_info.append(copy_state_info)

        self._active_objs = [
            [info.obj for info in state_info if info.is_active]
            for state_info in objs_info
        ]
        self._inactive_objs = [
            [info.obj for info in state_info if not info.is_active]
            for state_info in objs_info
        ]

    def _leave_state(self, state: int) -> None:
        """
        Clears all the relevant data of objects with the leave method when leaving a state.

        Args:
            state
        """

        for obj in self._active_objs[state]:
            if hasattr(obj, "leave"):
                obj.leave()

        self._get_objs()
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

    def _close(self) -> NoReturn:
        """
        Saves the file and closes the program.

        Raises:
            SystemExit
        """

        grid_ratio: Optional[list[float]] = (
            [GRID_UI.values_ratio.w, GRID_UI.values_ratio.h]
            if GRID_UI.checkbox.is_checked else None
        )

        data: dict[str, Any] = {
            "file": self._file_path,
            "grid_offset": [GRID_MANAGER.grid.offset.x, GRID_MANAGER.grid.offset.y],
            "grid_area": [GRID_MANAGER.grid.area.w, GRID_MANAGER.grid.area.h],
            "grid_vis_area": [GRID_MANAGER.grid.visible_area.w, GRID_MANAGER.grid.visible_area.h],
            "brush_size_i": BRUSH_SIZES.clicked_i,
            "color_i": PALETTE_MANAGER.colors_grid.clicked_i,
            "tool_i": TOOLS_MANAGER.tools_grid.clicked_i,
            "grid_ratio": grid_ratio,
            "colors": _get_hex_colors()
        }

        if self._file_path:
            GRID_MANAGER.save_to_file(self._file_path)
        with self._data_file_obj.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        raise SystemExit

    def _resize_objs(self) -> None:
        """Resizes every object with the resize method."""

        win_ratio: Ratio = Ratio(
            WIN_SURF.get_width() / INIT_WIN_SIZE.w, WIN_SURF.get_height() / INIT_WIN_SIZE.h
        )

        for state_objs in self._active_objs + self._inactive_objs:
            for obj in state_objs:
                if hasattr(obj, "resize"):
                    obj.resize(win_ratio)

        post_resize_objs: list[Any] = [
            obj
            for state_objs in self._active_objs + self._inactive_objs
            for obj in state_objs
            if hasattr(obj, "post_resize")
        ]

        for obj in post_resize_objs:
            obj.post_resize()

    def _add_to_keys(self, k: int) -> None:
        """
        Adds a key to the pressed_keys if it"s not using alt.

        Args:
            key
        """

        converted_k: int = k
        if k in NUMPAD_MAP:
            numpad_map_i: int = int(bool(pg.key.get_mods() & pg.KMOD_NUM))
            converted_k = NUMPAD_MAP[k][numpad_map_i]

        if not (pg.key.get_mods() & pg.KMOD_ALT) or (converted_k < pg.K_0 or converted_k > pg.K_9):
            self._pressed_keys.append(k)
        else:
            self._alt_k += chr(converted_k)
            if int(self._alt_k) > CHR_LIMIT:
                self._alt_k = self._alt_k[-1]

            self._alt_k = self._alt_k.lstrip("0")
        self._last_k_input_time = 0

    def _handle_key_press(self, k: int) -> None:
        """
        Handles key presses.

        Args:
            key
        """

        self._add_to_keys(k)
        if k == pg.K_ESCAPE:
            self._close()
        elif k == pg.K_F1:
            WIN.size = WIN.minimum_size
            WIN.set_windowed()
            self._is_fullscreen = False
            self._resize_objs()
        elif k == pg.K_F11:
            # Triggers the VIDEORESIZE event, calling resize_objs is unnecessary
            if self._is_fullscreen:
                WIN.set_windowed()
            else:
                WIN.set_fullscreen(True)
            self._is_fullscreen = not self._is_fullscreen

    def _refine_keys(self) -> None:
        """Refines keyboard inputs."""

        self._timed_keys.clear()
        if pg.time.get_ticks() - self._last_k_input_time >= 100:
            numpad_map_i: int = int(bool(pg.key.get_mods() & pg.KMOD_NUM))
            self._timed_keys = [
                NUMPAD_MAP[k][numpad_map_i] if k in NUMPAD_MAP else k for k in self._pressed_keys
            ]
            self._last_k_input_time = pg.time.get_ticks()

        if not (pg.key.get_mods() & pg.KMOD_ALT) and self._alt_k:
            self._timed_keys.append(int(self._alt_k))
            self._alt_k = ""

    def _zoom_objs(self, amount: int) -> None:
        """
        Zooms objects with that behavior.

        Args:
            amount
        """

        should_reach_limit: list[bool] = [False, False]
        if self._kmod_ctrl:
            if pg.K_MINUS in self._timed_keys:
                amount = 1
                should_reach_limit[0] = bool(pg.key.get_mods() & pg.KMOD_SHIFT)
            if pg.K_PLUS in self._timed_keys:
                amount = -1
                should_reach_limit[1] = bool(pg.key.get_mods() & pg.KMOD_SHIFT)

        if amount:
            GRID_MANAGER.zoom(amount, BRUSH_SIZES.clicked_i + 1, should_reach_limit)

    def _handle_events(self) -> None:
        """Handles events."""

        zoom_amount: int = 0
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self._close()
            elif event.type == pg.VIDEORESIZE:
                self._resize_objs()
            elif event.type == pg.MOUSEWHEEL:
                zoom_amount = event.y
            elif event.type == pg.KEYDOWN:
                self._handle_key_press(event.key)
            elif event.type == pg.KEYUP and event.key in self._pressed_keys:
                self._pressed_keys.remove(event.key)
            elif event.type == FPSUPDATE:
                fps_text: str = "FPS: " + str(round(CLOCK.get_fps(), 2))
                FPS_TEXT_LABEL.set_text(fps_text)

        self._kmod_ctrl = pg.key.get_mods() & pg.KMOD_CTRL
        self._refine_keys()
        self._zoom_objs(zoom_amount)

    def _resize_with_keys(self) -> None:
        """Resizes the window trough keys."""

        win_w: int = WIN_SURF.get_width()
        win_h: int = WIN_SURF.get_height()
        if pg.K_F5 in self._timed_keys:
            win_w -= 1
        if pg.K_F6 in self._timed_keys:
            win_w += 1
        if pg.K_F7 in self._timed_keys:
            win_h -= 1
        if pg.K_F8 in self._timed_keys:
            win_h += 1

        WIN.size = (win_w, win_h)
        self._resize_objs()

    def _get_hovered_obj(self, mouse_xy: PosPair) -> None:
        """
        Gets the hovered object.

        Args:
            mouse position
        """

        self._hovered_obj = None

        max_hovered_layer: int = BG_LAYER
        for obj in self._active_objs[self._state]:
            if hasattr(obj, "get_hovering_info"):
                is_hovering: bool
                obj_layer: int
                is_hovering, obj_layer = obj.get_hovering_info(mouse_xy)
                if is_hovering and obj_layer >= max_hovered_layer:
                    self._hovered_obj = obj
                    max_hovered_layer = obj_layer

    def _upt_ui_openers(self) -> None:
        """Updates the buttons that open UIs."""

        is_add_color_clicked: bool = ADD_COLOR.upt(self._hovered_obj, self._mouse_info)
        is_ctrl_a_pressed: bool = bool(self._kmod_ctrl and pg.K_a in self._timed_keys)
        if is_add_color_clicked or is_ctrl_a_pressed:
            self._state = STATE_COLOR
            COLOR_PICKER.set_color(BLACK)

        is_modify_grid_clicked: bool = MODIFY_GRID.upt(self._hovered_obj, self._mouse_info)
        is_ctrl_m_pressed: bool = bool(self._kmod_ctrl and pg.K_m in self._timed_keys)
        if is_modify_grid_clicked or is_ctrl_m_pressed:
            self._state = STATE_GRID
            GRID_UI.set_info(GRID_MANAGER.grid.area, GRID_MANAGER.grid.tiles)

    def _upt_file_saving(self) -> None:
        """Updates the save as button."""

        is_save_as_clicked: bool = SAVE_AS.upt(self._hovered_obj, self._mouse_info)
        is_ctrl_s_pressed: bool = bool(self._kmod_ctrl and pg.K_s in self._timed_keys)
        if is_save_as_clicked or is_ctrl_s_pressed:
            self._leave_state(self._state)
            self._draw()  # Applies the leave method changes since tkinter stops the execution

            file_path: str = ask_save_to_file()
            if file_path:
                self._file_path = GRID_MANAGER.save_to_file(file_path)

    def _upt_file_opening(self) -> None:
        """Updates the open file button."""

        is_open_clicked: bool = OPEN.upt(self._hovered_obj, self._mouse_info)
        is_ctrl_o_pressed: bool = bool(self._kmod_ctrl and pg.K_o in self._timed_keys)
        if is_open_clicked or is_ctrl_o_pressed:
            self._leave_state(self._state)
            self._draw()  # Applies the leave method changes since tkinter stops the execution

            file_path: str = ask_open_file()
            if file_path:
                if self._file_path:
                    self._file_path = GRID_MANAGER.save_to_file(self._file_path)

                self._file_path = file_path
                self._state = STATE_GRID
                img: pg.Surface = get_img(self._file_path)
                GRID_UI.set_info(GRID_MANAGER.grid.area, get_pixels(img))
                self._is_opening_file = True

    def _upt_file_closing(self) -> None:
        """Updates the close file button."""

        is_close_clicked: bool = CLOSE.upt(self._hovered_obj, self._mouse_info)
        is_ctrl_q_pressed: bool = bool(self._kmod_ctrl and pg.K_q in self._timed_keys)
        if (is_close_clicked or is_ctrl_q_pressed) and self._file_path:
            GRID_MANAGER.save_to_file(self._file_path)
            self._leave_state(self._state)

            self._file_path = ""
            grid_img: Optional[pg.Surface] = get_img(self._file_path) if self._file_path else None
            GRID_MANAGER.grid.set_tiles(grid_img)

    def _crash(self, exception: Exception) -> NoReturn:
        """
        Saves the file before crashing.

        Args:
            exception
        Raises:
            exception
        """

        if not self._file_path:
            duplicate_name_counter: int = 0
            file_path: str = "new_file.png"
            while Path(file_path).exists():
                duplicate_name_counter += 1
                file_path = f"new_file_{duplicate_name_counter}.png"

            self._file_path = file_path

        grid_ratio: Optional[list[float]] = (
            [GRID_UI.values_ratio.w, GRID_UI.values_ratio.h]
            if GRID_UI.checkbox.is_checked else None
        )

        data: dict[str, Any] = {
            "file": self._file_path,
            "grid_offset": [GRID_MANAGER.grid.offset.x, GRID_MANAGER.grid.offset.y],
            "grid_area": [GRID_MANAGER.grid.area.w, GRID_MANAGER.grid.area.h],
            "grid_vis_area": [GRID_MANAGER.grid.visible_area.w, GRID_MANAGER.grid.visible_area.h],
            "brush_size_i": BRUSH_SIZES.clicked_i,
            "color_i": PALETTE_MANAGER.colors_grid.clicked_i,
            "tool_i": TOOLS_MANAGER.tools_grid.clicked_i,
            "grid_ratio": grid_ratio,
            "colors": _get_hex_colors()
        }

        GRID_MANAGER.save_to_file(self._file_path)
        with self._data_file_obj.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        raise exception

    def _main_interface(self) -> None:
        """Handles the main interface."""

        brush_size: int = BRUSH_SIZES.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        ) + 1

        color: Color
        color_to_edit: Optional[Color]
        color, color_to_edit = PALETTE_MANAGER.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        )
        if color_to_edit:
            self._state = STATE_COLOR
            COLOR_PICKER.set_color(color_to_edit)

        tool_info: ToolInfo = TOOLS_MANAGER.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        )
        GRID_MANAGER.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys, color, brush_size, tool_info
        )

        self._upt_ui_openers()
        self._upt_file_saving()
        self._upt_file_opening()
        self._upt_file_closing()

        if self._kmod_ctrl:  # Independent shortcuts
            for i in range(len(BRUSH_SIZES.checkboxes)):  # Check for keys 1 - max brush size
                if pg.K_1 + i in self._timed_keys:
                    BRUSH_SIZES.check(i)

    def _color_ui(self) -> None:
        """Handles the color UI."""

        is_ui_closed: bool
        future_color: Optional[Color]
        is_ui_closed, future_color = COLOR_PICKER.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        )
        if is_ui_closed:
            PALETTE_MANAGER.add(future_color)
            self._state = STATE_MAIN

    def _grid_ui(self) -> None:
        """Handles the grid UI."""

        is_ui_closed: bool
        future_area: Optional[Size]
        is_ui_closed, future_area = GRID_UI.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        )
        if is_ui_closed:
            pointer_offset: Optional[Point] = GRID_MANAGER.grid.offset
            pointer_visible_area: Optional[Size] = GRID_MANAGER.grid.visible_area
            GRID_MANAGER.set_info(pointer_offset, future_area, pointer_visible_area)

            if not self._is_opening_file:
                GRID_MANAGER.grid.update_full()
            else:
                grid_img: Optional[pg.Surface] = (
                    get_img(self._file_path) if self._file_path else None
                )
                GRID_MANAGER.grid.set_tiles(grid_img)
                self._is_opening_file = False

            self._state = STATE_MAIN

    def _handle_states(self) -> None:
        """Handles updating and leaving states."""

        prev_state: int = self._state
        if self._state == STATE_MAIN:
            self._main_interface()
        elif self._state == STATE_COLOR:
            self._color_ui()
        elif self._state == STATE_GRID:
            self._grid_ui()

        if self._state != prev_state:
            self._leave_state(prev_state)

    def run(self) -> None:
        """Game loop."""

        WIN.show()
        try:
            while True:
                CLOCK.tick(60)
                self._handle_events()

                resizing_keys: tuple[int, int, int, int] = (pg.K_F5, pg.K_F6, pg.K_F7, pg.K_F8)
                if not self._is_fullscreen and any(k in self._timed_keys for k in resizing_keys):
                    self._resize_with_keys()

                # When the mouse is off the window its position is (0, 0)
                mouse_xy: PosPair = pg.mouse.get_pos() if pg.mouse.get_focused() else (-1, -1)
                self._mouse_info = MouseInfo(
                    *mouse_xy, pg.mouse.get_pressed(), pg.mouse.get_just_released()
                )

                self._get_objs()
                self._get_hovered_obj(mouse_xy)
                self._handle_states()

                self._draw()
        except KeyboardInterrupt:
            self._close()
        except Exception as e:
            self._crash(e)


if __name__ == "__main__":
    Dixel().run()
