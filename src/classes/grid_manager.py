"""
paintable pixel grid
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, Final, Optional

from src.utils import Point, Size, RectPos, MouseInfo
from src.const import EMPTY_1, EMPTY_2, ColorType, BlitSequence

INIT_PIXEL_DIM: Final[int] = 18

TRANSPARENT: Final[Tuple[int, ...]] = (120, 120, 120, 125)


class Grid:
    """
    class to convert an image into a pixel array and blit a section of it into a grid
    """

    __slots__ = (
        'size', '_init_pos', 'visible_area', 'pixel_dim', '_img', 'rect', 'pixels',
        '_empty_pixel', 'transparent_pixel'
    )

    def __init__(self, pos: RectPos) -> None:
        """
        loads an image into a fixed size grid then
        creates the surfaces used for empty and selected pixels
        takes position and image
        """

        self.size: Size = Size(32, 32)  # cols, rows

        self._init_pos: RectPos = pos
        self.visible_area: Size = Size(32, 32)
        self.pixel_dim: int = INIT_PIXEL_DIM

        self._img: pg.SurfaceType = pg.Surface(
            (self.pixel_dim * self.visible_area.w, self.pixel_dim * self.visible_area.h)
        )
        self.rect: pg.FRect = self._img.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self.pixels: NDArray[np.uint8]

        self._empty_pixel: pg.SurfaceType = pg.Surface((self.pixel_dim, self.pixel_dim))
        half_size: int = (self.pixel_dim + 1) // 2
        for row in range(2):
            for col in range(2):
                rect: Tuple[int, int, int, int] = (
                    col * half_size, row * half_size, half_size, half_size
                )
                color: ColorType = EMPTY_1 if (row + col) % 2 == 0 else EMPTY_2
                pg.draw.rect(self._empty_pixel, color, rect)

        self.transparent_pixel: pg.SurfaceType = pg.Surface(
            (self.pixel_dim, self.pixel_dim), pg.SRCALPHA
        )
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

        size_ratio: float = min(win_ratio_w, win_ratio_h)

        self.pixel_dim = int(INIT_PIXEL_DIM * size_ratio)
        size: Tuple[int, int] = (
            self.pixel_dim * self.visible_area.w, self.pixel_dim * self.visible_area.h
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._img = pg.transform.scale(self._img, size)
        self.rect = self._img.get_frect(**{self._init_pos.pos: pos})

        self._empty_pixel = pg.transform.scale(
            self._empty_pixel, (self.pixel_dim, self.pixel_dim)
        )
        self.transparent_pixel = pg.transform.scale(
            self.transparent_pixel, (self.pixel_dim, self.pixel_dim)
        )

    def resize(self, new_size: Size) -> bool:
        """
        resizes the grid
        returns whatever the grid should be updated or not
        """

        self.size = new_size

        prev_visible_area: Size = Size(self.visible_area.w, self.visible_area.h)
        self.visible_area = Size(
            min(self.size.w, 32), min(self.size.h, 32)
        )

        get_grid: bool = self.visible_area != prev_visible_area
        if get_grid:
            self._img = pg.Surface(
                (self.pixel_dim * self.visible_area.w, self.pixel_dim * self.visible_area.h)
            )
            self.rect = self._img.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        add_rows: int = self.size.h - self.pixels.shape[0]
        add_cols: int = self.size.w - self.pixels.shape[1]

        if add_rows < 0:
            self.pixels = self.pixels[:self.size.h, :, :]
        elif add_rows > 0:
            self.pixels = np.pad(
                self.pixels, ((0, add_rows), (0, 0), (0, 0)),
                constant_values=0
            )
        if add_cols < 0:
            self.pixels = self.pixels[:, :self.size.w, :]
        elif add_cols > 0:
            self.pixels = np.pad(
                self.pixels, ((0, 0), (0, add_cols), (0, 0)),
                constant_values=0
            )

        return get_grid

    def load_img(self, img: Optional[pg.SurfaceType]) -> None:
        """
        loads a surface's rgba values into a 3d array
        takes image if it's None it creates an empty grid
        """

        if not img:
            self.pixels = np.zeros((self.size.h, self.size.w, 4), dtype=np.uint8)

            return

        self.pixels = np.dstack(
            (pg.surfarray.pixels3d(img), pg.surfarray.pixels_alpha(img))
        )
        self.pixels = np.transpose(self.pixels, (1, 0, 2))

        self.resize(self.size)

    def get_grid(self, offset: Point, selected_pixel_pos: Optional[Tuple[int, int]]) -> None:
        """
        takes the offset from (0, 0) and the position of the pixel the mouse is hovering
        """

        sequence: BlitSequence = []

        area_w: int = self.visible_area.w
        pixel_dim: int = self.pixel_dim
        pixels: NDArray[np.uint8] = self.pixels

        empty_pixel: pg.SurfaceType = self._empty_pixel
        pixel_surf: pg.SurfaceType = pg.Surface((self.pixel_dim, self.pixel_dim))
        for y in range(self.visible_area.h):
            for x in range(area_w):
                pos: Tuple[int, int] = (x * pixel_dim, y * pixel_dim)

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

        self._selected_pixel_pos = None  # recalculate the selected pixel
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

        prev_mouse_pixel: Point = Point(
            int(self._prev_mouse_pos.x - self.grid.rect.x) // self.grid.pixel_dim,
            int(self._prev_mouse_pos.y - self.grid.rect.y) // self.grid.pixel_dim
        )
        mouse_pixel: Point = Point(
            int(mouse_info.x - self.grid.rect.x) // self.grid.pixel_dim,
            int(mouse_info.y - self.grid.rect.y) // self.grid.pixel_dim
        )

        start: Point = Point(
            prev_mouse_pixel.x - brush_size // 2, prev_mouse_pixel.y - brush_size // 2)
        end: Point = Point(
            mouse_pixel.x - brush_size // 2, mouse_pixel.y - brush_size // 2
        )

        redraw_grid: bool = False

        if hoovering and (start != end or not self._selected_pixel_pos):
            self._selected_pixel_pos = (
                end.x * self.grid.pixel_dim, end.y * self.grid.pixel_dim
            )
            redraw_grid = True

        if mouse_info.buttons[0] or mouse_info.buttons[2]:
            # get the coordinates of the grid pixels the mouse touched between frames
            steps: int = max(abs(end.x - start.x) + 1, abs(end.y - start.y) + 1)

            start.x = np.clip(
                start.x, -brush_size + 1, self.grid.visible_area.w - 1
            ) + self._grid_offset.x
            start.y = np.clip(
                start.y, -brush_size + 1, self.grid.visible_area.h - 1
            ) + self._grid_offset.y

            end.x = np.clip(
                end.x, -brush_size + 1, self.grid.visible_area.w - 1
            ) + self._grid_offset.x
            end.y = np.clip(
                end.y, -brush_size + 1, self.grid.visible_area.h - 1
            ) + self._grid_offset.y

            x_coords: NDArray[np.int_] = np.linspace(start.x, end.x, steps, dtype=int)
            y_coords: NDArray[np.int_] = np.linspace(start.y, end.y, steps, dtype=int)

            for point in zip(x_coords, y_coords):
                x: slice = slice(max(point[0], 0), min(point[0] + brush_size, self.grid.size.w))
                y: slice = slice(max(point[1], 0), min(point[1] + brush_size, self.grid.size.h))

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
            pixels_traveled: int

            self._traveled_dist.x += self._prev_mouse_pos.x - mouse_info.x
            if abs(self._traveled_dist.x) > self.grid.pixel_dim:
                pixels_traveled = round(self._traveled_dist.x / self.grid.pixel_dim)
                self._traveled_dist.x -= pixels_traveled * self.grid.pixel_dim

                self._grid_offset.x = np.clip(
                    self._grid_offset.x + pixels_traveled,
                    0, self.grid.size.w - self.grid.visible_area.w
                )

                redraw_grid = True

            self._traveled_dist.y += self._prev_mouse_pos.y - mouse_info.y
            if abs(self._traveled_dist.y) > self.grid.pixel_dim:
                pixels_traveled = round(self._traveled_dist.y / self.grid.pixel_dim)
                self._traveled_dist.y -= pixels_traveled * self.grid.pixel_dim

                self._grid_offset.y = np.clip(
                    self._grid_offset.y + pixels_traveled,
                    0, self.grid.size.h - self.grid.visible_area.h
                )

                redraw_grid = True

        return redraw_grid

    def resize(self, new_size: Size) -> None:
        """
        resizes the grid
        takes new size
        """

        self._grid_offset = Point(0, 0)
        self._traveled_dist = Point(0, 0)
        if self.grid.resize(new_size):
            self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)

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
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
                self._hovering = True

            if self.grid.transparent_pixel.get_width() != brush_size:
                self.grid.transparent_pixel = pg.transform.scale(
                    self.grid.transparent_pixel,
                    (self.grid.pixel_dim * brush_size, self.grid.pixel_dim * brush_size)
                )

        if self._draw(mouse_info, hoovering, color, brush_size):
            redraw_grid = True

        if self._move(mouse_info):
            redraw_grid = True

        if redraw_grid:
            self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)

        self._prev_mouse_pos = Point(*mouse_info.xy)
