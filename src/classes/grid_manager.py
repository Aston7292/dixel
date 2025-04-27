"""
Paintable pixel grid with a minimap.

Grid and minimap are refreshed automatically when offset or visible area changes.
"""

from tkinter import messagebox
from pathlib import Path
from typing import TypeAlias, Final, Optional, Any

import pygame as pg
from pygame.locals import *
import numpy as np
from numpy.typing import NDArray
import cv2

from src.utils import (
    Point, RectPos, Size, ObjInfo, Mouse, Keyboard, get_pixels, try_create_dir, resize_obj
)
from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import XY, WH, RGBAColor, HexColor, ToolInfo, LayeredBlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT, EMPTY_TILE_ARR, TILE_H, TILE_W,
    GRID_TRANSITION_START, GRID_TRANSITION_END, NUM_MAX_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY, BG_LAYER
)


BlitSequence: TypeAlias = list[tuple[pg.Surface, XY]]
BucketStack: TypeAlias = list[tuple[np.uint16, tuple[np.uint16, np.uint16]]]

GRID_INIT_VISIBLE_DIM: Final[int] = 32
GRID_DIM_CAP: Final[int] = 600
MINIMAP_DIM_CAP: Final[int] = 256
TRANSPARENT_GRAY: Final[RGBAColor] = (150, 150, 150, 150)


def _dec_mouse_tile(rel_mouse_coord: int, step: int, offset: int, is_ctrl_on: bool) -> XY:
    """
    Decreases a coordinate of the mouse tile.

    Args:
        relative mouse coordinate, movement step, offset, control mode flag
    Returns:
        relative mouse coordinate, offset
    """

    if is_ctrl_on:
        return 0, 0

    rel_mouse_coord -= step
    did_exit_visible_area: bool = rel_mouse_coord < 0
    if did_exit_visible_area:
        extra_offset: int = rel_mouse_coord
        offset = max(offset + extra_offset, 0)
        rel_mouse_coord = 0

    return rel_mouse_coord, offset


def _inc_mouse_tile(
        rel_mouse_coord: int, step: int, offset: int, visible_side: int, side: int,
        is_ctrl_on: bool
) -> XY:
    """
    Increases a coordinate of the mouse tile.

    Args:
        relative mouse coordinate, movement step, offset, side of visible area, side of area,
        control mode flag
    Returns:
        relative mouse coordinate, offset
    """

    if is_ctrl_on:
        return visible_side - 1, side - visible_side

    rel_mouse_coord += step
    did_exit_visible_area: bool = rel_mouse_coord > visible_side - 1
    if did_exit_visible_area:
        extra_offset: int = rel_mouse_coord - visible_side + 1
        offset = min(offset + extra_offset, side - visible_side)
        rel_mouse_coord = visible_side - 1

    return rel_mouse_coord, offset


def _get_tiles_in_line(x_1: int, y_1: int, x_2: int, y_2: int) -> list[XY]:
    """
    Gets the tiles that touch a line using Bresenham's Line Algorithm.

    Args:
        line start x, line start y, line end x, line end y
    Returns:
        tiles
    """

    delta_x: int
    delta_y: int
    step_x: int
    step_y: int

    tiles: list[XY] = []

    delta_x, delta_y = abs(x_2 - x_1), abs(y_2 - y_1)
    step_x, step_y = 1 if x_1 < x_2 else -1, 1 if y_1 < y_2 else -1
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
        "_grid_init_pos", "area", "visible_area", "grid_tile_dim", "grid_rect", "tiles",
        "brush_dim", "_minimap_init_pos", "_minimap_rect", "_small_minimap_img",
        "offset", "selected_tiles", "layer", "blit_sequence", "_win_w_ratio", "_win_h_ratio"
    )

    cursor_type: int = SYSTEM_CURSOR_CROSSHAIR

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the grid and minimap.

        Args:
            grid position, minimap position
        """

        # Tiles dimensions are floats to represent the full size more accurately when resizing

        self._win_w_ratio: float
        self._win_h_ratio: float

        self._grid_init_pos: RectPos = grid_pos

        self.area: Size = Size(64, 64)
        self.visible_area: Size = Size(GRID_INIT_VISIBLE_DIM, GRID_INIT_VISIBLE_DIM)
        self.grid_tile_dim: float = GRID_DIM_CAP / GRID_INIT_VISIBLE_DIM

        grid_img: pg.Surface = pg.Surface((GRID_DIM_CAP, GRID_DIM_CAP)).convert()
        self.grid_rect: pg.Rect = pg.Rect(0, 0, *grid_img.get_size())
        grid_init_xy: XY = (self._grid_init_pos.x, self._grid_init_pos.y)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, grid_init_xy)

        self.tiles: NDArray[np.uint8] = np.zeros((self.area.w, self.area.h, 4), np.uint8)
        self.brush_dim: int = 1

        self._minimap_init_pos: RectPos = minimap_pos

        minimap_img: pg.Surface = pg.Surface((MINIMAP_DIM_CAP, MINIMAP_DIM_CAP)).convert()
        self._minimap_rect: pg.Rect = pg.Rect(0, 0, *minimap_img.get_size())
        minimap_init_xy: XY = (self._minimap_init_pos.x, self._minimap_init_pos.y)
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, minimap_init_xy)

        # Better for scaling
        self._small_minimap_img: pg.Surface = pg.Surface(
            (self.tiles.shape[0], self.tiles.shape[1])
        )

        self.offset: Point = Point(0, 0)
        self.selected_tiles: NDArray[np.bool_] = np.zeros((self.area.w, self.area.h), np.bool_)

        self.layer: int = BG_LAYER
        self.blit_sequence: list[LayeredBlitInfo] = [
            (grid_img, self.grid_rect, self.layer), (minimap_img, self._minimap_rect, self.layer)
        ]
        self._win_w_ratio = self._win_h_ratio = 1

    def get_hovering(self, mouse_xy: XY) -> bool:
        """
        Gets the hovering flag.

        Args:
            mouse xy
        Returns:
            hovering flag
        """

        return self.grid_rect.collidepoint(mouse_xy)

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self.selected_tiles.fill(False)
        self.refresh_grid_img()

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio

        self.refresh_grid_img()
        self._refresh_minimap_rect()
        self.refresh_minimap_img()

    def set_info(
            self, area: Size, visible_w: int, visible_h: int, offset_x: int, offset_y: int
    ) -> None:
        """
        Sets the offset, area, visible area and not the tiles dimension.

        Something that gets the minimap and grid should be called later.

        Args:
            area, visible columns, visible rows, x offset, y offset
        """

        self.area = area
        self.visible_area.w = min(visible_w, self.area.w)
        self.visible_area.h = min(visible_h, self.area.h)
        self.offset.x = min(offset_x, self.area.w - self.visible_area.w)
        self.offset.y = min(offset_y, self.area.h - self.visible_area.h)

        extra_w: int = self.area.w - self.tiles.shape[0]
        if extra_w < 0:
            self.tiles = self.tiles[:self.area.w, ...]
        elif extra_w > 0:
            self.tiles = np.pad(
                self.tiles, ((0, extra_w), (0, 0), (0, 0)), constant_values=0
            )

        extra_h: int = self.area.h - self.tiles.shape[1]
        if extra_h < 0:
            self.tiles = self.tiles[:, :self.area.h, ...]
        elif extra_h > 0:
            self.tiles = np.pad(
                self.tiles, ((0, 0), (0, extra_h), (0, 0)), constant_values=0
            )

        self.selected_tiles: NDArray[np.bool_] = np.zeros((self.area.w, self.area.h), np.bool_)

    def _resize_grid(self, small_img: pg.Surface) -> None:
        """
        Resizes the grid.

        Args:
            small grid image
        """

        xy: XY
        w: int
        h: int
        init_w: float
        init_h: float
        img: pg.Surface

        init_tile_dim: float = GRID_DIM_CAP / max(self.visible_area.w, self.visible_area.h)
        init_w, init_h = self.visible_area.w * init_tile_dim, self.visible_area.h * init_tile_dim

        xy, (w, h) = resize_obj(
            self._grid_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )
        self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)
        self.grid_tile_dim = max(self.grid_tile_dim, 1e-4)

        max_visible_dim: int = max(self.visible_area.w, self.visible_area.h)
        if max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(small_img, (w, h))
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(small_img, (w, h))
        else:
            # Gradual transition
            img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(small_img)
            img_arr = cv2.resize(img_arr, (h, w), interpolation=cv2.INTER_AREA).astype(np.uint8)
            img = pg.surfarray.make_surface(img_arr)

        self.grid_rect.size = (w, h)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, xy)

        self.blit_sequence[0] = (img.convert(), self.grid_rect, self.layer)

    def refresh_grid_img(self) -> None:
        """Refreshes the grid image from the minimap."""

        selected_tiles_xs: NDArray[np.intp]
        selected_tiles_ys: NDArray[np.intp]

        rect: pg.Rect = pg.Rect(
            self.offset.x * TILE_W, self.offset.y * TILE_H,
            self.visible_area.w * TILE_W, self.visible_area.h * TILE_H
        )
        visible_selected_tiles: NDArray[np.bool_] = self.selected_tiles[
            self.offset.x:self.offset.x + self.visible_area.w,
            self.offset.y:self.offset.y + self.visible_area.h
        ]

        selected_tiles_xs, selected_tiles_ys = np.nonzero(visible_selected_tiles)
        selected_tiles_xs *= TILE_W
        selected_tiles_ys *= TILE_H

        # Having a version where 1 tile = 1 pixel is better for scaling
        img: pg.Surface = self._small_minimap_img.subsurface(rect)
        if selected_tiles_xs.size > 14_000:
            # On small amounts it's faster to not copy and restore after resize
            img = img.copy()
        small_img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(img)

        # For every position get all indexes of the NUM_TILE_COLSxNUM_TILE_ROWS slice as a 1D array
        repeated_cols: NDArray[np.uint8] = np.repeat(np.arange(TILE_W), TILE_H)
        tiled_rows: NDArray[np.uint8] = np.tile(np.arange(TILE_H), TILE_W)

        target_xs: NDArray[np.intp] = (
            selected_tiles_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]
        ).ravel()
        target_ys: NDArray[np.intp] = (
            selected_tiles_ys[:, np.newaxis] + tiled_rows[np.newaxis, :]
        ).ravel()

        a: int = 128
        color_range: NDArray[np.uint16] = np.arange(256, dtype=np.uint16)
        # Lookup table for every blend combination with gray (150, 150, 150)
        blend_lut: NDArray[np.uint8] = ((150 * a + color_range * (255 - a)) >> 8).astype(np.uint8)

        target_pixels: NDArray[np.uint8] = small_img_arr[target_xs, target_ys]
        small_img_arr[target_xs, target_ys] = blend_lut[target_pixels]
        self._resize_grid(img)
        if selected_tiles_xs.size <= 14_000:
            small_img_arr[target_xs, target_ys] = target_pixels

    def _refresh_minimap_rect(self) -> None:
        """Refreshes the minimap rect."""

        init_tile_dim: float = MINIMAP_DIM_CAP / max(self.area.w, self.area.h)
        init_w, init_h = self.area.w * init_tile_dim, self.area.h * init_tile_dim

        xy, wh = resize_obj(
            self._minimap_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )
        self._minimap_rect.size = wh
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, xy)

    def _resize_minimap(self) -> None:
        """Resizes the minimap."""

        img: pg.Surface

        max_visible_dim: int = max(self.area.w, self.area.h)
        if max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(self._small_minimap_img, self._minimap_rect.size)
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(self._small_minimap_img, self._minimap_rect.size)
        else:
            # Gradual transition
            img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(self._small_minimap_img)
            img_arr = cv2.resize(
                img_arr, (self._minimap_rect.h, self._minimap_rect.w), interpolation=cv2.INTER_AREA
            ).astype(np.uint8)
            img = pg.surfarray.make_surface(img_arr)

        self.blit_sequence[1] = (img.convert(), self._minimap_rect, self.layer)

    def refresh_minimap_img(self) -> None:
        """Refreshes the minimap image scaled to the minimap rect."""

        # Having a version where 1 tile = 1 pixel is better for scaling
        img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(self._small_minimap_img)

        offset_x: int = self.offset.x * TILE_W
        offset_y: int = self.offset.y * TILE_H
        visible_w: int = self.visible_area.w * TILE_W
        visible_h: int = self.visible_area.h * TILE_H

        src_top_pixels: int = 128
        color_range: NDArray[np.uint16] = np.arange(256, dtype=np.uint16)
        # Lookup table for every blend combination with gray (150, 150, 150)
        blend_lut: NDArray[np.uint8] = ((150 * src_top_pixels + color_range * (255 - src_top_pixels)) >> 8).astype(np.uint8)

        top_x_sl: slice = slice(offset_x, offset_x + visible_w)
        top_y_sl: slice = slice(offset_y, offset_y + TILE_H)
        target_top_pixels: NDArray[np.uint8] = img_arr[top_x_sl, top_y_sl]

        right_x_sl: slice = slice(offset_x + visible_w - TILE_W, offset_x + visible_w)
        right_y_sl: slice = slice(offset_y, offset_y + visible_h)
        target_right_pixels: NDArray[np.uint8] = img_arr[right_x_sl, right_y_sl]

        bottom_x_sl: slice = top_x_sl
        bottom_y_sl: slice = slice(offset_y + visible_h - TILE_H, offset_y + visible_h)
        target_bottom_pixels: NDArray[np.uint8] = img_arr[bottom_x_sl, bottom_y_sl]

        left_x_sl: slice = slice(offset_x, offset_x + TILE_W)
        left_y_sl: slice = right_y_sl
        target_left_pixels: NDArray[np.uint8] = img_arr[left_x_sl, left_y_sl]

        src_top_pixels: NDArray[np.uint8] = target_top_pixels.copy()
        src_right_pixels: NDArray[np.uint8] = target_right_pixels.copy()
        src_bottom_pixels: NDArray[np.uint8] = target_bottom_pixels.copy()
        src_left_pixels: NDArray[np.uint8] = target_left_pixels.copy()

        target_top_pixels[...] = blend_lut[target_top_pixels]
        target_right_pixels[...] = blend_lut[target_right_pixels]
        target_bottom_pixels[...] = blend_lut[target_bottom_pixels]
        target_left_pixels[...] = blend_lut[target_left_pixels]

        self._resize_minimap()
        # Indicator is small, resetting changed pixels is faster than copy
        target_top_pixels[...] = src_top_pixels
        target_right_pixels[...] = src_right_pixels
        target_bottom_pixels[...] = src_bottom_pixels
        target_left_pixels[...] = src_left_pixels

    def refresh_full(self) -> None:
        """Refreshes all the tiles on the minimap and retrieves the grid."""

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles: NDArray[np.uint8] = self.tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_tiles: NDArray[np.uint8] = np.tile(EMPTY_TILE_ARR, (self.area.w, self.area.h, 1))
        empty_tiles_mask: NDArray[np.bool_] = (tiles[..., 3] == 0)[..., np.newaxis]

        tiles = np.where(empty_tiles_mask, empty_tiles, tiles[..., :3])
        self._small_minimap_img = pg.surfarray.make_surface(tiles)

        self.refresh_grid_img()
        self._refresh_minimap_rect()
        self.refresh_minimap_img()

    def _refresh_section_coloring(self, rgba_color: RGBAColor) -> None:
        """
        Refreshes the changed tiles after coloring.

        Args:
            rgba color
        """

        img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(self._small_minimap_img)

        selected_tiles_xs, selected_tiles_ys = np.nonzero(self.selected_tiles)
        selected_tiles_xs *= TILE_W
        selected_tiles_ys *= TILE_H

        # For every position get all indexes of the NUM_TILE_COLSxNUM_TILE_ROWS slice as a 1D array
        repeated_cols: NDArray[np.uint8] = np.repeat(np.arange(TILE_W), TILE_H)
        tiled_rows: NDArray[np.uint8] = np.tile(np.arange(TILE_H), TILE_W)

        target_xs: NDArray[np.intp] = (
            selected_tiles_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]
        ).ravel()
        target_ys: NDArray[np.intp] = (
            selected_tiles_ys[:, np.newaxis] + tiled_rows[np.newaxis, :]
        ).ravel()

        img_arr[target_xs, target_ys] = rgba_color[:3]

    def _refresh_section_erasing(self) -> None:
        """Refreshes the changed tiles after erasing."""

        img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(self._small_minimap_img)

        selected_tiles_xs, selected_tiles_ys = np.nonzero(self.selected_tiles)
        selected_tiles_xs *= TILE_W
        selected_tiles_ys *= TILE_H

        # For every position get all indexes of the NUM_TILE_COLSxNUM_TILE_ROWS slice as a 1D array
        repeated_cols: NDArray[np.uint8] = np.repeat(np.arange(TILE_W), TILE_H)
        tiled_rows: NDArray[np.uint8] = np.tile(np.arange(TILE_H), TILE_W)

        target_xs: NDArray[np.intp] = (
            selected_tiles_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]
        ).ravel()
        target_ys: NDArray[np.intp] = (
            selected_tiles_ys[:, np.newaxis] + tiled_rows[np.newaxis, :]
        ).ravel()

        img_arr[target_xs, target_ys] = EMPTY_TILE_ARR[target_xs % TILE_W, target_ys % TILE_H]

    def upt_section(self, is_coloring: bool, is_erasing: bool, hex_color: str) -> bool:
        """
        Updates the changed tiles.

        Args:
            coloring flag, erasing flag, hex color
        Returns:
            changed flag
        """

        if not (is_coloring or is_erasing):
            return False

        prev_tiles: NDArray[np.uint8] = self.tiles[self.selected_tiles].copy()
        rgba_color: RGBAColor = (*bytes.fromhex(hex_color), 255) if is_coloring else (0, 0, 0, 0)
        self.tiles[self.selected_tiles] = rgba_color
        did_change: bool = not np.array_equal(self.tiles[self.selected_tiles], prev_tiles)  # TODO: improve
        if did_change:
            if is_coloring:
                self._refresh_section_coloring(rgba_color)
            else:
                self._refresh_section_erasing()

        return did_change

    def set_tiles(self, img: Optional[pg.Surface]) -> None:
        """
        Sets the grid tiles using an image pixels.

        Args:
            image (if None it creates an empty grid)
        """

        if img is None:
            self.tiles = np.zeros((self.area.w, self.area.h, 4), np.uint8)
        else:
            self.tiles = get_pixels(img)

            extra_w: int = self.area.w - self.tiles.shape[0]
            if extra_w < 0:
                self.tiles = self.tiles[:self.area.w, ...]
            elif extra_w > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, extra_w), (0, 0), (0, 0)), constant_values=0
                )

            extra_h: int = self.area.h - self.tiles.shape[1]
            if extra_h < 0:
                self.tiles = self.tiles[:, :self.area.h, ...]
            elif extra_h > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, 0), (0, extra_h), (0, 0)), constant_values=0
                )

        self.refresh_full()

    def move_with_keys(self, keyboard: Keyboard, rel_mouse_col: int, rel_mouse_row: int) -> XY:
        """
        Moves the mouse tile with arrows.

        Args:
            keyboard, relative mouse column, relative mouse row
        Returns:
            relative mouse column, relative mouse row
        """

        prev_rel_mouse_col: int
        prev_rel_mouse_row: int
        direction: int

        prev_rel_mouse_col, prev_rel_mouse_row = rel_mouse_col, rel_mouse_row

        step: int = 1
        if keyboard.is_alt_on:
            step = self.brush_dim
        if keyboard.is_shift_on:
            step = max(self.visible_area.w, self.visible_area.h)

        if K_LEFT in keyboard.timed:
            rel_mouse_col, self.offset.x = _dec_mouse_tile(
                rel_mouse_col, step, self.offset.x, keyboard.is_ctrl_on
            )
        if K_RIGHT in keyboard.timed:
            rel_mouse_col, self.offset.x = _inc_mouse_tile(
                rel_mouse_col, step, self.offset.x, self.visible_area.w, self.area.w,
                keyboard.is_ctrl_on
            )
        if K_UP in keyboard.timed:
            rel_mouse_row, self.offset.y = _dec_mouse_tile(
                rel_mouse_row, step, self.offset.y, keyboard.is_ctrl_on
            )
        if K_DOWN in keyboard.timed:
            rel_mouse_row, self.offset.y = _inc_mouse_tile(
                rel_mouse_row, step, self.offset.y, self.visible_area.h, self.area.h,
                keyboard.is_ctrl_on
            )

        did_col_change: bool = rel_mouse_col != prev_rel_mouse_col
        did_row_change: bool = rel_mouse_row != prev_rel_mouse_row
        if did_col_change or did_row_change:
            # Mouse is in the center of the tile
            rel_mouse_x: int = round(rel_mouse_col * self.grid_tile_dim + self.grid_tile_dim // 2)
            rel_mouse_y: int = round(rel_mouse_row * self.grid_tile_dim + self.grid_tile_dim // 2)

            if did_col_change:
                prev_rel_mouse_x: int = round(rel_mouse_col * self.grid_tile_dim)
                if rel_mouse_x == prev_rel_mouse_x:  # Grid is so large that mouse x stays the same
                    direction = 1 if rel_mouse_col > prev_rel_mouse_col else -1
                    rel_mouse_x = min(max(rel_mouse_x + direction, 0), self.grid_rect.w - 1)
            if did_row_change:
                prev_rel_mouse_y: int = round(rel_mouse_row * self.grid_tile_dim)
                if rel_mouse_y == prev_rel_mouse_y:  # Grid is so large that mouse y stays the same
                    direction = 1 if rel_mouse_row > prev_rel_mouse_row else -1
                    rel_mouse_y = min(max(rel_mouse_y + direction, 0), self.grid_rect.h - 1)

            pg.mouse.set_pos(self.grid_rect.x + rel_mouse_x, self.grid_rect.y + rel_mouse_y)

        return rel_mouse_col, rel_mouse_row

    def _dec_largest_side(self, amount: int) -> None:
        """
        Decreases the largest side of the visible area.

        Args:
            amount
        """

        if self.visible_area.w > self.visible_area.h:
            self.visible_area.w = max(self.visible_area.w - amount, 1)
            self.visible_area.h = min(self.visible_area.h, self.visible_area.w)
        else:
            self.visible_area.h = max(self.visible_area.h - amount, 1)
            self.visible_area.w = min(self.visible_area.w, self.visible_area.h)

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
            self.visible_area.h = max(self.visible_area.h, min(self.visible_area.w, self.area.h))
        else:
            self.visible_area.h = min(self.visible_area.h - amount, self.area.h)
            self.visible_area.w = max(self.visible_area.w, min(self.visible_area.h, self.area.w))

    def _zoom_visible_area(
            self, amount: int, should_reach_min_limit: bool, should_reach_max_limit: bool
    ) -> None:
        """
        Zooms the visible area.

        Something that gets the minimap and grid should be called later.

        Args:
            amount, reach minimum limit flag, reach maximum limit flag
        """

        # amount: wheel down (-), wheel up (+)

        if should_reach_min_limit:
            self.visible_area.w = self.visible_area.h = 1
        elif should_reach_max_limit:
            self.visible_area.w, self.visible_area.h = self.area.w, self.area.h
        elif self.visible_area.w == self.visible_area.h:
            self.visible_area.w = min(max(self.visible_area.w - amount, 1), self.area.w)
            self.visible_area.h = min(max(self.visible_area.h - amount, 1), self.area.h)
        elif amount > 0:
            self._dec_largest_side(amount)
        elif amount < 0:
            self._inc_smallest_side(amount)

    def zoom(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Zooms in/out.

        Args:
            mouse, keyboard
        """

        uncapped_amount: int

        amount: int = mouse.scroll_amount
        should_reach_min_limit: bool = False
        should_reach_max_limit: bool = False

        if keyboard.is_ctrl_on:
            # Amount depends on zoom level
            if K_PLUS in keyboard.timed:
                uncapped_amount = round(15 / self.grid_tile_dim)
                amount = min(max(uncapped_amount, 1), 100)
                should_reach_min_limit = keyboard.is_shift_on
            if K_MINUS in keyboard.timed:
                uncapped_amount = round(25 / self.grid_tile_dim)
                amount = -min(max(uncapped_amount, 1), 100)
                should_reach_max_limit = keyboard.is_shift_on

        if amount != 0:
            prev_mouse_col: int = int((mouse.x - self.grid_rect.x) / self.grid_tile_dim)
            prev_mouse_row: int = int((mouse.y - self.grid_rect.y) / self.grid_tile_dim)

            self._zoom_visible_area(amount, should_reach_min_limit, should_reach_max_limit)
            init_tile_dim: float = GRID_DIM_CAP / max(self.visible_area.w, self.visible_area.h)
            self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)
            self.grid_tile_dim = max(self.grid_tile_dim, 1e-4)

            mouse_col: int = int((mouse.x - self.grid_rect.x) / self.grid_tile_dim)
            mouse_row: int = int((mouse.y - self.grid_rect.y) / self.grid_tile_dim)

            uncapped_offset_x: int = self.offset.x + prev_mouse_col - mouse_col
            self.offset.x = min(max(uncapped_offset_x, 0), self.area.w - self.visible_area.w)
            uncapped_offset_y: int = self.offset.y + prev_mouse_row - mouse_row
            self.offset.y = min(max(uncapped_offset_y, 0), self.area.h - self.visible_area.h)

    def try_save_to_file(self, file_str: str, should_ask_create_dir: bool) -> Optional[pg.Surface]:
        """
        Saves the tiles to a file.

        Args:
            file string, ask dir creation flag
        Returns:
            image (can be None)
        """

        if file_str == "":
            return None

        img: pg.Surface = pg.Surface((self.area.w, self.area.h), SRCALPHA)
        img.lock()
        pg.surfarray.blit_array(img, self.tiles[..., :3])
        pg.surfarray.pixels_alpha(img)[...] = self.tiles[..., 3]
        img.unlock()

        file_path: Path = Path(file_str)
        did_succeed: bool = False
        num_dir_creation_attempts: int = 0
        num_system_attempts: int = 0
        while True:
            try:
                # If you open in write mode it will empty the file even if it's locked
                with file_path.open("ab") as f:
                    try_lock_file(f, False)
                    f.truncate(0)
                    pg.image.save(img, f, file_path.name)
                did_succeed = True
                break
            except FileNotFoundError:
                num_dir_creation_attempts += 1
                did_fail: bool = try_create_dir(
                    file_path.parent, should_ask_create_dir, num_dir_creation_attempts
                )
                if did_fail:
                    break
            except PermissionError:
                messagebox.showerror("Image Save Failed", f"{file_path.name}\nPermission denied.")
                break
            except LockException:
                messagebox.showerror("Image Save Failed", f"{file_path.name}\nFile locked.")
                break
            except FileException as e:
                messagebox.showerror("Image Save Failed", f"{file_path.name}\n{e.error_str}")
                break
            except pg.error as e:
                messagebox.showerror("Image Save Failed", f"{file_path.name}\n{e}")
                break
            except OSError as e:
                num_system_attempts += 1
                if num_system_attempts == NUM_MAX_FILE_ATTEMPTS:
                    messagebox.showerror("Image Save Failed", f"{file_path.name}\n{e}")
                    break

                pg.time.wait(FILE_ATTEMPT_DELAY * num_system_attempts)

        return img if did_succeed else None


class GridManager:
    """Class to create and edit a grid of pixels."""

    __slots__ = (
        "_prev_mouse_x", "_prev_mouse_y", "_prev_hovered_obj", "_can_leave", "_prev_mouse_col",
        "_prev_mouse_row", "_mouse_col", "_mouse_row", "_traveled_x", "_traveled_y", "grid",
        "blit_sequence", "objs_info"
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
        self._can_leave: bool = True

        self._prev_mouse_col: int = 0
        self._prev_mouse_row: int = 0
        self._mouse_col: int = 0
        self._mouse_row: int = 0
        self._traveled_x: float = 0
        self._traveled_y: float = 0

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self.blit_sequence: list[LayeredBlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid)]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()
        self._prev_hovered_obj = None
        self._can_leave = True
        self._traveled_x = self._traveled_y = 0

    def _handle_tile_info(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Calculates previous and current mouse tile and handles arrow movement.

        Args:
            mouse, keyboard
        """

        grid_x: int = self.grid.grid_rect.x
        grid_y: int = self.grid.grid_rect.y
        prev_rel_mouse_col: int = int((self._prev_mouse_x - grid_x) / self.grid.grid_tile_dim)
        prev_rel_mouse_row: int = int((self._prev_mouse_y - grid_y) / self.grid.grid_tile_dim)
        rel_mouse_col: int = int((mouse.x - grid_x) / self.grid.grid_tile_dim)
        rel_mouse_row: int = int((mouse.y - grid_y) / self.grid.grid_tile_dim)

        # By setting prev_mouse_tile before changing offset you can draw a line with shift/ctrl
        self._prev_mouse_col = prev_rel_mouse_col + self.grid.offset.x
        self._prev_mouse_row = prev_rel_mouse_row + self.grid.offset.y

        if keyboard.timed != []:
            # Changes the offset
            rel_mouse_col, rel_mouse_row = self.grid.move_with_keys(
                keyboard, rel_mouse_col, rel_mouse_row
            )

        self._mouse_col = rel_mouse_col + self.grid.offset.x
        self._mouse_row = rel_mouse_row + self.grid.offset.y

    def _brush(self, extra_info: dict[str, Any]) -> None:
        """
        Handles brush tool.

        Args:
            drawing flag, extra info (mirrors)
        """

        w_edge: int = self.grid.area.w - 1
        h_edge: int = self.grid.area.h - 1

        brush_dim: int = self.grid.brush_dim
        # Center tiles to cursor
        y_1: int = min(max(self._prev_mouse_row, 0), h_edge) - brush_dim // 2
        x_1: int = min(max(self._prev_mouse_col, 0), w_edge) - brush_dim // 2
        x_2: int = min(max(self._mouse_col, 0), w_edge) - brush_dim // 2
        y_2: int = min(max(self._mouse_row, 0), h_edge) - brush_dim // 2
        selected_tiles_list: list[XY] = _get_tiles_in_line(x_1, y_1, x_2, y_2)

        selected_tiles_list = [
            (x, y)
            for original_x, original_y in selected_tiles_list
            for x in range(max(original_x, 0), min(original_x + brush_dim, self.grid.area.w))
            for y in range(max(original_y, 0), min(original_y + brush_dim, self.grid.area.h))
        ]

        if extra_info["mirror_x"]:
            selected_tiles_list.extend([(w_edge - x, y) for x, y in selected_tiles_list])
        if extra_info["mirror_y"]:
            selected_tiles_list.extend([(x, h_edge - y) for x, y in selected_tiles_list])
        self.grid.selected_tiles[*zip(*selected_tiles_list)] = True

    def _init_bucket_stack(self, x: int, y: int, mask: NDArray[np.bool_]) -> BucketStack:
        """
        Initializes the stack for the bucket tool flood fill.

        Args:
            x, y, tiles mask
        Returns:
            stack
        """

        up_tiles: NDArray[np.bool_] = mask[x, :y + 1]
        up_stop: int | np.intp = up_tiles[::-1].argmin()
        if up_stop == 0:
            up_stop = up_tiles.size
        first_y: int | np.intp = y - up_stop + 1

        down_tiles: NDArray[np.bool_] = mask[x, y:]
        down_stop: int | np.intp = down_tiles.argmin()
        if down_stop == 0:
            down_stop = down_tiles.size
        last_y: int | np.intp = y + down_stop - 1

        return [(np.uint16(x), (np.uint16(first_y), np.uint16(last_y)))]

    def _bucket(self, extra_info: dict[str, Any]) -> None:
        """
        Handles brush tool using the scan-line algorithm.

        Args:
            extra info (color fill)
        """

        x: np.uint16
        first_y: np.uint16
        last_y: np.uint16

        seed_x: int = self._mouse_col
        seed_y: int = self._mouse_row
        w: int = self.grid.area.w
        h: int = self.grid.area.h
        if seed_x < 0 or seed_x >= w or seed_y < 0 or seed_y >= h:
            return

        color: NDArray[np.uint8] = self.grid.tiles[seed_x, seed_y]
        selected_tiles: NDArray[np.bool_] = self.grid.selected_tiles

        tiles_view: NDArray[np.uint32] = self.grid.tiles.view(np.uint32)[..., 0]
        color_view: NDArray[np.uint32] = color.view(np.uint32)[0]
        mask: NDArray[np.bool_] = tiles_view == color_view
        if extra_info["color_fill"]:
            selected_tiles[mask] = True
            return

        # Padded to avoid boundary checks
        visitable_tiles: NDArray[np.bool_] = np.ones((w + 2, h), np.bool_)
        visitable_tiles[0] = visitable_tiles[-1] = False

        right_shifted_col_mask: NDArray[np.bool_] = np.empty(h, np.bool_)
        right_shifted_col_mask[0] = False
        left_shifted_col_mask: NDArray[np.bool_] = np.empty(h, np.bool_)
        left_shifted_col_mask[-1] = False
        indexes: NDArray[np.uint16] = np.arange(0, h, dtype=np.uint16)

        stack: BucketStack = self._init_bucket_stack(seed_x, seed_y, mask)
        while stack != []:
            x, (first_y, last_y) = stack.pop()
            selected_tiles[x, first_y:last_y + 1] = True
            visitable_tiles[x + 1, first_y:last_y + 1] = False

            if visitable_tiles[x, first_y] or visitable_tiles[x, last_y]:
                prev_col_temp_mask: NDArray[np.bool_] = mask[x - 1] & visitable_tiles[x]

                # Starts of True sequences
                right_shifted_col_mask[1:] = mask[x - 1, :-1]
                prev_col_starts_mask: NDArray[np.bool_] = prev_col_temp_mask & ~right_shifted_col_mask
                # Ends of True sequences
                left_shifted_col_mask[:-1] = mask[x - 1, 1:]
                prev_col_ends_mask: NDArray[np.bool_] = prev_col_temp_mask & ~left_shifted_col_mask

                prev_col_spans: list[tuple[np.uint16, np.uint16]] = [
                    (start, end)
                    for start, end in zip(indexes[prev_col_starts_mask], indexes[prev_col_ends_mask])
                    if start <= last_y and first_y <= end
                ]
                if prev_col_spans != []:
                    stack.extend(zip([x - 1] * len(prev_col_spans), prev_col_spans))
            if visitable_tiles[x + 2, first_y] or visitable_tiles[x + 2, last_y]:
                next_col_temp_mask: NDArray[np.bool_] = mask[x + 1] & visitable_tiles[x + 2]

                # Starts of True sequences
                right_shifted_col_mask[1:] = mask[x + 1, :-1]
                next_col_starts_mask: NDArray[np.bool_] = next_col_temp_mask & ~right_shifted_col_mask
                # Ends of True sequences
                left_shifted_col_mask[:-1] = mask[x + 1, 1:]
                next_col_ends_mask: NDArray[np.bool_] = next_col_temp_mask & ~left_shifted_col_mask

                next_col_spans: list[tuple[np.uint16, np.uint16]] = [
                    (start, end)
                    for start, end in zip(indexes[next_col_starts_mask], indexes[next_col_ends_mask])
                    if start <= last_y and first_y <= end
                ]
                if next_col_spans != []:
                    stack.extend(zip([x + 1] * len(next_col_spans), next_col_spans))

    def _handle_draw(
            self, mouse: Mouse, keyboard: Keyboard, hex_color: HexColor, tool_info: ToolInfo
    ) -> tuple[bool, bool]:
        """
        Handles grid drawing.

        Args:
            mouse, keyboard, hexadecimal color, tool info
        Returns:
            grid changed flag, selected tiles changed flag
        """

        tool_name: str
        extra_tool_info: dict[str, Any]

        self._handle_tile_info(mouse, keyboard)

        prev_selected_tiles_bytes: bytes = np.packbits(self.grid.selected_tiles).tobytes()
        self.grid.selected_tiles.fill(False)
        tool_name, extra_tool_info = tool_info
        if tool_name == "brush":
            self._brush(extra_tool_info)
        elif tool_name == "bucket":
            self._bucket(extra_tool_info)

        is_coloring: bool = mouse.pressed[MOUSE_LEFT] or K_RETURN in keyboard.pressed
        is_erasing: bool = mouse.pressed[MOUSE_RIGHT] or K_BACKSPACE in keyboard.pressed
        selected_tiles_bytes: bytes = np.packbits(self.grid.selected_tiles).tobytes()
        did_grid_change: bool = self.grid.upt_section(is_coloring, is_erasing, hex_color)

        # Comparing bytes in this situation is faster
        return did_grid_change, selected_tiles_bytes != prev_selected_tiles_bytes

    def _move(self, mouse: Mouse) -> None:
        """
        Moves the section of the grid that is drawn, it's faster when moving the mouse faster.

        Args:
            mouse
        """

        tiles_traveled: int

        x_speed: float = abs(self._prev_mouse_x - mouse.x) ** 1.25
        if mouse.x > self._prev_mouse_x:
            x_speed = -x_speed
        self._traveled_x += x_speed

        y_speed: float = abs(self._prev_mouse_y - mouse.y) ** 1.25
        if mouse.y > self._prev_mouse_y:
            y_speed = -y_speed
        self._traveled_y += y_speed

        if abs(self._traveled_x) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_x / self.grid.grid_tile_dim)
            self._traveled_x -= tiles_traveled * self.grid.grid_tile_dim

            uncapped_offset_x: int = self.grid.offset.x + int(tiles_traveled)
            max_offset_x: int = self.grid.area.w - self.grid.visible_area.w
            self.grid.offset.x = min(max(uncapped_offset_x, 0), max_offset_x)

        if abs(self._traveled_y) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_y / self.grid.grid_tile_dim)
            self._traveled_y -= tiles_traveled * self.grid.grid_tile_dim

            uncapped_offset_y: int = self.grid.offset.y + tiles_traveled
            max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
            self.grid.offset.y = min(max(uncapped_offset_y, 0), max_offset_y)

    def upt(
            self, mouse: Mouse, keyboard: Keyboard, hex_color: HexColor, tool_info: ToolInfo
    ) -> bool:
        """
        Allows drawing, moving and zooming.

        Args:
            mouse, keyboard, hexadecimal color, tool info
        Returns:
            grid changed flag
        """

        grid: Grid = self.grid
        prev_visible_w: int = grid.visible_area.w
        prev_visible_h: int = grid.visible_area.h
        prev_offset_x: int = grid.offset.x
        prev_offset_y: int = grid.offset.y

        if mouse.pressed[MOUSE_WHEEL]:
            self._move(mouse)
        else:
            self._traveled_x = self._traveled_y = 0

        did_grid_change: bool = False
        did_selected_tiles_change: bool = False
        if grid == mouse.hovered_obj or grid == self._prev_hovered_obj:  # Extra frame to draw
            did_grid_change, did_selected_tiles_change = self._handle_draw(
                mouse, keyboard, hex_color, tool_info
            )
            self._can_leave = True
        elif self._can_leave:
            grid.leave()
            self._can_leave = False

        if grid == mouse.hovered_obj and (mouse.scroll_amount != 0 or keyboard.timed != []):
            grid.zoom(mouse, keyboard)

        if keyboard.is_ctrl_on and K_r in keyboard.pressed:
            grid.visible_area.w = min(GRID_INIT_VISIBLE_DIM, grid.area.w)
            grid.visible_area.h = min(GRID_INIT_VISIBLE_DIM, grid.area.h)
            grid.offset.x = grid.offset.y = 0
            self._traveled_x = self._traveled_y = 0

        did_visible_area_change: bool = (
            grid.visible_area.w != prev_visible_w and grid.visible_area.h != prev_visible_h
        )
        did_offset_change: bool = grid.offset.x != prev_offset_x or grid.offset.y != prev_offset_y
        if did_grid_change or did_visible_area_change or did_offset_change:
            grid.refresh_grid_img()
            grid.refresh_minimap_img()
        elif did_selected_tiles_change:
            grid.refresh_grid_img()

        self._prev_mouse_x, self._prev_mouse_y = mouse.x, mouse.y
        self._prev_hovered_obj = mouse.hovered_obj

        return did_grid_change
