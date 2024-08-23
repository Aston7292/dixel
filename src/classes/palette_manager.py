"""
class to manage color palettes
"""

import pygame as pg
from PIL import Image
from typing import Tuple, List, Set, Final, Optional, Any

from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import Button
from src.utils import RectPos, MouseInfo, add_border, ColorType, BlitSequence
from src.const import EMPTY_1

OPTIONS: Final[Tuple[str, ...]] = ('modify', 'delete')


def get_color_info(color: ColorType) -> Tuple[pg.SurfaceType, str]:
    """
    creates a surface and a text for a color
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
    class to manage color palettes
    """

    __slots__ = (
        'values', '_colors', '_options', '_view_menu', '_win_ratio_w', '_win_ratio_h'
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType]) -> None:
        """
        creates a grid of colors and a menu to modify it
        takes position
        """

        self.values: List[ColorType] = [(0, 0, 0)]
        self._colors = CheckBoxGrid(pos, [get_color_info(self.values[0])], 5, (True, True))

        self._options: Tuple[Button, ...] = tuple(
            Button(RectPos(0, 0, 'topleft'), imgs, option, 20) for option in OPTIONS
        )
        self._view_menu: bool = False

        self._win_ratio_w: float = 1
        self._win_ratio_h: float = 1

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = self._colors.blit()
        if self._view_menu:
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

    def add(self, color: ColorType) -> ColorType:
        """
        adds a color to the palette
        takes color
        returns color
        """

        if color not in self.values:
            self.values.append(color)
            self._colors.add(get_color_info(color))
        self._colors.set(self.values.index(color))

        return color

    def load_path(self, file_path: str) -> None:
        """
        makes a palette out of every character in an image
        takes path
        """

        if not file_path:
            self.values = [(0, 0, 0)]
        else:
            img: Image.Image = Image.open(file_path).convert('RGB')

            colors: Set[ColorType] = set()
            for y in range(img.height):
                for x in range(img.width):
                    color: Any = img.getpixel((x, y))
                    if isinstance(color, tuple):
                        colors.add(color)
            self.values = list(colors)

        self._colors.x, self._colors.y = self._colors.pos.xy
        self._colors.check_boxes = []
        for value in self.values:
            self._colors.add(get_color_info(value))

        self._colors.check_boxes[0].ticked = True

    def upt(self, mouse_info: MouseInfo, ctrl: int) -> Optional[ColorType]:
        """
        makes the object interactable
        takes mouse info, keys anf ctrl
        returns the selected color
        """

        index: int = self._colors.upt(mouse_info)

        if mouse_info.released[2]:
            for i, check_box in enumerate(self._colors.check_boxes):
                if check_box.rect.collidepoint(mouse_info.xy):
                    self._view_menu = not self._view_menu
                    if self._view_menu:
                        y: float = mouse_info.y + 10
                        for option in self._options:
                            option.move_rect(
                                mouse_info.x + 10, y, self._win_ratio_w, self._win_ratio_h
                            )
                            y += option.rect.h

                        pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                        self._colors.check_boxes[i].img_i = 0
                        self._colors.check_boxes[i].hovering = False

                    break

        if self._view_menu:
            for option in self._options:
                option.upt(mouse_info)

        if mouse_info.released[0] or ctrl:
            self._view_menu = False

        return self.values[index] if index != -1 else None
