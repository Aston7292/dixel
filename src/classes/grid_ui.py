"""
interface to modify the grid
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Final, Optional, Any

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, CHECK_BOX_1, CHECK_BOX_2, INPUT_BOX
from src.classes.clickable import CheckBox
from src.classes.text import Text
from src.utils import (
    RectPos, Size, MouseInfo, ColorType, BlitSequence, LayeredBlitSequence, LayersInfo
)
from src.const import EMPTY_1, EMPTY_2, BG_LAYER, ELEMENT_LAYER

MAX_SIZE: Final[int] = 256


class NumSlider:
    """
    class that allows the user to pick a number in a predefined range either via mouse or keyboard
    """

    __slots__ = (
        'value', 'value_input_box', 'rect', 'traveled_x', 'sliding', '_prev_mouse_x', '_add_text'
    )

    def __init__(self, pos: RectPos, value: int, text: str, base_layer: int = BG_LAYER) -> None:
        """
        creates the slider and text
        takes position, starting value and text
        """

        self.value: int = value
        self.value_input_box: NumInputBox = NumInputBox(
            pos, INPUT_BOX, str(self.value), base_layer
        )

        self.rect: pg.FRect = self.value_input_box.box_rect

        self.traveled_x: int = 0
        self.sliding: bool = False

        self._prev_mouse_x: int = pg.mouse.get_pos()[0]

        self._add_text: Text = Text(
            RectPos(self.rect.x - 10.0, self.rect.centery, 'midright'), text, base_layer
        )

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = self.value_input_box.blit()
        sequence += self._add_text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self.value_input_box.handle_resize(win_ratio_w, win_ratio_h)
        self._add_text.handle_resize(win_ratio_w, win_ratio_h)

    def leave(self) -> None:
        """
        clears everything that needs to be cleared when the object is leaved
        """

        self.sliding = False
        self.traveled_x = 0
        self.value_input_box.leave()

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = [('slider', -1, counter)]
        layers_info += self.value_input_box.print_layers('input box', counter + 1)
        layers_info += self._add_text.print_layers('text', counter + 1)

        return layers_info

    def set_value(self, value: int) -> None:
        """
        sets the slider on a specific value
        takes value
        """

        self.traveled_x = 0
        self.value = value
        self.value_input_box.text.set_text(str(self.value))
        self.value_input_box.text_i = 0

        self.value_input_box.get_cursor_pos()

    def upt(self, mouse_info: MouseInfo, keys: list[int], selection: 'NumSlider') -> bool:
        """
        makes the object interactable
        takes mouse info, keys and selection
        returns whatever the slider was clicked or not
        """

        prev_text: str = self.value_input_box.text.text

        clicked: bool
        text: str
        clicked, text = self.value_input_box.upt(
            mouse_info, keys, (1, MAX_SIZE), selection == self
        )

        if clicked:
            return True

        if not self.value_input_box.hovering:
            if not mouse_info.buttons[0]:
                self.sliding = False
                self.traveled_x = 0
        else:
            if not mouse_info.buttons[0]:
                self.sliding = False
                self.traveled_x = 0
            else:
                self.sliding = True

        if self.sliding:
            self.traveled_x += mouse_info.x - self._prev_mouse_x
            if abs(self.traveled_x) >= 10:
                pixels_traveled: int = round(self.traveled_x / 10)
                self.traveled_x -= pixels_traveled * 10

                value: int = max(min(self.value + pixels_traveled, MAX_SIZE), 1)
                text = str(value)

        if text != prev_text:
            self.value = int(text) if text else 1
            self.value_input_box.text.set_text(text)
            self.value_input_box.get_cursor_pos()

        self._prev_mouse_x = mouse_info.x

        return False


class GridUI(UI):
    """
    class to create an interface that allows the user to modify the grid, includes preview,
    """

    __slots__ = (
        '_preview_init_pos', '_preview_pos', '_preview_init_dim', '_preview_img', '_preview_rect',
        '_preview_layer', '_h_slider', '_w_slider', '_values_ratio', '_pixels', '_selection_i',
        '_check_box', '_min_win_ratio', '_small_preview_img'
    )

    def __init__(self, pos: RectPos, grid_size: Size) -> None:
        """
        initializes the interface
        takes position and starting grid size
        """

        #  preview pixel_dim is a float to represent the full size more accurately when resizing

        super().__init__(pos, 'MODIFY GRID')

        self._preview_init_pos: RectPos = RectPos(
            self._ui_rect.centerx, self._ui_rect.centery + 40.0, 'center'
        )
        self._preview_pos: tuple[float, float] = self._preview_init_pos.xy

        self._preview_init_dim: int = 300

        self._preview_img: pg.SurfaceType = pg.Surface(
            (self._preview_init_dim, self._preview_init_dim)
        )
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: self._preview_pos}
        )

        self._preview_layer: int = self._base_layer + ELEMENT_LAYER

        self._h_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20.0, self._preview_rect.y - 25.0, 'bottomleft'),
            grid_size.h, 'height', self._base_layer
        )
        self._w_slider: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20.0, self._h_slider.rect.y - 25.0, 'bottomleft'),
            grid_size.w, 'width', self._base_layer
        )
        self._values_ratio: tuple[float, float] = (1.0, 1.0)

        self._pixels: NDArray[np.uint8] = np.empty(
            (self._h_slider.value, self._w_slider.value, 4), np.uint8
        )
        self._selection_i: int = 0

        self._check_box: CheckBox = CheckBox(
            RectPos(self._preview_rect.right - 20.0, self._h_slider.rect.centery, 'midright'),
            (CHECK_BOX_1, CHECK_BOX_2), 'keep ratio', '(CTRL+K)', self._base_layer
        )

        self._min_win_ratio: float = 1.0  # keeps the pixels as squares

        # having a version where 1 grid pixel = 1 pixel is better for scaling
        self._small_preview_img: pg.SurfaceType = pg.Surface(
            (self._w_slider.value * 2, self._h_slider.value * 2)
        )
        self._get_preview(Size(self._w_slider.value, self._h_slider.value))

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = super().blit()
        sequence += self._w_slider.blit()
        sequence += self._h_slider.blit()
        sequence += self._check_box.blit()
        sequence += [(self._preview_img, self._preview_rect.topleft, self._preview_layer)]

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size
        """

        self._min_win_ratio = min(win_ratio_w, win_ratio_h)

        super().handle_resize(win_ratio_w, win_ratio_h)

        pixel_dim: float = min(
            self._preview_init_dim / self._w_slider.value * self._min_win_ratio,
            self._preview_init_dim / self._h_slider.value * self._min_win_ratio
        )
        size: tuple[int, int] = (
            int(self._w_slider.value * pixel_dim),
            int(self._h_slider.value * pixel_dim)
        )

        self._preview_pos = (
            self._preview_init_pos.x * win_ratio_w, self._preview_init_pos.y * win_ratio_h
        )

        self._preview_img = pg.transform.scale(self._small_preview_img, size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: self._preview_pos}
        )

        self._w_slider.handle_resize(win_ratio_w, win_ratio_h)
        self._h_slider.handle_resize(win_ratio_w, win_ratio_h)
        self._check_box.handle_resize(win_ratio_w, win_ratio_h)

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = super().print_layers(name, counter)
        layers_info += self._w_slider.print_layers('slider', counter + 1)
        layers_info += self._h_slider.print_layers('slider', counter + 1)
        layers_info += self._check_box.print_layers('checkbox', counter + 1)
        layers_info += [('preview', self._preview_layer, counter + 1)]

        return layers_info

    def set_size(self, size: Size, pixels: NDArray[np.uint8]) -> None:
        """
        sets the ui on a specific size
        takes size and grid pixels
        """

        self._w_slider.set_value(size.w)
        self._h_slider.set_value(size.h)
        self._pixels = pixels
        self._values_ratio = (size.h / size.w, size.w / size.h)

        self._get_preview(size)

    def _get_preview(self, grid_size: Size) -> None:
        """
        draws a preview of the grid
        takes grid size
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

        empty_pixel: pg.SurfaceType = pg.Surface((2, 2))
        for y in range(2):
            for x in range(2):
                color: ColorType = EMPTY_1 if (x + y) % 2 == 0 else EMPTY_2
                empty_pixel.set_at((x, y), color)

        sequence: BlitSequence = []
        pixel_surf: pg.SurfaceType = pg.Surface((2, 2))
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
        size: tuple[int, int] = (
            int(grid_size.w * pixel_dim),
            int(grid_size.h * pixel_dim)
        )

        self._preview_img = pg.transform.scale(self._small_preview_img, size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: self._preview_pos}
        )

    def upt(
            self, mouse_info: MouseInfo, keys: list[int], ctrl: int
    ) -> tuple[bool, Optional[Size]]:
        """
        makes the object interactable
        takes mouse info, keys and ctrl
        returns whatever the interface was closed or not and the size (can be None)
        """

        if keys:
            if pg.K_UP in keys:
                self._selection_i = 0
            if pg.K_DOWN in keys:
                self._selection_i = 1

        prev_grid_size: Size = Size(self._w_slider.value, self._h_slider.value)
        selection: Any = (self._w_slider, self._h_slider)[self._selection_i]

        if self._w_slider.upt(mouse_info, keys, selection):
            self._selection_i = 0
        if self._h_slider.upt(mouse_info, keys, selection):
            self._selection_i = 1

        grid_size: Size = Size(self._w_slider.value, self._h_slider.value)
        if grid_size != prev_grid_size:
            if self._check_box.ticked_on:
                value: int
                opp_slider: NumSlider
                if grid_size.w != prev_grid_size.w:
                    value = max(min(round(grid_size.w * self._values_ratio[0]), MAX_SIZE), 1)
                    opp_slider = self._h_slider
                else:
                    value = max(min(round(grid_size.h * self._values_ratio[1]), MAX_SIZE), 1)
                    opp_slider = self._w_slider

                opp_slider.value = value
                opp_slider.value_input_box.text.set_text(str(opp_slider.value))
                opp_slider.value_input_box.text_i = min(
                    opp_slider.value_input_box.text_i, len(opp_slider.value_input_box.text.text)
                )

                opp_slider.value_input_box.get_cursor_pos()
                grid_size.w, grid_size.h = self._w_slider.value, self._h_slider.value

            self._get_preview(grid_size)

        if self._check_box.upt(mouse_info, bool(ctrl and pg.K_k in keys)):
            self._values_ratio = (grid_size.h / grid_size.w, grid_size.w / grid_size.h)

        confirmed: bool
        exited: bool
        confirmed, exited = self._base_upt(mouse_info, keys, ctrl)

        if confirmed or exited:
            self._selection_i = 0
            for slider in (self._w_slider, self._h_slider):
                slider.leave()
            self._check_box.leave()

        return confirmed or exited, grid_size if confirmed else None
