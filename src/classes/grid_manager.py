"""
paintable pixel grid with minimap
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, List, Final, Optional

from src.utils import Point, Size, RectPos, MouseInfo
from src.const import WHITE, EMPTY_1, EMPTY_2, ColorType, BlitSequence

TRANSPARENT: Final[ColorType] = (120, 120, 120, 125)


class Grid:
    """
    class to convert an image into a pixel array and blit a section of it into a grid
    """

    __slots__ = (
        'grid_size', 'grid_visible_area', '_grid_init_visible_area', '_win_ratio',
        '_grid_init_pos', '_grid_pos', 'grid_pixel_dim', '_grid_init_dim',
        '_grid_img', 'grid_rect', 'pixels', '_pixel_surf', '_empty_pixel',
        'transparent_pixel', '_minimap_init_pos', '_minimap_pos', '_minimap_init_dim',
        '_minimap_img', '_minimap_rect',
        '_small_minimap_img_1', '_small_minimap_img_2', '_small_grid_img',
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        loads an image into a fixed size grid,
        creates the surfaces used for empty and selected pixel
        and creates a minimap in the top right corner
        takes grid and minimap position
        """

        self.grid_size: Size = Size(64, 64)  # cols, rows
        self._grid_init_visible_area: int = 32
        self.grid_visible_area: Size = Size(
            self._grid_init_visible_area, self._grid_init_visible_area
        )

        self._grid_init_pos: RectPos = grid_pos
        self._grid_pos: Tuple[float, float] = self._grid_init_pos.xy

        self.grid_pixel_dim: float = 18
        self._grid_init_dim: int = self.grid_visible_area.w * self.grid_pixel_dim

        self._grid_img: pg.SurfaceType = pg.Surface(
            (self._grid_init_dim, self._grid_init_dim)
        )
        self.grid_rect: pg.FRect = self._grid_img.get_frect(
            **{self._grid_init_pos.pos: self._grid_init_pos.xy}
        )

        self.pixels: NDArray[np.uint8] = np.zeros(
            (self.grid_size.h, self.grid_size.w, 4), dtype=np.uint8
        )

        self._pixel_surf: pg.SurfaceType = pg.Surface((2, 2))
        self._empty_pixel: pg.SurfaceType = pg.Surface((2, 2))
        for row in range(2):
            for col in range(2):
                pixel_color: ColorType = EMPTY_1 if (row + col) % 2 == 0 else EMPTY_2
                self._empty_pixel.set_at((col, row), pixel_color)

        self.transparent_pixel: pg.SurfaceType = pg.Surface(
            (2, 2), pg.SRCALPHA
        )
        self.transparent_pixel.fill(TRANSPARENT)

        self._minimap_init_pos: RectPos = minimap_pos
        self._minimap_pos: Tuple[float, float] = self._minimap_init_pos.xy

        self._minimap_init_dim: int = 256

        self._minimap_img: pg.SurfaceType = pg.Surface(
            (self._minimap_init_dim, self._minimap_init_dim)
        )
        self._minimap_rect: pg.FRect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.pos: self._minimap_init_pos.xy}
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
        returns a sequence to add in the main blit sequence
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

        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._win_ratio
        )

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
            self._minimap_init_dim / self.grid_size.w * self._win_ratio,
            self._minimap_init_dim / self.grid_size.h * self._win_ratio
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

    def load_img(
            self, img: Optional[pg.SurfaceType], offset: Point, selected_pixel_pos: Optional[Point]
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

        self.grid_visible_area.w = self._grid_init_visible_area
        self.grid_visible_area.h = self._grid_init_visible_area
        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._win_ratio
        )

        self.update_full(offset, selected_pixel_pos)

    def resize(self, new_size: Size, offset: Point, selected_pixel_pos: Optional[Point]) -> None:
        """
        resizes the grid
        takes new size and offset, selected pixel
        """
        # TODO: keep offset and zoom
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

        self.grid_visible_area.w = min(self.grid_size.w, self._grid_init_visible_area)
        self.grid_visible_area.h = min(self.grid_size.h, self._grid_init_visible_area)
        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._win_ratio
        )

        self._small_minimap_img_1 = pg.Surface((self.grid_size.w * 2, self.grid_size.h * 2))
        self.update_full(offset, selected_pixel_pos)

    def zoom(self, amount: int, offset: Point) -> None:
        """
        changes pixel dim and visible area
        takes zoom amount offset and selected pixel
        """

        amount *= -1  # negative when zooming in, positive when zooming out

        add_w: bool = True
        add_h: bool = True
        if self.grid_visible_area.w != self.grid_visible_area.h:
            if amount < 0:
                # if zooming in decrease only the largest side
                if self.grid_visible_area.w > self.grid_visible_area.h:
                    add_h = False
                else:
                    add_w = False
            else:
                # if zooming out increase only the smallest side if it's not already at max size
                if self.grid_visible_area.w < self.grid_visible_area.h:
                    if self.grid_visible_area.w != self.grid_size.w - offset.x:
                        add_h = False
                else:
                    if self.grid_visible_area.h != self.grid_size.h - offset.y:
                        add_w = False

        extra: int
        if add_w:
            self.grid_visible_area.w = max(self.grid_visible_area.w + amount, 1)

            extra = offset.x + self.grid_visible_area.w - self.grid_size.w
            if extra > 0:
                offset.x -= extra
                if offset.x < 0:
                    offset.x = 0
                    self.grid_visible_area.w = self.grid_size.w
        if add_h:
            self.grid_visible_area.h = max(self.grid_visible_area.h + amount, 1)

            extra = offset.y + self.grid_visible_area.h - self.grid_size.h
            if extra > 0:
                offset.y -= extra
                if offset.y < 0:
                    offset.y = 0
                    self.grid_visible_area.h = self.grid_size.h

        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._win_ratio
        )

    def get_square(self, offset: Point) -> None:
        """
        gets the square of the visible area and draws it on the minimap
        """

        self._small_minimap_img_2 = self._small_minimap_img_1.copy()

        visible_area: Size = self.grid_visible_area
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

    def get_grid(self, offset: Point, selected_pixel_pos: Optional[Point]) -> None:
        """
        gets the grid image from the minimap
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
        ).copy()
        if selected_pixel_pos:
            self._small_grid_img.blit(self.transparent_pixel, selected_pixel_pos.xy)

        grid_img_size: Tuple[int, int] = (
            int(self.grid_visible_area.w * self.grid_pixel_dim),
            int(self.grid_visible_area.h * self.grid_pixel_dim)
        )

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_img_size)
        self.grid_rect = self._grid_img.get_frect(**{self._grid_init_pos.pos: self._grid_pos})

    def update_full(self, offset: Point, selected_pixel_pos: Optional[Point]) -> None:
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
        pixel_surf: pg.SurfaceType = self._pixel_surf
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
            self._minimap_init_dim / grid_w * self._win_ratio,
            self._minimap_init_dim / grid_h * self._win_ratio
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
            self, offset: Point, selected_pixel_pos: Optional[Point],
            changed_pixels: List[Tuple[int, int]]
    ) -> None:
        """
        updates specific pixels on the minimap
        takes offset, selected pixel and changed pixels
        """

        sequence: BlitSequence = []

        pixels: NDArray[np.uint8] = self.pixels
        empty_pixel: pg.SurfaceType = self._empty_pixel
        pixel_surf: pg.SurfaceType = self._pixel_surf
        for x, y in changed_pixels:
            if not pixels[y, x, -1]:
                sequence.append((empty_pixel, (x * 2, y * 2)))
            else:
                pixel_surf.fill(pixels[y, x])
                sequence.append((pixel_surf.copy(), (x * 2, y * 2)))

        # making a new surface and blitting it on the big minimap is inaccurate
        self._small_minimap_img_1.fblits(sequence)

        self.get_square(offset)
        self.get_grid(offset, selected_pixel_pos)


class GridManager:
    """
    class to create and edit a grid of pixels
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

        self._selected_pixel_pos: Optional[Point] = None
        self._hovering: bool = False

        self._prev_mouse_pos: Point = Point(*pg.mouse.get_pos())
        self._traveled_dist: Point = Point(0, 0)

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
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

        self._grid_offset.x, self._grid_offset.y = 0, 0
        self._selected_pixel_pos = None
        self._traveled_dist.x, self._traveled_dist.y = 0, 0

        img: Optional[pg.SurfaceType] = pg.image.load(path).convert_alpha() if path else None
        self.grid.load_img(img, self._grid_offset, self._selected_pixel_pos)

    def _get_draw_info(
            self, mouse_info: MouseInfo, keys: List[int], brush_size: int
    ) -> Tuple[Point, Point]:
        """
        calculates start and end, updates transparent and selected pixel and handles keys
        takes mouse info, keys and brush size
        returns start, end
        """

        prev_mouse_pixel: Point = Point(
            int(int(self._prev_mouse_pos.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int(int(self._prev_mouse_pos.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )
        mouse_pixel: Point = Point(
            int(int(mouse_info.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int(int(mouse_info.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )

        start: Point = Point(
            prev_mouse_pixel.x - brush_size // 2, prev_mouse_pixel.y - brush_size // 2)
        end: Point = Point(
            mouse_pixel.x - brush_size // 2, mouse_pixel.y - brush_size // 2
        )

        if self.grid.grid_rect.collidepoint(mouse_info.xy):
            brush_size_changed: bool = self.grid.transparent_pixel.get_width() != brush_size * 2
            if brush_size_changed:
                self.grid.transparent_pixel = pg.transform.scale(
                    self.grid.transparent_pixel, (brush_size * 2, brush_size * 2)
                )

            if (start != end or not self._selected_pixel_pos) or brush_size_changed:
                self._selected_pixel_pos = Point(end.x * 2, end.y * 2)
                self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)

            if any(key in keys for key in (pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN)):
                k_mods: int = pg.key.get_mods()
                ctrl: int = k_mods & pg.KMOD_CTRL

                value: int
                extra: int
                if k_mods & pg.KMOD_ALT:
                    value = brush_size
                elif k_mods & pg.KMOD_SHIFT:
                    value = max(self.grid.grid_visible_area.w, self.grid.grid_visible_area.h)
                else:
                    value = 1

                size: Size = self.grid.grid_size
                visible_area: Size = self.grid.grid_visible_area
                pixel_dim: float = self.grid.grid_pixel_dim

                if pg.K_LEFT in keys:
                    if ctrl:
                        mouse_pixel.x = 0
                        self._grid_offset.x = 0
                    else:
                        mouse_pixel.x -= value
                        if mouse_pixel.x < 0:
                            extra = mouse_pixel.x
                            self._grid_offset.x = max(self._grid_offset.x + extra, 0)
                            mouse_pixel.x = 0
                elif pg.K_RIGHT in keys:
                    if ctrl:
                        mouse_pixel.x = visible_area.w - 1
                        self._grid_offset.x = size.w - visible_area.w
                    else:
                        mouse_pixel.x += value
                        if mouse_pixel.x + 1 > visible_area.w:
                            extra = mouse_pixel.x + 1 - visible_area.w
                            self._grid_offset.x = min(
                                self._grid_offset.x + extra, size.w - visible_area.w
                            )
                            mouse_pixel.x = visible_area.w - 1
                elif pg.K_UP in keys:
                    if ctrl:
                        mouse_pixel.y = 0
                        self._grid_offset.y = 0
                    else:
                        mouse_pixel.y -= value
                        if mouse_pixel.y < 0:
                            extra = mouse_pixel.y
                            self._grid_offset.y = max(self._grid_offset.y + extra, 0)
                            mouse_pixel.y = 0
                else:
                    if ctrl:
                        mouse_pixel.y = visible_area.h - 1
                        self._grid_offset.y = size.h - visible_area.h
                    else:
                        mouse_pixel.y += value
                        if mouse_pixel.y + 1 > visible_area.h:
                            extra = mouse_pixel.y + 1 - visible_area.h
                            self._grid_offset.y = min(
                                self._grid_offset.y + extra, size.h - visible_area.h
                            )
                            mouse_pixel.y = visible_area.h - 1

                end.x, end.y = mouse_pixel.x - brush_size // 2, mouse_pixel.y - brush_size // 2

                self.grid.get_square(self._grid_offset)
                pg.mouse.set_pos((
                    int(self.grid.grid_rect.x + mouse_pixel.x * pixel_dim + pixel_dim / 2),
                    int(self.grid.grid_rect.y + mouse_pixel.y * pixel_dim + pixel_dim / 2)
                ))

        return start, end

    def _draw_rect(
        self, left: int, top: int, right: int, bottom: int, color: ColorType
    ) -> List[Tuple[int, int]]:
        """
        draws a rectangular area on the pixels array
        takes the top left and bottom right coordinates and the color
        """

        pixels: NDArray[np.uint8] = self.grid.pixels
        changed_pixels: List[Tuple[int, int]] = []

        for row in range(top, bottom):
            for col in range(left, right):
                pixels[row, col] = color
                changed_pixels.append((col, row))

        return changed_pixels

    def _draw(
            self, mouse_info: MouseInfo, keys: List[int], color: ColorType, brush_size: int
    ) -> List[Tuple[int, int]]:
        """
        gets the selected pixel and handles changing it
        takes mouse_info, keys, color and  brush size
        returns the changed pixels
        """

        if not (
                self.grid.grid_rect.collidepoint(self._prev_mouse_pos.xy) or
                self.grid.grid_rect.collidepoint(mouse_info.xy)
        ):
            return []

        changed_pixels: List[Tuple[int, int]] = []
        prev_grid_offset: Point = Point(self._grid_offset.x, self._grid_offset.y)

        start: Point
        end: Point
        start, end = self._get_draw_info(mouse_info, keys, brush_size)

        if (
                (mouse_info.buttons[0] or mouse_info.buttons[2]) or
                (pg.K_RETURN in keys or pg.K_BACKSPACE in keys)
        ):
            x: int
            y: int
            color = (
                color + (255,) if mouse_info.buttons[0] or pg.K_RETURN in keys else (0, 0, 0, 0)
            )
            if start == end:
                x = end.x + self._grid_offset.x
                y = end.y + self._grid_offset.y

                changed_pixels += self._draw_rect(
                    max(x, 0), max(y, 0),
                    min(x + brush_size, self.grid.grid_size.w),
                    min(y + brush_size, self.grid.grid_size.h), color
                )
            else:
                '''
                get the coordinates of the grid pixels the mouse touched between frames using
                Bresenham's Line Algorithm and change the pixels
                '''

                x = min(
                    max(start.x, -brush_size + 1), self.grid.grid_visible_area.w - 1
                ) + prev_grid_offset.x
                y = min(
                    max(start.y, -brush_size + 1), self.grid.grid_visible_area.h - 1
                ) + prev_grid_offset.y
                x1: int = min(
                    max(end.x, -brush_size + 1), self.grid.grid_visible_area.w - 1
                ) + self._grid_offset.x
                y1: int = min(
                    max(end.y, -brush_size + 1), self.grid.grid_visible_area.h - 1
                ) + self._grid_offset.y

                d: Point = Point(abs(x1 - x), abs(y1 - y))
                s: Point = Point(1 if x < x1 else -1, 1 if y < y1 else -1)
                err: int = d.x - d.y

                grid_size: Size = self.grid.grid_size
                while True:
                    changed_pixels += self._draw_rect(
                        max(x, 0), max(y, 0),
                        min(x + brush_size, grid_size.w),
                        min(y + brush_size, grid_size.h), color
                    )

                    if x == x1 and y == y1:
                        break

                    e2: int = err * 2
                    if e2 > -d.y:
                        err -= d.y
                        x += s.x
                    if e2 < d.x:
                        err += d.x
                        y += s.y

        return changed_pixels

    def _move(self, mouse_info: MouseInfo) -> bool:
        """
        allows the user to change the section of the grid that is drawn
        takes mouse info
        returns True if the visible area was moved
        """

        moved: bool = False

        if not mouse_info.buttons[1]:
            self._traveled_dist.x = self._traveled_dist.y = 0
        else:
            pixels_traveled: int

            self._traveled_dist.x += self._prev_mouse_pos.x - mouse_info.x
            if abs(self._traveled_dist.x) > self.grid.grid_pixel_dim:
                pixels_traveled = round(self._traveled_dist.x / self.grid.grid_pixel_dim)
                self._traveled_dist.x -= int(pixels_traveled * self.grid.grid_pixel_dim)

                self._grid_offset.x = min(
                    max(self._grid_offset.x + pixels_traveled, 0),
                    self.grid.grid_size.w - self.grid.grid_visible_area.w
                )

                moved = True

            self._traveled_dist.y += self._prev_mouse_pos.y - mouse_info.y
            if abs(self._traveled_dist.y) > self.grid.grid_pixel_dim:
                pixels_traveled = round(self._traveled_dist.y / self.grid.grid_pixel_dim)
                self._traveled_dist.y -= int(pixels_traveled * self.grid.grid_pixel_dim)

                self._grid_offset.y = min(
                    max(self._grid_offset.y + pixels_traveled, 0),
                    self.grid.grid_size.h - self.grid.grid_visible_area.h
                )

                moved = True

        return moved

    def resize(self, new_size: Size) -> None:
        """
        resizes the grid
        takes new size
        """

        self._grid_offset.x, self._grid_offset.y = 0, 0
        self._traveled_dist.x, self._traveled_dist.y = 0, 0
        self.grid.resize(new_size, self._grid_offset, self._selected_pixel_pos)

    def zoom(self, amount: int, brush_size: int) -> None:
        """
        zooms in/out
        takes zooming amount and brush size
        """

        if self._selected_pixel_pos:
            prev_mouse_pixel: Point = Point(
                self._selected_pixel_pos.x // 2, self._selected_pixel_pos.y // 2
            )

            self.grid.zoom(amount, self._grid_offset)

            mouse_pos: Point = Point(*pg.mouse.get_pos())
            mouse_pixel: Point = Point(
                int(int(mouse_pos.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
                int(int(mouse_pos.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
            )
            mouse_pixel.x -= brush_size // 2
            mouse_pixel.y -= brush_size // 2

            self._grid_offset.x = max(self._grid_offset.x + prev_mouse_pixel.x - mouse_pixel.x, 0)
            self._grid_offset.y = max(self._grid_offset.y + prev_mouse_pixel.y - mouse_pixel.y, 0)
            self._selected_pixel_pos.x = mouse_pixel.x * 2
            self._selected_pixel_pos.y = mouse_pixel.y * 2

            self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)
            self.grid.get_square(self._grid_offset)
            '''self._grid_offset.x = self._grid_offset.x + self._selected_pixel_pos[0] - end.x
            self._grid_offset.y = self._grid_offset.y + self._selected_pixel_pos[1] - end.y'''

    def upt(
            self, mouse_info: MouseInfo, keys: List[int], color: ColorType, brush_size: int
    ) -> None:
        """
        makes the object interactable
        takes mouse info, keys, color and brush size
        """

        changed_pixels: List[Tuple[int, int]] = []

        if not self.grid.grid_rect.collidepoint(mouse_info.xy):
            if self._hovering:
                self._selected_pixel_pos = None
                self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)

                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
                self._hovering = True

        changed_pixels += self._draw(mouse_info, keys, color, brush_size)

        if self._move(mouse_info):
            self.grid.get_square(self._grid_offset)
            self.grid.get_grid(self._grid_offset, self._selected_pixel_pos)

        if changed_pixels:
            self.grid.update_section(self._grid_offset, self._selected_pixel_pos, changed_pixels)

        self._prev_mouse_pos.x, self._prev_mouse_pos.y = mouse_info.x, mouse_info.y
