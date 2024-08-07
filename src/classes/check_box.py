"""
class to create a checkbox or a grid of connected checkboxes
"""

import pygame as pg
from typing import Tuple, List

from src.utils import Point, RectPos, Size, MouseInfo
from src.const import BlitSequence


class CheckBox:
    """
    class to create a checkbox, when hovered changes image and
    when clicked it will always display the hovering image
    """

    __slots__ = (
        '_init_pos', '_imgs', '_init_size', 'rect', '_img_i', '_hovering', 'clicked'
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, ...]) -> None:
        """
        creates button surface, rect and text object
        takes position and two images
        """

        self._init_pos: RectPos = pos

        self._imgs: Tuple[pg.SurfaceType, ...] = imgs
        self.rect: pg.FRect = self._imgs[0].get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self._img_i: int = 0
        self._hovering: bool = False
        self.clicked: bool = False

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        img_i: int = 1 if self.clicked else self._img_i

        return [(self._imgs[img_i], self.rect.topleft)]

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        size: Tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._imgs = tuple(pg.transform.scale(img, size) for img in self._imgs)
        self.rect = self._imgs[0].get_frect(**{self._init_pos.pos: pos})

    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        updates the checkbox image if the mouse is hovering it and toggles it on if clicked
        takes mouse info
        returns true if the checkbox was toggled on
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

        self._check_boxes: List[CheckBox] = []

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

            self._check_boxes.append(CheckBox(RectPos(x, y, 'topleft'), img))
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
        if a checkbox was toggled on it returns its index else -1
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
