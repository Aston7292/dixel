"""
Interface to modify the grid's size
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Final, Optional, Any

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, CHECK_BOX_1, CHECK_BOX_2, INPUT_BOX
from src.classes.clickable import CheckBox
from src.classes.text import Text
from src.utils import RectPos, Size, ObjInfo, MouseInfo
from src.type_utils import ColorType, BlitSequence, LayeredBlitSequence, LayerSequence

from src.consts import LIGHT_GRAY, DARK_GRAY, BG_LAYER, ELEMENT_LAYER

MAX_SIZE: Final[int] = 256


class NumSlider:
    """
    Class that allows picking a number in a predefined range either by sliding or typing
    """

    __slots__ = (
        'value', 'value_input_box', '_traveled_x', '_sliding', '_prev_mouse_x', 'objs_info'
    )

    def __init__(self, pos: RectPos, value: int, text: str, base_layer: int = BG_LAYER) -> None:
        """
        Creates the slider and text
        Args:
            position, value, text, base layer (default = BG_LAYER)
        """

        self.value: int = value
        self.value_input_box: NumInputBox = NumInputBox(
            pos, INPUT_BOX, str(self.value), base_layer
        )

        self._traveled_x: int = 0
        self._sliding: bool = False

        self._prev_mouse_x: int = pg.mouse.get_pos()[0]

        add_text_obj: Text = Text(
            RectPos(
                self.value_input_box.box_rect.x - 10.0, self.value_input_box.box_rect.centery,
                'midright'
            ),
            text, base_layer
        )
        self.objs_info: list[ObjInfo] = [
            ObjInfo('input box', self.value_input_box), ObjInfo('additional text', add_text_obj)
        ]

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._sliding = False
        self._traveled_x = 0

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, -1, depth_counter)]

    def set_value(self, value: int) -> None:
        """
        Sets the slider on a specific value
        Args:
            value
        """

        self._traveled_x = 0
        self.value = value
        self.value_input_box.set_text(str(self.value), 0)

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...],
            selection: 'NumSlider'
    ) -> bool:
        """
        Allows to select a color either by sliding or typing
        Args:
            hovered object (can be None), mouse info, keys, selection
        Returns:
            True if the slider was clicked else False
        """

        prev_text: str = self.value_input_box.text.text

        clicked: bool
        text: str
        clicked, text = self.value_input_box.upt(
            hover_obj, mouse_info, keys, (1, MAX_SIZE), selection == self
        )

        if clicked:
            return True

        if not self.value_input_box.hovering:
            if not mouse_info.pressed[0]:
                self._sliding = False
                self._traveled_x = 0
        else:
            if not mouse_info.pressed[0]:
                self._sliding = False
                self._traveled_x = 0
            else:
                self._sliding = True

        if self._sliding:
            self._traveled_x += mouse_info.x - self._prev_mouse_x
            if abs(self._traveled_x) >= 10:
                pixels_traveled: int = round(self._traveled_x / 10.0)
                self._traveled_x -= pixels_traveled * 10

                value: int = max(min(self.value + pixels_traveled, MAX_SIZE), 1)
                text = str(value)

        if text != prev_text:
            self.value = int(text) if text else 1
            self.value_input_box.set_text(text)

        self._prev_mouse_x = mouse_info.x

        return False


class GridUI(UI):
    """
    Class to create an interface that allows modifying the grid's size with 2 sliders,
    includes preview
    """

    __slots__ = (
        '_preview_init_pos', '_preview_pos', '_preview_init_dim', '_preview_img', '_preview_rect',
        '_preview_layer', '_h_slider', '_w_slider', '_values_ratio', '_pixels', '_selection_i',
        '_check_box', '_min_win_ratio', '_small_preview_img'
    )

    def __init__(self, pos: RectPos, grid_size: Size) -> None:
        """
        Initializes the interface
        Args:
            position, grid size
        """

        '''
        Preview pixels dimension is a float
        to represent the full size more accurately when resizing
        '''

        super().__init__(pos, 'MODIFY GRID')

        self._preview_init_pos: RectPos = RectPos(
            self._rect.centerx, self._rect.centery + 40.0, 'center'
        )
        self._preview_pos: tuple[float, float] = self._preview_init_pos.xy

        self._preview_init_dim: int = 300

        self._preview_img: pg.Surface = pg.Surface(
            (self._preview_init_dim, self._preview_init_dim)
        )
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord_type: self._preview_pos}
        )

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        self._h_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20.0, self._preview_rect.y - 25.0, 'bottomleft'),
            grid_size.h, 'height', self._base_layer
        )
        self._w_slider: NumSlider = NumSlider(
            RectPos(
                self._preview_rect.x + 20.0, self._h_slider.value_input_box.box_rect.y - 25.0,
                'bottomleft'
            ),
            grid_size.w, 'width', self._base_layer
        )
        self._values_ratio: tuple[float, float] = (1.0, 1.0)

        self._pixels: NDArray[np.uint8] = np.empty(
            (self._h_slider.value, self._w_slider.value, 4), np.uint8
        )
        self._selection_i: int = 0

        self._check_box: CheckBox = CheckBox(
            RectPos(
                self._preview_rect.right - 20.0, self._h_slider.value_input_box.box_rect.centery,
                'midright'
            ),
            (CHECK_BOX_1, CHECK_BOX_2), 'keep ratio', '(CTRL+K)', self._base_layer
        )

        self._min_win_ratio: float = 1.0  # Keeps the pixels as squares
        self.objs_info.extend((
            ObjInfo('width slider', self._w_slider), ObjInfo('height slider', self._h_slider),
            ObjInfo('checkbox', self._check_box)
        ))

        # Having a version where 1 grid pixel = 1 pixel is better for scaling
        self._small_preview_img: pg.Surface = pg.Surface(
            (self._w_slider.value * 2, self._h_slider.value * 2)
        )
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

        pixel_dim: float = min(
            self._preview_init_dim / self._w_slider.value * self._min_win_ratio,
            self._preview_init_dim / self._h_slider.value * self._min_win_ratio
        )
        size: tuple[int, int] = (
            int(self._w_slider.value * pixel_dim), int(self._h_slider.value * pixel_dim)
        )

        self._preview_pos = (
            self._preview_init_pos.x * win_ratio_w, self._preview_init_pos.y * win_ratio_h
        )

        self._preview_img = pg.transform.scale(self._small_preview_img, size)
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
        sequence.append(('preview', self._preview_layer, depth_counter + 1))

        return sequence

    def set_size(self, size: Size, pixels: NDArray[np.uint8]) -> None:
        """
        Sets the UI on a specific size
        Args:
            size, grid pixels
        """

        self._w_slider.set_value(size.w)
        self._h_slider.set_value(size.h)
        self._pixels = pixels
        self._values_ratio = (size.h / size.w, size.w / size.h)

        self._get_preview(size)

    def _get_preview(self, grid_size: Size) -> None:
        """
        Draws a preview of the grid
        Args:
            grid size
        """

        self._small_preview_img = pg.Surface((grid_size.w * 2, grid_size.h * 2))

        pixels: NDArray[np.uint8] = self._pixels
        add_rows: int = grid_size.h - pixels.shape[0]
        add_cols: int = grid_size.w - pixels.shape[1]

        if add_rows < 0:
            pixels = pixels[:grid_size.h, :, :]
        elif add_rows > 0:
            pixels = np.pad(pixels, ((0, add_rows), (0, 0), (0, 0)), constant_values=0)
        if add_cols < 0:
            pixels = pixels[:, :grid_size.w, :]
        elif add_cols > 0:
            pixels = np.pad(pixels, ((0, 0), (0, add_cols), (0, 0)), constant_values=0)

        empty_pixel: pg.Surface = pg.Surface((2, 2))
        for y in range(2):
            for x in range(2):
                color: ColorType = LIGHT_GRAY if (x + y) % 2 == 0 else DARK_GRAY
                empty_pixel.set_at((x, y), color)

        sequence: BlitSequence = []
        pixel_surf: pg.Surface = pg.Surface((2, 2))
        for y in range(grid_size.h):
            row: NDArray[np.uint8] = pixels[y]
            for x in range(grid_size.w):
                if not row[x, -1]:
                    sequence.append((empty_pixel, (x * 2, y * 2)))
                else:
                    pixel_surf.fill(row[x])
                    sequence.append((pixel_surf.copy(), (x * 2, y * 2)))
        self._small_preview_img.fblits(sequence)

        pixel_dim: float = min(
            self._preview_init_dim / grid_size.w * self._min_win_ratio,
            self._preview_init_dim / grid_size.h * self._min_win_ratio
        )
        size: tuple[int, int] = (int(grid_size.w * pixel_dim), int(grid_size.h * pixel_dim))

        self._preview_img = pg.transform.scale(self._small_preview_img, size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord_type: self._preview_pos}
        )

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], ctrl: int
    ) -> tuple[bool, Optional[Size]]:
        """
        Allows selecting a grid size with 2 sliders and view it's preview
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

        prev_grid_size: Size = Size(self._w_slider.value, self._h_slider.value)
        selection: Any = (self._w_slider, self._h_slider)[self._selection_i]

        if self._w_slider.upt(hover_obj, mouse_info, keys, selection):
            self._selection_i = 0
        if self._h_slider.upt(hover_obj, mouse_info, keys, selection):
            self._selection_i = 1

        grid_size: Size = Size(self._w_slider.value, self._h_slider.value)
        if grid_size != prev_grid_size:
            if self._check_box.is_ticked:
                value: int
                opp_slider: NumSlider
                if grid_size.w != prev_grid_size.w:
                    value = max(min(round(grid_size.w * self._values_ratio[0]), MAX_SIZE), 1)
                    opp_slider = self._h_slider
                else:
                    value = max(min(round(grid_size.h * self._values_ratio[1]), MAX_SIZE), 1)
                    opp_slider = self._w_slider

                opp_slider.value = value
                opp_slider.value_input_box.set_text(str(opp_slider.value))
                grid_size.w, grid_size.h = self._w_slider.value, self._h_slider.value

            self._get_preview(grid_size)

        if self._check_box.upt(hover_obj, mouse_info, bool(ctrl and pg.K_k in keys)):
            self._values_ratio = (grid_size.h / grid_size.w, grid_size.w / grid_size.h)

        confirmed: bool
        exited: bool
        confirmed, exited = self._base_upt(hover_obj, mouse_info, keys, ctrl)

        return confirmed or exited, grid_size if confirmed else None
