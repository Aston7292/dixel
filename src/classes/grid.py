'''
class to create a grid of pixels that can be changed via the mouse
'''

import pygame as pg
from numpy import dstack, transpose, ndarray, dtype, uint8, ceil
from typing import Tuple, Final, Optional, Any

from src.utils import Point, Size, RectPos
from src.const import S_INIT_WIN, ColorType, BlitSequence

PIXEL_RATIO: Final[Size] = Size(S_INIT_WIN.w // 25, S_INIT_WIN.h // 25)


class Grid:
    '''
    class to create a grid of pixels that can be changed via the mouse
    '''

    __slots__ = (
        '_pixels', '_s_img', '_s_pixel', '_surf', '_pos', '_rect',
        '_empty_pixel', '_transparent_pixel', '_selected_pixel'
    )

    def __init__(self, pos: RectPos) -> None:
        '''
        loads an image and creates the grid of pixels
        takes position
        '''

        img: pg.SurfaceType = pg.image.load('test.png').convert_alpha()

        self._pixels: ndarray[Any, dtype[uint8]] = dstack(
            (pg.surfarray.pixels3d(img), pg.surfarray.pixels_alpha(img))
        )
        self._pixels = transpose(self._pixels, (1, 0, 2))
        self._s_img: Size = Size(*self._pixels.shape[:2])

        self._s_pixel: Size = Size(
            S_INIT_WIN.w // PIXEL_RATIO.w, S_INIT_WIN.h // PIXEL_RATIO.h
        )

        self._surf: pg.SurfaceType = pg.Surface(
            (self._s_pixel.w * self._s_img.w, self._s_pixel.h * self._s_img.h)
        )

        self._pos: RectPos = pos
        self._rect: pg.Rect = self._surf.get_rect(**{self._pos.pos: self._pos.xy})

        self._empty_pixel: pg.SurfaceType = self._get_empty_pixel()
        self._transparent_pixel: pg.SurfaceType = pg.Surface(self._s_pixel.size, pg.SRCALPHA)
        self._transparent_pixel.fill((120, 120, 120, 150))
        self._selected_pixel: Optional[Point] = None

    def _get_empty_pixel(self) -> pg.SurfaceType:
        '''
        returns the surface used when representing a transparent pixel
        '''

        empty_pixel: pg.SurfaceType = pg.Surface((self._s_pixel.w, self._s_pixel.h))
        s_empty_pixel: Size = Size(ceil(self._s_pixel.w / 2), ceil(self._s_pixel.h / 2))

        for row in range(2):
            for col in range(2):
                rect: Tuple[int, int, int, int] = (
                    col * s_empty_pixel.w, row * s_empty_pixel.h, *s_empty_pixel.size
                )
                color: ColorType = (75, 75, 75) if not (row + col) % 2 else (85, 85, 85)

                pg.draw.rect(empty_pixel, color, rect)

        return empty_pixel

    def blit(self) -> BlitSequence:
        '''
        return a sequence to add in the main blit sequence
        '''

        grid_sequence: BlitSequence = tuple()

        for y in range(self._s_img.h):
            for x in range(self._s_img.w):
                pos: Point = Point(x * self._s_pixel.w, y * self._s_pixel.h)

                if not self._pixels[y, x, -1]:
                    grid_sequence += ((self._empty_pixel, pos.xy),)
                else:
                    pg.draw.rect(self._surf, self._pixels[y, x], (pos.xy, self._s_pixel.size))

        if self._selected_pixel:
            grid_sequence += ((self._transparent_pixel, self._selected_pixel.xy),)

        self._surf.fblits(grid_sequence)

        return ((self._surf, self._rect.topleft),)

    def handle_resize(self, win_size: Size) -> None:
        '''
        resizes surfaces
        takes window size
        '''

        self._s_pixel = Size(
            win_size.w // PIXEL_RATIO.w, win_size.h // PIXEL_RATIO.h
        )

        self._surf = pg.Surface((self._s_pixel.w * self._s_img.w, self._s_pixel.h * self._s_img.h))
        self._rect = self._surf.get_rect(**{self._pos.pos: self._pos.xy})

        self._empty_pixel = self._get_empty_pixel()
        self._transparent_pixel = pg.Surface((self._s_pixel.w, self._s_pixel.h), pg.SRCALPHA)
        self._transparent_pixel.fill((120, 120, 120, 150))

    def upt(self, mouse_pos: Point, mouse_buttons: Tuple[bool, bool, bool]) -> None:
        '''
        makes the grid interactable
        takes mouse position and buttons state
        '''

        if not self._rect.collidepoint(mouse_pos.xy):
            self._selected_pixel = None

            return

        pos: Point = Point(
            (mouse_pos.x - self._rect.x) // self._s_pixel.w,
            (mouse_pos.y - self._rect.y) // self._s_pixel.h
        )

        if mouse_buttons[0]:
            self._pixels[pos.y, pos.x] = (255, 255, 255, 255)
        elif mouse_buttons[2]:
            self._pixels[pos.y, pos.x] = (0, 0, 0, 0)

        self._selected_pixel = Point(pos.x * self._s_pixel.w, pos.y * self._s_pixel.h)
