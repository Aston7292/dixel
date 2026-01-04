"""
Class to edit a grid of pixels with a minimap.

Grid and minimap are refreshed automatically when offset or visible area changes.
"""

from zlib import decompress
from collections.abc import Callable
from typing import Literal, Never, Self, TypeAlias, Any

import numpy as np
from pygame import Rect, K_BACKSPACE, K_RETURN, K_DELETE, K_r, K_y, K_z
from numpy import uint8, uint16, uint32, int32, intp, bool_, newaxis
from numpy.typing import NDArray

from src.classes.tools_manager import ToolName, ToolInfo
from src.classes.grid import Grid
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE, KEYBOARD

import src.vars as my_vars
from src.obj_utils import UIElement
from src.type_utils import XY, HexColor, BlitInfo, RectPos
from src.consts import (
    BLACK,
    MOUSE_LEFT, MOUSE_WHEEL, MOUSE_RIGHT,
    BG_LAYER, TEXT_LAYER, TOP_LAYER,
)

_ToolsFuncs: TypeAlias = dict[ToolName, Callable[[dict[str, Any]], None]]

def _get_tiles_in_line(x_1: int, y_1: int, x_2: int, y_2: int) -> NDArray[int32]:
    """
    Gets the tiles that touch a line using Bresenham's Line Algorithm.

    Args:
        line start x, line start y, line end x, line end y
    Returns:
        tiles
    """

    delta_x: int = abs(x_2 - x_1)
    delta_y: int = abs(y_2 - y_1)
    step_x: Literal[-1, 1] = 1 if x_1 < x_2 else -1
    step_y: Literal[-1, 1] = 1 if y_1 < y_2 else -1
    err: int = delta_x - delta_y

    tiles: list[XY] = []
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


class GridManager(UIElement):
    """Class to edit a grid of pixels with a minimap."""

    __slots__ = (
        "_is_hovering", "_last_mouse_move_time",
        "_prev_mouse_col", "_prev_mouse_row", "_mouse_col", "_mouse_row",
        "_traveled_x", "_traveled_y",
        "_is_erasing", "_is_coloring", "_did_stop_erasing", "_did_stop_coloring",
        "is_x_mirror_on", "is_y_mirror_on", "_can_leave", "_can_add_to_history",
        "_tools_funcs", "rgb_eye_dropped_color", "saved_col", "saved_row",
        "grid", "_hovering_text_label",
        "_prev_hovered_obj",
    )

    def __init__(self: Self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object and wrapper info.

        Args:
            grid position, minimap position
        """

        super().__init__()

        self._is_hovering: bool = False
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

        self._can_leave: bool = False
        self._can_add_to_history: bool = False

        self._tools_funcs: _ToolsFuncs = {
            "pencil": self._pencil,
            "eraser": self._eraser,
            "bucket": self._bucket,
            "eye_dropper": self._eye_dropper,
            "line": self._line,
            "rect": self._rect,
        }
        self.rgb_eye_dropped_color: tuple[int, int, int] | None = None
        # Used for line, rect, etc.
        self.saved_col: int | None = None
        self.saved_row: int | None = None

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self._hovering_text_label: TextLabel = TextLabel(
            RectPos(MOUSE.x, MOUSE.y, "topleft"),
            "Enter\nBackspace", BG_LAYER + TOP_LAYER - TEXT_LAYER,
            h=12, bg_color=BLACK
        )
        self._hovering_text_label.rec_set_active(False)
        self._hovering_text_label.should_follow_parent = False

        self._prev_hovered_obj: UIElement | None = MOUSE.hovered_obj

        self.sub_objs = (self.grid, self._hovering_text_label)

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._last_mouse_move_time = my_vars.ticks

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._prev_hovered_obj = None
        self._traveled_x = self._traveled_y = 0
        self.rgb_eye_dropped_color = self.saved_col = self.saved_row = None

        if self._can_add_to_history:
            self.grid.add_to_history()
            self._can_add_to_history = False

        self._hovering_text_label.rec_set_active(False)

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
        """Refreshes the previous and current mouse tiles and handles keyboard movement."""

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

    def _pencil(self: Self, _sub_tools_data: dict[str, Any]) -> None:
        """
        Handles the pencil tool.

        Args:
            sub tools data
        """

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

        xs: NDArray[int32] = (selected_xs[:, newaxis] + repeated_cols[newaxis, :]).ravel()
        ys: NDArray[int32] = (selected_ys[:, newaxis] + repeated_rows[newaxis, :]).ravel()
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

    def _eraser(self: Self, sub_tools_data: dict[str, Any]) -> None:
        """
        Handles the eraser tool.

        Args:
            sub tools data
        """

        self._pencil(sub_tools_data)
        self._is_erasing = self._is_erasing or self._is_coloring
        self._is_coloring = False

    def _init_bucket_stack(self: Self, mask: NDArray[bool_]) -> list[tuple[intp, uint16, uint16]]:
        """
        Initializes the stack for the bucket tool.

        Args:
            tiles mask
        Returns:
            stack
        """

        up_tiles: NDArray[bool_] = mask[self._mouse_col, :self._mouse_row + 1]
        up_stop: intp | int = up_tiles[::-1].argmin() or up_tiles.size
        first_y: uint16 = uint16(self._mouse_row - up_stop   + 1)

        down_tiles: NDArray[bool_] = mask[self._mouse_col, self._mouse_row:]
        down_stop: intp | int = down_tiles.argmin() or down_tiles.size
        last_y: uint16  = uint16(self._mouse_row + down_stop - 1)

        return [(intp(self._mouse_col), first_y, last_y)]

    def _bucket(self: Self, sub_tools_data: dict[str, Any]) -> None:
        """
        Handles the bucket tool using the scan-line algorithm, includes a color fill.

        Args:
            sub tools data (color fill)
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
        if sub_tools_data["color_fill"]:
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

            if visitable_tiles[x, start_y] or visitable_tiles[x, end_y]:
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

    def _eye_dropper(self: Self, _sub_tools_data: dict[str, Any]) -> None:
        """
        Handles the eye dropper tool.

        Args:
            sub tools data
        """

        if not self._is_hovering:
            return

        self.grid.selected_tiles[self._mouse_col, self._mouse_row] = True
        if self._is_coloring:
            self.rgb_eye_dropped_color = self.grid.tiles[self._mouse_col, self._mouse_row][:3]
        self._is_erasing = self._is_coloring = False

    def _line(self: Self, _sub_tools_data: dict[str, Any]) -> None:
        """
        Handles the line tool.

        Args:
            sub tools data
        """

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

        xs: NDArray[int32] = selected_xs[:, newaxis] + repeated_cols[newaxis, :]
        ys: NDArray[int32] = selected_ys[:, newaxis] + repeated_rows[newaxis, :]
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

    def _rect(self: Self, sub_tools_data: dict[str, Any]) -> None:
        """
        Handles the rect tool.

        Args:
            sub tools data (fill)
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
                max(y, 0):y + self.grid.brush_dim,
            ] = True

            if self._did_stop_erasing or self._did_stop_coloring:
                self.saved_col, self.saved_row = x, y
        else:
            start_x: int = min(self.saved_col, self._mouse_col)
            start_y: int = min(self.saved_row, self._mouse_row)
            end_x: int   = max(self.saved_col, self._mouse_col) + 1
            end_y: int   = max(self.saved_row, self._mouse_row) + 1

            # Rect can't be smaller than brush_dim
            end_x = max(end_x, start_x + self.grid.brush_dim)
            end_y = max(end_y, start_y + self.grid.brush_dim)

            if sub_tools_data["fill"]:
                self.grid.selected_tiles[start_x:end_x, start_y:end_y] = True
            else:
                self.grid.selected_tiles[
                    start_x:start_x + self.grid.brush_dim,
                    start_y:end_y,
                ] = True
                self.grid.selected_tiles[
                    start_x:end_x,
                    start_y:start_y + self.grid.brush_dim,
                ] = True
                self.grid.selected_tiles[
                    end_x - self.grid.brush_dim:end_x,
                    start_y:end_y,
                ] = True
                self.grid.selected_tiles[
                    start_x:end_x,
                    end_y - self.grid.brush_dim:end_y,
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
        Handles grid drawing via tools and refreshes the unscaled grid image.

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
        sub_tools_data: dict[str, Any] = tool_info[1]
        self._tools_funcs[tool_name](sub_tools_data)

        selected_tiles_bytes: bytes = np.packbits(self.grid.selected_tiles).tobytes()
        if self._is_erasing or self._is_coloring:
            did_draw = self.grid.upt_section(self._is_erasing, hex_color)
        else:
            did_draw = False

        # Comparing bytes in this situation is faster
        return did_draw, selected_tiles_bytes != prev_selected_tiles_bytes

    def _refresh(
            self: Self, did_draw: bool,
            prev_visible_cols: int, prev_visible_rows: int, prev_offset_x: int, prev_offset_y: int,
            did_selected_tiles_change: bool
    ) -> None:
        """
        Refreshes the hovering text label and grid info.

        Args:
            drawn flag,
            previous visible columns, previous visible rows, previous x offset, previous y offset,
            selected tiles changed flag
        """

        if not self._is_hovering or (MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y):
            self._last_mouse_move_time = my_vars.ticks
            self._hovering_text_label.rec_set_active(False)
        if self._is_hovering and (my_vars.ticks - self._last_mouse_move_time >= 750):
            self._hovering_text_label.rec_move_to(MOUSE.x + 4, MOUSE.y, should_scale=False)
            if not self._hovering_text_label.is_active:
                self._hovering_text_label.start_animation()
                self._hovering_text_label.rec_set_active(True)

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
            self.rgb_eye_dropped_color = None
            did_draw, did_selected_tiles_change = self._handle_draw(hex_color, tool_info)

            self._can_leave = True
            if did_draw:
                self._can_add_to_history = True
        elif self._can_leave:
            self.grid.leave()
            self._can_leave = False

        if K_DELETE in KEYBOARD.pressed:
            self.saved_col = self.saved_row = None

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
