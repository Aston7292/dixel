"""
Paintable pixel grid with a minimap.

Grid and minimap are refreshed automatically when offset or visible area changes.
"""

from tkinter import messagebox
from pathlib import Path
from zlib import compress, decompress
from collections import deque
from itertools import islice
from io import BytesIO
from typing import Literal, TypeAlias, Final, Any

import pygame as pg
from pygame.locals import *
import numpy as np
from numpy import uint8, uint16, uint32, intp, bool_
from numpy.typing import NDArray
import cv2

from src.classes.tools_manager import ToolInfo
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import (
    UIElement, Point, RectPos, Size, ObjInfo,
    get_pixels, try_write_file, handle_file_os_error, try_create_dir, resize_obj, rec_move_rect,
)
from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import XY, WH, RGBColor, HexColor, BlitInfo
import src.vars as VARS
from src.consts import (
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT,
    BLACK,
    EMPTY_TILE_ARR, TILE_H, TILE_W,
    FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I,
    BG_LAYER, TOP_LAYER,
)


_BucketStack: TypeAlias = list[tuple[uint16, tuple[uint16, uint16]]]

_GRID_INIT_VISIBLE_DIM: Final[int] = 32
_GRID_DIM_CAP: Final[int] = 600
_MINIMAP_DIM_CAP: Final[int] = 256
GRID_TRANSITION_START: Final[int] = 32
GRID_TRANSITION_END: Final[int]   = 200


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
        rel_mouse_coord: int, step: int, offset: int, visible_side: int, side: int
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


def _get_tiles_in_line(x_1: int, y_1: int, x_2: int, y_2: int) -> list[XY]:
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
    step_x: Literal[1, -1] = 1 if x_1 < x_2 else -1
    step_y: Literal[1, -1] = 1 if y_1 < y_2 else -1

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

    return tiles


class Grid:
    """Class to create a pixel grid and its minimap."""

    __slots__ = (
        "_grid_init_pos", "area", "visible_area", "grid_tile_dim", "grid_rect",
        "tiles", "brush_dim", "history", "history_i",
        "_minimap_init_pos", "minimap_rect",
        "_unscaled_minimap_img", "offset", "selected_tiles",
        "hover_rects", "layer", "blit_sequence", "_win_w_ratio", "_win_h_ratio",
    )

    cursor_type: int = SYSTEM_CURSOR_CROSSHAIR
    objs_info: list[ObjInfo] = []

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the grid and minimap.

        Args:
            grid position, minimap position
        """

        # Tiles dimensions are floats to represent the full size more accurately when resizing

        self._grid_init_pos: RectPos = grid_pos

        self.area: Size = Size(64, 64)
        self.visible_area: Size = Size(_GRID_INIT_VISIBLE_DIM, _GRID_INIT_VISIBLE_DIM)
        self.grid_tile_dim: float = _GRID_DIM_CAP / _GRID_INIT_VISIBLE_DIM

        grid_img: pg.Surface = pg.Surface((_GRID_DIM_CAP, _GRID_DIM_CAP))
        self.grid_rect: pg.Rect = pg.Rect(0, 0, *grid_img.get_size())
        grid_init_xy: XY = (self._grid_init_pos.x, self._grid_init_pos.y)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, grid_init_xy)

        self.tiles: NDArray[uint8] = np.zeros((self.area.w, self.area.h, 4), uint8)
        self.brush_dim: int = 1
        compressed_tiles: bytes = compress(self.tiles.tobytes())
        self.history: deque[tuple[int, int, bytes]] = deque(
            [(self.area.w, self.area.h, compressed_tiles)], 512
        )
        self.history_i: int = 0

        self._minimap_init_pos: RectPos = minimap_pos

        minimap_img: pg.Surface = pg.Surface((_MINIMAP_DIM_CAP, _MINIMAP_DIM_CAP))
        self.minimap_rect: pg.Rect = pg.Rect(0, 0, *minimap_img.get_size())
        minimap_init_xy: XY = (self._minimap_init_pos.x, self._minimap_init_pos.y)
        setattr(self.minimap_rect, self._minimap_init_pos.coord_type, minimap_init_xy)

        # Better for scaling
        unscaled_wh: WH = (self.tiles.shape[0], self.tiles.shape[1])
        self._unscaled_minimap_img: pg.Surface = pg.Surface(unscaled_wh)
        self.offset: Point = Point(0, 0)
        self.selected_tiles: NDArray[bool_] = np.zeros((self.area.w, self.area.h), bool_)

        self.hover_rects: list[pg.Rect] = [self.grid_rect]
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = [
            (grid_img   , self.grid_rect   , self.layer),
            (minimap_img, self.minimap_rect, self.layer),
        ]
        self._win_w_ratio: float = 1
        self._win_h_ratio: float = 1

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

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
            self, tiles: NDArray[uint8], visible_w: int, visible_h: int,
            offset_x: int, offset_y: int, should_reset_history: bool
    ) -> None:
        """
        Sets the tiles, area, visible area and offset without refreshing.

        Args:
            tiles, visible columns, visible rows, x offset, y offset, reset history flag
        """

        self.tiles = tiles
        self.area.w, self.area.h = self.tiles.shape[0], self.tiles.shape[1]
        self.selected_tiles = np.zeros((self.area.w, self.area.h), bool_)

        self.visible_area.w = min(visible_w, self.area.w)
        self.visible_area.h = min(visible_h, self.area.h)
        self.offset.x = min(offset_x, self.area.w - self.visible_area.w)
        self.offset.y = min(offset_y, self.area.h - self.visible_area.h)

        if should_reset_history:
            compressed_tiles: bytes = compress(self.tiles.tobytes())
            self.history = deque([(self.area.w, self.area.h, compressed_tiles)], 512)
            self.history_i = 0

    def _resize_grid(self, unscaled_img: pg.Surface) -> None:
        """
        Resizes the unscaled grid with a gradual blur.

        Args:
            unscaled grid image
        """

        xy: XY
        w: int
        h: int
        img: pg.Surface

        init_tile_dim: float = _GRID_DIM_CAP / max(self.visible_area.w, self.visible_area.h)
        self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)
        xy, (w, h) = resize_obj(
            self._grid_init_pos,
            self.visible_area.w * init_tile_dim, self.visible_area.h * init_tile_dim,
            self._win_w_ratio, self._win_h_ratio, True
        )

        max_visible_dim: int = max(self.visible_area.w, self.visible_area.h)
        if   max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(      unscaled_img, (w, h))
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(unscaled_img, (w, h))
        elif GRID_TRANSITION_START <= max_visible_dim <= GRID_TRANSITION_END:
            # Gradual transition
            img_arr: NDArray[uint8] = pg.surfarray.pixels3d(unscaled_img)
            img_arr = cv2.resize(img_arr, (h, w), interpolation=cv2.INTER_AREA).astype(uint8)
            img = pg.surfarray.make_surface(img_arr)

        self.grid_rect.size = (w, h)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, xy)

        self.blit_sequence[0] = (img.convert(), self.grid_rect, self.layer)

    def refresh_grid_img(self) -> None:
        """Refreshes the grid image from the small minimap and draws the selected tiles."""

        selected_tiles_xs: NDArray[intp]
        selected_tiles_ys: NDArray[intp]
        target_xs: NDArray[intp]
        target_ys: NDArray[intp]

        rect: pg.Rect = pg.Rect(
            self.offset.x       * TILE_W, self.offset.y       * TILE_H,
            self.visible_area.w * TILE_W, self.visible_area.h * TILE_H,
        )
        visible_selected_tiles: NDArray[bool_] = self.selected_tiles[
            self.offset.x:self.offset.x + self.visible_area.w,
            self.offset.y:self.offset.y + self.visible_area.h,
        ]

        selected_tiles_xs, selected_tiles_ys = np.nonzero(visible_selected_tiles)
        selected_tiles_xs *= TILE_W
        selected_tiles_ys *= TILE_H

        # Having a version where 1 tile = 1 pixel is better for scaling
        img: pg.Surface = self._unscaled_minimap_img.subsurface(rect)
        if selected_tiles_xs.size > 14_000:
            # On small amounts it's faster to not copy and restore after resize
            img = img.copy()

        # For every position get indexes of the TILE_WxTILE_H slice as a 1D array
        repeated_cols: NDArray[uint8] = np.repeat(np.arange(TILE_W, dtype=uint8), TILE_H)
        repeated_rows: NDArray[uint8] = np.tile(  np.arange(TILE_H, dtype=uint8), TILE_W)

        target_xs = (selected_tiles_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]).ravel()
        target_ys = (selected_tiles_ys[:, np.newaxis] + repeated_rows[np.newaxis, :]).ravel()

        color_range: NDArray[uint16] = np.arange(256, dtype=uint16)
        # Lookup table for every blend combination with gray (150, 150, 150, 128)
        a: int = 128
        blend_lut: NDArray[uint8] = (((150 * a) + (color_range * (255 - a))) >> 8).astype(uint8)

        unscaled_img_arr: NDArray[uint8] = pg.surfarray.pixels3d(img)
        target_pixels: NDArray[uint8] = unscaled_img_arr[target_xs, target_ys]
        unscaled_img_arr[target_xs, target_ys] = blend_lut[target_pixels]
        self._resize_grid(img)
        if selected_tiles_xs.size <= 14_000:
            unscaled_img_arr[target_xs, target_ys] = target_pixels

    def _refresh_minimap_rect(self) -> None:
        """Refreshes the minimap rect."""

        init_tile_dim: float = _MINIMAP_DIM_CAP / max(self.area.w, self.area.h)
        xy, self.minimap_rect.size = resize_obj(
            self._minimap_init_pos,
            self.area.w * init_tile_dim, self.area.h * init_tile_dim,
            self._win_w_ratio, self._win_h_ratio, True
        )
        setattr(self.minimap_rect, self._minimap_init_pos.coord_type, xy)

    def _resize_minimap(self) -> None:
        """Resizes the small minimap with a gradual blur."""

        img: pg.Surface

        max_visible_dim: int = max(self.area.w, self.area.h)
        if   max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(      self._unscaled_minimap_img, self.minimap_rect.size)
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(self._unscaled_minimap_img, self.minimap_rect.size)
        elif GRID_TRANSITION_START <= max_visible_dim <= GRID_TRANSITION_END:
            # Gradual transition
            img_arr: NDArray[uint8] = pg.surfarray.pixels3d(self._unscaled_minimap_img)
            wh: WH = (self.minimap_rect.h, self.minimap_rect.w)
            img_arr = cv2.resize(img_arr, wh, interpolation=cv2.INTER_AREA).astype(uint8)
            img = pg.surfarray.make_surface(img_arr)

        self.blit_sequence[1] = (img.convert(), self.minimap_rect, self.layer)

    def refresh_minimap_img(self) -> None:
        """Refreshes the minimap image scaled to minimap_rect and draws the indicator."""

        # Having a version where 1 tile = 1 pixel is better for scaling
        img_arr: NDArray[uint8] = pg.surfarray.pixels3d(self._unscaled_minimap_img)

        offset_x: int  = self.offset.x       * TILE_W
        offset_y: int  = self.offset.y       * TILE_H
        visible_w: int = self.visible_area.w * TILE_W
        visible_h: int = self.visible_area.h * TILE_H

        top_x_sl: slice = slice(offset_x, offset_x + visible_w)
        top_y_sl: slice = slice(offset_y, offset_y + TILE_H)
        target_top_pixels: NDArray[uint8]    = img_arr[top_x_sl, top_y_sl]

        right_x_sl: slice = slice(offset_x + visible_w - TILE_W, offset_x + visible_w)
        right_y_sl: slice = slice(offset_y, offset_y + visible_h)
        target_right_pixels: NDArray[uint8]  = img_arr[right_x_sl, right_y_sl]

        bottom_x_sl: slice = top_x_sl
        bottom_y_sl: slice = slice(offset_y + visible_h - TILE_H, offset_y + visible_h)
        target_bottom_pixels: NDArray[uint8] = img_arr[bottom_x_sl, bottom_y_sl]

        left_x_sl: slice = slice(offset_x, offset_x + TILE_W)
        left_y_sl: slice = right_y_sl
        target_left_pixels: NDArray[uint8]   = img_arr[left_x_sl, left_y_sl]

        src_top_pixels: NDArray[uint8]    = target_top_pixels.copy()
        src_right_pixels: NDArray[uint8]  = target_right_pixels.copy()
        src_bottom_pixels: NDArray[uint8] = target_bottom_pixels.copy()
        src_left_pixels: NDArray[uint8]   = target_left_pixels.copy()

        color_range: NDArray[uint16] = np.arange(256, dtype=uint16)
        # Lookup table for every blend combination with gray (150, 150, 150, 128)
        a: int = 128
        blend_lut: NDArray[uint8] = (((150 * a) + (color_range * (255 - a))) >> 8).astype(uint8)
        target_top_pixels   [...] = blend_lut[target_top_pixels]
        target_right_pixels [...] = blend_lut[target_right_pixels]
        target_bottom_pixels[...] = blend_lut[target_bottom_pixels]
        target_left_pixels  [...] = blend_lut[target_left_pixels]

        self._resize_minimap()
        # Indicator is small, resetting changed pixels is faster than copy
        target_top_pixels   [...] = src_top_pixels
        target_right_pixels [...] = src_right_pixels
        target_bottom_pixels[...] = src_bottom_pixels
        target_left_pixels  [...] = src_left_pixels

    def refresh_full(self) -> None:
        """Refreshes the tiles on the minimap, its rect and retrieves the grid."""

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        repeated_tiles: NDArray[uint8] = self.tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_img_arr: NDArray[uint8] = np.tile(EMPTY_TILE_ARR, (self.area.w, self.area.h, 1))
        empty_tiles_mask: NDArray[bool_] = (repeated_tiles[..., 3] == 0)[..., np.newaxis]

        rgb_repeated_tiles: NDArray[uint8] = repeated_tiles[..., :3]
        img_arr: NDArray[uint8] = np.where(empty_tiles_mask, empty_img_arr, rgb_repeated_tiles)
        self._unscaled_minimap_img = pg.surfarray.make_surface(img_arr)

        self.refresh_grid_img()
        self._refresh_minimap_rect()
        self.refresh_minimap_img()

    # TODO: reset history on image load
    def set_tiles(self, img: pg.Surface | None) -> None:
        """
        Sets the grid tiles using an image pixels.

        Args:
            image (if None it creates an empty grid)
        """

        if img is None:
            self.tiles = np.zeros((self.area.w, self.area.h, 4), uint8)
        else:
            self.tiles = get_pixels(img)

            extra_w: int = self.area.w - self.tiles.shape[0]
            if   extra_w < 0:
                self.tiles = self.tiles[:self.area.w, ...]
            elif extra_w > 0:
                padding_w: tuple[WH, WH, WH] = ((0, extra_w), (0, 0      ), (0, 0))
                self.tiles = np.pad(self.tiles, padding_w, constant_values=0)

            extra_h: int = self.area.h - self.tiles.shape[1]
            if   extra_h < 0:
                self.tiles = self.tiles[:, :self.area.h, ...]
            elif extra_h > 0:
                padding_h: tuple[WH, WH, WH] = ((0, 0      ), (0, extra_h), (0, 0))
                self.tiles = np.pad(self.tiles, padding_h, constant_values=0)

        compressed_tiles: bytes = compress(self.tiles.tobytes())
        self.history = deque([(self.area.w, self.area.h, compressed_tiles)], 512)
        self.history_i = 0

        self.refresh_full()

    def move_with_keys(self, rel_mouse_col: int, rel_mouse_row: int) -> XY:
        """
        Moves the mouse tile with the keyboard.

        Args:
            relative mouse column, relative mouse row
        Returns:
            relative mouse column, relative mouse row
        """

        direction: Literal[1, -1]

        prev_rel_mouse_col: int = rel_mouse_col
        prev_rel_mouse_row: int = rel_mouse_row

        step: int = 1
        if KEYBOARD.is_shift_on:
            if K_LEFT in KEYBOARD.timed or K_RIGHT in KEYBOARD.timed:
                step = self.visible_area.w
            else:
                step = self.visible_area.h
        if K_TAB in KEYBOARD.pressed:
            step = self.brush_dim

        if K_LEFT  in KEYBOARD.timed:
            rel_mouse_col, self.offset.x = _dec_mouse_tile(
                rel_mouse_col, step, self.offset.x
            )
        if K_RIGHT in KEYBOARD.timed:
            rel_mouse_col, self.offset.x = _inc_mouse_tile(
                rel_mouse_col, step, self.offset.x, self.visible_area.w, self.area.w
            )
        if K_UP    in KEYBOARD.timed:
            rel_mouse_row, self.offset.y = _dec_mouse_tile(
                rel_mouse_row, step, self.offset.y
            )
        if K_DOWN  in KEYBOARD.timed:
            rel_mouse_row, self.offset.y = _inc_mouse_tile(
                rel_mouse_row, step, self.offset.y, self.visible_area.h, self.area.h
            )

        if rel_mouse_col != prev_rel_mouse_col or rel_mouse_row != prev_rel_mouse_row:
            half_tile_dim: float = self.grid_tile_dim / 2  # Mouse is in the center of the tile

            rel_mouse_x: int = round((rel_mouse_col * self.grid_tile_dim) + half_tile_dim)
            if rel_mouse_col != prev_rel_mouse_col:
                prev_rel_mouse_x: int = round(prev_rel_mouse_col * self.grid_tile_dim)
                if rel_mouse_x == prev_rel_mouse_x:  # Grid is so large that mouse x stays the same
                    direction = 1 if rel_mouse_col > prev_rel_mouse_col else -1
                    rel_mouse_x = min(max(rel_mouse_x + direction, 0), self.grid_rect.w - 1)

            rel_mouse_y: int = round((rel_mouse_row * self.grid_tile_dim) + half_tile_dim)
            if rel_mouse_row != prev_rel_mouse_row:
                prev_rel_mouse_y: int = round(prev_rel_mouse_row * self.grid_tile_dim)
                if rel_mouse_y == prev_rel_mouse_y:  # Grid is so large that mouse y stays the same
                    direction = 1 if rel_mouse_row > prev_rel_mouse_row else -1
                    rel_mouse_y = min(max(rel_mouse_y + direction, 0), self.grid_rect.h - 1)

            MOUSE.x, MOUSE.y = self.grid_rect.x + rel_mouse_x, self.grid_rect.y + rel_mouse_y
            pg.mouse.set_pos(MOUSE.x, MOUSE.y)

        return rel_mouse_col, rel_mouse_row

    def _dec_largest_side(self, amount: int) -> None:
        """
        Decreases the largest side of the visible area.

        Args:
            amount
        """

        if   self.visible_area.w > self.visible_area.h:
            self.visible_area.w = max(self.visible_area.w - amount, 1)
            self.visible_area.h = min(self.visible_area.h, self.visible_area.w)
        elif self.visible_area.h > self.visible_area.w:
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
            self.visible_area.w = min(self.visible_area.w + amount, self.area.w)
            self.visible_area.h = max(self.visible_area.h, min(self.visible_area.w, self.area.h))
        else:
            self.visible_area.h = min(self.visible_area.h + amount, self.area.h)
            self.visible_area.w = max(self.visible_area.w, min(self.visible_area.h, self.area.w))

    def _zoom_visible_area(
            self, amount: int, should_reach_min_limit: bool, should_reach_max_limit: bool
    ) -> None:
        """
        Zooms the visible area.

        Args:
            amount, reach minimum limit flag, reach maximum limit flag
        """

        # amount: wheel down (-), wheel up (+)

        if   should_reach_min_limit:
            self.visible_area.w = self.visible_area.h = 1
        elif should_reach_max_limit:
            self.visible_area.w, self.visible_area.h = self.area.w, self.area.h
        elif self.visible_area.w == self.visible_area.h:
            self.visible_area.w = min(max(self.visible_area.w - amount, 1), self.area.w)
            self.visible_area.h = min(max(self.visible_area.h - amount, 1), self.area.h)
        elif amount > 0:
            self._dec_largest_side(  amount)
        elif amount < 0:
            self._inc_smallest_side(-amount)

    def zoom(self) -> None:
        """Zooms the grid in or out."""

        amount: int = 0
        should_reach_min_limit: bool = False
        should_reach_max_limit: bool = False

        if MOUSE.scroll_amount != 0:
            # Amount depends on zoom level
            uncapped_amount: int = int(MOUSE.scroll_amount * (25 / self.grid_tile_dim))
            if uncapped_amount == 0:
                uncapped_amount = 1 if MOUSE.scroll_amount > 0 else -1
            amount = min(max(uncapped_amount, -100), 100)

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
            init_tile_dim: float = _GRID_DIM_CAP / max(self.visible_area.w, self.visible_area.h)
            self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)

            mouse_col: int = int((MOUSE.x - self.grid_rect.x) / self.grid_tile_dim)
            mouse_row: int = int((MOUSE.y - self.grid_rect.y) / self.grid_tile_dim)

            self.offset.x += prev_mouse_col - mouse_col
            self.offset.x = min(max(self.offset.x, 0), self.area.w - self.visible_area.w)
            self.offset.y += prev_mouse_row - mouse_row
            self.offset.y = min(max(self.offset.y, 0), self.area.h - self.visible_area.h)

    def add_to_history(self) -> None:
        """Adds the current info to the history if different from the last snapshot."""

        snapshot: tuple[int, int, bytes] = (self.area.w, self.area.h, compress(self.tiles.tobytes()))
        if snapshot != self.history[self.history_i]:
            if self.history_i != (len(self.history) - 1):
                history_sl: islice[tuple[int, int, bytes]] = islice(self.history, self.history_i + 1)
                self.history = deque(history_sl, 512)
            self.history.append(snapshot)
            self.history_i += 1

    def upt_section(self, is_coloring: bool, hex_color: HexColor) -> bool:
        """
        Updates the changed tiles and refreshes the small minimap.

        Args:
            coloring flag, hexadecimal color
        Returns:
            drawed flag
        """

        rgba_color: tuple[int, int, int, int]
        selected_tiles_xs: NDArray[intp]
        selected_tiles_ys: NDArray[intp]
        target_xs: NDArray[intp]
        target_ys: NDArray[intp]

        prev_tiles: NDArray[uint8] = self.tiles[self.selected_tiles].copy()

        if is_coloring:
            rgba_color = (
                int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), 255
            )
        else:  # is_erasing
            rgba_color = (0, 0, 0, 0)
        self.tiles[self.selected_tiles] = rgba_color

        did_draw: bool = not np.array_equal(self.tiles[self.selected_tiles], prev_tiles)
        if did_draw:
            img_arr: NDArray[uint8] = pg.surfarray.pixels3d(self._unscaled_minimap_img)

            selected_tiles_xs, selected_tiles_ys = np.nonzero(self.selected_tiles)
            selected_tiles_xs *= TILE_W
            selected_tiles_ys *= TILE_H

            # For every position get indexes of the TILE_WxTILE_H slice as a 1D array
            repeated_cols: NDArray[uint8] = np.repeat(np.arange(TILE_W, dtype=uint8), TILE_H)
            repeated_rows: NDArray[uint8] = np.tile(  np.arange(TILE_H, dtype=uint8), TILE_W)

            target_xs = (selected_tiles_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]).ravel()
            target_ys = (selected_tiles_ys[:, np.newaxis] + repeated_rows[np.newaxis, :]).ravel()
            img_arr[target_xs, target_ys] = (
                rgba_color[:3] if is_coloring else
                EMPTY_TILE_ARR[target_xs % TILE_W, target_ys % TILE_H]
            )

        return did_draw

    def try_save_to_file(self, file_str: str, should_ask_create_dir: bool) -> pg.Surface | None:
        """
        Saves the image to a file with retries.

        Args:
            file string, ask dir creation flag
        Returns:
            image (can be None)
        """

        error_str: str
        should_retry: bool

        if file_str == "":
            return None

        img: pg.Surface = pg.Surface((self.area.w, self.area.h), SRCALPHA)
        pg.surfarray.blit_array(  img,        self.tiles[..., :3])
        pg.surfarray.pixels_alpha(img)[...] = self.tiles[...,  3]

        file_path: Path = Path(file_str)
        did_succeed: bool = False

        dummy_file: BytesIO = BytesIO()
        pg.image.save(img, dummy_file, file_path.name)
        img_bytes: bytes = dummy_file.getvalue()

        dir_creation_attempt_i: int = FILE_ATTEMPT_START_I
        system_attempt_i: int       = FILE_ATTEMPT_START_I
        while (
            dir_creation_attempt_i <= FILE_ATTEMPT_STOP_I and
            system_attempt_i       <= FILE_ATTEMPT_STOP_I
        ):
            try:
                # If you open in write mode it will empty the file even if it's locked
                with file_path.open("ab") as f:
                    try_lock_file(f, False)
                    try_write_file(f, img_bytes)
                did_succeed = True
                break
            except FileNotFoundError:
                dir_creation_attempt_i += 1
                did_fail: bool = try_create_dir(
                    file_path.parent, should_ask_create_dir, dir_creation_attempt_i
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
            except OSError as e:
                system_attempt_i += 1
                error_str, should_retry = handle_file_os_error(e)
                if should_retry and system_attempt_i != FILE_ATTEMPT_STOP_I:
                    pg.time.wait(2 ** system_attempt_i)
                    continue

                messagebox.showerror("Image Save Failed", f"{file_path.name}\n{error_str}")
                break

        return img if did_succeed else None


class GridManager:
    """Class to create and edit a grid of pixels."""

    __slots__ = (
        "_is_hovering", "_prev_hovered_obj", "_can_leave",
        "_prev_mouse_col", "_prev_mouse_row", "_mouse_col", "_mouse_row",
        "_traveled_x", "_traveled_y",
        "_is_coloring", "_is_erasing", "is_x_mirror_on", "is_y_mirror_on",
        "eye_dropped_color", "_can_add_to_history",
        "grid", "_hovering_text_label", "_hovering_text_label_obj_info", "_hovering_text_alpha", "_last_mouse_move_time",
        "hover_rects", "layer", "blit_sequence", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object and wrapper info.

        Args:
            grid position, minimap position
        """

        img: pg.Surface

        self._is_hovering: bool = False
        self._prev_hovered_obj: UIElement | None = MOUSE.hovered_obj
        self._can_leave: bool = False

        # Used to avoid passing parameters
        self._prev_mouse_col: int = 0
        self._prev_mouse_row: int = 0
        self._mouse_col: int      = 0
        self._mouse_row: int      = 0

        self._traveled_x: float = 0
        self._traveled_y: float = 0

        # Used to avoid passing parameters
        self._is_coloring: bool = False
        self._is_erasing: bool  = False
        self.is_x_mirror_on: bool = False
        self.is_y_mirror_on: bool = False
        self.eye_dropped_color: RGBColor | None = None

        self._can_add_to_history: bool = False

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self._hovering_text_label: TextLabel = TextLabel(
            RectPos(MOUSE.x, MOUSE.y, "topleft"),
            "Enter\nBackspace", BG_LAYER, 12, BLACK
        )
        self._hovering_text_label.layer = TOP_LAYER
        self._hovering_text_label_obj_info: ObjInfo = ObjInfo(self._hovering_text_label)
        self._hovering_text_alpha: int = 0
        self._last_mouse_move_time: int = VARS.ticks

        for img in self._hovering_text_label.imgs:
            img.set_alpha(self._hovering_text_alpha)
        self._hovering_text_label_obj_info.rec_set_active(False)

        self.hover_rects: list[pg.Rect] = []
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid), self._hovering_text_label_obj_info]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._last_mouse_move_time = VARS.ticks

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._is_hovering = False
        self._prev_hovered_obj = None
        self._can_leave = False
        self._traveled_x = self._traveled_y = 0
        self.eye_dropped_color = None

        if self._can_add_to_history:
            self.grid.add_to_history()
            self._can_add_to_history = False

        # Modifying alpha values is unnecessary
        self._hovering_text_alpha = 0
        self._hovering_text_label_obj_info.rec_set_active(False)

    def resize(self, _win_w_ratio: float, _win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        img: pg.Surface

        for img in self._hovering_text_label.imgs:
            img.set_alpha(self._hovering_text_alpha)

    def _move(self) -> None:
        """Moves the visible section, it's faster when moving the mouse faster."""

        tiles_traveled: int

        speed_x: float = abs(MOUSE.prev_x - MOUSE.x) ** 1.25
        if MOUSE.x > MOUSE.prev_x:
            speed_x = -speed_x
        self._traveled_x += speed_x

        speed_y: float = abs(MOUSE.prev_y - MOUSE.y) ** 1.25
        if MOUSE.y > MOUSE.prev_y:
            speed_y = -speed_y
        self._traveled_y += speed_y

        if abs(self._traveled_x) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_x / self.grid.grid_tile_dim)
            self._traveled_x -= tiles_traveled * self.grid.grid_tile_dim

            max_offset_x: int = self.grid.area.w - self.grid.visible_area.w
            self.grid.offset.x = min(max(self.grid.offset.x + tiles_traveled, 0), max_offset_x)

        if abs(self._traveled_y) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_y / self.grid.grid_tile_dim)
            self._traveled_y -= tiles_traveled * self.grid.grid_tile_dim

            max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
            self.grid.offset.y = min(max(self.grid.offset.y + tiles_traveled, 0), max_offset_y)

    def _move_history_i(self) -> bool:
        """
        Changes the index of the viewed history snapshot with the keyboard.

        Returns:
            changed flag
        """

        prev_history_i: int = self.grid.history_i

        max_history_i: int = len(self.grid.history) - 1
        if K_z in KEYBOARD.timed:
            move_sign: Literal[1, -1] = 1 if KEYBOARD.is_shift_on else -1
            self.grid.history_i = min(max(self.grid.history_i + move_sign, 0), max_history_i)
        if K_y in KEYBOARD.timed:
            self.grid.history_i = min(self.grid.history_i + 1                , max_history_i)

        if self.grid.history_i != prev_history_i:
            grid_w: int             = self.grid.history[self.grid.history_i][0]
            grid_h: int             = self.grid.history[self.grid.history_i][1]
            compressed_tiles: bytes = self.grid.history[self.grid.history_i][2]
            # copy makes it writable
            tiles_1d: NDArray[uint8] = np.frombuffer(decompress(compressed_tiles), uint8).copy()
            self.grid.set_info(
                tiles_1d.reshape((grid_w, grid_h, 4)),
                self.grid.visible_area.w, self.grid.visible_area.h,
                self.grid.offset.x, self.grid.offset.y,
                False,
            )
            self.grid.refresh_full()

        return self.grid.history_i != prev_history_i

    def _handle_tile_info(self) -> None:
        """Calculates previous and current mouse tiles and handles keyboard movement."""

        grid_tile_dim: float = self.grid.grid_tile_dim
        prev_rel_mouse_col: int = int((MOUSE.prev_x - self.grid.grid_rect.x) / grid_tile_dim)
        prev_rel_mouse_row: int = int((MOUSE.prev_y - self.grid.grid_rect.y) / grid_tile_dim)
        rel_mouse_col: int      = int((MOUSE.x      - self.grid.grid_rect.x) / grid_tile_dim)
        rel_mouse_row: int      = int((MOUSE.y      - self.grid.grid_rect.y) / grid_tile_dim)

        # By setting prev_mouse_tile before changing offset you can draw a line with shift/ctrl
        self._prev_mouse_col = prev_rel_mouse_col + self.grid.offset.x
        self._prev_mouse_row = prev_rel_mouse_row + self.grid.offset.y

        if KEYBOARD.timed != []:
            # Changes the offset
            rel_mouse_col, rel_mouse_row = self.grid.move_with_keys(rel_mouse_col, rel_mouse_row)

        self._mouse_col      = rel_mouse_col      + self.grid.offset.x
        self._mouse_row      = rel_mouse_row      + self.grid.offset.y

    def _pencil(self) -> None:
        """Handles the pencil tool."""

        w_edge: int = self.grid.area.w - 1
        h_edge: int = self.grid.area.h - 1
        brush_dim: int = self.grid.brush_dim

        # Center tiles to the cursor
        selected_tiles_list: list[XY] = _get_tiles_in_line(
            min(max(self._prev_mouse_col, 0), w_edge) - (brush_dim // 2),
            min(max(self._prev_mouse_row, 0), h_edge) - (brush_dim // 2),
            min(max(self._mouse_col     , 0), w_edge) - (brush_dim // 2),
            min(max(self._mouse_row     , 0), h_edge) - (brush_dim // 2),
        )

        selected_tiles_list = [
            (x, y)
            for original_x, original_y in selected_tiles_list
            for x in range(max(original_x, 0), min(original_x + brush_dim, self.grid.area.w))
            for y in range(max(original_y, 0), min(original_y + brush_dim, self.grid.area.h))
        ]

        if self.is_x_mirror_on:
            selected_tiles_list.extend([(w_edge - x, y         ) for x, y in selected_tiles_list])
        if self.is_y_mirror_on:
            selected_tiles_list.extend([(x         , h_edge - y) for x, y in selected_tiles_list])
        self.grid.selected_tiles[*zip(*selected_tiles_list)] = True

    def _init_bucket_stack(self, mask: NDArray[bool_]) -> _BucketStack:
        """
        Initializes the stack for the bucket tool.

        Args:
            tiles mask
        Returns:
            stack
        """

        up_tiles: NDArray[bool_]   = mask[self._mouse_col, :self._mouse_row + 1]
        up_stop: int | intp   = up_tiles[::-1].argmin()
        if up_stop == 0:
            up_stop   = up_tiles.size
        first_y: uint16 = uint16(self._mouse_row - up_stop + 1)

        down_tiles: NDArray[bool_] = mask[self._mouse_col, self._mouse_row:]
        down_stop: int | intp = down_tiles.argmin()
        if down_stop == 0:
            down_stop = down_tiles.size
        last_y: uint16  = uint16(self._mouse_row + down_stop - 1)

        x: uint16 = uint16(self._mouse_col)
        return [(x, (first_y, last_y))]

    def _bucket(self, extra_info: dict[str, Any]) -> None:
        """
        Handles the bucket tool using the scan-line algorithm, includes a color fill.

        Args:
            extra info (color fill)
        """

        x: uint16
        start_y: uint16
        end_y: uint16

        if (
            (self._mouse_col < 0 or self._mouse_col >= self.grid.area.w) or
            (self._mouse_row < 0 or self._mouse_row >= self.grid.area.h)
        ):
            return

        selected_tiles: NDArray[bool_] = self.grid.selected_tiles

        # Pack a color as a uint32 and compare
        color: NDArray[uint8] = self.grid.tiles[self._mouse_col, self._mouse_row]
        mask: NDArray[bool_] = self.grid.tiles.view(uint32)[..., 0] == color.view(uint32)[0]
        if extra_info["color_fill"]:
            selected_tiles[mask] = True
            return

        stack: _BucketStack = self._init_bucket_stack(mask)

        # Padded to avoid boundary checks
        visitable_tiles: NDArray[bool_] = np.ones((self.grid.area.w + 2, self.grid.area.h), bool_)
        visitable_tiles[0] = visitable_tiles[-1] = False

        right_shifted_col_mask: NDArray[bool_] = np.empty(self.grid.area.h, bool_)
        right_shifted_col_mask[0] = False
        left_shifted_col_mask: NDArray[bool_]  = np.empty(self.grid.area.h, bool_)
        left_shifted_col_mask[-1] = False
        indexes: NDArray[uint16] = np.arange(0, self.grid.area.h, dtype=uint16)

        while stack != []:
            x, (start_y, end_y) = stack.pop()
            selected_tiles [x    , start_y:end_y + 1] = True
            visitable_tiles[x + 1, start_y:end_y + 1] = False

            if visitable_tiles[x, start_y] or visitable_tiles[x, end_y]:
                # Find spans for x - 1, start_y, end_y
                prev_temp_mask: NDArray[bool_] = mask[x - 1] & visitable_tiles[x]
                right_shifted_col_mask[1:] = mask[x - 1, :-1]
                left_shifted_col_mask[:-1] = mask[x - 1, 1:]

                # Starts of True sequences
                prev_starts: NDArray[uint16] = indexes[prev_temp_mask & ~right_shifted_col_mask]
                # Ends of True sequences
                prev_ends: NDArray[uint16]   = indexes[prev_temp_mask & ~left_shifted_col_mask ]
                # Faster than numpy
                stack.extend([
                    (x - 1, span)
                    for span in zip(prev_starts, prev_ends)
                    if not (span[1] < start_y or span[0] > end_y)
                ])

            if visitable_tiles[x + 2, start_y] or visitable_tiles[x + 2, end_y]:
                # Find spans for x + 1, start_y, end_y
                next_temp_mask: NDArray[bool_] = mask[x + 1] & visitable_tiles[x + 2]
                right_shifted_col_mask[1:] = mask[x + 1, :-1]
                left_shifted_col_mask[:-1] = mask[x + 1, 1:]

                # Starts of True sequences
                next_starts: NDArray[uint16] = indexes[next_temp_mask & ~right_shifted_col_mask]
                # Ends of True sequences
                next_ends: NDArray[uint16]   = indexes[next_temp_mask & ~left_shifted_col_mask]
                # Faster than numpy
                stack.extend([
                    (x + 1, span)
                    for span in zip(next_starts, next_ends)
                    if not (span[1] < start_y or span[0] > end_y)
                ])

    def _eye_dropper(self) -> None:
        """Handles the eye dropper tool."""

        if (0 <= self._mouse_col < self.grid.area.w) and (0 <= self._mouse_row < self.grid.area.h):
            if self._is_coloring:
                self.eye_dropped_color = self.grid.tiles[self._mouse_col, self._mouse_row][:3]
            self.grid.selected_tiles[self._mouse_col, self._mouse_row] = True

        self._is_coloring = self._is_erasing = False

    def _handle_draw(self, hex_color: HexColor, tool_info: ToolInfo) -> tuple[bool, bool]:
        """
        Handles grid drawing via tools and refreshes the small grid image.

        Args:
            hexadecimal color, tool info
        Returns:
            drawed flag, selected tiles changed flag
        """

        did_draw: bool

        self._handle_tile_info()

        prev_selected_tiles_bytes: bytes = np.packbits(self.grid.selected_tiles).tobytes()
        self.grid.selected_tiles.fill(False)
        self._is_coloring = MOUSE.pressed[MOUSE_LEFT]  or K_RETURN    in KEYBOARD.pressed
        self._is_erasing  = MOUSE.pressed[MOUSE_RIGHT] or K_BACKSPACE in KEYBOARD.pressed

        tool_name: str                  = tool_info[0]
        extra_tool_info: dict[str, Any] = tool_info[1]
        if   tool_name == "pencil":
            self._pencil()
        elif tool_name == "bucket":
            self._bucket(extra_tool_info)
        elif tool_name == "eye_dropper":
            self._eye_dropper()

        selected_tiles_bytes: bytes = np.packbits(self.grid.selected_tiles).tobytes()
        if self._is_coloring or self._is_erasing:
            did_draw = self.grid.upt_section(self._is_coloring, hex_color)
        else:
            did_draw = False

        # Comparing bytes in this situation is faster
        return did_draw, selected_tiles_bytes != prev_selected_tiles_bytes

    def _upt_hovering_text_label(self) -> None:
        """Increases the alpha value gradually if hovering still and resets it otherwise."""

        img: pg.Surface

        if self._is_hovering and (VARS.ticks - self._last_mouse_move_time >= 750):
            if self._hovering_text_alpha == 0:
                self._hovering_text_label_obj_info.rec_set_active(True)
            if self._hovering_text_alpha != 255:
                self._hovering_text_alpha = round(self._hovering_text_alpha + (16 * VARS.dt))
                self._hovering_text_alpha = min(self._hovering_text_alpha, 255)
                for img in self._hovering_text_label.imgs:
                    img.set_alpha(self._hovering_text_alpha)

            rec_move_rect(self._hovering_text_label, MOUSE.x + 5, MOUSE.y, 1, 1)
        elif self._hovering_text_alpha != 0:
            # Modifying alpha values is unnecessary
            self._hovering_text_alpha = 0
            self._hovering_text_label_obj_info.rec_set_active(False)

    def upt(self, hex_color: HexColor, tool_info: ToolInfo) -> bool:
        """
        Allows moving, zooming, moving in history, resetting and drawing.

        Args:
            hexadecimal color, tool info
        Returns:
            grid changed flag
        """

        prev_visible_w: int = self.grid.visible_area.w
        prev_visible_h: int = self.grid.visible_area.h
        prev_offset_x: int = self.grid.offset.x
        prev_offset_y: int = self.grid.offset.y

        self._is_hovering = MOUSE.hovered_obj == self.grid

        if MOUSE.pressed[MOUSE_WHEEL]:
            self._move()
        else:
            self._traveled_x = self._traveled_y = 0

        if self._is_hovering and (MOUSE.scroll_amount != 0 or KEYBOARD.is_ctrl_on):
            self.grid.zoom()

        did_move_history_i: bool = False
        did_draw: bool = False
        did_selected_tiles_change: bool = False

        if KEYBOARD.is_ctrl_on:
            did_move_history_i = self._move_history_i()

            if K_r in KEYBOARD.pressed:
                self.grid.visible_area.w = min(_GRID_INIT_VISIBLE_DIM, self.grid.area.w)
                self.grid.visible_area.h = min(_GRID_INIT_VISIBLE_DIM, self.grid.area.h)
                self.grid.offset.x = self.grid.offset.y = 0
                self._traveled_x = self._traveled_y = 0

        if self._is_hovering or self._prev_hovered_obj == self.grid:  # Extra frame to draw
            self.eye_dropped_color = None
            did_draw, did_selected_tiles_change = self._handle_draw(hex_color, tool_info)
            self._can_leave = True

            if did_draw:
                self._can_add_to_history = True
        elif self._can_leave:
            self.grid.leave()
            self._can_leave = False

        did_stop_drawing: bool = (
            (MOUSE.released[MOUSE_LEFT] or MOUSE.released[MOUSE_RIGHT]) or
            (K_RETURN in KEYBOARD.released or K_BACKSPACE in KEYBOARD.released)
        )
        if self._can_add_to_history and (did_stop_drawing or not self._is_hovering):
            self.grid.add_to_history()
            self._can_add_to_history = False

        if MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y:
            self._last_mouse_move_time = VARS.ticks
        self._upt_hovering_text_label()

        did_visible_area_change: bool = (
            self.grid.visible_area.w != prev_visible_w or
            self.grid.visible_area.h != prev_visible_h
        )
        did_offset_change: bool = (
            self.grid.offset.x != prev_offset_x or
            self.grid.offset.y != prev_offset_y
        )

        if did_draw or did_visible_area_change or did_offset_change:
            self.grid.refresh_grid_img()
            self.grid.refresh_minimap_img()
        elif did_selected_tiles_change:
            self.grid.refresh_grid_img()

        self._prev_hovered_obj = MOUSE.hovered_obj

        return did_move_history_i or did_draw
