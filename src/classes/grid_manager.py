"""
paintable pixel grid with minimap
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, List, Dict, Final, Optional, Any

from src.utils import Point, Size, RectPos, MouseInfo, ColorType, BlitSequence
from src.const import WHITE, EMPTY_1, EMPTY_2

TRANSPARENT: Final[ColorType] = (120, 120, 120, 125)


class Grid:
    """
    class to create a grid of pixels it's minimap
    """

    __slots__ = (
        'grid_size', '_grid_init_visible_area', 'grid_visible_area', '_grid_init_pos', '_grid_pos',
        'grid_pixel_dim', '_grid_init_dim', '_grid_img', 'grid_rect', 'pixels', '_pixel_surf',
        '_empty_pixel', 'transparent_pixel', '_minimap_init_pos', '_minimap_pos',
        '_minimap_init_dim', '_minimap_img', '_minimap_rect', '_min_win_ratio',
        '_small_minimap_img_1', '_small_minimap_img_2', '_small_grid_img',
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        creates all the objects
        takes grid and minimap position
        """

        self.grid_size: Size = Size(64, 64)  # cols, rows
        self._grid_init_visible_area: int = 32
        self.grid_visible_area: Size = Size(
            self._grid_init_visible_area, self._grid_init_visible_area
        )

        self._grid_init_pos: RectPos = grid_pos
        self._grid_pos: Tuple[float, float] = self._grid_init_pos.xy

        self.grid_pixel_dim: float = 18.0
        self._grid_init_dim: int = int(self.grid_visible_area.w * self.grid_pixel_dim)

        self._grid_img: pg.SurfaceType = pg.Surface(
            (self._grid_init_dim, self._grid_init_dim)
        )
        self.grid_rect: pg.FRect = self._grid_img.get_frect(
            **{self._grid_init_pos.coord: self._grid_init_pos.xy}
        )

        self.pixels: NDArray[np.uint8] = np.zeros(
            (self.grid_size.h, self.grid_size.w, 4), np.uint8
        )
        self._pixel_surf: pg.SurfaceType = pg.Surface((2, 2))

        self._empty_pixel: pg.SurfaceType = pg.Surface((2, 2))
        for y in range(2):
            for x in range(2):
                pixel_color: ColorType = EMPTY_1 if (x + y) % 2 == 0 else EMPTY_2
                self._empty_pixel.set_at((x, y), pixel_color)

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
            **{self._minimap_init_pos.coord: self._minimap_init_pos.xy}
        )

        self._min_win_ratio: float = 1.0  # keeps the pixels as squares

        # having a version where 1 grid pixel = 1 pixel is better for scaling
        self._small_minimap_img_1: pg.SurfaceType = pg.Surface(
            (self.grid_size.w * 2, self.grid_size.h * 2)
        )
        # adds section indicator
        self._small_minimap_img_2: pg.SurfaceType = self._small_minimap_img_1.copy()
        self._small_grid_img: pg.SurfaceType = self._small_minimap_img_1.subsurface(
            (0, 0, self.grid_visible_area.w * 2, self.grid_visible_area.h * 2)
        ).copy()

        self.update_full(Point(0, 0), [])

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

        self._min_win_ratio = min(win_ratio_w, win_ratio_h)

        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._min_win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._min_win_ratio
        )

        grid_img_size: Tuple[int, int] = (
            int(self.grid_visible_area.w * self.grid_pixel_dim),
            int(self.grid_visible_area.h * self.grid_pixel_dim)
        )
        self._grid_pos = (
            self._grid_init_pos.x * win_ratio_w, self._grid_init_pos.y * win_ratio_h
        )

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_img_size)
        self.grid_rect = self._grid_img.get_frect(**{self._grid_init_pos.coord: self._grid_pos})

        minimap_pixel_dim: float = min(
            self._minimap_init_dim / self.grid_size.w * self._min_win_ratio,
            self._minimap_init_dim / self.grid_size.h * self._min_win_ratio
        )

        minimap_img_size: Tuple[int, int] = (
            int(self.grid_size.w * minimap_pixel_dim), int(self.grid_size.h * minimap_pixel_dim)
        )
        self._minimap_pos = (
            self._minimap_init_pos.x * win_ratio_w, self._minimap_init_pos.y * win_ratio_h
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_img_size)
        self._minimap_rect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.coord: self._minimap_pos}
        )

    def get_section_indicator(self, offset: Point) -> None:
        """
        indicates the visible area on the minimap with a white rectangle
        takes offset
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

    def get_grid(self, offset: Point, selected_pixels: List[Point]) -> None:
        """
        gets the grid image from the minimap
        takes offset and selected pixels
        """

        w: int = self.grid_visible_area.w
        if offset.x + w > self.grid_size.w:
            w -= offset.x + w - self.grid_size.w
        h: int = self.grid_visible_area.h
        if offset.y + h > self.grid_size.h:
            h -= offset.y + h - self.grid_size.h

        w *= 2
        h *= 2

        small_grid_rect: pg.Rect = pg.Rect(offset.x * 2, offset.y * 2, w, h)
        self._small_grid_img = self._small_minimap_img_1.subsurface(small_grid_rect).copy()

        for pixel in selected_pixels:
            if small_grid_rect.collidepoint(pixel.xy):
                self._small_grid_img.blit(self.transparent_pixel, pixel.xy)

        grid_img_size: Tuple[int, int] = (
            int(self.grid_visible_area.w * self.grid_pixel_dim),
            int(self.grid_visible_area.h * self.grid_pixel_dim)
        )

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_img_size)
        self.grid_rect = self._grid_img.get_frect(**{self._grid_init_pos.coord: self._grid_pos})

    def update_full(self, offset: Point, selected_pixels: List[Point]) -> None:
        """
        updates all the pixels on the minimap and retrieves the grid
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
            row: NDArray[np.uint8] = pixels[y]
            for x in range(grid_w):
                if not row[x, -1]:
                    sequence.append((empty_pixel, (x * 2, y * 2)))
                else:
                    pixel_surf.fill(row[x])
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
            self._minimap_init_dim / grid_w * self._min_win_ratio,
            self._minimap_init_dim / grid_h * self._min_win_ratio
        )
        minimap_img_size: Tuple[int, int] = (
            int(grid_w * minimap_pixel_dim), int(grid_h * minimap_pixel_dim)
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_img_size)
        self._minimap_rect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.coord: self._minimap_pos}
        )

        self.get_grid(offset, selected_pixels)

    def update_section(
            self, offset: Point, selected_pixels: List[Point],
            changed_pixels: List[Tuple[int, int]]
    ) -> None:
        """
        updates specific pixels on the minimap and retrieves the grid
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
        self._small_minimap_img_1.fblits(sequence)

        self.get_section_indicator(offset)
        self.get_grid(offset, selected_pixels)

    def load_img(
            self, img: Optional[pg.SurfaceType], offset: Point, selected_pixels: List[Point]
    ) -> None:
        """
        loads a surface's rgba values into a 3D array
        takes image (if it's None it creates an empty grid), offset and selected pixel
        """

        if not img:
            self.pixels = np.zeros((self.grid_size.h, self.grid_size.w, 4), np.uint8)
        else:
            pixels_rgb: NDArray[np.uint8] = pg.surfarray.pixels3d(img)
            pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img)
            self.pixels = np.dstack((pixels_rgb, pixels_alpha))
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
            self._grid_init_dim / self.grid_visible_area.w * self._min_win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._min_win_ratio
        )

        self.update_full(offset, selected_pixels)

    def resize(self, size: Size) -> None:
        """
        resizes the grid
        takes size
        """
        self.grid_size = size

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

        self.grid_visible_area.w = min(self.grid_visible_area.w, self.grid_size.w)
        self.grid_visible_area.h = min(self.grid_visible_area.h, self.grid_size.h)
        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._min_win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._min_win_ratio
        )

        self._small_minimap_img_1 = pg.Surface((self.grid_size.w * 2, self.grid_size.h * 2))

    def zoom(self, amount: int, offset: Point) -> None:
        """
        changes pixel dim and visible area
        takes zoom amount and offset
        """

        neg_amount: int = amount * -1  # negative when zooming in, positive when zooming out

        add_w: bool = True
        add_h: bool = True
        if self.grid_visible_area.w != self.grid_visible_area.h:
            if neg_amount < 0:
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
            self.grid_visible_area.w = max(self.grid_visible_area.w + neg_amount, 1)

            extra = offset.x + self.grid_visible_area.w - self.grid_size.w
            if extra > 0:
                offset.x = max(offset.x - extra, 0)
                self.grid_visible_area.w = min(self.grid_visible_area.w, self.grid_size.w)
        if add_h:
            self.grid_visible_area.h = max(self.grid_visible_area.h + neg_amount, 1)

            extra = offset.y + self.grid_visible_area.h - self.grid_size.h
            if extra > 0:
                offset.y = max(offset.y - extra, 0)
                self.grid_visible_area.h = min(self.grid_visible_area.h, self.grid_size.h)

        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._min_win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._min_win_ratio
        )

    def reset(self) -> None:
        """
        resets visible area and offset
        """

        self.grid_visible_area.w = min(self.grid_visible_area.w, self._grid_init_visible_area)
        self.grid_visible_area.h = min(self.grid_visible_area.h, self._grid_init_visible_area)
        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._min_win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._min_win_ratio
        )

        self.get_grid(Point(0, 0), [])
        self.get_section_indicator(Point(0, 0))


class GridManager:
    """
    class to create and edit a grid of pixels
    """

    __slots__ = (
        'grid', '_grid_offset', '_selected_pixels', '_hovering',
        '_prev_mouse_pos', '_traveled_dist'
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        creates the grid
        takes grid and minimap position
        """

        self.grid: Grid = Grid(grid_pos, minimap_pos)
        self._grid_offset: Point = Point(0, 0)

        self._selected_pixels: List[Point] = []
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

        self.grid.handle_resize(win_ratio_w, win_ratio_h)

    def load_path(self, file_path: str) -> None:
        """
        loads an image from a path and renders it into the grid
        takes path if it's empty it creates an empty grid
        """

        self._grid_offset.x = self._grid_offset.y = 0
        self._traveled_dist.x = self._traveled_dist.y = 0

        img: Optional[pg.SurfaceType] = (
            pg.image.load(file_path).convert_alpha() if file_path else None
        )
        self.grid.load_img(img, self._grid_offset, self._selected_pixels)

    def _get_draw_info(
            self, mouse_info: MouseInfo, keys: List[int], brush_size: int
    ) -> Tuple[Point, Point]:
        """
        calculates start and end, updates transparent pixel and handles keys
        takes mouse info, keys and brush size
        returns start and end
        """

        prev_mouse_pixel: Point = Point(
            int((self._prev_mouse_pos.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int((self._prev_mouse_pos.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )
        mouse_pixel: Point = Point(
            int((mouse_info.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int((mouse_info.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )

        if self.grid.grid_rect.collidepoint(mouse_info.xy):
            if self.grid.transparent_pixel.get_width() != brush_size * 2:
                self.grid.transparent_pixel = pg.transform.scale(
                    self.grid.transparent_pixel, (brush_size * 2, brush_size * 2)
                )

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

                self.grid.get_section_indicator(self._grid_offset)
                pg.mouse.set_pos((
                    int(self.grid.grid_rect.x + mouse_pixel.x * pixel_dim + pixel_dim / 2),
                    int(self.grid.grid_rect.y + mouse_pixel.y * pixel_dim + pixel_dim / 2)
                ))

        start: Point = Point(
            prev_mouse_pixel.x - brush_size // 2, prev_mouse_pixel.y - brush_size // 2)
        end: Point = Point(
            mouse_pixel.x - brush_size // 2, mouse_pixel.y - brush_size // 2
        )

        return start, end

    def _draw_rect_to_pixels(
            self, left: int, top: int, right: int, bottom: int, color: ColorType
    ) -> List[Tuple[int, int]]:
        """
        draws a rectangular area on the pixels array
        takes the top left, bottom right coordinates and the color
        returns the coordinates of every pixel in the rect
        """

        changed_pixels: List[Tuple[int, int]] = []
        pixels: NDArray[np.uint8] = self.grid.pixels

        for y in range(top, bottom):
            row: NDArray[np.uint8] = pixels[y]
            for x in range(left, right):
                row[x] = color
                changed_pixels.append((x, y))

        return changed_pixels

    def _brush(
            self, start: Point, end: Point, prev_grid_offset: Point, brush_size: int,
            color: ColorType, extra_info: Dict[str, Any]
    ) -> List[Tuple[int, int]]:
        """
        handles brush tool
        takes start, end, previous offset, brush size, color and extra info
        return changed pixels
        """

        '''
        get the coordinates of the grid pixels the mouse touched between frames using
        Bresenham's Line Algorithm and change the pixels
        '''

        changed_pixels: List[Tuple[int, int]] = []

        x_1: int = max(min(start.x, self.grid.grid_visible_area.w - 1), -brush_size + 1)
        y_1: int = max(min(start.y, self.grid.grid_visible_area.h - 1), -brush_size + 1)
        x_2: int = max(min(end.x, self.grid.grid_visible_area.w - 1), -brush_size + 1)
        y_2: int = max(min(end.y, self.grid.grid_visible_area.h - 1), -brush_size + 1)

        x_1 += prev_grid_offset.x
        y_1 += prev_grid_offset.y
        x_2 += self._grid_offset.x
        y_2 += self._grid_offset.y

        d: Point = Point(abs(x_2 - x_1), abs(y_2 - y_1))
        s: Point = Point(1 if x_1 < x_2 else -1, 1 if y_1 < y_2 else -1)
        err: int = d.x - d.y
        while True:
            changed_pixels += [(x_1, y_1)]
            if x_1 == x_2 and y_1 == y_2:
                break

            err_2: int = err * 2
            if err_2 > -d.y:
                err -= d.y
                x_1 += s.x
            if err_2 < d.x:
                err += d.x
                y_1 += s.y

        grid_size: Size = self.grid.grid_size
        if extra_info['x_mirror']:
            for x, y in changed_pixels.copy():
                x = grid_size.w - x - 1
                changed_pixels += [(x, y)]
        if extra_info['y_mirror']:
            for x, y in changed_pixels.copy():
                y = grid_size.h - y - 1
                changed_pixels += [(x, y)]

        for x, y in changed_pixels.copy():
            changed_pixels += self._draw_rect_to_pixels(
                max(x, 0), max(y, 0),
                min(x + brush_size, self.grid.grid_size.w),
                min(y + brush_size, self.grid.grid_size.h), color
            )

        return changed_pixels

    def _draw(
            self, mouse_info: MouseInfo, keys: List[int], color: ColorType, brush_size: int,
            tool_info: Tuple[str, Dict[str, Any]]
    ) -> List[Tuple[int, int]]:
        """
        gets the selected pixel and handles changing it
        takes mouse_info, keys, color, brush size and tool info
        returns the changed pixels
        """

        if not (
                self.grid.grid_rect.collidepoint(self._prev_mouse_pos.xy) or
                self.grid.grid_rect.collidepoint(mouse_info.xy)
        ):
            if self._selected_pixels:
                self._selected_pixels = []
                self.grid.get_grid(self._grid_offset, self._selected_pixels)

            return []

        changed_pixels: List[Tuple[int, int]] = []
        prev_grid_offset: Point = Point(self._grid_offset.x, self._grid_offset.y)

        start: Point
        end: Point
        start, end = self._get_draw_info(mouse_info, keys, brush_size)

        prev_selected_pixels: List[Point] = self._selected_pixels
        self._selected_pixels = []

        self._selected_pixels += [Point(end.x * 2, end.y * 2)]
        if tool_info[1]['x_mirror']:
            for pixel in self._selected_pixels.copy():
                x: int = (self.grid.grid_size.w - brush_size) * 2 - pixel.x
                self._selected_pixels += [Point(x, pixel.y)]
        if tool_info[1]['y_mirror']:
            for pixel in self._selected_pixels.copy():
                y: int = (self.grid.grid_size.h - brush_size) * 2 - pixel.y
                self._selected_pixels += [Point(pixel.x, y)]

        if self._selected_pixels != prev_selected_pixels:
            self.grid.get_grid(self._grid_offset, self._selected_pixels)

        if (
                (mouse_info.buttons[0] or mouse_info.buttons[2]) or
                (pg.K_RETURN in keys or pg.K_BACKSPACE in keys)
        ):
            full_color: ColorType = (
                color + (255,) if mouse_info.buttons[0] or pg.K_RETURN in keys else (0, 0, 0, 0)
            )

            match tool_info[0]:
                case 'brush':
                    changed_pixels += self._brush(
                        start, end, prev_grid_offset, brush_size, full_color, tool_info[1]
                    )

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

                self._grid_offset.x = max(
                    min(
                        self._grid_offset.x + pixels_traveled,
                        self.grid.grid_size.w - self.grid.grid_visible_area.w
                    ), 0
                )

                moved = True

            self._traveled_dist.y += self._prev_mouse_pos.y - mouse_info.y
            if abs(self._traveled_dist.y) > self.grid.grid_pixel_dim:
                pixels_traveled = round(self._traveled_dist.y / self.grid.grid_pixel_dim)
                self._traveled_dist.y -= int(pixels_traveled * self.grid.grid_pixel_dim)

                self._grid_offset.y = max(
                    min(
                        self._grid_offset.y + pixels_traveled,
                        self.grid.grid_size.h - self.grid.grid_visible_area.h
                    ), 0
                )

                moved = True

        return moved

    def resize(self, size: Optional[Size]) -> None:
        """
        resizes the grid
        takes size
        """

        if not size:
            return

        self._traveled_dist.x, self._traveled_dist.y = 0, 0

        self.grid.resize(size)
        self._grid_offset.x = min(
            self._grid_offset.x, self.grid.grid_size.w - self.grid.grid_visible_area.w
        )
        self._grid_offset.y = min(
            self._grid_offset.y, self.grid.grid_size.h - self.grid.grid_visible_area.h
        )

        self.grid.update_full(self._grid_offset, self._selected_pixels)

    def zoom(self, amount: int, brush_size: int) -> None:
        """
        zooms in/out
        takes zooming amount and brush size
        """

        if self._hovering:
            mouse_pos: Point = Point(*pg.mouse.get_pos())

            prev_mouse_pixel: Point = Point(
                int((mouse_pos.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
                int((mouse_pos.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
            )
            prev_mouse_pixel.x -= brush_size // 2
            prev_mouse_pixel.y -= brush_size // 2

            self.grid.zoom(amount, self._grid_offset)

            mouse_pixel: Point = Point(
                int((mouse_pos.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
                int((mouse_pos.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
            )
            mouse_pixel.x -= brush_size // 2
            mouse_pixel.y -= brush_size // 2

            self._grid_offset.x = max(
                min(
                    self._grid_offset.x + prev_mouse_pixel.x - mouse_pixel.x,
                    self.grid.grid_size.w - self.grid.grid_visible_area.w
                ), 0
            )
            self._grid_offset.y = max(
                min(
                    self._grid_offset.y + prev_mouse_pixel.y - mouse_pixel.y,
                    self.grid.grid_size.h - self.grid.grid_visible_area.h
                ), 0
            )

            for pixel in self._selected_pixels:
                pixel.x = mouse_pixel.x * 2
                pixel.y = mouse_pixel.y * 2

            self.grid.get_grid(self._grid_offset, self._selected_pixels)
            self.grid.get_section_indicator(self._grid_offset)

    def upt(
            self, mouse_info: MouseInfo, keys: List[int], color: ColorType, brush_size: int,
            tool_info: Tuple[str, Dict[str, Any]]
    ) -> None:
        """
        makes the object interactable
        takes mouse info, keys, color and tool info
        """

        if not self.grid.grid_rect.collidepoint(mouse_info.xy):
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
                self._hovering = True

        changed_pixels: List[Tuple[int, int]] = self._draw(
            mouse_info, keys, color, brush_size, tool_info
        )
        if changed_pixels:
            self.grid.update_section(self._grid_offset, self._selected_pixels, changed_pixels)

        if self._move(mouse_info):
            self.grid.get_section_indicator(self._grid_offset)
            self.grid.get_grid(self._grid_offset, self._selected_pixels)

        mods: int = pg.key.get_mods()
        if mods & pg.KMOD_CTRL and pg.K_r in keys:
            self._grid_offset.x = self._grid_offset.y = 0
            self._traveled_dist.x = self._traveled_dist.y = 0
            self.grid.reset()

        self._prev_mouse_pos.x, self._prev_mouse_pos.y = mouse_info.x, mouse_info.y
