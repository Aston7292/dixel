"""Paintable pixel grid with a minimap."""

from typing import Optional, Any

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.utils import Point, RectPos, Size, Ratio, ObjInfo, Mouse, Keyboard, get_pixels, resize_obj
from src.file_utils import get_img_state
from src.type_utils import PosPair, SizePair, Color, ToolInfo, BlitSequence, LayeredBlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT, WHITE, EMPTY_TILE_ARR, NUM_TILE_ROWS, NUM_TILE_COLS,
    BG_LAYER, IMG_STATE_OK, IMG_STATE_DENIED, IMG_STATE_LOCKED
)


def _dec_mouse_tile(
        rel_mouse_coord: int, value: int, offset: int, is_ctrl_on: bool
) -> tuple[int, int]:
    """
    Decreases a coordinate of the mouse tile.

    Args:
        relative mouse coordinate, movement value, offset, control flag
    Returns:
        relative mouse coordinate, offset
    """

    copy_rel_mouse_coord: int = rel_mouse_coord
    copy_offset: int = offset
    if is_ctrl_on:
        copy_rel_mouse_coord = copy_offset = 0
    else:
        copy_rel_mouse_coord -= value
        has_exited_visible_area: bool = copy_rel_mouse_coord < 0
        if has_exited_visible_area:
            extra_offset: int = copy_rel_mouse_coord
            copy_offset = max(copy_offset + extra_offset, 0)
            copy_rel_mouse_coord = 0

    return copy_rel_mouse_coord, copy_offset


def _inc_mouse_tile(
        rel_mouse_coord: int, value: int, offset: int, visible_side: int, side: int,
        is_ctrl_on: bool
) -> tuple[int, int]:
    """
    Increases a coordinate of the mouse tile.

    Args:
        relative mouse coordinate, movement value, offset, side of visible area, side of area,
        control flag
    Returns:
        relative mouse coordinate, offset
    """

    copy_rel_mouse_coord: int = rel_mouse_coord
    copy_offset: int = offset
    if is_ctrl_on:
        copy_rel_mouse_coord = visible_side - 1
        copy_offset = side - visible_side
    else:
        copy_rel_mouse_coord += value
        has_exited_visible_area: bool = copy_rel_mouse_coord >= visible_side
        if has_exited_visible_area:
            extra_offset: int = copy_rel_mouse_coord + 1 - visible_side
            copy_offset = min(copy_offset + extra_offset, side - visible_side)
            copy_rel_mouse_coord = visible_side - 1

    return copy_rel_mouse_coord, copy_offset


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
        "_grid_img", "grid_rect", "_grid_size_cap", "tiles", "transparent_tile_img",
        "_minimap_init_pos", "_minimap_img", "_minimap_rect", "_minimap_size_cap",
        "offset", "selected_tiles", "_win_ratio", "_no_indicator_small_minimap_img",
        "_layer", "cursor_type"
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

        self._grid_size_cap: Size = Size(
            round(self.visible_area.w * self.grid_tile_dim),
            round(self.visible_area.h * self.grid_tile_dim)
        )

        self.tiles: NDArray[np.uint8] = np.empty((0, 0, 4), np.uint8)
        transparent_gray: Color = [120, 120, 120, 125]
        transparent_tile_wh: SizePair = (NUM_TILE_COLS, NUM_TILE_ROWS)
        self.transparent_tile_img: pg.Surface = pg.Surface(transparent_tile_wh, pg.SRCALPHA)
        self.transparent_tile_img.fill(transparent_gray)

        self._minimap_init_pos: RectPos = minimap_pos

        self._minimap_img: pg.Surface
        self._minimap_rect: pg.Rect
        # Having a version where 1 tile = 1 pixel is better for scaling, used for update section
        self._no_indicator_small_minimap_img: pg.Surface

        self._minimap_size_cap: Size = Size(256, 256)

        self.offset: Point = Point(0, 0)
        self.selected_tiles: list[PosPair] = []
        self._win_ratio: Ratio = Ratio(1, 1)

        self._layer: int = BG_LAYER
        self.cursor_type: int = pg.SYSTEM_CURSOR_CROSSHAIR

    def get_blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

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
            mouse xy
        Returns:
            hovered flag, hovered object layer
        """

        return self.grid_rect.collidepoint(mouse_xy), self._layer

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

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

        cap_w: int = self._grid_size_cap.w
        cap_h: int = self._grid_size_cap.h
        init_tile_dim: float = min(cap_w / self.visible_area.w, cap_h / self.visible_area.h)
        init_w: float = self.visible_area.w * init_tile_dim
        init_h: float = self.visible_area.h * init_tile_dim
        self.grid_tile_dim = init_tile_dim * min(self._win_ratio.wh)

        xy: PosPair
        wh: SizePair
        xy, wh = resize_obj(self._grid_init_pos, init_w, init_h, self._win_ratio, True)
        self._grid_img = pg.transform.scale(small_grid_img, wh)
        self.grid_rect = self._grid_img.get_rect(**{self._grid_init_pos.coord_type: xy})

    def get_grid(self) -> None:
        """Gets the grid image from the minimap."""

        # Having a version where 1 tile = 1 pixel is better for scaling
        ptr_small_minimap_img: pg.Surface = self._no_indicator_small_minimap_img

        small_rect: pg.Rect = pg.Rect(
            self.offset.x * NUM_TILE_COLS, self.offset.y * NUM_TILE_ROWS,
            self.visible_area.w * NUM_TILE_COLS, self.visible_area.h * NUM_TILE_ROWS
        )
        small_img: pg.Surface = ptr_small_minimap_img.subsurface(small_rect).copy()

        selected_tiles: list[PosPair] = self.selected_tiles
        scaled_selected_tiles: list[PosPair] = [
            (tile_x * NUM_TILE_COLS, tile_y * NUM_TILE_ROWS) for tile_x, tile_y in selected_tiles
        ]
        tile_wh: SizePair = self.transparent_tile_img.get_size()
        visible_selected_tiles: list[PosPair] = [
            tile for tile in scaled_selected_tiles if small_rect.colliderect((tile, tile_wh))
        ]

        scaled_offset_x: int = self.offset.x * NUM_TILE_COLS
        scaled_offset_y: int = self.offset.y * NUM_TILE_ROWS
        blit_sequence: BlitSequence = [
            (self.transparent_tile_img, (tile_x - scaled_offset_x, tile_y - scaled_offset_y))
            for tile_x, tile_y in visible_selected_tiles
        ]
        small_img.fblits(blit_sequence)
        self._resize_grid(small_img)

    def _get_minimap_rect(self) -> None:
        """Gets the minimap rect."""

        cap_w: int = self._minimap_size_cap.w
        cap_h: int = self._minimap_size_cap.h
        init_tile_dim: float = min(cap_w / self.area.w, cap_h / self.area.h)
        init_w: float = self.area.w * init_tile_dim
        init_h: float = self.area.h * init_tile_dim

        xy: PosPair
        wh: SizePair
        xy, wh = resize_obj(self._minimap_init_pos, init_w, init_h, self._win_ratio, True)
        self._minimap_rect = pg.Rect(0, 0, *wh)
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, xy)

    def get_minimap_img(self) -> None:
        """Gets the minimap image scaled from the minimap rect."""

        # Having a version where 1 tile = 1 pixel is better for scaling
        small_img: pg.Surface = self._no_indicator_small_minimap_img.copy()

        visible_area_rect: pg.Rect = pg.Rect(
            self.offset.x * NUM_TILE_COLS, self.offset.y * NUM_TILE_ROWS,
            self.visible_area.w * NUM_TILE_COLS, self.visible_area.h * NUM_TILE_ROWS
        )
        pg.draw.rect(small_img, WHITE, visible_area_rect, 2)

        self._minimap_img = pg.transform.scale(small_img, self._minimap_rect.size)

    def refresh_full(self) -> None:
        """Refreshes all the tiles on the minimap and retrieves the grid."""

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles: NDArray[np.uint8] = np.repeat(
            np.repeat(self.tiles, NUM_TILE_ROWS, 0), NUM_TILE_COLS, 1
        )
        empty_tiles_mask: NDArray[np.bool_] = tiles[..., 3:4] == 0
        tiles = tiles[..., :3]

        empty_tiles: NDArray[np.uint8] = np.tile(EMPTY_TILE_ARR, (self.area.h, self.area.w, 1))
        # Swaps columns and rows, because pygame uses it like this
        tiles = np.where(empty_tiles_mask, empty_tiles, tiles).transpose((1, 0, 2))
        self._no_indicator_small_minimap_img = pg.surfarray.make_surface(tiles)

        self.get_grid()
        self._get_minimap_rect()
        self.get_minimap_img()

    def refresh_section(self, changed_tiles: tuple[PosPair, ...]) -> None:
        """
        Refreshes specific tiles on the minimap and retrieves the grid.

        Args:
            changed tiles
        """

        ptr_tiles: NDArray[np.uint8] = self.tiles
        # Swaps columns and rows, because pygame uses it like this
        empty_tile_img: pg.Surface = pg.surfarray.make_surface(EMPTY_TILE_ARR.transpose((1, 0, 2)))

        blit_sequence: BlitSequence = []
        tile_img: pg.Surface = pg.Surface((NUM_TILE_COLS, NUM_TILE_ROWS))
        for x, y in changed_tiles:
            tile_xy: PosPair = (x * NUM_TILE_COLS, y * NUM_TILE_ROWS)
            if ptr_tiles[y, x, 3]:
                tile_img.fill(ptr_tiles[y, x])
                blit_sequence.append((tile_img.copy(), tile_xy))
            else:
                blit_sequence.append((empty_tile_img, tile_xy))
        self._no_indicator_small_minimap_img.fblits(blit_sequence)

        self.get_grid()
        self.get_minimap_img()

    def set_tiles(self, img: Optional[pg.Surface]) -> None:
        """
        Sets the grid tiles using an image pixels.

        Args:
            image (if None it creates an empty grid)
        """

        if not img:
            self.tiles = np.zeros((self.area.h, self.area.w, 4), np.uint8)
        else:
            self.tiles = get_pixels(img)

            pad_width: tuple[SizePair, SizePair, SizePair]
            num_extra_rows: int = self.area.h - self.tiles.shape[0]
            if num_extra_rows < 0:
                self.tiles = self.tiles[:self.area.h, ...]
            elif num_extra_rows > 0:
                pad_width = ((0, num_extra_rows), (0, 0), (0, 0))
                self.tiles = np.pad(self.tiles, pad_width, constant_values=0)

            num_extra_cols: int = self.area.w - self.tiles.shape[1]
            if num_extra_cols < 0:
                self.tiles = self.tiles[:, :self.area.w, ...]
            elif num_extra_cols > 0:
                pad_width = ((0, 0), (0, num_extra_cols), (0, 0))
                self.tiles = np.pad(self.tiles, pad_width, constant_values=0)

        self.refresh_full()

    def set_area(self, area: Size) -> None:
        """
        Sets the grid area and not the tiles dimension.

        Something that gets the minimap and grid should be called later.

        Args:
            area
        """

        self.area = area
        pad_width: tuple[SizePair, SizePair, SizePair]

        num_extra_rows: int = self.area.h - self.tiles.shape[0]
        if num_extra_rows < 0:
            self.tiles = self.tiles[:self.area.h, ...]
        elif num_extra_rows > 0:
            pad_width = ((0, num_extra_rows), (0, 0), (0, 0))
            self.tiles = np.pad(self.tiles, pad_width, constant_values=0)

        num_extra_cols: int = self.area.w - self.tiles.shape[1]
        if num_extra_cols < 0:
            self.tiles = self.tiles[:, :self.area.w, ...]
        elif num_extra_cols > 0:
            pad_width = ((0, 0), (0, num_extra_cols), (0, 0))
            self.tiles = np.pad(self.tiles, pad_width, constant_values=0)

    def _dec_largest_side(self, amount: int) -> None:
        """
        Decreases the largest side of the visible area.

        Args:
            amount
        """

        if self.visible_area.w > self.visible_area.h:
            self.visible_area.w = max(self.visible_area.w - amount, 1)
            self.visible_area.h = min(self.visible_area.wh)
        else:
            self.visible_area.h = max(self.visible_area.h - amount, 1)
            self.visible_area.w = min(self.visible_area.wh)

    def _inc_smallest_side(self, amount: int) -> None:
        """
        Increases the smallest side of the visible area.

        Args:
            amount
        """

        is_visible_w_smaller: bool = self.visible_area.w < self.visible_area.h
        can_increase_visible_w: bool = self.visible_area.w != self.area.w
        is_visible_h_capped: bool = self.visible_area.h == self.area.h
        if (is_visible_w_smaller or is_visible_h_capped) and can_increase_visible_w:
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
            self.visible_area.wh = (1, 1)
        elif should_reach_limit[1]:
            self.visible_area.wh = self.area.wh
        elif self.visible_area.w == self.visible_area.h:
            self.visible_area.w = max(min(self.visible_area.w - amount, self.area.w), 1)
            self.visible_area.h = max(min(self.visible_area.h - amount, self.area.h), 1)
        elif amount > 0:
            self._dec_largest_side(amount)
        else:
            self._inc_smallest_side(amount)

        cap_w: int = self._grid_size_cap.w
        cap_h: int = self._grid_size_cap.h
        grid_init_tile_dim: float = min(cap_w / self.visible_area.w, cap_h / self.visible_area.h)
        self.grid_tile_dim = grid_init_tile_dim * min(self._win_ratio.wh)

    def reset(self) -> None:
        """Resets the offset and the visible_are."""

        self.offset.xy = (0, 0)
        self.visible_area.w = min(self._init_visible_area.w, self.area.w)
        self.visible_area.h = min(self._init_visible_area.h, self.area.h)

        self.get_grid()
        self.get_minimap_img()


class GridManager:
    """Class to create and edit a grid of pixels."""

    __slots__ = (
        "_prev_mouse_x", "_prev_mouse_y", "_prev_hovered_obj",
        "_prev_mouse_tile", "_mouse_tile", "_traveled_dist", "grid", "objs_info"
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object.

        Args:
            grid position, minimap position
        """

        self._prev_mouse_x: int
        self._prev_mouse_y: int
        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()
        self._prev_hovered_obj: Optional[Grid] = None

        self._prev_mouse_tile: Point = Point(0, 0)
        self._mouse_tile: Point = Point(0, 0)
        self._traveled_dist: Point = Point(0, 0)

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid)]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self._prev_hovered_obj = None
        self._traveled_dist.xy = (0, 0)

    def _move_with_keys(
            self, keyboard: Keyboard, rel_mouse_tile_x: int, rel_mouse_tile_y: int, brush_size: int
    ) -> PosPair:
        """
        Moves the mouse tile with arrows.

        Args:
            keyboard, relative mouse tile x, relative mouse tile y, brush size
        Returns:
            relative mouse tile x, relative mouse tile y
        """

        copy_rel_mouse_tile_x: int = rel_mouse_tile_x
        copy_rel_mouse_tile_y: int = rel_mouse_tile_y

        value: int = 1
        if keyboard.is_alt_on:
            value = brush_size
        if keyboard.is_shift_on:
            value = max(self.grid.visible_area.wh)

        prev_offset_x: int = self.grid.offset.x
        prev_offset_y: int = self.grid.offset.y
        if pg.K_LEFT in keyboard.timed:
            copy_rel_mouse_tile_x, self.grid.offset.x = _dec_mouse_tile(
                copy_rel_mouse_tile_x, value, self.grid.offset.x, keyboard.is_ctrl_on
            )
        if pg.K_RIGHT in keyboard.timed:
            copy_rel_mouse_tile_x, self.grid.offset.x = _inc_mouse_tile(
                copy_rel_mouse_tile_x, value, self.grid.offset.x,
                self.grid.visible_area.w, self.grid.area.w, keyboard.is_ctrl_on
            )
        if pg.K_UP in keyboard.timed:
            copy_rel_mouse_tile_y, self.grid.offset.y = _dec_mouse_tile(
                copy_rel_mouse_tile_y, value, self.grid.offset.y, keyboard.is_ctrl_on
            )
        if pg.K_DOWN in keyboard.timed:
            copy_rel_mouse_tile_y, self.grid.offset.y = _inc_mouse_tile(
                copy_rel_mouse_tile_y, value, self.grid.offset.y,
                self.grid.visible_area.h, self.grid.area.h, keyboard.is_ctrl_on
            )

        has_rel_mouse_tile_x_changed: bool = copy_rel_mouse_tile_x != rel_mouse_tile_x
        has_rel_mouse_tile_y_changed: bool = copy_rel_mouse_tile_y != rel_mouse_tile_y
        if has_rel_mouse_tile_x_changed or has_rel_mouse_tile_y_changed:
            # Mouse is in the center of the tile
            grid_tile_dim: float = self.grid.grid_tile_dim
            ptr_grid_rect: pg.Rect = self.grid.grid_rect
            rel_mouse_x: int = round((copy_rel_mouse_tile_x * grid_tile_dim) + grid_tile_dim / 2)
            rel_mouse_y: int = round((copy_rel_mouse_tile_y * grid_tile_dim) + grid_tile_dim / 2)
            pg.mouse.set_pos((ptr_grid_rect.x + rel_mouse_x, ptr_grid_rect.y + rel_mouse_y))

        if self.grid.offset.x != prev_offset_x or self.grid.offset.y != prev_offset_y:
            self.grid.get_minimap_img()

        return copy_rel_mouse_tile_x, copy_rel_mouse_tile_y

    def _get_tile_info(self, mouse: Mouse, keyboard: Keyboard, brush_size: int) -> None:
        """
        Calculates previous and current mouse tile and handles arrow movement.

        Args:
            mouse, keyboard, brush size
        """

        ptr_grid_rect: pg.Rect = self.grid.grid_rect
        grid_tile_dim: float = self.grid.grid_tile_dim

        prev_rel_mouse_tile_x: int = int((self._prev_mouse_x - ptr_grid_rect.x) / grid_tile_dim)
        prev_rel_mouse_tile_y: int = int((self._prev_mouse_y - ptr_grid_rect.y) / grid_tile_dim)
        rel_mouse_tile_x: int = int((mouse.x - ptr_grid_rect.x) / grid_tile_dim)
        rel_mouse_tile_y: int = int((mouse.y - ptr_grid_rect.y) / grid_tile_dim)

        # By setting prev_mouse_tile before moving you can draw a line when moving with shift/ctrl
        self._prev_mouse_tile.x = prev_rel_mouse_tile_x + self.grid.offset.x - (brush_size // 2)
        self._prev_mouse_tile.y = prev_rel_mouse_tile_y + self.grid.offset.y - (brush_size // 2)
        if keyboard.timed:
            # Changes the offset
            rel_mouse_tile_x, rel_mouse_tile_y = self._move_with_keys(
                keyboard, rel_mouse_tile_x, rel_mouse_tile_y, brush_size
            )

        self._mouse_tile.x = rel_mouse_tile_x + self.grid.offset.x - (brush_size // 2)
        self._mouse_tile.y = rel_mouse_tile_y + self.grid.offset.y - (brush_size // 2)

    def _brush(
            self, is_drawing: bool, brush_size: int, extra_info: dict[str, Any]
    ) -> list[PosPair]:
        """
        Handles brush tool.

        Args:
            drawing flag, brush size, extra info
        Returns:
            changed tiles
        """

        changed_tiles: list[PosPair] = []
        grid_hor_edge: int = self.grid.area.w - brush_size
        grid_ver_edge: int = self.grid.area.h - brush_size

        self.grid.selected_tiles.append(self._mouse_tile.xy)
        if extra_info["mirror_x"]:
            self.grid.selected_tiles.extend([
                (grid_hor_edge - tile_x, tile_y) for tile_x, tile_y in self.grid.selected_tiles
            ])
        if extra_info["mirror_y"]:
            self.grid.selected_tiles.extend([
                (tile_x, grid_ver_edge - tile_y) for tile_x, tile_y in self.grid.selected_tiles
            ])

        if not is_drawing:
            return changed_tiles

        x_1: int = max(min(self._prev_mouse_tile.x, self.grid.area.w - 1), -brush_size + 1)
        y_1: int = max(min(self._prev_mouse_tile.y, self.grid.area.h - 1), -brush_size + 1)
        x_2: int = max(min(self._mouse_tile.x, self.grid.area.w - 1), -brush_size + 1)
        y_2: int = max(min(self._mouse_tile.y, self.grid.area.h - 1), -brush_size + 1)
        changed_tiles.extend(_get_tiles_in_line(x_1, y_1, x_2, y_2))

        if extra_info["mirror_x"]:
            changed_tiles.extend([(grid_hor_edge - x, y) for x, y in changed_tiles])
        if extra_info["mirror_y"]:
            changed_tiles.extend([(x, grid_ver_edge - y) for x, y in changed_tiles])

        scaled_changed_tiles: list[PosPair] = [
            (x, y)
            for original_x, original_y in changed_tiles
            for x in range(max(original_x, 0), min(original_x + brush_size, self.grid.area.w))
            for y in range(max(original_y, 0), min(original_y + brush_size, self.grid.area.h))
        ]

        return scaled_changed_tiles

    def _draw_on_grid(
            self, tiles: list[PosPair], color: Color, prev_selected_tiles: list[PosPair]
    ) -> None:
        """
        Draws tiles on the grid.

        Args:
            tiles, color, previous selected tiles
        """

        unique_tiles: tuple[PosPair, ...] = tuple(set(tiles))

        tuple_color: tuple[int, ...] = tuple(color)
        has_changed: bool = False
        for x, y in unique_tiles:
            if tuple(self.grid.tiles[y, x]) != tuple_color:
                has_changed = True
                self.grid.tiles[y, x] = tuple_color

        if has_changed:
            self.grid.refresh_section(unique_tiles)
        elif self.grid.selected_tiles != prev_selected_tiles:
            self.grid.get_grid()

    def _handle_draw(
            self, mouse: Mouse, keyboard: Keyboard, color: Color, brush_size: int,
            tool_info: ToolInfo
    ) -> None:
        """
        Handles grid drawing.

        Args:
            mouse, keyboard, color, brush size, tool info
        """

        self._get_tile_info(mouse, keyboard, brush_size)
        transparent_tile_wh: SizePair = (brush_size * NUM_TILE_COLS, brush_size * NUM_TILE_ROWS)
        if self.grid.transparent_tile_img.get_size() != transparent_tile_wh:
            self.grid.transparent_tile_img = pg.transform.scale(
                self.grid.transparent_tile_img, transparent_tile_wh
            )
            self.grid.get_grid()

        prev_selected_tiles: list[PosPair] = self.grid.selected_tiles.copy()
        self.grid.selected_tiles.clear()
        is_coloring: bool = mouse.pressed[MOUSE_LEFT] or pg.K_RETURN in keyboard.pressed
        is_erasing: bool = mouse.pressed[MOUSE_RIGHT] or pg.K_BACKSPACE in keyboard.pressed

        changed_tiles: list[PosPair] = []
        tool_name: str
        extra_tool_info: dict[str, Any]
        tool_name, extra_tool_info = tool_info

        if tool_name == "brush":
            changed_tiles = self._brush(is_coloring or is_erasing, brush_size, extra_tool_info)

        rgba_color: Color = color + [255] if is_coloring else [0, 0, 0, 0]
        self._draw_on_grid(changed_tiles, rgba_color, prev_selected_tiles)

    def _move(self, mouse: Mouse) -> None:
        """
        Allows changing the section of the grid that is drawn.

        Args:
            mouse
        """

        tiles_traveled: int

        self._traveled_dist.x += self._prev_mouse_x - mouse.x
        if abs(self._traveled_dist.x) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_dist.x / self.grid.grid_tile_dim)
            self._traveled_dist.x -= int(tiles_traveled * self.grid.grid_tile_dim)

            max_offset_x: int = self.grid.area.w - self.grid.visible_area.w
            self.grid.offset.x = max(min(self.grid.offset.x + tiles_traveled, max_offset_x), 0)
            self.grid.get_grid()
            self.grid.get_minimap_img()

        self._traveled_dist.y += self._prev_mouse_y - mouse.y
        if abs(self._traveled_dist.y) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_dist.y / self.grid.grid_tile_dim)
            self._traveled_dist.y -= int(tiles_traveled * self.grid.grid_tile_dim)

            max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
            self.grid.offset.y = max(min(self.grid.offset.y + tiles_traveled, max_offset_y), 0)
            self.grid.get_grid()
            self.grid.get_minimap_img()

    def set_info(self, offset: Point, area: Size, visible_area: Size) -> None:
        """
        Sets the offset, area, visible area and not the tiles dimension.

        Something that gets the minimap and grid should be called later.

        Args:
            offset, area, visible area (can be None)
        """

        self.grid.visible_area.wh = (min(visible_area.w, area.w), min(visible_area.h, area.h))
        self.grid.set_area(area)
        self.grid.offset.x = min(offset.x, area.w - visible_area.w)
        self.grid.offset.y = min(offset.y, area.h - visible_area.h)

    def _zoom(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Zooms in/out.

        Args:
            mouse, keyboard
        """

        amount: int = mouse.scroll_amount
        should_reach_limit: list[bool] = [False, False]
        if keyboard.is_ctrl_on:
            if pg.K_MINUS in keyboard.timed:
                amount = 1
                should_reach_limit[0] = keyboard.is_shift_on
            if pg.K_PLUS in keyboard.timed:
                amount = -1
                should_reach_limit[1] = keyboard.is_shift_on

        if not (amount or any(should_reach_limit)):
            return

        prev_mouse_tile_x: int = int((mouse.x - self.grid.grid_rect.x) / self.grid.grid_tile_dim)
        prev_mouse_tile_y: int = int((mouse.y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)
        self.grid.zoom(amount, should_reach_limit)

        mouse_tile_x: int = int((mouse.x - self.grid.grid_rect.x) / self.grid.grid_tile_dim)
        mouse_tile_y: int = int((mouse.y - self.grid.grid_rect.y) / self.grid.grid_tile_dim)

        uncapped_offset_x: int = self.grid.offset.x + prev_mouse_tile_x - mouse_tile_x
        max_offset_x: int = self.grid.area.w - self.grid.visible_area.w
        self.grid.offset.x = max(min(uncapped_offset_x, max_offset_x), 0)
        uncapped_offset_y: int = self.grid.offset.y + prev_mouse_tile_y - mouse_tile_y
        max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
        self.grid.offset.y = max(min(uncapped_offset_y, max_offset_y), 0)

        self.grid.get_grid()
        self.grid.get_minimap_img()

    def try_save_to_file(self, file_path: str) -> None:
        """
        Saves the tiles to a file.

        Args:
            file path
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

            return

        # Swaps columns and rows, because pygame uses it like this
        transposed_tiles: NDArray[np.uint8] = np.transpose(self.grid.tiles, (1, 0, 2))
        surf: pg.Surface = pg.surfarray.make_surface(transposed_tiles[..., :3]).convert_alpha()
        pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(surf)
        pixels_alpha[...] = transposed_tiles[..., 3]

        pg.image.save(surf, file_path)

    def upt(
            self, mouse: Mouse, keyboard: Keyboard, color: Color, brush_size: int,
            tool_info: ToolInfo
    ) -> None:
        """
        Allows drawing, moving and zooming.

        Args:
            mouse, keyboard, color, brush size, tool info
        """

        # Extra frame to draw
        if self.grid == mouse.hovered_obj or self.grid == self._prev_hovered_obj:
            self._handle_draw(mouse, keyboard, color, brush_size, tool_info)
        elif self.grid.selected_tiles:
            self.grid.selected_tiles.clear()
            self.grid.get_grid()

        if mouse.pressed[MOUSE_WHEEL]:
            self._move(mouse)
        else:
            self._traveled_dist.xy = (0, 0)

        if self.grid == mouse.hovered_obj and (mouse.scroll_amount or keyboard.timed):
            self._zoom(mouse, keyboard)

        if keyboard.is_ctrl_on and pg.K_r in keyboard.pressed:
            self.grid.reset()
            self._traveled_dist.xy = (0, 0)

        self._prev_mouse_x, self._prev_mouse_y = mouse.xy
        self._prev_hovered_obj = mouse.hovered_obj
