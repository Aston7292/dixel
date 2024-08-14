"""
drawing program for pixel art
"""

import pygame as pg

from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from PIL.Image import fromarray
from os.path import join, exists
from traceback import print_exc
from typing import Tuple, List, Final, Optional, Any

from src.utils import Point, RectPos, Size, MouseInfo, get_monitor_size
from src.const import INIT_WIN_SIZE, BLACK, ColorType, BlitSequence

pg.init()

ADD_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE
INIT_WIN: Final[pg.SurfaceType] = pg.display.set_mode(
    (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h), pg.RESIZABLE | ADD_FLAGS
)
pg.display.set_caption('Dixel')
pg.display.set_icon(pg.image.load(join('sprites', 'icon.png')).convert_alpha())

from src.classes.grid_ui import GridUI
from src.classes.color_manager import ColorPicker
from src.classes.grid_manager import GridManager
from src.classes.check_box import CheckBoxGrid
from src.classes.clickable import Button
from src.classes.text import Text

BUTTON_OFF: Final[pg.SurfaceType] = pg.image.load(join('sprites', 'button_off.png')).convert_alpha()
BUTTON_ON: Final[pg.SurfaceType] = pg.image.load(join('sprites', 'button_on.png')).convert_alpha()

GRID_MANAGER: Final[GridManager] = GridManager(
    RectPos(INIT_WIN_SIZE.w / 2, INIT_WIN_SIZE.h / 2, 'center'),
    RectPos(INIT_WIN_SIZE.w - 10, 10, 'topright')
)
ADD_COLOR: Final[Button] = Button(
    RectPos(INIT_WIN_SIZE.w - 25, INIT_WIN_SIZE.h - 25, 'bottomright'),
    (BUTTON_OFF, BUTTON_ON), 'add color'
)
MODIFY_GRID: Final[Button] = Button(
    RectPos(ADD_COLOR.rect.x, ADD_COLOR.rect.y - 25, 'bottomleft'),
    (BUTTON_OFF, BUTTON_ON), 'modify grid'
)

SAVE_AS: Final[Button] = Button(
    RectPos(25, INIT_WIN_SIZE.h - 25, 'bottomleft'), (BUTTON_OFF, BUTTON_ON), 'save as'
)
LOAD: Final[Button] = Button(
    RectPos(25, SAVE_AS.rect.y - 25, 'bottomleft'), (BUTTON_OFF, BUTTON_ON), 'load file'
)
CLOSE: Final[Button] = Button(
    RectPos(25, LOAD.rect.y - 25, 'bottomleft'), (BUTTON_OFF, BUTTON_ON), 'close file'
)

FPS_TEXT: Final[Text] = Text(RectPos(0, 0, 'topleft'), 32, 'FPS: 0')

brush_size_imgs: List[Tuple[pg.SurfaceType, ...]] = []
for n in range(1, 6):
    off: pg.SurfaceType = pg.image.load(join('sprites', f'size_{n}_off.png')).convert_alpha()
    on: pg.SurfaceType = pg.image.load(join('sprites', f'size_{n}_on.png')).convert_alpha()
    brush_size_imgs.append((off, on))

BRUSH_SIZE_GRID: Final[CheckBoxGrid] = CheckBoxGrid(
    Point(10, FPS_TEXT.surf.get_height()), tuple(brush_size_imgs), 1
)

INIT_COLOR: Final[ColorType] = (0, 0, 0)
COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(INIT_WIN_SIZE.w / 2, INIT_WIN_SIZE.h / 2, 'center'), INIT_COLOR
)

GRID_UI: Final[GridUI] = GridUI(
    RectPos(INIT_WIN_SIZE.w / 2, INIT_WIN_SIZE.h / 2, 'center'), GRID_MANAGER.grid.grid_size
)

GLOBAL_OBJS: Final[Tuple[Any, ...]] = (
    GRID_MANAGER, ADD_COLOR, MODIFY_GRID, BRUSH_SIZE_GRID, SAVE_AS, LOAD, CLOSE, FPS_TEXT
)

FPS_UPT: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPS_UPT, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()


class Dixel:
    """
    drawing program for pixel art
    """

    __slots__ = (
        '_win_size', '_prev_win_size', '_flag', '_full_screen', '_focused', '_win',
        '_keys', '_k', '_last_k_input',  '_ctrl', '_color', '_brush_size', '_state',
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

        self._keys: List[int] = []
        self._k: int = 0
        self._last_k_input: int = pg.time.get_ticks()
        self._ctrl: bool = False

        self._color: ColorType = INIT_COLOR
        self._brush_size: int = 1

        self._state: int = 0

        self._file_path: str
        if not exists('data.txt'):
            self._file_path = ''
        else:
            with open('data.txt', encoding='utf-8') as f:
                prev_path: str = f.read()
            self._file_path = prev_path if exists(prev_path) else ''

            if self._file_path:
                GRID_MANAGER.load_path(self._file_path)

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
        takes the pressed key
        raises KeyboardInterrupt when esc is pressed
        """

        self._keys.append(k)
        self._ctrl = bool(pg.key.get_mods() & pg.KMOD_CTRL)

        if k == pg.K_ESCAPE:
            raise KeyboardInterrupt

        if k == pg.K_F1:
            self._win_size, self._flag = Size(INIT_WIN_SIZE.w, INIT_WIN_SIZE.h), pg.RESIZABLE
            self._full_screen = False
            self._win = pg.display.set_mode(self._win_size.wh, self._flag | ADD_FLAGS)

            self._handle_resize()
        elif k == pg.K_F11:
            self._full_screen = not self._full_screen

            if not self._full_screen:
                # exiting full screen triggers VIDEORESIZE so handle resize is not necessary
                self._win_size, self._flag = Size(*self._prev_win_size), pg.RESIZABLE
            else:
                self._prev_win_size = self._win_size.wh
                self._win_size, self._flag = Size(*get_monitor_size()), pg.FULLSCREEN
                self._handle_resize()

            self._win = pg.display.set_mode(self._win_size.wh, self._flag | ADD_FLAGS)

    def _handle_events(self) -> None:
        """
        handles events,
        raises KeyboardInterrupt when window is closed
        """

        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise KeyboardInterrupt

            if event.type == pg.ACTIVEEVENT and event.state & pg.APPACTIVE:
                self._focused = event.gain == 1
            elif event.type == pg.VIDEORESIZE:
                if event.w < INIT_WIN_SIZE.w or event.h < INIT_WIN_SIZE.h:
                    event.w, event.h = max(event.w, INIT_WIN_SIZE.w), max(event.h, INIT_WIN_SIZE.h)
                    self._win = pg.display.set_mode((event.w, event.h), self._flag | ADD_FLAGS)
                self._win_size = Size(event.w, event.h)

                self._handle_resize()
            elif event.type == pg.KEYDOWN:
                self._handle_keys(event.key)
            elif event.type == pg.KEYUP:
                self._keys.remove(event.key)
                self._last_k_input = 0
                self._ctrl = bool(pg.key.get_mods() & pg.KMOD_CTRL)

            if event.type == FPS_UPT:
                FPS_TEXT.modify_text('FPS: ' + str(int(CLOCK.get_fps())))

        if not self._keys or pg.time.get_ticks() - self._last_k_input < 150:
            self._k = 0
        else:
            self._k = self._keys[-1]
            self._last_k_input = pg.time.get_ticks()

    def _handle_file_operations(self, mouse_info: MouseInfo) -> None:
        """
        handles the save as, open and close button actions
        takes mouse info
        """

        root: Tk
        path: str
        if SAVE_AS.upt(mouse_info) or (self._ctrl and self._k == pg.K_s):
            root = Tk()
            root.withdraw()

            path = asksaveasfilename(
                defaultextension='.png',
                filetypes=(('png Files', '*.png'), ('jpeg Files', '')),
                title='Save as'
            )
            root.destroy()

            if path:
                self._file_path = path
                fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)

        if LOAD.upt(mouse_info) or (self._ctrl and self._k == pg.K_o):
            if self._file_path:
                fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)

            root = Tk()
            root.withdraw()

            path = askopenfilename(
                defaultextension='.png',
                filetypes=(('png Files', '*.png'),),
                title='Open'
            )
            root.destroy()

            if path:
                self._file_path = path
                GRID_MANAGER.load_path(self._file_path)

        if (CLOSE.upt(mouse_info) or (self._ctrl and self._k == pg.K_q)) and self._file_path:
            fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)

            self._file_path = ''
            GRID_MANAGER.load_path(self._file_path)

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

                mouse_info: MouseInfo = MouseInfo(
                    *pg.mouse.get_pos(), pg.mouse.get_pressed(), pg.mouse.get_just_released()
                )

                closed: bool
                match self._state:
                    case 0:
                        GRID_MANAGER.upt(mouse_info, self._k, self._color, self._brush_size)

                        brush_size: int = BRUSH_SIZE_GRID.upt(mouse_info)
                        if brush_size != -1:
                            self._brush_size = brush_size + 1
                        elif self._ctrl and self._k <= 0x110000:  # chr limit
                            u: str = chr(self._k)
                            if u.isdigit() and 1 <= int(u) <= len(BRUSH_SIZE_GRID.check_boxes):
                                BRUSH_SIZE_GRID.set(int(u) - 1)
                                self._brush_size = int(u)

                        if ADD_COLOR.upt(mouse_info) or (self._ctrl and self._k == pg.K_a):
                            self._state = 1

                            COLOR_PICKER.ui.prev_mouse_cursor = pg.mouse.get_cursor()
                            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                            COLOR_PICKER.set(BLACK)

                        if MODIFY_GRID.upt(mouse_info) or (self._ctrl and self._k == pg.K_m):
                            self._state = 2

                            GRID_UI.ui.prev_mouse_cursor = pg.mouse.get_cursor()
                            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                            GRID_UI.set(GRID_MANAGER.grid.grid_size)

                        self._handle_file_operations(mouse_info)
                    case 1:
                        new_color: Optional[ColorType]
                        closed, new_color = COLOR_PICKER.upt(mouse_info, self._ctrl, self._k)
                        if closed:
                            if new_color:
                                self._color = new_color

                            self._state = 0
                    case 2:
                        new_size: Optional[Size]
                        closed, new_size = GRID_UI.upt(mouse_info, self._ctrl, self._k)
                        if closed:
                            if new_size:
                                GRID_MANAGER.resize(new_size)

                            self._state = 0

                self._redraw()
        except KeyboardInterrupt:
            if self._file_path:
                fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(self._file_path)
        except Exception:  # pylint: disable=broad-exception-caught
            if not self._file_path:
                name: str = 'new_file.png'
                i: int = 0
                while exists(name):
                    i += 1
                    name = f'new_file_{i}.png'
                self._file_path = name

            fromarray(GRID_MANAGER.grid.pixels, 'RGBA').save(self._file_path)
            with open('data.txt', 'w', encoding='utf-8') as f:
                f.write(self._file_path)

            print_exc()


if __name__ == '__main__':
    Dixel().run()
