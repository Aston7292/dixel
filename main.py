"""
drawing program for pixel art
"""

import pygame as pg

from copy import copy
from traceback import print_exc
from typing import Tuple, Final

pg.init()

from src.classes.color_manager import ColorPicker
from src.classes.grid_manager import GridManager
from src.classes.text import Text
from src.classes.button import Button
from src.utils import RectPos, Size, MouseInfo, get_monitor_size
from src.const import INIT_WIN_SIZE, BLACK, BlitSequence

ADD_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE
WIN: Final[pg.SurfaceType] = pg.display.set_mode(
    (INIT_WIN_SIZE.w, INIT_WIN_SIZE.h), pg.RESIZABLE | ADD_FLAGS
)
pg.display.set_caption('Dixel')

ADD_COLOR_1: Final[pg.SurfaceType] = pg.Surface((100, 100))
ADD_COLOR_1.fill('goldenrod')
ADD_COLOR_2: Final[pg.SurfaceType] = pg.Surface((100, 100))
ADD_COLOR_2.fill('darkgoldenrod4')

GRID: Final[GridManager] = GridManager(
    RectPos(INIT_WIN_SIZE.w / 2, INIT_WIN_SIZE.h / 2, 'center')
)
ADD_COLOR: Final[Button] = Button(
    RectPos(INIT_WIN_SIZE.w - 50, INIT_WIN_SIZE.h - 50, 'bottomright'),
    (ADD_COLOR_1, ADD_COLOR_2), 'add color'
)
FPS_TEXT: Final[Text] = Text(RectPos(0, 0, 'topleft'), 32, 'FPS: 0')

COLOR_PICKER: Final[ColorPicker] = ColorPicker(
    RectPos(INIT_WIN_SIZE.w / 2, INIT_WIN_SIZE.h / 2, 'center')
)

FPS_UPT: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPS_UPT, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()


class Dixel:
    """
    drawing program for pixel art
    """

    __slots__ = (
        '_win_size', '_prev_win_size', '_flag', '_full_screen', '_focused', '_win', '_state'
    )

    def __init__(self) -> None:
        """
        initializes the window
        """

        self._win_size: Size = copy(INIT_WIN_SIZE)
        self._prev_win_size: Tuple[int, int] = self._win_size.wh
        self._flag: int = pg.RESIZABLE
        self._full_screen: bool = False
        self._focused: bool = True

        self._win: pg.SurfaceType = WIN

        self._state: int = 0

    def _handle_resize(self) -> None:
        """
        resizes objects
        """

        win_ratio_w: float = self._win_size.w / INIT_WIN_SIZE.w
        win_ratio_h: float = self._win_size.h / INIT_WIN_SIZE.h

        GRID.handle_resize(win_ratio_w, win_ratio_h)
        ADD_COLOR.handle_resize(win_ratio_w, win_ratio_h)
        FPS_TEXT.handle_resize(win_ratio_w, win_ratio_h)

        COLOR_PICKER.handle_resize(win_ratio_w, win_ratio_h)

    def _handle_keys(self, k: int) -> None:
        """
        handles keyboard inputs
        takes the pressed key
        raises KeyboardInterrupt when esc is pressed
        """

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

            if event.type == FPS_UPT:
                FPS_TEXT.modify_text('FPS: ' + str(int(CLOCK.get_fps())))

    def _redraw(self) -> None:
        """
        redraws the screen
        """

        self._win.fill(BLACK)

        blit_sequence: BlitSequence = []
        blit_sequence += GRID.blit()
        blit_sequence += ADD_COLOR.blit()
        blit_sequence += FPS_TEXT.blit()

        if self._state == 1:
            blit_sequence += COLOR_PICKER.blit()

        self._win.fblits(blit_sequence)
        pg.display.flip()

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

                match self._state:
                    case 0:
                        GRID.upt(mouse_info)

                        if ADD_COLOR.upt(mouse_info, True):
                            self._state = 1
                    case 1:
                        if COLOR_PICKER.upt(mouse_info):
                            self._state = 0

                self._redraw()
        except KeyboardInterrupt:
            pass  # save only if user is already working on a file
        except Exception:  # pylint: disable=broad-exception-caught
            print_exc()  # save no matter what


if __name__ == '__main__':
    Dixel().run()
