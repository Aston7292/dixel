"""
interface to modify the grid
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, List, Final, Optional, Any

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, CHECK_BOX_1, CHECK_BOX_2, INPUT_BOX
from src.classes.clickable import CheckBox
from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo, ColorType, BlitSequence
from src.const import EMPTY_1, EMPTY_2

MAX_SIZE: Final[int] = 256


class NumSlider:
    """
    class that allows the user to pick a number in a predefined range either via mouse or keyboard
    """

    __slots__ = (
        'value', 'value_input_box', 'rect', 'scrolling', 'traveled_x', '_prev_mouse_x', '_add_text'
    )

    def __init__(self, pos: RectPos, value: int, text: str) -> None:
        """
        creates the slider and text
        takes position, starting value and text
        """

        self.value: int = value
        self.value_input_box: NumInputBox = NumInputBox(pos, INPUT_BOX, str(self.value))

        self.rect: pg.FRect = self.value_input_box.box_rect

        self.traveled_x: int = 0
        self.scrolling: bool = False

        self._prev_mouse_x: int = pg.mouse.get_pos()[0]

        self._add_text: Text = Text(
            RectPos(self.value_input_box.box_rect.x - 10.0, self.rect.centery, 'midright'), text
        )

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = self.value_input_box.blit()
        sequence += self._add_text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self.value_input_box.handle_resize(win_ratio_w, win_ratio_h)
        self._add_text.handle_resize(win_ratio_w, win_ratio_h)

    def set(self, value: int) -> None:
        """
        sets the slider on a specific value
        takes value
        """

        self.traveled_x = 0
        self.value = min(value, MAX_SIZE)
        if self.value > MAX_SIZE:
            self.value = MAX_SIZE
        else:
            self.value_input_box.text_i = 0

        self.value_input_box.text.modify_text(str(self.value))
        self.value_input_box.get_cursor_pos()

    def upt(self, mouse_info: MouseInfo, keys: List[int], selection: 'NumSlider') -> bool:
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
                self.scrolling = False
                self.traveled_x = 0
        else:
            if not mouse_info.buttons[0]:
                self.scrolling = False
                self.traveled_x = 0
            else:
                self.scrolling = True

        # TODO: change mouse sprite when scrolling?
        if self.scrolling:
            self.traveled_x += mouse_info.x - self._prev_mouse_x
            if abs(self.traveled_x) >= 10:
                pixels_traveled: int = round(self.traveled_x / 10)
                self.traveled_x -= pixels_traveled * 10

                value: int = max(min(self.value + pixels_traveled, MAX_SIZE), 1)
                text = str(value)

        if text != prev_text:
            self.value = int(text) if text else 1

            self.value_input_box.text.modify_text(text)
            self.value_input_box.get_cursor_pos()

        self._prev_mouse_x = mouse_info.x

        return False


class GridUI:
    """
    class to create an interface that allows the user to modify the grid, includes preview,
    """

    __slots__ = (
        'ui', '_preview_init_pos', '_preview_pos', '_preview_init_dim',
        '_preview_img', '_preview_rect', '_h_chooser', '_w_chooser', '_values_ratio', '_pixels',
        '_check_box', '_min_win_ratio', '_small_preview_img', '_selection_i'
    )

    def __init__(self, pos: RectPos, grid_size: Size) -> None:
        """
        initializes the interface
        takes position and starting grid size
        """

        self.ui: UI = UI(pos, 'MODIFY GRID')

        self._preview_init_pos: RectPos = RectPos(
            self.ui.rect.centerx, self.ui.rect.centery + 40.0, 'center'
        )
        self._preview_pos: Tuple[float, float] = self._preview_init_pos.xy

        self._preview_init_dim: int = 300

        self._preview_img: pg.SurfaceType = pg.Surface(
            (self._preview_init_dim, self._preview_init_dim)
        )
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: self._preview_pos}
        )

        self._h_chooser: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20.0, self._preview_rect.y - 25.0, 'bottomleft'),
            grid_size.h, 'height'
        )
        self._w_chooser: NumSlider = NumSlider(
            RectPos(self._preview_rect.x + 20.0, self._h_chooser.rect.y - 25.0, 'bottomleft'),
            grid_size.w, 'width'
        )
        self._values_ratio: Tuple[float, float] = (1.0, 1.0)
        self._pixels: NDArray[np.uint8] = np.empty(
            (self._h_chooser.value, self._w_chooser.value, 4), np.uint8
        )

        self._selection_i: int = 0

        self._check_box: CheckBox = CheckBox(
            RectPos(self._preview_rect.right - 20.0, self._h_chooser.rect.centery, 'midright'),
            (CHECK_BOX_1, CHECK_BOX_2), 'keep ratio'
        )

        self._min_win_ratio: float = 1.0  # keeps the pixels as squares

        # having a version where 1 grid pixel = 1 pixel is better for scaling
        self._small_preview_img: pg.SurfaceType = pg.Surface(
            (self._w_chooser.value * 2, self._h_chooser.value * 2)
        )
        self._get_preview(Size(self._w_chooser.value, self._h_chooser.value))

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = self.ui.blit()
        sequence += self._w_chooser.blit()
        sequence += self._h_chooser.blit()
        sequence += self._check_box.blit()
        sequence += [(self._preview_img, self._preview_rect.topleft)]

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size
        """

        self._min_win_ratio = min(win_ratio_w, win_ratio_h)

        self.ui.handle_resize(win_ratio_w, win_ratio_h)

        pixel_dim: float = min(
            self._preview_init_dim / self._w_chooser.value * self._min_win_ratio,
            self._preview_init_dim / self._h_chooser.value * self._min_win_ratio
        )
        size: Tuple[int, int] = (
            int(self._w_chooser.value * pixel_dim),
            int(self._h_chooser.value * pixel_dim)
        )

        self._preview_pos = (
            self._preview_init_pos.x * win_ratio_w, self._preview_init_pos.y * win_ratio_h
        )

        self._preview_img = pg.transform.scale(self._small_preview_img, size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: self._preview_pos}
        )

        self._w_chooser.handle_resize(win_ratio_w, win_ratio_h)
        self._h_chooser.handle_resize(win_ratio_w, win_ratio_h)
        self._check_box.handle_resize(win_ratio_w, win_ratio_h)

    def set(self, size: Size, pixels: NDArray[np.uint8]) -> None:
        """
        sets the ui on a specific size
        takes size and grid pixels
        """

        self._w_chooser.set(size.w)
        self._h_chooser.set(size.h)
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
        size: Tuple[int, int] = (
            int(grid_size.w * pixel_dim),
            int(grid_size.h * pixel_dim)
        )

        self._preview_img = pg.transform.scale(self._small_preview_img, size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.coord: self._preview_pos}
        )

    def upt(
            self, mouse_info: MouseInfo, keys: List[int], ctrl: int
    ) -> Tuple[bool, Optional[Size]]:
        """
        makes the object interactable
        takes mouse info, keys and ctrl
        returns whatever the interface was closed or not and the size
        """

        if keys:
            if pg.K_UP in keys:
                self._selection_i = 0
            elif pg.K_DOWN in keys:
                self._selection_i = 1

        prev_grid_size: Size = Size(self._w_chooser.value, self._h_chooser.value)
        selection: Any = (self._w_chooser, self._h_chooser)[self._selection_i]

        if self._w_chooser.upt(mouse_info, keys, selection):
            self._selection_i = 0
        if self._h_chooser.upt(mouse_info, keys, selection):
            self._selection_i = 1

        grid_size: Size = Size(self._w_chooser.value, self._h_chooser.value)
        if grid_size != prev_grid_size:
            if self._check_box.ticked_on:
                if grid_size.w != prev_grid_size.w:
                    self._h_chooser.set(round(grid_size.w * self._values_ratio[0]))
                    grid_size.h = self._h_chooser.value
                else:
                    self._w_chooser.set(round(grid_size.h * self._values_ratio[1]))
                    grid_size.w = self._w_chooser.value

            self._get_preview(grid_size)

        if self._check_box.upt(mouse_info, bool(ctrl and pg.K_k in keys)):
            self._values_ratio = (grid_size.h / grid_size.w, grid_size.w / grid_size.h)

        confirmed: bool
        exited: bool
        confirmed, exited = self.ui.upt(mouse_info, keys, ctrl)

        if confirmed or exited:
            self._selection_i = 0
            for chooser in (self._w_chooser, self._h_chooser):
                chooser.scrolling = False
                chooser.traveled_x = 0
                chooser.value_input_box.hovering = chooser.value_input_box.selected = False

            self._check_box.hovering = False

        return confirmed or exited, grid_size if confirmed else None
