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
        '_init_pos', 'grid_size', 'pixel_size', '_surf', 'rect', 'pixels',
        '_empty_pixel', '_transparent_pixel'
    )

    def __init__(self, pos: RectPos, img: pg.SurfaceType) -> None:
        """
        loads an image into a fixed size grid then
        creates the surfaces used for empty and selected pixels
        takes position and image
        """

        self._init_pos: RectPos = pos
        self.grid_size: Size = Size(32, 32)
        self.pixel_size: Size = Size(INIT_PIXEL_SIZE, INIT_PIXEL_SIZE)

        self._surf: pg.SurfaceType = pg.Surface(
            (self.pixel_size.w * self.grid_size.w, self.pixel_size.h * self.grid_size.h)
        )
        self.rect: pg.FRect = self._surf.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self.pixels: ndarray[Any, dtype[uint8]] = dstack(
            (pg.surfarray.pixels3d(img), pg.surfarray.pixels_alpha(img))
        )
        self.pixels = transpose(self.pixels, (1, 0, 2))
        extra_rows: int = max(self.grid_size.h - self.pixels.shape[0], 0)
        extra_cols: int = max(self.grid_size.w - self.pixels.shape[1], 0)
        if extra_rows or extra_cols:
            self.pixels = pad(
                self.pixels, ((0, extra_rows), (0, extra_cols), (0, 0)),
                'constant', constant_values=0
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

    def blit(self, offset: Point, selected_pixel: Optional[Tuple[int, int]]) -> BlitSequence:
        """
        takes the offset from (0, 0) and the position of the pixel the mouse is hovering
        return a sequence to add in the main blit sequence
        """

        grid_sequence: list[Tuple[pg.SurfaceType, Tuple[int, int]]] = []

        grid_w: int = self.grid_size.w
        pixel_w: int = self.pixel_size.w
        pixel_h: int = self.pixel_size.h

        grid_x: int = int(self.rect.x)
        grid_y: int = int(self.rect.y)

        pixels: ndarray[Any, dtype[uint8]] = self.pixels
        pixel_surf: pg.SurfaceType = pg.Surface(self.pixel_size.wh)
        empty_pixel: pg.SurfaceType = self._empty_pixel

        for y in range(self.grid_size.h):
            y_pos: int = grid_y + y * pixel_h
            for x in range(grid_w):
                if not pixels[y + offset.y, x + offset.x, 3]:
                    grid_sequence.append((empty_pixel, (grid_x + x * pixel_w, y_pos)))
                else:
                    pixel_surf.fill(pixels[y + offset.y, x + offset.x])
                    grid_sequence.append((pixel_surf.copy(), (grid_x + x * pixel_w, y_pos)))

        if selected_pixel:
            grid_sequence.append((self._transparent_pixel, selected_pixel))

        return tuple(grid_sequence)

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self.pixel_size.w, self.pixel_size.h = (
            int(INIT_PIXEL_SIZE * win_ratio_w), int(INIT_PIXEL_SIZE * win_ratio_h)
        )
        size: Tuple[int, int] = (
            self.pixel_size.w * self.grid_size.w, self.pixel_size.h * self.grid_size.h
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._surf = pg.Surface(size)
        self.rect = self._surf.get_frect(**{self._init_pos.pos: pos})

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
        self._grid_offset: Point = Point(0 ,0)

        self._selected_pixel_pos: Optional[Tuple[int, int]] = None
        self._hovering: bool = False

        self._prev_mouse_pos: Point = Point(*pg.mouse.get_pos())
        self._traveled_dist: Point = Point(0, 0)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return self._grid.blit(self._grid_offset, self._selected_pixel_pos)

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self._grid.handle_resize(win_ratio_w, win_ratio_h)

    def _draw(self, mouse_info: MouseInfo) -> None:
        """
        gets the selected pixel
        and handles changing it
        takes mouse_info
        """

        rel_pos: Point = Point(
            int(mouse_info.x - self._grid.rect.x) // self._grid.pixel_size.w,
            int(mouse_info.y - self._grid.rect.y) // self._grid.pixel_size.h
        )
        abs_pos: Point = Point(
            rel_pos.y + self._grid_offset.y, rel_pos.x + self._grid_offset.x
        )

        self._selected_pixel_pos = (
            int(self._grid.rect.x) + rel_pos.x * self._grid.pixel_size.w,
            int(self._grid.rect.y) + rel_pos.y * self._grid.pixel_size.h
        )

        if mouse_info.buttons[0]:
            self._grid.pixels[abs_pos.xy] = (255, 255, 255, 255)
        elif mouse_info.buttons[2]:
            self._grid.pixels[abs_pos.xy] = (0, 0, 0, 0)

    def _move(self, mouse_info: MouseInfo):
        """
        allows the user change the section of the grid that is drawn
        takes mouse info
        """

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

                cap = self._grid.pixels.shape[1] - self._grid.grid_size.w
                self._grid_offset.x += pixels_traveled * direction
                self._grid_offset.x = max(min(self._grid_offset.x, cap), 0)

            self._traveled_dist.y += self._prev_mouse_pos.y - mouse_info.y
            if abs(self._traveled_dist.y) > self._grid.pixel_size.h:
                direction = 1 if self._traveled_dist.y > 0 else -1

                pixels_traveled = abs(self._traveled_dist.y) // self._grid.pixel_size.h
                self._traveled_dist.y -= pixels_traveled * self._grid.pixel_size.h * direction

                cap = self._grid.pixels.shape[0] - self._grid.grid_size.h
                self._grid_offset.y += pixels_traveled * direction
                self._grid_offset.y = max(min(self._grid_offset.y, cap), 0)

        self._prev_mouse_pos = Point(*mouse_info.xy)

    def upt(self, mouse_info: MouseInfo) -> None:
        """
        makes the object interactable
        takes mouse info
        """

        if not self._grid.rect.collidepoint(mouse_info.xy):
            if self._hovering:
                self._selected_pixel_pos = None
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)  # TODO: replace with pencil
                self._hovering = True
            self._draw(mouse_info)

        self._move(mouse_info)
