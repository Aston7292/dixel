"""
Paintable pixel grid with a minimap.

Grid and minimap are refreshed automatically when offset or visible area changes.
"""

from tkinter import messagebox
from pathlib import Path
from zlib import compress, decompress
from collections import deque
from collections.abc import Callable
from itertools import islice
from sys import stderr
from io import BytesIO
from typing import Literal, Never, Self, TypeAlias, Final, Any

import pygame as pg
import numpy as np
import cv2
from pygame.locals import *
from numpy import uint8, uint16, uint32, int32, intp, bool_
from numpy.typing import NDArray
from PIL import Image

from src.classes.tools_manager import ToolName, ToolInfo
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE, KEYBOARD

import src.vars as my_vars
from src.utils import get_pixels
from src.obj_utils import UIElement, ObjInfo, resize_obj, rec_move_rect
from src.file_utils import (
    FileError, handle_file_os_error,
    try_write_file, try_replace_file, try_remove_file, try_create_dir
)
from src.lock_utils import LockError, try_lock_file
from src.type_utils import XY, RGBColor, HexColor, BlitInfo, RectPos
from src.consts import (
    BLACK,
    EMPTY_TILE_ARR, TILE_H, TILE_W,
    FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I,
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT,
    BG_LAYER, TEXT_LAYER, TOP_LAYER,
)


_HistorySnapshot: TypeAlias = tuple[int, int, bytes]

_GRID_DIM_CAP: Final[int] = 600
_GRID_TRANSITION_START: Final[int] = 30
_GRID_TRANSITION_END: Final[int]   = 165
_MINIMAP_DIM_CAP: Final[int] = 256
_MINIMAP_TRANSITION_START: Final[int] = 25
_MINIMAP_TRANSITION_END: Final[int]   = 130


def _dec_mouse_tile(rel_mouse_coord: int, step: int, offset: int) -> XY:
    """
    Decreases a coordinate of the mouse tile.

    Args:
        relative mouse coordinate, movement step, offset
    Returns:
        relative mouse coordinate, offset
    """

    if KEYBOARD.is_ctrl_on:
        return 0, 0

    rel_mouse_coord -= step
    did_exit_visible_area: bool = rel_mouse_coord < 0
    if did_exit_visible_area:
        offset = max(offset + rel_mouse_coord, 0)
        rel_mouse_coord = 0

    return rel_mouse_coord, offset


def _inc_mouse_tile(
        rel_mouse_coord: int, step: int, offset: int,
        visible_side: int, side: int
) -> XY:
    """
    Increases a coordinate of the mouse tile.

    Args:
        relative mouse coordinate, movement step, offset, side of visible area, side of area
    Returns:
        relative mouse coordinate, offset
    """

    if KEYBOARD.is_ctrl_on:
        return visible_side - 1, side - visible_side

    rel_mouse_coord += step
    did_exit_visible_area: bool = rel_mouse_coord > visible_side - 1
    if did_exit_visible_area:
        extra_offset: int = rel_mouse_coord - (visible_side - 1)
        offset = min(offset + extra_offset, side - visible_side)
        rel_mouse_coord = visible_side - 1

    return rel_mouse_coord, offset


def _get_tiles_in_line(x_1: int, y_1: int, x_2: int, y_2: int) -> NDArray[int32]:
    """
    Gets the tiles that touch a line using Bresenham's Line Algorithm.

    Args:
        line start x, line start y, line end x, line end y
    Returns:
        tiles
    """

    tiles: list[XY] = []
    delta_x: int = abs(x_2 - x_1)
    delta_y: int = abs(y_2 - y_1)
    err: int = delta_x - delta_y
    step_x: Literal[-1, 1] = 1 if x_1 < x_2 else -1
    step_y: Literal[-1, 1] = 1 if y_1 < y_2 else -1

    while True:
        tiles.append((x_1, y_1))
        if x_1 == x_2 and y_1 == y_2:
            break

        err_2: int = err * 2
        if err_2 > -delta_y:
            err -= delta_y
            x_1 += step_x
        if err_2 <  delta_x:
            err += delta_x
            y_1 += step_y

    return np.array(tiles, int32)


class Grid:
    """Class to create a pixel grid and its minimap."""

    __slots__ = (
        "_grid_init_pos",
        "cols", "rows", "visible_cols", "visible_rows", "offset_x", "offset_y", "grid_tile_dim",
        "grid_rect",
        "tiles", "selected_tiles", "brush_dim", "zoom_direction", "history", "history_i",
        "_minimap_init_pos", "minimap_rect", "_unscaled_minimap_img",
        "hover_rects", "layer", "blit_sequence", "_win_w_ratio", "_win_h_ratio",
    )

    cursor_type: int = SYSTEM_CURSOR_CROSSHAIR
    objs_info: tuple[ObjInfo, ...] = ()

    def __init__(self: Self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the grid and minimap.

        Args:
            grid position, minimap position
        """

        # Tiles dimensions are floats to represent the full size more accurately when resizing

        self._grid_init_pos: RectPos = grid_pos

        self.cols: int = 1
        self.rows: int = 1
        self.visible_cols: int = 1
        self.visible_rows: int = 1
        self.offset_x: int = 0
        self.offset_y: int = 0
        self.grid_tile_dim: float = _GRID_DIM_CAP / max(self.visible_cols, self.visible_rows)

        grid_img: pg.Surface = pg.Surface((_GRID_DIM_CAP, _GRID_DIM_CAP))
        self.grid_rect: pg.Rect = pg.Rect(0, 0, *grid_img.get_size())
        setattr(
            self.grid_rect, self._grid_init_pos.coord_type,
            (self._grid_init_pos.x, self._grid_init_pos.y)
        )

        self.tiles: NDArray[uint8] = np.zeros((self.cols, self.rows, 4), uint8)
        self.selected_tiles: NDArray[bool_] = np.zeros((self.cols, self.rows), bool_)

        self.brush_dim: int = 1
        self.zoom_direction: Literal[-1, 1] = 1
        compressed_tiles: bytes = compress(self.tiles.tobytes())
        self.history: deque[_HistorySnapshot] = deque(((self.cols, self.rows, compressed_tiles),))
        self.history_i: int = 0

        self._minimap_init_pos: RectPos = minimap_pos

        minimap_img: pg.Surface = pg.Surface((_MINIMAP_DIM_CAP, _MINIMAP_DIM_CAP))
        self.minimap_rect: pg.Rect = pg.Rect(0, 0, *minimap_img.get_size())
        setattr(
            self.minimap_rect, self._minimap_init_pos.coord_type,
            (self._minimap_init_pos.x, self._minimap_init_pos.y)
        )

        # Better for scaling
        self._unscaled_minimap_img: pg.Surface = pg.Surface(
            (self.tiles.shape[0], self.tiles.shape[1]),
            depth=24
        )

        self.hover_rects: tuple[pg.Rect, ...] = (self.grid_rect,)
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = [
            (grid_img   , self.grid_rect   , self.layer),
            (minimap_img, self.minimap_rect, self.layer),
        ]
        self._win_w_ratio: float = 1
        self._win_h_ratio: float = 1

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self.selected_tiles.fill(False)
        self.refresh_grid_img()

    def resize(self: Self, win_w_ratio: float, win_h_ratio: float) -> None:
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
            self: Self, tiles: NDArray[uint8],
            visible_cols: int, visible_rows: int, offset_x: int, offset_y: int,
            should_reset_history: bool
    ) -> None:
        """
        Sets the tiles, area, visible area and offset without refreshing.

        Args:
            tiles, visible columns, visible rows, x offset, y offset, reset history flag
        """

        self.tiles = tiles
        self.cols, self.rows = self.tiles.shape[0], self.tiles.shape[1]
        self.visible_cols, self.visible_rows = visible_cols, visible_rows
        self.offset_x, self.offset_y = offset_x, offset_y

        self.selected_tiles = np.zeros((self.cols, self.rows), bool_)
        if should_reset_history:
            self.history.clear()
            self.history.append((self.cols, self.rows, compress(self.tiles.tobytes())))
            self.history_i = 0

    def _resize_grid_img(self: Self, unscaled_img: pg.Surface) -> None:
        """
        Resizes the unscaled grid image with a gradual blur.

        Args:
            unscaled grid image
        """

        xy: XY
        w: int
        h: int
        img: pg.Surface

        init_tile_dim: float = _GRID_DIM_CAP / max(self.visible_cols, self.visible_rows)
        self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)
        xy, (w, h) = resize_obj(
            self._grid_init_pos,
            self.visible_cols * init_tile_dim, self.visible_rows * init_tile_dim,
            self._win_w_ratio, self._win_h_ratio, should_keep_wh_ratio=True
        )

        max_visible_dim: int = max(self.visible_cols, self.visible_rows)
        if   max_visible_dim < _GRID_TRANSITION_START:
            img = pg.transform.scale(      unscaled_img, (w, h))
        elif max_visible_dim > _GRID_TRANSITION_END:
            img = pg.transform.smoothscale(unscaled_img, (w, h))
        elif _GRID_TRANSITION_START <= max_visible_dim <= _GRID_TRANSITION_END:
            # Gradual transition
            img = pg.surfarray.make_surface(cv2.resize(
                pg.surfarray.pixels3d(unscaled_img),
                (h, w),
                interpolation=cv2.INTER_AREA
            ).astype(uint8))

        self.grid_rect.size = (w, h)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, xy)

        self.blit_sequence[0] = (img.convert(), self.grid_rect, self.layer)

    def refresh_grid_img(self: Self) -> None:
        """Refreshes the grid image from the small minimap and draws the selected tiles."""

        selected_xs: NDArray[intp]
        selected_ys: NDArray[intp]

        selected_tiles_indexes: NDArray[intp] = np.flatnonzero(
            self.selected_tiles[
                self.offset_x:self.offset_x + self.visible_cols,
                self.offset_y:self.offset_y + self.visible_rows,
            ]
        )
        selected_xs, selected_ys = np.divmod(selected_tiles_indexes, self.visible_rows)
        selected_xs += self.offset_x
        selected_ys += self.offset_y
        selected_xs *= TILE_W
        selected_ys *= TILE_H

        unscaled_minimap_img: pg.Surface = (
            self._unscaled_minimap_img.copy() if selected_tiles_indexes.size > 250_000 else
            self._unscaled_minimap_img
        )

        # For every position get indexes of the TILE_WxTILE_H section as a 1D array
        repeated_cols: NDArray[uint8] = np.repeat(np.arange(TILE_W, dtype=uint8), TILE_H)
        repeated_rows: NDArray[uint8] = np.tile(  np.arange(TILE_H, dtype=uint8), TILE_W)
        xs: NDArray[intp] = (selected_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]).ravel()
        ys: NDArray[intp] = (selected_ys[:, np.newaxis] + repeated_rows[np.newaxis, :]).ravel()

        # Faster
        selected_1d_indexes: NDArray[intp] = ys
        selected_1d_indexes *= (self.cols * TILE_W)
        selected_1d_indexes += xs

        color_range: NDArray[uint16] = np.arange(256, dtype=uint16)
        # Lookup table for every blend combination with gray (150, 150, 150, 128)
        a: int = 128
        blend_lut: NDArray[uint8] = (((150 * a) + (color_range * (255 - a))) >> 8).astype(uint8)

        unscaled_img_arr: NDArray[uint8] = pg.surfarray.pixels3d(unscaled_minimap_img)
        # Fortran order avoids copying, reshaping a subsurface will always copy
        unscaled_img_arr = unscaled_img_arr.reshape(-1, 3, order="F")
        target_pixels: NDArray[uint8] = unscaled_img_arr[selected_1d_indexes]
        unscaled_img_arr[selected_1d_indexes] = blend_lut[target_pixels]

        # Better for scaling
        self._resize_grid_img(
            unscaled_minimap_img.subsurface(
                pg.Rect(
                    self.offset_x     * TILE_W, self.offset_y     * TILE_H,
                    self.visible_cols * TILE_W, self.visible_rows * TILE_H,
                )
            )
        )

        if selected_tiles_indexes.size < 250_000:
            unscaled_img_arr[selected_1d_indexes] = target_pixels


    def _refresh_minimap_rect(self: Self) -> None:
        """Refreshes the minimap rect."""

        init_tile_dim: float = _MINIMAP_DIM_CAP / max(self.cols, self.rows)
        xy, self.minimap_rect.size = resize_obj(
            self._minimap_init_pos,
            self.cols * init_tile_dim, self.rows * init_tile_dim,
            self._win_w_ratio, self._win_h_ratio, should_keep_wh_ratio=True
        )

        setattr(self.minimap_rect, self._minimap_init_pos.coord_type, xy)

    def _resize_minimap_img(self: Self) -> None:
        """Resizes the small minimap image with a gradual blur."""

        img: pg.Surface

        max_visible_dim: int = max(self.cols, self.rows)
        if   max_visible_dim < _MINIMAP_TRANSITION_START:
            img = pg.transform.scale(      self._unscaled_minimap_img, self.minimap_rect.size)
        elif max_visible_dim > _MINIMAP_TRANSITION_END:
            img = pg.transform.smoothscale(self._unscaled_minimap_img, self.minimap_rect.size)
        elif _MINIMAP_TRANSITION_START <= max_visible_dim <= _MINIMAP_TRANSITION_END:
            # Gradual transition
            img = pg.surfarray.make_surface(cv2.resize(
                pg.surfarray.pixels3d(self._unscaled_minimap_img),
                (self.minimap_rect.h, self.minimap_rect.w),
                interpolation=cv2.INTER_AREA
            ).astype(uint8))

        self.blit_sequence[1] = (img.convert(), self.minimap_rect, self.layer)

    def refresh_minimap_img(self: Self) -> None:
        """Refreshes the minimap image scaled to minimap_rect and draws the indicator."""

        # Better for scaling
        img_arr: NDArray[uint8] = pg.surfarray.pixels3d(self._unscaled_minimap_img)

        offset_x: int = self.offset_x * TILE_W
        offset_y: int = self.offset_y * TILE_H
        visible_cols: int = self.visible_cols * TILE_W
        visible_rows: int = self.visible_rows * TILE_H

        target_left_pixels: NDArray[uint8] = img_arr[
            offset_x:offset_x + TILE_W,
            offset_y:offset_y + visible_rows
        ]
        target_top_pixels: NDArray[uint8] = img_arr[
            offset_x:offset_x + visible_cols,
            offset_y:offset_y + TILE_H
        ]
        target_right_pixels: NDArray[uint8] = img_arr[
            offset_x + visible_cols - TILE_W:offset_x + visible_cols,
            offset_y:offset_y + visible_rows
        ]
        target_bottom_pixels: NDArray[uint8] = img_arr[
            offset_x:offset_x + visible_cols,
            offset_y + visible_rows - TILE_H:offset_y + visible_rows
        ]

        src_left_pixels: NDArray[uint8]   = target_left_pixels.copy()
        src_top_pixels: NDArray[uint8]    = target_top_pixels.copy()
        src_right_pixels: NDArray[uint8]  = target_right_pixels.copy()
        src_bottom_pixels: NDArray[uint8] = target_bottom_pixels.copy()

        color_range: NDArray[uint16] = np.arange(256, dtype=uint16)
        # Lookup table for every blend combination with gray (150, 150, 150, 128)
        a: int = 128
        blend_lut: NDArray[uint8] = (((150 * a) + (color_range * (255 - a))) >> 8).astype(uint8)
        target_left_pixels[  ...] = blend_lut[target_left_pixels]
        target_top_pixels[   ...] = blend_lut[target_top_pixels]
        target_right_pixels[ ...] = blend_lut[target_right_pixels]
        target_bottom_pixels[...] = blend_lut[target_bottom_pixels]

        self._resize_minimap_img()

        # Indicator is small, resetting changed pixels is faster than copy
        target_left_pixels[  ...] = src_left_pixels
        target_top_pixels[   ...] = src_top_pixels
        target_right_pixels[ ...] = src_right_pixels
        target_bottom_pixels[...] = src_bottom_pixels

    def refresh_full(self: Self) -> None:
        """Refreshes the tiles on the minimap, its rect and retrieves the grid."""

        # Repeats tiles so an empty tile image takes 1 normal-sized tile
        repeated_tiles: NDArray[uint8] = self.tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_tiles_mask: NDArray[bool_] = (repeated_tiles[..., 3] == 0)[..., np.newaxis]

        empty_img_arr: NDArray[uint8] = np.tile(EMPTY_TILE_ARR, (self.cols, self.rows, 1))
        rgb_repeated_tiles: NDArray[uint8] = repeated_tiles[..., :3]
        img_arr: NDArray[uint8] = np.where(empty_tiles_mask, empty_img_arr, rgb_repeated_tiles)
        self._unscaled_minimap_img = pg.surfarray.make_surface(img_arr)

        self.refresh_grid_img()
        self._refresh_minimap_rect()
        self.refresh_minimap_img()

    def set_tiles(self: Self, img: pg.Surface | None) -> None:
        """
        Sets the grid tiles using an image pixels.

        Args:
            image (if None it creates an empty grid)
        """

        if img is None:
            self.tiles = np.zeros((self.cols, self.rows, 4), uint8)
        else:
            self.tiles = get_pixels(img)

            extra_w: int = self.cols - self.tiles.shape[0]
            if   extra_w < 0:
                self.tiles = self.tiles[:self.cols, ...]
            elif extra_w > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, extra_w), (0, 0), (0, 0)),
                    constant_values=0
                )

            extra_h: int = self.rows - self.tiles.shape[1]
            if   extra_h < 0:
                self.tiles = self.tiles[:, :self.rows, ...]
            elif extra_h > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, 0), (0, extra_h), (0, 0)),
                    constant_values=0
                )

        self.history.clear()
        self.history.append((self.cols, self.rows, compress(self.tiles.tobytes())))
        self.history_i = 0

        self.refresh_full()

    def add_to_history(self: Self) -> None:
        """Adds the current info to the history if different from the last snapshot."""

        snapshot: _HistorySnapshot = (self.cols, self.rows, compress(self.tiles.tobytes()))
        if snapshot != self.history[self.history_i]:
            if self.history_i != (len(self.history) - 1):
                stop_i: int = self.history_i + 1
                history_sl: tuple[_HistorySnapshot, ...] = tuple(islice(self.history, stop_i))
                self.history.clear()
                self.history.extend(history_sl)
            self.history.append(snapshot)
            self.history_i = min(self.history_i + 1, len(self.history) - 1)

    def handle_move_with_keys(self: Self, rel_mouse_col: int, rel_mouse_row: int) -> XY:
        """
        Handles moving the mouse tile with the keyboard.

        Args:
            relative mouse column, relative mouse row
        Returns:
            relative mouse column, relative mouse row
        """

        prev_rel_mouse_col: int = rel_mouse_col
        prev_rel_mouse_row: int = rel_mouse_row

        step: int = 1
        if KEYBOARD.is_shift_on:
            if K_LEFT in KEYBOARD.timed or K_RIGHT in KEYBOARD.timed:
                step = self.visible_cols
            else:
                step = self.visible_rows
        if K_TAB in KEYBOARD.pressed:
            step = self.brush_dim

        if K_LEFT  in KEYBOARD.timed:
            rel_mouse_col, self.offset_x = _dec_mouse_tile(
                rel_mouse_col, step, self.offset_x
            )
        if K_RIGHT in KEYBOARD.timed:
            rel_mouse_col, self.offset_x = _inc_mouse_tile(
                rel_mouse_col, step, self.offset_x, self.visible_cols, self.cols
            )
        if K_UP    in KEYBOARD.timed:
            rel_mouse_row, self.offset_y = _dec_mouse_tile(
                rel_mouse_row, step, self.offset_y
            )
        if K_DOWN  in KEYBOARD.timed:
            rel_mouse_row, self.offset_y = _inc_mouse_tile(
                rel_mouse_row, step, self.offset_y, self.visible_rows, self.rows
            )

        if rel_mouse_col != prev_rel_mouse_col or rel_mouse_row != prev_rel_mouse_row:
            def _get_rel_mouse_coord(grid_coord: int, prev_grid_coord: int, max_coord: int) -> int:
                """
                Gets the relative mouse coordinate making sure the mouse actually moves.

                Args:
                    grid coordinate, grid previous coordinate, maximum coordinate
                Returns:
                    relative coordinate
                """

                half_tile_dim: float = self.grid_tile_dim / 2
                rel_coord: int      = round((grid_coord      * self.grid_tile_dim) + half_tile_dim)
                prev_rel_coord: int = round((prev_grid_coord * self.grid_tile_dim) + half_tile_dim)
                # Grid is so large that coord stays the same
                if grid_coord != prev_grid_coord and rel_coord == prev_rel_coord:
                    direction: Literal[-1, 1] = 1 if grid_coord > prev_grid_coord else -1
                    rel_coord = min(max(rel_coord + direction, 0), max_coord)

                return rel_coord
            rel_mouse_x: int = _get_rel_mouse_coord(
                rel_mouse_col, prev_rel_mouse_col,
                self.grid_rect.w - 1
            )
            rel_mouse_y: int = _get_rel_mouse_coord(
                rel_mouse_row, prev_rel_mouse_row,
                self.grid_rect.h - 1
            )

            MOUSE.x, MOUSE.y = self.grid_rect.x + rel_mouse_x, self.grid_rect.y + rel_mouse_y
            pg.mouse.set_pos(MOUSE.x, MOUSE.y)

        return rel_mouse_col, rel_mouse_row

    def _dec_largest_side(self: Self, amount: int) -> None:
        """
        Decreases the largest side of the visible area.

        Args:
            amount
        """

        if   self.visible_cols > self.visible_rows:
            self.visible_cols = max(self.visible_cols - amount, 1)
            self.visible_rows = min(self.visible_rows, self.visible_cols)
        elif self.visible_rows > self.visible_cols:
            self.visible_rows = max(self.visible_rows - amount, 1)
            self.visible_cols = min(self.visible_cols, self.visible_rows)

    def _inc_smallest_side(self: Self, amount: int) -> None:
        """
        Increases the smallest side of the visible area.

        Args:
            amount
        """

        if (
            self.visible_cols != self.cols and
            (self.visible_cols < self.visible_rows or self.visible_rows == self.rows)
        ):
            self.visible_cols = min(self.visible_cols + amount, self.cols)
            self.visible_rows = max(self.visible_rows, min(self.visible_cols, self.rows))
        else:
            self.visible_rows = min(self.visible_rows + amount, self.rows)
            self.visible_cols = max(self.visible_cols, min(self.visible_rows, self.cols))

    def _zoom_visible_area(
            self: Self, amount: int, should_reach_min_limit: bool, should_reach_max_limit: bool
    ) -> None:
        """
        Zooms the visible area.

        Args:
            amount, reach minimum limit flag, reach maximum limit flag
        """

        # amount: wheel down (-), wheel up (+)

        if   should_reach_min_limit:
            self.visible_cols = self.visible_rows = 1
        elif should_reach_max_limit:
            self.visible_cols, self.visible_rows = self.cols, self.rows
        elif self.visible_cols == self.visible_rows:
            self.visible_cols = min(max(self.visible_cols - amount, 1), self.cols)
            self.visible_rows = min(max(self.visible_rows - amount, 1), self.rows)
        elif amount > 0:
            self._dec_largest_side(amount)
        elif amount < 0:
            self._inc_smallest_side(-amount)

    def handle_zoom(self: Self) -> None:
        """Zooms the grid in or out."""

        amount: int = 0
        should_reach_min_limit: bool = False
        should_reach_max_limit: bool = False

        if MOUSE.scroll_amount != 0:
            # Amount depends on zoom level
            uncapped_amount: int = int(MOUSE.scroll_amount * (25 / self.grid_tile_dim))
            if uncapped_amount == 0:
                uncapped_amount = 1 if MOUSE.scroll_amount > 0 else -1
            amount = min(max(uncapped_amount * self.zoom_direction, -128), 128)

        if KEYBOARD.is_ctrl_on:
            if K_PLUS  in KEYBOARD.timed:
                amount = 1
                should_reach_min_limit = KEYBOARD.is_shift_on
            if K_MINUS in KEYBOARD.timed:
                amount = -1
                should_reach_max_limit = KEYBOARD.is_shift_on

        if amount != 0:
            prev_mouse_col: int = int((MOUSE.x - self.grid_rect.x) / self.grid_tile_dim)
            prev_mouse_row: int = int((MOUSE.y - self.grid_rect.y) / self.grid_tile_dim)

            self._zoom_visible_area(amount, should_reach_min_limit, should_reach_max_limit)
            init_tile_dim: float = _GRID_DIM_CAP / max(self.visible_cols, self.visible_rows)
            self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)

            mouse_col: int      = int((MOUSE.x - self.grid_rect.x) / self.grid_tile_dim)
            mouse_row: int      = int((MOUSE.y - self.grid_rect.y) / self.grid_tile_dim)

            self.offset_x = min(max(
                self.offset_x + (prev_mouse_col - mouse_col),
                0), self.cols - self.visible_cols
            )
            self.offset_y = min(max(
                self.offset_y + (prev_mouse_row - mouse_row),
                0), self.rows - self.visible_rows
            )

    def upt_section(self: Self, is_erasing: bool, hex_color: HexColor) -> bool:
        """
        Updates the changed tiles and refreshes the small minimap.

        Args:
            erasing flag, hexadecimal color
        Returns:
            drawn flag
        """

        selected_xs: NDArray[intp]
        selected_ys: NDArray[intp]

        rgba_color: NDArray[uint8] = np.array(
            (0, 0, 0, 0) if is_erasing else pg.Color("#" + hex_color),
            uint8
        )

        # Packs a color as a uint32 and compares
        tiles_view: NDArray[uint32] = self.tiles[self.selected_tiles].view(uint32)
        rgba_color_view: NDArray[uint32] = rgba_color.view(uint32)
        did_draw: bool = (tiles_view[..., 0] != rgba_color_view[0]).any()
        if did_draw:
            self.tiles[self.selected_tiles] = rgba_color
            selected_tiles_indexes: NDArray[intp] = np.flatnonzero(self.selected_tiles)
            selected_xs, selected_ys = np.divmod(selected_tiles_indexes, self.rows)
            selected_xs *= TILE_W
            selected_ys *= TILE_H

            # For every position get indexes of the TILE_WxTILE_H section as a 1D array
            repeated_cols: NDArray[uint8] = np.repeat(np.arange(TILE_W, dtype=uint8), TILE_H)
            repeated_rows: NDArray[uint8] = np.tile(  np.arange(TILE_H, dtype=uint8), TILE_W)
            xs: NDArray[intp] = (selected_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]).ravel()
            ys: NDArray[intp] = (selected_ys[:, np.newaxis] + repeated_rows[np.newaxis, :]).ravel()

            # Faster
            selected_1d_indexes: NDArray[intp] = ys.copy()
            selected_1d_indexes *= (self.cols * TILE_W)
            selected_1d_indexes += xs

            unscaled_img_arr: NDArray[uint8] = pg.surfarray.pixels3d(self._unscaled_minimap_img)
            # Fortran order avoids copying
            unscaled_img_arr = unscaled_img_arr.reshape(-1, 3, order="F")
            if is_erasing:
                xs %= TILE_W
                ys %= TILE_H
                empty_tile_arr_1d_indexes: NDArray[intp] = ys
                empty_tile_arr_1d_indexes *= TILE_W
                empty_tile_arr_1d_indexes += xs
                empty_tile_arr_1d: NDArray[uint8] = EMPTY_TILE_ARR.reshape(-1, 3, order="F")
                unscaled_img_arr[selected_1d_indexes] = empty_tile_arr_1d[empty_tile_arr_1d_indexes]
            else:
                unscaled_img_arr[selected_1d_indexes] = rgba_color[:3]

        return did_draw

    def try_save(
            self: Self, file_str: str,
            should_ask_create_dir: bool, should_use_gui: bool = True
    ) -> pg.Surface | None:
        """
        Saves the image to a file with retries.

        Args:
            file string, ask directory creation flag, use GUI for errors flag (default = True)
        Returns:
            image (can be None)
        """

        error_str: str
        should_retry: bool

        if file_str == "":
            return None

        pg_img: pg.Surface = pg.Surface((self.cols, self.rows), SRCALPHA)
        pg.surfarray.blit_array(pg_img, self.tiles[..., :3])
        pg.surfarray.pixels_alpha(pg_img)[...] = self.tiles[..., 3]
        pg_img_bytes: bytes = pg.image.tobytes(pg_img, "RGBA")
        img: Image.Image = Image.frombytes("RGBA", pg_img.get_size(), pg_img_bytes)

        file_path: Path = Path(file_str)
        temp_file_path: Path = Path(file_str + ".tmp")

        dummy_file: BytesIO = BytesIO()
        suffix: str = file_path.suffix if file_path.suffix != "" else file_path.name  # Dotfiles
        img.save(dummy_file, suffix[1:], lossless=True)
        img_bytes: bytes = dummy_file.getvalue()

        display_error: Callable[[str, str], None] = (
            (lambda title, error_str: (messagebox.showerror(title, error_str), None)[1])
            if should_use_gui else
            (lambda title, error_str: print(f"{title}\n{error_str}", file=stderr))
        )
        def _handle_dir_not_found() -> bool:
            """
            Creates the directory, asks the user if it should.

            Returns:
                failed flag
            """

            if should_ask_create_dir and dir_creation_attempt_i == FILE_ATTEMPT_START_I + 1:
                should_create: bool = messagebox.askyesno(
                    "Image Save Failed",
                    f"Directory missing: {file_path.parent.name}\nDo you wanna create it?",
                    icon="warning",
                )

                if not should_create:
                    return True

            error_str: str | None = try_create_dir(file_path.parent, dir_creation_attempt_i)
            if error_str is not None:
                display_error("Image Save Failed", error_str)

            return error_str is not None

        dir_creation_attempt_i: int = FILE_ATTEMPT_START_I
        system_attempt_i: int       = FILE_ATTEMPT_START_I
        did_succeed: bool = False
        while (
            dir_creation_attempt_i <= FILE_ATTEMPT_STOP_I and
            system_attempt_i       <= FILE_ATTEMPT_STOP_I
        ):
            try:
                # If you open in write mode it will empty the file even if it's locked
                with temp_file_path.open("ab") as f:
                    try_lock_file(f, is_shared=False)
                    try_write_file(f, img_bytes)
                try_replace_file(temp_file_path, file_path)
                did_succeed = True
                break
            except FileNotFoundError:
                dir_creation_attempt_i += 1
                did_fail: bool = _handle_dir_not_found()
                if did_fail:
                    break
            except (PermissionError, LockError, FileError) as e:
                error_str = {
                    PermissionError: "Permission denied.",
                    LockError: "File locked.",
                    FileError: e.error_str if isinstance(e, FileError) else "",
                }[type(e)]

                display_error("Image Save Failed", f"{file_path.name}: {error_str}")
                break
            except OSError as e:
                system_attempt_i += 1
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** system_attempt_i)
                    continue

                try_remove_file(temp_file_path)
                display_error("Image Save Failed", f"{file_path.name}: {error_str}")
                break

        return pg_img if did_succeed else None


class GridManager:
    """Class to create and edit a grid of pixels."""

    __slots__ = (
        "_is_hovering", "_can_leave", "_prev_hovered_obj", "_last_mouse_move_time",
        "_prev_mouse_col", "_prev_mouse_row", "_mouse_col", "_mouse_row",
        "_traveled_x", "_traveled_y",
        "_is_erasing", "_is_coloring", "_did_stop_erasing", "_did_stop_coloring",
        "is_x_mirror_on", "is_y_mirror_on", "_can_add_to_history",
        "eye_dropped_color", "saved_col", "saved_row",
        "grid", "_hovering_text_label", "_hovering_text_label_obj_info",
        "hover_rects", "layer", "blit_sequence", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(self: Self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object and wrapper info.

        Args:
            grid position, minimap position
        """

        self._is_hovering: bool = False
        self._can_leave: bool = False
        self._prev_hovered_obj: UIElement | None = MOUSE.hovered_obj
        self._last_mouse_move_time: int = my_vars.ticks

        # Used to avoid passing parameters
        self._prev_mouse_col: int = 0
        self._prev_mouse_row: int = 0
        self._mouse_col: int      = 0
        self._mouse_row: int      = 0

        self._traveled_x: float = 0
        self._traveled_y: float = 0

        # Used to avoid passing parameters
        self._is_erasing: bool  = False
        self._is_coloring: bool = False
        self._did_stop_erasing: bool  = False
        self._did_stop_coloring: bool = False
        self.is_x_mirror_on: bool = False
        self.is_y_mirror_on: bool = False

        self._can_add_to_history: bool = False

        self.eye_dropped_color: RGBColor | None = None
        # Used for line, rect, etc.
        self.saved_col: int | None = None
        self.saved_row: int | None = None

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self._hovering_text_label: TextLabel = TextLabel(
            RectPos(MOUSE.x, MOUSE.y, "topleft"),
            "Enter\nBackspace", BG_LAYER + TOP_LAYER - TEXT_LAYER,
            h=12, bg_color=BLACK, alpha=0
        )
        self._hovering_text_label_obj_info: ObjInfo = ObjInfo(self._hovering_text_label)
        self._hovering_text_label_obj_info.rec_set_active(False)

        self.hover_rects: tuple[pg.Rect, ...] = ()
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = []
        self.objs_info: tuple[ObjInfo, ...] = (
            ObjInfo(self.grid), self._hovering_text_label_obj_info
        )

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._last_mouse_move_time = my_vars.ticks

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._is_hovering = False
        self._prev_hovered_obj = None
        self._can_leave = False
        self._traveled_x = self._traveled_y = 0
        self.eye_dropped_color = self.saved_col = self.saved_row = None

        if self._can_add_to_history:
            self.grid.add_to_history()
            self._can_add_to_history = False

        if self._hovering_text_label_obj_info.is_active:
            self._hovering_text_label.alpha = 0
            self._hovering_text_label_obj_info.rec_set_active(False)

    def resize(self: Self, _win_w_ratio: float, _win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

    def _handle_move(self: Self) -> None:
        """Handles moving the visible section."""

        # Faster when moving the mouse faster

        speed_x: float = abs(MOUSE.prev_x - MOUSE.x) ** 1.25
        if MOUSE.x > MOUSE.prev_x:
            speed_x = -speed_x
        self._traveled_x += speed_x

        speed_y: float = abs(MOUSE.prev_y - MOUSE.y) ** 1.25
        if MOUSE.y > MOUSE.prev_y:
            speed_y = -speed_y
        self._traveled_y += speed_y

        if abs(self._traveled_x) >= self.grid.grid_tile_dim:
            hor_tiles_traveled: int = int(self._traveled_x / self.grid.grid_tile_dim)
            self._traveled_x -= hor_tiles_traveled * self.grid.grid_tile_dim
            self.grid.offset_x = min(max(
                self.grid.offset_x + hor_tiles_traveled,
                0), self.grid.cols - self.grid.visible_cols
            )

        if abs(self._traveled_y) >= self.grid.grid_tile_dim:
            ver_tiles_traveled: int = int(self._traveled_y / self.grid.grid_tile_dim)
            self._traveled_y -= ver_tiles_traveled * self.grid.grid_tile_dim
            self.grid.offset_y = min(max(
                self.grid.offset_y + ver_tiles_traveled,
                0), self.grid.rows - self.grid.visible_rows
            )

    def _handle_move_history_i(self: Self) -> bool:
        """
        Handles changing the index of the viewed history snapshot with the keyboard.

        Returns:
            changed flag
        """

        prev_history_i: int = self.grid.history_i

        if K_z in KEYBOARD.timed:
            move_sign: Literal[-1, 1] = 1 if KEYBOARD.is_shift_on else -1
            self.grid.history_i = min(max(
                self.grid.history_i + move_sign,
                0), len(self.grid.history) - 1
            )
        if K_y in KEYBOARD.timed:
            self.grid.history_i = min(self.grid.history_i + 1, len(self.grid.history) - 1)

        if self.grid.history_i != prev_history_i:
            grid_w: int             = self.grid.history[self.grid.history_i][0]
            grid_h: int             = self.grid.history[self.grid.history_i][1]
            compressed_tiles: bytes = self.grid.history[self.grid.history_i][2]

            # copying makes it writable
            tiles_1d: NDArray[uint8] = np.frombuffer(decompress(compressed_tiles), uint8).copy()
            self.grid.set_info(
                tiles_1d.reshape((grid_w, grid_h, 4)),
                self.grid.visible_cols, self.grid.visible_rows,
                self.grid.offset_x, self.grid.offset_y,
                should_reset_history=False
            )
            self.grid.refresh_full()

        return self.grid.history_i != prev_history_i

    def _handle_tile_info(self: Self) -> None:
        """Calculates previous and current mouse tiles and handles keyboard movement."""

        grid_tile_dim: float = self.grid.grid_tile_dim
        prev_rel_mouse_col: int = int((MOUSE.prev_x - self.grid.grid_rect.x) / grid_tile_dim)
        prev_rel_mouse_row: int = int((MOUSE.prev_y - self.grid.grid_rect.y) / grid_tile_dim)
        rel_mouse_col: int      = int((MOUSE.x      - self.grid.grid_rect.x) / grid_tile_dim)
        rel_mouse_row: int      = int((MOUSE.y      - self.grid.grid_rect.y) / grid_tile_dim)

        # By setting prev_mouse_tile before changing offset you can draw a line with shift/ctrl
        self._prev_mouse_col = prev_rel_mouse_col + self.grid.offset_x
        self._prev_mouse_row = prev_rel_mouse_row + self.grid.offset_y

        if KEYBOARD.timed != ():
            # Changes the offset
            rel_mouse_col, rel_mouse_row = self.grid.handle_move_with_keys(rel_mouse_col, rel_mouse_row)

        self._mouse_col      = rel_mouse_col      + self.grid.offset_x
        self._mouse_row      = rel_mouse_row      + self.grid.offset_y

    def _pencil(self: Self) -> None:
        """Handles the pencil tool."""

        # Centers tiles to the cursor
        selected_tiles_coords: NDArray[int32] = _get_tiles_in_line(
            min(max(self._prev_mouse_col, 0), self.grid.cols - 1) - (self.grid.brush_dim // 2),
            min(max(self._prev_mouse_row, 0), self.grid.rows - 1) - (self.grid.brush_dim // 2),
            min(max(self._mouse_col     , 0), self.grid.cols - 1) - (self.grid.brush_dim // 2),
            min(max(self._mouse_row     , 0), self.grid.rows - 1) - (self.grid.brush_dim // 2),
        )
        selected_xs: NDArray[int32] = selected_tiles_coords[:, 0]
        selected_ys: NDArray[int32] = selected_tiles_coords[:, 1]

        # For every position get indexes of the brush_dimXbrush_dim section as a 1D array
        brush_dim_range: NDArray[uint8] = np.arange(self.grid.brush_dim, dtype=uint8)
        repeated_cols: NDArray[uint8] = np.repeat(brush_dim_range, self.grid.brush_dim)
        repeated_rows: NDArray[uint8] = np.tile(  brush_dim_range, self.grid.brush_dim)

        xs: NDArray[int32] = (selected_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]).ravel()
        ys: NDArray[int32] = (selected_ys[:, np.newaxis] + repeated_rows[np.newaxis, :]).ravel()
        np.clip(xs, 0, self.grid.cols - 1, out=xs, dtype=int32)
        np.clip(ys, 0, self.grid.rows - 1, out=ys, dtype=int32)

        # Faster
        selected_1d_indexes: NDArray[intp] = xs.astype(intp)
        selected_1d_indexes *= self.grid.rows
        selected_1d_indexes += ys
        self.grid.selected_tiles.reshape(-1)[selected_1d_indexes] = True

        if self.is_x_mirror_on:
            self.grid.selected_tiles |= self.grid.selected_tiles[::-1, :]
        if self.is_y_mirror_on:
            self.grid.selected_tiles |= self.grid.selected_tiles[:, ::-1]

    def _init_bucket_stack(self: Self, mask: NDArray[bool_]) -> list[tuple[intp, uint16, uint16]]:
        """
        Initializes the stack for the bucket tool.

        Args:
            tiles mask
        Returns:
            stack
        """

        up_tiles: NDArray[bool_] = mask[self._mouse_col, :self._mouse_row + 1]
        up_stop: int | intp = up_tiles[::-1].argmin() or up_tiles.size
        first_y: uint16 = uint16(self._mouse_row - up_stop   + 1)

        down_tiles: NDArray[bool_] = mask[self._mouse_col, self._mouse_row:]
        down_stop: int | intp = down_tiles.argmin() or down_tiles.size
        last_y: uint16  = uint16(self._mouse_row + down_stop - 1)

        return [(intp(self._mouse_col), first_y, last_y)]

    def _bucket(self: Self, extra_info: dict[str, Any]) -> None:
        """
        Handles the bucket tool using the scan-line algorithm, includes a color fill.

        Args:
            extra info (color fill)
        """

        x: intp
        start_y: uint16
        end_y: uint16
        span_starts: NDArray[uint16]
        span_ends: NDArray[uint16]
        valid_spans_mask: NDArray[bool_]
        xs: tuple[intp, ...]

        if not self._is_hovering:
            return

        # Packs a color as a uint32 and compares
        color: NDArray[uint8] = self.grid.tiles[self._mouse_col, self._mouse_row]
        mask: NDArray[bool_] = self.grid.tiles.view(uint32)[..., 0] == color.view(uint32)[0]
        if extra_info["color_fill"]:
            self.grid.selected_tiles[mask] = True
            return

        stack: list[tuple[intp, uint16, uint16]] = self._init_bucket_stack(mask)
        empty_list: list[Never] = []

        # Padded to avoid boundary checks
        visitable_tiles: NDArray[bool_] = np.ones((self.grid.cols + 2, self.grid.rows), bool_)
        visitable_tiles[0] = visitable_tiles[-1] = False

        left_shifted_cols_mask: NDArray[bool_] = np.empty((self.grid.cols, self.grid.rows), bool_)
        left_shifted_cols_mask[:, :-1] = mask[:, 1:]
        left_shifted_cols_mask[:, -1] = False
        right_shifted_cols_mask: NDArray[bool_] = np.empty((self.grid.cols, self.grid.rows), bool_)
        right_shifted_cols_mask[:, 1:] = mask[:, :-1]
        right_shifted_cols_mask[:, 0] = False

        temp_mask: NDArray[bool_] = np.empty(self.grid.rows, bool_)
        indexes: NDArray[uint16] = np.arange(0, self.grid.rows, dtype=uint16)

        selected_tiles: NDArray[bool_] = self.grid.selected_tiles
        np_logical_and = np.logical_and
        stack_pop, stack_extend = stack.pop, stack.extend
        local_zip = zip

        while stack != empty_list:
            x, start_y, end_y = stack_pop()
            selected_tiles[ x    , start_y:end_y + 1] = True
            visitable_tiles[x + 1, start_y:end_y + 1] = False

            if visitable_tiles[x, start_y] or visitable_tiles[x, + end_y]:
                np_logical_and(mask[x - 1], visitable_tiles[x], out=temp_mask)
                span_starts = indexes[temp_mask & ~right_shifted_cols_mask[x - 1]]
                span_ends   = indexes[temp_mask & ~left_shifted_cols_mask[ x - 1]]
                valid_spans_mask = (span_ends >= start_y) & (span_starts <= end_y)

                xs = (x - 1,) * valid_spans_mask.size
                stack_extend(local_zip(xs, span_starts[valid_spans_mask], span_ends[valid_spans_mask]))
            if visitable_tiles[x + 2, start_y] or visitable_tiles[x + 2, end_y]:
                np_logical_and(mask[x + 1], visitable_tiles[x + 2], out=temp_mask)
                span_starts = indexes[temp_mask & ~right_shifted_cols_mask[x + 1]]
                span_ends   = indexes[temp_mask & ~left_shifted_cols_mask[ x + 1]]
                valid_spans_mask = (span_ends >= start_y) & (span_starts <= end_y)

                xs = (x + 1,) * valid_spans_mask.size
                stack_extend(local_zip(xs, span_starts[valid_spans_mask], span_ends[valid_spans_mask]))

    def _eye_dropper(self: Self) -> None:
        """Handles the eye dropper tool."""

        if not self._is_hovering:
            return

        self.grid.selected_tiles[self._mouse_col, self._mouse_row] = True
        if self._is_coloring:
            self.eye_dropped_color = self.grid.tiles[self._mouse_col, self._mouse_row][:3]
        self._is_erasing = self._is_coloring = False

    def _line(self: Self) -> None:
        """Handles the line tool."""

        if not self._is_hovering:
            return

        self._is_erasing = self._is_coloring = False
        selected_tiles_coords: NDArray[int32] = np.empty((0, 2), int32)
        # Centers tiles to the cursor
        if self.saved_col is not None and self.saved_row is not None:
            selected_tiles_coords = _get_tiles_in_line(
                min(max(self.saved_col, 0) , self.grid.cols - 1) - (self.grid.brush_dim // 2),
                min(max(self.saved_row, 0) , self.grid.rows - 1) - (self.grid.brush_dim // 2),
                min(max(self._mouse_col, 0), self.grid.cols - 1) - (self.grid.brush_dim // 2),
                min(max(self._mouse_row, 0), self.grid.rows - 1) - (self.grid.brush_dim // 2),
            )

            if self._did_stop_erasing or self._did_stop_coloring:
                self.saved_col = self.saved_row = None
                self._is_erasing = self._did_stop_erasing
                self._is_coloring = self._did_stop_coloring
        else:
            selected_tiles_coords = np.array(
                ((
                    self._mouse_col - (self.grid.brush_dim // 2),
                    self._mouse_row - (self.grid.brush_dim // 2),
                ),),
                int32
            )

            if self._did_stop_erasing or self._did_stop_coloring:
                self.saved_col, self.saved_row = self._mouse_col, self._mouse_row

        selected_xs: NDArray[int32] = selected_tiles_coords[:, 0]
        selected_ys: NDArray[int32] = selected_tiles_coords[:, 1]

        # For every position get indexes of the brush_dimXbrush_dim section as a 1D array
        brush_dim_range: NDArray[uint8] = np.arange(self.grid.brush_dim, dtype=uint8)
        repeated_cols: NDArray[uint8] = np.repeat(brush_dim_range, self.grid.brush_dim)
        repeated_rows: NDArray[uint8] = np.tile(  brush_dim_range, self.grid.brush_dim)

        xs: NDArray[int32] = selected_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]
        ys: NDArray[int32] = selected_ys[:, np.newaxis] + repeated_rows[np.newaxis, :]
        xs = xs.ravel()
        ys = ys.ravel()
        np.clip(xs, 0, self.grid.cols - 1, out=xs, dtype=int32)
        np.clip(ys, 0, self.grid.rows - 1, out=ys, dtype=int32)

        # Faster
        selected_1d_indexes: NDArray[intp] = xs.astype(intp)
        selected_1d_indexes *= self.grid.rows
        selected_1d_indexes += ys
        self.grid.selected_tiles.reshape(-1)[selected_1d_indexes] = True

        if self.is_x_mirror_on:
            self.grid.selected_tiles |= self.grid.selected_tiles[::-1, :]
        if self.is_y_mirror_on:
            self.grid.selected_tiles |= self.grid.selected_tiles[:, ::-1]

    def _rectangle(self: Self, extra_info: dict[str, Any]) -> None:
        """
        Handles the rectangle tool.

        Args:
            extra info (fill)
        """

        if not self._is_hovering:
            return

        self._is_erasing = self._is_coloring = False
        if self.saved_col is None or self.saved_row is None:
            # Centers tiles to the cursor
            x: int = self._mouse_col - (self.grid.brush_dim // 2)
            y: int = self._mouse_row - (self.grid.brush_dim // 2)
            self.grid.selected_tiles[
                max(x, 0):x + self.grid.brush_dim,
                max(y, 0):y + self.grid.brush_dim
            ] = True

            if self._did_stop_erasing or self._did_stop_coloring:
                self.saved_col, self.saved_row = x, y
        else:
            start_x: int = min(self.saved_col, self._mouse_col)
            start_y: int = min(self.saved_row, self._mouse_row)
            end_x: int   = max(self.saved_col, self._mouse_col) + 1
            end_y: int   = max(self.saved_row, self._mouse_row) + 1

            # Better UX
            if self._mouse_col < self.saved_col:
                end_x += self.grid.brush_dim - 1
            if self._mouse_row < self.saved_row:
                end_y += self.grid.brush_dim - 1
            # Rect can't be smaller than brush_dim
            end_x = max(end_x, start_x + self.grid.brush_dim)
            end_y = max(end_y, start_y + self.grid.brush_dim)

            if extra_info["fill"]:
                self.grid.selected_tiles[start_x:end_x, start_y:end_y] = True
            else:
                self.grid.selected_tiles[
                    start_x:start_x + self.grid.brush_dim,
                    start_y:end_y
                ] = True
                self.grid.selected_tiles[
                    start_x:end_x,
                    start_y:start_y + self.grid.brush_dim
                ] = True
                self.grid.selected_tiles[
                    end_x - self.grid.brush_dim:end_x,
                    start_y:end_y
                ] = True
                self.grid.selected_tiles[
                    start_x:end_x,
                    end_y - self.grid.brush_dim:end_y
                ] = True

            if self._did_stop_erasing or self._did_stop_coloring:
                self.saved_col = self.saved_row = None
                self._is_erasing = self._did_stop_erasing
                self._is_coloring = self._did_stop_coloring

        if self.is_x_mirror_on:
            self.grid.selected_tiles |= self.grid.selected_tiles[::-1, :]
        if self.is_y_mirror_on:
            self.grid.selected_tiles |= self.grid.selected_tiles[:, ::-1]

    def _handle_draw(self: Self, hex_color: HexColor, tool_info: ToolInfo) -> tuple[bool, bool]:
        """
        Handles grid drawing via tools and refreshes the small grid image.

        Args:
            hexadecimal color, tool info
        Returns:
            drawn flag, selected tiles changed flag
        """

        did_draw: bool

        self._handle_tile_info()

        prev_selected_tiles_bytes: bytes = np.packbits(self.grid.selected_tiles).tobytes()
        self.grid.selected_tiles.fill(False)
        self._is_erasing  = MOUSE.pressed[MOUSE_RIGHT] or K_BACKSPACE in KEYBOARD.pressed
        self._is_coloring = MOUSE.pressed[MOUSE_LEFT ] or K_RETURN    in KEYBOARD.pressed

        tool_name: ToolName             = tool_info[0]
        tool_extra_info: dict[str, Any] = tool_info[1]
        if   tool_name == "pencil":
            self._pencil()
        elif tool_name == "bucket":
            self._bucket(tool_extra_info)
        elif tool_name == "eye_dropper":
            self._eye_dropper()
        elif tool_name == "line":
            self._line()
        elif tool_name == "rectangle":
            self._rectangle(tool_extra_info)

        selected_tiles_bytes: bytes = np.packbits(self.grid.selected_tiles).tobytes()
        if self._is_erasing or self._is_coloring:
            did_draw = self.grid.upt_section(self._is_erasing, hex_color)
        else:
            did_draw = False

        # Comparing bytes in this situation is faster
        return did_draw, selected_tiles_bytes != prev_selected_tiles_bytes

    def _refresh_hovering_text_label(self: Self) -> None:
        """Increases the alpha value gradually if hovering still and resets it otherwise."""

        if self._is_hovering and (my_vars.ticks - self._last_mouse_move_time >= 750):
            if not self._hovering_text_label_obj_info.is_active:
                self._hovering_text_label_obj_info.rec_set_active(True)
            rec_move_rect(
                self._hovering_text_label, MOUSE.x + 4, MOUSE.y,
                win_w_ratio=1, win_h_ratio=1
            )

            if self._hovering_text_label.alpha != 255:
                self._hovering_text_label.set_alpha(
                    round(self._hovering_text_label.alpha + (8 * my_vars.dt))
                )

    def _refresh(
            self: Self, did_draw: bool,
            prev_visible_cols: int, prev_visible_rows: int, prev_offset_x: int, prev_offset_y: int,
            did_selected_tiles_change: bool
    ) -> None:
        """
        Refreshes the hovering text and grid info.

        Args:
            drawn flag,
            previous visible columns, previous visible rows, previous x offset, previous y offset,
            selected tiles changed flag
        """

        if not self._is_hovering or (MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y):
            self._last_mouse_move_time = my_vars.ticks
            if self._hovering_text_label_obj_info.is_active:
                self._hovering_text_label.alpha = 0
                self._hovering_text_label_obj_info.rec_set_active(False)
        self._refresh_hovering_text_label()

        if (
            did_draw or
            self.grid.visible_cols != prev_visible_cols or
            self.grid.visible_rows != prev_visible_rows or
            self.grid.offset_x != prev_offset_x or
            self.grid.offset_y != prev_offset_y
        ):
            self.grid.refresh_grid_img()
            self.grid.refresh_minimap_img()
        elif did_selected_tiles_change:
            self.grid.refresh_grid_img()

        self._prev_hovered_obj = MOUSE.hovered_obj

    def upt(self: Self, hex_color: HexColor, tool_info: ToolInfo) -> bool:
        """
        Allows moving, zooming, moving in history, resetting and drawing.

        Args:
            hexadecimal color, tool info
        Returns:
            grid changed flag
        """

        prev_visible_cols: int = self.grid.visible_cols
        prev_visible_rows: int = self.grid.visible_rows
        prev_offset_x: int = self.grid.offset_x
        prev_offset_y: int = self.grid.offset_y

        self._is_hovering = MOUSE.hovered_obj == self.grid
        self._did_stop_erasing = MOUSE.released[MOUSE_RIGHT] or K_BACKSPACE in KEYBOARD.released
        self._did_stop_coloring = MOUSE.released[MOUSE_LEFT] or K_RETURN in KEYBOARD.released

        if MOUSE.pressed[MOUSE_WHEEL]:
            self._handle_move()
        else:
            self._traveled_x = self._traveled_y = 0

        if self._is_hovering and (MOUSE.scroll_amount != 0 or KEYBOARD.is_ctrl_on):
            self.grid.handle_zoom()

        did_move_history_i: bool = False
        did_draw: bool = False
        did_selected_tiles_change: bool = False

        if KEYBOARD.is_ctrl_on:
            did_move_history_i = self._handle_move_history_i()

            if K_r in KEYBOARD.pressed:
                self.grid.visible_cols = min(32, self.grid.cols)
                self.grid.visible_rows = min(32, self.grid.rows)
                self.grid.offset_x = self.grid.offset_y = 0
                self._traveled_x = self._traveled_y = 0

        if self._is_hovering or self._prev_hovered_obj == self.grid:  # Extra frame to draw
            self.eye_dropped_color = None
            did_draw, did_selected_tiles_change = self._handle_draw(hex_color, tool_info)
            self._can_leave = True

            if did_draw:
                self._can_add_to_history = True
        elif self._can_leave:
            self.grid.leave()
            self.saved_col = self.saved_row = None
            self._can_leave = False

        if (
            self._can_add_to_history and
            (self._did_stop_erasing or self._did_stop_coloring or not self._is_hovering)
        ):
            self.grid.add_to_history()
            self._can_add_to_history = False

        self._refresh(
            did_draw,
            prev_visible_cols, prev_visible_rows, prev_offset_x, prev_offset_y,
            did_selected_tiles_change,
        )

        return did_move_history_i or did_draw
