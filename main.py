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
    The check_hover method takes the mouse info and
    returns the object that it's being hovered and its layer,
    only one object can be hovered at a time,
    if there's more than one it will be chose the one with the highest layer

Leaving a state:
    The leave method get's called when the state changes
    and clears all the relevant data, like the selected pixels of the grid or
    the hovering flag for clickables, responsible for showing hovering text

Window resizing:
    The handle_resize method scales position and image manually because
    blitting everything on a surface, scaling it to match the window size and blitting it
    removes text anti aliasing and causes 1 pixel offsets on some elements at specific sizes and
    pygame.SCALED doesn't scale position and images

Layer debugging:
    The print_layer method returns the object name, its layer and its depth in the hierarchy
    The name and layer of an object are printed in a nested hierarchy,
    if an object doesn't have a layer it will print None

    A printed element looks like this:
    brush sizes: 0
        checkbox 0: 1
                hovering text: 3
        checkbox 1: 1
                hovering text: 3
        checkbox 2: 1
                hovering text: 3
        checkbox 3: 1
                hovering text: 3
        checkbox 4: 1
                hovering text: 3

Interacting with elements:
    Interaction is possible with the upt method
'''

'''
TODO:
- open GRID_UI when opening file
- terminal arguments
- save current colors along with the image
- slider is faster when moving the mouse faster
- consistent text_i across different NumInputBox
- option to change the palette to match the current colors/multiple palettes
- CTRL Z/Y (store without alpha channel, UI to view history)
- option to make drawing only affect the visible_area?
- better mouse sprite handling (if switching objects between frame it won't always be right)

- COLOR_PICKER:
    - hex_text as NumInputBox

- GRID_UI:
    - add option to resize in order to fit image
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

debug:
    - togglable debug mode
    - view next checkbox position in CheckBoxGrid
    - view grid, minimap and GRID_UI preview info
    - view hovering_text for Clickable
    - view text_i for NumInputBox
'''

import pygame as pg
from tkinter import Tk, filedialog
from PIL import Image
from pathlib import Path
from traceback import print_exc
from typing import Final, Optional, Any

from src.classes.palette_manager import PaletteManager
from src.classes.grid_manager import GridManager
from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import Button
from src.classes.text import Text
from src.utils import RectPos, Size, ObjInfo, MouseInfo, load_img
from src.type_utils import (
    ColorType, BlitSequence, LayeredBlitInfo, LayeredBlitSequence, LayerSequence
)

from src.consts import INIT_WIN_SIZE, BLACK

pg.init()

EXTRA_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE
INIT_WIN: Final[pg.Surface] = pg.display.set_mode(
    (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h), pg.RESIZABLE | EXTRA_FLAGS
)
pg.display.set_caption('Dixel')
pg.display.set_icon(load_img('sprites', 'icon.png'))

# These files load images at the start which require pygame to be already initialized
from src.classes.grid_ui import GridUI
from src.classes.color_ui import ColorPicker
from src.classes.ui import BUTTON_M_OFF, BUTTON_M_ON
from src.classes.tools_manager import ToolsManager

BUTTON_S_OFF_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_OFF, (64, 32))
BUTTON_S_ON_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_ON, (64, 32))
DATA_FILE: Final[Path] = Path('data.txt')

ADD_COLOR: Final[Button] = Button(
    RectPos(INIT_WIN_SIZE.w - 25.0, INIT_WIN_SIZE.h - 25.0, 'bottomright'),
    (BUTTON_M_OFF, BUTTON_M_ON), 'add color', '(CTRL+A)'
)
MODIFY_GRID: Final[Button] = Button(
    RectPos(ADD_COLOR.rect.x - 10.0, ADD_COLOR.rect.y, 'topright'),
    (BUTTON_M_OFF, BUTTON_M_ON), 'modify grid', '(CTRL+M)'
)

SAVE_AS: Final[Button] = Button(
    RectPos(0.0, 0.0, 'topleft'), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    'save as', '(CTRL+S)', text_h=15
)
OPEN: Final[Button] = Button(
    RectPos(SAVE_AS.rect.right, 0.0, 'topleft'), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    'open file', '(CTRL+O)', text_h=15
)
CLOSE: Final[Button] = Button(
    RectPos(OPEN.rect.right, 0.0, 'topleft'), (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG),
    'close file', '(CTRL+Q)', text_h=15
)

GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(INIT_WIN_SIZE.w / 2.0, INIT_WIN_SIZE.h / 2.0, 'center'),
    RectPos(INIT_WIN_SIZE.w - 10.0, 10.0, 'topright')
)

BRUSH_SIZES_INFO: tuple[tuple[pg.Surface, str], ...] = tuple(
    (load_img('sprites', f'size_{n}_off.png'), f'{n}px\n(CTRL+{n})') for n in range(1, 6)
)
BRUSH_SIZES: Final[CheckBoxGrid] = CheckBoxGrid(
    RectPos(10.0, SAVE_AS.rect.bottom + 10.0, 'topleft'), BRUSH_SIZES_INFO, len(BRUSH_SIZES_INFO),
    (False, False)
)

PALETTE_MANAGER: Final[PaletteManager] = PaletteManager(
    RectPos(INIT_WIN_SIZE.w - 75.0, ADD_COLOR.rect.y - 25.0, 'bottomright'),
    (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG)
)

TOOLS_MANAGER: Final[ToolsManager] = ToolsManager(
    RectPos(10.0, INIT_WIN_SIZE.h - 10.0, 'bottomleft')
)

FPS_TEXT_LABEL: Final[Text] = Text(RectPos(INIT_WIN_SIZE.w / 2.0, 0.0, 'midtop'), 'FPS: 0')

COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(INIT_WIN_SIZE.w / 2.0, INIT_WIN_SIZE.h / 2.0, 'center'), PALETTE_MANAGER.values[0]
)

GRID_UI: Final[GridUI] = GridUI(
    RectPos(INIT_WIN_SIZE.w / 2.0, INIT_WIN_SIZE.h / 2.0, 'center'), GRID_MANAGER.grid.grid_size
)

MAIN_OBJS_INFO: Final[tuple[list[ObjInfo], ...]] = (  # Grouped by state
    [
        ObjInfo('add color', ADD_COLOR),
        ObjInfo('modify grid', MODIFY_GRID),
        ObjInfo('save as', SAVE_AS), ObjInfo('open', OPEN), ObjInfo('close', CLOSE),
        ObjInfo('grid manager', GRID_MANAGER),
        ObjInfo('brush sizes', BRUSH_SIZES),
        ObjInfo('palette manager', PALETTE_MANAGER),
        ObjInfo('tools manager', TOOLS_MANAGER),
        ObjInfo('fps text', FPS_TEXT_LABEL)
    ],
    [ObjInfo('color ui', COLOR_PICKER)],
    [ObjInfo('grid ui', GRID_UI)]
)

FPSUPDATE: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPSUPDATE, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()


class Dixel:
    """
    Drawing program for pixel art
    """

    __slots__ = (
        '_win_size', '_prev_win_size', '_main_win_flag', '_is_fullscreen', '_win', '_mouse_info',
        '_pressed_keys', '_timed_keys', '_prev_k_input', '_kmod_ctrl', '_hovered_obj', '_state',
        '_active_objs', '_inactive_objs', '_file_path'
    )

    def __init__(self) -> None:
        """
        Initializes the window
        """

        self._win_size: Size = Size(INIT_WIN_SIZE.w, INIT_WIN_SIZE.h)
        self._prev_win_size: tuple[int, int] = self._win_size.wh
        self._main_win_flag: int = pg.RESIZABLE
        self._is_fullscreen: bool = False

        self._win: pg.Surface = INIT_WIN

        self._mouse_info: MouseInfo = MouseInfo(
            *pg.mouse.get_pos(), pg.mouse.get_pressed(), pg.mouse.get_just_released()
        )

        self._pressed_keys: list[int] = []
        self._timed_keys: tuple[int, ...] = tuple(self._pressed_keys)
        self._prev_k_input: int = pg.time.get_ticks()
        self._kmod_ctrl: int = 0

        self._hovered_obj: Any = None

        '''
        0 = main interface
        1 = color ui
        2 = grid ui
        '''
        self._state: int = 0

        self._active_objs: list[list[Any]] = []
        self._inactive_objs: list[list[Any]] = []

        self._file_path: str = ''
        if DATA_FILE.is_file():
            with DATA_FILE.open(encoding='utf-8') as f:
                saved_file_path: str = f.read()

            if Path(saved_file_path).is_file():
                self._file_path = saved_file_path
                GRID_MANAGER.load_path(self._file_path)
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
            if hasattr(obj, 'blit'):
                main_sequence.extend(obj.blit())

        def get_layer(layered_blit_info: LayeredBlitInfo) -> int:
            return layered_blit_info[2]

        main_sequence.sort(key=get_layer)
        blit_sequence: BlitSequence = [(surf, pos) for surf, pos, _ in main_sequence]

        self._win.fblits(blit_sequence)
        pg.display.flip()

    def _leave(self, prev_state: int) -> None:
        """
        Clears all the relevant data when leaving a state
        Args:
            previous state
        """

        for obj in self._active_objs[prev_state]:
            if hasattr(obj, 'leave'):
                obj.leave()

        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

    def _handle_resize(self) -> None:
        """
        Resizes the object
        """

        win_ratio_w: float = self._win_size.w / INIT_WIN_SIZE.w
        win_ratio_h: float = self._win_size.h / INIT_WIN_SIZE.h

        post_resize_objs: list[Any] = []
        for state in self._active_objs + self._inactive_objs:
            for obj in state:
                if hasattr(obj, 'handle_resize'):
                    obj.handle_resize(win_ratio_w, win_ratio_h)
                if hasattr(obj, 'post_resize'):
                    post_resize_objs.append(obj)

        for obj in post_resize_objs:
            obj.post_resize()

    def _handle_keys(self, k: int) -> None:
        """
        Handles keyboard inputs
        Args:
            key
        Raises:
            KeyboardInterrupt when esc is pressed
        """

        self._pressed_keys.append(k)
        self._prev_k_input = 0
        self._kmod_ctrl = pg.key.get_mods() & pg.KMOD_CTRL

        if k == pg.K_ESCAPE:
            raise KeyboardInterrupt

        if k == pg.K_F1:
            self._win_size.w, self._win_size.h = INIT_WIN_SIZE.w, INIT_WIN_SIZE.h
            self._main_win_flag = pg.RESIZABLE
            self._is_fullscreen = False
            self._win = pg.display.set_mode(self._win_size.wh, self._main_win_flag | EXTRA_FLAGS)

            self._handle_resize()
        elif k == pg.K_F11:
            self._is_fullscreen = not self._is_fullscreen

            if not self._is_fullscreen:
                '''
                Exiting full screen triggers the VIDEORESIZE event
                so the handle_resize method is not necessary
                '''

                self._win_size.w, self._win_size.h = self._prev_win_size
                self._main_win_flag = pg.RESIZABLE
                self._win = pg.display.set_mode(
                    self._win_size.wh, self._main_win_flag | EXTRA_FLAGS
                )
            else:
                self._main_win_flag = pg.FULLSCREEN
                # A window of size (0, 0) becomes of the monitor's size
                self._win = pg.display.set_mode(flags=self._main_win_flag | EXTRA_FLAGS)
                self._prev_win_size = self._win_size.wh
                self._win_size.w, self._win_size.h = self._win.get_size()
                self._handle_resize()

    def _handle_events(self) -> None:
        """
        Handles events
        Raises:
            KeyboardInterrupt when window is closed
        """

        zoom_amount: int = 0
        reach_zoom_limit: list[bool] = [False, False]
        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise KeyboardInterrupt

            if event.type == pg.VIDEORESIZE:
                self._win_size.w = max(event.w, INIT_WIN_SIZE.w)
                self._win_size.h = max(event.h, INIT_WIN_SIZE.h)
                if self._win_size.w != event.w or self._win_size.h != event.h:
                    self._win = pg.display.set_mode(
                        self._win_size.wh, self._main_win_flag | EXTRA_FLAGS
                    )

                self._handle_resize()
            elif event.type == pg.MOUSEWHEEL:
                zoom_amount = event.y
            elif event.type == pg.KEYDOWN:
                self._handle_keys(event.key)
            elif event.type == pg.KEYUP:
                self._pressed_keys.remove(event.key)
                self._kmod_ctrl = pg.key.get_mods() & pg.KMOD_CTRL
            elif event.type == FPSUPDATE:
                FPS_TEXT_LABEL.set_text('FPS: ' + str(round(CLOCK.get_fps())))

        if pg.time.get_ticks() - self._prev_k_input < 100:
            self._timed_keys = ()
        else:
            self._timed_keys = tuple(self._pressed_keys)
            self._prev_k_input = pg.time.get_ticks()

        if self._kmod_ctrl:
            if pg.K_MINUS in self._timed_keys:
                zoom_amount = 1
                if pg.key.get_mods() & pg.KMOD_SHIFT:
                    reach_zoom_limit[0] = True
            if pg.K_PLUS in self._timed_keys:
                zoom_amount = -1
                if pg.key.get_mods() & pg.KMOD_SHIFT:
                    reach_zoom_limit[1] = True

        if zoom_amount:
            GRID_MANAGER.zoom(zoom_amount, BRUSH_SIZES.clicked_i + 1, reach_zoom_limit)

    def _handle_debugging(self) -> None:
        """
        Handles everything related to debugging
        """

        if pg.key.get_mods() & pg.KMOD_ALT:
            if pg.K_l in self._timed_keys:
                sequence: LayerSequence = []

                layer_info: list[tuple[str, Any, int]] = [
                    (info.name, info.obj, 0)
                    for state_info in MAIN_OBJS_INFO
                    for info in state_info
                ]
                # Layer info is added to the sequence from last to first
                layer_info = layer_info[::-1]

                while layer_info:
                    name: str
                    obj: Any
                    depth_counter: int
                    name, obj, depth_counter = layer_info.pop()

                    if hasattr(obj, 'print_layer'):
                        sequence.extend(obj.print_layer(name, depth_counter))
                    if hasattr(obj, 'objs_info'):
                        obj_info: tuple[tuple[str, Any, int], ...] = tuple(
                            (info.name, info.obj, depth_counter + 1) for info in obj.objs_info
                        )
                        layer_info.extend(obj_info[::-1])

                for name, layer, depth_counter in sequence:
                    layer_repr: str = str(layer) if layer != -1 else 'None'
                    print(f'{'\t' * depth_counter}{name}: {layer_repr}')
                print('-' * 50)

    def _handle_open_ui_buttons(self) -> None:
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
            GRID_UI.set_size(GRID_MANAGER.grid.grid_size, GRID_MANAGER.grid.pixels)

    def _handle_file_buttons(self) -> None:
        """
        Handles the save as, open and close buttons
        """

        tk_root: Tk
        new_file_path: str
        new_file_img: Image.Image

        ctrl_s: bool = bool(self._kmod_ctrl and pg.K_s in self._timed_keys)
        if SAVE_AS.upt(self._hovered_obj, self._mouse_info) or ctrl_s:
            self._leave(self._state)
            '''
            Applies the leave method changes immediately
            because the tkinter window stops the execution
            '''
            self._draw()

            tk_root = Tk()
            tk_root.withdraw()
            new_file_path = filedialog.asksaveasfilename(
                defaultextension='.png', filetypes=(('png Files', '*.png'),), title='Save as'
            )
            tk_root.destroy()

            if new_file_path:
                self._file_path = new_file_path
                new_file_img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                new_file_img.save(self._file_path)

        ctrl_o: bool = bool(self._kmod_ctrl and pg.K_o in self._timed_keys)
        if OPEN.upt(self._hovered_obj, self._mouse_info) or ctrl_o:
            if self._file_path:
                new_file_img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                new_file_img.save(self._file_path)

            self._leave(self._state)
            '''
            Applies the leave method changes immediately
            because the tkinter window stops the execution
            '''
            self._draw()

            tk_root = Tk()
            tk_root.withdraw()
            new_file_path = filedialog.askopenfilename(
                defaultextension='.png', filetypes=(('png Files', '*.png'),), title='Open'
            )
            tk_root.destroy()

            if new_file_path:
                self._file_path = new_file_path
                GRID_MANAGER.load_path(self._file_path)
                PALETTE_MANAGER.load_from_arr(GRID_MANAGER.grid.pixels)

        ctrl_q: bool = bool(self._kmod_ctrl and pg.K_q in self._timed_keys)
        if (CLOSE.upt(self._hovered_obj, self._mouse_info) or ctrl_q) and self._file_path:
            new_file_img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            new_file_img.save(self._file_path)
            self._leave(self._state)

            self._file_path = ''
            GRID_MANAGER.load_path(self._file_path)
            PALETTE_MANAGER.load_from_arr(GRID_MANAGER.grid.pixels)

    def run(self) -> None:
        """
        Game loop
        """

        new_file_img: Image.Image
        try:
            while True:
                CLOCK.tick(6000)  # TODO: put back at 60

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

                objs_info: list[list[ObjInfo]] = []
                for state in MAIN_OBJS_INFO:
                    state_info: list[ObjInfo] = state.copy()
                    for info in state_info:
                        if hasattr(info.obj, 'objs_info'):
                            state_info.extend(info.obj.objs_info)
                    objs_info.append(state_info)

                self._active_objs = [
                    [info.obj for info in state_info if info.is_active]
                    for state_info in objs_info
                ]
                self._inactive_objs = [
                    [info.obj for info in state_info if not info.is_active]
                    for state_info in objs_info
                ]

                self._hovered_obj = None
                max_hovered_layer: int = 0
                for obj in self._active_objs[self._state]:
                    if hasattr(obj, 'check_hover'):
                        hovered_obj: Any
                        hovered_layer: int
                        hovered_obj, hovered_layer = obj.check_hover(mouse_pos)
                        if hovered_obj and hovered_layer >= max_hovered_layer:
                            self._hovered_obj = hovered_obj
                            max_hovered_layer = hovered_layer

                is_ui_closed: bool
                prev_state: int = self._state
                match self._state:
                    case 0:
                        brush_size: int = BRUSH_SIZES.upt(
                            self._hovered_obj, self._mouse_info, self._timed_keys
                        ) + 1

                        color: ColorType
                        color_to_edit: Optional[ColorType]
                        color, color_to_edit = PALETTE_MANAGER.upt(
                            self._hovered_obj, self._mouse_info, self._timed_keys, self._kmod_ctrl
                        )
                        if color_to_edit:
                            self._state = 1
                            COLOR_PICKER.set_color(color_to_edit)

                        tool_info: tuple[str, dict[str, Any]] = TOOLS_MANAGER.upt(
                            self._hovered_obj, self._mouse_info, self._timed_keys
                        )

                        GRID_MANAGER.upt(
                            self._hovered_obj, self._mouse_info, self._timed_keys, color,
                            brush_size, tool_info
                        )

                        self._handle_open_ui_buttons()
                        self._handle_file_buttons()

                        if self._kmod_ctrl:  # Independent shortcuts
                            # Check if keys from 1 to max brush size are pressed
                            for i in range(len(BRUSH_SIZES.checkboxes)):
                                if pg.K_1 + i in self._timed_keys:
                                    BRUSH_SIZES.tick_on(i)
                    case 1:
                        new_color: Optional[ColorType]
                        is_ui_closed, new_color = COLOR_PICKER.upt(
                            self._hovered_obj, self._mouse_info, self._timed_keys, self._kmod_ctrl
                        )
                        if is_ui_closed:
                            PALETTE_MANAGER.add(new_color)
                            self._state = 0
                    case 2:
                        new_size: Optional[Size]
                        is_ui_closed, new_size = GRID_UI.upt(
                            self._hovered_obj, self._mouse_info, self._timed_keys, self._kmod_ctrl
                        )
                        if is_ui_closed:
                            GRID_MANAGER.resize(new_size)
                            self._state = 0

                if self._state != prev_state:
                    self._leave(prev_state)
                self._handle_debugging()

                self._draw()
        except KeyboardInterrupt:
            if self._file_path:
                new_file_img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                new_file_img.save(self._file_path)
            with DATA_FILE.open('w', encoding='utf-8') as f:
                f.write(self._file_path)

        except Exception:  # pylint: disable=broad-exception-caught
            if not self._file_path:
                duplicate_name_counter: int = 0
                new_file_name: str = 'new_file.png'
                while Path(new_file_name).exists():
                    duplicate_name_counter += 1
                    new_file_name = f'new_file_{duplicate_name_counter}.png'
                self._file_path = new_file_name

            new_file_img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            new_file_img.save(self._file_path)
            with DATA_FILE.open('w', encoding='utf-8') as f:
                f.write(self._file_path)

            print_exc()


if __name__ == '__main__':
    Dixel().run()
