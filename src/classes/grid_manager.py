"""
paintable pixel grid
"""

import pygame as pg
from numpy import dstack, transpose, pad, ndarray, dtype, uint8
from typing import Tuple, Final, Optional, Any

from src.utils import Point, Size, RectPos, MouseInfo
from src.const import ColorType, BlitSequence

INIT_PIXEL_SIZE: Final[int] = 24


class Grid:
    """
    class to convert an image into a pixel array and blit a section of it into a grid
    """

    __slots__ = (
        '_init_pos', 'size', 'pixel_size', '_img', 'rect', 'pixels',
        '_empty_pixel', '_transparent_pixel'
    )

    def __init__(self, pos: RectPos, img: pg.SurfaceType) -> None:
        """
        loads an image into a fixed size grid then
        creates the surfaces used for empty and selected pixels
        takes position and image
        """

        self._init_pos: RectPos = pos
        self.size: Size = Size(32, 32)
        self.pixel_size: Size = Size(INIT_PIXEL_SIZE, INIT_PIXEL_SIZE)

        self._img: pg.SurfaceType = pg.Surface(
            (self.pixel_size.w * self.size.w, self.pixel_size.h * self.size.h)
        )
        self.rect: pg.FRect = self._img.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self.pixels: ndarray[Any, dtype[uint8]] = dstack(
            (pg.surfarray.pixels3d(img), pg.surfarray.pixels_alpha(img))
        )
        self.pixels = transpose(self.pixels, (1, 0, 2))
        extra_rows: int = max(self.size.h - self.pixels.shape[0], 0)
        extra_cols: int = max(self.size.w - self.pixels.shape[1], 0)
        if extra_rows or extra_cols:
            self.pixels = pad(
                self.pixels, ((0, extra_rows), (0, extra_cols), (0, 0)),
                constant_values=0
            )

        self._empty_pixel: pg.SurfaceType = pg.Surface(self.pixel_size.wh)
        half_size: Size = Size((self.pixel_size.w + 1) // 2, (self.pixel_size.h + 1) // 2)
        for row in range(2):
            for col in range(2):
                rect: Tuple[int, int, int, int] = (
                    col * half_size.w, row * half_size.h, *half_size.wh
                )
                color: ColorType = (75, 75, 75) if not (row + col) % 2 else (85, 85, 85)
                pg.draw.rect(self._empty_pixel, color, rect)

        self._transparent_pixel: pg.SurfaceType = pg.Surface(self.pixel_size.wh, pg.SRCALPHA)
        self._transparent_pixel.fill((120, 120, 120, 150))

    def get_grid(self, offset: Point, selected_pixel_pos: Optional[Tuple[int, int]]) -> None:
        """
        takes the offset from (0, 0) and the position of the pixel the mouse is hovering
        """

        sequence: BlitSequence = []

        pixel_surf: pg.SurfaceType = pg.Surface(self.pixel_size.wh)
        for y in range(self.size.h):
            for x in range(self.size.w):
                pos: Tuple[int, int] = (x * self.pixel_size.w, y * self.pixel_size.h)

                if not self.pixels[y + offset.y, x + offset.x, -1]:
                    sequence.append((self._empty_pixel, pos))
                else:
                    pixel_surf.fill(self.pixels[y + offset.y, x + offset.x])
                    sequence.append((pixel_surf.copy(), pos))

        if selected_pixel_pos:
            sequence.append((self._transparent_pixel, selected_pixel_pos))

        self._img.fblits(sequence)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return [(self._img, self.rect.topleft)]

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self.pixel_size.w, self.pixel_size.h = (
            int(INIT_PIXEL_SIZE * win_ratio_w), int(INIT_PIXEL_SIZE * win_ratio_h)
        )
        size: Tuple[int, int] = (
            self.pixel_size.w * self.size.w, self.pixel_size.h * self.size.h
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._img = pg.transform.scale(self._img, size)
        self.rect = self._img.get_frect(**{self._init_pos.pos: pos})

        self._empty_pixel = pg.transform.scale(self._empty_pixel, self.pixel_size.wh)
        self._transparent_pixel = pg.transform.scale(self._transparent_pixel, self.pixel_size.wh)


class GridManager:
    """
    class to create and edit a grid of pixel
    """

    __slots__ = (
        '_grid', '_grid_offset', '_selected_pixel_pos', '_prev_mouse_pos', '_hovering',
        '_prev_mouse_pos', '_traveled_dist'
    )

    def __init__(self, pos: RectPos) -> None:
        """
        loads an image, creates surface and rect
        takes position
        """

        img: pg.SurfaceType = pg.image.load('test.png').convert_alpha()
        self._grid: Grid = Grid(pos, img)
        self._grid_offset: Point = Point(0, 0)

        self._selected_pixel_pos: Optional[Tuple[int, int]] = None
        self._hovering: bool = False

        self._prev_mouse_pos: Point = Point(*pg.mouse.get_pos())
        self._traveled_dist: Point = Point(0, 0)

        self._grid.get_grid(self._grid_offset, self._selected_pixel_pos)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return self._grid.blit()

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self._grid.handle_resize(win_ratio_w, win_ratio_h)

    def _draw(self, mouse_info: MouseInfo) -> bool:
        """
        gets the selected pixel and handles changing it
        takes mouse_info
        return the redraw grid flag
        """

        redraw_grid: bool = False

        rel_pos: Point = Point(
            int(mouse_info.x - self._grid.rect.x) // self._grid.pixel_size.w,
            int(mouse_info.y - self._grid.rect.y) // self._grid.pixel_size.h
        )
        abs_pos: Point = Point(
            rel_pos.y + self._grid_offset.y, rel_pos.x + self._grid_offset.x
        )

        prev_selected_pixel_pos: Optional[Tuple[int, int]] = self._selected_pixel_pos
        self._selected_pixel_pos = (
            rel_pos.x * self._grid.pixel_size.w, rel_pos.y * self._grid.pixel_size.h
        )

        redraw_grid = prev_selected_pixel_pos != self._selected_pixel_pos

        if mouse_info.buttons[0]:
            self._grid.pixels[abs_pos.xy] = (255, 255, 255, 255)
            redraw_grid = True
        elif mouse_info.buttons[2]:
            self._grid.pixels[abs_pos.xy] = (0, 0, 0, 0)
            redraw_grid = True

        return redraw_grid

    def _move(self, mouse_info: MouseInfo) -> bool:
        """
        allows the user change the section of the grid that is drawn
        takes mouse info
        returns the redraw grid flag
        """

        redraw_grid: bool = False

        if not mouse_info.buttons[1]:
            self._traveled_dist.x = self._traveled_dist.y = 0
        else:
            direction: int
            pixels_traveled: int
            cap: int

            self._traveled_dist.x += self._prev_mouse_pos.x - mouse_info.x
            if abs(self._traveled_dist.x) > self._grid.pixel_size.w:
                direction = 1 if self._traveled_dist.x > 0 else -1

                pixels_traveled = abs(self._traveled_dist.x) // self._grid.pixel_size.w
                self._traveled_dist.x -= pixels_traveled * self._grid.pixel_size.w * direction

                cap = self._grid.pixels.shape[1] - self._grid.size.w
                self._grid_offset.x += pixels_traveled * direction
                self._grid_offset.x = max(min(self._grid_offset.x, cap), 0)

                redraw_grid = True

            self._traveled_dist.y += self._prev_mouse_pos.y - mouse_info.y
            if abs(self._traveled_dist.y) > self._grid.pixel_size.h:
                direction = 1 if self._traveled_dist.y > 0 else -1

                pixels_traveled = abs(self._traveled_dist.y) // self._grid.pixel_size.h
                self._traveled_dist.y -= pixels_traveled * self._grid.pixel_size.h * direction

                cap = self._grid.pixels.shape[0] - self._grid.size.h
                self._grid_offset.y += pixels_traveled * direction
                self._grid_offset.y = max(min(self._grid_offset.y, cap), 0)

                redraw_grid = True

        self._prev_mouse_pos = Point(*mouse_info.xy)

        return redraw_grid

    def upt(self, mouse_info: MouseInfo) -> None:
        """
        makes the object interactable
        takes mouse info
        """

        redraw_grid: bool = False

        if not self._grid.rect.collidepoint(mouse_info.xy):
            if self._hovering:
                self._selected_pixel_pos = None
                redraw_grid = True
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
                self._hovering = True

            if self._draw(mouse_info):
                redraw_grid = True

        if self._move(mouse_info):
            redraw_grid = True

        if redraw_grid:
            self._grid.get_grid(self._grid_offset, self._selected_pixel_pos)