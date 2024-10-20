"""
Drawing program for pixel art
"""

'''
INFO:

There are three states, the main interface and 2 extra UI windows
that can be opened by clicking their respective button

Keyboard input:
    Every key that's currently pressed is in a tuple, accidental spamming is prevented
    by temporarily clearing this tuple when a key is held and reverting it back for
    one frame every 100ms

Mouse info:
    Mouse info is contained in a dataclass that tracks:
    x and y position, pressed buttons and recently released ones (for clicking elements)

Sub objects:
    Objects may have objects info for sub objects,
    they're retrieved at the start of each frame and automatically call the methods below

Blitting:
    The blit method returns a list with one or more groups of image, position and layer
    objects with an higher layer will be blitted on top of objects with a lower one

    There are 4 layer types:
        background: background elements and grid
        element: UI elements that can be interacted with
        text: normal text labels
        top: elements that aren't always present like hovering text or a cursor in an input box

    Layers can also be extended into the special group,
    they will still keep their hierarchy so special top goes on top of special text and so on
    but every special layer goes on top of any normal one,
    it's used for stuff like drop-down menus that appear on right click
    The UI group extends the special group in a similar way,
    used for the UI windows of other states

Hover checking:
    The check_hovering method takes the mouse info and
    returns the object that it's being hovered and its layer,
    only one object can be hovered at a time,
    if there's more than one it will be chose the one with the highest layer

Leaving a state:
    The leave method gets called when the state changes
    and clears all the relevant data, like the selected pixels of the grid or
    the hovering flag for clickables, responsible for showing hovering text

Window resizing:
    The resize method scales positions and images manually because
    blitting everything on a surface, scaling it to match the window size and blitting it
    removes text anti aliasing , causes 1 pixel offsets on some elements at specific sizes, is slow
    and doesn't allow for custom behavior on some objects
    pygame.SCALED doesn't scale position and images

Interacting with elements:
    Interaction is possible with the upt method
'''

'''
TODO:
- save current colors along with the image
- slider is faster when moving the mouse faster
- consistent cursor_i across different NumInputBox
- option to change the palette to match the current colors/multiple palettes
- CTRL Z/Y (store without alpha channel, UI to view history)
- option to make drawing only affect the visible_area?
- better mouse sprite handling (if switching objects between frames it won't always be right)

- COLOR_PICKER:
    - hex_text as NumInputBox

- GRID_UI:
    - add option to resize in order to fit image
    - separate minimap from grid and place minimap in grid UI
    - option to change visible_area?
    - move image before resizing?
    - change mouse sprite when using a slider?
    - if checkbox is on, the current slider text is empty and the opp_slider value is 1
    the opp_slider text should be empty

- TOOLS_MANAGER:
    - brush (different shapes?)
    - fill (change all pixels of the same color to the one in use)
    - pick color
    - draw line (pixelated?)
    - draw rectangle (auto fill)
    - draw circle, semi circle and ellipse (auto fill, pixelated?)
    - copy and paste (flip and rotate?)
    - move, flip or rotate section (affects all grid)
    - change brightness of pixel/area
    - scale section

optimizations:
    - general:
        - scale large images with Pillow
        - use pygame.surfarray.blit_array instead of nested for loops and fblits
    - GRID_UI: get_preview
    - GRID_MANAGER: update_section (precalculate section_indicator?)
'''

import pygame as pg
from tkinter import Tk, filedialog
from PIL import Image
from pathlib import Path
import sys
from typing import Final, Optional, Any, NoReturn

from src.classes.grid_manager import GridManager
from src.classes.palette_manager import PaletteManager
from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, Size, ObjInfo, MouseInfo, load_img_from_path, get_pixels
from src.type_utils import ColorType, ToolInfo, BlitSequence, LayeredBlitInfo, LayeredBlitSequence
from src.consts import CHR_LIMIT, INIT_WIN_SIZE, BLACK

pg.init()

EXTRA_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE
INIT_WIN: Final[pg.Surface] = pg.display.set_mode(
    (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h), pg.RESIZABLE | EXTRA_FLAGS
)
pg.display.set_caption("Dixel")
pg.display.set_icon(load_img_from_path("sprites", "icon.png"))

# These files load images at the start which require pygame to be already initialized
from src.classes.grid_ui import GridUI
from src.classes.color_ui import ColorPicker
from src.classes.ui import BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG
from src.classes.tools_manager import ToolsManager

BUTTON_S_OFF_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_OFF_IMG, (64, 32))
BUTTON_S_ON_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_ON_IMG, (64, 32))

NumPadKeys = dict[int, tuple[int, int]]
NUM_PAD_KEYS: Final[NumPadKeys] = {
    pg.K_KP_0: (pg.K_INSERT, pg.K_0), pg.K_KP_1: (pg.K_END, pg.K_1),
    pg.K_KP_2: (pg.K_DOWN, pg.K_2), pg.K_KP_3: (pg.K_PAGEDOWN, pg.K_3),
    pg.K_KP_4: (pg.K_LEFT, pg.K_4), pg.K_KP_5: (0, pg.K_5),
    pg.K_KP_6: (pg.K_RIGHT, pg.K_6), pg.K_KP_7: (pg.K_HOME, pg.K_7),
    pg.K_KP_8: (pg.K_UP, pg.K_8), pg.K_KP_9: (pg.K_PAGEUP, pg.K_9),
    pg.K_KP_PERIOD: (pg.K_DELETE, pg.K_PERIOD)  # Others aren't needed
}

ADD_COLOR: Final[Button] = Button(
    RectPos(INIT_WIN_SIZE.w - 25, INIT_WIN_SIZE.h - 25, 'bottomright'),
    (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "add color", "(CTRL+A)"
)
MODIFY_GRID: Final[Button] = Button(
    RectPos(ADD_COLOR.rect.x - 10, ADD_COLOR.rect.y, 'topright'),
    (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "modify grid", "(CTRL+M)"
)

SAVE_AS: Final[Button] = Button(
    RectPos(0, 0, 'topleft'), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    "save as", "(CTRL+S)", text_h=15
)
OPEN: Final[Button] = Button(
    RectPos(SAVE_AS.rect.right, 0, 'topleft'), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    "open file", "(CTRL+O)", text_h=15
)
CLOSE: Final[Button] = Button(
    RectPos(OPEN.rect.right, 0, 'topleft'), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    "close file", "(CTRL+Q)", text_h=15
)

GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(round(INIT_WIN_SIZE.w / 2.0), round(INIT_WIN_SIZE.h / 2.0), 'center'),
    RectPos(INIT_WIN_SIZE.w - 10, 10, 'topright')
)

BRUSH_SIZES_INFO: tuple[tuple[pg.Surface, str], ...] = tuple(
    (load_img_from_path("sprites", f"size_{n}_off.png"), f"{n}px\n(CTRL+{n})") for n in range(1, 6)
)
BRUSH_SIZES: Final[CheckboxGrid] = CheckboxGrid(
    RectPos(10, SAVE_AS.rect.bottom + 10, 'topleft'), BRUSH_SIZES_INFO, len(BRUSH_SIZES_INFO),
    (False, False)
)

PALETTE_MANAGER: Final[PaletteManager] = PaletteManager(
    RectPos(INIT_WIN_SIZE.w - 75, ADD_COLOR.rect.y - 25, 'bottomright'),
    (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG)
)

TOOLS_MANAGER: Final[ToolsManager] = ToolsManager(
    RectPos(10, INIT_WIN_SIZE.h - 10, 'bottomleft')
)

FPS_TEXT_LABEL: Final[TextLabel] = TextLabel(
    RectPos(round(INIT_WIN_SIZE.w / 2.0), 0, 'midtop'), "FPS: 0"
)

COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(round(INIT_WIN_SIZE.w / 2.0), round(INIT_WIN_SIZE.h / 2.0), 'center'),
    PALETTE_MANAGER.values[0]
)
GRID_UI: Final[GridUI] = GridUI(
    RectPos(round(INIT_WIN_SIZE.w / 2.0), round(INIT_WIN_SIZE.h / 2.0), 'center'),
    GRID_MANAGER.grid.area
)

MultiStateObjInfo = tuple[list[ObjInfo], ...]
MAIN_OBJS_INFO: Final[MultiStateObjInfo] = (  # Grouped by state
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

FPSUPDATE: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPSUPDATE, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()


def convert_k_from_num_pad(k: int) -> int:
    """
    Converts a num pad key into into its normal equivalent
    Args:
        k
    Returns:
        k
    """

    if k not in NUM_PAD_KEYS:
        return k

    is_num_pad_on: bool = bool(pg.key.get_mods() & pg.KMOD_NUM)

    return NUM_PAD_KEYS[k][int(is_num_pad_on)]


def handle_path_from_args() -> Path:
    """
    Handles file opening with cmd args
    Returns:
        path object
    """

    new_file_path: Path = Path(' '.join(sys.argv[1:]))
    if new_file_path.suffix != '.png':
        new_file_path = new_file_path.with_suffix('.png')

    if not new_file_path.is_file():
        if not new_file_path.parent.is_dir():
            print("Invalid directory.")
        else:
            new_file_img: Image.Image = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            try:
                new_file_img.save(new_file_path)
            except PermissionError:
                print("Permission denied.")

    return new_file_path


class Dixel:
    """
    Drawing program for pixel art
    """

    __slots__ = (
        '_win_restore_size', '_main_win_flag', '_is_fullscreen', '_win', '_mouse_info',
        '_pressed_keys', '_timed_keys', '_k_input_elapsed_time', '_alt_k', '_kmod_ctrl',
        '_state', '_active_objs', '_inactive_objs', '_hovered_obj',
        '_data_file', '_file_path', '_is_opening_file'
    )

    def __init__(self) -> None:
        """
        Initializes the window
        """

        self._win_restore_size: tuple[int, int] = INIT_WIN_SIZE.wh
        self._main_win_flag: int = pg.RESIZABLE
        self._is_fullscreen: bool = False
        self._win: pg.Surface = INIT_WIN

        self._mouse_info: MouseInfo = MouseInfo(
            *pg.mouse.get_pos(), pg.mouse.get_pressed(), pg.mouse.get_just_released()
        )

        self._pressed_keys: list[int] = []
        self._timed_keys: list[int] = self._pressed_keys.copy()
        self._k_input_elapsed_time: int = pg.time.get_ticks()
        self._alt_k: str = ''
        self._kmod_ctrl: int = 0

        '''
        0 = main interface
        1 = color ui
        2 = grid ui
        '''

        self._state: int = 0

        self._active_objs: list[list[Any]] = []
        self._inactive_objs: list[list[Any]] = []
        self._hovered_obj: Any = None

        self._data_file: Path = Path("data.txt")
        self._file_path: str = ''
        self._is_opening_file: bool = False

        new_file_path: Path
        if len(sys.argv) != 1:
            new_file_path = handle_path_from_args()
        elif self._data_file.is_file():
            with self._data_file.open(encoding='utf-8') as f:
                new_file_path = Path(f.read())

        if new_file_path.is_file():
            self._file_path = str(new_file_path)
        GRID_MANAGER.load_from_path(self._file_path, GRID_MANAGER.grid.area)
        PALETTE_MANAGER.load_from_arr(GRID_MANAGER.grid.pixels)

    def _draw(self) -> None:
        """
        Draws objects on the screen
        """

        self._win.fill(BLACK)

        main_sequence: LayeredBlitSequence = []

        blittable_objs: list[Any] = self._active_objs[0].copy()
        if self._state:
            blittable_objs.extend(self._active_objs[self._state])

        for obj in blittable_objs:
            if hasattr(obj, "blit"):
                main_sequence.extend(obj.blit())

        def get_layer(layered_blit_info: LayeredBlitInfo) -> int:
            return layered_blit_info[2]

        main_sequence.sort(key=get_layer)
        blit_sequence: BlitSequence = [(img, pos) for img, pos, _ in main_sequence]

        self._win.fblits(blit_sequence)
        pg.display.flip()

    def _get_objs(self) -> None:
        """
        Gets active and inactive objects
        """

        objs_info: list[list[ObjInfo]] = []
        for state_info in MAIN_OBJS_INFO:
            state_list: list[ObjInfo] = state_info.copy()
            for info in state_list:
                if hasattr(info.obj, "objs_info"):
                    state_list.extend(info.obj.objs_info)
            objs_info.append(state_list)

        self._active_objs = [
            [info.obj for info in state_info if info.is_active]
            for state_info in objs_info
        ]
        self._inactive_objs = [
            [info.obj for info in state_info if not info.is_active]
            for state_info in objs_info
        ]

    def _leave(self, prev_state: int) -> None:
        """
        Clears all the relevant data when leaving a state
        Args:
            previous state
        """

        for obj in self._active_objs[prev_state]:
            if hasattr(obj, "leave"):
                obj.leave()

        self._get_objs()
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

    def _close(self) -> None:
        """
        Saves the file and closes the program
        """

        if self._file_path:
            new_file_img: Image.Image = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            new_file_img.save(self._file_path)
        with self._data_file.open('w', encoding='utf-8') as f:
            f.write(self._file_path)

        sys.exit()

    def _resize(self) -> None:
        """
        Resizes the object
        """

        win_ratio: tuple[float, float] = (
            self._win.get_width() / INIT_WIN_SIZE.w, self._win.get_height() / INIT_WIN_SIZE.h
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

    def _handle_key_press(self, k: int) -> None:
        """
        Handles key presses
        Args:
            key
        """

        converted_k: int = convert_k_from_num_pad(k)
        if (pg.key.get_mods() & pg.KMOD_ALT) and pg.K_0 <= converted_k <= pg.K_9:
            self._alt_k += chr(converted_k)
            if int(self._alt_k) > CHR_LIMIT:
                self._alt_k = chr(converted_k)

            self._alt_k = self._alt_k.lstrip('0')

        # TODO: don't insert if alt
        self._pressed_keys.append(k)
        self._k_input_elapsed_time = 0

        if converted_k == pg.K_ESCAPE:
            self._close()
        elif converted_k == pg.K_F1:
            self._main_win_flag = pg.RESIZABLE
            self._is_fullscreen = False
            self._win = pg.display.set_mode(INIT_WIN_SIZE.wh, self._main_win_flag | EXTRA_FLAGS)

            self._resize()
        elif converted_k == pg.K_F11:
            self._is_fullscreen = not self._is_fullscreen

            if not self._is_fullscreen:
                '''
                Exiting full screen triggers the VIDEORESIZE event
                so the resize method is not necessary
                '''

                self._main_win_flag = pg.RESIZABLE
                self._win = pg.display.set_mode(
                    self._win_restore_size, self._main_win_flag | EXTRA_FLAGS
                )
            else:
                self._main_win_flag = pg.FULLSCREEN
                self._win_restore_size = self._win.get_size()
                # A window of size (0, 0) becomes of the monitor's size
                self._win = pg.display.set_mode(flags=self._main_win_flag | EXTRA_FLAGS)

                self._resize()

    def _refine_keys(self) -> None:
        """
        Refines keyboard inputs
        """

        self._timed_keys = []
        if pg.time.get_ticks() - self._k_input_elapsed_time >= 100:
            self._timed_keys = [convert_k_from_num_pad(k) for k in self._pressed_keys]
            self._k_input_elapsed_time = pg.time.get_ticks()

        if not (pg.key.get_mods() & pg.KMOD_ALT) and self._alt_k:
            self._timed_keys.append(int(self._alt_k))
            self._alt_k = ''

    def _resize_with_keys(self) -> None:
        """
        Resizes the window trough keys
        """

        resizing_keys: tuple[int, ...] = (pg.K_F5, pg.K_F6, pg.K_F7, pg.K_F8)
        if self._is_fullscreen or not any(k in self._timed_keys for k in resizing_keys):
            return

        win_w: int
        win_h: int
        win_w, win_h = self._win.get_size()

        if pg.K_F5 in self._timed_keys:
            win_w = max(win_w - 1, INIT_WIN_SIZE.w)
        if pg.K_F6 in self._timed_keys:
            win_w += 1
        if pg.K_F7 in self._timed_keys:
            win_h = max(win_h - 1, INIT_WIN_SIZE.h)
        if pg.K_F8 in self._timed_keys:
            win_h += 1

        self._win = pg.display.set_mode(
            (win_w, win_h), self._main_win_flag | EXTRA_FLAGS
        )
        self._resize()

    def _zoom_objs(self, amount: int) -> None:
        """
        Zooms objects with that behavior
        Args:
            amount
        """

        reach_limit: list[bool] = [False, False]
        if self._kmod_ctrl:
            if pg.K_MINUS in self._timed_keys:
                amount = 1
                reach_limit[0] = bool(pg.key.get_mods() & pg.KMOD_SHIFT)
            if pg.K_PLUS in self._timed_keys:
                amount = -1
                reach_limit[1] = bool(pg.key.get_mods() & pg.KMOD_SHIFT)

        if amount:
            GRID_MANAGER.zoom(amount, BRUSH_SIZES.clicked_i + 1, reach_limit)

    def _handle_events(self) -> None:
        """
        Handles events
        """

        zoom_amount: int = 0
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self._close()
            elif event.type == pg.VIDEORESIZE:
                win_size: tuple[int, int] = (
                    max(event.w, INIT_WIN_SIZE.w), max(event.h, INIT_WIN_SIZE.h)
                )
                self._win = pg.display.set_mode(win_size, self._main_win_flag | EXTRA_FLAGS)

                self._resize()
            elif event.type == pg.MOUSEWHEEL:
                zoom_amount = event.y
            elif event.type == pg.KEYDOWN:
                self._handle_key_press(event.key)
            elif event.type == pg.KEYUP:
                self._pressed_keys.remove(event.key)
            elif event.type == FPSUPDATE:
                FPS_TEXT_LABEL.set_text("FPS: " + str(round(CLOCK.get_fps(), 2)))

        self._kmod_ctrl = pg.key.get_mods() & pg.KMOD_CTRL
        self._refine_keys()
        self._resize_with_keys()
        self._zoom_objs(zoom_amount)

    def _get_hovered_obj(self, mouse_pos: tuple[int, int]) -> None:
        """
        Gets the hovered object
        Args:
            mouse position
        """

        self._hovered_obj = None

        max_hovered_layer: int = 0
        for obj in self._active_objs[self._state]:
            if hasattr(obj, "check_hovering"):
                hovered_obj: Any
                hovered_layer: int
                hovered_obj, hovered_layer = obj.check_hovering(mouse_pos)
                if hovered_obj and hovered_layer >= max_hovered_layer:
                    self._hovered_obj = hovered_obj
                    max_hovered_layer = hovered_layer

    def _handle_ui_openers(self) -> None:
        """
        Handles the buttons that open uis
        """

        ctrl_a: bool = bool(self._kmod_ctrl and pg.K_a in self._timed_keys)
        if ADD_COLOR.upt(self._hovered_obj, self._mouse_info) or ctrl_a:
            self._state = 1
            COLOR_PICKER.set_color(BLACK)

        ctrl_m: bool = bool(self._kmod_ctrl and pg.K_m in self._timed_keys)
        if MODIFY_GRID.upt(self._hovered_obj, self._mouse_info) or ctrl_m:
            self._state = 2
            GRID_UI.set_size(GRID_MANAGER.grid.area, GRID_MANAGER.grid.pixels)

    def _handle_file_saving(self) -> None:
        """
        Handles the save as button
        """

        ctrl_s: bool = bool(self._kmod_ctrl and pg.K_s in self._timed_keys)
        if SAVE_AS.upt(self._hovered_obj, self._mouse_info) or ctrl_s:
            '''
            Applies the leave method changes immediately
            because the tkinter window stops the execution
            '''

            self._leave(self._state)
            self._draw()

            tk_root: Tk = Tk()
            tk_root.withdraw()
            new_file_path: str = filedialog.asksaveasfilename(
                defaultextension='.png', filetypes=(("png Files", '*.png'),), title="Save as"
            )
            tk_root.destroy()

            if new_file_path:
                self._file_path = new_file_path
                new_file_img: Image.Image = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                new_file_img.save(self._file_path)

    def _handle_file_opening(self) -> None:
        """
        Handles the open file button
        """

        ctrl_o: bool = bool(self._kmod_ctrl and pg.K_o in self._timed_keys)
        if OPEN.upt(self._hovered_obj, self._mouse_info) or ctrl_o:
            if self._file_path:
                new_file_img: Image.Image = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                new_file_img.save(self._file_path)

            '''
            Applies the leave method changes immediately
            because the tkinter window stops the execution
            '''

            self._leave(self._state)
            self._draw()

            tk_root: Tk = Tk()
            tk_root.withdraw()
            new_file_path: str = filedialog.askopenfilename(
                defaultextension='.png', filetypes=(("png Files", '*.png'),), title="Open"
            )
            tk_root.destroy()

            if new_file_path:
                self._file_path = new_file_path

                self._state = 2
                img: pg.Surface = load_img_from_path(self._file_path)
                GRID_UI.set_size(GRID_MANAGER.grid.area, get_pixels(img))
                self._is_opening_file = True

    def _handle_file_closing(self) -> None:
        """
        Handles the close file button
        """

        ctrl_q: bool = bool(self._kmod_ctrl and pg.K_q in self._timed_keys)
        if (CLOSE.upt(self._hovered_obj, self._mouse_info) or ctrl_q) and self._file_path:
            new_file_img: Image.Image = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            new_file_img.save(self._file_path)
            self._leave(self._state)

            self._file_path = ''
            GRID_MANAGER.load_from_path(self._file_path, GRID_MANAGER.grid.area)
            PALETTE_MANAGER.load_from_arr(GRID_MANAGER.grid.pixels)

    def _crash(self, exception: Exception) -> NoReturn:
        """
        Saves the file before crashing
        Args:
            exception
        Raises:
            exception
        """

        if not self._file_path:
            duplicate_name_counter: int = 0
            new_file_name: str = "new_file.png"
            while Path(new_file_name).exists():
                duplicate_name_counter += 1
                new_file_name = f"new_file_{duplicate_name_counter}.png"
            self._file_path = new_file_name

        new_file_img: Image.Image = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
        new_file_img.save(self._file_path)
        with self._data_file.open('w', encoding='utf-8') as f:
            f.write(self._file_path)

        raise exception

    def _main_interface(self) -> None:
        """
        Handles the main interface
        """

        brush_size: int = BRUSH_SIZES.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        ) + 1

        color: ColorType
        color_to_edit: Optional[ColorType]
        color, color_to_edit = PALETTE_MANAGER.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        )
        if color_to_edit:
            self._state = 1
            COLOR_PICKER.set_color(color_to_edit)

        tool_info: ToolInfo = TOOLS_MANAGER.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        )

        GRID_MANAGER.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys, color,
            brush_size, tool_info
        )

        self._handle_ui_openers()
        self._handle_file_saving()
        self._handle_file_opening()
        self._handle_file_closing()

        if self._kmod_ctrl:  # Independent shortcuts
            # Check if keys 1 - max brush size are pressed
            for i in range(len(BRUSH_SIZES.checkboxes)):
                if pg.K_1 + i in self._timed_keys:
                    BRUSH_SIZES.check(i)

    def _color_ui(self) -> None:
        """
        Handles the color UI
        """

        is_ui_closed: bool
        new_color: Optional[ColorType]
        is_ui_closed, new_color = COLOR_PICKER.upt(
            self._hovered_obj, self._mouse_info, self._timed_keys
        )
        if is_ui_closed:
            PALETTE_MANAGER.add(new_color)
            self._state = 0

    def _grid_ui(self) -> None:
        """
        Handles the grid UI
        """

        is_ui_closed: bool
        new_area: Optional[Size]
        is_ui_closed, new_area = GRID_UI.upt(self._hovered_obj, self._mouse_info, self._timed_keys)
        if is_ui_closed:
            if not self._is_opening_file:
                GRID_MANAGER.set_size(new_area)
            else:
                GRID_MANAGER.load_from_path(self._file_path, new_area)
                PALETTE_MANAGER.load_from_arr(GRID_MANAGER.grid.pixels)
                self._is_opening_file = False
            self._state = 0

    def run(self) -> None:
        """
        Game loop
        """

        try:
            while True:
                CLOCK.tick(60)
                self._handle_events()

                '''
                When the mouse is off the window it's x and y positions are 0,
                it can cause wrong hovering
                '''

                mouse_pos: tuple[int, int] = (
                    pg.mouse.get_pos() if pg.mouse.get_focused() else (-1, -1)
                )
                self._mouse_info = MouseInfo(
                    *mouse_pos, pg.mouse.get_pressed(), pg.mouse.get_just_released()
                )

                self._get_objs()
                self._get_hovered_obj(mouse_pos)

                prev_state: int = self._state
                match self._state:
                    case 0:
                        self._main_interface()
                    case 1:
                        self._color_ui()
                    case 2:
                        self._grid_ui()

                if self._state != prev_state:
                    self._leave(prev_state)

                self._draw()
        except KeyboardInterrupt:
            self._close()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._crash(e)


if __name__ == '__main__':
    Dixel().run()
