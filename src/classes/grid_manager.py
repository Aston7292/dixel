"""Paintable pixel grid with a minimap."""

from pathlib import Path
from math import ceil
from typing import Optional, Any

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.utils import (
    Point, RectPos, Size, Ratio, ObjInfo, MouseInfo, get_img, get_pixels, resize_obj
)
from src.file_utils import check_file_access
from src.type_utils import PosPair, SizePair, Color, ToolInfo, BlitSequence, LayeredBlitInfo
from src.consts import (
    WHITE, EMPTY_TILE_IMG, BG_LAYER, ACCESS_SUCCESS, ACCESS_DENIED, ACCESS_LOCKED
)


def _decrease_mouse_tile(mouse_coord: int, value: int, offset: int) -> tuple[int, int]:
    """
    Decreases a coordinate of the mouse tile.

    Args:
        mouse coordinate, movement value, offset
    Returns:
        mouse coordinate, offset
    """

    local_mouse_coord: int = mouse_coord
    local_offset: int = offset
    if pg.key.get_mods() & pg.KMOD_CTRL:
        local_mouse_coord = local_offset = 0
    else:
        local_mouse_coord -= value
        if local_mouse_coord < 0:  # Exited the visible area
            extra_offset: int = local_mouse_coord
            local_offset = max(local_offset + extra_offset, 0)
            local_mouse_coord = 0

    return local_mouse_coord, local_offset


def _increase_mouse_tile(
        mouse_coord: int, value: int, offset: int, visible_side: int, side: int
) -> tuple[int, int]:
    """
    Increases a coordinate of the mouse tile.

    Args:
        mouse coordinate, movement value, offset, side of visible area, side of area
    Returns:
        mouse coordinate, offset
    """

    local_mouse_coord: int = mouse_coord
    local_offset: int = offset
    if pg.key.get_mods() & pg.KMOD_CTRL:
        local_mouse_coord = visible_side - 1
        local_offset = side - visible_side
    else:
        local_mouse_coord += value
        if local_mouse_coord >= visible_side:  # Exited the visible area
            extra_offset: int = local_mouse_coord + 1 - visible_side
            local_offset = min(local_offset + extra_offset, side - visible_side)
            local_mouse_coord = visible_side - 1

    return local_mouse_coord, local_offset


def _get_tiles_in_line(x_1: int, y_1: int, x_2: int, y_2: int) -> list[PosPair]:
    """
    Gets the tiles touched by a line using Bresenham's Line Algorithm.

    Args:
        line start x, line start y, line end x, line end y
    Returns:
        tiles
    """

    tiles: list[PosPair] = []

    delta_x: int = abs(x_2 - x_1)
    delta_y: int = abs(y_2 - y_1)
    step_x: int = 1 if x_1 < x_2 else -1
    step_y: int = 1 if y_1 < y_2 else -1
    err: int = delta_x - delta_y
    while True:
        tiles.append((x_1, y_1))
        if x_1 == x_2 and y_1 == y_2:
            return tiles

        err_2: int = err * 2
        if err_2 > -delta_y:
            err -= delta_y
            x_1 += step_x
        if err_2 < delta_x:
            err += delta_x
            y_1 += step_y


class Grid:
    """Class to create a pixel grid and its minimap."""

    __slots__ = (
        "_grid_init_pos", "area", "_init_visible_area", "visible_area", "grid_tile_dim",
        "_grid_img", "grid_rect", "_grid_init_size", "tiles", "transparent_tile_img",
        "_minimap_init_pos", "_minimap_img", "_minimap_rect", "_minimap_init_size",
        "_min_win_ratio", "_small_minimap_img_1", "_small_minimap_img_2", "_small_grid_img",
        "_layer"
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the grid and minimap.

        Args:
            grid position, minimap position
        """

        # Tiles dimensions are floats to represent the full size more accurately when resizing

        self._grid_init_pos: RectPos = grid_pos

        self.area: Size = Size(64, 64)
        self._init_visible_area: Size = Size(32, 32)
        self.visible_area: Size = Size(self._init_visible_area.w, self._init_visible_area.h)

        self.grid_tile_dim: float = 18.0

        self._grid_img: pg.Surface = pg.Surface((
            ceil(self.visible_area.w * self.grid_tile_dim),
            ceil(self.visible_area.h * self.grid_tile_dim)
        ))
        self.grid_rect: pg.Rect = self._grid_img.get_rect(
            **{self._grid_init_pos.coord_type: (self._grid_init_pos.x, self._grid_init_pos.y)}
        )

        self._grid_init_size: Size = Size(*self.grid_rect.size)

        transparent_grey: Color = (120, 120, 120, 125)

        self.tiles: NDArray[np.uint8] = np.zeros((self.area.h, self.area.w, 4), np.uint8)
        self.transparent_tile_img: pg.Surface = pg.Surface((2, 2), pg.SRCALPHA)
        self.transparent_tile_img.fill(transparent_grey)

        self._minimap_init_pos: RectPos = minimap_pos

        self._minimap_img: pg.Surface = pg.Surface((256, 256))
        minimap_xy: PosPair = (self._minimap_init_pos.x, self._minimap_init_pos.y)
        self._minimap_rect: pg.Rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: minimap_xy}
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

    def blit(self) -> list[LayeredBlitInfo]:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._grid_img, self.grid_rect.topleft, self._layer),
            (self._minimap_img, self._minimap_rect.topleft, self._layer)
        ]

    def check_hovering(self, mouse_xy: PosPair) -> tuple[Optional["Grid"], int]:
        """
        Checks if the mouse is hovering any interactable part of the object.

        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object layer
        """

        return self if self.grid_rect.collidepoint(mouse_xy) else None, self._layer

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        self._min_win_ratio = min(win_ratio.w, win_ratio.h)

        unscaled_grid_tile_dim: float = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        )
        unscaled_grid_wh: tuple[float, float] = (
            self.visible_area.w * unscaled_grid_tile_dim,
            self.visible_area.h * unscaled_grid_tile_dim
        )
        self.grid_tile_dim = unscaled_grid_tile_dim * self._min_win_ratio

        grid_xy: PosPair
        grid_wh: SizePair
        grid_xy, grid_wh = resize_obj(self._grid_init_pos, *unscaled_grid_wh, win_ratio, True)

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_wh)
        self.grid_rect = self._grid_img.get_rect(**{self._grid_init_pos.coord_type: grid_xy})

        unscaled_minimap_tile_dim: float = min(
            self._minimap_init_size.w / self.area.w, self._minimap_init_size.h / self.area.h
        ) * self._min_win_ratio
        unscaled_minimap_wh: tuple[float, float] = (
            self.area.w * unscaled_minimap_tile_dim, self.area.h * unscaled_minimap_tile_dim
        )

        minimap_xy: PosPair
        minimap_wh: SizePair
        minimap_xy, minimap_wh = resize_obj(
            self._minimap_init_pos, *unscaled_minimap_wh, win_ratio, True
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_wh)
        self._minimap_rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: minimap_xy}
        )

    def set_section_indicator(self, offset: Point) -> None:
        """
        Indicates the visible area on the minimap with a white rectangle.

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
        Gets the grid image from the minimap.

        Args:
            offset, selected tiles
        """

        small_grid_w: int = self.visible_area.w
        if offset.x + small_grid_w > self.area.w:
            small_grid_w -= offset.x + small_grid_w - self.area.w
        small_grid_w *= 2

        small_grid_h: int = self.visible_area.h
        if offset.y + small_grid_h > self.area.h:
            small_grid_h -= offset.y + small_grid_h - self.area.h
        small_grid_h *= 2

        small_grid_rect: pg.Rect = pg.Rect(offset.x * 2, offset.y * 2, small_grid_w, small_grid_h)
        self._small_grid_img = self._small_minimap_img_1.subsurface(small_grid_rect).copy()

        tile_wh: SizePair = self.transparent_tile_img.get_size()
        blit_sequence: BlitSequence = [
            (self.transparent_tile_img, (tile.x - (offset.x * 2), tile.y - (offset.y * 2)))
            for tile in selected_tiles
            if small_grid_rect.colliderect(((tile.x, tile.y), tile_wh))
        ]
        self._small_grid_img.fblits(blit_sequence)

        grid_coord: PosPair = getattr(self.grid_rect, self._grid_init_pos.coord_type)
        grid_wh: SizePair = (
            ceil(self.visible_area.w * self.grid_tile_dim),
            ceil(self.visible_area.h * self.grid_tile_dim)
        )

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_wh)
        self.grid_rect = self._grid_img.get_rect(**{self._grid_init_pos.coord_type: grid_coord})

    def update_full(self, offset: Point, selected_tiles: list[Point]) -> None:
        """
        Updates all the tiles on the minimap and retrieves the grid.

        Args:
            offset, selected tiles
        """

        local_area: Size = self.area
        local_tiles: NDArray[np.uint8] = self.tiles
        local_empty_tile_img: pg.Surface = EMPTY_TILE_IMG

        blit_sequence: BlitSequence = []
        tile_img: pg.Surface = pg.Surface((2, 2))
        for y in range(local_area.h):
            row: NDArray[np.uint8] = local_tiles[y]
            for x in range(local_area.w):
                if not row[x, -1]:
                    blit_sequence.append((local_empty_tile_img, (x * 2, y * 2)))
                else:
                    tile_img.fill(row[x])
                    blit_sequence.append((tile_img.copy(), (x * 2, y * 2)))
        self._small_minimap_img_1.fblits(blit_sequence)

        self._small_minimap_img_2 = self._small_minimap_img_1.copy()

        visible_area_rect: pg.Rect = pg.Rect(
            offset.x * 2, offset.y * 2, self.visible_area.w * 2, self.visible_area.h * 2
        )
        pg.draw.rect(self._small_minimap_img_2, WHITE, visible_area_rect, 2)

        minimap_tile_dim: float = min(
            self._minimap_init_size.w / local_area.w, self._minimap_init_size.h / local_area.h
        ) * self._min_win_ratio

        minimap_coord: PosPair = getattr(self._minimap_rect, self._minimap_init_pos.coord_type)
        minimap_wh: SizePair = (
            ceil(local_area.w * minimap_tile_dim), ceil(local_area.h * minimap_tile_dim)
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_wh)
        self._minimap_rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: minimap_coord}
        )

        self.get_grid(offset, selected_tiles)

    def update_section(
            self, offset: Point, selected_tiles: list[Point], changed_tiles: tuple[PosPair, ...]
    ) -> None:
        """
        Updates specific tiles on the minimap and retrieves the grid.

        Args:
            offset, selected tiles, changed tiles
        """

        local_tiles: NDArray[np.uint8] = self.tiles
        local_empty_tile_img: pg.Surface = EMPTY_TILE_IMG

        blit_sequence: BlitSequence = []
        tile_img: pg.Surface = pg.Surface((2, 2))
        for x, y in changed_tiles:
            if not local_tiles[y, x, -1]:
                blit_sequence.append((local_empty_tile_img, (x * 2, y * 2)))
            else:
                tile_img.fill(local_tiles[y, x])
                blit_sequence.append((tile_img.copy(), (x * 2, y * 2)))
        self._small_minimap_img_1.fblits(blit_sequence)

        self.set_section_indicator(offset)
        self.get_grid(offset, selected_tiles)

    def set_tiles(
            self, img: Optional[pg.Surface], offset: Point, selected_tiles: list[Point]
    ) -> None:
        """
        Sets the grid tiles using an image pixels.

        Args:
            image (if it's None it creates an empty grid), offset, selected tiles
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

        self.grid_tile_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

        self.update_full(offset, selected_tiles)

    def set_area(self, area: Size) -> None:
        """
        Sets the grid area.

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

    def _decrease_largest_side(self, amount: int) -> None:
        """
        Decreases the largest side of the visible area.

        Args:
            amount
        """

        if self.visible_area.w > self.visible_area.h:
            self.visible_area.w = max(self.visible_area.w - amount, 1)
            self.visible_area.h = min(self.visible_area.w, self.visible_area.h)
        else:
            self.visible_area.w = min(self.visible_area.w, self.visible_area.h)
            self.visible_area.h = max(self.visible_area.h - amount, 1)

    def _increase_smallest_side(self, amount: int) -> None:
        """
        Increases the smallest side of the visible area.

        Args:
            amount
        """

        should_increase_w: bool = (
            self.visible_area.w < self.visible_area.h or self.visible_area.h == self.area.h
        )
        if should_increase_w and self.visible_area.w != self.area.w:
            self.visible_area.w = min(self.visible_area.w - amount, self.area.w)
            self.visible_area.h = max(min(self.visible_area.w, self.area.h), self.visible_area.h)
        else:
            self.visible_area.h = min(self.visible_area.h - amount, self.area.h)
            self.visible_area.w = max(min(self.visible_area.h, self.area.w), self.visible_area.w)

    def zoom(self, amount: int, reach_limit: list[bool]) -> None:
        """
        Changes tiles dimension and visible area.

        Args:
            amount, reach limit flags
        """

        # Amount is positive when zooming in and negative when zooming out

        if any(reach_limit):
            if reach_limit[0]:
                self.visible_area.w = self.visible_area.h = 1
            if reach_limit[1]:
                self.visible_area.w, self.visible_area.h = self.area.w, self.area.h
        elif self.visible_area.w == self.visible_area.h:
            self.visible_area.w = max(min(self.visible_area.w - amount, self.area.w), 1)
            self.visible_area.h = max(min(self.visible_area.h - amount, self.area.h), 1)
        elif amount > 0:
            self._decrease_largest_side(amount)
        else:
            self._increase_smallest_side(amount)

        self.grid_tile_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

    def reset(self, selected_tiles: list[Point]) -> None:
        """
        Resets the visible area and offset.

        Args:
            selected tiles
        """

        self.visible_area.w = min(self._init_visible_area.w, self.area.w)
        self.visible_area.h = min(self._init_visible_area.h, self.area.h)
        self.grid_tile_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

        self.get_grid(Point(0, 0), selected_tiles)
        self.set_section_indicator(Point(0, 0))


class GridManager:
    """Class to create and edit a grid of pixels."""

    __slots__ = (
        "grid", "_selected_tiles", "_is_hovering", "_prev_mouse_x", "_prev_mouse_y",
        "_prev_hovered_obj", "offset", "_traveled_dist", "objs_info"
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object.

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

        self.offset: Point = Point(0, 0)
        self._traveled_dist: Point = Point(0, 0)

        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid)]

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self._selected_tiles.clear()
        self._is_hovering = False
        self._traveled_dist.x = self._traveled_dist.y = 0

        self.grid.get_grid(self.offset, self._selected_tiles)

    def set_from_path(
        self, file_path: str, area: Optional[Size], offset: Optional[PosPair] = None,
        visible_area: Optional[SizePair] = None
    ) -> None:
        """
        Sets the grid area and tiles.

        Args:
           file path (if it's empty it creates an empty grid), area (can be None),
           offset (can be None) (default = None), visible_area (can be None) (default = None)
        """

        self.offset.x = self.offset.y = 0

        if area:
            self.grid.set_area(area)
        if offset:
            self.offset.x, self.offset.y = offset
        if visible_area:
            self.grid.visible_area.w, self.grid.visible_area.h = visible_area

        img: Optional[pg.Surface] = get_img(file_path) if file_path else None
        self.grid.set_tiles(img, self.offset, self._selected_tiles)

    def _move_with_keys(self, keys: list[int], mouse_tile: Point, brush_size: int) -> None:
        """
        Moves the mouse tile with arrows.

        Args:
            keys, mouse tile, brush size
        """

        value: int = 1
        if pg.key.get_mods() & pg.KMOD_ALT:
            value = brush_size
        if pg.key.get_mods() & pg.KMOD_SHIFT:
            value = max(self.grid.visible_area.w, self.grid.visible_area.h)

        local_mouse_tile: Point = mouse_tile
        if pg.K_LEFT in keys:
            local_mouse_tile.x, self.offset.x = _decrease_mouse_tile(
                local_mouse_tile.x, value, self.offset.x
            )
        if pg.K_RIGHT in keys:
            local_mouse_tile.x, self.offset.x = _increase_mouse_tile(
                local_mouse_tile.x, value, self.offset.x,
                self.grid.visible_area.w, self.grid.area.w
            )
        if pg.K_UP in keys:
            local_mouse_tile.y, self.offset.y = _decrease_mouse_tile(
                local_mouse_tile.y, value, self.offset.y
            )
        if pg.K_DOWN in keys:
            local_mouse_tile.y, self.offset.y = _increase_mouse_tile(
                local_mouse_tile.y, value, self.offset.y,
                self.grid.visible_area.h, self.grid.area.h
            )
        self.grid.set_section_indicator(self.offset)

        relative_mouse_x: int = round(
            (local_mouse_tile.x * self.grid.grid_tile_dim) + (self.grid.grid_tile_dim / 2.0)
        )
        relative_mouse_y: int = round(
            (local_mouse_tile.y * self.grid.grid_tile_dim) + (self.grid.grid_tile_dim / 2.0)
        )
        pg.mouse.set_pos(
            (self.grid.grid_rect.x + relative_mouse_x, self.grid.grid_rect.y + relative_mouse_y)
        )

    def _get_tile_info(
            self, mouse_info: MouseInfo, keys: list[int], brush_size: int
    ) -> tuple[Point, Point]:
        """
        Calculates previous and current mouse tile and handles arrow movement.

        Args:
            mouse info, keys, brush size
        Returns:
            previous mouse tile and mouse tile
        """

        prev_mouse_tile: Point = Point(
            int((self._prev_mouse_x - self.grid.grid_rect.x) / self.grid.grid_tile_dim),
            int((self._prev_mouse_y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)
        )
        mouse_tile: Point = Point(
            int((mouse_info.x - self.grid.grid_rect.x) / self.grid.grid_tile_dim),
            int((mouse_info.y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)
        )

        prev_offset_x: int = self.offset.x
        prev_offset_y: int = self.offset.y

        if any(key in keys for key in (pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN)):
            self._move_with_keys(keys, mouse_tile, brush_size)  # Changes the offset

        # Mouse is in the center of the tile
        prev_mouse_tile.x += prev_offset_x - (brush_size // 2)
        prev_mouse_tile.y += prev_offset_y - (brush_size // 2)
        mouse_tile.x += self.offset.x - (brush_size // 2)
        mouse_tile.y += self.offset.y - (brush_size // 2)

        return prev_mouse_tile, mouse_tile

    def _brush(
            self, start: Point, end: Point, is_drawing: bool, brush_size: int,
            extra_info: dict[str, Any]
    ) -> list[PosPair]:
        """
        Handles brush tool.

        Args:
            start, end, drawing bool, brush size, extra info
        Returns:
            changed tiles
        """

        changed_tiles: list[PosPair] = []

        local_area: Size = self.grid.area
        self._selected_tiles.append(Point(end.x * 2, end.y * 2))
        if extra_info["mirror_x"]:
            self._selected_tiles.extend(
                Point(((local_area.w - brush_size) * 2) - tile.x, tile.y)
                for tile in self._selected_tiles.copy()
            )
        if extra_info["mirror_y"]:
            self._selected_tiles.extend(
                Point(tile.x, ((local_area.h - brush_size) * 2) - tile.y)
                for tile in self._selected_tiles.copy()
            )

        if not is_drawing:
            return changed_tiles

        x_1: int = max(min(start.x, local_area.w - 1), -brush_size + 1)
        y_1: int = max(min(start.y, local_area.h - 1), -brush_size + 1)
        x_2: int = max(min(end.x, local_area.w - 1), -brush_size + 1)
        y_2: int = max(min(end.y, local_area.h - 1), -brush_size + 1)
        changed_tiles.extend(_get_tiles_in_line(x_1, y_1, x_2, y_2))

        if extra_info["mirror_x"]:
            changed_tiles.extend(
                (local_area.w - brush_size - x, y) for x, y in changed_tiles.copy()
            )
        if extra_info["mirror_y"]:
            changed_tiles.extend(
                (x, local_area.h - brush_size - y) for x, y in changed_tiles.copy()
            )

        # Resizes the tiles to the brush size
        return [
            (x, y)
            for original_x, original_y in changed_tiles
            for x in range(max(original_x, 0), min(original_x + brush_size, local_area.w))
            for y in range(max(original_y, 0), min(original_y + brush_size, local_area.h))
        ]

    def _draw_on_grid(
            self, tiles: list[PosPair], color: Color, prev_selected_tiles: list[Point]
    ) -> None:
        """
        Draws tiles on the grid.

        Args:
            tiles, color, previous selected tiles
        """

        prev_tiles: NDArray[np.uint8] = np.copy(self.grid.tiles)

        unique_tiles: tuple[PosPair, ...] = tuple(set(tiles))
        for x, y in unique_tiles:
            self.grid.tiles[y, x] = color

        if not np.array_equal(self.grid.tiles, prev_tiles):
            self.grid.update_section(self.offset, self._selected_tiles, unique_tiles)
        elif self._selected_tiles != prev_selected_tiles:
            self.grid.get_grid(self.offset, self._selected_tiles)

    def _handle_draw(
            self, mouse_info: MouseInfo, keys: list[int], color: Color, brush_size: int,
            tool_info: ToolInfo
    ) -> None:
        """
        Handles grid drawing.

        Args:
            mouse info, keys, color, brush size, tool info
        """

        # Absolute coordinates
        prev_mouse_tile: Point
        mouse_tile: Point
        prev_mouse_tile, mouse_tile = self._get_tile_info(mouse_info, keys, brush_size)

        if self.grid.transparent_tile_img.get_width() != brush_size * 2:
            self.grid.transparent_tile_img = pg.transform.scale(
                self.grid.transparent_tile_img, (brush_size * 2, brush_size * 2)
            )
            self.grid.get_grid(self.offset, self._selected_tiles)

        prev_selected_tiles: list[Point] = self._selected_tiles.copy()
        self._selected_tiles.clear()

        is_coloring: bool = mouse_info.pressed[0] or pg.K_RETURN in keys
        is_drawing: bool = is_coloring or (mouse_info.pressed[2] or pg.K_BACKSPACE in keys)

        changed_tiles: list[PosPair] = []
        extra_tool_info: dict[str, Any] = tool_info[1]
        match tool_info[0]:
            case "brush":
                changed_tiles = self._brush(
                    prev_mouse_tile, mouse_tile, is_drawing, brush_size, extra_tool_info
                )

        rgba_color: Color = color + (255,) if is_coloring else (0, 0, 0, 0)
        self._draw_on_grid(changed_tiles, rgba_color, prev_selected_tiles)

    def _move(self, mouse_info: MouseInfo) -> None:
        """
        Allows changing the section of the grid that is drawn.

        Args:
            mouse info
        """

        tiles_traveled: int

        self._traveled_dist.x += self._prev_mouse_x - mouse_info.x
        if abs(self._traveled_dist.x) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_dist.x / self.grid.grid_tile_dim)
            self._traveled_dist.x -= int(tiles_traveled * self.grid.grid_tile_dim)

            max_offset_x: int = self.grid.area.w - self.grid.visible_area.w
            self.offset.x = max(min(self.offset.x + tiles_traveled, max_offset_x), 0)
            self.grid.set_section_indicator(self.offset)
            self.grid.get_grid(self.offset, self._selected_tiles)

        self._traveled_dist.y += self._prev_mouse_y - mouse_info.y
        if abs(self._traveled_dist.y) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_dist.y / self.grid.grid_tile_dim)
            self._traveled_dist.y -= int(tiles_traveled * self.grid.grid_tile_dim)

            max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
            self.offset.y = max(min(self.offset.y + tiles_traveled, max_offset_y), 0)
            self.grid.set_section_indicator(self.offset)
            self.grid.get_grid(self.offset, self._selected_tiles)

    def set_area(self, area: Optional[Size]) -> None:
        """
        Sets the grid area.

        Args:
            area (can be None)
        """

        if not area:
            return

        self._traveled_dist.x = self._traveled_dist.y = 0

        self.grid.set_area(area)
        self.offset.x = min(self.offset.x, self.grid.area.w - self.grid.visible_area.w)
        self.offset.y = min(self.offset.y, self.grid.area.h - self.grid.visible_area.h)

        self.grid.update_full(self.offset, self._selected_tiles)

    def zoom(self, amount: int, brush_size: int, reach_limit: list[bool]) -> None:
        """
        Zooms in/out.

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

        uncapped_offset_x: int = self.offset.x + prev_mouse_tile_x - mouse_tile_x
        self.offset.x = max(min(uncapped_offset_x, self.grid.area.w - self.grid.visible_area.w), 0)
        uncapped_offset_y: int = self.offset.y + prev_mouse_tile_y - mouse_tile_y
        self.offset.y = max(min(uncapped_offset_y, self.grid.area.h - self.grid.visible_area.h), 0)

        mouse_tile_x -= brush_size // 2
        mouse_tile_y -= brush_size // 2
        for tile in self._selected_tiles:
            tile.x, tile.y = mouse_tile_x * 2, mouse_tile_y * 2

        self.grid.get_grid(self.offset, self._selected_tiles)
        self.grid.set_section_indicator(self.offset)

    def save_to_file(self, file_path: str) -> str:
        """
        Saves the tiles to a file.

        Args:
            file path
        Returns:
            file path (empty if couldn't save)
        """

        file_exit_code: int = check_file_access(Path(file_path), True)
        if file_exit_code != ACCESS_SUCCESS:
            print("Couldn't save.", end=" ")
            if file_exit_code == ACCESS_DENIED:
                print("Permission denied.")
            if file_exit_code == ACCESS_LOCKED:
                print("File locked.")

            return ""

        # Swaps columns and rows
        tiles: NDArray[np.uint8] = np.transpose(self.grid.tiles, (1, 0, 2))
        surf: pg.Surface = pg.surfarray.make_surface(tiles[:, :, :3]).convert_alpha()
        pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(surf)
        pixels_alpha[:, :] = tiles[:, :, 3]

        pg.image.save(surf, file_path)

        return file_path

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int], color: Color,
            brush_size: int, tool_info: ToolInfo
    ) -> None:
        """
        Allows drawing, moving and zooming.

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

        if self.grid in (hovered_obj, self._prev_hovered_obj):  # 1 extra frame to draw
            self._handle_draw(mouse_info, keys, color, brush_size, tool_info)
        elif self._selected_tiles:
            self._selected_tiles.clear()
            self.grid.get_grid(self.offset, self._selected_tiles)

        if mouse_info.pressed[1]:
            self._move(mouse_info)
        else:
            self._traveled_dist.x = self._traveled_dist.y = 0

        if (pg.key.get_mods() & pg.KMOD_CTRL) and pg.K_r in keys:
            self.offset.x = self.offset.y = 0
            self._traveled_dist.x = self._traveled_dist.y = 0
            self.grid.reset(self._selected_tiles)

        self._prev_mouse_x, self._prev_mouse_y = mouse_info.x, mouse_info.y
        self._prev_hovered_obj = hovered_obj
