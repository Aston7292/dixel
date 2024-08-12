"""
interface to modify the grid
"""

import pygame as pg
from os.path import join
from typing import Tuple, Final, Optional

from src.classes.ui import UI
from src.classes.clickable import CheckBox
from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo
from src.const import EMPTY_1, EMPTY_2, ColorType, BlitSequence

CHOOSING_BOX: Final[pg.SurfaceType] = pg.Surface((75, 50))

CHECK_BOX_1: Final[pg.SurfaceType] = pg.image.load(
    join('sprites', 'check_box_off.png')
).convert_alpha()
CHECK_BOX_2: Final[pg.SurfaceType] = pg.image.load(
    join('sprites', 'check_box_on.png')
).convert_alpha()

MAX_SIZE: Final[int] = 256


class NumChooser:
    """
    class that allows the user to pick a number in a predefined range
    """

    __slots__ = (
        '_init_pos', '_img', 'rect', '_init_size', 'value', '_hovering', '_scrolling',
        '_traveled_x', '_prev_mouse_x', '_value_text', '_description'
    )

    def __init__(self, pos: RectPos, value: int, text: str):
        """
        creates the choosing box
        takes position, starting value and text
        """

        self._init_pos: RectPos = pos

        self._img: pg.SurfaceType = CHOOSING_BOX
        self.rect: pg.FRect = self._img.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self.value: int = value

        self._hovering: bool = False
        self._scrolling: bool = False

        self._traveled_x: int = 0
        self._prev_mouse_x: int = pg.mouse.get_pos()[0]

        self._value_text: Text = Text(RectPos(*self.rect.center, 'center'), 32, str(self.value))
        self._description: Text = Text(
            RectPos(self.rect.x - 10, self.rect.centery, 'midright'), 32, text
        )

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(self._img, self.rect.topleft)]
        sequence += self._value_text.blit()
        sequence += self._description.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        size: Tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._img = pg.transform.scale(self._img, size)
        self.rect = self._img.get_frect(**{self._init_pos.pos: pos})

        self._value_text.handle_resize(win_ratio_w, win_ratio_h)
        self._description.handle_resize(win_ratio_w, win_ratio_h)

    def set(self, value: int) -> None:
        """
        sets the chooser on a specific value
        takes value
        """

        self._traveled_x = 0
        self.value = max(min(value, MAX_SIZE), 1)
        self._value_text.modify_text(str(self.value))

    def upt(self, mouse_info: MouseInfo) -> None:
        """
        makes the object interactable
        takes mouse info
        return whatever the interface was closed or not
        """

        if not self.rect.collidepoint(mouse_info.xy):
            if self._hovering:
                self._hovering = False
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

            if not mouse_info.buttons[0]:
                self._scrolling = False
                self._traveled_x = 0
        else:
            if not self._hovering:
                self._hovering = True
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_SIZEWE)

            if not mouse_info.buttons[0]:
                self._scrolling = False
                self._traveled_x = 0
            elif not self._scrolling:
                self._scrolling = True

        if self._scrolling:
            self._traveled_x += mouse_info.x - self._prev_mouse_x
            if abs(self._traveled_x) >= 10:
                pixels_traveled: int = round(self._traveled_x / 10)
                self._traveled_x -= pixels_traveled * 10

                self.value = max(min(self.value + pixels_traveled, MAX_SIZE), 1)
                self._value_text.modify_text(str(self.value))

        self._prev_mouse_x = mouse_info.x


class GridUI:
    """
    class to create an interface that allows the user to modify the grid
    """

    __slots__ = (
        '_ui', '_preview_init_pos', '_preview_pos', '_preview_img', '_preview_rect',
        '_preview_init_size', '_h_chooser', '_w_chooser', '_check_box', '_ratio', '_win_ratio',
        '_small_preview_img'
    )

    def __init__(self, pos: RectPos, grid_size: Size) -> None:
        """
        initializes the interface
        takes position and starting grid size
        """

        self._ui: UI = UI(pos, 'MODIFY GRID')

        self._preview_init_pos: RectPos = RectPos(
            self._ui.rect.centerx, self._ui.rect.centery + 40, 'center'
        )
        self._preview_pos: Tuple[float, float] = self._preview_init_pos.xy

        self._preview_img: pg.SurfaceType = pg.Surface((300, 300))
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.pos: self._preview_pos}
        )

        self._preview_init_size: Size = Size(int(self._preview_rect.w), int(self._preview_rect.h))

        self._h_chooser: NumChooser = NumChooser(
            RectPos(self._preview_rect.x + 20, self._preview_rect.y - 25, 'bottomleft'),
            grid_size.h, 'height'
        )
        self._w_chooser: NumChooser = NumChooser(
            RectPos(self._preview_rect.x + 20, self._h_chooser.rect.y - 25, 'bottomleft'),
            grid_size.w, 'width'
        )

        self._check_box: CheckBox = CheckBox(
            RectPos(self._preview_rect.right - 20, self._h_chooser.rect.centery, 'midright'),
            (CHECK_BOX_1, CHECK_BOX_2), 'keep ratio'
        )

        self._ratio: Tuple[float, float] = (0, 0)
        self._win_ratio: float = 1

        self._small_preview_img: pg.SurfaceType = pg.Surface(
            (self._w_chooser.value * 2, self._h_chooser.value * 2)
        )
        self._get_preview(Size(self._w_chooser.value, self._h_chooser.value))

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = self._ui.blit()
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

        self._win_ratio = min(win_ratio_w, win_ratio_h)

        self._ui.handle_resize(win_ratio_w, win_ratio_h)

        pixel_dim: float = min(
            self._preview_init_size.w / self._w_chooser.value * self._win_ratio,
            self._preview_init_size.h / self._h_chooser.value * self._win_ratio
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
            **{self._preview_init_pos.pos: self._preview_pos}
        )

        self._w_chooser.handle_resize(win_ratio_w, win_ratio_h)
        self._h_chooser.handle_resize(win_ratio_w, win_ratio_h)
        self._check_box.handle_resize(win_ratio_w, win_ratio_h)

    def _get_preview(self, grid_size: Size) -> None:
        """
        draws a preview of the grid
        takes grid size
        """

        pixel_dim: float = min(
            self._preview_init_size.w / grid_size.w * self._win_ratio,
            self._preview_init_size.h / grid_size.h * self._win_ratio
        )

        self._small_preview_img = pg.Surface((grid_size.w * 2, grid_size.h * 2))

        empty_pixel: pg.SurfaceType = pg.Surface((2, 2))
        for row in range(2):
            for col in range(2):
                color: ColorType = EMPTY_1 if (row + col) % 2 == 0 else EMPTY_2
                empty_pixel.set_at((col, row), color)

        self._small_preview_img.fblits(
            (empty_pixel, (x * 2, y * 2)) for x in range(grid_size.w) for y in range(grid_size.h)
        )

        size: Tuple[int, int] = (
            int(grid_size.w * pixel_dim),
            int(grid_size.h * pixel_dim)
        )

        self._preview_img = pg.transform.scale(self._small_preview_img, size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.pos: self._preview_pos}
        )

    def upt(self, mouse_info: MouseInfo) -> Tuple[bool, Optional[Size]]:
        """
        makes the object interactable
        takes mouse info
        return whatever the interface was closed or not
        """

        prev_grid_size: Size = Size(self._w_chooser.value, self._h_chooser.value)

        self._w_chooser.upt(mouse_info)
        self._h_chooser.upt(mouse_info)

        grid_size: Size = Size(self._w_chooser.value, self._h_chooser.value)
        if grid_size != prev_grid_size:
            if self._check_box.ticked:
                if grid_size.w != prev_grid_size.w:
                    self._h_chooser.set(round(grid_size.w * self._ratio[0]))
                    grid_size.h = self._h_chooser.value
                else:
                    self._w_chooser.set(round(grid_size.h * self._ratio[1]))
                    grid_size.w = self._w_chooser.value

            self._get_preview(grid_size)

        if self._check_box.upt(mouse_info) and self._check_box.ticked:
            self._ratio = (
                grid_size.h / grid_size.w,
                grid_size.w / grid_size.h
            )

        confirmed: bool
        exited: bool
        confirmed, exited = self._ui.upt(mouse_info)

        return confirmed or exited, grid_size if confirmed else None
