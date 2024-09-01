"""
classes to create a locked checkbox or a grid of connected checkboxes
"""

import pygame as pg
from typing import Tuple, List

from src.classes.clickable import Clickable
from src.classes.text import Text
from src.utils import Point, RectPos, Size, MouseInfo, add_border, BlitSequence
from src.const import WHITE


class LockedCheckBox(Clickable):
    """
    class to create a checkbox, when hovered changes image and displays text,
    when ticked on it will always display the hovering image, cannot be ticked off
    """

    __slots__ = (
        'ticked_on', '_text', '_text_surf'
    )

    def __init__(
            self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType], text: str
    ) -> None:
        """
        creates the checkbox and text
        takes position, two images and text
        """

        super().__init__(pos, imgs)

        self.ticked_on: bool = False

        self._text: Text = Text(RectPos(0.0, 0.0, 'topleft'), text, 12)
        self._text_surf: pg.SurfaceType = pg.Surface(
            (int(self._text.rect.w), int(self._text.rect.h))
        )
        self._text_surf.fblits(self._text.blit())

    def blit(self) -> BlitSequence:
        """
        returns two sequences to add in the main blit sequence,
        """

        img_i: int = 1 if self.ticked_on else self.img_i

        sequence: BlitSequence = [(self._imgs[img_i], self.rect.topleft)]
        if self.hovering:
            mouse_pos: Point = Point(*pg.mouse.get_pos())
            sequence += [(self._text_surf, (mouse_pos.x + 15, mouse_pos.y))]

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        super().handle_resize(win_ratio_w, win_ratio_h)

        self._text.handle_resize(win_ratio_w, win_ratio_h)
        self._text_surf = pg.Surface((int(self._text.rect.w), int(self._text.rect.h)))
        self._text_surf.fblits(self._text.blit())

    def modify_info(self, imgs: Tuple[pg.SurfaceType, pg.SurfaceType], text: str) -> None:
        """
        modifies images and text
        takes images and text
        """

        self._imgs = imgs
        self._text.modify_text(text)
        self._text_surf = pg.Surface(
            (int(self._text.rect.w), int(self._text.rect.h))
        )
        self._text_surf.fblits(self._text.blit())

    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        updates the checkbox image if the mouse is hovering it and ticks it on if clicked
        takes mouse info
        returns True if the checkbox was ticked on
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
            self.ticked_on = True

            return True

        return False


class CheckBoxGrid:
    """
    creates a grid of checkboxes with n rows (images must be of the same size)
    """

    __slots__ = (
        'init_pos', 'current_x', 'current_y', '_cols', '_increment', '_inverted_axes',
        'check_boxes', 'clicked_i'
    )

    def __init__(
            self, pos: RectPos, info: List[Tuple[pg.SurfaceType, str]], cols: int,
            inverted_axes: Tuple[bool, bool]
    ) -> None:
        """
        creates all the checkboxes
        takes position, check boxes info, number of columns and the inverted axes
        """

        self.init_pos: RectPos = pos
        self.current_x: float = self.init_pos.x
        self.current_y: float = self.init_pos.y

        self._cols: int = cols

        self._increment: Size = Size(info[0][0].get_width() + 10, info[0][0].get_height() + 10)
        self._inverted_axes: Tuple[bool, bool] = inverted_axes
        if self._inverted_axes[0]:
            self._increment.w *= -1
        if self._inverted_axes[1]:
            self._increment.h *= -1

        self.check_boxes: List[LockedCheckBox] = []
        for i, element in enumerate(info):
            self.check_boxes.append(LockedCheckBox(
                RectPos(self.current_x, self.current_y, self.init_pos.coord),
                (element[0], add_border(element[0], WHITE)), element[1]
            ))

            self.current_x += self._increment.w
            if (i + 1) % self._cols == 0:
                self.current_x = self.init_pos.x
                self.current_y += self._increment.h
        self.clicked_i: int = 0

        self.set(self.clicked_i)

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

        if self.clicked_i < len(self.check_boxes):
            self.check_boxes[self.clicked_i].ticked_on = False
        self.clicked_i = index
        self.check_boxes[self.clicked_i].ticked_on = True

    def insert(
            self, info: Tuple[pg.SurfaceType, str], win_ratio_w: float, win_ratio_h: float,
            i: int = -1
    ) -> None:
        """
        inserts a checkbox at an index
        takes check box info, window size ratio and insert index appends if -1 (default = -1)
        """

        if i != -1:
            self.check_boxes[i].modify_info((info[0], add_border(info[0], WHITE)), info[1])
            self.check_boxes[i].handle_resize(win_ratio_w, win_ratio_h)
        else:
            check_box: LockedCheckBox = LockedCheckBox(
                RectPos(self.current_x, self.current_y, self.init_pos.coord),
                (info[0], add_border(info[0], WHITE)), info[1]
            )
            check_box.handle_resize(win_ratio_w, win_ratio_h)
            self.check_boxes.append(check_box)

            self.current_x += self._increment.w
            if len(self.check_boxes) % self._cols == 0:
                self.current_x = self.init_pos.x
                self.current_y += self._increment.h

    def remove(
            self, drop_down_i: int, fallback: Tuple[pg.SurfaceType, str],
            win_ratio_w: float, win_ratio_h: float
    ) -> None:
        """
        removes a checkbox from the grid
        takes drop-down index, fallback info and window size ratio
        """

        check_box: LockedCheckBox = self.check_boxes.pop(drop_down_i)
        self.current_x = getattr(check_box.rect, self.init_pos.coord)[0] / win_ratio_w
        self.current_y = getattr(check_box.rect, self.init_pos.coord)[1] / win_ratio_h
        for i in range(drop_down_i, len(self.check_boxes)):
            self.check_boxes[i].init_pos.x = self.current_x
            self.check_boxes[i].init_pos.y = self.current_y
            setattr(
                self.check_boxes[i].rect, self.init_pos.coord,
                (self.current_x * win_ratio_w, self.current_y * win_ratio_h)
            )

            self.current_x += self._increment.w
            if (i + 1) % self._cols == 0:
                self.current_x = self.init_pos.x
                self.current_y += self._increment.h

        if not self.check_boxes:
            check_box = LockedCheckBox(
                RectPos(self.current_x, self.current_y, self.init_pos.coord),
                (fallback[0], add_border(fallback[0], WHITE)), fallback[1]
            )
            check_box.handle_resize(win_ratio_w, win_ratio_h)
            self.check_boxes = [check_box]

            self.current_x, self.current_y = self.init_pos.x + self._increment.w, self.init_pos.y

        if self.clicked_i > drop_down_i:
            self.set(self.clicked_i - 1)
        elif self.clicked_i == drop_down_i:
            self.clicked_i = min(self.clicked_i, len(self.check_boxes) - 1)
            self.check_boxes[self.clicked_i].ticked_on = True

    def upt(self, mouse_info: MouseInfo, keys: List[int]) -> int:
        """
        makes the grid interactable and allows only one check_box to be pressed at a time
        takes mouse info and keys
        returns the index of the active checkbox
        """

        rects: Tuple[pg.FRect, ...] = tuple(check_box.rect for check_box in self.check_boxes)
        left: float = min(rect.left for rect in rects)
        right: float = max(rect.right for rect in rects)
        top: float = min(rect.top for rect in rects)
        bottom: float = max(rect.bottom for rect in rects)

        if (left <= mouse_info.x <= right and top <= mouse_info.y <= bottom) and keys:
            clicked_i: int = self.clicked_i

            sub_1: int
            add_1: int
            sub_cols: int
            add_cols: int
            if not self._inverted_axes[0]:
                sub_1, add_1 = pg.K_LEFT, pg.K_RIGHT
            else:
                sub_1, add_1 = pg.K_RIGHT, pg.K_LEFT
            if not self._inverted_axes[1]:
                sub_cols, add_cols = pg.K_UP, pg.K_DOWN
            else:
                sub_cols, add_cols = pg.K_DOWN, pg.K_UP

            if sub_1 in keys:
                clicked_i = max(clicked_i - 1, 0)
            if add_1 in keys:
                clicked_i = min(clicked_i + 1, len(self.check_boxes) - 1)
            if sub_cols in keys:
                if clicked_i - self._cols >= 0:
                    clicked_i -= self._cols
            if add_cols in keys:
                if clicked_i + self._cols <= len(self.check_boxes) - 1:
                    clicked_i += self._cols

            if self.clicked_i != clicked_i:
                self.set(clicked_i)

        for i, check_box in enumerate(self.check_boxes):
            if check_box.upt(mouse_info):
                self.set(i)

        return self.clicked_i
