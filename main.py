'''
drawing program for pixel art
'''

import pygame as pg
from pygetwindow import getWindowsWithTitle, BaseWindow  # type: ignore
from screeninfo import get_monitors, Monitor
from numpy import array, ndarray, dtype, uint8, bool_, ceil
from copy import copy
from traceback import print_exc
from typing import Tuple, Final, Any

pg.init()

from text import Text
from utils import Point, Size
from const import S_INIT_WIN, ColorType, BlitPair

ADD_FLAGS: Final[int] = pg.DOUBLEBUF | pg.HWSURFACE

PIXEL_RATIO: Final[Size] = Size(S_INIT_WIN.w // 25, S_INIT_WIN.h // 25)

BLACK: Final[ColorType] = (0, 0, 0)

FPS_TEXT: Final[Text] = Text('FPS: 0', Point(0, 0))

FPS_UPT: Final[int] = pg.USEREVENT + 1
pg.time.set_timer(FPS_UPT, 1_000)
CLOCK: Final[pg.Clock] = pg.time.Clock()

class Dixel:
    '''
    drawing program for pixel art
    '''

    __slots__ = (
        '_s_win', '_s_prev_win', '_flag', '_full_screen', '_focused', '_win',
        '_s_pixel', '_s_img', '_grid', '_pixels', '_pixels_alpha',
        '_empty_pixel', '_transparent_pixel'
    )

    def __init__(self) -> None:
        '''
        initializes the window
        '''

        self._s_win: Size = Size(S_INIT_WIN.w, S_INIT_WIN.h)
        self._s_prev_win: Size = copy(self._s_win)
        self._flag: int = pg.RESIZABLE
        self._full_screen: bool = False
        self._focused: bool = True

        self._win: pg.SurfaceType = pg.display.set_mode(
            (self._s_win.w, self._s_win.h), self._flag | ADD_FLAGS
        )
        pg.display.set_caption('Dixel')

        self._s_pixel: Size = Size(
            self._s_win.w // PIXEL_RATIO.w, self._s_win.h // PIXEL_RATIO.h
        )

        img: pg.SurfaceType = pg.image.load('test.png').convert_alpha()
        self._s_img: Size = Size(*img.get_size())

        s_grid: Size = Size(self._s_pixel.w * self._s_img.w, self._s_pixel.h * self._s_img.h)
        self._grid: pg.Rect = pg.Rect(
            (self._s_win.w - s_grid.w) // 2, (self._s_win.h - s_grid.h) // 2,
            s_grid.w, s_grid.h
        )

        self._pixels: ndarray[Any, dtype[uint8]] = pg.surfarray.array3d(img)
        self._pixels_alpha: ndarray[Any, dtype[bool_]] = array(
            [[bool(value) for value in row] for row in pg.surfarray.array_alpha(img)], dtype=bool_
        )

        self._empty_pixel: pg.SurfaceType = self._get_empty_pixel()
        self._transparent_pixel: pg.SurfaceType = pg.Surface(
            (self._s_pixel.w, self._s_pixel.h), pg.SRCALPHA
        )
        self._transparent_pixel.fill((120, 120, 120, 150))

    def _get_empty_pixel(self) -> pg.SurfaceType:
        '''
        return the surface used when representing a transparent pixel
        '''

        empty_pixel: pg.SurfaceType = pg.Surface((self._s_pixel.w, self._s_pixel.h))
        s_empty_pixel: Size = Size(ceil(self._s_pixel.w / 2), ceil(self._s_pixel.h / 2))

        for row in range(2):
            for col in range(2):
                rect: Tuple[int, int, int, int] = (
                    col * s_empty_pixel.w, row * s_empty_pixel.h, s_empty_pixel.w, s_empty_pixel.h
                )
                color: ColorType = (75, 75, 75) if not (row + col) % 2 else (85, 85, 85)

                pg.draw.rect(empty_pixel, color, rect)

        return empty_pixel

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

        self._s_pixel = Size(
            self._s_win.w // PIXEL_RATIO.w, self._s_win.h // PIXEL_RATIO.h
        )

        s_grid = Size(self._s_pixel.w * self._s_img.w, self._s_pixel.h * self._s_img.h)
        self._grid = pg.Rect(
            (self._s_win.w - s_grid.w) // 2, (self._s_win.h - s_grid.h) // 2,
            s_grid.w, s_grid.h
        )

        self._empty_pixel = self._get_empty_pixel()
        self._transparent_pixel = pg.Surface((self._s_pixel.w, self._s_pixel.h), pg.SRCALPHA)
        self._transparent_pixel.fill((120, 120, 120, 150))

        FPS_TEXT.handle_resize(self._s_win.h)

    def _handle_keys(self, k: int) -> None:
        '''
        handles keyboard inputs
        takes the pressed k
        raises KeyboardInterrupt when esc is pressed
        '''

        if k == pg.K_ESCAPE:
            raise KeyboardInterrupt

        if k == pg.K_F1:
            if self._s_win.w != S_INIT_WIN.w or self._s_win.h != S_INIT_WIN.h:
                self._s_win, self._flag = Size(S_INIT_WIN.w, S_INIT_WIN.h), pg.RESIZABLE
                self._full_screen = False
                self._win = pg.display.set_mode(
                    (self._s_win.w, self._s_win.h), self._flag | ADD_FLAGS
                )

                self._handle_resize()
        elif k == pg.K_F11:
            self._full_screen = not self._full_screen

            if not self._full_screen:
                self._s_win, self._flag = copy(self._s_prev_win), pg.RESIZABLE
            else:
                # fullscreen looks better on a big window
                self._s_prev_win = copy(self._s_win)
                self._s_win, self._flag = Size(*self._get_monitor_size()), pg.FULLSCREEN
            self._win = pg.display.set_mode(
                (self._s_win.w, self._s_win.h), self._flag | ADD_FLAGS
            )

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
                    self._win = pg.display.set_mode(
                        (event.w, event.h), self._flag | ADD_FLAGS
                    )
                self._s_win = Size(event.w, event.h)

                self._handle_resize()
            elif event.type == pg.KEYDOWN:
                self._handle_keys(event.key)

            if event.type == FPS_UPT:
                FPS_TEXT.modify_text('FPS: ' + str(int(CLOCK.get_fps())))

    def _redraw(self) -> None:
        '''
        redraw the screen every frame
        '''

        self._win.fill(BLACK)
        blit_sequence: Tuple[BlitPair, ...] = tuple()

        mouse_pos: Point = Point(*pg.mouse.get_pos())
        mouse_buttons: Tuple[bool, bool, bool] = pg.mouse.get_pressed()

        selected_pixel: Point
        if not self._grid.collidepoint(mouse_pos.x, mouse_pos.y):
            selected_pixel = Point(-1, -1)
        else:
            x_pos: int = (mouse_pos.x - self._grid.x) // self._s_pixel.w
            y_pos: int = (mouse_pos.y - self._grid.y) // self._s_pixel.h
            selected_pixel = Point(x_pos, y_pos)

        for x in range(self._s_img.w):
            for y in range(self._s_img.h):
                hovering: bool = x == selected_pixel.x and y == selected_pixel.y
                pos: Point = Point(
                    self._grid.x + (x * self._s_pixel.w), self._grid.y + (y * self._s_pixel.h)
                )

                if hovering:
                    if mouse_buttons[0]:
                        self._pixels[x, y], self._pixels_alpha[x, y] = (255, 255, 255), True
                    elif mouse_buttons[2]:
                        self._pixels[x, y], self._pixels_alpha[x, y] = (0, 0, 0), False

                if self._pixels_alpha[x, y]:
                    pg.draw.rect(
                        self._win, self._pixels[x, y],
                        (pos.x, pos.y, self._s_pixel.w, self._s_pixel.h)
                    )
                else:
                    blit_sequence += ((self._empty_pixel, (pos.x, pos.y)),)

                if hovering:
                    blit_sequence += ((self._transparent_pixel, (pos.x, pos.y)),)
        blit_sequence += (FPS_TEXT.blit(),)

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

                self._redraw()
        except KeyboardInterrupt:
            pass  # save only if user is already working on a file
        except Exception:  # pylint: disable=broad-exception-caught
            print_exc()  # save no matter what

if __name__ == '__main__':
    Dixel().run()
