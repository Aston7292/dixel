"""
class to manage color palettes, includes a drop-down menu
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Final, Optional, Any

from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import Button
from src.utils import RectPos, MouseInfo, check_nested_hover, add_border
from src.type_utils import ColorType, LayeredBlitSequence, LayerSequence
from src.const import BLACK, EMPTY_1, SPECIAL_LAYER

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
        '_options', '_drop_down_i', '_view_drop_down', '_changing_color'
    )

    def __init__(self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType]) -> None:
        """
        creates a grid of colors and a drop-down menu to modify it
        takes position and drop-down menu images
        """

        self._win_ratio_w: float = 1.0
        self._win_ratio_h: float = 1.0

        self.values: list[ColorType] = [BLACK]
        self._colors: CheckBoxGrid = CheckBoxGrid(
            pos, [get_color_info(self.values[0])], 5, (True, True)
        )

        self._options: tuple[Button, ...] = tuple(
            Button(RectPos(0.0, 0.0, 'topleft'), imgs, *option, SPECIAL_LAYER, 20)
            for option in OPTIONS
        )
        self._drop_down_i: int = 0
        self._view_drop_down: bool = False
        self._changing_color: bool = False

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = self._colors.blit()
        if self._view_drop_down:
            for option in self._options:
                sequence += option.blit()

        return sequence

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
        '''
        checks if the mouse is hovering any interactable part of the object
        takes mouse position
        returns the object that's being hovered (can be None) and the layer
        '''

        hover_obj: Any
        hover_layer: int
        hover_obj, hover_layer = self._colors.check_hover(mouse_pos)

        hover_obj, hover_layer = check_nested_hover(
            mouse_pos, self._options, hover_obj, hover_layer
        )

        return hover_obj, hover_layer

    def leave(self) -> None:
        """
        clears relevant data when a state is leaved
        """

        self._drop_down_i = 0
        self._view_drop_down = False
        self._colors.leave()
        for option in self._options:
            option.leave()

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self._win_ratio_w, self._win_ratio_h = win_ratio_w, win_ratio_h

        self._colors.handle_resize(self._win_ratio_w, self._win_ratio_h)
        for option in self._options:
            option.handle_resize(self._win_ratio_w, self._win_ratio_h)

    def print_layers(self, name: str, counter: int) -> LayerSequence:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns a sequence to add in the main layer sequence
        """

        layer_sequence: LayerSequence = [(name, -1, counter)]
        layer_sequence += self._colors.print_layers('colors', counter + 1)
        layer_sequence += [('options', -1, counter + 1)]
        for option in self._options:
            layer_sequence += option.print_layers('option', counter + 2)

        return layer_sequence

    def add(self, color: Optional[ColorType]) -> None:
        """
        adds a color to the palette or edits one
        takes color (if it's None it sets the changing_color flag off)
        """

        if not color:
            self._changing_color = False

            return

        '''
        insert method uses window size ratio to adjust the init_pos even when inserting
        at a different window size
        '''

        if self._changing_color:
            self.values[self._drop_down_i] = color
            self._colors.insert(
                self._drop_down_i, get_color_info(color), self._win_ratio_w, self._win_ratio_h
            )

            self._changing_color = False
        elif color not in self.values:
            self.values.append(color)
            self._colors.insert(-1, get_color_info(color), self._win_ratio_w, self._win_ratio_h)
        self._colors.tick_on(self.values.index(color))

    def load_path(self, pixels: NDArray[np.uint8]) -> None:
        """
        makes a palette out of all unique colors in a pixels array
        takes pixels
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
            self, hover_obj: Any, mouse_info: MouseInfo, keys: list[int], ctrl: int
    ) -> tuple[ColorType, Optional[ColorType]]:
        """
        allows to select a color and make a drop-down menu appear on right click
        takes hovered object (can be None), mouse info, keys anf ctrl
        returns the selected color and the color to edit (can be None)
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
        remove method uses window size ratio to adjust the init_pos
        even when removing at a different window size
        '''

        clicked_option: bool = False
        if ctrl:
            if pg.K_e in keys:
                self._drop_down_i = self._colors.clicked_i
                self._changing_color = True

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

        if self._view_drop_down:
            if self._options[0].upt(hover_obj, mouse_info):
                self._changing_color = True

                clicked_option = True
            if self._options[1].upt(hover_obj, mouse_info):
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
            self._colors.upt(hover_obj, mouse_info, keys)

        color: ColorType = self.values[self._colors.clicked_i]
        color_to_edit: Optional[ColorType] = None

        if self._changing_color:
            color_to_edit = self.values[self._drop_down_i]
            for check_box in self._colors.check_boxes:
                check_box._hovering = False

        return color, color_to_edit
