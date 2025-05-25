"""Interface to edit the grid, preview is refreshed automatically."""

from typing import TypeAlias, Final

import pygame as pg
from pygame.locals import *
import numpy as np
from numpy import uint8, intp, bool_
from numpy.typing import NDArray
import cv2

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI
from src.classes.clickable import Checkbox, Button
from src.classes.text_label import TextLabel
from src.classes.devices import Mouse, Keyboard

from src.utils import RectPos, Size, ObjInfo, resize_obj
from src.type_utils import XY
from src.consts import (
    EMPTY_TILE_ARR, TILE_H, TILE_W, GRID_TRANSITION_START, GRID_TRANSITION_END, UI_LAYER
)
from src.imgs import CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG, BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG

_Selection: TypeAlias = NumInputBox

_GRID_PREVIEW_DIM_CAP: Final[int] = 325


class GridUI(UI):
    """Class to create an interface that allows editing the grid, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_rect", "w_ratio", "h_ratio", "_original_tiles", "_tiles",
        "_h_box", "_w_box", "_selection_i", "checkbox", "_crop", "_win_w_ratio", "_win_h_ratio"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the interface, sliders and preview.

        Args:
            position
        """

        super().__init__(pos, "EDIT GRID")

        self._preview_init_pos: RectPos = RectPos(
            self._rect.centerx, self._rect.centery + 20, "center"
        )

        preview_img: pg.Surface = pg.Surface((_GRID_PREVIEW_DIM_CAP, _GRID_PREVIEW_DIM_CAP))
        self._preview_rect: pg.Rect = pg.Rect(0, 0, *preview_img.get_size())
        preview_init_xy: XY = (self._preview_init_pos.x, self._preview_init_pos.y)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_init_xy)

        self.w_ratio: float = 1
        self.h_ratio: float = 1
        self._original_tiles: NDArray[uint8] = np.zeros((1, 1, 4), uint8)
        self._tiles: NDArray[uint8] = self._original_tiles

        self._h_box: NumInputBox = NumInputBox(
            RectPos(self._preview_rect.x, self._preview_rect.y - 25, "bottomleft"),
            1, 999, UI_LAYER
        )
        h_text_label: TextLabel = TextLabel(
            RectPos(self._h_box.rect.x - 5, self._h_box.rect.centery, "midright"),
            "Height", UI_LAYER
        )

        self._w_box: NumInputBox = NumInputBox(
            RectPos(self._preview_rect.x, self._h_box.rect.y - 25, "bottomleft"),
            1, 999, UI_LAYER
        )
        w_text_label: TextLabel = TextLabel(
            RectPos(self._w_box.rect.x - 5, self._w_box.rect.centery, "midright"),
            "Width", UI_LAYER
        )

        self._selection_i: int = 0

        self.checkbox: Checkbox = Checkbox(
            RectPos(self._preview_rect.right - 20, self._preview_rect.bottom + 32, "topright"),
            [CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG], "Keep Ratio", "CTRL+K", UI_LAYER
        )
        self._crop: Button = Button(
            RectPos(self.checkbox.rect.x - 16, self.checkbox.rect.centery, "midright"),
            [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Crop", "(CTRL+C)", UI_LAYER
        )

        self.blit_sequence.append((preview_img, self._preview_rect, UI_LAYER))
        self._win_w_ratio: float = 1
        self._win_h_ratio: float = 1
        self.objs_info.extend([
            ObjInfo(self._w_box), ObjInfo(w_text_label), ObjInfo(self._h_box), ObjInfo(h_text_label),
            ObjInfo(self.checkbox), ObjInfo(self._crop)
        ])

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

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

    def set_info(self, area: Size, tiles: NDArray[uint8]) -> None:
        """
        Sets the area and tiles.

        Args:
            area, tiles
        """

        self._original_tiles = self._tiles = tiles

        self._w_box.value = area.w
        self._w_box.text_label.set_text(str(self._w_box.value))
        self._w_box.set_cursor_i(0)
        self._w_box.cursor_rect.x = self._w_box.text_label.rect.x

        self._h_box.value = area.h
        self._h_box.text_label.set_text(str(self._h_box.value))
        self._h_box.set_cursor_i(0)
        self._h_box.cursor_rect.x = self._h_box.text_label.rect.x

        self._refresh_preview()

    def _resize_preview(self, small_preview_img: pg.Surface) -> None:
        """
        Resizes the small preview with a gradual blur.

        Args:
            small preview image
        """

        xy: XY
        w: int
        h: int
        img: pg.Surface

        init_tile_dim: float = _GRID_PREVIEW_DIM_CAP / max(self._w_box.value, self._h_box.value)
        init_w: float = self._w_box.value * init_tile_dim
        init_h: float = self._h_box.value * init_tile_dim

        xy, (w, h) = resize_obj(
            self._preview_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )

        if   max(self._w_box.value, self._h_box.value) < GRID_TRANSITION_START:
            img = pg.transform.scale(small_preview_img, (w, h))
        elif max(self._w_box.value, self._h_box.value) > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(small_preview_img, (w, h))
        else:
            # Gradual transition
            img_arr: NDArray[uint8] = pg.surfarray.pixels3d(small_preview_img)
            img_arr = cv2.resize(img_arr, (h, w), interpolation=cv2.INTER_AREA).astype(uint8)
            img = pg.surfarray.make_surface(img_arr)

        self._preview_rect.size = (w, h)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, xy)

        self.blit_sequence[1] = (img.convert(), self._preview_rect, UI_LAYER)

    def _refresh_preview(self) -> None:
        """Refreshes the preview by using original_tiles."""

        empty_img_arr: NDArray[uint8]
        img_arr: NDArray[uint8]

        self._tiles = self._original_tiles  # Copying is unnecessary

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

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        repeated_tiles: NDArray[uint8] = self._tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_img_arr = np.tile(EMPTY_TILE_ARR, (self._w_box.value, self._h_box.value, 1))
        empty_tiles_mask: NDArray[bool_] = (repeated_tiles[..., 3] == 0)[..., np.newaxis]
        img_arr = np.where(empty_tiles_mask, empty_img_arr, repeated_tiles[..., :3])

        # Having a version where 1 tile = 1 pixel is better for scaling
        self._resize_preview(pg.surfarray.make_surface(img_arr))

    def _move_with_keys(self, timed_keys: list[int]) -> None:
        """
        Moves the selection with the keyboard.

        Args:
            timed keys
        """

        cursor_i: int

        if K_UP in timed_keys:
            self._selection_i = 0
            cursor_i = self._w_box.text_label.get_closest_to(self._h_box.cursor_rect.x)
            self._w_box.set_cursor_i(cursor_i)
        if K_DOWN in timed_keys:
            self._selection_i = 1
            cursor_i = self._h_box.text_label.get_closest_to(self._w_box.cursor_rect.x)
            self._h_box.set_cursor_i(cursor_i)

    def _upt_sliders(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Updates sliders and selection.

        Args:
            mouse, keyboard
        """

        selected_obj: _Selection = (self._w_box, self._h_box)[self._selection_i]

        is_w_slider_clicked: bool = self._w_box.upt(mouse, keyboard, selected_obj)
        if is_w_slider_clicked:
            self._selection_i = 0
            selected_obj = self._w_box

        is_h_slider_clicked: bool = self._h_box.upt(mouse, keyboard, selected_obj)
        if is_h_slider_clicked:
            self._selection_i = 1
            selected_obj = self._h_box

    def _adjust_opp_slider(self, did_grid_w_change: bool) -> None:
        """
        Adjusts the opposite slider to keep their ratio.

        Args:
            grid width changed flag
        """

        if did_grid_w_change:
            self._h_box.value = round(self._w_box.value * self.w_ratio)
            self._h_box.value = min(max(self._h_box.value, self._h_box.min_limit), self._h_box.max_limit)

            if self._w_box.text_label.text == "" and self._h_box.value == self._h_box.min_limit:
                self._h_box.text_label.text = ""
            else:
                self._h_box.text_label.text = str(self._h_box.value)
        else:
            self._w_box.value = round(self._h_box.value * self.h_ratio)
            self._w_box.value = min(max(self._w_box.value, self._w_box.min_limit), self._w_box.max_limit)

            if self._h_box.text_label.text == "" and self._w_box.value == self._w_box.min_limit:
                self._w_box.text_label.text = ""
            else:
                self._w_box.text_label.text = str(self._w_box.value)

    def _crop_tiles(self) -> None:
        """Removes unnecessary padding from the image, sets sliders and ratios."""

        top_left: NDArray[intp]
        bottom_right: NDArray[intp]

        indices: NDArray[intp] = np.argwhere(self._tiles[..., 3] != 0)
        if indices.size == 0:
            top_left = np.array((0, 0), intp)
            bottom_right = np.array((1, 1), intp)
        else:
            top_left = indices.min(0)
            bottom_right = indices.max(0) + 1

        self._tiles = self._original_tiles = self._tiles[
            top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]
        ]  # Copying is unnecessary

        self._w_box.value, self._h_box.value = self._tiles.shape[0], self._tiles.shape[1]
        self._w_box.text_label.text = str(self._w_box.value)
        self._h_box.text_label.text = str(self._h_box.value)
        self.w_ratio = self._h_box.value / self._w_box.value
        self.h_ratio = self._w_box.value / self._h_box.value

        self._refresh_preview()

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[bool, bool, NDArray[uint8]]:
        """
        Allows selecting an area with 2 sliders and view its preview.

        Args:
            mouse, keyboard
        Returns:
            exiting flag, confirming flag, tiles
        """

        is_exiting: bool
        is_confirming: bool

        if keyboard.timed != []:
            self._move_with_keys(keyboard.timed)

        prev_w_slider_text: str = self._w_box.text_label.text
        prev_h_slider_text: str = self._h_box.text_label.text

        is_ctrl_k_pressed: bool = keyboard.is_ctrl_on and K_k in keyboard.timed
        self._upt_sliders(mouse, keyboard)
        should_get_size_ratio: bool = self.checkbox.upt(mouse, is_ctrl_k_pressed)
        if should_get_size_ratio:
            self.w_ratio = self._h_box.value / self._w_box.value
            self.h_ratio = self._w_box.value / self._h_box.value

        did_grid_w_change: bool = self._w_box.text_label.text != prev_w_slider_text
        did_grid_h_change: bool = self._h_box.text_label.text != prev_h_slider_text
        if did_grid_w_change or did_grid_h_change:
            if self.checkbox.is_checked:
                self._adjust_opp_slider(did_grid_w_change)
            self._refresh_preview()

        is_crop_clicked: bool = self._crop.upt(mouse)
        is_ctrl_c_pressed: bool = keyboard.is_ctrl_on and K_c in keyboard.pressed
        if is_crop_clicked or is_ctrl_c_pressed:
            self._crop_tiles()

        self._w_box.refresh()
        self._h_box.refresh()
        is_exiting, is_confirming = self._base_upt(mouse, keyboard.released)

        return is_exiting, is_confirming, self._tiles
