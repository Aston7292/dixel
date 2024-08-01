'''
drawing program for pixel art
'''

import pygame as pg
from pygetwindow import getWindowsWithTitle, BaseWindow  # type: ignore
from screeninfo import get_monitors, Monitor

from copy import copy
from traceback import print_exc
from typing import Tuple, Final

from src.classes.grid import Grid
from src.classes.text import Text
from src.classes.button import Button
from src.utils import Point, RectPos, Size
from src.const import S_INIT_WIN, BLACK, BlitSequence

pg.init()

ADD_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE
WIN: Final[pg.SurfaceType] = pg.display.set_mode(
    (S_INIT_WIN.w, S_INIT_WIN.h), pg.RESIZABLE | ADD_FLAGS
)
pg.display.set_caption('Dixel')

img1 = pg.Surface((100, 100))
img1.fill('white')
img2 = pg.Surface((100, 100))
img2.fill('red')

GRID: Final[Grid] = Grid(RectPos((S_INIT_WIN.w // 2, S_INIT_WIN.h // 2), 'center'))
PICK_COLOR: Final[Button] = Button((img1, img2), RectPos((100, 100), 'center'), 'hello world')
FPS_TEXT: Final[Text] = Text(32, 'FPS: 0', RectPos((10, 0), 'topleft'))

FPS_UPT: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPS_UPT, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()


# TODO: https://stackoverflow.com/questions/34910086/pygame-how-do-i-resize-a-surface-and-keep-all-objects-within-proportionate-to-t
class Dixel:
    '''
    drawing program for pixel art
    '''

    __slots__ = (
        '_s_win', '_s_prev_win', '_flag', '_full_screen', '_focused', '_win', '_picking_color'
    )

    def __init__(self) -> None:
        '''
        initializes the window
        '''

        self._s_win: Size = copy(S_INIT_WIN)
        self._s_prev_win: Size = copy(self._s_win)
        self._flag: int = pg.RESIZABLE
        self._full_screen: bool = False
        self._focused: bool = True
        self._win: pg.SurfaceType = WIN

        self._picking_color: bool = False

    def _get_monitor_size(self) -> tuple[int, int]:
        '''
        returns the size of the monitor in which the window is in
        '''

        win_handler: BaseWindow = getWindowsWithTitle('Dixel')[0]
        monitors: Tuple[Monitor, ...] = tuple(get_monitors())
        for monitor in monitors:
            if (
                monitor.x <= win_handler.left < monitor.x + monitor.width and
                monitor.y <= win_handler.top < monitor.y + monitor.height
            ):
                return monitor.width, monitor.height

        return 0, 0

    def _handle_resize(self) -> None:
        '''
        resizes objects
        '''

        GRID.handle_resize(self._s_win)
        FPS_TEXT.handle_resize(self._s_win)

    def _handle_keys(self, k: int) -> None:
        '''
        handles keyboard inputs
        takes the pressed key
        raises KeyboardInterrupt when esc is pressed
        '''

        if k == pg.K_ESCAPE:
            raise KeyboardInterrupt

        if k == pg.K_F1:
            if self._s_win.w != S_INIT_WIN.w or self._s_win.h != S_INIT_WIN.h:
                self._s_win, self._flag = Size(S_INIT_WIN.w, S_INIT_WIN.h), pg.RESIZABLE
                self._full_screen = False
                self._win = pg.display.set_mode(self._s_win.size, self._flag | ADD_FLAGS)

                self._handle_resize()
        elif k == pg.K_F11:
            self._full_screen = not self._full_screen

            if not self._full_screen:
                self._s_win, self._flag = copy(self._s_prev_win), pg.RESIZABLE
            else:
                # fullscreen looks better on a big window
                self._s_prev_win = copy(self._s_win)
                self._s_win, self._flag = Size(*self._get_monitor_size()), pg.FULLSCREEN
            self._win = pg.display.set_mode(self._s_win.size, self._flag | ADD_FLAGS)

            self._handle_resize()

    def _handle_events(self) -> None:
        '''
        handles events,
        raises KeyboardInterrupt when window is closed
        '''

        for event in pg.event.get():
            if event.type == pg.QUIT:
                raise KeyboardInterrupt

            if event.type == pg.ACTIVEEVENT and event.state & pg.APPACTIVE:
                self._focused = event.gain == 1
            elif event.type == pg.VIDEORESIZE:
                if event.w < S_INIT_WIN.w or event.h < S_INIT_WIN.h:
                    event.w, event.h = max(event.w, S_INIT_WIN.w), max(event.h, S_INIT_WIN.h)
                    self._win = pg.display.set_mode((event.w, event.h), self._flag | ADD_FLAGS)
                self._s_win = Size(event.w, event.h)

                self._handle_resize()
            elif event.type == pg.KEYDOWN:
                self._handle_keys(event.key)

            if event.type == FPS_UPT:
                FPS_TEXT.modify_text('FPS: ' + str(int(CLOCK.get_fps())))

    def _redraw(self) -> None:
        '''
        redraws the screen
        '''

        self._win.fill(BLACK)

        blit_sequence: BlitSequence = tuple()
        blit_sequence += GRID.blit()
        blit_sequence += PICK_COLOR.blit()
        blit_sequence += FPS_TEXT.blit()

        self._win.fblits(blit_sequence)
        pg.display.flip()

    def run(self) -> None:
        '''
        game loop
        '''

        try:
            while True:
                CLOCK.tick(60)

                self._handle_events()
                if not self._focused:
                    continue

                mouse_pos: Point = Point(*pg.mouse.get_pos())
                mouse_buttons: Tuple[bool, bool, bool] = pg.mouse.get_pressed()

                if not self._picking_color:
                    GRID.upt(mouse_pos, mouse_buttons)

                    if PICK_COLOR.click(mouse_pos, mouse_buttons):
                        print(1)

                self._redraw()
        except KeyboardInterrupt:
            pass  # save only if user is already working on a file
        except Exception:  # pylint: disable=broad-exception-caught
            print_exc()  # save no matter what

if __name__ == '__main__':
    Dixel().run()
