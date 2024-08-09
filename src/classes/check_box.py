"""
classes to create a checkbox or a grid of connected checkboxes
"""

import pygame as pg
from typing import Tuple, List

from src.classes.clickable import Clickable
from src.utils import Point, RectPos, MouseInfo
from src.const import BlitSequence


class LockedCheckBox(Clickable):
    """
    class to create a checkbox, when hovered changes image and
    when clicked it will always display the hovering image, cannot be ticked off
    """

    __slots__ = (
        'clicked',
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, ...]) -> None:
        """
        creates surfaces and rect
        takes position and two images
        """

        super().__init__(pos, imgs)

        self.clicked: bool = False

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        img_i: int = 1 if self.clicked else self._img_i

        return [(self._imgs[img_i], self.rect.topleft)]

    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        updates the checkbox image if the mouse is hovering it and ticks it on if clicked
        takes mouse info
        returns True if the checkbox was ticked on
        """

        if not self.rect.collidepoint(mouse_info.xy):
            if self._hovering:
                self._img_i = 0
                self._hovering = False
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

            return False

        if not self._hovering:
            self._img_i = 1
            self._hovering = True
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)

        if mouse_info.released[0]:
            self.clicked = True

            return True

        return False


class CheckBoxGrid:
    """
    creates a grid of checkboxes with n rows
    """

    __slots__ = (
        '_check_boxes',
    )

    def __init__(
            self, pos: Point, all_imgs: Tuple[Tuple[pg.SurfaceType, ...], ...], rows: int
    ) -> None:
        """
        creates all the checkboxes
        takes position, all the images and the number of rows
        """

        x: int
        y: int
        w: int
        h: int
        x, y = pos.xy
        w, h = all_imgs[0][0].get_size()

        self._check_boxes: List[LockedCheckBox] = []

        extras: int = len(all_imgs) % rows
        row_len: int = len(all_imgs) // rows + (1 if extras else 0)

        index: int = 0
        for img in all_imgs:
            if index % row_len != 0:
                x += w + 10
            elif index:
                index = 0
                x = pos.x
                y += h + 10

                extras -= 1
                if not extras:
                    row_len -= 1
            index += 1

            self._check_boxes.append(LockedCheckBox(RectPos(x, y, 'topleft'), img))
        self._check_boxes[0].clicked = True

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = []
        for check_box in self._check_boxes:
            sequence += check_box.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        for check_box in self._check_boxes:
            check_box.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo) -> int:
        """
        makes the grid interactable and allows only one check_box to be pressed at a time
        takes mouse info
        if a checkbox was ticked on it returns its index else -1
        """

        index: int = -1
        for i, check_box in enumerate(self._check_boxes):
            if check_box.upt(mouse_info):
                index = i

        if index != -1:
            for i, check_box in enumerate(self._check_boxes):
                if i != index:
                    check_box.clicked = False

        return index
