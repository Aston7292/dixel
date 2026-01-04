"""Class to create a pixel grid with a minimap."""

from tkinter import messagebox
from pathlib import Path
from zlib import compress
from collections import deque
from collections.abc import Callable
from itertools import islice
from math import ceil
from sys import stderr
from io import BytesIO
from typing import Literal, Self, TypeAlias, Final

import pygame as pg
import numpy as np
import cv2
from pygame import (
    Color, Surface, Rect, surfarray, draw, transform, mouse,
    K_TAB, K_LEFT, K_RIGHT, K_DOWN, K_UP,
    K_MINUS, K_PLUS,
    SRCALPHA, SYSTEM_CURSOR_CROSSHAIR,
)
from numpy import uint8, uint16, uint32, intp, bool_, newaxis
from numpy.typing import NDArray
from cv2 import INTER_AREA
from PIL import Image

from src.classes.devices import MOUSE, KEYBOARD

import src.vars as my_vars
from src.utils import get_pixels
from src.obj_utils import UIElement, resize_obj
from src.file_utils import (
    FileError, handle_file_os_error,
    try_write_file, try_replace_file, try_remove_file, try_create_dir,
)
from src.lock_utils import LockError, try_lock_file
from src.type_utils import XY, WH, HexColor, RectPos
from src.consts import (
    YELLOW,
    EMPTY_TILE_ARR, TILE_H, TILE_W,
    FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I,
)

_HistorySnapshot: TypeAlias = tuple[int, int, bytes]

_GRID_DIM_CAP: Final[int] = 600
_MINIMAP_DIM_CAP: Final[int] = 256


def _dec_mouse_tile(rel_mouse_coord: int, step: int, offset: int) -> tuple[int, int]:
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
        rel_mouse_coord: int, step: int, offset: int, visible_side: int, side: int
) -> tuple[int, int]:
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

def grid_resize(
        small_img: Surface, rect: Rect,
        init_pos: RectPos, cols: int, rows: int,
        dim_cap: int, transition_start: int, transition_end: int
) -> Surface:
    """
    Resizes the grid image with a gradual blur.

    Args:
        small image, rect,
        position, columns, rows,
        size cap, transition start size, transition end size
    Returns:
        image
    """

    xy: XY
    w: int
    h: int

    init_tile_dim: float = dim_cap / max(cols, rows)
    xy, (w, h) = resize_obj(
        init_pos,
        cols * init_tile_dim, rows * init_tile_dim,
        should_keep_wh_ratio=True
    )

    max_dim: int = max(cols, rows)
    if   max_dim < transition_start:
        small_img = transform.scale(      small_img, (w, h))
    elif max_dim > transition_end:
        small_img = transform.smoothscale(small_img, (w, h))
    elif transition_start <= max_dim <= transition_end:
        # Gradual transition
        small_img = surfarray.make_surface(cv2.resize(
            surfarray.pixels3d(small_img), (h, w),
            interpolation=INTER_AREA
        ).astype(uint8))

    rect.size = (w, h)
    setattr(rect, init_pos.coord_type, xy)

    return small_img

def grid_draw_center(img: Surface, center: XY) -> None:
    """
    Draws a yellow rectangle to represent the center of the grid.

    Args:
        image, center
    """

    rect: Rect = Rect(0, 0, 5, 5)
    rect.center = center
    draw.rect(img, YELLOW, rect)

def grid_draw_tile_lines(
        img: Surface, wh: WH, grid_tile_dim: float,
        offset_x: int, offset_y: int
    ) -> None:
    """
    Draws yellow lines to represent tiles.

    Args:
        image, tile size, grid tile size, x offset, y offset
    """

    x: int
    y: int

    img_w: int = img.get_width()
    img_h: int = img.get_height()
    w: int = round(wh[0] * grid_tile_dim)
    h: int = round(wh[1] * grid_tile_dim)

    for x in range(w + offset_x, img_w, w):
        draw.line(img, YELLOW, (x, 0), (x, img_h))
    for y in range(h + offset_y, img_h, h):
        draw.line(img, YELLOW, (0, y), (img_w, y))


class Grid(UIElement):
    """Class to create a pixel grid with a minimap."""

    __slots__ = (
        "_grid_init_pos",
        "cols", "rows", "visible_cols", "visible_rows", "offset_x", "offset_y", "grid_tile_dim",
        "grid_rect",
        "tiles", "selected_tiles",
        "brush_dim", "zoom_direction", "should_show_center", "tile_mode_size",
        "history", "history_i",
        "_minimap_init_pos", "minimap_rect", "_unscaled_minimap_img",
    )

    def __init__(self: Self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the grid and minimap.

        Args:
            grid position, minimap position
        """

        super().__init__()

        # Tiles dimensions are floats to represent the full size more accurately when resizing

        self._grid_init_pos: RectPos = grid_pos

        self.cols: int = 1
        self.rows: int = 1
        self.visible_cols: int = 1
        self.visible_rows: int = 1
        self.offset_x: int = 0
        self.offset_y: int = 0
        self.grid_tile_dim: float = _GRID_DIM_CAP / max(self.visible_cols, self.visible_rows)

        grid_img: Surface = Surface((_GRID_DIM_CAP, _GRID_DIM_CAP))
        self.grid_rect: Rect = Rect(0, 0, *grid_img.get_size())
        setattr(
            self.grid_rect, self._grid_init_pos.coord_type,
            (self._grid_init_pos.x, self._grid_init_pos.y)
        )

        self.tiles: NDArray[uint8] = np.zeros((self.cols, self.rows, 4), uint8)
        self.selected_tiles: NDArray[bool_] = np.zeros((self.cols, self.rows), bool_)

        self.brush_dim: int = 1
        self.zoom_direction: Literal[-1, 1] = 1
        self.should_show_center: bool = False
        self.tile_mode_size: WH | None = None

        compressed_tiles: bytes = compress(self.tiles.tobytes())
        self.history: deque[_HistorySnapshot] = deque(((self.cols, self.rows, compressed_tiles),))
        self.history_i: int = 0

        self._minimap_init_pos: RectPos = minimap_pos

        minimap_img: Surface = Surface((_MINIMAP_DIM_CAP, _MINIMAP_DIM_CAP))
        self.minimap_rect: Rect = Rect(0, 0, *minimap_img.get_size())
        setattr(
            self.minimap_rect, self._minimap_init_pos.coord_type,
            (self._minimap_init_pos.x, self._minimap_init_pos.y)
        )

        # Better for scaling
        self._unscaled_minimap_img: Surface = Surface(
            (self.tiles.shape[0], self.tiles.shape[1]),
            depth=24
        )

        self.hover_rects = (self.grid_rect,)
        self.cursor_type = SYSTEM_CURSOR_CROSSHAIR
        self.blit_sequence = [
            (grid_img   , self.grid_rect   , self.layer),
            (minimap_img, self.minimap_rect, self.layer),
        ]

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self.selected_tiles.fill(False)
        self.refresh_grid_img()

    def resize(self: Self) -> None:
        """Resizes the object."""

        self.refresh_grid_img()
        self.refresh_minimap_img()

    def set_history_max_len(self: Self, n: int) -> None:
        """
        Sets the maximum history length and refresh the history index.

        Args:
            length
        """

        self.history = deque(self.history, n)
        self.history_i = min(self.history_i, len(self.history) - 1)

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
        self.visible_cols = min(visible_cols, self.cols)
        self.visible_rows = min(visible_rows, self.rows)
        self.offset_x = min(offset_x, self.cols - self.visible_cols)
        self.offset_y = min(offset_y, self.rows - self.visible_rows)

        self.selected_tiles = np.zeros((self.cols, self.rows), bool_)
        if should_reset_history:
            self.history.clear()
            self.history.append((self.cols, self.rows, compress(self.tiles.tobytes())))
            self.history_i = 0

    def refresh_grid_img(self: Self) -> None:
        """Refreshes the grid image from the unscaled minimap and draws the selected tiles."""

        selected_xs: NDArray[intp]
        selected_ys: NDArray[intp]

        selected_tiles_indexes: NDArray[intp] = np.flatnonzero(self.selected_tiles[
            self.offset_x:self.offset_x + self.visible_cols,
            self.offset_y:self.offset_y + self.visible_rows,
        ])
        selected_xs, selected_ys = np.divmod(selected_tiles_indexes, self.visible_rows)
        selected_xs += self.offset_x
        selected_ys += self.offset_y
        selected_xs *= TILE_W
        selected_ys *= TILE_H

        unscaled_minimap_img: Surface = (
            self._unscaled_minimap_img.copy() if selected_tiles_indexes.size > 250_000 else
            self._unscaled_minimap_img
        )

        # For every position get indexes of the TILE_WxTILE_H section as a 1D array
        repeated_cols: NDArray[uint8] = np.repeat(np.arange(TILE_W, dtype=uint8), TILE_H)
        repeated_rows: NDArray[uint8] = np.tile(  np.arange(TILE_H, dtype=uint8), TILE_W)
        xs: NDArray[intp] = (selected_xs[:, newaxis] + repeated_cols[newaxis, :]).ravel()
        ys: NDArray[intp] = (selected_ys[:, newaxis] + repeated_rows[newaxis, :]).ravel()

        # Faster
        selected_1d_indexes: NDArray[intp] = ys
        selected_1d_indexes *= (self.cols * TILE_W)
        selected_1d_indexes += xs

        color_range: NDArray[uint16] = np.arange(256, dtype=uint16)
        # Lookup table for every blend combination with gray (150, 150, 150, 128)
        a: int = 128
        blend_lut: NDArray[uint8] = (((150 * a) + (color_range * (255 - a))) >> 8).astype(uint8)

        unscaled_img_arr: NDArray[uint8] = surfarray.pixels3d(unscaled_minimap_img)
        # Fortran order avoids copying, reshaping a subsurface will always copy
        unscaled_img_arr = unscaled_img_arr.reshape(-1, 3, order="F")
        target_pixels: NDArray[uint8] = unscaled_img_arr[selected_1d_indexes]
        unscaled_img_arr[selected_1d_indexes] = blend_lut[target_pixels]

        # Better for scaling
        small_img: Surface = unscaled_minimap_img.subsurface(Rect(
            self.offset_x     * TILE_W, self.offset_y     * TILE_H,
            self.visible_cols * TILE_W, self.visible_rows * TILE_H,
        ))
        img: Surface = grid_resize(
            small_img, self.grid_rect, self._grid_init_pos,
            self.visible_cols, self.visible_rows,
            _GRID_DIM_CAP, transition_start=30, transition_end=165
        )
        init_tile_dim: float = _GRID_DIM_CAP / max(self.visible_cols, self.visible_rows)
        self.grid_tile_dim = init_tile_dim * my_vars.min_win_ratio

        if self.should_show_center:
            center: XY = (
                ceil((self.cols / 2 - self.offset_x) * self.grid_tile_dim),
                ceil((self.rows / 2 - self.offset_y) * self.grid_tile_dim),
            )
            grid_draw_center(img, center)
        self.blit_sequence[0] = (img.convert(), self.grid_rect, self.layer)

        if selected_tiles_indexes.size < 250_000:
            unscaled_img_arr[selected_1d_indexes] = target_pixels

    def refresh_minimap_img(self: Self) -> None:
        """Refreshes the minimap image scaled to minimap_rect and draws the indicator."""

        # Better for scaling
        img_arr: NDArray[uint8] = surfarray.pixels3d(self._unscaled_minimap_img)

        offset_x: int = self.offset_x * TILE_W
        offset_y: int = self.offset_y * TILE_H
        visible_cols: int = self.visible_cols * TILE_W
        visible_rows: int = self.visible_rows * TILE_H

        target_left_pixels: NDArray[uint8] = img_arr[
            offset_x:offset_x + TILE_W,
            offset_y:offset_y + visible_rows,
        ]
        target_top_pixels: NDArray[uint8] = img_arr[
            offset_x:offset_x + visible_cols,
            offset_y:offset_y + TILE_H,
        ]
        target_right_pixels: NDArray[uint8] = img_arr[
            offset_x + visible_cols - TILE_W:offset_x + visible_cols,
            offset_y:offset_y + visible_rows,
        ]
        target_bottom_pixels: NDArray[uint8] = img_arr[
            offset_x:offset_x + visible_cols,
            offset_y + visible_rows - TILE_H:offset_y + visible_rows,
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

        img: Surface = grid_resize(
            self._unscaled_minimap_img, self.minimap_rect,
            self._minimap_init_pos, self.cols, self.rows,
            _MINIMAP_DIM_CAP, transition_start=25, transition_end=130
        )
        init_tile_dim: float = _MINIMAP_DIM_CAP / max(self.cols, self.rows)
        tile_dim: float = init_tile_dim * my_vars.min_win_ratio

        if self.should_show_center:
            grid_draw_center(img, img.get_rect().center)
        if self.tile_mode_size is not None:
            grid_draw_tile_lines(img, self.tile_mode_size, tile_dim, offset_x=0, offset_y=0)
        self.blit_sequence[1] = (img.convert(), self.minimap_rect, self.layer)

        # Indicator is small, resetting changed pixels is faster than copy
        target_left_pixels[  ...] = src_left_pixels
        target_top_pixels[   ...] = src_top_pixels
        target_right_pixels[ ...] = src_right_pixels
        target_bottom_pixels[...] = src_bottom_pixels

    def refresh_full(self: Self) -> None:
        """Refreshes the grid, minimap and minimap rect."""

        # Repeats tiles so an empty tile image takes 1 normal-sized tile
        repeated_tiles: NDArray[uint8] = self.tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_tiles_mask: NDArray[bool_] = (repeated_tiles[..., 3] == 0)[..., newaxis]

        empty_img_arr: NDArray[uint8] = np.tile(EMPTY_TILE_ARR, (self.cols, self.rows, 1))
        rgb_repeated_tiles: NDArray[uint8] = repeated_tiles[..., :3]
        img_arr: NDArray[uint8] = np.where(empty_tiles_mask, empty_img_arr, rgb_repeated_tiles)
        self._unscaled_minimap_img = surfarray.make_surface(img_arr)

        self.refresh_grid_img()
        self.refresh_minimap_img()

    def set_tiles(self: Self, img: Surface | None) -> None:
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
            max_w: int = self.grid_rect.w - 1
            max_h: int = self.grid_rect.h -1
            rel_mouse_x: int = _get_rel_mouse_coord(rel_mouse_col, prev_rel_mouse_col, max_w)
            rel_mouse_y: int = _get_rel_mouse_coord(rel_mouse_row, prev_rel_mouse_row, max_h)

            MOUSE.x, MOUSE.y = self.grid_rect.x + rel_mouse_x, self.grid_rect.y + rel_mouse_y
            mouse.set_pos(MOUSE.x, MOUSE.y)

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
            self: Self, amount: int,
            should_reach_min_limit: bool, should_reach_max_limit: bool
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
            self.grid_tile_dim = init_tile_dim * my_vars.min_win_ratio

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
        Updates the changed tiles and refreshes the unscaled minimap.

        Args:
            erasing flag, hexadecimal color
        Returns:
            drawn flag
        """

        selected_xs: NDArray[intp]
        selected_ys: NDArray[intp]

        rgba_color: NDArray[uint8] = np.array(
            (0, 0, 0, 0) if is_erasing else Color("#" + hex_color),
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
            xs: NDArray[intp] = (selected_xs[:, newaxis] + repeated_cols[newaxis, :]).ravel()
            ys: NDArray[intp] = (selected_ys[:, newaxis] + repeated_rows[newaxis, :]).ravel()

            # Faster
            selected_1d_indexes: NDArray[intp] = ys.copy()
            selected_1d_indexes *= (self.cols * TILE_W)
            selected_1d_indexes += xs

            unscaled_img_arr: NDArray[uint8] = surfarray.pixels3d(self._unscaled_minimap_img)
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

    def add_to_history(self: Self) -> None:
        """Adds the current info to the history if different from the last snapshot."""

        snapshot: _HistorySnapshot = (self.cols, self.rows, compress(self.tiles.tobytes()))
        if snapshot != self.history[self.history_i]:
            if self.history_i != (len(self.history) - 1):
                end_i: int = self.history_i + 1
                history_sl: islice[_HistorySnapshot] = islice(self.history, end_i)
                self.history.clear()
                self.history.extend(history_sl)
            self.history.append(snapshot)
            self.history_i = min(self.history_i + 1, len(self.history) - 1)

    def try_save(
            self: Self, file_str: str,
            should_ask_create_dir: bool, should_use_gui: bool = True
    ) -> Surface | None:
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

        pg_img: Surface = Surface((self.cols, self.rows), SRCALPHA)
        surfarray.blit_array(pg_img, self.tiles[..., :3])
        surfarray.pixels_alpha(pg_img)[...] = self.tiles[..., 3]
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
                    try_lock_file(f, should_be_shared=False)
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
