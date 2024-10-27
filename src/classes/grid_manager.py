"""
Paintable pixel grid with a minimap
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from math import ceil
from typing import Final, Optional, Any

from src.utils import Point, Size, RectPos, ObjInfo, MouseInfo, get_img, get_pixels, resize_obj
from src.type_utils import ColorType, ToolInfo, BlitSequence, LayeredBlitSequence
from src.consts import WHITE, EMPTY_TILE_SURF, BG_LAYER

TRANSPARENT_GREY: Final[ColorType] = (120, 120, 120, 125)


def _decrease_mouse_tile(mouse_coord: int, value: int, offset: int) -> tuple[int, int]:
    """
    Decreases a coordinate of the mouse tile
    Args:
        mouse coordinate, movement value, offset
    Returns:
        new mouse coordinate, new offset
    """

    new_mouse_coord: int = mouse_coord
    new_offset: int = offset
    if pg.key.get_mods() & pg.KMOD_CTRL:
        new_mouse_coord = new_offset = 0
    else:
        new_mouse_coord -= value
        if new_mouse_coord < 0:
            extra_offset: int = new_mouse_coord
            new_offset = max(new_offset + extra_offset, 0)
            new_mouse_coord = 0

    return new_mouse_coord, new_offset


def _increase_mouse_tile(
        mouse_coord: int, value: int, offset: int, visible_side: int, side: int
) -> tuple[int, int]:
    """
    Increases a coordinate of the mouse tile
    Args:
        mouse coordinate, movement value, offset, side of visible area, side of area
    Returns:
        new mouse coordinate, new offset
    """

    new_mouse_coord: int = mouse_coord
    new_offset: int = offset
    if pg.key.get_mods() & pg.KMOD_CTRL:
        new_mouse_coord = visible_side - 1
        new_offset = side - visible_side
    else:
        new_mouse_coord += value
        if new_mouse_coord + 1 > visible_side:
            extra_offset: int = new_mouse_coord + 1 - visible_side
            new_offset = min(new_offset + extra_offset, side - visible_side)
            new_mouse_coord = visible_side - 1

    return new_mouse_coord, new_offset


def _get_tiles_in_line(x_1: int, y_1: int, x_2: int, y_2: int) -> list[tuple[int, int]]:
    """
    Gets the tiles touched by a line using Bresenham's Line Algorithm
    Args:
        line start x, line start y, line end x, line end y
    Returns:
        tiles
    """

    tiles: list[tuple[int, int]] = []

    delta_x: int = abs(x_2 - x_1)
    delta_y: int = abs(y_2 - y_1)
    step_x: int = 1 if x_1 < x_2 else -1
    step_y: int = 1 if y_1 < y_2 else -1
    err: int = delta_x - delta_y
    while True:
        tiles.append((x_1, y_1))
        if x_1 == x_2 and y_1 == y_2:
            break

        err_2: int = err * 2
        if err_2 > -delta_y:
            err -= delta_y
            x_1 += step_x
        if err_2 < delta_x:
            err += delta_x
            y_1 += step_y

    return tiles


class Grid:
    """
    Class to create a pixel grid and its minimap
    """

    __slots__ = (
        '_grid_init_pos', 'area', '_init_visible_area', 'visible_area', 'grid_tile_dim',
        '_grid_img', 'grid_rect', '_grid_init_size', 'tiles', 'transparent_tile_img',
        '_minimap_init_pos', '_minimap_img', '_minimap_rect', '_minimap_init_size',
        '_min_win_ratio', '_small_minimap_img_1', '_small_minimap_img_2', '_small_grid_img',
        '_layer'
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the grid and minimap
        Args:
            grid position, minimap position
        """

        #  Tiles dimensions are floats to represent the full size more accurately when resizing

        self._grid_init_pos: RectPos = grid_pos

        self.area: Size = Size(64, 64)
        self._init_visible_area: Size = Size(32, 32)
        self.visible_area: Size = Size(*self._init_visible_area.wh)

        self.grid_tile_dim: float = 18.0

        self._grid_img: pg.Surface = pg.Surface((
            ceil(self.visible_area.w * self.grid_tile_dim),
            ceil(self.visible_area.h * self.grid_tile_dim)
        ))
        self.grid_rect: pg.Rect = self._grid_img.get_rect(
            **{self._grid_init_pos.coord_type: self._grid_init_pos.xy}
        )

        self._grid_init_size: Size = Size(*self.grid_rect.size)

        self.tiles: NDArray[np.uint8] = np.zeros((self.area.h, self.area.w, 4), np.uint8)
        self.transparent_tile_img: pg.Surface = pg.Surface((2, 2), pg.SRCALPHA)
        self.transparent_tile_img.fill(TRANSPARENT_GREY)

        self._minimap_init_pos: RectPos = minimap_pos

        self._minimap_img: pg.Surface = pg.Surface((256, 256))
        self._minimap_rect: pg.Rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: self._minimap_init_pos.xy}
        )

        self._minimap_init_size: Size = Size(*self._minimap_rect.size)

        self._min_win_ratio: float = 1.0  # Keeps the tiles as squares

        # Having a version where 1 tile = 1 pixel is better for scaling
        self._small_minimap_img_1: pg.Surface = pg.Surface((self.area.w * 2, self.area.h * 2))
        # Adds the section indicator
        self._small_minimap_img_2: pg.Surface = self._small_minimap_img_1.copy()
        self._small_grid_img: pg.Surface = self._small_minimap_img_1.subsurface(
            (0, 0, self.visible_area.w * 2, self.visible_area.h * 2)
        ).copy()

        self._layer: int = BG_LAYER

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._grid_img, self.grid_rect.topleft, self._layer),
            (self._minimap_img, self._minimap_rect.topleft, self._layer)
        ]

    def check_hovering(self, mouse_pos: tuple[int, int]) -> tuple[Optional["Grid"], int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object layer
        """

        return self if self.grid_rect.collidepoint(mouse_pos) else None, self._layer

    def resize(self, win_ratio: tuple[float, float]) -> None:
        """
        Resizes the object
        Args:
            window size ratio
        """

        self._min_win_ratio = min(win_ratio)

        unscaled_grid_tile_dim: float = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        )
        unscaled_grid_size: tuple[float, float] = (
            self.visible_area.w * unscaled_grid_tile_dim,
            self.visible_area.h * unscaled_grid_tile_dim
        )
        self.grid_tile_dim = unscaled_grid_tile_dim * self._min_win_ratio

        grid_pos: tuple[int, int]
        grid_size: tuple[int, int]
        grid_pos, grid_size = resize_obj(
            self._grid_init_pos, *unscaled_grid_size, *win_ratio, True
        )

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_size)
        self.grid_rect = self._grid_img.get_rect(**{self._grid_init_pos.coord_type: grid_pos})

        unscaled_minimap_tile_dim: float = min(
            self._minimap_init_size.w / self.area.w, self._minimap_init_size.h / self.area.h
        ) * self._min_win_ratio
        unscaled_minimap_size: tuple[float, float] = (
            self.area.w * unscaled_minimap_tile_dim, self.area.h * unscaled_minimap_tile_dim
        )

        minimap_pos: tuple[int, int]
        minimap_size: tuple[int, int]
        minimap_pos, minimap_size = resize_obj(
            self._minimap_init_pos, *unscaled_minimap_size, *win_ratio, True
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_size)
        self._minimap_rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: minimap_pos}
        )

    def set_section_indicator(self, offset: Point) -> None:
        """
        Indicates the visible area on the minimap with a white rectangle
        Args:
            offset
        """

        self._small_minimap_img_2 = self._small_minimap_img_1.copy()

        visible_area_rect: pg.Rect = pg.Rect(
            offset.x * 2, offset.y * 2, self.visible_area.w * 2, self.visible_area.h * 2
        )
        pg.draw.rect(self._small_minimap_img_2, WHITE, visible_area_rect, 2)

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, self._minimap_rect.size)

    def get_grid(self, offset: Point, selected_tiles: list[Point]) -> None:
        """
        Gets the grid image from the minimap
        Args:
            offset, selected tiles
        """

        w: int
        h: int
        w, h = self.visible_area.wh
        if offset.x + w > self.area.w:
            w -= offset.x + w - self.area.w
        if offset.y + h > self.area.h:
            h -= offset.y + h - self.area.h

        w *= 2
        h *= 2

        small_grid_rect: pg.Rect = pg.Rect(offset.x * 2, offset.y * 2, w, h)
        self._small_grid_img = self._small_minimap_img_1.subsurface(small_grid_rect).copy()

        tile_size: tuple[int, int] = self.transparent_tile_img.get_size()
        blit_sequence: BlitSequence = [
            (self.transparent_tile_img, (tile.x - (offset.x * 2), tile.y - (offset.y * 2)))
            for tile in selected_tiles
            if small_grid_rect.colliderect((tile.xy, tile_size))
        ]
        self._small_grid_img.fblits(blit_sequence)

        grid_size: tuple[int, int] = (
            ceil(self.visible_area.w * self.grid_tile_dim),
            ceil(self.visible_area.h * self.grid_tile_dim)
        )
        grid_pos: tuple[int, int] = getattr(self.grid_rect, self._grid_init_pos.coord_type)

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_size)
        self.grid_rect = self._grid_img.get_rect(**{self._grid_init_pos.coord_type: grid_pos})

    def update_full(self, offset: Point) -> None:
        """
        Updates all the tiles on the minimap and retrieves the grid
        Args:
            offset
        """

        w: int
        h: int
        w, h = self.area.wh
        blit_sequence: BlitSequence = []

        tiles: NDArray[np.uint8] = self.tiles
        empty_tile_surf: pg.Surface = EMPTY_TILE_SURF
        tile_surf: pg.Surface = pg.Surface((2, 2))
        for y in range(h):
            row: NDArray[np.uint8] = tiles[y]
            for x in range(w):
                if not row[x, -1]:
                    blit_sequence.append((empty_tile_surf, (x * 2, y * 2)))
                else:
                    tile_surf.fill(row[x])
                    blit_sequence.append((tile_surf.copy(), (x * 2, y * 2)))
        self._small_minimap_img_1.fblits(blit_sequence)

        self._small_minimap_img_2 = self._small_minimap_img_1.copy()

        visible_area_rect: pg.Rect = pg.Rect(
            offset.x * 2, offset.y * 2, self.visible_area.w * 2, self.visible_area.h * 2
        )
        pg.draw.rect(self._small_minimap_img_2, WHITE, visible_area_rect, 2)

        minimap_tile_dim: float = min(
            self._minimap_init_size.w / w, self._minimap_init_size.h / h
        ) * self._min_win_ratio

        minimap_size: tuple[int, int] = (ceil(w * minimap_tile_dim), ceil(h * minimap_tile_dim))
        minimap_pos: tuple[int, int] = getattr(
            self._minimap_rect, self._minimap_init_pos.coord_type
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_size)
        self._minimap_rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: minimap_pos}
        )

        self.get_grid(offset, [])

    def update_section(
            self, offset: Point, selected_tiles: list[Point], changed_tiles: list[tuple[int, int]]
    ) -> None:
        """
        Updates specific tiles on the minimap and retrieves the grid
        Args:
            offset, selected tiles, changed tiles
        """

        blit_sequence: BlitSequence = []

        tiles: NDArray[np.uint8] = self.tiles
        empty_tile_surf: pg.Surface = EMPTY_TILE_SURF
        tile_surf: pg.Surface = pg.Surface((2, 2))
        for x, y in changed_tiles:
            if not tiles[y, x, -1]:
                blit_sequence.append((empty_tile_surf, (x * 2, y * 2)))
            else:
                tile_surf.fill(tiles[y, x])
                blit_sequence.append((tile_surf.copy(), (x * 2, y * 2)))
        self._small_minimap_img_1.fblits(blit_sequence)

        self.set_section_indicator(offset)
        self.get_grid(offset, selected_tiles)

    def set_tiles(self, img: Optional[pg.Surface], offset: Point) -> None:
        """
        Sets the grid tiles using an image pixels
        Args:
            image (if it's None it creates an empty grid), offset
        """

        self.tiles = np.zeros((self.area.h, self.area.w, 4), np.uint8)
        if img:
            self.tiles = get_pixels(img)

            extra_rows: int = self.area.h - self.tiles.shape[0]
            if extra_rows < 0:
                self.tiles = self.tiles[:self.area.h, :, :]
            elif extra_rows > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0
                )

            extra_cols: int = self.area.w - self.tiles.shape[1]
            if extra_cols < 0:
                self.tiles = self.tiles[:, :self.area.w, :]
            elif extra_cols > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0
                )

        self.update_full(offset)

    def set_size(self, area: Size) -> None:
        """
        Sets the grid size
        Args:
            area
        """

        self.area = area

        extra_rows: int = self.area.h - self.tiles.shape[0]
        if extra_rows < 0:
            self.tiles = self.tiles[:self.area.h, :, :]
        elif extra_rows > 0:
            self.tiles = np.pad(self.tiles, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0)

        extra_cols: int = self.area.w - self.tiles.shape[1]
        if extra_cols < 0:
            self.tiles = self.tiles[:, :self.area.w, :]
        elif extra_cols > 0:
            self.tiles = np.pad(self.tiles, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0)

        self.visible_area.w = min(self.visible_area.w, self.area.w)
        self.visible_area.h = min(self.visible_area.h, self.area.h)
        self.grid_tile_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

        self._small_minimap_img_1 = pg.Surface((self.area.w * 2, self.area.h * 2))

    def _zoom_needed_side(self, amount: int) -> None:
        """
        Zooms only the needed side of grid
        Args:
            amount
        """

        visible_area: Size = self.visible_area
        if amount > 0:
            #  Zooming in decreases the largest side
            if visible_area.w > visible_area.h:
                visible_area.w = max(visible_area.w - amount, 1)
                visible_area.h = min(visible_area.wh)
            else:
                visible_area.w = min(visible_area.wh)
                visible_area.h = max(visible_area.h - amount, 1)
        else:
            #  Zooming out increases the smallest side if it can be increased
            should_change_w: bool = (
                (visible_area.w < visible_area.h or visible_area.h == self.area.h) and
                visible_area.w != self.area.w
            )
            if should_change_w:
                visible_area.w = min(visible_area.w - amount, self.area.w)
                visible_area.h = max(min(visible_area.w, self.area.h), visible_area.h)
            else:
                visible_area.h = min(visible_area.h - amount, self.area.h)
                visible_area.w = max(min(visible_area.h, self.area.w), visible_area.w)

    def zoom(self, amount: int, reach_limit: list[bool]) -> None:
        """
        Changes tiles dimension and visible area
        Args:
            amount, reach limit flags
        """

        # Amount is positive when zooming in and negative when zooming out

        visible_area: Size = self.visible_area
        if any(reach_limit):
            if reach_limit[0]:
                visible_area.w = visible_area.h = 1
            if reach_limit[1]:
                visible_area.w, visible_area.h = self.area.wh
        else:
            if visible_area.w != visible_area.h:
                self._zoom_needed_side(amount)
            else:
                visible_area.w = max(min(visible_area.w - amount, self.area.w), 1)
                visible_area.h = max(min(visible_area.h - amount, self.area.h), 1)

        self.grid_tile_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

    def reset(self) -> None:
        """
        Resets the visible area and offset
        """

        self.visible_area.w, self.visible_area.h = self._init_visible_area.wh
        self.grid_tile_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

        self.get_grid(Point(0, 0), [])
        self.set_section_indicator(Point(0, 0))


class GridManager:
    """
    Class to create and edit a grid of pixels
    """

    __slots__ = (
        'grid', '_selected_tiles', '_is_hovering', '_prev_mouse_x', '_prev_mouse_y',
        '_prev_hovered_obj', '_offset', '_traveled_dist', 'objs_info'
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object
        Args:
            grid position, minimap position
        """

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self._selected_tiles: list[Point] = []  # Absolute coordinates
        self._is_hovering: bool = False

        self._prev_mouse_x: int
        self._prev_mouse_y: int
        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()
        self._prev_hovered_obj: Optional[Grid] = None

        self._offset: Point = Point(0, 0)
        self._traveled_dist: Size = Size(0, 0)

        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid)]

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._selected_tiles = []
        self._is_hovering = False
        self._traveled_dist.w = self._traveled_dist.h = 0

        self.grid.get_grid(self._offset, self._selected_tiles)

    def set_from_path(self, file_path: str, area: Optional[Size]) -> None:
        """
        Sets the grid size and tiles
        Args:
            path (if it's empty it creates an empty grid), area
        """

        self._offset.x = self._offset.y = 0

        if area:
            self.grid.set_size(area)
        img: Optional[pg.Surface] = get_img(file_path) if file_path else None
        self.grid.set_tiles(img, self._offset)

    def _move_with_keys(self, keys: list[int], mouse_tile: Point, brush_size: int) -> None:
        """
        Moves the mouse tile with arrows
        Args:
            keys, mouse tile, brush size
        """

        value: int = 1
        if pg.key.get_mods() & pg.KMOD_ALT:
            value = brush_size
        if pg.key.get_mods() & pg.KMOD_SHIFT:
            value = max(self.grid.visible_area.wh)

        new_mouse_tile_x: int
        new_mouse_tile_y: int
        new_mouse_tile_x, new_mouse_tile_y = mouse_tile.xy
        if pg.K_LEFT in keys:
            new_mouse_tile_x, self._offset.x = _decrease_mouse_tile(
                new_mouse_tile_x, value, self._offset.x
            )
        if pg.K_RIGHT in keys:
            new_mouse_tile_x, self._offset.x = _increase_mouse_tile(
                new_mouse_tile_x, value, self._offset.x, self.grid.visible_area.w, self.grid.area.w
            )
        if pg.K_UP in keys:
            new_mouse_tile_y, self._offset.y = _decrease_mouse_tile(
                new_mouse_tile_y, value, self._offset.y
            )
        if pg.K_DOWN in keys:
            new_mouse_tile_y, self._offset.y = _increase_mouse_tile(
                new_mouse_tile_y, value, self._offset.y, self.grid.visible_area.h, self.grid.area.h
            )
        self.grid.set_section_indicator(self._offset)

        relative_mouse_x: int = round(
            (new_mouse_tile_x * self.grid.grid_tile_dim) + (self.grid.grid_tile_dim / 2.0)
        )
        relative_mouse_y: int = round(
            (new_mouse_tile_y * self.grid.grid_tile_dim) + (self.grid.grid_tile_dim / 2.0)
        )
        pg.mouse.set_pos(
            (self.grid.grid_rect.x + relative_mouse_x, self.grid.grid_rect.y + relative_mouse_y)
        )

    def _get_tile_info(
            self, mouse_info: MouseInfo, keys: list[int], brush_size: int
    ) -> tuple[Point, Point]:
        """
        Calculates previous and current mouse tile and handles arrow movement
        Args:
            mouse info, keys, brush size
        Returns:
            start and end
        """

        prev_mouse_tile: Point = Point(
            int((self._prev_mouse_x - self.grid.grid_rect.x) / self.grid.grid_tile_dim),
            int((self._prev_mouse_y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)
        )
        mouse_tile: Point = Point(
            int((mouse_info.x - self.grid.grid_rect.x) / self.grid.grid_tile_dim),
            int((mouse_info.y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)
        )

        prev_offset_x: int
        prev_offset_y: int
        prev_offset_x, prev_offset_y = self._offset.xy

        # Can change offset, so it can't be in the move method
        if any(key in keys for key in (pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN)):
            self._move_with_keys(keys, mouse_tile, brush_size)

        # Mouse is in the center of the tile
        prev_mouse_tile.x += prev_offset_x - (brush_size // 2)
        prev_mouse_tile.y += prev_offset_y - (brush_size // 2)
        mouse_tile.x += self._offset.x - (brush_size // 2)
        mouse_tile.y += self._offset.y - (brush_size // 2)

        return prev_mouse_tile, mouse_tile

    def _brush(
            self, start: Point, end: Point, is_drawing: bool, brush_size: int,
            extra_info: dict[str, Any]
    ) -> list[tuple[int, int]]:
        """
        Handles brush tool
        Args:
            start, end, drawing bool, brush size, extra info
        Returns:
            changed tiles
        """

        changed_tiles: list[tuple[int, int]] = []
        area: Size = self.grid.area

        self._selected_tiles.append(Point(end.x * 2, end.y * 2))
        if extra_info["x_mirror"]:
            self._selected_tiles.extend(
                Point(((area.w - brush_size) * 2) - tile.x, tile.y)
                for tile in self._selected_tiles.copy()
            )
        if extra_info["y_mirror"]:
            self._selected_tiles.extend(
                Point(tile.x, ((area.h - brush_size) * 2) - tile.y)
                for tile in self._selected_tiles.copy()
            )

        if not is_drawing:
            return changed_tiles

        x_1: int = max(min(start.x, area.w - 1), -brush_size + 1)
        y_1: int = max(min(start.y, area.h - 1), -brush_size + 1)
        x_2: int = max(min(end.x, area.w - 1), -brush_size + 1)
        y_2: int = max(min(end.y, area.h - 1), -brush_size + 1)
        changed_tiles.extend(_get_tiles_in_line(x_1, y_1, x_2, y_2))

        if extra_info["x_mirror"]:
            changed_tiles.extend((area.w - brush_size - x, y) for x, y in changed_tiles.copy())
        if extra_info["y_mirror"]:
            changed_tiles.extend((x, area.h - brush_size - y) for x, y in changed_tiles.copy())

        # Resizes the tiles to the brush size
        return [
            (x, y)
            for original_x, original_y in changed_tiles
            for x in range(max(original_x, 0), min(original_x + brush_size, area.w))
            for y in range(max(original_y, 0), min(original_y + brush_size, area.h))
        ]

    def _draw_on_grid(self, tiles: list[tuple[int, int]], color: ColorType) -> None:
        """
        Draws tiles on the grid
        Args:
            tiles, color
        """

        prev_tiles: NDArray[np.uint8] = np.copy(self.grid.tiles)
        unique_tiles: list[tuple[int, int]] = list(set(tiles))
        for x, y in unique_tiles:
            self.grid.tiles[y, x] = color

        if not np.array_equal(self.grid.tiles, prev_tiles):
            self.grid.update_section(self._offset, self._selected_tiles, unique_tiles)

    def _draw(
            self, mouse_info: MouseInfo, keys: list[int], color: ColorType, brush_size: int,
            tool_info: ToolInfo
    ) -> None:
        """
        Handles grid drawing
        Args:
            mouse info, keys, color, brush size, tool info
        """

        prev_mouse_tile: Point  # Absolute coordinate
        mouse_tile: Point  # Absolute coordinate
        prev_mouse_tile, mouse_tile = self._get_tile_info(mouse_info, keys, brush_size)

        if self.grid.transparent_tile_img.get_width() != brush_size * 2:
            self.grid.transparent_tile_img = pg.transform.scale_by(
                self.grid.transparent_tile_img, (brush_size * 2, brush_size * 2)
            )
            self.grid.get_grid(self._offset, self._selected_tiles)

        prev_selected_tiles: list[Point] = self._selected_tiles
        self._selected_tiles = []

        is_coloring: bool = mouse_info.pressed[0] or pg.K_RETURN in keys
        is_drawing: bool = is_coloring or (mouse_info.pressed[2] or pg.K_BACKSPACE in keys)

        changed_tiles: list[tuple[int, int]] = []
        extra_tool_info: dict[str, Any] = tool_info[1]
        match tool_info[0]:
            case "brush":
                changed_tiles = self._brush(
                    prev_mouse_tile, mouse_tile, is_drawing, brush_size, extra_tool_info
                )

        if changed_tiles:
            self._draw_on_grid(changed_tiles, (color + (255,)) if is_coloring else (0, 0, 0, 0))
        elif self._selected_tiles != prev_selected_tiles:
            self.grid.get_grid(self._offset, self._selected_tiles)

    def _move(self, mouse_info: MouseInfo) -> None:
        """
        Allows changing the section of the grid that is drawn
        Args:
            mouse info
        """

        if not mouse_info.pressed[1]:
            self._traveled_dist.w = self._traveled_dist.h = 0

            return

        tiles_traveled: int

        self._traveled_dist.w += self._prev_mouse_x - mouse_info.x
        if abs(self._traveled_dist.w) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_dist.w / self.grid.grid_tile_dim)
            self._traveled_dist.w -= int(tiles_traveled * self.grid.grid_tile_dim)

            max_offset_x: int = self.grid.area.w - self.grid.visible_area.w
            self._offset.x = max(min(self._offset.x + tiles_traveled, max_offset_x), 0)
            self.grid.set_section_indicator(self._offset)
            self.grid.get_grid(self._offset, self._selected_tiles)

        self._traveled_dist.h += self._prev_mouse_y - mouse_info.y
        if abs(self._traveled_dist.h) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_dist.h / self.grid.grid_tile_dim)
            self._traveled_dist.h -= int(tiles_traveled * self.grid.grid_tile_dim)

            max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
            self._offset.y = max(min(self._offset.y + tiles_traveled, max_offset_y), 0)
            self.grid.set_section_indicator(self._offset)
            self.grid.get_grid(self._offset, self._selected_tiles)

    def set_size(self, area: Optional[Size]) -> None:
        """
        Sets the grid size
        Args:
            area
        """

        if not area:
            return

        self._traveled_dist.w = self._traveled_dist.h = 0

        self.grid.set_size(area)
        self._offset.x = min(self._offset.x, self.grid.area.w - self.grid.visible_area.w)
        self._offset.y = min(self._offset.y, self.grid.area.h - self.grid.visible_area.h)

        self.grid.update_full(self._offset)

    def zoom(self, amount: int, brush_size: int, reach_limit: list[bool]) -> None:
        """
        Zooms in/out
        Args:
            amount, brush size, reach limit flags
        """

        if not self._is_hovering:
            return

        mouse_x: int
        mouse_y: int
        mouse_x, mouse_y = pg.mouse.get_pos()

        prev_mouse_tile_x: int = int((mouse_x - self.grid.grid_rect.x) / self.grid.grid_tile_dim)
        prev_mouse_tile_y: int = int((mouse_y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)

        self.grid.zoom(amount, reach_limit)

        mouse_tile_x: int = int((mouse_x - self.grid.grid_rect.x) / self.grid.grid_tile_dim)
        mouse_tile_y: int = int((mouse_y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)

        uncapped_offset_x: int = self._offset.x + prev_mouse_tile_x - mouse_tile_x
        self._offset.x = max(
            min(uncapped_offset_x, self.grid.area.w - self.grid.visible_area.w), 0
        )
        uncapped_offset_y: int = self._offset.y + prev_mouse_tile_y - mouse_tile_y
        self._offset.y = max(
            min(uncapped_offset_y, self.grid.area.h - self.grid.visible_area.h), 0
        )

        mouse_tile_x -= brush_size // 2
        mouse_tile_y -= brush_size // 2
        for tile in self._selected_tiles:
            tile.x, tile.y = mouse_tile_x * 2, mouse_tile_y * 2

        self.grid.get_grid(self._offset, self._selected_tiles)
        self.grid.set_section_indicator(self._offset)

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int], color: ColorType,
            brush_size: int, tool_info: ToolInfo
    ) -> None:
        """
        Allows drawing, moving and zooming
        Args:
            hovered object (can be None), mouse info, keys, color, brush size, tool info
        """

        if self.grid != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False
        elif not self._is_hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
            self._is_hovering = True

        # Makes drawing possible even 1 frame after the grid was left
        if self.grid in (hovered_obj, self._prev_hovered_obj):
            self._draw(mouse_info, keys, color, brush_size, tool_info)
        elif self._selected_tiles:
            self._selected_tiles = []
            self.grid.get_grid(self._offset, self._selected_tiles)
        self._move(mouse_info)

        if (pg.key.get_mods() & pg.KMOD_CTRL) and pg.K_r in keys:
            self._offset.x = self._offset.y = 0
            self._traveled_dist.w = self._traveled_dist.h = 0
            self.grid.reset()

        self._prev_mouse_x, self._prev_mouse_y = mouse_info.xy
        self._prev_hovered_obj = hovered_obj
