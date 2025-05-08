"""Interface to edit the grid, preview is refreshed automatically."""

from typing import TypeAlias, Final

import pygame as pg
from pygame.locals import *
import numpy as np
from numpy.typing import NDArray
import cv2

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI
from src.classes.clickable import Checkbox, Button
from src.classes.text_label import TextLabel
from src.classes.devices import Mouse, Keyboard

from src.utils import RectPos, Size, ObjInfo, resize_obj
from src.type_utils import XY, BlitInfo
from src.consts import (
    MOUSE_LEFT, EMPTY_TILE_ARR, TILE_H, TILE_W,
    GRID_TRANSITION_START, GRID_TRANSITION_END, UI_LAYER
)
from src.imgs import CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG, BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG

_Selection: TypeAlias = NumInputBox

_GRID_PREVIEW_DIM_CAP: Final[int] = 325


class NumSlider:
    """Class that allows picking a number in a predefined range either by sliding or typing."""

    __slots__ = (
        "value", "input_box", "_prev_mouse_x", "_traveled_x", "_is_sliding", "blit_sequence",
        "objs_info"
    )

    def __init__(self, pos: RectPos, extra_text: str, base_layer: int = UI_LAYER) -> None:
        """
        Creates the input box and extra text.

        Args:
            position, extra text, base layer (default = UI_LAYER)
        """

        self.value: int = 1
        self.input_box: NumInputBox = NumInputBox(pos, 1, 999, base_layer)

        self._prev_mouse_x: int = pg.mouse.get_pos()[0]
        self._traveled_x: float = 0
        self._is_sliding: bool = False

        extra_text_label: TextLabel = TextLabel(
            RectPos(self.input_box.rect.x - 5, self.input_box.rect.centery, "midright"),
            extra_text, base_layer
        )

        self.blit_sequence: list[BlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.input_box), ObjInfo(extra_text_label)]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self.input_box.cursor_type = SYSTEM_CURSOR_IBEAM
        self._prev_mouse_x = pg.mouse.get_pos()[0]
        self._traveled_x = 0
        self._is_sliding = False

    def set_value(self, value: int) -> None:
        """
        Sets the slider on a specific value.

        Args:
            value
        """

        self.value = value
        self.input_box.text_label.set_text(str(self.value))
        self.input_box.cursor_i = 0
        self.input_box.cursor_rect.x = self.input_box.text_label.rect.x

    def _slide(self, mouse_x: int) -> None:
        """
        Changes the value with the mouse depending on its speed.

        Args:
            mouse x
        """

        speed: float = abs(mouse_x - self._prev_mouse_x) ** 1.5
        if self._prev_mouse_x > mouse_x:
            speed = -speed
        self._traveled_x += speed

        if abs(self._traveled_x) >= 20:
            units_traveled: int = int(self._traveled_x / 20)
            self._traveled_x -= units_traveled * 20

            min_limit: int = self.input_box.min_limit
            max_limit: int = self.input_box.max_limit
            self.value = min(max(self.value + units_traveled, min_limit), max_limit)
            self.input_box.text_label.text = str(self.value)

    def _slide_with_keys(self, keyboard: Keyboard) -> None:
        """
        Changes the value with the keyboard.

        Args:
            keyboard
        """

        step: int = 1
        if keyboard.is_shift_on:
            step = 25

        if K_MINUS in keyboard.timed:
            if keyboard.is_ctrl_on:
                self.value = self.input_box.min_limit
            else:
                self.value = max(self.value - step, self.input_box.min_limit)
            self.input_box.text_label.text = str(self.value)
        if K_PLUS in keyboard.timed:
            if keyboard.is_ctrl_on:
                self.value = self.input_box.max_limit
            else:
                self.value = min(self.value + step, self.input_box.max_limit)
            self.input_box.text_label.text = str(self.value)

    def upt(self, mouse: Mouse, keyboard: Keyboard, selected_obj: _Selection) -> bool:
        """
        Allows to choose a number either by sliding or typing.

        Args:
            mouse, keyboard, selected object
        Returns:
            clicked flag
        """

        if not mouse.pressed[MOUSE_LEFT]:
            self.input_box.cursor_type = SYSTEM_CURSOR_IBEAM
            self._traveled_x = 0
            self._is_sliding = False
        elif self.input_box == mouse.hovered_obj:
            self.input_box.cursor_type = SYSTEM_CURSOR_SIZEWE
            self._is_sliding = True

        if self._is_sliding:
            self._slide(mouse.x)
        if selected_obj == self.input_box and keyboard.timed != []:
            self._slide_with_keys(keyboard)
        is_input_box_clicked: bool = self.input_box.upt(mouse, keyboard, selected_obj)

        self.value = int(self.input_box.text_label.text or self.input_box.min_limit)
        self._prev_mouse_x = mouse.x

        return is_input_box_clicked


class GridUI(UI):
    """Class to create an interface that allows editing the grid, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_rect", "w_ratio", "h_ratio", "_tiles", "_h_slider",
        "_w_slider", "_selection_i", "checkbox", "_crop", "_win_w_ratio", "_win_h_ratio"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the interface, sliders and preview.

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

        preview_img: pg.Surface = pg.Surface(
            (_GRID_PREVIEW_DIM_CAP, _GRID_PREVIEW_DIM_CAP)
        ).convert()
        self._preview_rect: pg.Rect = pg.Rect(0, 0, *preview_img.get_size())
        preview_init_xy: XY = (self._preview_init_pos.x, self._preview_init_pos.y)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, preview_init_xy)

        self.w_ratio = self.h_ratio = 1
        self._tiles: NDArray[np.uint8] = np.zeros((1, 1, 4), np.uint8)

        self._h_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x, self._preview_rect.y - 25, "bottomleft"),
            "Height"
        )
        self._w_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x, self._h_slider.input_box.rect.y - 25, "bottomleft"),
            "Width"
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
        self._win_w_ratio = self._win_h_ratio = 1
        self.objs_info.extend([
            ObjInfo(self._w_slider), ObjInfo(self._h_slider),
            ObjInfo(self.checkbox), ObjInfo(self._crop)
        ])

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

        self._tiles = tiles
        self._w_slider.set_value(area.w)
        self._h_slider.set_value(area.h)
        self._refresh_preview()

    def _fit_tiles(self) -> NDArray[np.uint8]:
        """
        Adjusts the tiles to fit the area.

        Returns:
            tiles
        """

        tiles: NDArray[np.uint8] = self._tiles  # Copying isn't necessary

        extra_w: int = self._w_slider.value - tiles.shape[0]
        if extra_w < 0:
            tiles = tiles[:self._w_slider.value, ...]
        elif extra_w > 0:
            tiles = np.pad(tiles, ((0, extra_w), (0, 0), (0, 0)), constant_values=0)

        extra_h: int = self._h_slider.value - tiles.shape[1]
        if extra_h < 0:
            tiles = tiles[:, :self._h_slider.value, ...]
        elif extra_h > 0:
            tiles = np.pad(tiles, ((0, 0), (0, extra_h), (0, 0)), constant_values=0)

        return tiles

    def _resize_preview(self, small_preview_img: pg.Surface) -> None:
        """
        Resizes the small preview.

        Args:
            small preview image
        """

        xy: XY
        w: int
        h: int
        init_tile_dim: float
        img: pg.Surface

        init_tile_dim = _GRID_PREVIEW_DIM_CAP / max(self._w_slider.value, self._h_slider.value)
        init_w: float = self._w_slider.value * init_tile_dim
        init_h: float = self._h_slider.value * init_tile_dim

        xy, (w, h) = resize_obj(
            self._preview_init_pos, init_w, init_h, self._win_w_ratio, self._win_h_ratio, True
        )

        max_visible_dim: int = max(self._w_slider.value, self._h_slider.value)
        if max_visible_dim < GRID_TRANSITION_START:
            img = pg.transform.scale(small_preview_img, (w, h))
        elif max_visible_dim > GRID_TRANSITION_END:
            img = pg.transform.smoothscale(small_preview_img, (w, h))
        else:
            # Gradual transition
            img_arr: NDArray[np.uint8] = pg.surfarray.pixels3d(small_preview_img)
            img_arr = cv2.resize(img_arr, (h, w), interpolation=cv2.INTER_AREA).astype(np.uint8)
            img = pg.surfarray.make_surface(img_arr)

        self._preview_rect.size = (w, h)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, xy)

        self.blit_sequence[1] = (img.convert(), self._preview_rect, UI_LAYER)

    def _refresh_preview(self) -> None:
        """Refreshes the preview."""

        tiles: NDArray[np.uint8] = self._fit_tiles()

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles = tiles.repeat(TILE_W, 0).repeat(TILE_H, 1)
        empty_tiles: NDArray[np.uint8] = np.tile(
            EMPTY_TILE_ARR, (self._w_slider.value, self._h_slider.value, 1)
        )
        empty_tiles_mask: NDArray[np.bool_] = (tiles[..., 3] == 0)[..., np.newaxis]

        tiles = np.where(empty_tiles_mask, empty_tiles, tiles[..., :3])
        # Having a version where 1 tile = 1 pixel is better for scaling
        small_preview_img: pg.Surface = pg.surfarray.make_surface(tiles)
        self._resize_preview(small_preview_img)

    def _move_with_keys(self, timed_keys: list[int]) -> None:
        """
        Moves the selected object with the keyboard.

        Args:
            timed keys
        """

        if K_UP in timed_keys:
            self._selection_i = 0
            self._w_slider.input_box.cursor_i = self._w_slider.input_box.text_label.get_closest_to(
                self._h_slider.input_box.cursor_rect.x
            )
        if K_DOWN in timed_keys:
            self._selection_i = 1
            self._h_slider.input_box.cursor_i = self._h_slider.input_box.text_label.get_closest_to(
                self._w_slider.input_box.cursor_rect.x
            )

    def _upt_sliders(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Updates sliders and selection.

        Args:
            mouse, keyboard
        """

        selected_obj: _Selection = (self._w_slider, self._h_slider)[self._selection_i].input_box

        is_w_slider_clicked: bool = self._w_slider.upt(mouse, keyboard, selected_obj)
        if is_w_slider_clicked:
            self._selection_i = 0
            selected_obj = self._w_slider.input_box

        is_h_slider_clicked: bool = self._h_slider.upt(mouse, keyboard, selected_obj)
        if is_h_slider_clicked:
            self._selection_i = 1
            selected_obj = self._h_slider.input_box

    def _adjust_opp_slider(self, did_grid_w_change: bool) -> None:
        """
        Adjusts the opposite slider to keep their ratio.

        Args:
            grid width changed flag
        """

        opp_slider: NumSlider
        uncapped_value: int
        slider_text: str

        if did_grid_w_change:
            opp_slider = self._h_slider
            uncapped_value = round(self._w_slider.value * self.w_ratio)
            slider_text = self._w_slider.input_box.text_label.text
        else:
            opp_slider = self._w_slider
            uncapped_value = round(self._h_slider.value * self.h_ratio)
            slider_text = self._h_slider.input_box.text_label.text
        min_limit: int = opp_slider.input_box.min_limit
        max_limit: int = opp_slider.input_box.max_limit
        opp_slider.value = min(max(uncapped_value, min_limit), max_limit)

        opp_slider.input_box.text_label.text = str(opp_slider.value)
        if slider_text == "" and opp_slider.value == 1:
            opp_slider.input_box.text_label.text = ""

    def _crop_tiles(self) -> None:
        """Removes all unnecessary padding from the image, sets sliders and ratios."""

        top_left: NDArray[np.intp]
        bottom_right: NDArray[np.intp]

        mask: NDArray[np.bool_] = self._tiles[..., 3] != 0
        indices: NDArray[np.intp] = np.argwhere(mask)

        if indices.size == 0:
            top_left = np.array((0, 0), np.intp)
            bottom_right = np.array((1, 1), np.intp)
        else:
            top_left = indices.min(0)
            bottom_right = indices.max(0) + 1
        self._tiles = self._tiles[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]]

        self._w_slider.value, self._h_slider.value = self._tiles.shape[0], self._tiles.shape[1]
        self._w_slider.input_box.text_label.text = str(self._w_slider.value)
        self._h_slider.input_box.text_label.text = str(self._h_slider.value)
        self.w_ratio = self._h_slider.value / self._w_slider.value
        self.h_ratio = self._w_slider.value / self._h_slider.value

        self._refresh_preview()

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[bool, bool, int, int]:
        """
        Allows selecting a grid area with 2 sliders and view its preview.

        Args:
            mouse, keyboard
        Returns:
            exiting flag, confirming flag, width, height
        """

        is_exiting: bool
        is_confirming: bool

        if keyboard.timed != []:
            self._move_with_keys(keyboard.timed)

        prev_w_slider_text: str = self._w_slider.input_box.text_label.text
        prev_h_slider_text: str = self._h_slider.input_box.text_label.text

        is_ctrl_k_pressed: bool = keyboard.is_ctrl_on and K_k in keyboard.timed
        self._upt_sliders(mouse, keyboard)
        should_get_size_ratio: bool = self.checkbox.upt(mouse, is_ctrl_k_pressed)
        if should_get_size_ratio:
            self.w_ratio = self._h_slider.value / self._w_slider.value
            self.h_ratio = self._w_slider.value / self._h_slider.value

        did_grid_w_change: bool = self._w_slider.input_box.text_label.text != prev_w_slider_text
        did_grid_h_change: bool = self._h_slider.input_box.text_label.text != prev_h_slider_text
        if did_grid_w_change or did_grid_h_change:
            if self.checkbox.is_checked:
                self._adjust_opp_slider(did_grid_w_change)
            self._refresh_preview()

        is_crop_clicked: bool = self._crop.upt(mouse)
        is_ctrl_c_pressed: bool = keyboard.is_ctrl_on and K_c in keyboard.pressed
        if is_crop_clicked or is_ctrl_c_pressed:
            self._crop_tiles()

        self._w_slider.input_box.refresh()
        self._h_slider.input_box.refresh()
        is_exiting, is_confirming = self._base_upt(mouse, keyboard.pressed)

        return is_exiting, is_confirming, self._w_slider.value, self._h_slider.value
