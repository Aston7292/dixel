"""
Paintable pixel grid with minimap
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Final, Optional, Any

from src.utils import Point, Size, RectPos, MouseInfo, ColorType
from src.type_utils import ObjsInfo, BlitSequence, LayeredBlitSequence, LayerSequence

from src.consts import WHITE, EMPTY_1, EMPTY_2, BG_LAYER

TRANSPARENT: Final[ColorType] = (120, 120, 120, 125)


class Grid:
    """
    Class to create a grid of pixels and it's minimap
    """

    __slots__ = (
        'grid_size', '_grid_init_visible_area', 'grid_visible_area', '_grid_init_pos', '_grid_pos',
        'grid_pixel_dim', '_grid_init_dim', '_grid_img', 'grid_rect', 'pixels', '_pixel_surf',
        '_empty_pixel', 'transparent_pixel', '_minimap_init_pos', '_minimap_pos',
        '_minimap_init_dim', '_minimap_img', '_minimap_rect', '_min_win_ratio',
        '_small_minimap_img_1', '_small_minimap_img_2', '_small_grid_img', '_layer'
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the grid and minimap
        Args:
            grid position, minimap position
        """

        #  Pixels dimensions are floats to represent the full size more accurately when resizing

        self.grid_size: Size = Size(64, 64)  # Columns and rows
        self._grid_init_visible_area: int = 32
        self.grid_visible_area: Size = Size(
            self._grid_init_visible_area, self._grid_init_visible_area
        )

        self._grid_init_pos: RectPos = grid_pos
        self._grid_pos: tuple[float, float] = self._grid_init_pos.xy

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
        self._minimap_pos: tuple[float, float] = self._minimap_init_pos.xy

        self._minimap_init_dim: int = 256

        self._minimap_img: pg.SurfaceType = pg.Surface(
            (self._minimap_init_dim, self._minimap_init_dim)
        )
        self._minimap_rect: pg.FRect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.coord: self._minimap_init_pos.xy}
        )

        self._min_win_ratio: float = 1.0  # Keeps the pixels as squares

        # Having a version where 1 grid pixel = 1 pixel is better for scaling
        self._small_minimap_img_1: pg.SurfaceType = pg.Surface(
            (self.grid_size.w * 2, self.grid_size.h * 2)
        )
        # Adds section indicator
        self._small_minimap_img_2: pg.SurfaceType = self._small_minimap_img_1.copy()
        self._small_grid_img: pg.SurfaceType = self._small_minimap_img_1.subsurface(
            (0, 0, self.grid_visible_area.w * 2, self.grid_visible_area.h * 2)
        ).copy()

        self._layer: int = BG_LAYER

        self.update_full(Point(0, 0), [])

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._grid_img, self.grid_rect.topleft, self._layer),
            (self._minimap_img, self._minimap_rect.topleft, self._layer)
        ]

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object's layer
        """

        return self if self.grid_rect.collidepoint(mouse_pos) else None, self._layer

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes objects
        Args:
            window width ratio, window height ratio
        """

        self._min_win_ratio = min(win_ratio_w, win_ratio_h)

        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._min_win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._min_win_ratio
        )

        grid_img_size: tuple[int, int] = (
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

        minimap_img_size: tuple[int, int] = (
            int(self.grid_size.w * minimap_pixel_dim), int(self.grid_size.h * minimap_pixel_dim)
        )
        self._minimap_pos = (
            self._minimap_init_pos.x * win_ratio_w, self._minimap_init_pos.y * win_ratio_h
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_img_size)
        self._minimap_rect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.coord: self._minimap_pos}
        )

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [
            (name, self._layer, depth_counter),
            ('minimap', self._layer, depth_counter)
        ]

    def get_section_indicator(self, offset: Point) -> None:
        """
        Indicates the visible area on the minimap with a white rectangle
        Args:
            offset
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

    def get_grid(self, offset: Point, selected_pixels: list[Point]) -> None:
        """
        Gets the grid image from the minimap
        Args:
            offset, selected pixels
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

        pixel_size: tuple[int, int] = self.transparent_pixel.get_size()
        sequence: BlitSequence = []
        for pixel in selected_pixels:
            if small_grid_rect.colliderect((pixel.xy, pixel_size)):
                sequence.append(
                    (self.transparent_pixel, (pixel.x - offset.x * 2, pixel.y - offset.y * 2))
                )
        self._small_grid_img.fblits(sequence)

        grid_img_size: tuple[int, int] = (
            int(self.grid_visible_area.w * self.grid_pixel_dim),
            int(self.grid_visible_area.h * self.grid_pixel_dim)
        )

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_img_size)
        self.grid_rect = self._grid_img.get_frect(**{self._grid_init_pos.coord: self._grid_pos})

    def update_full(self, offset: Point, selected_pixels: list[Point]) -> None:
        """
        Updates all the pixels on the minimap and retrieves the grid
        Args:
            offset and selected pixels
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
        minimap_img_size: tuple[int, int] = (
            int(grid_w * minimap_pixel_dim), int(grid_h * minimap_pixel_dim)
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_img_size)
        self._minimap_rect = self._minimap_img.get_frect(
            **{self._minimap_init_pos.coord: self._minimap_pos}
        )

        self.get_grid(offset, selected_pixels)

    def update_section(
            self, offset: Point, selected_pixels: list[Point],
            changed_pixels: list[tuple[int, int]]
    ) -> None:
        """
        Updates specific pixels on the minimap and retrieves the grid
        Args:
            offset, selected pixels, changed pixels
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
            self, img: Optional[pg.SurfaceType], offset: Point, selected_pixels: list[Point]
    ) -> None:
        """
        Loads a surface's rgba values into a 3D array
        Args:
            image (if it's None it creates an empty grid), offset, selected pixels
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
        Resizes the grid
        Args:
            size
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

    def zoom(self, amount: int, reach_limit: list[bool]) -> None:
        """
        Changes pixel dimension and visible area
        Args:
            amount, reach limit flags
        """

        visible_area: Size = self.grid_visible_area
        if any(reach_limit):
            if reach_limit[0]:
                visible_area.w = visible_area.h = 1
            elif reach_limit[1]:
                visible_area.w, visible_area.h = self.grid_size.wh
        else:
            if visible_area.w == visible_area.h:
                visible_area.w = max(min(visible_area.w - amount, self.grid_size.w), 1)
                visible_area.h = max(min(visible_area.h - amount, self.grid_size.h), 1)
            else:
                if amount > 0:
                    #  Zooming in decreases the largest side
                    if visible_area.w > visible_area.h:
                        visible_area.w = max(visible_area.w - amount, 1)
                        visible_area.h = min(visible_area.wh)
                    else:
                        visible_area.h = max(visible_area.h - amount, 1)
                        visible_area.w = min(visible_area.wh)
                else:
                    #  Zooming out increases the smallest side only if it can be increased
                    increase_w: bool = (
                        (visible_area.w < visible_area.h or visible_area.h == self.grid_size.h) and
                        visible_area.w != self.grid_size.w
                    )
                    if increase_w:
                        visible_area.w = min(visible_area.w - amount, self.grid_size.w)
                        visible_area.h = max(min(visible_area.w, self.grid_size.h), visible_area.h)
                    else:
                        visible_area.h = min(visible_area.h - amount, self.grid_size.h)
                        visible_area.w = max(min(visible_area.h, self.grid_size.w), visible_area.w)

        self.grid_pixel_dim = min(
            self._grid_init_dim / visible_area.w * self._min_win_ratio,
            self._grid_init_dim / visible_area.h * self._min_win_ratio
        )

    def reset(self, selected_pixels: list[Point]) -> None:
        """
        Resets the visible area and offset
        Args:
            selected pixels
        """

        self.grid_visible_area.w = self.grid_visible_area.h = self._grid_init_visible_area
        self.grid_pixel_dim = min(
            self._grid_init_dim / self.grid_visible_area.w * self._min_win_ratio,
            self._grid_init_dim / self.grid_visible_area.h * self._min_win_ratio
        )

        self.get_grid(Point(0, 0), selected_pixels)
        self.get_section_indicator(Point(0, 0))


class GridManager:
    """
    Class to create and edit a grid of pixels
    """

    __slots__ = (
        'grid', '_offset', '_selected_pixels', '_hovering',
        '_prev_mouse_pos', '_traveled_dist', 'sub_objs'
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object
        Args:
            grid position, minimap position
        """

        self.grid: Grid = Grid(grid_pos, minimap_pos)
        self._offset: Point = Point(0, 0)

        self._selected_pixels: list[Point] = []
        self._hovering: bool = False

        self._prev_mouse_pos: Point = Point(*pg.mouse.get_pos())
        self._traveled_dist: Point = Point(0, 0)

        self.sub_objs: ObjsInfo = [
            ('grid', self.grid)
        ]

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._selected_pixels = []
        self._hovering = False
        self._traveled_dist.x = self._traveled_dist.y = 0

        self.grid.get_grid(self._offset, self._selected_pixels)

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, -1, depth_counter)]

    def load_path(self, file_path: str) -> None:
        """
        Loads an image from a path and renders it into the grid
        Args:
            path, if it's empty it creates an empty grid
        """

        self._offset.x = self._offset.y = 0

        img: Optional[pg.SurfaceType] = (
            pg.image.load(file_path).convert_alpha() if file_path else None
        )
        self.grid.load_img(img, self._offset, self._selected_pixels)

    def _handle_keys(self, keys: list[int], mouse_pixel: Point, brush_size: int) -> None:
        """
        Handles grid movement with arrows
        Args:
            keys, mouse pixel, brush size
        """

        if not any(key in keys for key in (pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN)):
            return

        k_mods: int = pg.key.get_mods()
        ctrl: int = k_mods & pg.KMOD_CTRL

        size: Size = self.grid.grid_size
        visible_area: Size = self.grid.grid_visible_area
        pixel_dim: float = self.grid.grid_pixel_dim

        value: int = 1
        if k_mods & pg.KMOD_ALT:
            value = brush_size
        if k_mods & pg.KMOD_SHIFT:
            value = max(visible_area.wh)

        extra: int
        if pg.K_LEFT in keys:
            if ctrl:
                mouse_pixel.x = 0
                self._offset.x = 0
            else:
                mouse_pixel.x -= value
                if mouse_pixel.x < 0:
                    extra = mouse_pixel.x
                    self._offset.x = max(self._offset.x + extra, 0)
                    mouse_pixel.x = 0
        if pg.K_RIGHT in keys:
            if ctrl:
                mouse_pixel.x = visible_area.w - 1
                self._offset.x = size.w - visible_area.w
            else:
                mouse_pixel.x += value
                if mouse_pixel.x + 1 > visible_area.w:
                    extra = mouse_pixel.x + 1 - visible_area.w
                    self._offset.x = min(
                        self._offset.x + extra, size.w - visible_area.w
                    )
                    mouse_pixel.x = visible_area.w - 1
        if pg.K_UP in keys:
            if ctrl:
                mouse_pixel.y = 0
                self._offset.y = 0
            else:
                mouse_pixel.y -= value
                if mouse_pixel.y < 0:
                    extra = mouse_pixel.y
                    self._offset.y = max(self._offset.y + extra, 0)
                    mouse_pixel.y = 0
        if pg.K_DOWN in keys:
            if ctrl:
                mouse_pixel.y = visible_area.h - 1
                self._offset.y = size.h - visible_area.h
            else:
                mouse_pixel.y += value
                if mouse_pixel.y + 1 > visible_area.h:
                    extra = mouse_pixel.y + 1 - visible_area.h
                    self._offset.y = min(
                        self._offset.y + extra, size.h - visible_area.h
                    )
                    mouse_pixel.y = visible_area.h - 1

        self.grid.get_section_indicator(self._offset)
        pg.mouse.set_pos((
            int(self.grid.grid_rect.x + mouse_pixel.x * pixel_dim + pixel_dim / 2.0),
            int(self.grid.grid_rect.y + mouse_pixel.y * pixel_dim + pixel_dim / 2.0)
        ))

    def _get_pixel_info(
            self, mouse_info: MouseInfo, keys: list[int], brush_size: int
    ) -> tuple[Point, Point]:
        """
        Calculates previous and current mouse pixel and handles arrow movement
        Args:
            mouse info, keys, brush size
        Returns:
            start and end
        """

        prev_mouse_pixel: Point = Point(
            int((self._prev_mouse_pos.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int((self._prev_mouse_pos.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )
        mouse_pixel: Point = Point(
            int((mouse_info.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int((mouse_info.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )

        prev_grid_offset: Point = Point(self._offset.x, self._offset.y)
        # Can change offset, can't be in the move method
        self._handle_keys(keys, mouse_pixel, brush_size)

        prev_mouse_pixel.x += prev_grid_offset.x - brush_size // 2
        prev_mouse_pixel.y += prev_grid_offset.y - brush_size // 2
        mouse_pixel.x += self._offset.x - brush_size // 2
        mouse_pixel.y += self._offset.y - brush_size // 2

        return prev_mouse_pixel, mouse_pixel

    def _brush(
            self, start: Point, end: Point, drawing: bool, brush_size: int,
            extra_info: dict[str, Any]
    ) -> list[tuple[int, int]]:
        """
        Handles brush tool
        Args:
            start, end, drawing bool, brush size, extra info
        Returns:
            changed pixels
        """

        single_pixels: list[tuple[int, int]] = []
        grid_size: Size = self.grid.grid_size

        self._selected_pixels.append(Point(end.x * 2, end.y * 2))
        if extra_info['x_mirror']:
            for pixel in self._selected_pixels.copy():
                x: int = (grid_size.w - brush_size) * 2 - pixel.x
                self._selected_pixels.append(Point(x, pixel.y))
        if extra_info['y_mirror']:
            for pixel in self._selected_pixels.copy():
                y: int = (grid_size.h - brush_size) * 2 - pixel.y
                self._selected_pixels.append(Point(pixel.x, y))

        if not drawing:
            return single_pixels

        '''
        Get the coordinates of the grid pixels the mouse touched between frames using
        Bresenham's Line Algorithm
        '''

        x_1: int = max(min(start.x, grid_size.w - 1), -brush_size + 1)
        y_1: int = max(min(start.y, grid_size.h - 1), -brush_size + 1)
        x_2: int = max(min(end.x, grid_size.w - 1), -brush_size + 1)
        y_2: int = max(min(end.y, grid_size.h - 1), -brush_size + 1)

        d: Point = Point(abs(x_2 - x_1), abs(y_2 - y_1))
        s: Point = Point(1 if x_1 < x_2 else -1, 1 if y_1 < y_2 else -1)
        err: int = d.x - d.y
        while True:
            single_pixels.append((x_1, y_1))
            if x_1 == x_2 and y_1 == y_2:
                break

            err_2: int = err * 2
            if err_2 > -d.y:
                err -= d.y
                x_1 += s.x
            if err_2 < d.x:
                err += d.x
                y_1 += s.y

        if extra_info['x_mirror']:
            for x, y in single_pixels.copy():
                new_x: int = grid_size.w - brush_size - x
                single_pixels.append((new_x, y))
        if extra_info['y_mirror']:
            for x, y in single_pixels.copy():
                new_y: int = grid_size.h - brush_size - y
                single_pixels.append((x, new_y))

        changed_pixels: list[tuple[int, int]] = []
        for x, y in single_pixels:
            changed_pixels += [
                (x_pos, y_pos)
                for x_pos in range(max(x, 0), min(x + brush_size, grid_size.w))
                for y_pos in range(max(y, 0), min(y + brush_size, grid_size.h))
            ]

        return changed_pixels

    def _draw(
            self, mouse_info: MouseInfo, keys: list[int], color: ColorType, brush_size: int,
            tool_info: tuple[str, dict[str, Any]]
    ) -> None:
        """
        Handles grid drawing
        Args:
            mouse_info, keys, color, brush size, tool info
        """

        prev_mouse_pixel: Point  # Absolute coordinate
        mouse_pixel: Point  # Absolute coordinate
        prev_mouse_pixel, mouse_pixel = self._get_pixel_info(mouse_info, keys, brush_size)

        if self.grid.transparent_pixel.get_width() != brush_size * 2:
            self.grid.transparent_pixel = pg.transform.scale(
                self.grid.transparent_pixel, (brush_size * 2, brush_size * 2)
            )
            self.grid.get_grid(self._offset, self._selected_pixels)

        prev_selected_pixels: list[Point] = self._selected_pixels
        self._selected_pixels = []

        drawing: bool = (
            (mouse_info.buttons[0] or pg.K_RETURN in keys) or
            (mouse_info.buttons[2] or pg.K_BACKSPACE in keys)
        )

        changed_pixels: list[tuple[int, int]] = []
        match tool_info[0]:
            case 'brush':
                changed_pixels += self._brush(
                    prev_mouse_pixel, mouse_pixel, drawing, brush_size, tool_info[1]
                )

        prev_grid_pixels: NDArray[np.uint8] = np.copy(self.grid.pixels)
        if changed_pixels:
            full_color: ColorType = (0, 0, 0, 0)
            if mouse_info.buttons[0] or pg.K_RETURN in keys:
                full_color = color + (255,)

            changed_pixels = list(set(changed_pixels))
            for x, y in changed_pixels:
                self.grid.pixels[y, x] = full_color

        if not np.array_equal(self.grid.pixels, prev_grid_pixels):
            self.grid.update_section(self._offset, self._selected_pixels, changed_pixels)
        elif self._selected_pixels != prev_selected_pixels:
            self.grid.get_grid(self._offset, self._selected_pixels)

    def _move(self, mouse_info: MouseInfo) -> None:
        """
        Allows changing the section of the grid that is drawn
        Args:
            mouse info
        """

        if not mouse_info.buttons[1]:
            self._traveled_dist.x = self._traveled_dist.y = 0

            return

        pixels_traveled: int

        self._traveled_dist.x += self._prev_mouse_pos.x - mouse_info.x
        if abs(self._traveled_dist.x) > self.grid.grid_pixel_dim:
            pixels_traveled = round(self._traveled_dist.x / self.grid.grid_pixel_dim)
            self._traveled_dist.x -= int(pixels_traveled * self.grid.grid_pixel_dim)

            self._offset.x = max(
                min(
                    self._offset.x + pixels_traveled,
                    self.grid.grid_size.w - self.grid.grid_visible_area.w
                ), 0
            )
            self.grid.get_section_indicator(self._offset)
            self.grid.get_grid(self._offset, self._selected_pixels)

        self._traveled_dist.y += self._prev_mouse_pos.y - mouse_info.y
        if abs(self._traveled_dist.y) > self.grid.grid_pixel_dim:
            pixels_traveled = round(self._traveled_dist.y / self.grid.grid_pixel_dim)
            self._traveled_dist.y -= int(pixels_traveled * self.grid.grid_pixel_dim)

            self._offset.y = max(
                min(
                    self._offset.y + pixels_traveled,
                    self.grid.grid_size.h - self.grid.grid_visible_area.h
                ), 0
            )
            self.grid.get_section_indicator(self._offset)
            self.grid.get_grid(self._offset, self._selected_pixels)

    def resize(self, size: Optional[Size]) -> None:
        """
        Resizes the grid
        Args:
            size
        """

        if not size:
            return

        self._traveled_dist.x, self._traveled_dist.y = 0, 0

        self.grid.resize(size)
        self._offset.x = min(
            self._offset.x, self.grid.grid_size.w - self.grid.grid_visible_area.w
        )
        self._offset.y = min(
            self._offset.y, self.grid.grid_size.h - self.grid.grid_visible_area.h
        )

        self.grid.update_full(self._offset, self._selected_pixels)

    def zoom(self, amount: int, brush_size: int, reach_limit: list[bool]) -> None:
        """
        Zooms in/out
        Args:
            amount, brush size, reach limit flags
        """

        if not self._hovering:
            return

        mouse_pos: Point = Point(*pg.mouse.get_pos())

        prev_mouse_pixel: Point = Point(
            int((mouse_pos.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int((mouse_pos.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )
        prev_mouse_pixel.x -= brush_size // 2
        prev_mouse_pixel.y -= brush_size // 2

        self.grid.zoom(amount, reach_limit)

        mouse_pixel: Point = Point(
            int((mouse_pos.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int((mouse_pos.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )
        mouse_pixel.x -= brush_size // 2
        mouse_pixel.y -= brush_size // 2

        self._offset.x = max(
            min(
                self._offset.x + prev_mouse_pixel.x - mouse_pixel.x,
                self.grid.grid_size.w - self.grid.grid_visible_area.w
            ), 0
        )
        self._offset.y = max(
            min(
                self._offset.y + prev_mouse_pixel.y - mouse_pixel.y,
                self.grid.grid_size.h - self.grid.grid_visible_area.h
            ), 0
        )

        for pixel in self._selected_pixels:
            pixel.x = mouse_pixel.x * 2
            pixel.y = mouse_pixel.y * 2

        self.grid.get_grid(self._offset, self._selected_pixels)
        self.grid.get_section_indicator(self._offset)

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: list[int], color: ColorType,
            brush_size: int, tool_info: tuple[str, dict[str, Any]]
    ) -> None:
        """
        Allows drawing, moving and zooming
        Args:
            hovered object (can be None), mouse info, keys, color, brush size, tool info
        """

        if self.grid != hover_obj:
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False
        else:
            if not self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
                self._hovering = True

        # Makes drawing possible even 1 frame after the grid was left
        if self.grid == hover_obj or self.grid.check_hover(self._prev_mouse_pos.xy)[0]:
            self._draw(mouse_info, keys, color, brush_size, tool_info)
        elif self._selected_pixels:
            self._selected_pixels = []
            self.grid.get_grid(self._offset, self._selected_pixels)

        self._move(mouse_info)

        k_mods: int = pg.key.get_mods()
        if k_mods & pg.KMOD_CTRL and pg.K_r in keys:
            self._offset.x = self._offset.y = 0
            self._traveled_dist.x = self._traveled_dist.y = 0
            self.grid.reset(self._selected_pixels)

        self._prev_mouse_pos.x, self._prev_mouse_pos.y = mouse_info.x, mouse_info.y
