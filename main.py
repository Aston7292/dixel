"""
Drawing program for pixel art
"""

'''
INFO:

There are three states, the main interface and 2 extra UI windows
that can be opened by clicking their respective button

Keyboard input:
    Every key that's currently pressed is in a list, accidental spamming is prevented
    by temporarily clearing this list when a key is held and reverting it back for
    one frame every 100ms

Mouse info:
    Mouse info is contained in a dataclass that tracks:
    x and y position, button states and recently released buttons (for clicking elements)

Sub objects:
    Objects may have sub objects, they're retrieved at the start of each frame and
    automatically used in the methods below

Blitting:
    The blit method returns a list with one or more groups of image, position and layer
    objects with an higher layer will be blitted on top of objects with a lower one

    There are 4 layer types:
        background: background elements and grid
        element: UI elements that can be interacted with
        text: normal text labels
        top: elements that aren't always present like text on hover or a cursor in an input box

    Layers can also be extended into the special group,
    they will still keep their hierarchy so special top goes on top of special text and so on
    but every special layer goes on top of any normal one,
    it's used for stuff like drop down menus that appear on right click
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
                hover text: 3
        checkbox 1: 1
                hover text: 3
        checkbox 2: 1
                hover text: 3
        checkbox 3: 1
                hover text: 3
        checkbox 4: 1
                hover text: 3

Interacting with elements:
    Interaction is possible with the upt method
'''

'''
TODO:
- open GRID_RESIZER when opening file
- save current colors along with the image
- slider is faster when moving the mouse faster
- consistent text_i across different NumInputBox
- option to change the palette to match the current colors/multiple palettes
- CTRL Z/Y (store without alpha channel, ui to view history)
- option to make drawing only affect the visible_area?
- better mouse sprite handling

- COLOR_PICKER:
    - hex_text as NumInputBox

- GRID_RESIZER:
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
    - GRID_RESIZER: get_preview
    - GRID_MANAGER: update_section (precalculate section_indicator?)

debug:
    - togglable debug mode
    - view next checkbox position in CheckBoxGrid
    - view grid, minimap and GRID_RESIZER preview info
    - view hover_text for Clickable
    - view text_i for NumInputBox
'''

import pygame as pg
from tkinter import Tk, filedialog
from PIL import Image
from os import path
from traceback import print_exc
from typing import Final, Optional, Any

from src.classes.palette_manager import PaletteManager
from src.classes.grid_manager import GridManager
from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import Button
from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo, ColorType
from src.type_utils import ObjsInfo, BlitSequence, LayeredBlitSequence, LayerSequence

from src.consts import INIT_WIN_SIZE, BLACK

pg.init()

ADD_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE
INIT_WIN: Final[pg.SurfaceType] = pg.display.set_mode(
    (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h), pg.RESIZABLE | ADD_FLAGS
)
pg.display.set_caption('Dixel')
pg.display.set_icon(pg.image.load(path.join('sprites', 'icon.png')).convert_alpha())

# These files load images at the start which require pygame to be already initialized
from src.classes.grid_ui import GridResizer
from src.classes.color_ui import ColorPicker
from src.classes.ui import BUTTON_M_OFF, BUTTON_M_ON
from src.classes.tools_manager import ToolsManager

BUTTON_S_OFF: Final[pg.SurfaceType] = pg.transform.scale(BUTTON_M_OFF, (64, 32))
BUTTON_S_ON: Final[pg.SurfaceType] = pg.transform.scale(BUTTON_M_ON, (64, 32))

ADD_COLOR: Final[Button] = Button(
    RectPos(INIT_WIN_SIZE.w - 25.0, INIT_WIN_SIZE.h - 25.0, 'bottomright'),
    (BUTTON_M_OFF, BUTTON_M_ON), 'add color', '(CTRL+A)'
)
MODIFY_GRID: Final[Button] = Button(
    RectPos(ADD_COLOR.rect.x - 10.0, ADD_COLOR.rect.y, 'topright'),
    (BUTTON_M_OFF, BUTTON_M_ON), 'modify grid', '(CTRL+M)'
)

SAVE_AS: Final[Button] = Button(
    RectPos(0.0, 0.0, 'topleft'), (BUTTON_S_OFF, BUTTON_S_ON),
    'save as', '(CTRL+S)', text_h=15
)
OPEN: Final[Button] = Button(
    RectPos(SAVE_AS.rect.right, 0.0, 'topleft'), (BUTTON_S_OFF, BUTTON_S_ON),
    'open file', '(CTRL+O)', text_h=15
)
CLOSE: Final[Button] = Button(
    RectPos(OPEN.rect.right, 0.0, 'topleft'), (BUTTON_S_OFF, BUTTON_S_ON),
    'close file', '(CTRL+Q)', text_h=15
)

GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(INIT_WIN_SIZE.w / 2.0, INIT_WIN_SIZE.h / 2.0, 'center'),
    RectPos(INIT_WIN_SIZE.w - 10.0, 10.0, 'topright')
)

BRUSH_SIZES_INFO: list[tuple[pg.SurfaceType, str]] = [
    (
        pg.image.load(path.join('sprites', f'size_{n}_off.png')).convert_alpha(),
        f'{n}px\n(CTRL+{n})'
    ) for n in range(1, 6)
]
BRUSH_SIZES: Final[CheckBoxGrid] = CheckBoxGrid(
    RectPos(10.0, SAVE_AS.rect.bottom + 10.0, 'topleft'), BRUSH_SIZES_INFO, len(BRUSH_SIZES_INFO),
    (False, False)
)

PALETTE_MANAGER: Final[PaletteManager] = PaletteManager(
    RectPos(INIT_WIN_SIZE.w - 75.0, ADD_COLOR.rect.y - 25.0, 'bottomright'),
    (BUTTON_S_OFF, BUTTON_S_ON)
)

TOOLS_MANAGER: Final[ToolsManager] = ToolsManager(
    RectPos(10.0, INIT_WIN_SIZE.h - 10.0, 'bottomleft')
)

FPS_TEXT: Final[Text] = Text(RectPos(INIT_WIN_SIZE.w / 2.0, 0.0, 'midtop'), 'FPS: 0')

COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(INIT_WIN_SIZE.w / 2.0, INIT_WIN_SIZE.h / 2.0, 'center'), PALETTE_MANAGER.values[0]
)

GRID_RESIZER: Final[GridResizer] = GridResizer(
    RectPos(INIT_WIN_SIZE.w / 2.0, INIT_WIN_SIZE.h / 2.0, 'center'), GRID_MANAGER.grid.grid_size
)

OBJS_INFO: Final[tuple[ObjsInfo, ...]] = (  # Grouped by state
    [
        ('add color', ADD_COLOR),
        ('modify grid', MODIFY_GRID),
        ('save as', SAVE_AS),
        ('open', OPEN),
        ('close', CLOSE),
        ('grid manager', GRID_MANAGER),
        ('brush sizes', BRUSH_SIZES),
        ('palette manager', PALETTE_MANAGER),
        ('tools manager', TOOLS_MANAGER),
        ('fps text', FPS_TEXT)
    ],
    [
        ('color ui', COLOR_PICKER),
    ],
    [
        ('grid ui', GRID_RESIZER),
    ]
)
OBJS: Final[tuple[tuple[Any, ...], ...]] = tuple(
    tuple(obj for _, obj in state) for state in OBJS_INFO
)

FPS_UPT: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPS_UPT, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()


class Dixel:
    """
    Drawing program for pixel art
    """

    __slots__ = (
        '_win_size', '_prev_win_size', '_flag', '_full_screen', '_focused', '_win', '_mouse_info',
        '_saved_keys', '_keys', '_last_k_input', '_ctrl', '_hover_obj', '_state', '_objs',
        '_file_path',
    )

    def __init__(self) -> None:
        """
        Initializes the window
        """

        self._win_size: Size = Size(INIT_WIN_SIZE.w, INIT_WIN_SIZE.h)
        self._prev_win_size: tuple[int, int] = self._win_size.wh
        self._flag: int = pg.RESIZABLE
        self._full_screen: bool = False
        self._focused: bool = True

        self._win: pg.SurfaceType = INIT_WIN

        self._mouse_info: MouseInfo = MouseInfo(
            *pg.mouse.get_pos(), pg.mouse.get_pressed(), pg.mouse.get_just_released()
        )

        self._saved_keys: list[int] = []
        self._keys: list[int] = self._saved_keys
        self._last_k_input: int = pg.time.get_ticks()
        self._ctrl: int = 0

        self._hover_obj: Any = None

        '''
        0 = main interface
        1 = color ui
        2 = grid ui
        '''
        self._state: int = 0

        self._objs: list[list[Any]] = []

        self._file_path: str = ''
        if path.exists('data.txt'):
            with open('data.txt', encoding='utf-8') as f:
                file_path: str = f.read()

            if path.exists(file_path):
                self._file_path = file_path
                GRID_MANAGER.load_path(self._file_path)
                PALETTE_MANAGER.load_from_arr(GRID_MANAGER.grid.pixels)

    def _draw(self) -> None:
        """
        Draws objects on the screen
        """

        self._win.fill(BLACK)

        layered_blit_sequence: LayeredBlitSequence = []

        objs: list[Any] = self._objs[0].copy()
        if self._state:
            objs += self._objs[self._state]

        for obj in objs:
            if hasattr(obj, 'blit'):
                layered_blit_sequence += obj.blit()

        layer_i: int = 2
        layered_blit_sequence.sort(key=lambda info: info[layer_i])  # type: ignore
        blit_sequence: BlitSequence = [(surf, pos) for surf, pos, _ in layered_blit_sequence]

        self._win.fblits(blit_sequence)
        pg.display.flip()

    def _leave(self, state: int) -> None:
        """
        Clears all the relevant data when leaving a state
        Args:
            state
        """

        for obj in self._objs[state]:
            if hasattr(obj, 'leave'):
                obj.leave()

        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

    def _handle_resize(self) -> None:
        """
        Resizes objects
        """

        win_ratio_w: float = self._win_size.w / INIT_WIN_SIZE.w
        win_ratio_h: float = self._win_size.h / INIT_WIN_SIZE.h

        post_resizes: list[Any] = []
        for state in self._objs:
            for obj in state:
                if hasattr(obj, 'handle_resize'):
                    obj.handle_resize(win_ratio_w, win_ratio_h)
                if hasattr(obj, 'post_resize'):
                    post_resizes.append(obj)

        for obj in post_resizes:
            obj.post_resize()

    def _handle_keys(self, k: int) -> None:
        """
        Handles keyboard inputs
        Args:
            key
        Raises:
            KeyboardInterrupt when esc is pressed
        """

        self._saved_keys.append(k)
        self._last_k_input = 0
        self._ctrl = pg.key.get_mods() & pg.KMOD_CTRL

        if k == pg.K_ESCAPE:
            raise KeyboardInterrupt

        if k == pg.K_F1:
            self._win_size.w, self._win_size.h = INIT_WIN_SIZE.w, INIT_WIN_SIZE.h
            self._flag = pg.RESIZABLE
            self._full_screen = False
            self._win = pg.display.set_mode(self._win_size.wh, self._flag | ADD_FLAGS)

            self._handle_resize()
        elif k == pg.K_F11:
            self._full_screen = not self._full_screen

            if not self._full_screen:
                '''
                Exiting full screen triggers the VIDEORESIZE event
                so the handle_resize method is not necessary
                '''

                self._win_size.w, self._win_size.h = self._prev_win_size
                self._flag = pg.RESIZABLE
                self._win = pg.display.set_mode(self._win_size.wh, self._flag | ADD_FLAGS)
            else:
                self._flag = pg.FULLSCREEN
                self._win = pg.display.set_mode((0, 0), self._flag | ADD_FLAGS)
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
        reach_limit: list[bool] = [False, False]
        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise KeyboardInterrupt

            if event.type == pg.ACTIVEEVENT and event.state & pg.APPACTIVE:
                self._focused = event.gain == 1
            elif event.type == pg.VIDEORESIZE:
                self._win_size.w = max(event.w, INIT_WIN_SIZE.w)
                self._win_size.h = max(event.h, INIT_WIN_SIZE.h)
                if self._win_size.w != event.w or self._win_size.h != event.h:
                    self._win = pg.display.set_mode(self._win_size.wh, self._flag | ADD_FLAGS)

                self._handle_resize()
            elif event.type == pg.MOUSEWHEEL:
                zoom_amount = event.y
            elif event.type == pg.KEYDOWN:
                self._handle_keys(event.key)
            elif event.type == pg.KEYUP:
                self._saved_keys.remove(event.key)
                self._ctrl = pg.key.get_mods() & pg.KMOD_CTRL
            elif event.type == FPS_UPT:
                FPS_TEXT.set_text('FPS: ' + str(int(CLOCK.get_fps())))

        if pg.time.get_ticks() - self._last_k_input < 100:
            self._keys = []
        else:
            self._keys = self._saved_keys
            self._last_k_input = pg.time.get_ticks()

        if self._ctrl:
            if pg.K_MINUS in self._keys:
                zoom_amount = 1
                if pg.key.get_mods() & pg.KMOD_SHIFT:
                    reach_limit[0] = True
            if pg.K_PLUS in self._keys:
                zoom_amount = -1
                if pg.key.get_mods() & pg.KMOD_SHIFT:
                    reach_limit[1] = True

        if zoom_amount:
            GRID_MANAGER.zoom(zoom_amount, BRUSH_SIZES.clicked_i + 1, reach_limit)

    def _handle_debugging(self) -> None:
        """
        Handles everything related to debugging
        """

        if pg.key.get_mods() & pg.KMOD_ALT:
            if pg.K_l in self._keys:
                sequence: LayerSequence = []
                info: list[tuple[str, Any, int]] = [
                    (name, obj, 0) for state in OBJS_INFO for name, obj in state
                ]
                info = info[::-1]  # Info is added to the sequence from last to first

                while info:
                    name: str
                    obj: Any
                    depth_counter: int
                    name, obj, depth_counter = info.pop()

                    if hasattr(obj, 'print_layer'):
                        sequence += obj.print_layer(name, depth_counter)
                    if hasattr(obj, 'sub_objs'):
                        sub_info: list[tuple[str, Any, int]] = [
                            (name, sub_obj, depth_counter + 1) for name, sub_obj in obj.sub_objs
                        ]
                        info += sub_info[::-1]

                for name, layer, depth_counter in sequence:
                    string_layer: str = str(layer) if layer != -1 else 'None'
                    print(f'{'\t' * depth_counter}{name}: {string_layer}')
                print('-' * 50)

    def _handle_open_ui_buttons(self) -> None:
        """
        Handles the buttons that open uis
        """

        ctrl_a: bool = bool(self._ctrl and pg.K_a in self._keys)
        if ADD_COLOR.upt(self._hover_obj, self._mouse_info) or ctrl_a:
            self._state = 1
            COLOR_PICKER.set_color(BLACK)

        ctrl_m: bool = bool(self._ctrl and pg.K_m in self._keys)
        if MODIFY_GRID.upt(self._hover_obj, self._mouse_info) or ctrl_m:
            self._state = 2
            GRID_RESIZER.set_size(GRID_MANAGER.grid.grid_size, GRID_MANAGER.grid.pixels)

    def _handle_file_buttons(self) -> None:
        """
        Handles the save as, open and close buttons
        """

        root: Tk
        file_path: str
        img: Image.Image
        if SAVE_AS.upt(self._hover_obj, self._mouse_info) or (self._ctrl and pg.K_s in self._keys):
            self._leave(self._state)
            '''
            Applies the leave method changes immediately
            because the tkinter window stops the execution
            '''
            self._draw()

            root = Tk()
            root.withdraw()

            file_path = filedialog.asksaveasfilename(
                defaultextension='.png',
                filetypes=(('png Files', '*.png'), ('jpeg Files', '')),
                title='Save as'
            )
            root.destroy()

            if file_path:
                self._file_path = file_path
                img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                img.save(self._file_path)

        if OPEN.upt(self._hover_obj, self._mouse_info) or (self._ctrl and pg.K_o in self._keys):
            if self._file_path:
                img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                img.save(self._file_path)

            self._leave(self._state)
            '''
            Applies the leave method changes immediately
            because the tkinter window stops the execution
            '''
            self._draw()

            root = Tk()
            root.withdraw()

            file_path = filedialog.askopenfilename(
                defaultextension='.png',
                filetypes=(('png Files', '*.png'),),
                title='Open'
            )
            root.destroy()

            if file_path:
                self._leave(self._state)
                self._file_path = file_path
                GRID_MANAGER.load_path(self._file_path)
                PALETTE_MANAGER.load_from_arr(GRID_MANAGER.grid.pixels)

        ctrl_q: bool = bool(self._ctrl and pg.K_q in self._keys)
        if (CLOSE.upt(self._hover_obj, self._mouse_info) or ctrl_q) and self._file_path:
            img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            img.save(self._file_path)
            self._leave(self._state)

            self._file_path = ''
            GRID_MANAGER.load_path(self._file_path)
            PALETTE_MANAGER.load_from_arr(GRID_MANAGER.grid.pixels)

    def run(self) -> None:
        """
        Game loop
        """

        img: Image.Image
        try:
            while True:
                CLOCK.tick(6000)  # TODO: put back at 60

                self._handle_events()
                if not self._focused:
                    continue

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

                self._objs = []
                for state in OBJS:
                    state_objs = list(state)
                    for obj in state_objs:
                        if hasattr(obj, 'sub_objs'):
                            state_objs += [obj for _, obj in obj.sub_objs]

                    self._objs.append(state_objs)

                self._hover_obj = None
                hover_layer: int = 0
                for obj in self._objs[self._state]:
                    if hasattr(obj, 'check_hover'):
                        current_hover_obj: Any
                        current_hover_layer: int
                        current_hover_obj, current_hover_layer = obj.check_hover(mouse_pos)
                        if current_hover_obj and current_hover_layer >= hover_layer:
                            self._hover_obj = current_hover_obj
                            hover_layer = current_hover_layer

                closed: bool
                prev_state: int = self._state
                match self._state:
                    case 0:
                        brush_size: int = BRUSH_SIZES.upt(
                            self._hover_obj, self._mouse_info, self._keys
                        ) + 1

                        color: ColorType
                        color_to_edit: Optional[ColorType]
                        color, color_to_edit = PALETTE_MANAGER.upt(
                            self._hover_obj, self._mouse_info, self._keys, self._ctrl
                        )
                        if color_to_edit:
                            self._state = 1
                            COLOR_PICKER.set_color(color_to_edit)

                        tool_info: tuple[str, dict[str, Any]] = TOOLS_MANAGER.upt(
                            self._hover_obj, self._mouse_info, self._keys
                        )

                        GRID_MANAGER.upt(
                            self._hover_obj, self._mouse_info, self._keys, color, brush_size,
                            tool_info
                        )

                        self._handle_open_ui_buttons()
                        self._handle_file_buttons()

                        if self._ctrl:  # Independent shortcuts
                            # Check if keys from 1 to max brush size are pressed
                            for i in range(len(BRUSH_SIZES.check_boxes)):
                                if pg.K_1 + i in self._keys:
                                    BRUSH_SIZES.tick_on(i)
                    case 1:
                        chose_color: Optional[ColorType]
                        closed, chose_color = COLOR_PICKER.upt(
                            self._hover_obj, self._mouse_info, self._keys, self._ctrl
                        )
                        if closed:
                            PALETTE_MANAGER.add(chose_color)
                            self._state = 0
                    case 2:
                        size: Optional[Size]
                        closed, size = GRID_RESIZER.upt(
                            self._hover_obj, self._mouse_info, self._keys, self._ctrl
                        )
                        if closed:
                            GRID_MANAGER.resize(size)
                            self._state = 0

                if self._state != prev_state:
                    self._leave(prev_state)
                self._handle_debugging()

                self._draw()
        except KeyboardInterrupt:
            if self._file_path:
                img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                img.save(self._file_path)
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(self._file_path)

        except Exception:  # pylint: disable=broad-exception-caught
            if not self._file_path:
                duplicate_counter: int = 0
                name: str = 'new_file.png'
                while path.exists(name):
                    duplicate_counter += 1
                    name = f'new_file_{duplicate_counter}.png'
                self._file_path = name

            img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            img.save(self._file_path)
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(self._file_path)

            print_exc()


if __name__ == '__main__':
    Dixel().run()
