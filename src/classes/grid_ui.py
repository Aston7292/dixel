"""
interface to modify the grid
"""

import pygame as pg
from typing import Tuple, Final

from src.classes.ui import UI
from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo
from src.const import ColorType, BlitSequence

CHOOSING_BOX: Final[pg.SurfaceType] = pg.Surface((100, 50))


class NumChooser:
    """
    class that allows the user to pick a number in a range
    """

    __slots__ = (
        '_init_pos', '_img', 'rect', '_init_size',  'value', '_hovering', '_scrolling',
        '_starting_x', '_starting_value', '_text'
    )

    def __init__(self, pos: RectPos, value: int):
        """
        creates the choosing box
        takes position and starting value
        """

        self._init_pos: RectPos = pos

        self._img: pg.SurfaceType = CHOOSING_BOX
        self.rect: pg.FRect = self._img.get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self.value: int = value

        self._hovering: bool = False
        self._scrolling: bool = False

        self._starting_x: int = 0
        self._starting_value: int = self.value

        self._text: Text = Text(RectPos(*self.rect.center, 'center'), 32, str(self.value))

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(self._img, self.rect.topleft)]
        sequence += self._text.blit()

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

        self._text.handle_resize(win_ratio_w, win_ratio_h)

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
                self._starting_x = 0
        else:
            if not self._hovering:
                self._hovering = True
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_SIZEWE)

            if not mouse_info.buttons[0]:
                self._scrolling = False
            elif not self._scrolling:
                self._scrolling = True
                self._starting_x = mouse_info.x
                self._starting_value = self.value

        if self._scrolling:
            self.value = self._starting_value + (mouse_info.x - self._starting_x) // 10

            self.value = max(min(self.value, 128), 0)
            self._text.modify_text(str(self.value))

class GridUI:
    """
    class to create an interface that allows the user to modify the grid
    """

    __slots__ = (
        '_ui', '_preview_init_pos', '_pixel_dim', '_preview_img', '_preview_rect',
        '_preview_init_size', '_h_chooser', '_w_chooser'
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

        self._pixel_dim: int = 8
        self._preview_img: pg.SurfaceType = pg.Surface(
            (grid_size.w * self._pixel_dim, grid_size.h * self._pixel_dim)
        )
        self._preview_rect: pg.FRect = self._preview_img.get_frect(
            **{self._preview_init_pos.pos: self._preview_init_pos.xy}
        )

        self._preview_init_size: Size = Size(int(self._preview_rect.w), int(self._preview_rect.h))

        self._h_chooser: NumChooser = NumChooser(
            RectPos(self._ui.rect.centerx, self._preview_rect.y - 25, 'midbottom'), grid_size.h
        )
        self._w_chooser: NumChooser = NumChooser(
            RectPos(self._ui.rect.centerx, self._h_chooser.rect.y - 25, 'midbottom'), grid_size.w
        )

        self._get_preview()

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = self._ui.blit()
        sequence += self._w_chooser.blit()
        sequence += self._h_chooser.blit()
        sequence += [(self._preview_img, self._preview_rect.topleft)]

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size
        """

        self._ui.handle_resize(win_ratio_w, win_ratio_h)

        preview_size: Tuple[int, int] = (
            int(self._preview_init_size.w * win_ratio_w),
            int(self._preview_init_size.h * win_ratio_h)
        )
        preview_pos: Tuple[float, float] = (
            self._preview_init_pos.x * win_ratio_w, self._preview_init_pos.y * win_ratio_h
        )

        self._preview_img = pg.transform.scale(self._preview_img, preview_size)
        self._preview_rect = self._preview_img.get_frect(
            **{self._preview_init_pos.pos: preview_pos}
        )

        self._w_chooser.handle_resize(win_ratio_w, win_ratio_h)
        self._h_chooser.handle_resize(win_ratio_w, win_ratio_h)

    def _get_preview(self) -> None:
        """
        Draws a preview of the grid
        """

        empty_pixel: pg.SurfaceType = pg.Surface((self._pixel_dim, self._pixel_dim))
        half_size: int = (self._pixel_dim + 1) // 2
        for row in range(2):
            for col in range(2):
                rect: Tuple[int, int, int, int] = (
                    col * half_size, row * half_size, half_size, half_size
                )
                color: ColorType = (85, 85, 85) if (row + col) % 2 == 0 else (75, 75, 75)
                pg.draw.rect(empty_pixel, color, rect)

        sequence: BlitSequence = [
            (empty_pixel, (x * self._pixel_dim, y * self._pixel_dim))
            for x in range(self._w_chooser.value) for y in range(self._h_chooser.value)
        ]
        self._preview_img.fblits(sequence)

    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        makes the object interactable
        takes mouse info
        return whatever the interface was closed or not
        """

        self._w_chooser.upt(mouse_info)
        self._h_chooser.upt(mouse_info)

        confirmed: bool
        exited: bool
        confirmed, exited = self._ui.upt(mouse_info)

        return confirmed or exited
