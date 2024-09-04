"""
class to manage color palettes, includes a drop-down menu
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Final, Optional

from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import Button
from src.utils import RectPos, MouseInfo, add_border, ColorType, LayeredBlitSequence, LayersInfo
from src.const import BLACK, EMPTY_1, S_LAYER

OPTIONS: Final[tuple[tuple[str, str], ...]] = (('edit', '(CTRL+E)'), ('delete', 'CTRL+DEL'))


def get_color_info(color: ColorType) -> tuple[pg.SurfaceType, str]:
    """
    creates surface and text for a color
    takes color
    returns surface and text
    """

    surf: pg.SurfaceType = pg.Surface((32, 32))
    surf.fill(color)
    surf = add_border(surf, EMPTY_1)

    rgb_string: str = f'({color[0]}, {color[1]}, {color[2]})'
    hex_string: str = f'(#{''.join((f'{channel:02x}' for channel in color))})'
    text: str = f'{rgb_string}\n{hex_string}'

    return surf, text


class PaletteManager:
    """
    class to manage color palettes, includes a drop-down menu
    """

    __slots__ = (
        '_win_ratio_w', '_win_ratio_h', 'values', '_colors',
        '_options', '_drop_down_i', '_view_drop_down', 'changing_color'
    )

    def __init__(self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType]) -> None:
        """
        creates a grid of colors and a drop-down menu to modify it
        takes position
        """

        self._win_ratio_w: float = 1.0
        self._win_ratio_h: float = 1.0

        self.values: list[ColorType] = [BLACK]
        self._colors: CheckBoxGrid = CheckBoxGrid(
            pos, [get_color_info(self.values[0])], 5, (True, True)
        )

        self._options: tuple[Button, ...] = tuple(
            Button(RectPos(0.0, 0.0, 'topleft'), imgs, *option, S_LAYER, 20)
            for option in OPTIONS
        )
        self._drop_down_i: int = 0
        self._view_drop_down: bool = False
        self.changing_color: bool = False

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = self._colors.blit()
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

    def leave(self) -> None:
        """
        clears everything that needs to be cleared when the object is leaved
        """

        self._drop_down_i = 0
        self._view_drop_down = False
        self._colors.leave()
        for option in self._options:
            option.leave()

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = [(name, -1, counter)]
        layers_info += self._colors.print_layers('colors', counter + 1)
        layers_info += [('options', -1, counter + 1)]
        for option in self._options:
            layers_info += option.print_layers('option', counter + 2)

        return layers_info

    def add(self, color: Optional[ColorType]) -> None:
        """
        adds a color to the palette or edits one
        takes color
        """

        if not color:
            self.changing_color = False

            return

        '''
        insert method uses window size ratio to adjust the init_pos even when inserting
        at a different window size
        '''

        if self.changing_color:
            self.values[self._drop_down_i] = color
            self._colors.insert(
                self._drop_down_i, get_color_info(color), self._win_ratio_w, self._win_ratio_h
            )

            self.changing_color = False
        elif color not in self.values:
            self.values.append(color)
            self._colors.insert(-1, get_color_info(color), self._win_ratio_w, self._win_ratio_h)
        self._colors.tick_on(self.values.index(color))

    def load_path(self, pixels: NDArray[np.uint8]) -> None:
        """
        makes a palette out of all colors in an image
        takes path
        """

        pixels_2d: NDArray[np.uint8] = pixels.reshape(-1, 4)[:, :3]
        colors: NDArray[np.uint8] = np.unique(pixels_2d, axis=0)
        self.values = [tuple(int(value) for value in color) for color in colors]

        self._colors.current_x, self._colors.current_y = self._colors.init_pos.xy
        self._colors.check_boxes = []
        for value in self.values:
            self._colors.insert(-1, get_color_info(value), self._win_ratio_w, self._win_ratio_h)

        self._colors.tick_on(0)

    def upt(
            self, mouse_info: MouseInfo, keys: list[int], ctrl: int
    ) -> tuple[ColorType, Optional[ColorType]]:
        """
        makes the object interactable
        takes mouse info, keys anf ctrl
        returns the selected color and the color to edit
        """

        if mouse_info.released[2]:
            for i, check_box in enumerate(self._colors.check_boxes):
                if check_box.rect.collidepoint(mouse_info.xy):
                    self._view_drop_down = (
                        not self._view_drop_down if self._drop_down_i == i else True
                    )

                    if self._view_drop_down:
                        self._drop_down_i = i
                        current_y: float = mouse_info.y + 5.0
                        for option in self._options:
                            # also changes init_pos for resizing
                            option.move_rect(
                                mouse_info.x + 5.0, current_y, self._win_ratio_w, self._win_ratio_h
                            )
                            current_y += option.rect.h
                    break
            else:
                self._view_drop_down = False

        '''
        remove method uses window size ratio to adjust the init_pos even when removing
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

        if ctrl:
            if pg.K_e in keys:
                self._drop_down_i = self._colors.clicked_i
                self.changing_color = True

                clicked_option = True
            if pg.K_DELETE in keys:
                self._drop_down_i = self._colors.clicked_i
                self.values.pop(self._drop_down_i)
                if not self.values:
                    self.values = [BLACK]
                self._colors.remove(
                    self._drop_down_i, get_color_info(self.values[0]),
                    self._win_ratio_w, self._win_ratio_h
                )

                clicked_option = True

        if clicked_option:
            self._view_drop_down = False
        else:
            self._colors.upt(mouse_info, keys)

        color: ColorType = self.values[self._colors.clicked_i]
        color_to_edit: Optional[ColorType] = None

        if self.changing_color:
            color_to_edit = self.values[self._drop_down_i]
            for check_box in self._colors.check_boxes:
                check_box.hovering = False

        return color, color_to_edit
