"""
Class to manage color palettes, includes a drop-down menu
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Final, Optional, Any

from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import Button
from src.utils import RectPos, ObjInfo, MouseInfo, add_border
from src.type_utils import ColorType, LayerSequence
from src.consts import BLACK, LIGHT_GRAY, SPECIAL_LAYER

OPTIONS: Final[tuple[tuple[str, str], ...]] = (
    ('edit', '(CTRL+E)'),
    ('delete', '(CTRL+DEL)')
)


def get_color_info(color: ColorType) -> tuple[pg.Surface, str]:
    """
    Creates the surface and text for a color
    Args:
        color
    Returns:
        surface, text
    """

    surf: pg.Surface = pg.Surface((32, 32))
    surf.fill(color)
    surf = add_border(surf, LIGHT_GRAY)

    rgb_text: str = f'({color[0]}, {color[1]}, {color[2]})'
    hex_text: str = f'(#{''.join(f'{channel:02x}' for channel in color)})'
    text: str = f'{rgb_text}\n{hex_text}'

    return surf, text


class PaletteManager:
    """
    Class to manage color palettes, includes a drop-down menu
    """

    __slots__ = (
        'values', '_colors', '_options', '_drop_down_i', '_view_drop_down', '_changing_color',
        '_win_ratio_w', '_win_ratio_h', 'objs_info', '_drop_down_info_start', '_drop_down_info_end'
    )

    def __init__(self, pos: RectPos, imgs: tuple[pg.Surface, pg.Surface]) -> None:
        """
        Creates the grid of colors and the drop-down menu to modify it
        Args:
            position and drop-down menu image pair
        """

        self.values: list[ColorType] = [BLACK]
        self._colors: CheckBoxGrid = CheckBoxGrid(
            pos, (get_color_info(self.values[0]),), 5, (True, True)
        )

        self._options: tuple[Button, ...] = tuple(
            Button(RectPos(0, 0.0, 'topleft'), imgs, *option, SPECIAL_LAYER, 20)
            for option in OPTIONS
        )

        self._drop_down_i: int = 0
        self._view_drop_down: bool = False
        self._changing_color: bool = False

        self._win_ratio_w: float = 1.0
        self._win_ratio_h: float = 1.0

        self.objs_info: list[ObjInfo] = [ObjInfo('colors', self._colors)]
        self._drop_down_info_start: int = len(self.objs_info)
        self.objs_info.extend(
            ObjInfo(OPTIONS[i][0], option) for i, option in enumerate(self._options)
        )
        self._drop_down_info_end: int = len(self.objs_info)

        for i in range(self._drop_down_info_start, self._drop_down_info_end):
            self.objs_info[i].set_active(self._view_drop_down)

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._drop_down_i = 0
        self._view_drop_down = False

        for i in range(self._drop_down_info_start, self._drop_down_info_end):
            self.objs_info[i].set_active(self._view_drop_down)

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
        Args:
            window width ratio, window height ratio
        """

        self._win_ratio_w, self._win_ratio_h = win_ratio_w, win_ratio_h

    def post_resize(self) -> None:
        """
        Handles post resizing behavior
        """

        if self._view_drop_down:
            current_y: float = self._options[0].rect.y
            for option in self._options:
                # More precise
                option.move_rect(option.rect.x, current_y, self._win_ratio_w, self._win_ratio_h)
                current_y += option.rect.h

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, -1, depth_counter)]

    def add(self, color: Optional[ColorType]) -> None:
        """
        Adds a color to the palette or edits one based on the changing_color boolean
        Args:
            color (if it's None it sets changing_color to False)
        """

        if not color:
            self._changing_color = False

            return

        '''
        The insert method uses the window size ratio to adjust the initial position
        even at different window sizes
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

    def load_from_arr(self, pixels: NDArray[np.uint8]) -> None:
        """
        Creates a palette out of every unique colors in a pixels array
        Args:
            pixels
        """

        pixels_2d: NDArray[np.uint8] = pixels.reshape(-1, 4)[:, :3]
        colors: NDArray[np.uint8] = np.unique(pixels_2d, axis=0)
        self.values = [tuple(int(value) for value in color) for color in colors]

        check_boxes_info: tuple[tuple[pg.Surface, str], ...] = tuple(
            get_color_info(value) for value in self.values
        )
        self._colors.change_grid(check_boxes_info, self._win_ratio_w, self._win_ratio_h)

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], ctrl: int
    ) -> tuple[ColorType, Optional[ColorType]]:
        """
        Allows selecting a color and making a drop-down menu appear on right click
        Args:
            hovered object (can be None), mouse info, keys, ctrl
        Returns:
            selected color, color to edit (can be None)
        """

        prev_drop_down_state: bool = self._view_drop_down

        if mouse_info.released[2]:
            for i, check_box in enumerate(self._colors.checkboxes):
                if check_box.rect.collidepoint(mouse_info.xy):
                    self._view_drop_down = (
                        not self._view_drop_down if self._drop_down_i == i else True
                    )

                    if self._view_drop_down:
                        self._drop_down_i = i
                        current_y: float = mouse_info.y + 5.0
                        for option in self._options:
                            # Also changes the initial position
                            option.move_rect(
                                mouse_info.x + 5.0, current_y, self._win_ratio_w, self._win_ratio_h
                            )
                            current_y += option.rect.h
                    break
            else:
                self._view_drop_down = False

        '''
        The remove method uses the window size ratio to adjust the initial position
        even at different window sizes
        '''

        if ctrl:
            if pg.K_e in keys:
                self._drop_down_i = self._colors.clicked_i
                self._view_drop_down = False
                self._changing_color = True
            if pg.K_DELETE in keys:
                self._drop_down_i = self._colors.clicked_i
                self._view_drop_down = False

                self.values.pop(self._drop_down_i)
                if not self.values:
                    self.values = [BLACK]
                self._colors.remove(
                    self._drop_down_i, get_color_info(self.values[0]),
                    self._win_ratio_w, self._win_ratio_h
                )

        if self._view_drop_down:
            if self._options[0].upt(hover_obj, mouse_info):
                self._view_drop_down = False
                self._changing_color = True
            if self._options[1].upt(hover_obj, mouse_info):
                self._view_drop_down = False

                self.values.pop(self._drop_down_i)
                if not self.values:
                    self.values = [BLACK]
                self._colors.remove(
                    self._drop_down_i, get_color_info(self.values[0]),
                    self._win_ratio_w, self._win_ratio_h
                )

        if prev_drop_down_state == self._view_drop_down:
            self._colors.upt(hover_obj, mouse_info, keys)
        else:
            drop_down_objs_info: list[ObjInfo] = self.objs_info[
                self._drop_down_info_start:self._drop_down_info_end
            ]
            for info in drop_down_objs_info:
                info.set_active(self._view_drop_down)

            if not self._view_drop_down:
                drop_down_objs: list[Any] = [info.obj for info in drop_down_objs_info]
                while drop_down_objs:
                    obj: Any = drop_down_objs.pop()

                    if hasattr(obj, 'leave'):
                        obj.leave()
                    if hasattr(obj, 'objs_info'):
                        drop_down_objs.extend(obj.objs_info)

        color_to_edit: Optional[ColorType] = None
        if self._changing_color:
            color_to_edit = self.values[self._drop_down_i]

        return self.values[self._colors.clicked_i], color_to_edit
