"""Paintable pixel grid with a minimap."""

from typing import Optional, Any

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.utils import Point, RectPos, Size, Ratio, ObjInfo, MouseInfo, get_pixels, resize_obj
from src.file_utils import get_img_state
from src.type_utils import PosPair, SizePair, Color, ToolInfo, BlitSequence, LayeredBlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT, WHITE, EMPTY_TILE_ARR, BG_LAYER,
    IMG_STATE_OK, IMG_STATE_DENIED, IMG_STATE_LOCKED
)


def _decrease_mouse_tile(rel_mouse_coord: int, value: int, offset: int) -> tuple[int, int]:
    """
    Decreases a coordinate of the mouse tile.

    Args:
        relative mouse coordinate, movement value, offset
    Returns:
        relative mouse coordinate, offset
    """

    local_rel_mouse_coord: int = rel_mouse_coord
    local_offset: int = offset
    if pg.key.get_mods() & pg.KMOD_CTRL:
        local_rel_mouse_coord = local_offset = 0
    else:
        local_rel_mouse_coord -= value
        has_exited_visible_area: bool = local_rel_mouse_coord < 0
        if has_exited_visible_area:
            extra_offset: int = local_rel_mouse_coord
            local_offset = max(local_offset + extra_offset, 0)
            local_rel_mouse_coord = 0

    return local_rel_mouse_coord, local_offset


def _increase_mouse_tile(
        rel_mouse_coord: int, value: int, offset: int, visible_side: int, side: int
) -> tuple[int, int]:
    """
    Increases a coordinate of the mouse tile.

    Args:
        relative mouse coordinate, movement value, offset, side of visible area, side of area
    Returns:
        relative mouse coordinate, offset
    """

    local_rel_mouse_coord: int = rel_mouse_coord
    local_offset: int = offset
    if pg.key.get_mods() & pg.KMOD_CTRL:
        local_rel_mouse_coord = visible_side - 1
        local_offset = side - visible_side
    else:
        local_rel_mouse_coord += value
        has_exited_visible_area: bool = local_rel_mouse_coord >= visible_side
        if has_exited_visible_area:
            extra_offset: int = local_rel_mouse_coord + 1 - visible_side
            local_offset = min(local_offset + extra_offset, side - visible_side)
            local_rel_mouse_coord = visible_side - 1

    return local_rel_mouse_coord, local_offset


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
    """Class to create a pixel grid and its minimap."""

    __slots__ = (
        "_grid_init_pos", "area", "_init_visible_area", "visible_area", "grid_tile_dim",
        "_grid_img", "grid_rect", "_grid_init_size", "tiles", "transparent_tile_img",
        "_minimap_init_pos", "_minimap_img", "_minimap_rect", "_minimap_size_cap",
        "offset", "selected_tiles", "_win_ratio", "_no_indicator_small_minimap_img", "_layer"
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

        self.grid_tile_dim: float = 18

        self._grid_img: pg.Surface
        self.grid_rect: pg.Rect

        self._grid_init_size: Size = Size(
            round(self.visible_area.w * self.grid_tile_dim),
            round(self.visible_area.h * self.grid_tile_dim)
        )

        self.tiles: NDArray[np.uint8] = np.empty((self.area.h, self.area.w, 4), np.uint8)
        transparent_grey: Color = (120, 120, 120, 125)
        self.transparent_tile_img: pg.Surface = pg.Surface((2, 2), pg.SRCALPHA)
        self.transparent_tile_img.fill(transparent_grey)

        self._minimap_init_pos: RectPos = minimap_pos

        self._minimap_img: pg.Surface
        self._minimap_rect: pg.Rect

        self._minimap_size_cap: Size = Size(256, 256)

        self.offset: Point = Point(0, 0)
        self.selected_tiles: list[Point] = []
        self._win_ratio: Ratio = Ratio(1, 1)

        # Having a version where 1 tile = 1 pixel is better for scaling
        # Used for update_section
        self._no_indicator_small_minimap_img: pg.Surface

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

    def get_hovering_info(self, mouse_xy: PosPair) -> tuple[bool, int]:
        """
        Gets the hovering info.

        Args:
            mouse position
        Returns:
            True if the object is being hovered else False, hovered object layer
        """

        return self.grid_rect.collidepoint(mouse_xy), self._layer

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self.selected_tiles.clear()
        self.get_grid()

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        self._win_ratio = win_ratio

        self.get_grid()
        self._get_minimap_rect()
        self.get_minimap_img()

    def _resize_grid(self, small_grid_img: pg.Surface) -> None:
        """
        Resizes the grid.

        Args:
            small grid image
        """

        unscaled_grid_tile_dim: float = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        )
        unscaled_grid_wh: tuple[float, float] = (
            self.visible_area.w * unscaled_grid_tile_dim,
            self.visible_area.h * unscaled_grid_tile_dim
        )
        self.grid_tile_dim = unscaled_grid_tile_dim * min(self._win_ratio.w, self._win_ratio.h)

        grid_xy: PosPair
        grid_wh: SizePair
        grid_xy, grid_wh = resize_obj(
            self._grid_init_pos, *unscaled_grid_wh, self._win_ratio, True
        )

        self._grid_img = pg.transform.scale(small_grid_img, grid_wh)
        self.grid_rect = self._grid_img.get_rect(**{self._grid_init_pos.coord_type: grid_xy})

    def get_grid(self) -> None:
        """Gets the grid image from the minimap."""

        small_grid_w: int = self.visible_area.w
        if self.offset.x + small_grid_w > self.area.w:
            small_grid_w -= self.offset.x + small_grid_w - self.area.w
        small_grid_w *= 2

        small_grid_h: int = self.visible_area.h
        if self.offset.y + small_grid_h > self.area.h:
            small_grid_h -= self.offset.y + small_grid_h - self.area.h
        small_grid_h *= 2

        small_grid_rect: pg.Rect = pg.Rect(
            self.offset.x * 2, self.offset.y * 2, small_grid_w, small_grid_h
        )
        # Having a version where 1 tile = 1 pixel is better for scaling
        small_grid_img: pg.Surface = (
            self._no_indicator_small_minimap_img.subsurface(small_grid_rect).copy()
        )

        tile_wh: SizePair = self.transparent_tile_img.get_size()
        visible_selected_tiles: list[Point] = [
            tile
            for tile in self.selected_tiles
            if small_grid_rect.colliderect(((tile.x, tile.y), tile_wh))
        ]

        tile_offset_x: int = self.offset.x * 2
        tile_offset_y: int = self.offset.y * 2
        blit_sequence: BlitSequence = [
            (self.transparent_tile_img, (tile.x - tile_offset_x, tile.y - tile_offset_y))
            for tile in visible_selected_tiles
        ]
        small_grid_img.fblits(blit_sequence)
        self._resize_grid(small_grid_img)

    def _get_minimap_rect(self) -> None:
        """Gets the minimap rect."""

        unscaled_minimap_tile_dim: float = min(
            self._minimap_size_cap.w / self.area.w, self._minimap_size_cap.h / self.area.h
        )
        unscaled_minimap_wh: tuple[float, float] = (
            self.area.w * unscaled_minimap_tile_dim, self.area.h * unscaled_minimap_tile_dim
        )

        minimap_xy: PosPair
        minimap_wh: SizePair
        minimap_xy, minimap_wh = resize_obj(
            self._minimap_init_pos, *unscaled_minimap_wh, self._win_ratio, True
        )
        self._minimap_rect = pg.Rect(0, 0, *minimap_wh)
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, minimap_xy)

    def get_minimap_img(self) -> None:
        """Gets the minimap image scaled from the minimap rect."""

        # Having a version where 1 tile = 1 pixel is better for scaling
        small_minimap_img: pg.Surface = self._no_indicator_small_minimap_img.copy()

        visible_area_rect: pg.Rect = pg.Rect(
            self.offset.x * 2, self.offset.y * 2,
            self.visible_area.w * 2, self.visible_area.h * 2
        )
        pg.draw.rect(small_minimap_img, WHITE, visible_area_rect, 2)

        self._minimap_img = pg.transform.scale(small_minimap_img, self._minimap_rect.size)

    def update_full(self) -> None:
        """Updates all the tiles on the minimap and retrieves the grid."""

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles: NDArray[np.uint8] = np.repeat(
            np.repeat(self.tiles, EMPTY_TILE_ARR.shape[0], 0), EMPTY_TILE_ARR.shape[1], 1
        )
        empty_tiles_mask: NDArray[np.bool_] = tiles[..., 3:4] == 0
        tiles = tiles[..., :3]

        empty_tiles: NDArray[np.uint8] = np.tile(EMPTY_TILE_ARR, (self.area.h, self.area.w, 1))
        tiles = np.where(empty_tiles_mask, empty_tiles, tiles)
        self._no_indicator_small_minimap_img = pg.surfarray.make_surface(
            tiles.transpose((1, 0, 2))
        )

        self.get_grid()
        self._get_minimap_rect()
        self.get_minimap_img()

    def update_section(self, changed_tiles: tuple[PosPair, ...]) -> None:
        """
        Updates specific tiles on the minimap and retrieves the grid.

        Args:
            changed tiles
        """

        pointer_tiles: NDArray[np.uint8] = self.tiles
        empty_tile_img: pg.Surface = pg.surfarray.make_surface(EMPTY_TILE_ARR)

        blit_sequence: BlitSequence = []
        tile_img: pg.Surface = pg.Surface((2, 2))
        for x, y in changed_tiles:
            if not pointer_tiles[y, x, 3]:
                blit_sequence.append((empty_tile_img, (x * 2, y * 2)))
            else:
                tile_img.fill(pointer_tiles[y, x])
                blit_sequence.append((tile_img.copy(), (x * 2, y * 2)))
        self._no_indicator_small_minimap_img.fblits(blit_sequence)

        self.get_grid()
        self.get_minimap_img()

    def set_tiles(self, img: Optional[pg.Surface]) -> None:
        """
        Sets the grid tiles using an image pixels.

        Args:
            image (if None it creates an empty grid)
        """

        self.tiles = np.zeros((self.area.h, self.area.w, 4), np.uint8)
        if img:
            self.tiles = get_pixels(img)

            extra_rows: int = self.area.h - self.tiles.shape[0]
            if extra_rows < 0:
                self.tiles = self.tiles[:self.area.h, ...]
            elif extra_rows > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0
                )

            extra_cols: int = self.area.w - self.tiles.shape[1]
            if extra_cols < 0:
                self.tiles = self.tiles[:, :self.area.w, ...]
            elif extra_cols > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0
                )

        self.update_full()

    def set_area(self, area: Size) -> None:
        """
        Sets the grid area and not the tiles dimension.

        Something that gets the minimap and grid should be called later.

        Args:
            area
        """

        self.area = area

        extra_rows: int = self.area.h - self.tiles.shape[0]
        if extra_rows < 0:
            self.tiles = self.tiles[:self.area.h, ...]
        elif extra_rows > 0:
            self.tiles = np.pad(self.tiles, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0)

        extra_cols: int = self.area.w - self.tiles.shape[1]
        if extra_cols < 0:
            self.tiles = self.tiles[:, :self.area.w, ...]
        elif extra_cols > 0:
            self.tiles = np.pad(self.tiles, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0)

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
            self.visible_area.h = max(self.visible_area.h - amount, 1)
            self.visible_area.w = min(self.visible_area.w, self.visible_area.h)

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

    def zoom(self, amount: int, should_reach_limit: list[bool]) -> None:
        """
        Changes and visible area and tiles dimension.

        Something that gets the minimap and grid should be called later.

        Args:
            amount, reach limit flags
        """

        # Amount is positive when zooming in and negative when zooming out

        if should_reach_limit[0]:
            self.visible_area.w = self.visible_area.h = 1
        elif should_reach_limit[1]:
            self.visible_area.w, self.visible_area.h = self.area.w, self.area.h
        elif self.visible_area.w == self.visible_area.h:
            self.visible_area.w = max(min(self.visible_area.w - amount, self.area.w), 1)
            self.visible_area.h = max(min(self.visible_area.h - amount, self.area.h), 1)
        elif amount > 0:
            self._decrease_largest_side(amount)
        else:
            self._increase_smallest_side(amount)

        unscaled_grid_tile_dim: float = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        )
        self.grid_tile_dim = unscaled_grid_tile_dim * min(self._win_ratio.w, self._win_ratio.h)

    def reset(self) -> None:
        """Resets the offset and the visible_are."""

        self.offset.x = self.offset.y = 0
        self.visible_area.w = min(self._init_visible_area.w, self.area.w)
        self.visible_area.h = min(self._init_visible_area.h, self.area.h)

        self.get_grid()
        self.get_minimap_img()


class GridManager:
    """Class to create and edit a grid of pixels."""

    __slots__ = (
        "_is_hovering", "_prev_mouse_x", "_prev_mouse_y", "_prev_hovered_obj", "_traveled_dist",
        "grid", "objs_info"
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object.

        Args:
            grid position, minimap position
        """

        self._is_hovering: bool = False

        self._prev_mouse_x: int
        self._prev_mouse_y: int
        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()
        self._prev_hovered_obj: Optional[Grid] = None

        self._traveled_dist: Point = Point(0, 0)

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid)]

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self._is_hovering = False
        self._traveled_dist.x = self._traveled_dist.y = 0

    def _move_with_keys(self, keys: list[int], rel_mouse_tile: Point, brush_size: int) -> None:
        """
        Moves the mouse tile with arrows.

        Args:
            keys, relative mouse tile, brush size
        """

        value: int = 1
        if pg.key.get_mods() & pg.KMOD_ALT:
            value = brush_size
        if pg.key.get_mods() & pg.KMOD_SHIFT:
            value = max(self.grid.visible_area.w, self.grid.visible_area.h)

        local_rel_mouse_tile: Point = Point(rel_mouse_tile.x, rel_mouse_tile.y)
        prev_mouse_tile_x: int = local_rel_mouse_tile.x
        prev_mouse_tile_y: int = local_rel_mouse_tile.y

        if pg.K_LEFT in keys:
            local_rel_mouse_tile.x, self.grid.offset.x = _decrease_mouse_tile(
                local_rel_mouse_tile.x, value, self.grid.offset.x
            )
        if pg.K_RIGHT in keys:
            local_rel_mouse_tile.x, self.grid.offset.x = _increase_mouse_tile(
                local_rel_mouse_tile.x, value, self.grid.offset.x,
                self.grid.visible_area.w, self.grid.area.w
            )
        if pg.K_UP in keys:
            local_rel_mouse_tile.y, self.grid.offset.y = _decrease_mouse_tile(
                local_rel_mouse_tile.y, value, self.grid.offset.y
            )
        if pg.K_DOWN in keys:
            local_rel_mouse_tile.y, self.grid.offset.y = _increase_mouse_tile(
                local_rel_mouse_tile.y, value, self.grid.offset.y,
                self.grid.visible_area.h, self.grid.area.h
            )

        has_mouse_tile_x_changed: bool = local_rel_mouse_tile.x != prev_mouse_tile_x
        has_mouse_tile_y_changed: bool = local_rel_mouse_tile.y != prev_mouse_tile_y
        if has_mouse_tile_x_changed or has_mouse_tile_y_changed:
            self.grid.get_minimap_img()

            # Mouse is in the center of the tile
            half_tile_dim: float = self.grid.grid_tile_dim / 2
            rel_mouse_x: int = round(
                (local_rel_mouse_tile.x * self.grid.grid_tile_dim) + half_tile_dim
            )
            rel_mouse_y: int = round(
                (local_rel_mouse_tile.y * self.grid.grid_tile_dim) + half_tile_dim
            )
            pg.mouse.set_pos(
                (self.grid.grid_rect.x + rel_mouse_x, self.grid.grid_rect.y + rel_mouse_y)
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

        prev_offset_x: int = self.grid.offset.x
        prev_offset_y: int = self.grid.offset.y

        if keys:
            self._move_with_keys(keys, mouse_tile, brush_size)  # Changes the offset

        prev_mouse_tile.x += prev_offset_x - (brush_size // 2)
        prev_mouse_tile.y += prev_offset_y - (brush_size // 2)
        mouse_tile.x += self.grid.offset.x - (brush_size // 2)
        mouse_tile.y += self.grid.offset.y - (brush_size // 2)

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

        pointer_area: Size = self.grid.area
        self.grid.selected_tiles.append(Point(end.x * 2, end.y * 2))
        if extra_info["mirror_x"]:
            self.grid.selected_tiles.extend(
                Point(((pointer_area.w - brush_size) * 2) - tile.x, tile.y)
                for tile in self.grid.selected_tiles.copy()
            )
        if extra_info["mirror_y"]:
            self.grid.selected_tiles.extend(
                Point(tile.x, ((pointer_area.h - brush_size) * 2) - tile.y)
                for tile in self.grid.selected_tiles.copy()
            )

        if not is_drawing:
            return changed_tiles

        x_1: int = max(min(start.x, pointer_area.w - 1), -brush_size + 1)
        y_1: int = max(min(start.y, pointer_area.h - 1), -brush_size + 1)
        x_2: int = max(min(end.x, pointer_area.w - 1), -brush_size + 1)
        y_2: int = max(min(end.y, pointer_area.h - 1), -brush_size + 1)
        changed_tiles.extend(_get_tiles_in_line(x_1, y_1, x_2, y_2))

        if extra_info["mirror_x"]:
            changed_tiles.extend(
                (pointer_area.w - brush_size - x, y) for x, y in changed_tiles.copy()
            )
        if extra_info["mirror_y"]:
            changed_tiles.extend(
                (x, pointer_area.h - brush_size - y) for x, y in changed_tiles.copy()
            )

        scaled_changed_tiles: list[PosPair] = [
            (x, y)
            for original_x, original_y in changed_tiles
            for x in range(max(original_x, 0), min(original_x + brush_size, pointer_area.w))
            for y in range(max(original_y, 0), min(original_y + brush_size, pointer_area.h))
        ]

        return scaled_changed_tiles

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
            self.grid.update_section(unique_tiles)
        elif self.grid.selected_tiles != prev_selected_tiles:
            self.grid.get_grid()

    def _handle_draw(
            self, mouse_info: MouseInfo, keys: list[int], color: Color, brush_size: int,
            tool_info: ToolInfo
    ) -> None:
        """
        Handles grid drawing.

        Args:
            mouse info, keys, color, brush size, tool info
        """

        prev_mouse_tile: Point
        mouse_tile: Point
        prev_mouse_tile, mouse_tile = self._get_tile_info(mouse_info, keys, brush_size)

        if self.grid.transparent_tile_img.get_width() != brush_size * 2:
            self.grid.transparent_tile_img = pg.transform.scale(
                self.grid.transparent_tile_img, (brush_size * 2, brush_size * 2)
            )
            self.grid.get_grid()

        prev_selected_tiles: list[Point] = self.grid.selected_tiles.copy()
        self.grid.selected_tiles.clear()

        is_coloring: bool = mouse_info.pressed[MOUSE_LEFT] or pg.K_RETURN in keys
        is_drawing: bool = (
            is_coloring or (mouse_info.pressed[MOUSE_RIGHT] or pg.K_BACKSPACE in keys)
        )

        changed_tiles: list[PosPair] = []
        tool_name: str
        extra_tool_info: dict[str, Any]
        tool_name, extra_tool_info = tool_info
        match tool_name:
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
            self.grid.offset.x = max(min(self.grid.offset.x + tiles_traveled, max_offset_x), 0)
            self.grid.get_grid()
            self.grid.get_minimap_img()

        self._traveled_dist.y += self._prev_mouse_y - mouse_info.y
        if abs(self._traveled_dist.y) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_dist.y / self.grid.grid_tile_dim)
            self._traveled_dist.y -= int(tiles_traveled * self.grid.grid_tile_dim)

            max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
            self.grid.offset.y = max(min(self.grid.offset.y + tiles_traveled, max_offset_y), 0)
            self.grid.get_grid()
            self.grid.get_minimap_img()

    def set_info(
        self, offset: Optional[Point], area: Optional[Size], visible_area: Optional[Size]
    ) -> None:
        """
        Sets the grid offset, area. visible area and not the tiles dimension.

        Something that gets the minimap and grid should be called later.

        Args:
            offset (can be None), area (can be None), visible area (can be None)
        """

        if not (offset and area and visible_area):
            return

        self.grid.visible_area.w = min(visible_area.w, area.w)
        self.grid.visible_area.h = min(visible_area.h, area.h)
        self.grid.set_area(area)
        self.grid.offset.x = min(offset.x, area.w - visible_area.w)
        self.grid.offset.y = min(offset.y, area.h - visible_area.h)

        self._traveled_dist.x = self._traveled_dist.y = 0

    def _zoom(self, mouse_info: MouseInfo, keys: list[int], brush_size: int) -> None:
        """
        Zooms in/out.

        Args:
            mouse info, keys, brush size
        """

        amount: int = mouse_info.scroll_amount
        should_reach_limit: list[bool] = [False, False]
        if pg.key.get_mods() & pg.KMOD_CTRL:
            if pg.K_MINUS in keys:
                amount = 1
                should_reach_limit[0] = bool(pg.key.get_mods() & pg.KMOD_SHIFT)
            if pg.K_PLUS in keys:
                amount = -1
                should_reach_limit[1] = bool(pg.key.get_mods() & pg.KMOD_SHIFT)

        mouse_x: int
        mouse_y: int
        mouse_x, mouse_y = pg.mouse.get_pos()

        prev_mouse_tile_x: int = int((mouse_x - self.grid.grid_rect.x) / self.grid.grid_tile_dim)
        prev_mouse_tile_y: int = int((mouse_y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)

        self.grid.zoom(amount, should_reach_limit)

        mouse_tile_x: int = int((mouse_x - self.grid.grid_rect.x) / self.grid.grid_tile_dim)
        mouse_tile_y: int = int((mouse_y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)

        uncapped_offset_x: int = self.grid.offset.x + prev_mouse_tile_x - mouse_tile_x
        max_offset_x: int = self.grid.area.w - self.grid.visible_area.w
        self.grid.offset.x = max(min(uncapped_offset_x, max_offset_x), 0)
        uncapped_offset_y: int = self.grid.offset.y + prev_mouse_tile_y - mouse_tile_y
        max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
        self.grid.offset.y = max(min(uncapped_offset_y, max_offset_y), 0)

        mouse_tile_x -= brush_size // 2
        mouse_tile_y -= brush_size // 2
        for tile in self.grid.selected_tiles:
            tile.x, tile.y = mouse_tile_x * 2, mouse_tile_y * 2

        self.grid.get_grid()
        self.grid.get_minimap_img()

    def save_to_file(self, file_path: str) -> str:
        """
        Saves the tiles to a file.

        Args:
            file path
        Returns:
            file path (empty if couldn't save)
        """

        img_state: int = get_img_state(file_path, True)
        if img_state != IMG_STATE_OK:
            print("Couldn't save.", end=" ")
            if img_state == IMG_STATE_DENIED:
                print("Permission denied.")
            elif img_state == IMG_STATE_LOCKED:
                print("File locked.")
            else:
                print(f"Unknown reason. State: {img_state}.")

            return ""

        # Swaps columns and rows, because pygame uses it like this
        transposed_tiles: NDArray[np.uint8] = np.transpose(self.grid.tiles, (1, 0, 2))
        surf: pg.Surface = pg.surfarray.make_surface(transposed_tiles[..., :3]).convert_alpha()
        pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(surf)
        pixels_alpha[...] = transposed_tiles[..., 3]

        pg.image.save(surf, file_path)

        return file_path

    def _handle_hover(self, hovered_obj: Any) -> None:
        """
        Handles the hovering behavior.

        Args:
            hovered object, mouse info
        """

        if self.grid != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False
        elif not self._is_hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
            self._is_hovering = True

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int], color: Color,
            brush_size: int, tool_info: ToolInfo
    ) -> None:
        """
        Allows drawing, moving and zooming.

        Args:
            hovered object (can be None), mouse info, keys, color, brush size, tool info
        """

        self._handle_hover(hovered_obj, mouse_info)

        if self.grid == hovered_obj or self.grid == self._prev_hovered_obj:  # Extra frame to draw
            self._handle_draw(mouse_info, keys, color, brush_size, tool_info)
        elif self.grid.selected_tiles:
            self.grid.selected_tiles.clear()
            self.grid.get_grid()

        if mouse_info.pressed[MOUSE_WHEEL]:
            self._move(mouse_info)
        else:
            self._traveled_dist.x = self._traveled_dist.y = 0

        if self._is_hovering and (keys or mouse_info.scroll_amount):
            self._zoom(mouse_info, keys, brush_size)

        if (pg.key.get_mods() & pg.KMOD_CTRL) and pg.K_r in keys:
            self._traveled_dist.x = self._traveled_dist.y = 0
            self.grid.reset()

        self._prev_mouse_x, self._prev_mouse_y = mouse_info.x, mouse_info.y
        self._prev_hovered_obj = hovered_obj
