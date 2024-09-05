"""
drawing program for pixel art
"""

'''
TODO:
- open GRID_UI when opening file
- save current colors along with the image
- slider is faster when moving the mouse faster
- consistent text_i across different NumInputBox
- option to change the palette to match the current colors/multiple palettes
- CTRL Z/Y (store without alpha channel, ui to view history)
- option to make drawing only affect the visible_area?
- better mouse sprite handling

- COLOR_PICKER:
    - hex_text as NumInputBox

- GRID_UI:
    - add option to resize in order to fit image
    - option to change visible_area?
    - move image before resizing?
    - change mouse sprite when using a slider?
    - if check box is on, the current slider text is empty and the opp_slider value is 1
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
    - GRID_MANAGER: update_section (precalculate section indicator?)

debug:
    - togglable debug mode
    - view next checkbox position in CheckBoxGrid
    - view grid, minimap and GRID_UI preview info
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
from src.utils import (
    Point, RectPos, Size, MouseInfo, ColorType, BlitSequence, LayeredBlitSequence, LayersInfo
)
from src.const import INIT_WIN_SIZE, BLACK

pg.init()

ADD_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE
INIT_WIN: Final[pg.SurfaceType] = pg.display.set_mode(
    (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h), pg.RESIZABLE | ADD_FLAGS
)
pg.display.set_caption('Dixel')
pg.display.set_icon(pg.image.load(path.join('sprites', 'icon.png')).convert_alpha())

# they load images at the start which require pygame to be already initialized
from src.classes.grid_ui import GridUI
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

GRID_UI: Final[GridUI] = GridUI(
    RectPos(INIT_WIN_SIZE.w / 2.0, INIT_WIN_SIZE.h / 2.0, 'center'), GRID_MANAGER.grid.grid_size
)

GLOBAL_OBJS: Final[tuple[Any, ...]] = (
    ADD_COLOR, MODIFY_GRID, SAVE_AS, OPEN, CLOSE, GRID_MANAGER, BRUSH_SIZES, PALETTE_MANAGER,
    TOOLS_MANAGER, FPS_TEXT
)
ALL_OBJS: Final[dict[str, Any]] = {  # mainly for debug
    'button add color': ADD_COLOR,
    'button modify grid': MODIFY_GRID,
    'button save': SAVE_AS,
    'button open': OPEN,
    'button close': CLOSE,
    'grid manager': GRID_MANAGER,
    'checkbox_grid brush sizes': BRUSH_SIZES,
    'palette manager': PALETTE_MANAGER,
    'tools manager': TOOLS_MANAGER,
    'ui pick color': COLOR_PICKER,
    'ui modify grid': GRID_UI,
    'text fps': FPS_TEXT
}

FPS_UPT: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPS_UPT, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()


class Dixel:
    """
    drawing program for pixel art
    """

    __slots__ = (
        '_win_size', '_prev_win_size', '_flag', '_full_screen', '_focused', '_win', '_mouse_info',
        '_saved_keys', '_keys', '_last_k_input', '_ctrl', '_hover_obj', '_state', '_file_path'
    )

    def __init__(self) -> None:
        """
        initializes the window
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
        self._state: str = 'main_interface'

        self._file_path: str = ''
        if path.exists('data.txt'):
            with open('data.txt', encoding='utf-8') as f:
                file_path: str = f.read()

            if path.exists(file_path):
                self._file_path = file_path
                GRID_MANAGER.load_path(self._file_path)
                PALETTE_MANAGER.load_path(GRID_MANAGER.grid.pixels)

    def _draw(self) -> None:
        """
        draws objects on the screen
        """

        self._win.fill(BLACK)

        layered_blit_sequence: LayeredBlitSequence = []

        for obj in GLOBAL_OBJS:
            layered_blit_sequence += obj.blit()

        match self._state:
            case 'color_ui':
                layered_blit_sequence += COLOR_PICKER.blit()
            case 'grid_ui':
                layered_blit_sequence += GRID_UI.blit()

        layer_i: int = 2
        layered_blit_sequence.sort(key=lambda info: info[layer_i])  # type: ignore
        blit_sequence: BlitSequence = [(pair[0], pair[1]) for pair in layered_blit_sequence]

        self._win.fblits(blit_sequence)
        pg.display.flip()

    def _handle_resize(self) -> None:
        """
        resizes objects
        """

        '''
        blitting everything on a surface, scaling it to match to self._win_size and blitting it
        removes text anti aliasing and causes 1 pixel offsets on some elements at specific sizes
        pygame.SCALED doesn't scale position and images
        all objects have an init_pos and init_size
        to scale position and image size
        '''

        win_ratio_w: float = self._win_size.w / INIT_WIN_SIZE.w
        win_ratio_h: float = self._win_size.h / INIT_WIN_SIZE.h
        for obj in ALL_OBJS.values():
            obj.handle_resize(win_ratio_w, win_ratio_h)

    def _leave(self) -> None:
        """
        clears everything that needs to be cleared when leaving state 0
        """

        for obj in GLOBAL_OBJS:
            if hasattr(obj, 'leave'):
                obj.leave()
        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

    def _handle_keys(self, k: int) -> None:
        """
        handles keyboard inputs
        takes k
        raises KeyboardInterrupt when esc is pressed
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
                # exiting full screen triggers VIDEORESIZE so self._handle_resize is not necessary
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
        handles events,
        raises KeyboardInterrupt when window is closed
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
        handles everything related to debugging
        """

        if pg.key.get_mods() & pg.KMOD_ALT:
            if pg.K_l in self._keys:
                layers_info: LayersInfo = []
                for name, obj in ALL_OBJS.items():
                    layers_info += obj.print_layers(name, 0)

                for name, layer, counter in layers_info:
                    string_layer: str = str(layer) if layer != -1 else 'None'
                    print(f'{'\t' * counter}{name}: {string_layer}')
                print('-' * 50)

    def _handle_open_ui_buttons(self) -> None:
        """
        handles the buttons that open uis
        """

        ctrl_a: bool = bool(self._ctrl and pg.K_a in self._keys)
        if ADD_COLOR.upt(self._hover_obj, self._mouse_info) or ctrl_a:
            self._state = 'color_ui'
            COLOR_PICKER.set_color(BLACK)

        ctrl_m: bool = bool(self._ctrl and pg.K_m in self._keys)
        if MODIFY_GRID.upt(self._hover_obj, self._mouse_info) or ctrl_m:
            self._state = 'grid_ui'
            GRID_UI.set_size(GRID_MANAGER.grid.grid_size, GRID_MANAGER.grid.pixels)

    def _handle_file_buttons(self) -> None:
        """
        handles the save as, open and close buttons
        """

        root: Tk
        file_path: str
        img: Image.Image
        if SAVE_AS.upt(self._hover_obj, self._mouse_info) or (self._ctrl and pg.K_s in self._keys):
            self._leave()
            self._draw()  # applies self._leave changes immediately since root stops the execution

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
            self._leave()
            self._draw()  # applies self._leave changes immediately since root stops the execution

            root = Tk()
            root.withdraw()

            file_path = filedialog.askopenfilename(
                defaultextension='.png',
                filetypes=(('png Files', '*.png'),),
                title='Open'
            )
            root.destroy()

            if file_path:
                self._leave()
                self._file_path = file_path
                GRID_MANAGER.load_path(self._file_path)
                PALETTE_MANAGER.load_path(GRID_MANAGER.grid.pixels)

        ctrl_q: bool = bool(self._ctrl and pg.K_q in self._keys)
        if (CLOSE.upt(self._hover_obj, self._mouse_info) or ctrl_q) and self._file_path:
            img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            img.save(self._file_path)
            self._leave()

            self._file_path = ''
            GRID_MANAGER.load_path(self._file_path)
            PALETTE_MANAGER.load_path(GRID_MANAGER.grid.pixels)

    def run(self) -> None:
        """
        game loop
        """

        img: Image.Image
        try:
            while True:
                CLOCK.tick(6000)  # TODO: put at 60

                self._handle_events()
                if not self._focused:
                    continue

                # when mouse is off the window it's position is (0, 0), it can cause wrong hovering
                mouse_pos: tuple[int, int] = (
                    pg.mouse.get_pos() if pg.mouse.get_focused() else (-1, -1)
                )
                self._mouse_info = MouseInfo(
                    *mouse_pos, pg.mouse.get_pressed(), pg.mouse.get_just_released()
                )

                self._handle_debugging()

                closed: bool
                match self._state:
                    case 'main_interface':
                        prev_state: str = self._state

                        self._hover_obj = None
                        hover_layer: int = 0
                        for obj in GLOBAL_OBJS:
                            if hasattr(obj, 'check_hover'):
                                current_hover_obj: Any
                                current_hover_layer: int
                                current_hover_obj, current_hover_layer = obj.check_hover(mouse_pos)
                                if current_hover_obj and current_hover_layer >= hover_layer:
                                    self._hover_obj = current_hover_obj
                                    hover_layer = current_hover_layer

                        brush_size: int = BRUSH_SIZES.upt(
                            self._hover_obj, self._mouse_info, self._keys
                        ) + 1

                        color: ColorType
                        color_to_edit: Optional[ColorType]
                        color, color_to_edit = PALETTE_MANAGER.upt(
                            self._hover_obj, self._mouse_info, self._keys, self._ctrl
                        )
                        if color_to_edit:
                            self._state = 'color_ui'
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

                        if self._ctrl:  # independent shortcuts
                            # check if keys 1 trough max brush size are pressed
                            for i in range(len(BRUSH_SIZES.check_boxes)):
                                if pg.K_1 + i in self._keys:
                                    BRUSH_SIZES.tick_on(i)

                        if self._state != prev_state:
                            self._leave()
                    case 'color_ui':
                        chose_color: Optional[ColorType]
                        closed, chose_color = COLOR_PICKER.upt(
                            self._mouse_info, self._keys, self._ctrl
                        )
                        if closed:
                            PALETTE_MANAGER.add(chose_color)
                            self._state = 'main_interface'
                    case 'grid_ui':
                        size: Optional[Size]
                        closed, size = GRID_UI.upt(self._mouse_info, self._keys, self._ctrl)
                        if closed:
                            GRID_MANAGER.resize(size)
                            self._state = 'main_interface'

                self._draw()

        except KeyboardInterrupt:
            if self._file_path:
                img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
                img.save(self._file_path)
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(self._file_path)

        except Exception:  # pylint: disable=broad-exception-caught
            if not self._file_path:
                counter: int = 0
                name: str = 'new_file.png'
                while path.exists(name):
                    counter += 1
                    name = f'new_file_{counter}.png'
                self._file_path = name

            img = Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA')
            img.save(self._file_path)
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(self._file_path)

            print_exc()


if __name__ == '__main__':
    Dixel().run()
