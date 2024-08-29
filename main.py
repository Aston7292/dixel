"""
drawing program for pixel art
"""

import pygame as pg
from tkinter import Tk, filedialog
from PIL import Image
from os import path
from traceback import print_exc
from typing import Tuple, List, Final, Optional, Any

from src.utils import RectPos, Size, MouseInfo, ColorType, BlitSequence
from src.const import INIT_WIN_SIZE, BLACK

pg.init()

ADD_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE
INIT_WIN: Final[pg.SurfaceType] = pg.display.set_mode(
    (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h), pg.RESIZABLE | ADD_FLAGS
)
pg.display.set_caption('Dixel')
pg.display.set_icon(pg.image.load(path.join('sprites', 'icon.png')).convert_alpha())

from src.classes.grid_ui import GridUI
from src.classes.color_manager import ColorPicker
from src.classes.palette_manager import PaletteManager
from src.classes.grid_manager import GridManager
from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import Button
from src.classes.text import Text

BUTTON_M_OFF: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'button_m_off.png')
).convert_alpha()
BUTTON_M_ON: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'button_m_on.png')
).convert_alpha()
BUTTON_S_OFF: Final[pg.SurfaceType] = pg.transform.scale(BUTTON_M_OFF, (64, 32))
BUTTON_S_ON: Final[pg.SurfaceType] = pg.transform.scale(BUTTON_M_ON, (64, 32))

GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(INIT_WIN_SIZE.w / 2, INIT_WIN_SIZE.h / 2, 'center'),
    RectPos(INIT_WIN_SIZE.w - 10, 10, 'topright')
)
ADD_COLOR: Final[Button] = Button(
    RectPos(INIT_WIN_SIZE.w - 25, INIT_WIN_SIZE.h - 25, 'bottomright'),
    (BUTTON_M_OFF, BUTTON_M_ON), 'add color'
)
MODIFY_GRID: Final[Button] = Button(
    RectPos(ADD_COLOR.rect.x - 10, ADD_COLOR.rect.y, 'topright'),
    (BUTTON_M_OFF, BUTTON_M_ON), 'modify grid'
)

SAVE_AS: Final[Button] = Button(
    RectPos(0, 0, 'topleft'), (BUTTON_S_OFF, BUTTON_S_ON), 'save as', 20
)
OPEN: Final[Button] = Button(
    RectPos(SAVE_AS.rect.right, 0, 'topleft'), (BUTTON_S_OFF, BUTTON_S_ON), 'open file', 20
)
CLOSE: Final[Button] = Button(
    RectPos(OPEN.rect.right, 0, 'topleft'), (BUTTON_S_OFF, BUTTON_S_ON), 'close file', 20
)

BRUSH_SIZES_INFO: List[Tuple[pg.SurfaceType, str]] = [
    (
        pg.image.load(path.join('sprites', f'size_{n}_off.png')).convert_alpha(),
        str(n) + 'px'
    ) for n in range(1, 6)
]
BRUSH_SIZES: Final[CheckBoxGrid] = CheckBoxGrid(
    RectPos(10, SAVE_AS.rect.bottom + 10, 'topleft'), BRUSH_SIZES_INFO, len(BRUSH_SIZES_INFO),
    (False, False)
)

PALETTE_MANAGER: Final[PaletteManager] = PaletteManager(
    RectPos(INIT_WIN_SIZE.w - 75, ADD_COLOR.rect.y - 100, 'bottomright'),
    (BUTTON_S_OFF, BUTTON_S_ON)
)

FPS_TEXT: Final[Text] = Text(RectPos(INIT_WIN_SIZE.w / 2, 0, 'midtop'), 'FPS: 0')

COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(INIT_WIN_SIZE.w / 2, INIT_WIN_SIZE.h / 2, 'center'), PALETTE_MANAGER.values[0]
)

GRID_UI: Final[GridUI] = GridUI(
    RectPos(INIT_WIN_SIZE.w / 2, INIT_WIN_SIZE.h / 2, 'center'), GRID_MANAGER.grid.grid_size
)

GLOBAL_OBJS: Final[Tuple[Any, ...]] = (
    GRID_MANAGER, ADD_COLOR, MODIFY_GRID, SAVE_AS, OPEN, CLOSE, BRUSH_SIZES, PALETTE_MANAGER,
    FPS_TEXT
)

FPS_UPT: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPS_UPT, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()


class Dixel:
    """
    drawing program for pixel art
    """

    __slots__ = (
        '_win_size', '_prev_win_size', '_flag', '_full_screen', '_focused', '_win', '_mouse_info',
        '_saved_keys', '_keys', '_last_k_input', '_ctrl', '_color', '_brush_size', '_state',
        '_file_path'
    )

    def __init__(self) -> None:
        """
        initializes the window
        """

        self._win_size: Size = Size(INIT_WIN_SIZE.w, INIT_WIN_SIZE.h)
        self._prev_win_size: Tuple[int, int] = self._win_size.wh
        self._flag: int = pg.RESIZABLE
        self._full_screen: bool = False
        self._focused: bool = True

        self._win: pg.SurfaceType = INIT_WIN

        self._mouse_info: MouseInfo = MouseInfo(
            *pg.mouse.get_pos(), pg.mouse.get_pressed(), pg.mouse.get_just_released()
        )

        self._saved_keys: List[int] = []
        self._keys: List[int] = self._saved_keys
        self._last_k_input: int = pg.time.get_ticks()
        self._ctrl: int = 0

        self._color: ColorType = PALETTE_MANAGER.values[0]
        self._brush_size: int = 1

        self._state: int = 0

        self._file_path: str
        if not path.exists('data.txt'):
            self._file_path = ''
        else:
            with open('data.txt', encoding='utf-8') as f:
                prev_path: str = f.read()
            self._file_path = prev_path if path.exists(prev_path) else ''

            if self._file_path:
                GRID_MANAGER.load_path(self._file_path)
                PALETTE_MANAGER.load_path(self._file_path)
                self._color = PALETTE_MANAGER.values[0]

    def _redraw(self) -> None:
        """
        redraws the screen
        """

        self._win.fill(BLACK)

        blit_sequence: BlitSequence = []

        for obj in GLOBAL_OBJS:
            blit_sequence += obj.blit()

        match self._state:
            case 1:
                blit_sequence += COLOR_PICKER.blit()
            case 2:
                blit_sequence += GRID_UI.blit()

        self._win.fblits(blit_sequence)
        pg.display.flip()

    def _handle_resize(self) -> None:
        """
        resizes objects
        """

        win_ratio_w: float = self._win_size.w / INIT_WIN_SIZE.w
        win_ratio_h: float = self._win_size.h / INIT_WIN_SIZE.h

        for obj in GLOBAL_OBJS:
            obj.handle_resize(win_ratio_w, win_ratio_h)

        COLOR_PICKER.handle_resize(win_ratio_w, win_ratio_h)
        GRID_UI.handle_resize(win_ratio_w, win_ratio_h)

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
                # exiting full screen triggers VIDEORESIZE so handle resize is not necessary
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
        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise KeyboardInterrupt

            if event.type == pg.ACTIVEEVENT and event.state & pg.APPACTIVE:
                self._focused = event.gain == 1
            elif event.type == pg.VIDEORESIZE:
                if event.w < INIT_WIN_SIZE.w or event.h < INIT_WIN_SIZE.h:
                    event.w, event.h = max(event.w, INIT_WIN_SIZE.w), max(event.h, INIT_WIN_SIZE.h)
                    self._win = pg.display.set_mode((event.w, event.h), self._flag | ADD_FLAGS)
                self._win_size.w, self._win_size.h = event.w, event.h

                self._handle_resize()
            elif event.type == pg.MOUSEWHEEL:
                zoom_amount = event.y
            elif event.type == pg.KEYDOWN:
                self._handle_keys(event.key)
            elif event.type == pg.KEYUP:
                self._saved_keys.remove(event.key)
                self._ctrl = pg.key.get_mods() & pg.KMOD_CTRL

            if event.type == FPS_UPT:
                FPS_TEXT.modify_text('FPS: ' + str(int(CLOCK.get_fps())))

        if pg.time.get_ticks() - self._last_k_input < 100:
            self._keys = []
        else:
            self._keys = self._saved_keys
            self._last_k_input = pg.time.get_ticks()

        if self._ctrl:
            if pg.K_PLUS in self._keys:
                zoom_amount = 1
            if pg.K_MINUS in self._keys:
                zoom_amount = -1
        if zoom_amount:
            GRID_MANAGER.zoom(zoom_amount, self._brush_size)

    def _handle_ui_buttons(self) -> None:
        """
        handles the buttons that open uis
        """

        if ADD_COLOR.upt(self._mouse_info) or (self._ctrl and pg.K_a in self._keys):
            self._state = 1

            COLOR_PICKER.ui.prev_mouse_cursor = pg.mouse.get_cursor()
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
            COLOR_PICKER.set(BLACK)

        if MODIFY_GRID.upt(self._mouse_info) or (self._ctrl and pg.K_m in self._keys):
            self._state = 2

            GRID_UI.ui.prev_mouse_cursor = pg.mouse.get_cursor()
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
            GRID_UI.set(GRID_MANAGER.grid.grid_size, GRID_MANAGER.grid.pixels)

    def _handle_file_buttons(self) -> None:
        """
        handles the save as, open and close buttons
        """

        root: Tk
        file_path: str
        if SAVE_AS.upt(self._mouse_info) or (self._ctrl and pg.K_s in self._keys):
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
                Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)

        if OPEN.upt(self._mouse_info) or (self._ctrl and pg.K_o in self._keys):
            if self._file_path:
                Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)

            root = Tk()
            root.withdraw()

            file_path = filedialog.askopenfilename(
                defaultextension='.png',
                filetypes=(('png Files', '*.png'),),
                title='Open'
            )
            root.destroy()

            if file_path:
                # TODO: resize grid before loading image
                self._file_path = file_path
                GRID_MANAGER.load_path(self._file_path)
                PALETTE_MANAGER.load_path(self._file_path)
                self._color = PALETTE_MANAGER.values[0]

        if (
                (CLOSE.upt(self._mouse_info) or (self._ctrl and pg.K_q in self._keys)) and
                self._file_path
        ):
            Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)

            self._file_path = ''
            GRID_MANAGER.load_path(self._file_path)
            PALETTE_MANAGER.load_path(self._file_path)
            self._color = PALETTE_MANAGER.values[0]

    def run(self) -> None:
        """
        game loop
        """

        try:
            while True:
                CLOCK.tick(60)

                self._handle_events()
                if not self._focused:
                    continue

                mouse_pos: Tuple[int, int] = (
                    pg.mouse.get_pos() if pg.mouse.get_focused() else (-1, -1)
                )  # when mouse is off the windows position is (0, 0)
                self._mouse_info = MouseInfo(
                    *mouse_pos, pg.mouse.get_pressed(), pg.mouse.get_just_released()
                )

                closed: bool
                match self._state:
                    case 0:
                        GRID_MANAGER.upt(
                            self._mouse_info, self._keys, self._color, self._brush_size
                        )

                        brush_size: int = BRUSH_SIZES.upt(self._mouse_info)
                        if brush_size != -1:
                            self._brush_size = brush_size + 1

                        selected_color: Optional[ColorType]
                        color_to_edit: Optional[ColorType]
                        selected_color, color_to_edit = PALETTE_MANAGER.upt(
                            self._mouse_info, self._keys, self._ctrl
                        )
                        if selected_color:
                            self._color = selected_color
                        elif color_to_edit:
                            self._state = 1

                            COLOR_PICKER.ui.prev_mouse_cursor = pg.mouse.get_cursor()
                            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                            COLOR_PICKER.set(color_to_edit)

                        self._handle_ui_buttons()
                        self._handle_file_buttons()

                        if self._ctrl:  # independent shortcuts
                            for i in range(pg.K_1, pg.K_1 + len(BRUSH_SIZES.check_boxes)):
                                if i in self._keys:
                                    BRUSH_SIZES.set(i - pg.K_1)
                                    self._brush_size = i - pg.K_1 + 1
                    case 1:
                        color: Optional[ColorType]
                        closed, color = COLOR_PICKER.upt(
                            self._mouse_info, self._keys, self._ctrl
                        )
                        if closed:
                            if color:
                                self._color = PALETTE_MANAGER.add(color)
                            else:
                                PALETTE_MANAGER.changing_color = False

                            self._state = 0
                    case 2:
                        size: Optional[Size]
                        closed, size = GRID_UI.upt(self._mouse_info, self._keys, self._ctrl)
                        if closed:
                            if size:
                                GRID_MANAGER.resize(size)

                            self._state = 0

                self._redraw()

        except KeyboardInterrupt:
            if self._file_path:
                Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(self._file_path)

        except Exception:  # pylint: disable=broad-exception-caught
            if not self._file_path:
                name: str = 'new_file.png'
                i = 0
                while path.exists(name):
                    i += 1
                    name = f'new_file_{i}.png'
                self._file_path = name

            Image.fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(self._file_path)

            print_exc()


if __name__ == '__main__':
    Dixel().run()
