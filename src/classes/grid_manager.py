"""
paintable pixel grid
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, Final, Optional

from src.utils import Point, Size, RectPos, MouseInfo
from src.const import ColorType, BlitSequence

INIT_PIXEL_SIZE: Final[int] = 18

EMPTY_1: Final[ColorType] = (75, 75, 75)
EMPTY_2: Final[ColorType] = (85, 85, 85)
TRANSPARENT: Final[Tuple[int, ...]] = (120, 120, 120, 125)


class Grid:
    """
    class to convert an image into a pixel array and blit a section of it into a grid
    """

    __slots__ = (
        '_init_pos', 'size', 'pixel_size', '_img', 'rect', 'pixels',
        '_empty_pixel', 'transparent_pixel'
    )

    def __init__(self, pos: RectPos) -> None:
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

        self.pixels: NDArray[np.uint8]
        self.load_img(None)

        self._empty_pixel: pg.SurfaceType = pg.Surface(self.pixel_size.wh)
        half_size: Size = Size((self.pixel_size.w + 1) // 2, (self.pixel_size.h + 1) // 2)
        for row in range(2):
            for col in range(2):
                rect: Tuple[int, int, int, int] = (
                    col * half_size.w, row * half_size.h, *half_size.wh
                )
                color: ColorType = EMPTY_1 if (row + col) % 2 == 0 else EMPTY_2
                pg.draw.rect(self._empty_pixel, color, rect)

        self.transparent_pixel: pg.SurfaceType = pg.Surface(self.pixel_size.wh, pg.SRCALPHA)
        self.transparent_pixel.fill(TRANSPARENT)

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
        self.transparent_pixel = pg.transform.scale(self.transparent_pixel, self.pixel_size.wh)

    def load_img(self, img: Optional[pg.SurfaceType]) -> None:
        """
        loads a surface's rgba values into a 3d array
        takes image if it's None it creates an empty grid
        """

        if not img:
            self.pixels = np.zeros((*self.size.wh, 4), dtype=np.uint8)

            return

        self.pixels = np.dstack(
            (pg.surfarray.pixels3d(img), pg.surfarray.pixels_alpha(img))
        )
        self.pixels = np.transpose(self.pixels, (1, 0, 2))

        add_rows: int = max(self.size.h - self.pixels.shape[0], 0)
        add_cols: int = max(self.size.w - self.pixels.shape[1], 0)
        if add_rows or add_cols:
            self.pixels = np.pad(
                self.pixels, ((0, add_rows), (0, add_cols), (0, 0)),
                constant_values=0
            )

    def get_grid(self, offset: Point, selected_pixel_pos: Optional[Tuple[int, int]]) -> None:
        """
        takes the offset from (0, 0) and the position of the pixel the mouse is hovering
        """

        sequence: BlitSequence = []

        grid_w: int = self.size.w
        pixel_w: int = self.pixel_size.w
        pixel_h: int = self.pixel_size.h
        pixels: NDArray[np.uint8] = self.pixels

        empty_pixel: pg.SurfaceType = self._empty_pixel
        pixel_surf: pg.SurfaceType = pg.Surface(self.pixel_size.wh)
        for y in range(self.size.h):
            for x in range(grid_w):
                pos: Tuple[int, int] = (x * pixel_w, y * pixel_h)

                if not pixels[y + offset.y, x + offset.x, -1]:
                    sequence.append((empty_pixel, pos))
                else:
                    pixel_surf.fill(pixels[y + offset.y, x + offset.x])
                    sequence.append((pixel_surf.copy(), pos))

        if selected_pixel_pos:
            sequence.append((self.transparent_pixel, selected_pixel_pos))

        self._img.fblits(sequence)


class GridManager:
    """
    class to create and edit a grid of pixel
    """

    __slots__ = (
        'grid', '_grid_offset', '_selected_pixel_pos', '_prev_mouse_pos', '_hovering',
        '_prev_mouse_pos', '_traveled_dist'
    )

    def __init__(self, pos: RectPos) -> None:
        """
        loads an image, creates surface and rect
        takes position
        """

        self.grid: Grid = Grid(pos)
        self._grid_offset: Point = Point(0, 0)

        self._selected_pixel_pos: Optional[Tuple[int, int]] = None
        self._hovering: bool = False

        self._prev_mouse_pos: Point = Point(*pg.mouse.get_pos())
        self._traveled_dist: Point = Point(0, 0)

        self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return self.grid.blit()

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self.grid.handle_resize(win_ratio_w, win_ratio_h)

    def load_path(self, path: str) -> None:
        """
        loads an image from a path and renders it into the grid
        takes path if it's empty it creates an empty grid
        """

        self._grid_offset = Point(0, 0)
        self._traveled_dist = Point(0, 0)

        img: Optional[pg.SurfaceType] = pg.image.load(path).convert_alpha() if path else None
        self.grid.load_img(img)

        self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)

    def _draw(
            self, mouse_info: MouseInfo, hoovering: bool, color: ColorType, brush_size: int
    ) -> bool:
        """
        gets the selected pixel and handles changing it
        takes mouse_info, hoovering bool, color and  brush size
        return the redraw grid flag
        """

        if not (hoovering or self.grid.rect.collidepoint(self._prev_mouse_pos.xy)):
            return False

        mouse_pixel: Point = Point(
            int(self._prev_mouse_pos.x - self.grid.rect.x) // self.grid.pixel_size.w,
            int(self._prev_mouse_pos.y - self.grid.rect.y) // self.grid.pixel_size.h
        )
        prev_mouse_pixel: Point = Point(
            int(mouse_info.x - self.grid.rect.x) // self.grid.pixel_size.w,
            int(mouse_info.y - self.grid.rect.y) // self.grid.pixel_size.h
        )

        start: Point = Point(mouse_pixel.x - brush_size // 2, mouse_pixel.y - brush_size // 2)
        end: Point = Point(
            prev_mouse_pixel.x - brush_size // 2, prev_mouse_pixel.y - brush_size // 2
        )

        redraw_grid: bool = False

        if hoovering and (start != end or not self._selected_pixel_pos):
            self._selected_pixel_pos = (
                end.x * self.grid.pixel_size.w, end.y * self.grid.pixel_size.h
            )
            redraw_grid = True

        if mouse_info.buttons[0] or mouse_info.buttons[2]:
            # get the coordinates of the grid pixels the mouse touched between frames
            steps: int = max(abs(end.x - start.x) + 1, abs(end.y - start.y) + 1)

            start.x = np.clip(start.x, 0, self.grid.size.w - 1)
            start.y = np.clip(start.y, 0, self.grid.size.h - 1)
            end.x = np.clip(end.x, 0, self.grid.size.w - 1)
            end.y = np.clip(end.y, 0, self.grid.size.h - 1)
            x_coords: NDArray[np.int_] = np.linspace(start.x, end.x, steps, dtype=int)
            y_coords: NDArray[np.int_] = np.linspace(start.y, end.y, steps, dtype=int)

            for point in zip(x_coords, y_coords):
                x: slice = slice(point[0], min(point[0] + brush_size, self.grid.size.w))
                y: slice = slice(point[1], min(point[1] + brush_size, self.grid.size.h))

                if mouse_info.buttons[0]:
                    self.grid.pixels[y, x] = color + (255,)
                else:
                    self.grid.pixels[y, x] = (0, 0, 0, 0)
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
            if abs(self._traveled_dist.x) > self.grid.pixel_size.w:
                direction = 1 if self._traveled_dist.x > 0 else -1

                pixels_traveled = abs(self._traveled_dist.x) // self.grid.pixel_size.w
                self._traveled_dist.x -= pixels_traveled * self.grid.pixel_size.w * direction

                cap = self.grid.pixels.shape[1] - self.grid.size.w
                self._grid_offset.x += pixels_traveled * direction
                self._grid_offset.x = np.clip(self._grid_offset.x, 0, cap)

                redraw_grid = True

            self._traveled_dist.y += self._prev_mouse_pos.y - mouse_info.y
            if abs(self._traveled_dist.y) > self.grid.pixel_size.h:
                direction = 1 if self._traveled_dist.y > 0 else -1

                pixels_traveled = abs(self._traveled_dist.y) // self.grid.pixel_size.h
                self._traveled_dist.y -= pixels_traveled * self.grid.pixel_size.h * direction

                cap = self.grid.pixels.shape[0] - self.grid.size.h
                self._grid_offset.y += pixels_traveled * direction
                self._grid_offset.y = np.clip(self._grid_offset.y, 0, cap)

                redraw_grid = True

        return redraw_grid

    def upt(self, mouse_info: MouseInfo, color: ColorType, brush_size: int) -> None:
        """
        makes the object interactable
        takes mouse info, color and brush size
        """

        redraw_grid: bool = False

        hoovering: bool = self.grid.rect.collidepoint(mouse_info.xy)
        if not hoovering:
            if self._hovering:
                self._selected_pixel_pos = None
                redraw_grid = True
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
                self._hovering = True

            if self.grid.transparent_pixel.get_width() != brush_size:
                self.grid.transparent_pixel = pg.transform.scale(
                    self.grid.transparent_pixel,
                    (self.grid.pixel_size.w * brush_size, self.grid.pixel_size.h * brush_size)
                )

        if self._draw(mouse_info, hoovering, color, brush_size):
            redraw_grid = True

        if self._move(mouse_info):
            redraw_grid = True

        if redraw_grid:
            self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)

        self._prev_mouse_pos = Point(*mouse_info.xy)
