"""Interface to edit the grid, preview is refreshed automatically."""

from typing import Self, Literal, Final

import pygame as pg
from pygame.locals import *
import numpy as np
from numpy import uint8, intp, bool_
from numpy.typing import NDArray
import cv2

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI
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
        "_preview_init_pos", "_preview_rect",
        "w_ratio", "h_ratio", "_original_tiles", "_tiles",
        "_h_box", "_w_box", "_selection_i",
        "checkbox", "_rotate_left", "_rotate_right", "_crop",
        "_win_w_ratio", "_win_h_ratio",
    )

    def __init__(self: Self) -> None:
        """Creates the interface, sliders and preview."""

        super().__init__("EDIT GRID", True)
        assert self._confirm is not None

        self._preview_init_pos: RectPos = RectPos(
            self._rect.centerx, self._rect.centery + 16,
            "center"
        )

        preview_img: pg.Surface = pg.Surface((_GRID_PREVIEW_DIM_CAP, _GRID_PREVIEW_DIM_CAP))
        self._preview_rect: pg.Rect = pg.Rect(0, 0, *preview_img.get_size())
        setattr(
            self._preview_rect, self._preview_init_pos.coord_type,
            (self._preview_init_pos.x, self._preview_init_pos.y)
        )

        self.w_ratio: float = 1
        self.h_ratio: float = 1
        self._original_tiles: NDArray[uint8] = np.zeros((1, 1, 4), uint8)
        self._tiles: NDArray[uint8] = self._original_tiles

        self._h_box: NumInputBox = NumInputBox(
            RectPos(self._preview_rect.x - 8, self._preview_rect.y - 25, "bottomleft"),
            min_limit=1, max_limit=999, base_layer=self.layer
        )
        self._w_box: NumInputBox = NumInputBox(
            RectPos(self._preview_rect.x - 8, self._h_box.rect.y   - 25, "bottomleft"),
            min_limit=1, max_limit=999, base_layer=self.layer
        )

        self._selection_i: int = 0

        self.checkbox: Checkbox = Checkbox(
            RectPos(self._preview_rect.right - 16, self._confirm.rect.y - 16, "bottomright"),
            [CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG], "Keep Ratio", "(CTRL+K)", self.layer
        )
        self._rotate_left: SpammableButton = SpammableButton(
            RectPos(self._preview_rect.x         + 16, self.checkbox.rect.centery, "midleft"),
            [ROTATE_LEFT_OFF_IMG , ROTATE_LEFT_ON_IMG ], "(CTRL+SHIFT+R)", self.layer
        )
        self._rotate_right: SpammableButton = SpammableButton(
            RectPos(self._rotate_left.rect.right + 8 , self.checkbox.rect.centery, "midleft"),
            [ROTATE_RIGHT_OFF_IMG, ROTATE_RIGHT_ON_IMG], "(CTRL+R)"      , self.layer
        )
        self._crop: Button = Button(
            RectPos(self._rotate_left.rect.right + 4, self._confirm.rect.centery, "center"),
            [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], "Crop", "(CTRL+C)", self.layer
        )

        def _get_box_tex_label_info(box: NumInputBox, text: str) -> ObjInfo:
            """
            Creates a text label to the left of an input box.

            Args:
                input box
            Returns:
                text label object info
            """

            return ObjInfo(TextLabel(
                RectPos(box.rect.x - 8, box.rect.centery, "midright"),
                text , self.layer
            ))
        self.blit_sequence.append((preview_img, self._preview_rect, self.layer))
        self._win_w_ratio: float = 1
        self._win_h_ratio: float = 1
        self.objs_info.extend((
            ObjInfo(self._w_box), _get_box_tex_label_info(self._w_box, "Width"),
            ObjInfo(self._h_box), _get_box_tex_label_info(self._h_box, "Height"),
            ObjInfo(self.checkbox), ObjInfo(self._rotate_left), ObjInfo(self._rotate_right),
            ObjInfo(self._crop),
        ))

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        super().enter()
        self._selection_i = 0

    def resize(self: Self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        super().resize(win_w_ratio, win_h_ratio)

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio
        self._refresh_preview()

    def set_info(self: Self, cols: int, rows: int, tiles: NDArray[uint8]) -> None:
        """
        Sets the area and tiles.

        Args:
            columns, rows, tiles
        """

        self._original_tiles = self._tiles = tiles
        self._w_box.set_value(cols)
        self._h_box.set_value(rows)
        self._refresh_preview()

    def _resize_preview(self: Self, unscaled_preview_img: pg.Surface) -> None:
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
        xy, (w, h) = resize_obj(
            self._preview_init_pos,
            self._w_box.value * init_tile_dim, self._h_box.value * init_tile_dim,
            self._win_w_ratio, self._win_h_ratio, should_keep_wh_ratio=True
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
        """Refreshes the preview by using original_tiles."""

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

        # Repeats tiles so an empty tile image takes 1 normal-sized tile
        repeated_tiles: NDArray[uint8] = self._tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_tiles_mask: NDArray[bool_] = (repeated_tiles[..., 3] == 0)[..., np.newaxis]

        empty_img_arr_reps: tuple[int, int, int] = (self._w_box.value, self._h_box.value, 1)
        empty_img_arr: NDArray[uint8] = np.tile(EMPTY_TILE_ARR, empty_img_arr_reps)
        rgb_repeated_tiles: NDArray[uint8] = repeated_tiles[..., :3]
        # Better for scaling
        img_arr: NDArray[uint8] = np.where(empty_tiles_mask, empty_img_arr, rgb_repeated_tiles)

        self._resize_preview(pg.surfarray.make_surface(img_arr))

    def _move_with_keys(self: Self) -> None:
        """Moves the selection with the keyboard."""

        if K_UP   in KEYBOARD.timed:
            self._selection_i = 0
            self._w_box.cursor_i = self._w_box.text_label.get_closest_to(self._h_box.cursor_rect.x)
        if K_DOWN in KEYBOARD.timed:
            self._selection_i = 1
            self._h_box.cursor_i = self._h_box.text_label.get_closest_to(self._w_box.cursor_rect.x)

    def _upt_sliders(self: Self) -> None:
        """Updates sliders and selection."""

        obj: UIElement

        selected_obj: UIElement = (self._w_box, self._h_box)[self._selection_i]
        for i, obj in enumerate((self._w_box, self._h_box)):
            prev_selected_obj: UIElement = selected_obj
            selected_obj = obj.upt(selected_obj)

            if selected_obj != prev_selected_obj:
                prev_selected_obj.leave()
                self._selection_i = i

    def _adjust_opp_slider(self: Self, prev_w_box_text: str) -> None:
        """
        Adjusts the opposite slider to keep their ratio.

        Args:
            previous width input box text
        """

        if self._w_box.text_label.text != prev_w_box_text:
            self._h_box.value = min(max(
                round(self._w_box.value * self.w_ratio),
                self._h_box.min_limit), self._h_box.max_limit
            )

            if self._w_box.text_label.text == "" and self._h_box.value == self._h_box.min_limit:
                self._h_box.text_label.text = ""
            else:
                self._h_box.text_label.text = str(self._h_box.value)
        else:  # did_grid_h_change
            self._w_box.value = min(max(
                round(self._h_box.value * self.h_ratio),
                self._w_box.min_limit), self._w_box.max_limit
            )

            if self._h_box.text_label.text == "" and self._w_box.value == self._w_box.min_limit:
                self._w_box.text_label.text = ""
            else:
                self._w_box.text_label.text = str(self._w_box.value)

    def _crop_tiles(self: Self) -> None:
        """Removes unnecessary padding from the image, sets sliders and ratios."""

        left: intp
        right: intp
        top: intp
        bottom: intp

        colored_tiles_indices: NDArray[intp] = np.argwhere(self._original_tiles[..., 3] != 0)
        if colored_tiles_indices.size == 0:
            left  = top    = intp(0)
            right = bottom = intp(1)
        else:
            left , top    = colored_tiles_indices.min(0)
            right, bottom = colored_tiles_indices.max(0) + 1

        # Copying is unnecessary
        self._original_tiles = self._tiles = self._original_tiles[left:right, top:bottom]
        self._w_box.value = min(max(
            self._tiles.shape[0],
            self._w_box.min_limit), self._w_box.max_limit
        )
        self._h_box.value = min(max(
            self._tiles.shape[1],
            self._h_box.min_limit), self._h_box.max_limit
        )
        self.w_ratio = self._h_box.value / self._w_box.value
        self.h_ratio = self._w_box.value / self._h_box.value

        self._refresh_preview()

    def _rotate_tiles(self: Self, direction: Literal[-1, 1]) -> None:
        """
        Rotates the tiles by 90 degrees in a direction.

        Args:
            direction
        """

        # Copying is unnecessary
        self._original_tiles = self._tiles = np.rot90(self._original_tiles, direction)
        self._w_box.value, self._h_box.value = self._h_box.value, self._w_box.value
        self.w_ratio, self.h_ratio = self.h_ratio, self.w_ratio
        self._refresh_preview()

    def upt(self: Self) -> tuple[bool, bool, NDArray[uint8]]:
        """
        Allows selecting an area with 2 sliders and view its preview.

        Returns:
            exiting flag, confirming flag, tiles
        """

        is_exiting: bool
        is_confirming: bool

        prev_w_box_text: str = self._w_box.text_label.text
        prev_h_box_text: str = self._h_box.text_label.text

        if KEYBOARD.timed != []:
            self._move_with_keys()

        self._upt_sliders()

        is_ctrl_k_pressed: bool = KEYBOARD.is_ctrl_on and K_k in KEYBOARD.timed
        did_toggle_checkbox: bool = self.checkbox.upt(is_ctrl_k_pressed)
        if did_toggle_checkbox and self.checkbox.is_checked:
            self.w_ratio = self._h_box.value / self._w_box.value
            self.h_ratio = self._w_box.value / self._h_box.value

        if (
            self._w_box.text_label.text != prev_w_box_text or
            self._h_box.text_label.text != prev_h_box_text
        ):
            if self.checkbox.is_checked:
                self._adjust_opp_slider(prev_w_box_text)
            self._refresh_preview()

        is_crop_clicked: bool = self._crop.upt()
        is_ctrl_c_pressed: bool = KEYBOARD.is_ctrl_on and K_c in KEYBOARD.pressed
        if is_crop_clicked or is_ctrl_c_pressed:
            self._crop_tiles()

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

        self._w_box.refresh()
        self._h_box.refresh()
        is_exiting, is_confirming = self._base_upt()
        return is_exiting, is_confirming, self._tiles
