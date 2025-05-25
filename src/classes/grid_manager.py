"""
Paintable pixel grid with a minimap.

Grid and minimap are refreshed automatically when offset or visible area changes.
"""

from tkinter import messagebox
from pathlib import Path
from zlib import compress, decompress
from collections import deque
from itertools import islice
from typing import TypeAlias, Final, Optional, Any

import pygame as pg
from pygame.locals import *
import numpy as np
from numpy import uint8, uint16, uint32, intp, bool_
from numpy.typing import NDArray
import cv2

from src.classes.devices import Mouse, Keyboard

from src.utils import Point, RectPos, Size, ObjInfo, get_pixels, try_create_dir, resize_obj
from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import XY, RGBColor, RGBAColor, HexColor, ToolInfo, BlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT, EMPTY_TILE_ARR, TILE_H, TILE_W,
    GRID_TRANSITION_START, GRID_TRANSITION_END, NUM_MAX_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY, BG_LAYER
)


_BucketStack: TypeAlias = list[tuple[uint16, tuple[uint16, uint16]]]

_GRID_INIT_VISIBLE_DIM: Final[int] = 32
_GRID_DIM_CAP: Final[int] = 600
_MINIMAP_DIM_CAP: Final[int] = 256


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

    tiles: list[XY] = []
    delta_x: int = abs(x_2 - x_1)
    delta_y: int = abs(y_2 - y_1)
    err: int = delta_x - delta_y
    step_x: int = 1 if x_1 < x_2 else -1
    step_y: int = 1 if y_1 < y_2 else -1

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
        "brush_dim", "history", "history_i", "_minimap_init_pos", "_minimap_rect",
        "_small_minimap_img", "offset", "selected_tiles", "layer", "blit_sequence", "_win_w_ratio",
        "_win_h_ratio"
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
        self.visible_area: Size = Size(_GRID_INIT_VISIBLE_DIM, _GRID_INIT_VISIBLE_DIM)
        self.grid_tile_dim: float = _GRID_DIM_CAP / _GRID_INIT_VISIBLE_DIM

        grid_img: pg.Surface = pg.Surface((_GRID_DIM_CAP, _GRID_DIM_CAP))
        self.grid_rect: pg.Rect = pg.Rect(0, 0, *grid_img.get_size())
        grid_init_xy: XY = (self._grid_init_pos.x, self._grid_init_pos.y)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, grid_init_xy)

        self.tiles: NDArray[uint8] = np.zeros((self.area.w, self.area.h, 4), uint8)
        self.brush_dim: int = 1
        self.history: deque[tuple[int, int, bytes]] = deque([
            (self.area.w, self.area.h, compress(self.tiles.tobytes()))
        ], 512)
        self.history_i: int = 0

        self._minimap_init_pos: RectPos = minimap_pos

        minimap_img: pg.Surface = pg.Surface((_MINIMAP_DIM_CAP, _MINIMAP_DIM_CAP))
        self._minimap_rect: pg.Rect = pg.Rect(0, 0, *minimap_img.get_size())
        minimap_init_xy: XY = (self._minimap_init_pos.x, self._minimap_init_pos.y)
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, minimap_init_xy)

        # Better for scaling
        self._small_minimap_img: pg.Surface = pg.Surface(
            (self.tiles.shape[0], self.tiles.shape[1])
        )

        self.offset: Point = Point(0, 0)
        self.selected_tiles: NDArray[bool_] = np.zeros((self.area.w, self.area.h), bool_)

        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = [
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
            self.history = deque([(self.area.w, self.area.h, compress(self.tiles.tobytes()))], 512)
            self.history_i: int = 0

    def _resize_grid(self, small_img: pg.Surface) -> None:
        """
        Resizes the small grid with a gradual blur.

        Args:
            small grid image
        """

        xy: XY
        w: int
        h: int
        init_w: float
        init_h: float
        img: pg.Surface

        init_tile_dim: float = _GRID_DIM_CAP / max(self.visible_area.w, self.visible_area.h)
        init_w, init_h = self.visible_area.w * init_tile_dim, self.visible_area.h * init_tile_dim

        xy, (w, h) = resize_obj(
            self._grid_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )
        self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)

        max_visible_dim: int = max(self.visible_area.w, self.visible_area.h)
        if   max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(small_img, (w, h))
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(small_img, (w, h))
        else:
            # Gradual transition
            img_arr: NDArray[uint8] = pg.surfarray.pixels3d(small_img)
            img_arr = cv2.resize(img_arr, (h, w), interpolation=cv2.INTER_AREA).astype(uint8)
            img = pg.surfarray.make_surface(img_arr)

        self.grid_rect.size = (w, h)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, xy)

        self.blit_sequence[0] = (img.convert(), self.grid_rect, self.layer)

    def refresh_grid_img(self) -> None:
        """Refreshes the grid image from the small minimap and draws the selected tiles."""

        selected_tiles_xs: NDArray[intp]
        selected_tiles_ys: NDArray[intp]

        rect: pg.Rect = pg.Rect(
            self.offset.x * TILE_W, self.offset.y * TILE_H,
            self.visible_area.w * TILE_W, self.visible_area.h * TILE_H
        )
        visible_selected_tiles: NDArray[bool_] = self.selected_tiles[
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
        small_img_arr: NDArray[uint8] = pg.surfarray.pixels3d(img)

        # For every position get indexes of the TILE_WxTILE_H slice as a 1D array
        repeated_cols: NDArray[uint8] = np.repeat(np.arange(TILE_W, dtype=uint8), TILE_H)
        tiled_rows: NDArray[uint8] = np.tile(np.arange(TILE_H, dtype=uint8), TILE_W)

        target_xs: NDArray[intp] = (
            selected_tiles_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]
        ).ravel()
        target_ys: NDArray[intp] = (
            selected_tiles_ys[:, np.newaxis] + tiled_rows[np.newaxis, :]
        ).ravel()

        a: int = 128
        color_range: NDArray[uint16] = np.arange(256, dtype=uint16)
        # Lookup table for every blend combination with gray (150, 150, 150)
        blend_lut: NDArray[uint8] = ((150 * a + color_range * (255 - a)) >> 8).astype(uint8)

        target_pixels: NDArray[uint8] = small_img_arr[target_xs, target_ys]
        small_img_arr[target_xs, target_ys] = blend_lut[target_pixels]
        self._resize_grid(img)
        if selected_tiles_xs.size <= 14_000:
            small_img_arr[target_xs, target_ys] = target_pixels

    def _refresh_minimap_rect(self) -> None:
        """Refreshes the minimap rect."""

        init_tile_dim: float = _MINIMAP_DIM_CAP / max(self.area.w, self.area.h)
        init_w, init_h = self.area.w * init_tile_dim, self.area.h * init_tile_dim

        xy, self._minimap_rect.size = resize_obj(
            self._minimap_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, xy)

    def _resize_minimap(self) -> None:
        """Resizes the small minimap with a gradual blur."""

        img: pg.Surface

        max_visible_dim: int = max(self.area.w, self.area.h)
        if   max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(self._small_minimap_img, self._minimap_rect.size)
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(self._small_minimap_img, self._minimap_rect.size)
        else:
            # Gradual transition
            img_arr: NDArray[uint8] = pg.surfarray.pixels3d(self._small_minimap_img)
            img_arr = cv2.resize(
                img_arr, (self._minimap_rect.h, self._minimap_rect.w), interpolation=cv2.INTER_AREA
            ).astype(uint8)
            img = pg.surfarray.make_surface(img_arr)

        self.blit_sequence[1] = (img.convert(), self._minimap_rect, self.layer)

    def refresh_minimap_img(self) -> None:
        """Refreshes the minimap image scaled to minimap_rect and draws the indicator."""

        # Having a version where 1 tile = 1 pixel is better for scaling
        img_arr: NDArray[uint8] = pg.surfarray.pixels3d(self._small_minimap_img)

        offset_x: int = self.offset.x * TILE_W
        offset_y: int = self.offset.y * TILE_H
        visible_w: int = self.visible_area.w * TILE_W
        visible_h: int = self.visible_area.h * TILE_H

        a: int = 128
        color_range: NDArray[uint16] = np.arange(256, dtype=uint16)
        # Lookup table for every blend combination with gray (150, 150, 150)
        blend_lut: NDArray[uint8] = ((150 * a + color_range * (255 - a)) >> 8).astype(uint8)

        top_x_sl: slice = slice(offset_x, offset_x + visible_w)
        top_y_sl: slice = slice(offset_y, offset_y + TILE_H)
        target_top_pixels: NDArray[uint8] = img_arr[top_x_sl, top_y_sl]

        right_x_sl: slice = slice(offset_x + visible_w - TILE_W, offset_x + visible_w)
        right_y_sl: slice = slice(offset_y, offset_y + visible_h)
        target_right_pixels: NDArray[uint8] = img_arr[right_x_sl, right_y_sl]

        bottom_x_sl: slice = top_x_sl
        bottom_y_sl: slice = slice(offset_y + visible_h - TILE_H, offset_y + visible_h)
        target_bottom_pixels: NDArray[uint8] = img_arr[bottom_x_sl, bottom_y_sl]

        left_x_sl: slice = slice(offset_x, offset_x + TILE_W)
        left_y_sl: slice = right_y_sl
        target_left_pixels: NDArray[uint8] = img_arr[left_x_sl, left_y_sl]

        src_top_pixels: NDArray[uint8] = target_top_pixels.copy()
        src_right_pixels: NDArray[uint8] = target_right_pixels.copy()
        src_bottom_pixels: NDArray[uint8] = target_bottom_pixels.copy()
        src_left_pixels: NDArray[uint8] = target_left_pixels.copy()

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
        """Refreshes the tiles on the minimap, its rect and retrieves the grid."""

        img_arr: NDArray[uint8]

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        repeated_tiles: NDArray[uint8] = self.tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_img_arr: NDArray[uint8] = np.tile(EMPTY_TILE_ARR, (self.area.w, self.area.h, 1))
        empty_tiles_mask: NDArray[bool_] = (repeated_tiles[..., 3] == 0)[..., np.newaxis]

        img_arr = np.where(empty_tiles_mask, empty_img_arr, repeated_tiles[..., :3])
        self._small_minimap_img = pg.surfarray.make_surface(img_arr)

        self.refresh_grid_img()
        self._refresh_minimap_rect()
        self.refresh_minimap_img()

    def set_tiles(self, img: Optional[pg.Surface]) -> None:
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
                self.tiles = np.pad(
                    self.tiles, ((0, extra_w), (0, 0), (0, 0)), constant_values=0
                )

            extra_h: int = self.area.h - self.tiles.shape[1]
            if   extra_h < 0:
                self.tiles = self.tiles[:, :self.area.h, ...]
            elif extra_h > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, 0), (0, extra_h), (0, 0)), constant_values=0
                )

        self.history = deque([(self.area.w, self.area.h, compress(self.tiles.tobytes()))], 512)
        self.history_i = 0

        self.refresh_full()

    def move_with_keys(self, keyboard: Keyboard, rel_mouse_col: int, rel_mouse_row: int) -> XY:
        """
        Moves the mouse tile with the keyboard.

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
        if keyboard.is_shift_on:
            if K_LEFT in keyboard.timed or K_RIGHT in keyboard.timed:
                step = self.visible_area.w
            else:
                step = self.visible_area.h
        if K_TAB in keyboard.pressed:
            step = self.brush_dim

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

        if rel_mouse_col != prev_rel_mouse_col or rel_mouse_row != prev_rel_mouse_row:
            # Mouse is in the center of the tile

            rel_mouse_x: int = round(rel_mouse_col * self.grid_tile_dim + self.grid_tile_dim // 2)
            if rel_mouse_col != prev_rel_mouse_col:
                prev_rel_mouse_x: int = round(rel_mouse_col * self.grid_tile_dim)
                if rel_mouse_x == prev_rel_mouse_x:  # Grid is so large that mouse x stays the same
                    direction = 1 if rel_mouse_col > prev_rel_mouse_col else -1
                    rel_mouse_x = min(max(rel_mouse_x + direction, 0), self.grid_rect.w - 1)

            rel_mouse_y: int = round(rel_mouse_row * self.grid_tile_dim + self.grid_tile_dim // 2)
            if rel_mouse_row != prev_rel_mouse_row:
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
            self._inc_smallest_side(-amount)

    def zoom(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Zooms the grid in or out.

        Args:
            mouse, keyboard
        """

        amount: Optional[int] = None
        should_reach_min_limit: bool = False
        should_reach_max_limit: bool = False

        if mouse.scroll_amount != 0:
            # Amount depends on zoom level
            uncapped_amount: int = int(mouse.scroll_amount * (25 / self.grid_tile_dim))
            if uncapped_amount == 0:
                uncapped_amount = 1 if mouse.scroll_amount > 0 else -1
            amount = min(max(uncapped_amount, -100), 100)

        if keyboard.is_ctrl_on:
            if K_PLUS in keyboard.timed:
                amount = 1
                should_reach_min_limit = keyboard.is_shift_on
            if K_MINUS in keyboard.timed:
                amount = -1
                should_reach_max_limit = keyboard.is_shift_on

        if amount is not None:
            prev_mouse_col: int = int((mouse.x - self.grid_rect.x) / self.grid_tile_dim)
            prev_mouse_row: int = int((mouse.y - self.grid_rect.y) / self.grid_tile_dim)

            self._zoom_visible_area(amount, should_reach_min_limit, should_reach_max_limit)
            init_tile_dim: float = _GRID_DIM_CAP / max(self.visible_area.w, self.visible_area.h)
            self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)

            mouse_col: int = int((mouse.x - self.grid_rect.x) / self.grid_tile_dim)
            mouse_row: int = int((mouse.y - self.grid_rect.y) / self.grid_tile_dim)

            uncapped_offset_x: int = self.offset.x + prev_mouse_col - mouse_col
            self.offset.x = min(max(uncapped_offset_x, 0), self.area.w - self.visible_area.w)
            uncapped_offset_y: int = self.offset.y + prev_mouse_row - mouse_row
            self.offset.y = min(max(uncapped_offset_y, 0), self.area.h - self.visible_area.h)

    def add_to_history(self) -> None:
        """Adds the current info to the history if different from the last snapshot."""

        snapshot: tuple[int, int, bytes] = (self.area.w, self.area.h, compress(self.tiles.tobytes()))
        if snapshot != self.history[self.history_i]:
            if self.history_i != len(self.history) - 1:
                history_sl: islice[tuple[int, int, bytes]] = islice(self.history, self.history_i + 1)
                self.history = deque(history_sl, 512)
            self.history.append(snapshot)
            self.history_i += 1

    def upt_section(self, is_coloring: bool, hex_color: str) -> bool:
        """
        Updates the changed tiles and refreshes the small minimap.

        Args:
            coloring flag, hex color
        Returns:
            drawed flag
        """

        rgba_color: RGBAColor
        selected_tiles_xs: NDArray[intp]
        selected_tiles_ys: NDArray[intp]

        prev_tiles: NDArray[uint8] = self.tiles[self.selected_tiles].copy()

        if is_coloring:
            rgba_color = (
                int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), 255
            )
        else:
            rgba_color = (0, 0, 0, 0)
        self.tiles[self.selected_tiles] = rgba_color

        did_draw: bool = not np.array_equal(self.tiles[self.selected_tiles], prev_tiles)
        if did_draw:
            img_arr: NDArray[uint8] = pg.surfarray.pixels3d(self._small_minimap_img)

            selected_tiles_xs, selected_tiles_ys = np.nonzero(self.selected_tiles)
            selected_tiles_xs *= TILE_W
            selected_tiles_ys *= TILE_H

            # For every position get indexes of the TILE_WxTILE_H slice as a 1D array
            repeated_cols: NDArray[uint8] = np.repeat(np.arange(TILE_W, dtype=uint8), TILE_H)
            tiled_rows: NDArray[uint8] = np.tile(np.arange(TILE_H, dtype=uint8), TILE_W)

            target_xs: NDArray[intp] = (
                selected_tiles_xs[:, np.newaxis] + repeated_cols[np.newaxis, :]
            ).ravel()
            target_ys: NDArray[intp] = (
                selected_tiles_ys[:, np.newaxis] + tiled_rows[np.newaxis, :]
            ).ravel()

            if is_coloring:
                img_arr[target_xs, target_ys] = rgba_color[:3]
            else:
                img_arr[target_xs, target_ys] = EMPTY_TILE_ARR[
                    target_xs % TILE_W, target_ys % TILE_H
                ]

        return did_draw

    def try_save_to_file(self, file_str: str, should_ask_create_dir: bool) -> Optional[pg.Surface]:
        """
        Saves the image to a file.

        Args:
            file string, ask dir creation flag
        Returns:
            image (can be None)
        """

        if file_str == "":
            return None

        img: pg.Surface = pg.Surface((self.area.w, self.area.h), SRCALPHA)
        pg.surfarray.blit_array(img, self.tiles[..., :3])
        pg.surfarray.pixels_alpha(img)[...] = self.tiles[..., 3]

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
        "_prev_hovered_obj", "_can_leave", "_prev_mouse_col", "_prev_mouse_row", "_mouse_col",
        "_mouse_row", "_traveled_x", "_traveled_y", "_is_coloring", "_is_erasing",
        "eye_dropped_color", "_can_add_to_history", "grid", "blit_sequence", "objs_info"
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object and wrapper info.

        Args:
            grid position, minimap position
        """

        self._prev_hovered_obj: Optional[Grid] = None
        self._can_leave: bool = False

        self._prev_mouse_col: int = 0
        self._prev_mouse_row: int = 0
        self._mouse_col: int = 0
        self._mouse_row: int = 0
        self._traveled_x: float = 0
        self._traveled_y: float = 0

        self._is_coloring: bool = False
        self._is_erasing: bool = False
        self.eye_dropped_color: Optional[RGBColor] = None

        self._can_add_to_history: bool = False

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self.blit_sequence: list[BlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid)]

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._prev_hovered_obj = None
        self._can_leave = False
        self._traveled_x = self._traveled_y = 0

        if self._can_add_to_history:
            self.grid.add_to_history()
            self._can_add_to_history = False

    def _move(self, mouse: Mouse) -> None:
        """
        Moves the visible section, it's faster when moving the mouse faster.

        Args:
            mouse
        """

        tiles_traveled: int

        x_speed: float = abs(mouse.prev_x - mouse.x) ** 1.25
        if mouse.x > mouse.prev_x:
            x_speed = -x_speed
        self._traveled_x += x_speed

        y_speed: float = abs(mouse.prev_y - mouse.y) ** 1.25
        if mouse.y > mouse.prev_y:
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

    def _move_history_i(self, keyboard: Keyboard) -> bool:
        """
        Changes the index of the viewed history snapshot with the keyboard.

        Args:
            keyboard
        Returns:
            changed flag
        """

        grid_w: int
        grid_h: int
        compressed_tiles: bytes

        prev_history_i: int = self.grid.history_i

        max_history_i: int = len(self.grid.history) - 1
        if K_z in keyboard.timed:
            move_sign: int = 1 if keyboard.is_shift_on else -1
            self.grid.history_i = min(max(self.grid.history_i + move_sign, 0), max_history_i)
        if K_y in keyboard.timed:
            self.grid.history_i = min(self.grid.history_i + 1, max_history_i)

        if self.grid.history_i != prev_history_i:
            grid_w, grid_h, compressed_tiles = self.grid.history[self.grid.history_i]
            # copy makes it writable
            tiles: NDArray[uint8] = np.frombuffer(decompress(compressed_tiles), uint8).copy()

            self.grid.set_info(
                tiles.reshape((grid_w, grid_h, 4)),
                self.grid.visible_area.w, self.grid.visible_area.h,
                self.grid.offset.x, self.grid.offset.y,
                False
            )
            self.grid.refresh_full()

        return self.grid.history_i != prev_history_i

    def _handle_tile_info(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Calculates previous and current mouse tiles and handles keyboard movement.

        Args:
            mouse, keyboard
        """

        grid_x: int = self.grid.grid_rect.x
        grid_y: int = self.grid.grid_rect.y
        prev_rel_mouse_col: int = int((mouse.prev_x - grid_x) / self.grid.grid_tile_dim)
        prev_rel_mouse_row: int = int((mouse.prev_y - grid_y) / self.grid.grid_tile_dim)
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
        Handles the brush tool.

        Args:
            drawing flag, extra info (mirrors)
        """

        w_edge: int = self.grid.area.w - 1
        h_edge: int = self.grid.area.h - 1

        brush_dim: int = self.grid.brush_dim
        # Center tiles to the cursor
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

    def _init_bucket_stack(self, x: int, y: int, mask: NDArray[bool_]) -> _BucketStack:
        """
        Initializes the stack for the bucket tool.

        Args:
            x, y, tiles mask
        Returns:
            stack
        """

        up_tiles: NDArray[bool_] = mask[x, :y + 1]
        up_stop: int | intp = up_tiles[::-1].argmin()
        if up_stop == 0:
            up_stop = up_tiles.size
        first_y: int | intp = y - up_stop + 1

        down_tiles: NDArray[bool_] = mask[x, y:]
        down_stop: int | intp = down_tiles.argmin()
        if down_stop == 0:
            down_stop = down_tiles.size
        last_y: int | intp = y + down_stop - 1

        return [(uint16(x), (uint16(first_y), uint16(last_y)))]

    def _bucket(self, extra_info: dict[str, Any]) -> None:
        """
        Handles the bucket tool using the scan-line algorithm, includes a color fill.

        Args:
            extra info (color fill)
        """

        x: uint16
        start_y: uint16
        end_y: uint16

        seed_x: int = self._mouse_col
        seed_y: int = self._mouse_row
        w: int = self.grid.area.w
        h: int = self.grid.area.h
        if seed_x < 0 or seed_x >= w or seed_y < 0 or seed_y >= h:
            return

        color: NDArray[uint8] = self.grid.tiles[seed_x, seed_y]
        selected_tiles: NDArray[bool_] = self.grid.selected_tiles

        # Pack a color as a uint32 and compare
        mask: NDArray[bool_] = self.grid.tiles.view(uint32)[..., 0] == color.view(uint32)[0]
        if extra_info["color_fill"]:
            selected_tiles[mask] = True
            return

        stack: _BucketStack = self._init_bucket_stack(seed_x, seed_y, mask)

        # Padded to avoid boundary checks
        visitable_tiles: NDArray[bool_] = np.ones((w + 2, h), bool_)
        visitable_tiles[0] = visitable_tiles[-1] = False

        right_shifted_col_mask: NDArray[bool_] = np.empty(h, bool_)
        right_shifted_col_mask[0] = False
        left_shifted_col_mask: NDArray[bool_] = np.empty(h, bool_)
        left_shifted_col_mask[-1] = False
        indexes: NDArray[uint16] = np.arange(0, h, dtype=uint16)

        while stack != []:
            x, (start_y, end_y) = stack.pop()
            selected_tiles[x, start_y:end_y + 1] = True
            visitable_tiles[x + 1, start_y:end_y + 1] = False

            if visitable_tiles[x, start_y] or visitable_tiles[x, end_y]:
                # Find spans for x - 1, start_y, end_y
                prev_temp_mask: NDArray[bool_] = mask[x - 1] & visitable_tiles[x]
                right_shifted_col_mask[1:] = mask[x - 1, :-1]
                left_shifted_col_mask[:-1] = mask[x - 1, 1:]

                # Starts of True sequences
                prev_starts: NDArray[uint16] = indexes[prev_temp_mask & ~right_shifted_col_mask]
                # Ends of True sequences
                prev_ends: NDArray[uint16] = indexes[prev_temp_mask & ~left_shifted_col_mask]
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
                next_ends: NDArray[uint16] = indexes[next_temp_mask & ~left_shifted_col_mask]
                # Faster than numpy
                stack.extend([
                    (x + 1, span)
                    for span in zip(next_starts, next_ends)
                    if not (span[1] < start_y or span[0] > end_y)
                ])

    def _eye_dropper(self) -> None:
        """Handles the eye dropper tool."""

        if 0 <= self._mouse_col < self.grid.area.w and 0 <= self._mouse_row < self.grid.area.h:
            if self._is_coloring:
                self.eye_dropped_color = self.grid.tiles[self._mouse_col, self._mouse_row][:3]
            self._is_coloring = self._is_erasing = False

            self.grid.selected_tiles[self._mouse_col, self._mouse_row] = True

    def _handle_draw(
            self, mouse: Mouse, keyboard: Keyboard, hex_color: HexColor, tool_info: ToolInfo
    ) -> tuple[bool, bool]:
        """
        Handles grid drawing via tools and refreshes the small grid image.

        Args:
            mouse, keyboard, hexadecimal color, tool info
        Returns:
            drawed flag, selected tiles changed flag
        """

        tool_name: str
        extra_tool_info: dict[str, Any]
        did_draw: bool

        self._handle_tile_info(mouse, keyboard)

        prev_selected_tiles_bytes: bytes = np.packbits(self.grid.selected_tiles).tobytes()
        self.grid.selected_tiles.fill(False)

        self._is_coloring = mouse.pressed[MOUSE_LEFT] or K_RETURN in keyboard.pressed
        self._is_erasing = mouse.pressed[MOUSE_RIGHT] or K_BACKSPACE in keyboard.pressed
        tool_name, extra_tool_info = tool_info
        if tool_name == "brush":
            self._brush(extra_tool_info)
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

    def upt(
            self, mouse: Mouse, keyboard: Keyboard, hex_color: HexColor, tool_info: ToolInfo
    ) -> bool:
        """
        Allows moving, zooming, moving in history, resetting and drawing.

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
        self.eye_dropped_color = None

        if mouse.pressed[MOUSE_WHEEL]:
            self._move(mouse)
        else:
            self._traveled_x = self._traveled_y = 0

        if grid == mouse.hovered_obj and (mouse.scroll_amount != 0 or keyboard.is_ctrl_on):
            grid.zoom(mouse, keyboard)

        did_move_history_i: bool = False
        did_draw: bool = False
        did_selected_tiles_change: bool = False

        if keyboard.is_ctrl_on:
            did_move_history_i = self._move_history_i(keyboard)

            if K_r in keyboard.pressed:
                grid.visible_area.w = min(_GRID_INIT_VISIBLE_DIM, grid.area.w)
                grid.visible_area.h = min(_GRID_INIT_VISIBLE_DIM, grid.area.h)
                grid.offset.x = grid.offset.y = 0
                self._traveled_x = self._traveled_y = 0

        if grid == mouse.hovered_obj or grid == self._prev_hovered_obj:  # Extra frame to draw
            did_draw, did_selected_tiles_change = self._handle_draw(
                mouse, keyboard, hex_color, tool_info
            )
            self._can_leave = True

            if did_draw:
                self._can_add_to_history = True
        elif self._can_leave:
            grid.leave()
            self._can_leave = False

        did_stop_drawing: bool = (
            mouse.released[MOUSE_LEFT] or mouse.released[MOUSE_RIGHT] or
            K_RETURN in keyboard.released or K_BACKSPACE in keyboard.released
        )
        if self._can_add_to_history and (did_stop_drawing or grid != mouse.hovered_obj):
            self.grid.add_to_history()
            self._can_add_to_history = False

        did_visible_area_change: bool = (
            grid.visible_area.w != prev_visible_w or grid.visible_area.h != prev_visible_h
        )
        did_offset_change: bool = grid.offset.x != prev_offset_x or grid.offset.y != prev_offset_y
        if did_draw or did_visible_area_change or did_offset_change:
            grid.refresh_grid_img()
            grid.refresh_minimap_img()
        elif did_selected_tiles_change:
            grid.refresh_grid_img()

        self._prev_hovered_obj = mouse.hovered_obj

        return did_move_history_i or did_draw
