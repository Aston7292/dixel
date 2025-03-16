"""Interface to edit the grid, preview is refreshed automatically."""

from typing import TypeAlias, Final

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from cv2 import resize as resize_arr, INTER_AREA

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON
from src.classes.clickable import Checkbox
from src.classes.text_label import TextLabel

from src.utils import RectPos, Size, ObjInfo, Mouse, Keyboard, resize_obj
from src.type_utils import XY, WH, LayeredBlitInfo
from src.consts import (
    MOUSE_LEFT, EMPTY_TILE_ARR, NUM_TILE_ROWS, NUM_TILE_COLS,
    GRID_TRANSITION_START, GRID_TRANSITION_END, UI_LAYER
)

SelectionType: TypeAlias = NumInputBox

MOVEMENT_THRESHOLD: Final[int] = 20


class NumSlider:
    """Class that allows picking a number in a predefined range either by sliding or typing."""

    __slots__ = (
        "value", "input_box", "_prev_mouse_x", "_traveled_x", "_speeds", "_is_sliding",
        "blit_sequence", "objs_info"
    )

    def __init__(self, pos: RectPos, extra_text: str, base_layer: int = UI_LAYER) -> None:
        """
        Creates the slider and extra text.

        Args:
            position, extra text, base layer (default = UI_LAYER)
        """

        self.value: int = 1
        self.input_box: NumInputBox = NumInputBox(pos, 1, 999, base_layer)

        self._prev_mouse_x: int = pg.mouse.get_pos()[0]
        self._traveled_x: int = 0
        self._speeds: list[int] = []
        self._is_sliding: bool = False

        extra_text_label: TextLabel = TextLabel(
            RectPos(self.input_box.rect.x - 10, self.input_box.rect.centery, "midright"),
            extra_text, base_layer
        )

        self.blit_sequence: list[LayeredBlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.input_box), ObjInfo(extra_text_label)]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self.input_box.cursor_type = pg.SYSTEM_CURSOR_IBEAM
        self._prev_mouse_x = pg.mouse.get_pos()[0]
        self._traveled_x = 0
        self._speeds = []
        self._is_sliding = False

    def set_value(self, value: int) -> None:
        """
        Sets the slider on a specific value.

        Args:
            value
        """

        self.value = value
        self.input_box.text_label.set_text(str(self.value))
        self.input_box.bounded_set_cursor_i(0)

    def _slide(self, mouse_x: int) -> None:
        """
        Changes the value with the mouse, it's faster when moving the mouse faster.

        Args:
            mouse x
        """

        speed: int = mouse_x - self._prev_mouse_x
        if speed != 0:
            self._speeds.append(speed)
        self._traveled_x += speed

        if abs(self._traveled_x) >= MOVEMENT_THRESHOLD:
            units_traveled: float = self._traveled_x / MOVEMENT_THRESHOLD
            avg_speed: float = abs(sum(self._speeds) / len(self._speeds))
            scaled_avg_speed: float = max(avg_speed / 75, 1)
            scaled_units: int = int(units_traveled * scaled_avg_speed)

            min_limit, max_limit = self.input_box.min_limit, self.input_box.max_limit
            self.value = max(min(self.value + scaled_units, max_limit), min_limit)
            self.input_box.text_label.text = str(self.value)

            self._speeds = []
            self._traveled_x -= int(units_traveled) * MOVEMENT_THRESHOLD

    def upt(self, mouse: Mouse, keyboard: Keyboard, selected_obj: SelectionType) -> bool:
        """
        Allows to select a color either by sliding or typing.

        Args:
            mouse, keyboard, selected object
        Returns:
            clicked flag
        """

        if not mouse.pressed[MOUSE_LEFT]:
            self.input_box.cursor_type = pg.SYSTEM_CURSOR_IBEAM
            self._traveled_x = 0
            self._speeds = []
            self._is_sliding = False
        elif self.input_box == mouse.hovered_obj:
            self.input_box.cursor_type = pg.SYSTEM_CURSOR_SIZEWE
            self._is_sliding = True

        prev_input_box_text: str = self.input_box.text_label.text

        if self._is_sliding:
            self._slide(mouse.x)
        is_input_box_clicked: bool = self.input_box.upt(
            mouse, keyboard, selected_obj, prev_input_box_text
        )

        self.value = int(self.input_box.text_label.text or self.input_box.min_limit)
        self._prev_mouse_x = mouse.x

        return is_input_box_clicked


class GridUI(UI):
    """Class to create an interface that allows editing the grid, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_dim_cap", "w_ratio", "h_ratio", "_preview_tiles",
        "_h_slider", "_w_slider", "_selection_i", "checkbox", "_win_w_ratio", "_win_h_ratio"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Initializes the interface.

        Args:
            position
        """

        self.w_ratio: float
        self.h_ratio: float
        self._win_w_ratio: float
        self._win_h_ratio: float

        super().__init__(pos, "EDIT GRID")

        self._preview_init_pos: RectPos = RectPos(
            self._rect.centerx, self._rect.centery + 20, "center"
        )
        self._preview_dim_cap: int = 325

        preview_rect: pg.Rect = pg.Rect(0, 0, self._preview_dim_cap, self._preview_dim_cap)
        preview_init_xy: XY = (self._preview_init_pos.x, self._preview_init_pos.y)
        setattr(preview_rect, self._preview_init_pos.coord_type, preview_init_xy)

        self.w_ratio = self.h_ratio = 1
        self._preview_tiles: NDArray[np.uint8] = np.zeros((1, 1, 4), np.uint8)

        self._h_slider: NumSlider = NumSlider(
            RectPos(preview_rect.x, preview_rect.y - 25, "bottomleft"),
            "Height"
        )
        self._w_slider: NumSlider = NumSlider(
            RectPos(preview_rect.x, self._h_slider.input_box.rect.y - 25, "bottomleft"),
            "Width"
        )
        self._selection_i: int = 0

        self.checkbox: Checkbox = Checkbox(
            RectPos(preview_rect.right - 20, preview_rect.bottom + 30, "topright"),
            [CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON], "Keep Ratio", "(CTRL+K)", UI_LAYER
        )

        self.blit_sequence.append(
            (pg.Surface((self._preview_dim_cap, self._preview_dim_cap)), preview_rect, UI_LAYER)
        )
        self._win_w_ratio = self._win_h_ratio = 1
        self.objs_info.extend(
            [ObjInfo(self._w_slider), ObjInfo(self._h_slider), ObjInfo(self.checkbox)]
        )

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._selection_i = 0

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        super().resize(win_w_ratio, win_h_ratio)

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio
        self._refresh_preview()

    def set_info(self, area: Size, tiles: NDArray[np.uint8]) -> None:
        """
        Sets the area and tiles.

        Args:
            area, tiles
        """

        self._preview_tiles = tiles
        self._w_slider.set_value(area.w)
        self._h_slider.set_value(area.h)
        self._refresh_preview()

    def _fit_tiles(self) -> NDArray[np.uint8]:
        """
        Adjusts the tiles to fit the area.

        Returns:
            tiles
        """

        tiles: NDArray[np.uint8] = self._preview_tiles  # Copying isn't necessary

        num_extra_cols: int = self._w_slider.value - tiles.shape[0]
        if num_extra_cols < 0:
            tiles = tiles[:self._w_slider.value, ...]
        elif num_extra_cols > 0:
            tiles = np.pad(tiles, ((0, num_extra_cols), (0, 0), (0, 0)), constant_values=0)

        num_extra_rows: int = self._h_slider.value - tiles.shape[1]
        if num_extra_rows < 0:
            tiles = tiles[:, :self._h_slider.value, ...]
        elif num_extra_rows > 0:
            tiles = np.pad(tiles, ((0, 0), (0, num_extra_rows), (0, 0)), constant_values=0)

        return tiles

    def _resize_preview(self, small_preview_img: pg.Surface) -> None:
        """
        Resizes the preview.

        Args:
            small preview image
        """

        xy: XY
        wh: WH
        init_w: float
        init_h: float
        w: int
        h: int
        img: pg.Surface

        dim_cap: int = self._preview_dim_cap
        init_tile_dim: float = min(dim_cap / self._w_slider.value, dim_cap / self._h_slider.value)
        init_w, init_h = self._w_slider.value * init_tile_dim, self._h_slider.value * init_tile_dim

        xy, wh = resize_obj(
            self._preview_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )

        max_visible_dim: int = max(self._w_slider.value, self._h_slider.value)
        if max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(small_preview_img, wh)
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(small_preview_img, wh)
        else:
            # Gradual transition
            w, h = wh
            img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(small_preview_img)
            img_arr = resize_arr(img_arr, (h, w), interpolation=INTER_AREA).astype(np.uint8)
            img = pg.surfarray.make_surface(img_arr)

        rect: pg.Rect = pg.Rect(0, 0, *wh)
        setattr(rect, self._preview_init_pos.coord_type, xy)

        self.blit_sequence[1] = (img, rect, UI_LAYER)

    def _refresh_preview(self) -> None:
        """Refreshes the preview."""

        tiles: NDArray[np.uint8] = self._fit_tiles()

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles = tiles.repeat(NUM_TILE_COLS, 0).repeat(NUM_TILE_ROWS, 1)
        empty_tiles_mask: NDArray[np.bool_] = tiles[..., 3:4] == 0
        tiles = tiles[..., :3]

        empty_tiles: NDArray[np.uint8] = np.tile(
            EMPTY_TILE_ARR, (self._w_slider.value, self._h_slider.value, 1)
        )
        tiles = np.where(empty_tiles_mask, empty_tiles, tiles)

        # Having a version where 1 tile = 1 pixel is better for scaling
        small_preview_img: pg.Surface = pg.surfarray.make_surface(tiles)
        self._resize_preview(small_preview_img)

    def _move_with_keys(self, timed_keys: list[int]) -> None:
        """
        Moves the selected object with keys.

        Args:
            timed keys
        """

        closest_char_i: int

        if pg.K_UP in timed_keys:
            self._selection_i = 0
            closest_char_i = self._w_slider.input_box.text_label.get_closest_to(
                self._h_slider.input_box.cursor_rect.x
            )
            self._w_slider.input_box.bounded_set_cursor_i(closest_char_i)
        if pg.K_DOWN in timed_keys:
            self._selection_i = 1
            closest_char_i = self._h_slider.input_box.text_label.get_closest_to(
                self._w_slider.input_box.cursor_rect.x
            )
            self._h_slider.input_box.bounded_set_cursor_i(closest_char_i)

    def _upt_sliders(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Updates sliders and selection.

        Args:
            mouse, keyboard
        """

        selected_obj: SelectionType = (self._w_slider, self._h_slider)[self._selection_i].input_box

        is_w_slider_clicked: bool = self._w_slider.upt(mouse, keyboard, selected_obj)
        if is_w_slider_clicked:
            self._selection_i = 0
            selected_obj = self._w_slider.input_box

        is_h_slider_clicked: bool = self._h_slider.upt(mouse, keyboard, selected_obj)
        if is_h_slider_clicked:
            self._selection_i = 1
            selected_obj = self._h_slider.input_box

    def _adjust_opp_slider(self, has_grid_w_changed: bool) -> None:
        """
        Adjusts the opposite slider when keeping their ratio.

        Args:
            grid width changed flag
        """

        opp_slider: NumSlider
        uncapped_value: int
        slider_text: str
        min_limit: int
        max_limit: int

        if has_grid_w_changed:
            opp_slider = self._h_slider
            uncapped_value = round(self._w_slider.value * self.w_ratio)
            slider_text = self._w_slider.input_box.text_label.text
        else:
            opp_slider = self._w_slider
            uncapped_value = round(self._h_slider.value * self.h_ratio)
            slider_text = self._h_slider.input_box.text_label.text
        min_limit, max_limit = opp_slider.input_box.min_limit, opp_slider.input_box.max_limit
        opp_slider.value = max(min(uncapped_value, max_limit), min_limit)

        opp_slider_text: str = str(opp_slider.value)
        if slider_text == "" and opp_slider.value == 1:
            opp_slider_text = ""

        opp_slider.input_box.text_label.set_text(opp_slider_text)
        opp_slider.input_box.bounded_set_cursor_i(None)

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[bool, bool, int, int]:
        """
        Allows selecting a grid area with 2 sliders and view its preview.

        Args:
            mouse, keyboard
        Returns:
            exiting flag, confirming flag, columns, rows
        """

        is_exiting: bool
        is_confirming: bool

        if keyboard.timed != []:
            self._move_with_keys(keyboard.timed)

        prev_w_slider_text: str = self._w_slider.input_box.text_label.text
        prev_h_slider_text: str = self._h_slider.input_box.text_label.text

        is_ctrl_k_pressed: bool = keyboard.is_ctrl_on and pg.K_k in keyboard.timed
        self._upt_sliders(mouse, keyboard)
        should_get_size_ratio: bool = self.checkbox.upt(mouse, is_ctrl_k_pressed)

        if should_get_size_ratio:
            self.w_ratio = self._h_slider.value / self._w_slider.value
            self.h_ratio = self._w_slider.value / self._h_slider.value

        has_grid_w_changed: bool = self._w_slider.input_box.text_label.text != prev_w_slider_text
        has_grid_h_changed: bool = self._h_slider.input_box.text_label.text != prev_h_slider_text
        if has_grid_w_changed or has_grid_h_changed:
            if self.checkbox.is_checked:
                self._adjust_opp_slider(has_grid_w_changed)
            self._refresh_preview()

        is_exiting, is_confirming = self._base_upt(mouse, keyboard.pressed)

        return is_exiting, is_confirming, self._w_slider.value, self._h_slider.value
