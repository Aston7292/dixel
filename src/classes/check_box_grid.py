"""
classes to create a checkbox or a grid of connected checkboxes
"""

import pygame as pg
from typing import Tuple, List

from src.classes.clickable import Clickable
from src.classes.text import Text
from src.utils import Point, RectPos, MouseInfo, add_border, BlitSequence
from src.const import WHITE


class LockedCheckBox(Clickable):
    """
    class to create a checkbox, when hovered changes image and displays text and
    when clicked it will always display the hovering image, cannot be ticked off
    """

    __slots__ = (
        'clicked', '_text', '_text_surf'
    )

    def __init__(
            self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType], text: str
        ) -> None:
        """
        creates surfaces and rects
        takes position, two images and text
        """

        super().__init__(pos, imgs)

        self.clicked: bool = False

        self._text: Text = Text(RectPos(0, 0, 'topleft'), text, 16)
        self._text_surf: pg.SurfaceType = pg.Surface(
            (int(self._text.rect.w), int(self._text.rect.h))
        )
        self._text_surf.fblits(self._text.blit())

    def blit(self) -> BlitSequence:
        """
        returns two sequences to add in the main blit sequence,
        """

        img_i: int = 1 if self.clicked else self.img_i

        sequence: BlitSequence = [(self._imgs[img_i], self.rect.topleft)]
        if self.hovering:
            mouse_pos: Point = Point(*pg.mouse.get_pos())
            sequence += [(self._text_surf, (mouse_pos.x + 10, mouse_pos.y))]

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        super().handle_resize(win_ratio_w, win_ratio_h)

        self._text.handle_resize(win_ratio_w, win_ratio_h)
        self._text_surf = pg.Surface((int(self._text.rect.w), int(self._text.rect.h)))
        self._text_surf.fblits(self._text.blit())

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
        '_pos', '_x', '_y', '_cols', '_x_increment', '_y_increment', 'check_boxes',
    )

    def __init__(
            self, pos: RectPos, info: List[Tuple[pg.SurfaceType, str]], cols: int,
            inverted_axes: Tuple[bool, bool]
    ) -> None:
        """
        creates all the checkboxes
        takes position, check boxes info, number of columns and the inverted axes
        """

        self._pos: RectPos = pos
        self._x: float
        self._y: float
        self._x, self._y = self._pos.xy

        self._cols: int = cols

        self._x_increment: int = info[0][0].get_width() + 10
        if inverted_axes[0]:
            self._x_increment *= -1
        self._y_increment: int = info[0][0].get_height() + 10
        if inverted_axes[1]:
            self._y_increment *= -1

        self.check_boxes: List[LockedCheckBox] = []
        for i, element in enumerate(info):
            img_on: pg.SurfaceType = add_border(element[0], WHITE)
            self.check_boxes.append(LockedCheckBox(
                    RectPos(self._x, self._y, self._pos.coord), (element[0], img_on), element[1]
            ))

            self._x += self._x_increment
            if (i + 1) % self._cols == 0:
                self._x = self._pos.x
                self._y += self._y_increment

        self.check_boxes[0].clicked = True

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = []
        add_sequence: BlitSequence = []
        for check_box in self.check_boxes:
            info: BlitSequence = check_box.blit()

            sequence.append(info[0])
            if len(info) == 2:
                add_sequence.append(info[1])  # text doesn't overlap other checkboxes

        return sequence + add_sequence

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

    def add(self, info: Tuple[pg.SurfaceType, str]) -> None:
        """
        adds a check box at the end of the grid
        takes check box info
        """

        img_on: pg.SurfaceType = add_border(info[0], WHITE)
        self.check_boxes.append(LockedCheckBox(
                RectPos(self._x, self._y, self._pos.coord), (info[0], img_on), info[1]
        ))

        self._x += self._x_increment
        if len(self.check_boxes) % self._cols == 0:
            self._x = self._pos.x
            self._y += self._y_increment

    def upt(self, mouse_info: MouseInfo) -> int:
        """
        makes the grid interactable and allows only one check_box to be pressed at a time
        takes mouse info
        returns the index of the check box that was ticked on, if none was ticked on it returns -1
        """

        index: int = -1
        for i, check_box in enumerate(self.check_boxes):
            if check_box.upt(mouse_info):
                index = i

        if index != -1:
            self.set(index)

        return index
