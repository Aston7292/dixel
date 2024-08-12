"""
paintable pixel grid with minimap
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, List, Final, Optional

from src.utils import Point, Size, RectPos, MouseInfo
from src.const import WHITE, EMPTY_1, EMPTY_2, ColorType, BlitSequence

TRANSPARENT: Final[Tuple[int, ...]] = (120, 120, 120, 125)


class Grid:
    """
    class to convert an image into a pixel array and blit a section of it into a grid
    """

    __slots__ = (
        'grid_size', 'grid_visible_area', '_win_ratio', '_grid_init_pos', '_grid_pos',
        '_grid_init_pixel_dim', 'grid_pixel_dim', '_grid_img', 'grid_rect', 'pixels',
        '_empty_pixel', '_transparent_pixel', '_minimap_init_pos', '_minimap_pos',
        '_minimap_img', '_minimap_rect', '_minimap_init_size',
        '_small_minimap_img_1', '_small_minimap_img_2', '_small_grid_img',
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        loads an image into a fixed size grid,
        creates the surfaces used for empty and selected pixels
        and creates a minimap in the top right corner
        takes grid and minimap position
        """

        self.grid_size: Size = Size(64, 64)  # cols, rows
        self.grid_visible_area: Size = Size(32, 32)

        self._grid_init_pos: RectPos = grid_pos
        self._grid_pos: Tuple[float, float] = self._grid_init_pos.xy

        self._grid_init_pixel_dim: int = 18
        self.grid_pixel_dim: int = self._grid_init_pixel_dim

        self._grid_img: pg.SurfaceType = pg.Surface((
            self.grid_visible_area.w * self.grid_pixel_dim,
            self.grid_visible_area.h * self.grid_pixel_dim
        ))
        self.grid_rect: pg.FRect = self._grid_img.get_frect(
            **{self._grid_init_pos.pos: self._grid_init_pos.xy}
        )

        self.pixels: NDArray[np.uint8] = np.zeros(
            (self.grid_size.h, self.grid_size.w, 4), dtype=np.uint8
        )

        self._empty_pixel: pg.SurfaceType = pg.Surface((2, 2))
        for row in range(2):
            for col in range(2):
                pixel_color: ColorType = EMPTY_1 if (row + col) % 2 == 0 else EMPTY_2
                self._empty_pixel.set_at((col, row), pixel_color)

        self._transparent_pixel: pg.SurfaceType = pg.Surface(
            (2, 2), pg.SRCALPHA
        )
        self._transparent_pixel.fill(TRANSPARENT)

        self._minimap_init_pos: RectPos = minimap_pos
        self._minimap_pos: Tuple[float, float] = self._minimap_init_pos.xy

        self._minimap_img: pg.SurfaceType = pg.Surface((200, 200))
        self._minimap_rect: pg.FRect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.pos: self._minimap_init_pos.xy}
        )

        self._minimap_init_size: Size = Size(
            int(self._minimap_rect.w), int(self._minimap_rect.h)
        )

        self._win_ratio: float = 1

        self._small_minimap_img_1: pg.SurfaceType = pg.Surface(
            (self.grid_size.w * 2, self.grid_size.h * 2)
        )
        self._small_minimap_img_2: pg.SurfaceType = self._small_minimap_img_1.copy()  # adds square
        self._small_grid_img: pg.SurfaceType = self._small_minimap_img_1.subsurface(
            (0, 0, self.grid_visible_area.w * 2, self.grid_visible_area.h * 2)
        )

        self.update_full(Point(0, 0), None)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return [
            (self._grid_img, self.grid_rect.topleft),
            (self._minimap_img, self._minimap_rect.topleft)
        ]

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self._win_ratio = min(win_ratio_w, win_ratio_h)

        self.grid_pixel_dim = int(self._grid_init_pixel_dim * self._win_ratio)

        grid_img_size: Tuple[int, int] = (
            int(self.grid_visible_area.w * self.grid_pixel_dim),
            int(self.grid_visible_area.h * self.grid_pixel_dim)
        )
        self._grid_pos = (
            self._grid_init_pos.x * win_ratio_w, self._grid_init_pos.y * win_ratio_h
        )

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_img_size)
        self.grid_rect = self._grid_img.get_frect(**{self._grid_init_pos.pos: self._grid_pos})

        minimap_pixel_dim: float = min(
            self._minimap_init_size.w / self.grid_size.w * self._win_ratio,
            self._minimap_init_size.h / self.grid_size.h * self._win_ratio
        )

        minimap_img_size: Tuple[int, int] = (
            int(self.grid_size.w * minimap_pixel_dim), int(self.grid_size.h * minimap_pixel_dim)
        )
        self._minimap_pos = (
            self._minimap_init_pos.x * win_ratio_w, self._minimap_init_pos.y * win_ratio_h
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_img_size)
        self._minimap_rect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.pos: self._minimap_pos}
        )

    def resize(
            self, new_size: Size, offset: Point, selected_pixel_pos: Optional[Tuple[int, int]]
    ) -> None:
        """
        resizes the grid
        takes new size and offset, selected pixel
        """

        self.grid_size = new_size

        add_rows: int = self.grid_size.h - self.pixels.shape[0]
        add_cols: int = self.grid_size.w - self.pixels.shape[1]

        if add_rows < 0:
            self.pixels = self.pixels[:self.grid_size.h, :, :]
        elif add_rows > 0:
            self.pixels = np.pad(self.pixels, ((0, add_rows), (0, 0), (0, 0)), constant_values=0)
        if add_cols < 0:
            self.pixels = self.pixels[:, :self.grid_size.w, :]
        elif add_cols > 0:
            self.pixels = np.pad(self.pixels, ((0, 0), (0, add_cols), (0, 0)), constant_values=0)

        self.grid_visible_area = Size(
            min(self.grid_size.w, 32), min(self.grid_size.h, 32)
        )

        self._small_minimap_img_1 = pg.Surface((self.grid_size.w * 2, self.grid_size.h * 2))
        self.update_full(offset, selected_pixel_pos)

    def load_img(
            self, img: Optional[pg.SurfaceType], offset: Point,
            selected_pixel_pos: Optional[Tuple[int, int]]
    ) -> None:
        """
        loads a surface's rgba values into a 3d array
        takes image (if it's None it creates an empty grid), offset and selected pixel
        """

        if not img:
            self.pixels = np.zeros((self.grid_size.h, self.grid_size.w, 4), dtype=np.uint8)
        else:
            self.pixels = np.dstack(
                (pg.surfarray.pixels3d(img), pg.surfarray.pixels_alpha(img))
            )
            self.pixels = np.transpose(self.pixels, (1, 0, 2))

            add_rows: int = self.grid_size.h - self.pixels.shape[0]
            add_cols: int = self.grid_size.w - self.pixels.shape[1]

            if add_rows < 0:
                self.pixels = self.pixels[:self.grid_size.h, :, :]
            elif add_rows > 0:
                self.pixels = np.pad(
                    self.pixels, ((0, add_rows), (0, 0), (0, 0)), constant_values=0
                )
            if add_cols < 0:
                self.pixels = self.pixels[:, :self.grid_size.w, :]
            elif add_cols > 0:
                self.pixels = np.pad(
                    self.pixels, ((0, 0), (0, add_cols), (0, 0)), constant_values=0
                )

        self.update_full(offset, selected_pixel_pos)

    def get_grid(self, offset: Point, selected_pixel_pos: Optional[Tuple[int, int]]) -> None:
        """
        get the grid image from the minimap
        takes offset and selected pixel
        """

        w: int = self.grid_visible_area.w
        if offset.x + w > self.grid_size.w:
            w -= offset.x + w - self.grid_size.w
        w *= 2
        h: int = self.grid_visible_area.h
        if offset.y + h > self.grid_size.h:
            h -= offset.y + h - self.grid_size.h
        h *= 2
        self._small_grid_img = self._small_minimap_img_1.subsurface(
            (offset.x * 2, offset.y * 2, w, h)
        )

        grid_img_size: Tuple[int, int] = (
            self.grid_visible_area.w * self.grid_pixel_dim,
            self.grid_visible_area.h * self.grid_pixel_dim
        )

        if not selected_pixel_pos:
            self._grid_img = pg.transform.scale(self._small_grid_img, grid_img_size)
        else:
            small_grid_img_copy: pg.SurfaceType = self._small_grid_img.copy()
            small_grid_img_copy.blit(self._transparent_pixel, selected_pixel_pos)
            self._grid_img = pg.transform.scale(small_grid_img_copy, grid_img_size)

        self.grid_rect = self._grid_img.get_frect(**{self._grid_init_pos.pos: self._grid_pos})

    def update_full(self, offset: Point, selected_pixel_pos: Optional[Tuple[int, int]]) -> None:
        """
        draws the pixels on the minimap
        and retrieves the visible area
        takes offset and selected_pixel
        """

        sequence: BlitSequence = []

        grid_w: int = self.grid_size.w
        grid_h: int = self.grid_size.h
        visible_area: Size = self.grid_visible_area
        pixels: NDArray[np.uint8] = self.pixels

        empty_pixel: pg.SurfaceType = self._empty_pixel
        pixel_surf: pg.SurfaceType = pg.Surface((2, 2))
        for y in range(grid_h):
            for x in range(grid_w):
                if not pixels[y, x, -1]:
                    sequence.append((empty_pixel, (x * 2, y * 2)))
                else:
                    pixel_surf.fill(pixels[y, x])
                    sequence.append((pixel_surf.copy(), (x * 2, y * 2)))

        self._small_minimap_img_1.fblits(sequence)

        self._small_minimap_img_2 = self._small_minimap_img_1.copy()
        pg.draw.rect(
            self._small_minimap_img_2, WHITE, (offset.x * 2, offset.y * 2, visible_area.w * 2, 2)
        )
        pg.draw.rect(
            self._small_minimap_img_2, WHITE,
            (offset.x * 2, (offset.y + visible_area.h - 1) * 2, visible_area.w * 2, 2)
        )
        pg.draw.rect(
            self._small_minimap_img_2, WHITE, (offset.x * 2, offset.y * 2, 2, visible_area.h * 2)
        )
        pg.draw.rect(
            self._small_minimap_img_2, WHITE,
            ((offset.x + visible_area.w - 1) * 2, offset.y * 2, 2, visible_area.h * 2)
        )

        minimap_pixel_dim: float = min(
            self._minimap_init_size.w / grid_w * self._win_ratio,
            self._minimap_init_size.h / grid_h * self._win_ratio
        )
        minimap_img_size: Tuple[int, int] = (
            int(grid_w * minimap_pixel_dim), int(grid_h * minimap_pixel_dim)
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_img_size)
        self._minimap_rect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.pos: self._minimap_pos}
        )

        self.get_grid(offset, selected_pixel_pos)

    def update_section(
            self, offset: Point, selected_pixel_pos: Optional[Tuple[int, int]], brush_size: int
    ) -> None:
        """
        draws the visible area on the minimap
        takes offset, selected pixel and brush size
        """

        '''
        create a rectangle the size of the visible area + brush size
        if x or y are negative decrease the size and make them 0
        if right or bottom coordinates exceed grid size also decrease the size
        '''

        if self._transparent_pixel.get_width() != brush_size * 2:
            self._transparent_pixel = pg.transform.scale(
                self._transparent_pixel, (brush_size * 2, brush_size * 2)
            )

        pos: Point = Point(
            offset.x - brush_size + 1, offset.y - brush_size + 1
        )
        visible_area: Size = self.grid_visible_area

        area: Size = Size(
            visible_area.w + (brush_size - 1) * 2, visible_area.h + (brush_size - 1) * 2
        )

        if pos.x < 0:
            area.w += pos.x
            pos.x = 0
        if pos.x + area.w > self.grid_size.w:
            area.w -= pos.x + area.w - self.grid_size.w

        if pos.y < 0:
            area.h += pos.y
            pos.y = 0
        if pos.y + area.h > self.grid_size.h:
            area.h -= pos.y + area.h - self.grid_size.h

        # draws the pixels using the position

        sequence: BlitSequence = []

        pixels: NDArray[np.uint8] = self.pixels
        empty_pixel: pg.SurfaceType = self._empty_pixel
        pixel_surf: pg.SurfaceType = pg.Surface((2, 2))
        for y in range(pos.y, pos.y + area.h):
            for x in range(pos.x, pos.x + area.w):
                if not pixels[y, x, - 1]:
                    sequence.append((empty_pixel, (x * 2, y * 2)))
                else:
                    pixel_surf.fill(pixels[y, x])
                    sequence.append((pixel_surf.copy(), (x * 2, y * 2)))

        # making a new surface and blitting it on the minimap is inaccurate
        self._small_minimap_img_1.fblits(sequence)

        self._small_minimap_img_2 = self._small_minimap_img_1.copy()
        pg.draw.rect(
            self._small_minimap_img_2, WHITE, (offset.x * 2, offset.y * 2, visible_area.w * 2, 2)
        )
        pg.draw.rect(
            self._small_minimap_img_2, WHITE,
            (offset.x * 2, (offset.y + visible_area.h - 1) * 2, visible_area.w * 2, 2)
        )
        pg.draw.rect(
            self._small_minimap_img_2, WHITE, (offset.x * 2, offset.y * 2, 2, visible_area.h * 2)
        )
        pg.draw.rect(
            self._small_minimap_img_2, WHITE,
            ((offset.x + visible_area.w - 1) * 2, offset.y * 2, 2, visible_area.h * 2)
        )

        self._minimap_img = pg.transform.scale(
            self._small_minimap_img_2, (int(self._minimap_rect.w), int(self._minimap_rect.h))
        )

        self.get_grid(offset, selected_pixel_pos)


class GridManager:
    """
    class to create and edit a grid of pixel with a minimap
    """

    __slots__ = (
        'grid', '_grid_offset', '_selected_pixel_pos', '_hovering',
        '_prev_mouse_pos', '_traveled_dist'
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        loads an image, creates surfaces and rects
        takes grid and minimap position
        """

        self.grid: Grid = Grid(grid_pos, minimap_pos)
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
        self.grid.load_img(img, self._grid_offset, self._selected_pixel_pos)

    def _draw(
            self, mouse_info: MouseInfo, hoovering: bool, color: ColorType, brush_size: int
    ) -> bool:
        """
        gets the selected pixel and handles changing it
        takes mouse_info, hoovering bool, color and  brush size
        return the redraw grid flag
        """

        if not (hoovering or self.grid.grid_rect.collidepoint(self._prev_mouse_pos.xy)):
            return False

        prev_mouse_pixel: Point = Point(
            int(self._prev_mouse_pos.x - self.grid.grid_rect.x) // self.grid.grid_pixel_dim,
            int(self._prev_mouse_pos.y - self.grid.grid_rect.y) // self.grid.grid_pixel_dim
        )
        mouse_pixel: Point = Point(
            int(mouse_info.x - self.grid.grid_rect.x) // self.grid.grid_pixel_dim,
            int(mouse_info.y - self.grid.grid_rect.y) // self.grid.grid_pixel_dim
        )

        start: Point = Point(
            prev_mouse_pixel.x - brush_size // 2, prev_mouse_pixel.y - brush_size // 2)
        end: Point = Point(
            mouse_pixel.x - brush_size // 2, mouse_pixel.y - brush_size // 2
        )

        redraw_grid: bool = False

        if hoovering and (start != end or not self._selected_pixel_pos):
            self._selected_pixel_pos = (end.x * 2, end.y * 2)
            redraw_grid = True

        if mouse_info.buttons[0] or mouse_info.buttons[2]:
            '''
            get the coordinates of the grid pixels the mouse touched between frames using
            Bresenham's Line Algorithm
            '''

            x0: int = min(
                max(start.x, -brush_size + 1), self.grid.grid_visible_area.w - 1
            ) + self._grid_offset.x
            y0: int = min(
                max(start.y, -brush_size + 1), self.grid.grid_visible_area.h - 1
            ) + self._grid_offset.y

            x1: int = min(
                max(end.x, -brush_size + 1), self.grid.grid_visible_area.w - 1
            ) + self._grid_offset.x
            y1: int = min(
                max(end.y, -brush_size + 1), self.grid.grid_visible_area.h - 1
            ) + self._grid_offset.y

            points: List[Tuple[int, int]] = []

            dx: int = abs(x1 - x0)
            dy: int = abs(y1 - y0)
            sx: int = 1 if x0 < x1 else -1
            sy: int = 1 if y0 < y1 else -1
            err: int = dx - dy
            while True:
                points.append((x0, y0))
                if x0 == x1 and y0 == y1:
                    break

                e2: int = err * 2
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if e2 < dx:
                    err += dx
                    y0 += sy

            for px, py in points:
                x: slice = slice(
                    max(px, 0), min(px + brush_size, self.grid.grid_size.w)
                )
                y: slice = slice(
                    max(py, 0), min(py + brush_size, self.grid.grid_size.h)
                )

                if mouse_info.buttons[0]:
                    self.grid.pixels[y, x] = color + (255,)
                else:
                    self.grid.pixels[y, x,] = (0, 0, 0, 0)
            redraw_grid = True

        return redraw_grid

    def _move(self, mouse_info: MouseInfo) -> bool:
        """
        allows the user change the section of the grid that is drawn
        takes mouse info
        returns the get grid flag
        """

        draw_grid: bool = False

        if not mouse_info.buttons[1]:
            self._traveled_dist.x = self._traveled_dist.y = 0
        else:
            pixels_traveled: int

            self._traveled_dist.x += self._prev_mouse_pos.x - mouse_info.x
            if abs(self._traveled_dist.x) > self.grid.grid_pixel_dim:
                pixels_traveled = round(self._traveled_dist.x / self.grid.grid_pixel_dim)
                self._traveled_dist.x -= pixels_traveled * self.grid.grid_pixel_dim

                self._grid_offset.x = min(
                    max(self._grid_offset.x + pixels_traveled, 0),
                    self.grid.grid_size.w - self.grid.grid_visible_area.w
                )

                draw_grid = True

            self._traveled_dist.y += self._prev_mouse_pos.y - mouse_info.y
            if abs(self._traveled_dist.y) > self.grid.grid_pixel_dim:
                pixels_traveled = round(self._traveled_dist.y / self.grid.grid_pixel_dim)
                self._traveled_dist.y -= pixels_traveled * self.grid.grid_pixel_dim

                self._grid_offset.y = min(
                    max(self._grid_offset.y + pixels_traveled, 0),
                    self.grid.grid_size.h - self.grid.grid_visible_area.h
                )

                draw_grid = True

        return draw_grid

    def resize(self, new_size: Size) -> None:
        """
        resizes the grid
        takes new size
        """

        self._grid_offset = Point(0, 0)
        self._traveled_dist = Point(0, 0)
        self.grid.resize(new_size, self._grid_offset, self._selected_pixel_pos)

    def upt(self, mouse_info: MouseInfo, color: ColorType, brush_size: int) -> None:
        """
        makes the object interactable
        takes mouse info, color and brush size
        """

        redraw_grid: bool = False

        hoovering: bool = self.grid.grid_rect.collidepoint(mouse_info.xy)
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

        if self._draw(mouse_info, hoovering, color, brush_size):
            redraw_grid = True

        if self._move(mouse_info):
            redraw_grid = True

        if redraw_grid:
            self.grid.update_section(self._grid_offset, self._selected_pixel_pos, brush_size)

        self._prev_mouse_pos = Point(*mouse_info.xy)
