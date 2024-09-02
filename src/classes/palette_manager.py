"""
class to manage color palettes, includes a drop-down menu
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, List, Final, Optional

from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import Button
from src.utils import RectPos, MouseInfo, add_border, ColorType, BlitSequence
from src.const import BLACK, EMPTY_1

OPTIONS: Final[Tuple[str, ...]] = ('edit', 'delete')


def get_color_info(color: ColorType) -> Tuple[pg.SurfaceType, str]:
    """
    creates surface and text for a color
    takes color
    returns surface and text
    """

    surf: pg.SurfaceType = pg.Surface((32, 32))
    surf.fill(color)
    surf = add_border(surf, EMPTY_1)

    text: str = f'{color[0]}, {color[1]}, {color[2]}'

    return surf, text


class PaletteManager:
    """
    class to manage color palettes, includes a drop-down menu
    """

    __slots__ = (
        '_win_ratio_w', '_win_ratio_h', 'values', '_colors',
        '_options', '_drop_down_i', '_view_drop_down', 'changing_color'
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType]) -> None:
        """
        creates a grid of colors and a drop-down menu to modify it
        takes position
        """

        self._win_ratio_w: float = 1.0
        self._win_ratio_h: float = 1.0

        self.values: List[ColorType] = [BLACK]
        self._colors: CheckBoxGrid = CheckBoxGrid(
            pos, [get_color_info(self.values[0])], 5, (True, True)
        )

        self._options: Tuple[Button, ...] = tuple(
            Button(RectPos(0.0, 0.0, 'topleft'), imgs, option, 20) for option in OPTIONS
        )
        self._drop_down_i: int = 0
        self._view_drop_down: bool = False
        self.changing_color: bool = False

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = self._colors.blit()
        if self._view_drop_down:
            for option in self._options:
                sequence += option.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self._win_ratio_w, self._win_ratio_h = win_ratio_w, win_ratio_h

        self._colors.handle_resize(self._win_ratio_w, self._win_ratio_h)
        for option in self._options:
            option.handle_resize(self._win_ratio_w, self._win_ratio_h)

    def add(self, color: Optional[ColorType]) -> None:
        """
        adds a color to the palette or edits one
        takes color
        """

        if not color:
            self.changing_color = False

            return

        '''
        insert uses window size ratio to adjust the initial position even when inserting
        at a different window size
        '''

        if self.changing_color:
            self.values[self._drop_down_i] = color
            self._colors.insert(
                get_color_info(color), self._win_ratio_w, self._win_ratio_h, self._drop_down_i
            )

            self.changing_color = False
        elif color not in self.values:
            self.values.append(color)
            self._colors.insert(get_color_info(color), self._win_ratio_w, self._win_ratio_h)
        self._colors.set(self.values.index(color))

    def load_path(self, pixels: NDArray[np.uint8]) -> None:
        """
        makes a palette out of every character in an image
        takes path
        """

        pixels_2d: NDArray[np.uint8] = pixels.reshape(-1, 4)[:, :3]
        colors: NDArray[np.uint8] = np.unique(pixels_2d, axis=0)
        self.values = [tuple(int(value) for value in color) for color in colors]

        self._colors.current_x, self._colors.current_y = self._colors.init_pos.xy
        self._colors.check_boxes = []
        for value in self.values:
            self._colors.insert(get_color_info(value), self._win_ratio_w, self._win_ratio_h)

        self._colors.set(0)

    def upt(
            self, mouse_info: MouseInfo, keys: List[int], ctrl: int
    ) -> Tuple[ColorType, Optional[ColorType]]:
        """
        makes the object interactable
        takes mouse info, keys anf ctrl
        returns the selected color and the color to edit
        """

        if mouse_info.released[2]:
            for i, check_box in enumerate(self._colors.check_boxes):
                if check_box.rect.collidepoint(mouse_info.xy):
                    self._view_drop_down = not self._view_drop_down
                    if self._view_drop_down:
                        self._drop_down_i = i
                        current_y: float = mouse_info.y + 5.0
                        for option in self._options:
                            # also changes initial position for resizing
                            option.move_rect(
                                mouse_info.x + 5.0, current_y, self._win_ratio_w, self._win_ratio_h
                            )
                            current_y += option.rect.h

                    break

        '''
        remove uses window size ratio to adjust the initial position even when removing
        at a different window size
        '''

        clicked_option: bool = False
        if self._view_drop_down:
            if self._options[0].upt(mouse_info):
                self.changing_color = True

                clicked_option = True

            if self._options[1].upt(mouse_info):
                self.values.pop(self._drop_down_i)
                if not self.values:
                    self.values = [BLACK]
                self._colors.remove(
                    self._drop_down_i, get_color_info(self.values[0]),
                    self._win_ratio_w, self._win_ratio_h
                )

                clicked_option = True

        if not clicked_option:
            self._colors.upt(mouse_info, keys)

        if ctrl:
            self._view_drop_down = False
            if pg.K_e in keys:
                self._drop_down_i = self._colors.clicked_i
                self.changing_color = True
            if pg.K_DELETE in keys:
                self._drop_down_i = self._colors.clicked_i
                self.values.pop(self._drop_down_i)
                if not self.values:
                    self.values = [BLACK]
                self._colors.remove(
                    self._drop_down_i, get_color_info(self.values[0]),
                    self._win_ratio_w, self._win_ratio_h
                )

        if mouse_info.released[0]:
            self._view_drop_down = False

        color: ColorType = self.values[self._colors.clicked_i]
        color_to_edit: Optional[ColorType] = None

        if self.changing_color:
            color_to_edit = self.values[self._drop_down_i]
            for check_box in self._colors.check_boxes:
                check_box.img_i = 0
                check_box.hovering = False

        return color, color_to_edit
