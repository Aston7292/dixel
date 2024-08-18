"""
classes to create a checkbox or a grid of connected checkboxes
"""

import pygame as pg
from typing import Tuple, List

from src.classes.clickable import Clickable
from src.classes.text import Text
from src.utils import Point, RectPos, MouseInfo
from src.const import BlitSequence


class LockedCheckBox(Clickable):
    """
    class to create a checkbox, when hovered changes image and displays text and
    when clicked it will always display the hovering image, cannot be ticked off
    """

    __slots__ = (
        'clicked', '_text_surf'
    )

    def __init__(
            self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType], text: str
        ) -> None:
        """
        creates surfaces and rect
        takes position, two images and text
        """

        super().__init__(pos, imgs)

        self.clicked: bool = False

        text_obj: Text = Text(RectPos(0, 0, 'topleft'), text, 16)
        self._text_surf: pg.SurfaceType = pg.Surface((int(text_obj.rect.w), int(text_obj.rect.h)))
        self._text_surf.fblits(text_obj.blit())

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        img_i: int = 1 if self.clicked else self.img_i

        sequence: BlitSequence = [(self._imgs[img_i], self.rect.topleft)]
        if self.hovering:
            mouse_pos: Point = Point(*pg.mouse.get_pos())
            sequence += [(self._text_surf, (mouse_pos.x + 10, mouse_pos.y))]

        return sequence

    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        updates the checkbox image if the mouse is hovering it and ticks it on if clicked
        takes mouse info
        returns True if the checkbox was clicked
        """

        if not self.rect.collidepoint(mouse_info.xy):
            if self.hovering:
                self.img_i = 0
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.hovering = False

            return False

        if not self.hovering:
            self.img_i = 1
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self.hovering = True

        if mouse_info.released[0]:
            self.clicked = True

            return True

        return False


class CheckBoxGrid:
    """
    creates a grid of checkboxes with n rows
    """

    __slots__ = (
        'check_boxes',
    )

    def __init__(
            self, pos: Point, info: Tuple[Tuple[pg.SurfaceType, pg.SurfaceType, str], ...],
            rows: int
    ) -> None:
        """
        creates all the checkboxes
        takes position, all the check boxes info and the number of rows
        """

        x: int
        y: int
        w: int
        h: int
        x, y = pos.xy
        w, h = info[0][0].get_size()

        self.check_boxes: List[LockedCheckBox] = []

        extras: int = len(info) % rows
        row_len: int = len(info) // rows + (1 if extras else 0)

        index: int = 0
        for element in info:
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

            self.check_boxes.append(
                LockedCheckBox(RectPos(x, y, 'topleft'), (element[0], element[1]), element[2])
            )
        self.check_boxes[0].clicked = True

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = []
        for check_box in self.check_boxes:
            sequence += check_box.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        for check_box in self.check_boxes:
            check_box.handle_resize(win_ratio_w, win_ratio_h)

    def set(self, index: int) -> None:
        """
        ticks on a specific checkbox
        """

        for i, check_box in enumerate(self.check_boxes):
            check_box.clicked = i == index

    def upt(self, mouse_info: MouseInfo) -> int:
        """
        makes the grid interactable and allows only one check_box to be pressed at a time
        takes mouse info
        if a checkbox was ticked on it returns its index else -1
        """

        index: int = -1
        for i, check_box in enumerate(self.check_boxes):
            if check_box.upt(mouse_info):
                index = i

        if index != -1:
            self.set(index)

        return index
