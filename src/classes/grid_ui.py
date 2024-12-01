"""Interface to modify the grid."""

from math import ceil
from typing import Union, Final, Optional, Any

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, CHECKBOX_1_IMG, CHECKBOX_2_IMG
from src.classes.clickable import Checkbox
from src.classes.text_label import TextLabel

from src.utils import RectPos, Size, Ratio, ObjInfo, MouseInfo, resize_obj
from src.type_utils import PosPair, SizePair, BlitSequence, LayeredBlitInfo
from src.consts import EMPTY_TILE_IMG, BG_LAYER, ELEMENT_LAYER

SelectionType = Union["NumSlider"]

MOVEMENT_THRESHOLD: Final[int] = 10
SPEED_SCALING_FACTOR: Final[int] = MOVEMENT_THRESHOLD * 15
MAX_DIM: Final[int] = 256


class NumSlider:
    """Class that allows picking a number in a predefined range either by sliding or typing."""

    __slots__ = (
        "value", "input_box", "_prev_mouse_x", "_traveled_x", "_speeds", "_is_sliding", "objs_info"
    )

    def __init__(
        self, pos: RectPos, value: int, text: str, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the slider and text.

        Args:
            position, value, text, base layer (default = BG_LAYER)
        """

        self.value: int = value
        self.input_box: NumInputBox = NumInputBox(pos, str(self.value), base_layer)

        self._prev_mouse_x: int = pg.mouse.get_pos()[0]
        self._traveled_x: int = 0
        self._speeds: list[int] = []
        self._is_sliding: bool = False

        extra_text_label: TextLabel = TextLabel(
            RectPos(self.input_box.rect.x - 10, self.input_box.rect.centery, "midright"), text,
            base_layer
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(self.input_box), ObjInfo(extra_text_label)]

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self._is_sliding = False
        self._traveled_x = 0
        self._speeds.clear()

    def set_value(self, value: int) -> None:
        """
        Sets the slider on a specific value.

        Args:
            value
        """

        self._traveled_x = 0
        self._speeds.clear()
        self.value = value
        self.input_box.text_label.set_text(str(self.value))
        self.input_box.bounded_set_cursor_i(0)

    def _handle_hover(self, mouse_info: MouseInfo) -> None:
        """
        Handles the hovering behavior.

        Args:
            mouse info
        """

        if not self.input_box.is_hovering:
            if not mouse_info.pressed[0]:
                self._is_sliding = False
                self._traveled_x = 0
                self._speeds.clear()
        else:
            self._is_sliding = mouse_info.pressed[0]
            if not mouse_info.pressed[0]:
                self._traveled_x = 0
                self._speeds.clear()

    def slide(self, mouse_info: MouseInfo, temp_input_box_text: str) -> str:
        """
        Changes the value with the mouse.

        Args:
            mouse info, input box text
        """

        # Slide faster depending on the mouse movement speed

        local_temp_input_box_text: str = temp_input_box_text

        if self._is_sliding:
            speed: int = mouse_info.x - self._prev_mouse_x
            if speed:
                self._speeds.append(speed)

            self._traveled_x += speed
            if abs(self._traveled_x) >= MOVEMENT_THRESHOLD:
                units_traveled: float = self._traveled_x / MOVEMENT_THRESHOLD
                avg_speed: float = sum(self._speeds) / len(self._speeds)
                scaled_avg_speed: float = max(avg_speed / SPEED_SCALING_FACTOR, 1.0)
                scaled_units: int = int(units_traveled * scaled_avg_speed)
                value: int = max(min(self.value + scaled_units, MAX_DIM), 1)

                local_temp_input_box_text = str(value)
                self._speeds.clear()
                self._traveled_x -= int(units_traveled) * MOVEMENT_THRESHOLD

        return local_temp_input_box_text

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int],
            selection: SelectionType
    ) -> bool:
        """
        Allows to select a color either by sliding or typing.

        Args:
            hovered object (can be None), mouse info, keys, selected object
        Returns:
            True if the slider was clicked else False
        """

        is_input_box_clicked: bool
        temp_input_box_text: str
        is_input_box_clicked, temp_input_box_text = self.input_box.upt(
            hovered_obj, mouse_info, keys, (1, MAX_DIM), selection == self
        )

        self._handle_hover(mouse_info)

        future_input_box_text: str = self.slide(mouse_info, temp_input_box_text)
        if self.input_box.text_label.text != future_input_box_text:
            self.value = int(future_input_box_text or 1)
            self.input_box.text_label.set_text(future_input_box_text)
            self.input_box.bounded_set_cursor_i()

        self._prev_mouse_x = mouse_info.x

        return is_input_box_clicked


class GridUI(UI):
    """Class to create an interface that allows modifying the grid, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_img", "_preview_rect", "_preview_init_size",
        "_preview_layer", "_h_slider", "_w_slider", "values_ratio", "_preview_tiles", "checkbox",
        "_selection_i", "_min_win_ratio", "_small_preview_img"
    )

    def __init__(self, pos: RectPos, area: Size) -> None:
        """
        Initializes the interface.

        Args:
            position, grid area
        """

        # Tiles dimension is a float to represent the full size more accurately when resizing

        super().__init__(pos, "MODIFY GRID")

        self._preview_init_pos: RectPos = RectPos(
            self._rect.centerx, self._rect.centery + 40, "center"
        )

        self._preview_img: pg.Surface = pg.Surface((300, 300))
        preview_xy: PosPair = (self._preview_init_pos.x, self._preview_init_pos.y)
        self._preview_rect: pg.Rect = self._preview_img.get_rect(
            **{self._preview_init_pos.coord_type: preview_xy}
        )

        self._preview_init_size: Size = Size(*self._preview_rect.size)

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        self._h_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20, self._preview_rect.y - 25, "bottomleft"),
            area.h, "height", self._base_layer
        )
        self._w_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20, self._h_slider.input_box.rect.y - 25, "bottomleft"),
            area.w, "width", self._base_layer
        )
        self.values_ratio: Ratio = Ratio(1.0, 1.0)

        self._preview_tiles: NDArray[np.uint8] = np.empty(
            (self._h_slider.value, self._w_slider.value, 4), np.uint8
        )

        checkbox_y: int = self._h_slider.input_box.rect.centery
        self.checkbox: Checkbox = Checkbox(
            RectPos(self._preview_rect.right - 20, checkbox_y, "midright"),
            (CHECKBOX_1_IMG, CHECKBOX_2_IMG), "keep ratio", "(CTRL+K)", self._base_layer
        )

        self._selection_i: int = 0
        self._min_win_ratio: float = 1.0  # Keeps the tiles as squares

        # Having a version where 1 tile = 1 pixel is better for scaling
        self._small_preview_img: pg.Surface = pg.Surface(
            (self._w_slider.value * 2, self._h_slider.value * 2)
        )

        self.objs_info.extend((
            ObjInfo(self._w_slider), ObjInfo(self._h_slider),
            ObjInfo(self.checkbox)
        ))

    def blit(self) -> list[LayeredBlitInfo]:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: list[LayeredBlitInfo] = super().blit()
        sequence.append((self._preview_img, self._preview_rect.topleft, self._preview_layer))

        return sequence

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self._selection_i = 0

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        self._min_win_ratio = min(win_ratio.w, win_ratio.h)

        super().resize(win_ratio)

        unscaled_preview_tile_dim: float = min(
            self._preview_init_size.w / self._w_slider.value,
            self._preview_init_size.h / self._h_slider.value
        )
        unscaled_preview_wh: tuple[float, float] = (
            self._w_slider.value * unscaled_preview_tile_dim,
            self._h_slider.value * unscaled_preview_tile_dim
        )

        preview_xy: PosPair
        preview_wh: SizePair
        preview_xy, preview_wh = resize_obj(
            self._preview_init_pos, *unscaled_preview_wh, win_ratio, True
        )

        self._preview_img = pg.transform.scale(self._small_preview_img, preview_wh)
        self._preview_rect = self._preview_img.get_rect(
            **{self._preview_init_pos.coord_type: preview_xy}
        )

    def set_info(self, area: Size, tiles: NDArray[np.uint8]) -> None:
        """
        Sets the UI size and tiles.

        Args:
            area, tiles
        """

        self._w_slider.set_value(area.w)
        self._h_slider.set_value(area.h)
        self._preview_tiles = tiles
        self.values_ratio.w, self.values_ratio.h = area.h / area.w, area.w / area.h

        self._get_preview(area)

    def _get_full_tiles(self, area: Size) -> NDArray[np.uint8]:
        """
        Adjusts the tiles to fit the preview.

        Args:
            area
        Returns:
            tiles
        """

        copy_tiles: NDArray[np.uint8] = self._preview_tiles

        extra_rows: int = area.h - copy_tiles.shape[0]
        if extra_rows < 0:
            copy_tiles = copy_tiles[:area.h, :, :]
        elif extra_rows > 0:
            copy_tiles = np.pad(copy_tiles, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0)

        extra_cols: int = area.w - copy_tiles.shape[1]
        if extra_cols < 0:
            copy_tiles = copy_tiles[:, :area.w, :]
        if extra_cols > 0:
            copy_tiles = np.pad(copy_tiles, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0)

        return copy_tiles

    def _get_preview(self, area: Size) -> None:
        """
        Draws a preview of the grid.

        Args:
            area
        """

        local_empty_tile_img: pg.Surface = EMPTY_TILE_IMG

        full_tiles: NDArray[np.uint8] = self._get_full_tiles(area)
        self._small_preview_img = pg.Surface((area.w * 2, area.h * 2))
        sequence: BlitSequence = []
        tile_img: pg.Surface = pg.Surface((2, 2))
        for y in range(area.h):
            row: NDArray[np.uint8] = full_tiles[y]
            for x in range(area.w):
                if not row[x, -1]:
                    sequence.append((local_empty_tile_img, (x * 2, y * 2)))
                else:
                    tile_img.fill(row[x])
                    sequence.append((tile_img.copy(), (x * 2, y * 2)))
        self._small_preview_img.fblits(sequence)

        tile_dim: float = min(
            self._preview_init_size.w / area.w, self._preview_init_size.h / area.h
        ) * self._min_win_ratio
        coord: PosPair = getattr(self._preview_rect, self._preview_init_pos.coord_type)
        wh: SizePair = (ceil(area.w * tile_dim), ceil(area.h * tile_dim))

        self._preview_img = pg.transform.scale(self._small_preview_img, wh)
        self._preview_rect = self._preview_img.get_rect(
            **{self._preview_init_pos.coord_type: coord}
        )

    def _move_with_keys(self, keys: list[int]) -> None:
        """
        Moves the selected object with keys.

        Args:
            keys
        """

        cursor_x: int
        closest_char_i: int
        if pg.K_UP in keys:
            self._selection_i = 0
            cursor_x = self._h_slider.input_box._cursor_rect.x
            closest_char_i = self._w_slider.input_box.text_label.get_closest_to(cursor_x)
            self._w_slider.input_box.bounded_set_cursor_i(closest_char_i)
        if pg.K_DOWN in keys:
            self._selection_i = 1
            cursor_x = self._w_slider.input_box._cursor_rect.x
            closest_char_i = self._h_slider.input_box.text_label.get_closest_to(cursor_x)
            self._h_slider.input_box.bounded_set_cursor_i(closest_char_i)

    def _upt_sliders(self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]) -> None:
        """
        Updates sliders and selection.

        Args:
            hovered object, mouse info, keys
        """

        selection: SelectionType = (self._w_slider, self._h_slider)[self._selection_i]
        if self._w_slider.upt(hovered_obj, mouse_info, keys, selection):
            self._selection_i = 0
        if self._h_slider.upt(hovered_obj, mouse_info, keys, selection):
            self._selection_i = 1

    def _adjust_opp_slider(self, grid_area: Size, prev_grid_w: int) -> SizePair:
        """
        Adjusts the opposite slider when keeping their ratio.

        Args:
            grid area, previous grid width
        Returns:
            grid area
        """

        opp_slider: NumSlider
        uncapped_value: int
        if grid_area.w != prev_grid_w:
            opp_slider = self._h_slider
            uncapped_value = round(grid_area.w * self.values_ratio.w)
            opp_slider.value = max(min(uncapped_value, MAX_DIM), 1)
        else:
            opp_slider = self._w_slider
            uncapped_value = round(grid_area.h * self.values_ratio.h)
            opp_slider.value = max(min(uncapped_value, MAX_DIM), 1)
        opp_slider.input_box.text_label.set_text(str(opp_slider.value))
        opp_slider.input_box.bounded_set_cursor_i()

        return self._w_slider.value, self._h_slider.value

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]
    ) -> tuple[bool, Optional[Size]]:
        """
        Allows selecting a grid area with 2 sliders and view its preview.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            True if the interface was closed else False, size (can be None)
        """

        if keys:
            self._move_with_keys(keys)

        prev_grid_w: int = self._w_slider.value
        prev_grid_h: int = self._h_slider.value
        self._upt_sliders(hovered_obj, mouse_info, keys)
        grid_area: Size = Size(self._w_slider.value, self._h_slider.value)

        if grid_area.w != prev_grid_w or grid_area.h != prev_grid_h:
            if self.checkbox.is_checked:
                grid_area.w, grid_area.h = self._adjust_opp_slider(grid_area, prev_grid_w)
            self._get_preview(grid_area)

        did_shortcut: bool = bool((pg.key.get_mods() & pg.KMOD_CTRL) and pg.K_k in keys)
        if self.checkbox.upt(hovered_obj, mouse_info, did_shortcut):
            self.values_ratio.w = grid_area.h / grid_area.w
            self.values_ratio.h = grid_area.w / grid_area.h

        confirmed: bool
        exited: bool
        confirmed, exited = self._base_upt(hovered_obj, mouse_info, keys)

        return confirmed or exited, grid_area if confirmed else None
