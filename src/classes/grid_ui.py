"""
Interface to modify the grid's size
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Final, Optional, Any

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, CHECKBOX_1_IMG, CHECKBOX_2_IMG, INPUT_BOX_IMG
from src.classes.clickable import Checkbox
from src.classes.text import TextLabel
from src.utils import RectPos, Size, ObjInfo, MouseInfo
from src.type_utils import BlitSequence, LayeredBlitSequence, LayerSequence

from src.consts import EMPTY_PIXEL_SURF, BG_LAYER, ELEMENT_LAYER

MAX_DIM: Final[int] = 256


class NumSlider:
    """
    Class that allows picking a number in a predefined range either by sliding or typing
    """

    __slots__ = (
        'value', 'input_box', '_prev_mouse_x', '_traveled_x', '_is_sliding', 'objs_info'
    )

    def __init__(self, pos: RectPos, value: int, text: str, base_layer: int = BG_LAYER) -> None:
        """
        Creates the slider and text
        Args:
            position, value, text, base layer (default = BG_LAYER)
        """

        self.value: int = value
        self.input_box: NumInputBox = NumInputBox(pos, INPUT_BOX_IMG, str(self.value), base_layer)

        self._prev_mouse_x: int = pg.mouse.get_pos()[0]
        self._traveled_x: int = 0
        self._is_sliding: bool = False

        extra_text_label: TextLabel = TextLabel(
            RectPos(self.input_box.box_rect.x - 10.0, self.input_box.box_rect.centery, 'midright'),
            text, base_layer
        )

        self.objs_info: list[ObjInfo] = [
            ObjInfo("input box", self.input_box),
            ObjInfo("additional text", extra_text_label)
        ]

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._is_sliding = False
        self._traveled_x = 0

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, None, depth_counter)]

    def set_value(self, value: int) -> None:
        """
        Sets the slider on a specific value
        Args:
            value
        """

        self._traveled_x = 0
        self.value = value
        self.input_box.set_text(str(self.value), 0)

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], selection: Any
    ) -> bool:
        """
        Allows to select a color either by sliding or typing
        Args:
            hovered object (can be None), mouse info, keys, selection
        Returns:
            True if the slider was clicked else False
        """

        prev_text: str = self.input_box.text_label.text

        is_input_box_clicked: bool
        new_text: str
        is_input_box_clicked, new_text = self.input_box.upt(
            hovered_obj, mouse_info, keys, (1, MAX_DIM), selection == self
        )

        if is_input_box_clicked:
            return True

        if not self.input_box.is_hovering:
            if not mouse_info.pressed[0]:
                self._is_sliding = False
                self._traveled_x = 0
        else:
            if not mouse_info.pressed[0]:
                self._is_sliding = False
                self._traveled_x = 0
            else:
                self._is_sliding = True

        if self._is_sliding:
            self._traveled_x += mouse_info.x - self._prev_mouse_x
            if abs(self._traveled_x) >= 10:
                pixels_traveled: int = round(self._traveled_x / 10.0)
                self._traveled_x -= pixels_traveled * 10

                new_value: int = max(min(self.value + pixels_traveled, MAX_DIM), 1)
                new_text = str(new_value)

        if new_text != prev_text:
            self.value = int(new_text) if new_text else 1
            self.input_box.set_text(new_text, None)

        self._prev_mouse_x = mouse_info.x

        return False


class GridUI(UI):
    """
    Class to create an interface that allows modifying the grid's size with 2 sliders,
    includes preview
    """

    __slots__ = (
        '_preview_init_pos', '_preview_pos', '_preview_img', '_preview_rect', '_preview_init_size',
        '_preview_layer', '_h_slider', '_w_slider', '_values_ratio', '_preview_pixels',
        '_checkbox', '_selection_i', '_min_win_ratio', '_small_preview_img'
    )

    def __init__(self, pos: RectPos, grid_area: Size) -> None:
        """
        Initializes the interface
        Args:
            position, grid area
        """

        '''
        Preview pixels dimension is a float
        to represent the full size more accurately when resizing
        '''

        super().__init__(pos, "MODIFY GRID")

        self._preview_init_pos: RectPos = RectPos(
            self._rect.centerx, self._rect.centery + 40.0, 'center'
        )
        self._preview_pos: tuple[float, float] = self._preview_init_pos.xy

        self._preview_img: pg.Surface = pg.Surface((300, 300))
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord_type: self._preview_pos}
        )

        self._preview_init_size: Size = Size(int(self._preview_rect.w), int(self._preview_rect.h))

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        self._h_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20.0, self._preview_rect.y - 25.0, 'bottomleft'),
            grid_area.h, "height", self._base_layer
        )
        self._w_slider: NumSlider = NumSlider(
            RectPos(
                self._preview_rect.x + 20.0, self._h_slider.input_box.box_rect.y - 25.0,
                'bottomleft'
            ),
            grid_area.w, "width", self._base_layer
        )
        self._values_ratio: tuple[float, float] = (1.0, 1.0)

        self._preview_pixels: NDArray[np.uint8] = np.empty(
            (self._h_slider.value, self._w_slider.value, 4), np.uint8
        )

        self._checkbox: Checkbox = Checkbox(
            RectPos(
                self._preview_rect.right - 20.0, self._h_slider.input_box.box_rect.centery,
                'midright'
            ),
            (CHECKBOX_1_IMG, CHECKBOX_2_IMG), "keep ratio", "(CTRL+K)", self._base_layer
        )

        self._selection_i: int = 0
        self._min_win_ratio: float = 1.0  # Keeps the pixels as squares

        # Having a version where 1 grid pixel = 1 pixel is better for scaling
        self._small_preview_img: pg.Surface = pg.Surface(
            (self._w_slider.value * 2, self._h_slider.value * 2)
        )

        self.objs_info.extend((
            ObjInfo("width slider", self._w_slider), ObjInfo("height slider", self._h_slider),
            ObjInfo("checkbox", self._checkbox)
        ))

        self._get_preview(Size(self._w_slider.value, self._h_slider.value))

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = super().blit()
        sequence.append((self._preview_img, self._preview_rect.topleft, self._preview_layer))

        return sequence

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._selection_i = 0

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
        Args:
            window width ratio, window height ratio
        """

        self._min_win_ratio = min(win_ratio_w, win_ratio_h)

        super().handle_resize(win_ratio_w, win_ratio_h)

        preview_pixel_dim: float = min(
            self._preview_init_size.w / self._w_slider.value * self._min_win_ratio,
            self._preview_init_size.h / self._h_slider.value * self._min_win_ratio
        )

        preview_size: tuple[int, int] = (
            int(self._w_slider.value * preview_pixel_dim),
            int(self._h_slider.value * preview_pixel_dim)
        )
        self._preview_pos = (
            self._preview_init_pos.x * win_ratio_w, self._preview_init_pos.y * win_ratio_h
        )

        self._preview_img = pg.transform.scale(self._small_preview_img, preview_size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord_type: self._preview_pos}
        )

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        sequence: LayerSequence = super().print_layer(name, depth_counter)
        sequence.append(("preview", self._preview_layer, depth_counter + 1))

        return sequence

    def set_size(self, area: Size, pixels: NDArray[np.uint8]) -> None:
        """
        Sets the UI on a specific size
        Args:
            area, grid pixels
        """

        self._w_slider.set_value(area.w)
        self._h_slider.set_value(area.h)
        self._preview_pixels = pixels
        self._values_ratio = (area.h / area.w, area.w / area.h)

        self._get_preview(area)

    def _get_preview(self, area: Size) -> None:
        """
        Draws a preview of the grid
        Args:
            area
        """

        self._small_preview_img = pg.Surface((area.w * 2, area.h * 2))

        pixels: NDArray[np.uint8] = self._preview_pixels
        extra_rows: int = area.h - pixels.shape[0]
        extra_cols: int = area.w - pixels.shape[1]

        if extra_rows < 0:
            pixels = pixels[:area.h, :, :]
        elif extra_rows > 0:
            pixels = np.pad(pixels, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0)
        if extra_cols < 0:
            pixels = pixels[:, :area.w, :]
        elif extra_cols > 0:
            pixels = np.pad(pixels, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0)

        sequence: BlitSequence = []

        empty_pixel_surf: pg.Surface = EMPTY_PIXEL_SURF
        pixel_surf: pg.Surface = pg.Surface((2, 2))
        for y in range(area.h):
            row: NDArray[np.uint8] = pixels[y]
            for x in range(area.w):
                if not row[x, -1]:
                    sequence.append((empty_pixel_surf, (x * 2, y * 2)))
                else:
                    pixel_surf.fill(row[x])
                    sequence.append((pixel_surf.copy(), (x * 2, y * 2)))
        self._small_preview_img.fblits(sequence)

        pixel_dim: float = min(
            self._preview_init_size.w / area.w * self._min_win_ratio,
            self._preview_init_size.h / area.h * self._min_win_ratio
        )
        size: tuple[int, int] = (int(area.w * pixel_dim), int(area.h * pixel_dim))

        self._preview_img = pg.transform.scale(self._small_preview_img, size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord_type: self._preview_pos}
        )

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], kmod_ctrl: int
    ) -> tuple[bool, Optional[Size]]:
        """
        Allows selecting a grid area with 2 sliders and view it's preview
        Args:
            hovered object (can be None), mouse info, keys, ctrl
        Returns:
            True if the interface was closed else False, size (can be None)
        """

        if keys:
            if pg.K_UP in keys:
                self._selection_i = 0
            if pg.K_DOWN in keys:
                self._selection_i = 1

        prev_grid_area: Size = Size(self._w_slider.value, self._h_slider.value)
        selection: Any = (self._w_slider, self._h_slider)[self._selection_i]

        if self._w_slider.upt(hovered_obj, mouse_info, keys, selection):
            self._selection_i = 0
        if self._h_slider.upt(hovered_obj, mouse_info, keys, selection):
            self._selection_i = 1

        grid_area: Size = Size(self._w_slider.value, self._h_slider.value)
        if grid_area != prev_grid_area:
            if self._checkbox.is_checked:
                opp_value: int
                opp_slider: NumSlider
                if grid_area.w != prev_grid_area.w:
                    opp_value = max(min(round(grid_area.w * self._values_ratio[0]), MAX_DIM), 1)
                    opp_slider = self._h_slider
                else:
                    opp_value = max(min(round(grid_area.h * self._values_ratio[1]), MAX_DIM), 1)
                    opp_slider = self._w_slider

                opp_slider.value = opp_value
                opp_slider.input_box.set_text(str(opp_slider.value), None)
                grid_area.w, grid_area.h = self._w_slider.value, self._h_slider.value

            self._get_preview(grid_area)

        if self._checkbox.upt(hovered_obj, mouse_info, bool(kmod_ctrl and pg.K_k in keys)):
            self._values_ratio = (grid_area.h / grid_area.w, grid_area.w / grid_area.h)

        confirmed: bool
        exited: bool
        confirmed, exited = self._base_upt(hovered_obj, mouse_info, keys, kmod_ctrl)

        return confirmed or exited, grid_area if confirmed else None
