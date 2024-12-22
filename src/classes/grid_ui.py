"""Interface to modify the grid."""

from typing import TypeAlias, Final, Optional, Any

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON
from src.classes.clickable import Checkbox
from src.classes.text_label import TextLabel

from src.utils import RectPos, Size, Ratio, ObjInfo, MouseInfo, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import MOUSE_LEFT, EMPTY_TILE_ARR, BG_LAYER, ELEMENT_LAYER

SelectionType: TypeAlias = "NumSlider"

MOVEMENT_THRESHOLD: Final[int] = 10
SPEED_SCALING_FACTOR: Final[int] = MOVEMENT_THRESHOLD * 15
MAX_DIM: Final[int] = 256


class NumSlider:
    """Class that allows picking a number in a predefined range either by sliding or typing."""

    __slots__ = (
        "value", "input_box", "_prev_mouse_x", "_traveled_x", "_speeds", "_is_sliding", "objs_info"
    )

    def __init__(
        self, pos: RectPos, text: str, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the slider and text.

        Args:
            position, text, base layer (default = BG_LAYER)
        """

        self.value: int
        self.input_box: NumInputBox = NumInputBox(pos, base_layer)

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
            if not mouse_info.pressed[MOUSE_LEFT]:
                self._is_sliding = False
                self._traveled_x = 0
                self._speeds.clear()
        else:
            self._is_sliding = mouse_info.pressed[MOUSE_LEFT]
            if not mouse_info.pressed[MOUSE_LEFT]:
                self._traveled_x = 0
                self._speeds.clear()

    def _slide(self, mouse_info: MouseInfo, temp_input_box_text: str, max_value: int) -> str:
        """
        Changes the value with the mouse.

        Args:
            mouse info, input box text, maximum value
        """

        # Slide is faster depending on the mouse movement speed

        local_temp_input_box_text: str = temp_input_box_text

        if self._is_sliding:
            speed: int = mouse_info.x - self._prev_mouse_x
            if speed:
                self._speeds.append(speed)

            self._traveled_x += speed
            if abs(self._traveled_x) >= MOVEMENT_THRESHOLD:
                units_traveled: float = self._traveled_x / MOVEMENT_THRESHOLD
                avg_speed: float = sum(self._speeds) / len(self._speeds)
                scaled_avg_speed: float = max(avg_speed / SPEED_SCALING_FACTOR, 1)
                scaled_units: int = int(units_traveled * scaled_avg_speed)
                value: int = max(min(self.value + scaled_units, max_value), 1)

                local_temp_input_box_text = str(value)
                self._speeds.clear()
                self._traveled_x -= int(units_traveled) * MOVEMENT_THRESHOLD

        return local_temp_input_box_text

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int], max_value: int,
            selection: SelectionType
    ) -> bool:
        """
        Allows to select a color either by sliding or typing.

        Args:
            hovered object (can be None), mouse info, keys, maximum value, selected object
        Returns:
            True if the slider was clicked else False
        """

        is_input_box_clicked: bool
        temp_input_box_text: str
        is_input_box_clicked, temp_input_box_text = self.input_box.upt(
            hovered_obj, mouse_info, keys, (1, max_value), selection == self
        )

        self._handle_hover(mouse_info)

        future_input_box_text: str = self._slide(mouse_info, temp_input_box_text, max_value)
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
        "_selection_i", "_win_ratio"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Initializes the interface.

        Args:
            position
        """

        # Tiles dimension is a float to represent the full size more accurately when resizing

        super().__init__(pos, "MODIFY GRID")

        self._preview_init_pos: RectPos = RectPos(
            self._rect.centerx, self._rect.centery + 40, "center"
        )

        self._preview_img: pg.Surface
        self._preview_rect: pg.Rect = pg.Rect(0, 0, 300, 300)
        preview_xy: PosPair = (self._preview_init_pos.x, self._preview_init_pos.y)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_xy)

        self._preview_init_size: Size = Size(*self._preview_rect.size)

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        self._h_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20, self._preview_rect.y - 25, "bottomleft"),
            "height", self._base_layer
        )
        self._w_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20, self._h_slider.input_box.rect.y - 25, "bottomleft"),
            "width", self._base_layer
        )
        self.values_ratio: Ratio = Ratio(1, 1)

        self._preview_tiles: NDArray[np.uint8]

        checkbox_y: int = self._h_slider.input_box.rect.centery
        self.checkbox: Checkbox = Checkbox(
            RectPos(self._preview_rect.right - 20, checkbox_y, "midright"),
            (CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON), "keep ratio", "(CTRL+K)", self._base_layer
        )

        self._selection_i: int = 0
        self._win_ratio: Ratio = Ratio(1, 1)

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

        self._win_ratio = win_ratio

        super().resize(self._win_ratio)
        self._get_preview()

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

        self._get_preview()

    def _fit_tiles(self) -> NDArray[np.uint8]:
        """
        Adjusts the tiles to fit the area.

        Returns:
            tiles
        """

        copy_tiles: NDArray[np.uint8] = self._preview_tiles

        extra_rows: int = self._h_slider.value - copy_tiles.shape[0]
        if extra_rows < 0:
            copy_tiles = copy_tiles[:self._h_slider.value, ...]
        elif extra_rows > 0:
            copy_tiles = np.pad(copy_tiles, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0)

        extra_cols: int = self._w_slider.value - copy_tiles.shape[1]
        if extra_cols < 0:
            copy_tiles = copy_tiles[:, :self._w_slider.value, ...]
        if extra_cols > 0:
            copy_tiles = np.pad(copy_tiles, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0)

        # Swaps columns and rows, because pygame uses it like this
        return copy_tiles

    def _resize_preview(self, small_preview_img: pg.Surface) -> None:
        """
        Resizes the preview.

        Args:
            small preview image
        """

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
            self._preview_init_pos, *unscaled_preview_wh, self._win_ratio, True
        )

        self._preview_img = pg.transform.scale(small_preview_img, preview_wh)
        self._preview_rect = self._preview_img.get_rect(
            **{self._preview_init_pos.coord_type: preview_xy}
        )

    def _get_preview(self) -> None:
        """Gets a preview of the grid."""

        tiles: NDArray[np.uint8] = self._fit_tiles()

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles = np.repeat(np.repeat(tiles, EMPTY_TILE_ARR.shape[0], 0), EMPTY_TILE_ARR.shape[1], 1)
        empty_tiles_mask: NDArray[np.bool_] = tiles[..., 3:4] == 0
        tiles = tiles[..., :3]

        empty_tiles: NDArray[np.uint8] = np.tile(
            EMPTY_TILE_ARR, (self._h_slider.value, self._w_slider.value, 1)
        )
        tiles = np.where(empty_tiles_mask, empty_tiles, tiles)
        # Having a version where 1 tile = 1 pixel is better for scaling
        small_preview_img: pg.Surface = pg.surfarray.make_surface(tiles.transpose((1, 0, 2)))
        self._resize_preview(small_preview_img)

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

        is_w_slider_clicked: bool = self._w_slider.upt(
            hovered_obj, mouse_info, keys, 256, selection
        )
        if is_w_slider_clicked:
            self._selection_i = 0

        is_h_slider_clicked: bool = self._h_slider.upt(
            hovered_obj, mouse_info, keys, 256, selection
        )
        if is_h_slider_clicked:
            self._selection_i = 1

    def _adjust_opp_slider(self, prev_grid_w: int) -> None:
        """
        Adjusts the opposite slider when keeping their ratio.

        Args:
            previous grid width
        """

        opp_slider: NumSlider
        uncapped_value: int
        if self._w_slider.value != prev_grid_w:
            opp_slider = self._h_slider
            uncapped_value = round(self._w_slider.value * self.values_ratio.w)
            opp_slider.value = max(min(uncapped_value, MAX_DIM), 1)
        else:
            opp_slider = self._w_slider
            uncapped_value = round(self._h_slider.value * self.values_ratio.h)
            opp_slider.value = max(min(uncapped_value, MAX_DIM), 1)
        opp_slider.input_box.text_label.set_text(str(opp_slider.value))
        opp_slider.input_box.bounded_set_cursor_i()

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

        prev_w_slider_value: int = self._w_slider.value
        prev_h_slider_value: int = self._h_slider.value
        self._upt_sliders(hovered_obj, mouse_info, keys)

        has_w_changed: bool = self._w_slider.value != prev_w_slider_value
        has_h_changed: bool = self._h_slider.value != prev_h_slider_value
        if has_w_changed or has_h_changed:
            if self.checkbox.is_checked:
                self._adjust_opp_slider(prev_w_slider_value)
            self._get_preview()

        is_shortcutting: bool = bool((pg.key.get_mods() & pg.KMOD_CTRL) and pg.K_k in keys)
        should_get_size_ratio: bool = self.checkbox.upt(hovered_obj, mouse_info, is_shortcutting)
        if should_get_size_ratio:
            self.values_ratio.w = self._h_slider.value / self._w_slider.value
            self.values_ratio.h = self._w_slider.value / self._h_slider.value

        is_confirming: bool
        is_exiting: bool
        is_confirming, is_exiting = self._base_upt(hovered_obj, mouse_info, keys)

        grid_area: Size = Size(self._w_slider.value, self._h_slider.value)

        return is_confirming or is_exiting, grid_area if is_confirming else None
