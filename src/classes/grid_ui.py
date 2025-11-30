"""Interface to edit the grid, preview is refreshed automatically."""

from typing import Literal, Self, Final

import pygame as pg
import numpy as np
import cv2
from pygame.locals import *
from numpy import uint8, uint16, intp, bool_
from numpy.typing import NDArray

from src.classes.ui import UI
from src.classes.grid_manager import Grid
from src.classes.num_input_box import NumInputBox
from src.classes.clickable import Checkbox, Button, SpammableButton
from src.classes.text_label import TextLabel
from src.classes.devices import KEYBOARD

from src.obj_utils import UIElement, ObjInfo, resize_obj
from src.type_utils import XY, RectPos
from src.consts import EMPTY_TILE_ARR, TILE_H, TILE_W
from src.imgs import (
    CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG, BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG,
    ROTATE_LEFT_OFF_IMG, ROTATE_LEFT_ON_IMG, ROTATE_RIGHT_OFF_IMG, ROTATE_RIGHT_ON_IMG,
)

_GRID_PREVIEW_DIM_CAP: Final[int] = 300
_GRID_PREVIEW_TRANSITION_START: Final[int] = 20
_GRID_PREVIEW_TRANSITION_END: Final[int]   = 80


class GridUI(UI):
    """Class to create an interface that allows editing the grid, has a preview."""

    __slots__ = (
        "w_ratio", "h_ratio", "_temp_w_ratio", "_temp_h_ratio", "is_keeping_wh_ratio",
        "_orig_tiles", "_tiles",
        "_w_box", "_h_box", "_visible_w_box", "_visible_h_box", "_offset_x_box", "_offset_y_box",
        "_objs", "_selection_x", "_selection_y",
        "_preview_init_pos", "_preview_rect",
        "_rotate_left", "_rotate_right", "checkbox", "_crop",
    )

    def __init__(self: Self) -> None:
        """Creates the interface, input boxes and preview."""

        super().__init__("EDIT GRID", True)
        assert self._confirm is not None

        self.w_ratio: float = 1
        self.h_ratio: float = 1
        self._temp_w_ratio: float = self.w_ratio
        self._temp_h_ratio: float = self.h_ratio
        self.is_keeping_wh_ratio: bool = False

        self._orig_tiles: NDArray[uint8] = np.zeros((1, 1, 4), uint8)
        self._tiles: NDArray[uint8] = self._orig_tiles

        first_x: int  = self._rect.x + round(self._rect.w / 4 * 1)
        second_x: int = self._rect.x + round(self._rect.w / 4 * 2)
        third_x: int  = self._rect.x + round(self._rect.w / 4 * 3)
        half_box_w: int = NumInputBox.half_w

        wh_text_label: TextLabel = TextLabel(
            RectPos(first_x, self._title_text_label.rect.bottom + 16, "midtop"),
            "Size", self.layer
        )
        self._w_box: NumInputBox = NumInputBox(
            RectPos(first_x - half_box_w, wh_text_label.rect.bottom + 16, "topleft"),
            min_limit=1, max_limit=999, base_layer=self.layer
        )
        self._h_box: NumInputBox = NumInputBox(
            RectPos(first_x - half_box_w, self._w_box.rect.bottom   + 16, "topleft"),
            min_limit=1, max_limit=999, base_layer=self.layer
        )

        visible_wh_text_label: TextLabel = TextLabel(
            RectPos(second_x, self._title_text_label.rect.bottom + 16, "midtop"),
            "Visible Size", self.layer
        )
        self._visible_w_box: NumInputBox = NumInputBox(
            RectPos(second_x - half_box_w, visible_wh_text_label.rect.bottom  + 16, "topleft"),
            min_limit=1, max_limit=999, base_layer=self.layer
        )
        self._visible_h_box: NumInputBox = NumInputBox(
            RectPos(second_x - half_box_w, self._visible_w_box.rect.bottom    + 16, "topleft"),
            min_limit=1, max_limit=999, base_layer=self.layer
        )

        offset_text_label: TextLabel = TextLabel(
            RectPos(third_x, self._title_text_label.rect.bottom + 16, "midtop"),
            "Offset", self.layer
        )
        self._offset_x_box: NumInputBox = NumInputBox(
            RectPos(third_x - half_box_w, offset_text_label.rect.bottom  + 16, "topleft"),
            min_limit=0, max_limit=999, base_layer=self.layer
        )
        self._offset_y_box: NumInputBox = NumInputBox(
            RectPos(third_x - half_box_w, self._offset_x_box.rect.bottom + 16, "topleft"),
            min_limit=0, max_limit=999, base_layer=self.layer
        )

        self._objs: tuple[tuple[NumInputBox, NumInputBox, NumInputBox], ...] = (
            (self._w_box, self._visible_w_box, self._offset_x_box),
            (self._h_box, self._visible_h_box, self._offset_y_box),
        )
        self._selection_x: int = 0
        self._selection_y: int = 0

        self._preview_init_pos: RectPos = RectPos(
            second_x, self._h_box.rect.bottom + round(_GRID_PREVIEW_DIM_CAP / 2) + 16,
            "center"
        )

        preview_img: pg.Surface = pg.Surface((_GRID_PREVIEW_DIM_CAP, _GRID_PREVIEW_DIM_CAP))
        self._preview_rect: pg.Rect = pg.Rect(0, 0, *preview_img.get_size())
        setattr(
            self._preview_rect, self._preview_init_pos.coord_type,
            (self._preview_init_pos.x, self._preview_init_pos.y)
        )

        self._rotate_left: SpammableButton = SpammableButton(
            RectPos(first_x - 4, self._preview_rect.bottom + 32, "topright"),
            (ROTATE_LEFT_OFF_IMG , ROTATE_LEFT_ON_IMG ), "(CTRL+SHIFT+R)", self.layer
        )
        self._rotate_right: SpammableButton = SpammableButton(
            RectPos(first_x + 4, self._preview_rect.bottom + 32, "topleft"),
            (ROTATE_RIGHT_OFF_IMG, ROTATE_RIGHT_ON_IMG), "(CTRL+R)"      , self.layer
        )
        self.checkbox: Checkbox = Checkbox(
            RectPos(third_x    , self._preview_rect.bottom + 32, "midtop"),
            (CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG), "Keep Ratio", "(CTRL+K)", self.layer
        )
        self._crop: Button = Button(
            RectPos(first_x, self._confirm.rect.centery, "center"),
            (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG), "Crop", "(CTRL+C)", self.layer
        )

        self.blit_sequence.append((preview_img, self._preview_rect, self.layer))
        self.objs_info += (
            ObjInfo(wh_text_label),
            ObjInfo(self._w_box), ObjInfo(self._h_box),

            ObjInfo(visible_wh_text_label),
            ObjInfo(self._visible_w_box), ObjInfo(self._visible_h_box),

            ObjInfo(offset_text_label),
            ObjInfo(self._offset_x_box), ObjInfo(self._offset_y_box),

            ObjInfo(self._rotate_left), ObjInfo(self._rotate_right), ObjInfo(self.checkbox),
            ObjInfo(self._crop),
        )

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        super().enter()
        self._temp_w_ratio, self._temp_h_ratio = self.w_ratio, self.h_ratio
        self.checkbox.set_checked(self.is_keeping_wh_ratio)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self._selection_x = self._selection_y = 0

    def resize(self: Self) -> None:
        """Resizes the object."""

        super().resize()
        self._refresh_preview()

    def set_info(self: Self, tiles: NDArray[uint8], grid: Grid) -> None:
        """
        Sets the area and tiles.

        Args:
            tiles, grid
        """

        self._orig_tiles = tiles
        self._w_box.set_value(grid.cols)
        self._h_box.set_value(grid.rows)
        self._visible_w_box.set_value(grid.visible_cols)
        self._visible_h_box.set_value(grid.visible_rows)
        self._offset_x_box.set_value(grid.offset_x)
        self._offset_y_box.set_value(grid.offset_y)

        self._refresh_preview()

        self._w_box.refresh()
        self._h_box.refresh()
        self._visible_w_box.refresh()
        self._visible_h_box.refresh()
        self._offset_x_box.refresh()
        self._offset_y_box.refresh()

    def _resize_preview_img(self: Self, unscaled_preview_img: pg.Surface) -> None:
        """
        Resizes the small preview image with a gradual blur.

        Args:
            small preview image
        """

        xy: XY
        w: int
        h: int
        img: pg.Surface

        init_tile_dim: float = _GRID_PREVIEW_DIM_CAP / max(self._w_box.value, self._h_box.value)
        xy, (w, h) = resize_obj(
            self._preview_init_pos,
            self._w_box.value * init_tile_dim, self._h_box.value * init_tile_dim,
            should_keep_wh_ratio=True
        )

        max_dim: int = max(self._w_box.value, self._h_box.value)
        if   max_dim < _GRID_PREVIEW_TRANSITION_START:
            img = pg.transform.scale(      unscaled_preview_img, (w, h))
        elif max_dim > _GRID_PREVIEW_TRANSITION_END:
            img = pg.transform.smoothscale(unscaled_preview_img, (w, h))
        elif _GRID_PREVIEW_TRANSITION_START <= max_dim <= _GRID_PREVIEW_TRANSITION_END:
            # Gradual transition
            img = pg.surfarray.make_surface(cv2.resize(
                pg.surfarray.pixels3d(unscaled_preview_img),
                (h, w),
                interpolation=cv2.INTER_AREA
            ).astype(uint8))

        self._preview_rect.size = (w, h)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, xy)

        self.blit_sequence[1] = (img.convert(), self._preview_rect, self.layer)

    def _refresh_preview(self: Self) -> None:
        """Refreshes the preview by using orig_tiles."""

        self._tiles = self._orig_tiles  # Copying is unnecessary

        extra_w: int = self._w_box.value - self._tiles.shape[0]
        if   extra_w < 0:
            self._tiles = self._tiles[:self._w_box.value, ...]
        elif extra_w > 0:
            self._tiles = np.pad(self._tiles, ((0, extra_w), (0, 0), (0, 0)), constant_values=0)

        extra_h: int = self._h_box.value - self._tiles.shape[1]
        if   extra_h < 0:
            self._tiles = self._tiles[:, :self._h_box.value, ...]
        elif extra_h > 0:
            self._tiles = np.pad(self._tiles, ((0, 0), (0, extra_h), (0, 0)), constant_values=0)

        # Repeats tiles so an empty tile image takes 1 normal-sized tile
        repeated_tiles: NDArray[uint8] = self._tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_tiles_mask: NDArray[bool_] = (repeated_tiles[..., 3] == 0)[..., np.newaxis]

        empty_img_arr_reps: tuple[int, int, int] = (self._w_box.value, self._h_box.value, 1)
        empty_img_arr: NDArray[uint8] = np.tile(EMPTY_TILE_ARR, empty_img_arr_reps)
        rgb_repeated_tiles: NDArray[uint8] = repeated_tiles[..., :3]
        # Better for scaling
        img_arr: NDArray[uint8] = np.where(empty_tiles_mask, empty_img_arr, rgb_repeated_tiles)

        visible_cols: int = min(self._visible_w_box.value, self._w_box.value)
        visible_rows: int = min(self._visible_h_box.value, self._h_box.value)
        offset_x: int = min(self._offset_x_box.value, self._w_box.value - visible_cols) * TILE_W
        offset_y: int = min(self._offset_y_box.value, self._h_box.value - visible_rows) * TILE_H
        visible_cols *= TILE_W
        visible_rows *= TILE_H

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

        color_range: NDArray[uint16] = np.arange(256, dtype=uint16)
        # Lookup table for every blend combination with gray (150, 150, 150, 128)
        a: int = 128
        blend_lut: NDArray[uint8] = (((150 * a) + (color_range * (255 - a))) >> 8).astype(uint8)
        target_left_pixels[  ...] = blend_lut[target_left_pixels]
        target_top_pixels[   ...] = blend_lut[target_top_pixels]
        target_right_pixels[ ...] = blend_lut[target_right_pixels]
        target_bottom_pixels[...] = blend_lut[target_bottom_pixels]

        self._resize_preview_img(pg.surfarray.make_surface(img_arr))

    def _handle_move_with_keys(self: Self) -> None:
        """Handles moving the selection with the keyboard."""

        prev_selection_y: int = self._selection_y

        if K_TAB in KEYBOARD.timed:
            if KEYBOARD.is_shift_on:
                self._selection_x = max(self._selection_x - 1, 0)
            else:
                self._selection_x = min(self._selection_x + 1, len(self._objs[0]) - 1)

        if K_UP   in KEYBOARD.timed:
            self._selection_y = max(self._selection_y - 1, 0)
        if K_DOWN in KEYBOARD.timed:
            self._selection_y = min(self._selection_y + 1, len(self._objs) - 1)

        if self._selection_y != prev_selection_y:
            prev_input_box: NumInputBox = self._objs[prev_selection_y ][self._selection_x]
            input_box: NumInputBox      = self._objs[self._selection_y][self._selection_x]
            input_box.cursor_i = input_box.text_label.get_closest_to(prev_input_box.cursor_rect.x)

    def _upt_input_boxes(self: Self) -> None:
        """Updates the input boxes and selection."""

        obj: NumInputBox

        objs: tuple[NumInputBox, ...] = (
            self._w_box, self._visible_w_box, self._offset_x_box,
            self._h_box, self._visible_h_box, self._offset_y_box,
        )

        selected_obj: UIElement = self._objs[self._selection_y][self._selection_x]
        for i, obj in enumerate(objs):
            prev_selected_obj: UIElement = selected_obj
            selected_obj = obj.upt(selected_obj)

            if selected_obj != prev_selected_obj:
                prev_selected_obj.leave()
                self._selection_x = i %  len(self._objs[0])
                self._selection_y = i // len(self._objs[0])

    def _adjust_opp_input_box(self: Self, did_w_change: bool) -> None:
        """
        Adjusts the opposite input box to keep their ratio.

        Args:
            width changed flag
        """

        if did_w_change:
            self._h_box.set_value(min(max(
                round(self._w_box.value * self._temp_w_ratio),
                self._h_box.min_limit), self._h_box.max_limit
            ))
            if self._w_box.text_label.text == "" and self._h_box.value == self._h_box.min_limit:
                self._h_box.text_label.text = ""
        else:  # did_h_change
            self._w_box.set_value(min(max(
                round(self._h_box.value * self._temp_h_ratio),
                self._w_box.min_limit), self._w_box.max_limit
            ))
            if self._h_box.text_label.text == "" and self._w_box.value == self._w_box.min_limit:
                self._w_box.text_label.text = ""

    def _rotate_tiles(self: Self, direction: Literal[-1, 1]) -> None:
        """
        Rotates the tiles by 90 degrees in a direction.

        Args:
            direction
        """

        # Copying is unnecessary
        self._orig_tiles = self._tiles = np.rot90(self._tiles, direction)

        cols: int = self._w_box.value
        self._w_box.set_value(self._h_box.value)
        self._h_box.set_value(cols)
        self._temp_w_ratio, self._temp_h_ratio = self._temp_h_ratio, self._temp_w_ratio

        self._refresh_preview()

    def _crop_tiles(self: Self) -> None:
        """Removes unnecessary padding from the image, sets sliders and ratios."""

        left: intp
        right: intp
        top: intp
        bottom: intp

        colored_tiles_indexes: NDArray[intp] = np.argwhere(self._orig_tiles[..., 3] != 0)
        if colored_tiles_indexes.size == 0:
            left  = top    = intp(0)
            right = bottom = intp(1)
        else:
            left , top    = colored_tiles_indexes.min(0)
            right, bottom = colored_tiles_indexes.max(0) + 1
        # Copying is unnecessary
        self._orig_tiles = self._tiles = self._orig_tiles[left:right, top:bottom]

        self._w_box.set_value(min(max(
            self._tiles.shape[0],
            self._w_box.min_limit), self._w_box.max_limit
        ))
        self._h_box.set_value(min(max(
            self._tiles.shape[1],
            self._h_box.min_limit), self._h_box.max_limit
        ))
        self._temp_w_ratio = self._h_box.value / self._w_box.value
        self._temp_h_ratio = self._w_box.value / self._h_box.value

        self._refresh_preview()

    def upt(self: Self) -> tuple[bool, bool, NDArray[uint8], int, int, int, int]:
        """
        Allows selecting an area with 2 sliders and view its preview.

        Returns:
            exiting flag, confirming flag, tiles
        """

        is_exiting: bool
        is_confirming: bool

        if KEYBOARD.timed != ():
            self._handle_move_with_keys()

        self._upt_input_boxes()

        is_ctrl_k_pressed: bool = KEYBOARD.is_ctrl_on and K_k in KEYBOARD.timed
        did_toggle_checkbox: bool = self.checkbox.upt(is_ctrl_k_pressed)
        if did_toggle_checkbox and self.checkbox.is_checked:
            self._temp_w_ratio = self._h_box.value / self._w_box.value
            self._temp_h_ratio = self._w_box.value / self._h_box.value

        did_w_change: bool = self._w_box.text_label.text != self._w_box.prev_text
        did_h_change: bool = self._h_box.text_label.text != self._h_box.prev_text
        if (did_w_change or did_h_change) and self.checkbox.is_checked:
            self._adjust_opp_input_box(did_w_change)

        is_ctrl_r_pressed: bool       = False
        is_ctrl_shift_r_pressed: bool = False
        if KEYBOARD.is_ctrl_on and K_r in KEYBOARD.timed:
            if KEYBOARD.is_shift_on:
                is_ctrl_shift_r_pressed = True
            else:
                is_ctrl_r_pressed       = True

        is_rotate_left_clicked: bool = self._rotate_left.upt()
        if is_rotate_left_clicked or is_ctrl_shift_r_pressed:
            self._rotate_tiles(-1)

        is_rotate_right_clicked: bool = self._rotate_right.upt()
        if is_rotate_right_clicked or is_ctrl_r_pressed:
            self._rotate_tiles(1)

        is_crop_clicked: bool = self._crop.upt()
        is_ctrl_c_pressed: bool = KEYBOARD.is_ctrl_on and K_c in KEYBOARD.pressed
        if is_crop_clicked or is_ctrl_c_pressed:
            self._crop_tiles()

        if (
            did_w_change or did_h_change or
            self._visible_w_box.text_label.text != self._visible_w_box.prev_text or
            self._visible_h_box.text_label.text != self._visible_h_box.prev_text or
            self._offset_x_box.text_label.text != self._offset_x_box.prev_text or
            self._offset_y_box.text_label.text != self._offset_y_box.prev_text
        ):
            self._refresh_preview()

        self._w_box.refresh()
        self._h_box.refresh()
        self._visible_w_box.refresh()
        self._visible_h_box.refresh()
        self._offset_x_box.refresh()
        self._offset_y_box.refresh()

        is_exiting, is_confirming = self._base_upt()
        if is_confirming:
            self.w_ratio, self.h_ratio = self._temp_w_ratio, self._temp_h_ratio
            self.is_keeping_wh_ratio = self.checkbox.is_checked
        return (
            is_exiting, is_confirming, self._tiles,
            self._visible_w_box.value, self._visible_h_box.value,
            self._offset_x_box.value, self._offset_y_box.value
        )
