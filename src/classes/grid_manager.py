"""
Paintable pixel grid with a minimap.

Grid and minimap are refreshed automatically when offset or visible area changes.
"""

from tkinter import messagebox
from pathlib import Path
from collections import deque
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
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT, EMPTY_TILE_ARR, NUM_TILE_ROWS, NUM_TILE_COLS,
    GRID_TRANSITION_START, GRID_TRANSITION_END, NUM_MAX_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY, BG_LAYER
)


BlitSequence: TypeAlias = list[tuple[pg.Surface, XY]]

GRID_INIT_VISIBLE_DIM: Final[int] = 32
GRID_DIM_CAP: Final[int] = 600
MINIMAP_DIM_CAP: Final[int] = 256
TRANSPARENT_GRAY: Final[pg.Color] = pg.Color(150, 150, 150, 150)


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


class Grid:
    """Class to create a pixel grid and its minimap."""

    __slots__ = (
        "_grid_init_pos", "area", "visible_area", "grid_tile_dim", "grid_rect", "tiles",
        "brush_dim", "_selected_tile_img", "_minimap_init_pos", "_minimap_rect",
        "_no_indicator_small_minimap_img", "offset", "selected_tiles", "changed_tiles",
        "layer", "blit_sequence", "_win_w_ratio", "_win_h_ratio"
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

        self.grid_rect: pg.Rect = pg.Rect(0, 0, GRID_DIM_CAP, GRID_DIM_CAP)
        grid_init_xy: XY = (self._grid_init_pos.x, self._grid_init_pos.y)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, grid_init_xy)

        self.tiles: NDArray[np.uint8] = np.zeros((self.area.w, self.area.h, 4), np.uint8)

        self.brush_dim: int = 1
        self._selected_tile_img: pg.Surface = pg.Surface(
            (NUM_TILE_COLS, NUM_TILE_ROWS), SRCALPHA
        ).convert_alpha()
        self._selected_tile_img.fill((125, 125, 125, 75))

        self._minimap_init_pos: RectPos = minimap_pos

        self._minimap_rect: pg.Rect = pg.Rect(0, 0, MINIMAP_DIM_CAP, MINIMAP_DIM_CAP)
        minimap_init_xy: XY = (self._minimap_init_pos.x, self._minimap_init_pos.y)
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, minimap_init_xy)
        # Better for scaling, used for update section
        self._no_indicator_small_minimap_img: pg.Surface = pg.Surface(
            (self.tiles.shape[0], self.tiles.shape[1])
        ).convert()

        self.offset: Point = Point(0, 0)
        self.selected_tiles: list[XY] = []
        self.changed_tiles: list[XY] = []

        grid_img: pg.Surface = pg.Surface((GRID_DIM_CAP, GRID_DIM_CAP)).convert()
        minimap_img: pg.Surface = pg.Surface((MINIMAP_DIM_CAP, MINIMAP_DIM_CAP)).convert()

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

        self.selected_tiles = []
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
            self, area: Size, num_visible_cols: int, num_visible_rows: int,
            offset_x: int, offset_y: int
    ) -> None:
        """
        Sets the offset, area, visible area and not the tiles dimension.

        Something that gets the minimap and grid should be called later.

        Args:
            area, visible columns, visible rows, x offset, y offset
        """

        self.area = area
        self.visible_area.w = min(num_visible_cols, self.area.w)
        self.visible_area.h = min(num_visible_rows, self.area.h)
        self.offset.x = min(offset_x, self.area.w - self.visible_area.w)
        self.offset.y = min(offset_y, self.area.h - self.visible_area.h)

        num_extra_cols: int = self.area.w - self.tiles.shape[0]
        if num_extra_cols < 0:
            self.tiles = self.tiles[:self.area.w, ...]
        elif num_extra_cols > 0:
            self.tiles = np.pad(
                self.tiles, ((0, num_extra_cols), (0, 0), (0, 0)), constant_values=0
            )

        num_extra_rows: int = self.area.h - self.tiles.shape[1]
        if num_extra_rows < 0:
            self.tiles = self.tiles[:, :self.area.h, ...]
        elif num_extra_rows > 0:
            self.tiles = np.pad(
                self.tiles, ((0, 0), (0, num_extra_rows), (0, 0)), constant_values=0
            )

    def _resize_grid(self, small_grid_img: pg.Surface) -> None:
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
            img = pg.transform.scale(small_grid_img, (w, h))
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(small_grid_img, (w, h))
        else:
            # Gradual transition
            img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(small_grid_img)
            img_arr = cv2.resize(img_arr, (h, w), interpolation=cv2.INTER_AREA).astype(np.uint8)
            img = pg.surfarray.make_surface(img_arr)

        self.grid_rect.size = (w, h)
        setattr(self.grid_rect, self._grid_init_pos.coord_type, xy)

        self.blit_sequence[0] = (img.convert(), self.grid_rect, self.layer)

    def refresh_grid_img(self) -> None:
        """Refreshes the grid image from the minimap."""

        scaled_offset_x: int = self.offset.x * NUM_TILE_COLS
        scaled_offset_y: int = self.offset.y * NUM_TILE_ROWS
        small_rect: pg.Rect = pg.Rect(
            scaled_offset_x, scaled_offset_y,
            self.visible_area.w * NUM_TILE_COLS, self.visible_area.h * NUM_TILE_ROWS
        )

        # Having a version where 1 tile = 1 pixel is better for scaling
        small_img: pg.Surface = self._no_indicator_small_minimap_img.subsurface(small_rect).copy()

        scaled_selected_tiles: list[XY] = [
            (x * NUM_TILE_COLS, y * NUM_TILE_ROWS) for x, y in self.selected_tiles
        ]

        blit_sequence: BlitSequence = [
            (self._selected_tile_img, (x - scaled_offset_x, y - scaled_offset_y))
            for x, y in scaled_selected_tiles
        ]
        small_img.fblits(blit_sequence, BLEND_ALPHA_SDL2)
        self._resize_grid(small_img)

    def _refresh_minimap_rect(self) -> None:
        """Refreshes the minimap rect."""

        init_tile_dim: float = MINIMAP_DIM_CAP / max(self.area.w, self.area.h)
        init_w, init_h = self.area.w * init_tile_dim, self.area.h * init_tile_dim

        xy, wh = resize_obj(
            self._minimap_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )
        self._minimap_rect.size = wh
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, xy)

    def refresh_minimap_img(self) -> None:
        """Refreshes the minimap image scaled to the minimap rect."""

        img: pg.Surface

        # Having a version where 1 tile = 1 pixel is better for scaling
        small_img: pg.Surface = self._no_indicator_small_minimap_img.copy()

        indicator: pg.Surface = pg.Surface(
            (self.visible_area.w * NUM_TILE_COLS, self.visible_area.h * NUM_TILE_ROWS), SRCALPHA
        )
        indicator_side_w: int = min(NUM_TILE_COLS, NUM_TILE_ROWS)
        pg.draw.rect(indicator, TRANSPARENT_GRAY, indicator.get_rect(), indicator_side_w)

        indicator_xy: XY = (self.offset.x * NUM_TILE_COLS, self.offset.y * NUM_TILE_ROWS)
        small_img.blit(indicator, indicator_xy, special_flags=BLEND_ALPHA_SDL2)

        max_visible_dim: int = max(self.area.w, self.area.h)
        if max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(small_img, self._minimap_rect.size)
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(small_img, self._minimap_rect.size)
        else:
            # Gradual transition
            img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(small_img)
            img_arr = cv2.resize(
                img_arr, (self._minimap_rect.h, self._minimap_rect.w), interpolation=cv2.INTER_AREA
            ).astype(np.uint8)
            img = pg.surfarray.make_surface(img_arr)

        self.blit_sequence[1] = (img.convert(), self._minimap_rect, self.layer)

    def refresh_full(self) -> None:
        """Refreshes all the tiles on the minimap and retrieves the grid."""

        tiles: NDArray[np.uint8] = self.tiles  # Copying isn't necessary

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles = tiles.repeat(NUM_TILE_COLS, 0).repeat(NUM_TILE_ROWS, 1)
        empty_tiles_mask: NDArray[np.bool_] = tiles[..., 3:4] == 0
        tiles = tiles[..., :3]

        empty_tiles: NDArray[np.uint8] = np.tile(EMPTY_TILE_ARR, (self.area.w, self.area.h, 1))
        tiles = np.where(empty_tiles_mask, empty_tiles, tiles)
        self._no_indicator_small_minimap_img = pg.surfarray.make_surface(tiles).convert()

        self.refresh_grid_img()
        self._refresh_minimap_rect()
        self.refresh_minimap_img()

    def _refresh_section(self, unique_changed_tiles: set[XY]) -> None:
        """
        Refreshes the changed tiles on the minimap and retrieves the grid.

        Args:
            unique changed tiles
        """

        x: int
        y: int

        tiles: NDArray[np.uint8] = self.tiles
        tile_img: pg.Surface = pg.Surface((NUM_TILE_COLS, NUM_TILE_ROWS)).convert()
        empty_tile_img: pg.Surface = pg.surfarray.make_surface(EMPTY_TILE_ARR).convert()

        blit_sequence: BlitSequence = []
        for x, y in unique_changed_tiles:
            tile_xy: XY = (x * NUM_TILE_COLS, y * NUM_TILE_ROWS)
            if tiles[x, y, 3] == 0:
                blit_sequence.append((empty_tile_img, tile_xy))
            else:
                tile_img.fill(tiles[x, y])
                blit_sequence.append((tile_img.copy(), tile_xy))
        self._no_indicator_small_minimap_img.fblits(blit_sequence)

        self.refresh_grid_img()
        self.refresh_minimap_img()

    def upt_section(self, rgba_color: RGBAColor, prev_selected_tiles: list[XY]) -> bool:
        """
        Updates the changed tiles.

        Args:
            rgba color, previous selected tiles
        Returns:
            changed flag
        """

        # The tiles array has x and y flipped, when making it a surface, pygame uses it like this

        x: int
        y: int

        did_change: bool = False

        unique_changed_tiles: set[XY] = set(self.changed_tiles)
        tiles: NDArray[np.uint8] = self.tiles
        for x, y in unique_changed_tiles:
            if tuple(tiles[x, y]) != rgba_color:
                did_change = True
                tiles[x, y] = rgba_color

        if did_change:
            self._refresh_section(unique_changed_tiles)
        elif self.selected_tiles != prev_selected_tiles:
            self.refresh_grid_img()
        self.changed_tiles = []

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

            num_extra_cols: int = self.area.w - self.tiles.shape[0]
            if num_extra_cols < 0:
                self.tiles = self.tiles[:self.area.w, ...]
            elif num_extra_cols > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, num_extra_cols), (0, 0), (0, 0)), constant_values=0
                )

            num_extra_rows: int = self.area.h - self.tiles.shape[1]
            if num_extra_rows < 0:
                self.tiles = self.tiles[:, :self.area.h, ...]
            elif num_extra_rows > 0:
                self.tiles = np.pad(
                    self.tiles, ((0, 0), (0, num_extra_rows), (0, 0)), constant_values=0
                )

        self.refresh_full()

    def set_selected_tile_dim(self, dim: int) -> None:
        """
        Sets the size of the selected tile.

        Args:
            dimension
        """

        self.brush_dim = dim
        wh: WH = (self.brush_dim * NUM_TILE_COLS, self.brush_dim * NUM_TILE_ROWS)
        self._selected_tile_img = pg.transform.scale(self._selected_tile_img, wh).convert_alpha()
        self.refresh_grid_img()

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
                uncapped_amount = int(15 / self.grid_tile_dim)
                amount = min(max(uncapped_amount, 1), 100)
                should_reach_min_limit = keyboard.is_shift_on
            if K_MINUS in keyboard.timed:
                uncapped_amount = int(25 / self.grid_tile_dim)
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
        "_prev_mouse_x", "_prev_mouse_y", "_prev_hovered_obj", "_prev_mouse_col",
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
        self._traveled_x: float
        self._traveled_y: float

        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()
        self._prev_hovered_obj: Optional[Grid] = None

        self._prev_mouse_col: int = 0
        self._prev_mouse_row: int = 0
        self._mouse_col: int = 0
        self._mouse_row: int = 0
        self._traveled_x = self._traveled_y = 0

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self.blit_sequence: list[LayeredBlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid)]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()
        self._prev_hovered_obj = None
        self._traveled_x = self._traveled_y = 0

    def _handle_tile_info(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Calculates previous and current mouse tile and handles arrow movement.

        Args:
            mouse, keyboard
        """

        grid_x: int
        grid_y: int

        grid_x, grid_y = self.grid.grid_rect.topleft

        prev_rel_mouse_col: int = int((self._prev_mouse_x - grid_x) / self.grid.grid_tile_dim)
        prev_rel_mouse_row: int = int((self._prev_mouse_y - grid_y) / self.grid.grid_tile_dim)
        rel_mouse_col: int = int((mouse.x - grid_x) / self.grid.grid_tile_dim)
        rel_mouse_row: int = int((mouse.y - grid_y) / self.grid.grid_tile_dim)
        half_brush_dim: int = self.grid.brush_dim // 2

        # By setting prev_mouse_tile before changing offset you can draw a line with shift/ctrl
        self._prev_mouse_col = prev_rel_mouse_col + self.grid.offset.x - half_brush_dim
        self._prev_mouse_row = prev_rel_mouse_row + self.grid.offset.y - half_brush_dim

        if keyboard.timed != []:
            # Changes the offset
            rel_mouse_col, rel_mouse_row = self.grid.move_with_keys(
                keyboard, rel_mouse_col, rel_mouse_row
            )

        self._mouse_col = rel_mouse_col + self.grid.offset.x - half_brush_dim
        self._mouse_row = rel_mouse_row + self.grid.offset.y - half_brush_dim

    def _add_tiles_in_line(self, x_1: int, y_1: int, x_2: int, y_2: int) -> None:
        """
        Adds the tiles touched by a line to the changed tiles using Bresenham's Line Algorithm.

        Args:
            line start x, line start y, line end x, line end y
        """

        delta_x: int
        delta_y: int
        step_x: int
        step_y: int

        changed_tiles: list[XY] = self.grid.changed_tiles

        delta_x, delta_y = abs(x_2 - x_1), abs(y_2 - y_1)
        step_x, step_y = 1 if x_1 < x_2 else -1, 1 if y_1 < y_2 else -1
        err: int = delta_x - delta_y
        while True:
            changed_tiles.append((x_1, y_1))
            if x_1 == x_2 and y_1 == y_2:
                return

            err_2: int = err * 2
            if err_2 > -delta_y:
                err -= delta_y
                x_1 += step_x
            if err_2 < delta_x:
                err += delta_x
                y_1 += step_y

    def _brush(self, is_drawing: bool, extra_info: dict[str, Any]) -> None:
        """
        Handles brush tool.

        Args:
            drawing flag, extra info
        """

        num_cols: int
        num_rows: int
        hor_edge: int
        ver_edge: int

        num_cols, num_rows = self.grid.area.w, self.grid.area.h
        hor_edge, ver_edge = num_cols - self.grid.brush_dim, num_rows - self.grid.brush_dim

        self.grid.selected_tiles.append((self._mouse_col, self._mouse_row))
        if extra_info["mirror_x"]:
            self.grid.selected_tiles.extend([
                (hor_edge - x, y) for x, y in self.grid.selected_tiles
            ])
        if extra_info["mirror_y"]:
            self.grid.selected_tiles.extend([
                (x, ver_edge - y) for x, y in self.grid.selected_tiles
            ])

        if is_drawing:
            x_1: int = min(max(self._prev_mouse_col, -self.grid.brush_dim + 1), num_cols - 1)
            y_1: int = min(max(self._prev_mouse_row, -self.grid.brush_dim + 1), num_rows - 1)
            x_2: int = min(max(self._mouse_col, -self.grid.brush_dim + 1), num_cols - 1)
            y_2: int = min(max(self._mouse_row, -self.grid.brush_dim + 1), num_rows - 1)
            self._add_tiles_in_line(x_1, y_1, x_2, y_2)

            if extra_info["mirror_x"]:
                self.grid.changed_tiles.extend(
                    [(hor_edge - x, y) for x, y in self.grid.changed_tiles]
                )
            if extra_info["mirror_y"]:
                self.grid.changed_tiles.extend(
                    [(x, ver_edge - y) for x, y in self.grid.changed_tiles]
                )

            # Scale to brush dim
            self.grid.changed_tiles = [
                (x, y)
                for original_x, original_y in self.grid.changed_tiles
                for x in range(max(original_x, 0), min(original_x + self.grid.brush_dim, num_cols))
                for y in range(max(original_y, 0), min(original_y + self.grid.brush_dim, num_rows))
            ]

    def _bucket(self, is_drawing: bool, extra_info: dict[str, Any]) -> None:
        """
        Handles brush tool.

        Args:
            drawing flag, extra info
        """

        up_stop: int
        down_stop: int

        x: int = self._mouse_col
        y: int = self._mouse_row
        cols: int = self.grid.area.w
        rows: int = self.grid.area.h
        if x < 0 or x >= cols or y < 0 or y >= rows:
            return

        color: NDArray[np.uint8] = self.grid.tiles[x, y]
        # TODO: precompute mask, mask and visitable tiles should have y first
        mask: NDArray[np.bool_] = np.empty((cols + 2, rows), np.bool_)
        mask[0] = mask[-1] = False
        mask[1:-1] = (self.grid.tiles == color).all(2)

        filled_mask: NDArray[np.bool_] = np.zeros((cols, rows), np.bool_)
        visitable_tiles: NDArray[np.bool_] = np.ones((cols + 2, rows), np.bool_)
        visitable_tiles[0] = visitable_tiles[-1] = False

        stack: deque[XY] = deque([(x, y)])
        shifted_full_col: NDArray[np.bool_] = np.empty(rows, np.bool)
        shifted_full_col[0] = False
        while len(stack) != 0:
            x, y = stack.popleft()

            up_tiles: Any = mask[x + 1, :y + 1]
            try:
                up_stop = up_tiles[::-1].tolist().index(False)
            except ValueError:
                up_stop = up_tiles.size
            start_y: int = y - up_stop + 1

            down_tiles: Any = mask[x + 1, y:]
            try:
                down_stop = down_tiles.tolist().index(False)
            except ValueError:
                down_stop = down_tiles.size
            end_y: int = y + down_stop

            filled_mask[x, start_y:end_y], visitable_tiles[x + 1, start_y:end_y] = True, False
            shifted_col = shifted_full_col[:end_y - start_y]
            indexes: NDArray[np.int_] = np.arange(start_y, end_y, dtype=np.int_)

            # Analyzing column anyway is faster than doing any checks for skip
            prev_col_sliced_mask: NDArray[np.bool_] = mask[x, start_y:end_y]

            # Starts of True sequences
            shifted_col[1:] = prev_col_sliced_mask[:-1]
            prev_col_starts_mask: NDArray[np.bool_] = (
                prev_col_sliced_mask & ~shifted_col & visitable_tiles[x, start_y:end_y]
            )
            prev_col_starts: NDArray[np.int_] = indexes[prev_col_starts_mask]
            if prev_col_starts.size != 0:
                stack.extend(zip([x - 1] * prev_col_starts.size, prev_col_starts))

            # Analyzing column anyway is faster than doing any checks for skip
            next_col_sliced_mask: NDArray[np.bool_] = mask[x + 2, start_y:end_y]

            # Starts of True sequences
            shifted_col[1:] = next_col_sliced_mask[:-1]
            next_col_starts_mask: NDArray[np.bool_] = (
                next_col_sliced_mask & ~shifted_col & visitable_tiles[x + 2, start_y:end_y]
            )
            next_col_starts: NDArray[np.int_] = indexes[next_col_starts_mask]
            if next_col_starts.size != 0:
                stack.extend(zip([x + 1] * next_col_starts.size, next_col_starts))

        selected_positions: list[Any] = np.argwhere(filled_mask).tolist()
        self.grid.selected_tiles = [(x, y) for x, y in selected_positions]
        if is_drawing:
            self.grid.changed_tiles = self.grid.selected_tiles

    def _handle_draw(
            self, mouse: Mouse, keyboard: Keyboard, hex_color: HexColor, tool_info: ToolInfo
    ) -> bool:
        """
        Handles grid drawing.

        Args:
            mouse, keyboard, hexadecimal color, tool info
        Returns:
            changed flag
        """

        rgba_color: RGBAColor
        tool_name: str
        extra_tool_info: dict[str, Any]

        prev_selected_tiles: list[XY] = self.grid.selected_tiles  # Copying isn't necessary
        self.grid.selected_tiles = []

        self._handle_tile_info(mouse, keyboard)
        is_coloring: bool = mouse.pressed[MOUSE_LEFT] or K_RETURN in keyboard.pressed
        is_erasing: bool = mouse.pressed[MOUSE_RIGHT] or K_BACKSPACE in keyboard.pressed
        is_drawing: bool = is_coloring or is_erasing

        tool_name, extra_tool_info = tool_info
        if tool_name == "brush":
            self._brush(is_drawing, extra_tool_info)
        elif tool_name == "bucket":
            self._bucket(is_drawing, extra_tool_info)

        if is_coloring:
            rgba_color = (
                int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), 255
            )
        else:
            rgba_color = (0, 0, 0, 0)
        did_change: bool = self.grid.upt_section(rgba_color, prev_selected_tiles)

        return did_change

    def _move(self, mouse: Mouse) -> None:
        """
        Moves the section of the grid that is drawn, it's faster when moving the mouse faster.

        Args:
            mouse
        """

        tiles_traveled: int

        x_speed: int = int(abs(self._prev_mouse_x - mouse.x) ** 1.25)
        if mouse.x > self._prev_mouse_x:
            x_speed = -x_speed
        self._traveled_x += x_speed

        y_speed: int = int(abs(self._prev_mouse_y - mouse.y) ** 1.25)
        if mouse.y > self._prev_mouse_y:
            y_speed = -y_speed
        self._traveled_y += y_speed

        if abs(self._traveled_x) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_x / self.grid.grid_tile_dim)
            self._traveled_x -= tiles_traveled * self.grid.grid_tile_dim

            uncapped_offset_x: int = self.grid.offset.x + tiles_traveled
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
            changed flag
        """

        prev_num_visible_cols: int
        prev_num_visible_rows: int
        prev_offset_x: int
        prev_offset_y: int

        grid: Grid = self.grid
        prev_num_visible_cols, prev_num_visible_rows = grid.visible_area.w, grid.visible_area.h
        prev_offset_x, prev_offset_y = grid.offset.x, grid.offset.y

        if mouse.pressed[MOUSE_WHEEL]:
            self._move(mouse)
        else:
            self._traveled_x = self._traveled_y = 0

        did_change: bool = False
        if grid == mouse.hovered_obj or grid == self._prev_hovered_obj:  # Extra frame to draw
            did_change = self._handle_draw(mouse, keyboard, hex_color, tool_info)
        elif grid.selected_tiles != []:
            grid.leave()

        if grid == mouse.hovered_obj and (mouse.scroll_amount != 0 or keyboard.timed != []):
            grid.zoom(mouse, keyboard)

        if keyboard.is_ctrl_on and K_r in keyboard.pressed:
            grid.visible_area.w = min(GRID_INIT_VISIBLE_DIM, grid.area.w)
            grid.visible_area.h = min(GRID_INIT_VISIBLE_DIM, grid.area.h)
            grid.offset.x = grid.offset.y = 0
            self._traveled_x = self._traveled_y = 0

        did_visible_cols_change: bool = grid.visible_area.w != prev_num_visible_cols
        did_visible_rows_change: bool = grid.visible_area.h != prev_num_visible_rows
        did_offset_change: bool = grid.offset.x != prev_offset_x or grid.offset.y != prev_offset_y
        if did_visible_cols_change or did_visible_rows_change or did_offset_change:
            grid.refresh_grid_img()
            grid.refresh_minimap_img()

        self._prev_mouse_x, self._prev_mouse_y = mouse.x, mouse.y
        self._prev_hovered_obj = mouse.hovered_obj

        return did_change
