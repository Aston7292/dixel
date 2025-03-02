"""
Paintable pixel grid with a minimap.

Grid and minimap are refreshed automatically when offset or visible area changes.
"""

from typing import TypeAlias, Final, Optional, Any

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.utils import Point, RectPos, Size, ObjInfo, Mouse, Keyboard, get_pixels, resize_obj
from src.file_utils import get_img_state
from src.type_utils import XY, WH, RGBAColor, HexColor, ToolInfo, LayeredBlitInfo
from src.consts import (
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT, EMPTY_TILE_ARR, NUM_TILE_ROWS, NUM_TILE_COLS, BG_LAYER,
    IMG_STATE_OK, IMG_STATE_DENIED, IMG_STATE_LOCKED
)


BlitSequence: TypeAlias = list[tuple[pg.Surface, XY]]

TRANSPARENT_GRAY: Final[pg.Color] = pg.Color(150, 150, 150, 150)


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

    if is_ctrl_on:
        return 0, 0

    rel_mouse_coord -= value
    has_exited_visible_area: bool = rel_mouse_coord < 0
    if has_exited_visible_area:
        extra_offset: int = rel_mouse_coord
        offset = max(offset + extra_offset, 0)
        rel_mouse_coord = 0

    return rel_mouse_coord, offset


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

    if is_ctrl_on:
        return visible_side - 1, side - visible_side

    rel_mouse_coord += value
    has_exited_visible_area: bool = rel_mouse_coord > visible_side - 1
    if has_exited_visible_area:
        extra_offset: int = rel_mouse_coord - visible_side + 1
        offset = min(offset + extra_offset, side - visible_side)
        rel_mouse_coord = visible_side - 1

    return rel_mouse_coord, offset


class Grid:
    """Class to create a pixel grid and its minimap."""

    __slots__ = (
        "_grid_init_pos", "area", "init_visible_dim", "visible_area", "grid_tile_dim",
        "_grid_dim_cap", "grid_rect", "tiles", "brush_dim", "selected_tile_img",
        "_minimap_init_pos", "_minimap_dim_cap", "_minimap_rect",
        "_no_indicator_small_minimap_img", "offset", "selected_tiles", "changed_tiles", "layer",
        "blit_sequence", "_win_w_ratio", "_win_h_ratio", "cursor_type"
    )

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
        self.init_visible_dim: int = 32
        self.visible_area: Size = Size(self.init_visible_dim, self.init_visible_dim)
        self.grid_tile_dim: float = 18
        self._grid_dim_cap: int = 600

        self.grid_rect: pg.Rect = pg.Rect()

        self.tiles: NDArray[np.uint8] = np.empty((0, 0, 4), np.uint8)

        self.brush_dim: int = 1
        self.selected_tile_img: pg.Surface = pg.Surface(
            (NUM_TILE_COLS, NUM_TILE_ROWS), pg.SRCALPHA
        )
        self.selected_tile_img.fill((125, 125, 125, 150))

        self._minimap_init_pos: RectPos = minimap_pos
        self._minimap_dim_cap: int = 256

        self._minimap_rect: pg.Rect = pg.Rect()
        # Having a version where 1 tile = 1 pixel is better for scaling, used for update section
        self._no_indicator_small_minimap_img: pg.Surface

        self.offset: Point = Point(0, 0)
        self.selected_tiles: list[XY] = []
        self.changed_tiles: list[XY] = []

        self.layer: int = BG_LAYER
        self.blit_sequence: list[LayeredBlitInfo] = [
            (pg.Surface((0, 0)), self.grid_rect, self.layer),
            (pg.Surface((0, 0)), self._minimap_rect, self.layer)
        ]
        self._win_w_ratio, self._win_h_ratio = 1, 1
        self.cursor_type: int = pg.SYSTEM_CURSOR_CROSSHAIR

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
        wh: WH
        init_w: float
        init_h: float

        dim_cap: int = self._grid_dim_cap
        init_tile_dim: float = min(dim_cap / self.visible_area.w, dim_cap / self.visible_area.h)
        init_w, init_h = self.visible_area.w * init_tile_dim, self.visible_area.h * init_tile_dim

        xy, wh = resize_obj(
            self._grid_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )
        grid_img: pg.Surface = pg.transform.scale(small_grid_img, wh)
        self.grid_rect.size = wh
        setattr(self.grid_rect, self._grid_init_pos.coord_type, xy)
        self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)

        self.blit_sequence[0] = (grid_img, self.grid_rect, self.layer)

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
            (col * NUM_TILE_COLS, row * NUM_TILE_ROWS) for col, row in self.selected_tiles
        ]

        blit_sequence: BlitSequence = [
            (self.selected_tile_img, (col - scaled_offset_x, row - scaled_offset_y))
            for col, row in scaled_selected_tiles
        ]
        small_img.fblits(blit_sequence)
        self._resize_grid(small_img)

    def _refresh_minimap_rect(self) -> None:
        """Refreshes the minimap rect."""

        dim_cap: int = self._minimap_dim_cap
        init_tile_dim: float = min(dim_cap / self.area.w, dim_cap / self.area.h)
        init_w, init_h = self.area.w * init_tile_dim, self.area.h * init_tile_dim

        xy, wh = resize_obj(
            self._minimap_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )
        self._minimap_rect.size = wh
        setattr(self._minimap_rect, self._minimap_init_pos.coord_type, xy)

    def refresh_minimap_img(self) -> None:
        """Refreshes the minimap image scaled to the minimap rect."""

        # Having a version where 1 tile = 1 pixel is better for scaling
        small_img: pg.Surface = self._no_indicator_small_minimap_img.copy()

        indicator: pg.Surface = pg.Surface(
            (self.visible_area.w * NUM_TILE_COLS, self.visible_area.h * NUM_TILE_ROWS), pg.SRCALPHA
        )
        pg.draw.rect(indicator, TRANSPARENT_GRAY, indicator.get_rect(), 2)

        small_img.blit(indicator, (self.offset.x * NUM_TILE_COLS, self.offset.y * NUM_TILE_ROWS))
        minimap_img: pg.Surface = pg.transform.scale(small_img, self._minimap_rect.size)

        self.blit_sequence[1] = (minimap_img, self._minimap_rect, self.layer)

    def refresh_full(self) -> None:
        """Refreshes all the tiles on the minimap and retrieves the grid."""

        tiles: NDArray[np.uint8] = self.tiles  # Copying isn't necessary

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles = tiles.repeat(NUM_TILE_COLS, 0).repeat(NUM_TILE_ROWS, 1)
        empty_tiles_mask: NDArray[np.bool_] = tiles[..., 3:4] == 0
        tiles = tiles[..., :3]

        empty_tiles: NDArray[np.uint8] = np.tile(EMPTY_TILE_ARR, (self.area.w, self.area.h, 1))
        tiles = np.where(empty_tiles_mask, empty_tiles, tiles)
        self._no_indicator_small_minimap_img = pg.surfarray.make_surface(tiles)

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
        tile_img: pg.Surface = pg.Surface((NUM_TILE_COLS, NUM_TILE_ROWS))
        empty_tile_img: pg.Surface = pg.surfarray.make_surface(EMPTY_TILE_ARR)

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

    def upt_section(self, rgba_color: RGBAColor, prev_selected_tiles: list[XY]) -> None:
        """
        Updates the changed tiles.

        Args:
            rgba color, previous selected tiles
        """

        # The tiles array has x and y flipped, when making it a surface, pygame uses it like this

        x: int
        y: int

        has_changed: bool = False

        unique_changed_tiles: set[XY] = set(self.changed_tiles)
        tiles: NDArray[np.uint8] = self.tiles
        for x, y in unique_changed_tiles:
            if tuple(tiles[x, y]) != rgba_color:
                has_changed = True
                tiles[x, y] = rgba_color

        if has_changed:
            self._refresh_section(unique_changed_tiles)
        elif self.selected_tiles != prev_selected_tiles:
            self.refresh_grid_img()
        self.changed_tiles = []

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
        self.selected_tile_img = pg.transform.scale(self.selected_tile_img, wh)
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

        prev_rel_mouse_col, prev_rel_mouse_row = rel_mouse_col, rel_mouse_row

        value: int = 1
        if keyboard.is_alt_on:
            value = self.brush_dim
        if keyboard.is_shift_on:
            value = max(self.visible_area.w, self.visible_area.h)

        if pg.K_LEFT in keyboard.timed:
            rel_mouse_col, self.offset.x = _dec_mouse_tile(
                rel_mouse_col, value, self.offset.x, keyboard.is_ctrl_on
            )
        if pg.K_RIGHT in keyboard.timed:
            rel_mouse_col, self.offset.x = _inc_mouse_tile(
                rel_mouse_col, value, self.offset.x, self.visible_area.w, self.area.w,
                keyboard.is_ctrl_on
            )
        if pg.K_UP in keyboard.timed:
            rel_mouse_row, self.offset.y = _dec_mouse_tile(
                rel_mouse_row, value, self.offset.y, keyboard.is_ctrl_on
            )
        if pg.K_DOWN in keyboard.timed:
            rel_mouse_row, self.offset.y = _inc_mouse_tile(
                rel_mouse_row, value, self.offset.y, self.visible_area.h, self.area.h,
                keyboard.is_ctrl_on
            )

        if rel_mouse_col != prev_rel_mouse_col or rel_mouse_row != prev_rel_mouse_row:
            # Mouse is in the center of the tile
            grid_tile_dim: float = self.grid_tile_dim
            rel_mouse_x: int = round(rel_mouse_col * grid_tile_dim + grid_tile_dim / 2)
            rel_mouse_y: int = round(rel_mouse_row * grid_tile_dim + grid_tile_dim / 2)
            pg.mouse.set_pos((self.grid_rect.x + rel_mouse_x, self.grid_rect.y + rel_mouse_y))

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

        # Amount is positive when zooming in and negative when zooming out, down (-), up (+).

        if should_reach_min_limit:
            self.visible_area.w = self.visible_area.h = 1
        elif should_reach_max_limit:
            self.visible_area.w, self.visible_area.h = self.area.w, self.area.h
        elif self.visible_area.w == self.visible_area.h:
            self.visible_area.w = max(min(self.visible_area.w - amount, self.area.w), 1)
            self.visible_area.h = max(min(self.visible_area.h - amount, self.area.h), 1)
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

        should_reach_min_limit: bool
        should_reach_max_limit: bool
        init_tile_dim: float

        amount: int = mouse.scroll_amount
        should_reach_min_limit, should_reach_max_limit = False, False
        if keyboard.is_ctrl_on:
            if pg.K_MINUS in keyboard.timed:
                amount = 1
                should_reach_min_limit = keyboard.is_shift_on
            if pg.K_PLUS in keyboard.timed:
                amount = -1
                should_reach_max_limit = keyboard.is_shift_on

        if amount != 0 or should_reach_min_limit or should_reach_max_limit:
            prev_mouse_col: int = int((mouse.x - self.grid_rect.x) / self.grid_tile_dim)
            prev_mouse_row: int = int((mouse.y - self.grid_rect.y) / self.grid_tile_dim)

            self._zoom_visible_area(amount, should_reach_min_limit, should_reach_max_limit)
            dim_cap: int = self._grid_dim_cap
            init_tile_dim = min(dim_cap / self.visible_area.w, dim_cap / self.visible_area.h)
            self.grid_tile_dim = init_tile_dim * min(self._win_w_ratio, self._win_h_ratio)

            mouse_col: int = int((mouse.x - self.grid_rect.x) / self.grid_tile_dim)
            mouse_row: int = int((mouse.y - self.grid_rect.y) / self.grid_tile_dim)

            uncapped_offset_x: int = self.offset.x + prev_mouse_col - mouse_col
            self.offset.x = max(min(uncapped_offset_x, self.area.w - self.visible_area.w), 0)
            uncapped_offset_y: int = self.offset.y + prev_mouse_row - mouse_row
            self.offset.y = max(min(uncapped_offset_y, self.area.h - self.visible_area.h), 0)

    def try_save_to_file(self, file_path: str) -> None:
        """
        Saves the tiles to a file.

        Args:
            file path
        """

        img_state: int = get_img_state(file_path, True)
        if img_state == IMG_STATE_OK:
            img: pg.Surface = pg.Surface((self.area.w, self.area.h), pg.SRCALPHA)

            pg.surfarray.blit_array(img, self.tiles[..., :3])
            pg.surfarray.pixels_alpha(img)[...] = self.tiles[..., 3]
            pg.image.save(img, file_path)
        else:
            print("Couldn't save.", end=" ")
            if img_state == IMG_STATE_DENIED:
                print("Permission denied.")
            elif img_state == IMG_STATE_LOCKED:
                print("File locked.")
            else:
                print(f"Unknown reason. State: {img_state}.")


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
        self._prev_mouse_col: int
        self._prev_mouse_row: int
        self._mouse_col: int
        self._mouse_row: int
        self._traveled_x: float
        self._traveled_y: float

        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()
        self._prev_hovered_obj: Optional[Grid] = None

        self._prev_mouse_col = self._prev_mouse_row = 0
        self._mouse_col = self._mouse_row = 0
        self._traveled_x = self._traveled_y = 0

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self.blit_sequence: list[LayeredBlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.grid)]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

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

        # By setting prev_mouse_tile before changing offset you can draw a line with shift/ctrl
        self._prev_mouse_col = prev_rel_mouse_col + self.grid.offset.x - self.grid.brush_dim // 2
        self._prev_mouse_row = prev_rel_mouse_row + self.grid.offset.y - self.grid.brush_dim // 2

        if keyboard.timed != []:
            # Changes the offset
            rel_mouse_col, rel_mouse_row = self.grid.move_with_keys(
                keyboard, rel_mouse_col, rel_mouse_row
            )

        self._mouse_col = rel_mouse_col + self.grid.offset.x - self.grid.brush_dim // 2
        self._mouse_row = rel_mouse_row + self.grid.offset.y - self.grid.brush_dim // 2

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

        self.grid.selected_tiles = [(self._mouse_col, self._mouse_row)]
        if extra_info["mirror_x"]:
            self.grid.selected_tiles.extend([
                (hor_edge - x, y) for x, y in self.grid.selected_tiles
            ])
        if extra_info["mirror_y"]:
            self.grid.selected_tiles.extend([
                (x, ver_edge - y) for x, y in self.grid.selected_tiles
            ])

        if is_drawing:
            x_1: int = max(min(self._prev_mouse_col, num_cols - 1), -self.grid.brush_dim + 1)
            y_1: int = max(min(self._prev_mouse_row, num_rows - 1), -self.grid.brush_dim + 1)
            x_2: int = max(min(self._mouse_col, num_cols - 1), -self.grid.brush_dim + 1)
            y_2: int = max(min(self._mouse_row, num_rows - 1), -self.grid.brush_dim + 1)
            self._add_tiles_in_line(x_1, y_1, x_2, y_2)

            if extra_info["mirror_x"]:
                self.grid.changed_tiles.extend(
                    [(hor_edge - x, y) for x, y in self.grid.changed_tiles]
                )
            if extra_info["mirror_y"]:
                self.grid.changed_tiles.extend(
                    [(x, ver_edge - y) for x, y in self.grid.changed_tiles]
                )

            # Scale to brush size
            self.grid.changed_tiles = [
                (x, y)
                for original_x, original_y in self.grid.changed_tiles
                for x in range(max(original_x, 0), min(original_x + self.grid.brush_dim, num_cols))
                for y in range(max(original_y, 0), min(original_y + self.grid.brush_dim, num_rows))
            ]

    def _handle_draw(
            self, mouse: Mouse, keyboard: Keyboard, hex_color: HexColor, tool_info: ToolInfo
    ) -> None:
        """
        Handles grid drawing.

        Args:
            mouse, keyboard, hexadecimal color, tool info
        """

        tool_name: str
        extra_tool_info: dict[str, Any]

        prev_selected_tiles: list[XY] = self.grid.selected_tiles  # Copying isn't necessary

        self._handle_tile_info(mouse, keyboard)
        is_coloring: bool = mouse.pressed[MOUSE_LEFT] or pg.K_RETURN in keyboard.pressed
        is_erasing: bool = mouse.pressed[MOUSE_RIGHT] or pg.K_BACKSPACE in keyboard.pressed

        tool_name, extra_tool_info = tool_info
        if tool_name == "brush":
            self._brush(is_coloring or is_erasing, extra_tool_info)

        rgba_color: RGBAColor
        if is_coloring:
            rgba_color = (
                int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), 255
            )
        else:
            rgba_color = (0, 0, 0, 0)

        self.grid.upt_section(rgba_color, prev_selected_tiles)

    def _move(self, mouse: Mouse) -> None:
        """
        Allows changing the section of the grid that is drawn.

        Args:
            mouse
        """

        tiles_traveled: int

        self._traveled_x += self._prev_mouse_x - mouse.x
        if abs(self._traveled_x) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_x / self.grid.grid_tile_dim)
            self._traveled_x -= tiles_traveled * self.grid.grid_tile_dim

            max_offset_x: int = self.grid.area.w - self.grid.visible_area.w
            self.grid.offset.x = max(min(self.grid.offset.x + tiles_traveled, max_offset_x), 0)

        self._traveled_y += self._prev_mouse_y - mouse.y
        if abs(self._traveled_y) >= self.grid.grid_tile_dim:
            tiles_traveled = int(self._traveled_y / self.grid.grid_tile_dim)
            self._traveled_y -= tiles_traveled * self.grid.grid_tile_dim

            max_offset_y: int = self.grid.area.h - self.grid.visible_area.h
            self.grid.offset.y = max(min(self.grid.offset.y + tiles_traveled, max_offset_y), 0)

    def upt(
            self, mouse: Mouse, keyboard: Keyboard, hex_color: HexColor, tool_info: ToolInfo
    ) -> None:
        """
        Allows drawing, moving and zooming.

        Args:
            mouse, keyboard, hexadecimal color, brush size, tool info
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

        if grid == mouse.hovered_obj or grid == self._prev_hovered_obj:  # Extra frame to draw
            self._handle_draw(mouse, keyboard, hex_color, tool_info)
        elif grid.selected_tiles != []:
            grid.leave()

        if grid == mouse.hovered_obj and (mouse.scroll_amount != 0 or keyboard.timed != []):
            grid.zoom(mouse, keyboard)

        if keyboard.is_ctrl_on and pg.K_r in keyboard.pressed:
            grid.visible_area.w = min(grid.init_visible_dim, grid.area.w)
            grid.visible_area.h = min(grid.init_visible_dim, grid.area.h)
            grid.offset.x = grid.offset.y = 0
            self._traveled_x = self._traveled_y = 0

        have_visible_cols_changed: bool = grid.visible_area.w != prev_num_visible_cols
        have_visible_rows_changed: bool = grid.visible_area.h != prev_num_visible_rows
        has_offset_changed: bool = grid.offset.x != prev_offset_x or grid.offset.y != prev_offset_y
        if have_visible_cols_changed or have_visible_rows_changed or has_offset_changed:
            grid.refresh_grid_img()
            grid.refresh_minimap_img()

        self._prev_mouse_x, self._prev_mouse_y = mouse.x, mouse.y
        self._prev_hovered_obj = mouse.hovered_obj
