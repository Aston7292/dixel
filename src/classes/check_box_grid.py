"""
classes to create a locked checkbox or a grid of connected checkboxes
"""

import pygame as pg

from src.classes.clickable import Clickable
from src.utils import RectPos, Size, MouseInfo, add_border, LayeredBlitSequence, LayersInfo
from src.const import WHITE, BG_LAYER


class LockedCheckBox(Clickable):
    """
    class to create a checkbox, when hovered changes image and displays text,
    when ticked on it will always display the hovering image, cannot be ticked off
    """

    __slots__ = (
        'ticked_on',
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType], hover_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        creates the checkbox and text
        takes position, two images, hover text and base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hover_text, base_layer)

        self.ticked_on: bool = False

    def blit(self) -> LayeredBlitSequence:
        """
        returns two sequences to add in the main blit sequence,
        """

        img_i: int = 1 if self.ticked_on else int(self.hovering)
        sequence: LayeredBlitSequence = self._base_blit(img_i)

        return sequence

    def set_info(self, imgs: tuple[pg.SurfaceType, pg.SurfaceType], text: str) -> None:
        """
        sets images and text
        takes images and text
        """

        self._imgs = imgs
        if self._hover_text:
            self._hover_text.set_text(text)
            self._hover_text_surfaces = tuple(
                pg.Surface((int(rect.w), int(rect.h))) for rect in self._hover_text.rects
            )

            for target, (surf, _, _) in zip(self._hover_text_surfaces, self._hover_text.blit()):
                target.blit(surf)

    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        updates the checkbox image if the mouse is hovering it and ticks it on if clicked
        takes mouse info
        returns True if the checkbox was ticked on
        """

        if not self.rect.collidepoint(mouse_info.xy):
            if self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.hovering = False

            return False

        if not self.hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self.hovering = True

        if mouse_info.released[0]:
            self.ticked_on = True

            return True

        return False


class CheckBoxGrid:
    """
    class to create a grid of checkboxes with n rows (images must be of the same size)
    """

    __slots__ = (
        'init_pos', 'current_x', 'current_y', '_cols', '_increment', '_inverted_axes',
        'check_boxes', 'clicked_i'
    )

    def __init__(
            self, pos: RectPos, info: list[tuple[pg.SurfaceType, str]], cols: int,
            inverted_axes: tuple[bool, bool], base_layer: int = BG_LAYER
    ) -> None:
        """
        creates all the checkboxes
        takes position, check boxes info, number of columns, the inverted axes
        and base layer (default = BG_LAYER)
        """

        self.init_pos: RectPos = pos
        self.current_x: float = self.init_pos.x
        self.current_y: float = self.init_pos.y

        self._cols: int = cols

        self._increment: Size = Size(info[0][0].get_width() + 10, info[0][0].get_height() + 10)
        self._inverted_axes: tuple[bool, bool] = inverted_axes
        if self._inverted_axes[0]:
            self._increment.w *= -1
        if self._inverted_axes[1]:
            self._increment.h *= -1

        self.check_boxes: list[LockedCheckBox] = []
        for i, element in enumerate(info):
            self.check_boxes.append(LockedCheckBox(
                RectPos(self.current_x, self.current_y, self.init_pos.coord),
                (element[0], add_border(element[0], WHITE)), element[1], base_layer
            ))

            self.current_x += self._increment.w
            if (i + 1) % self._cols == 0:
                self.current_x = self.init_pos.x
                self.current_y += self._increment.h
        self.clicked_i: int = 0

        self.tick_on(self.clicked_i)

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = []
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

    def leave(self) -> None:
        """
        clears everything that needs to be cleared when the object is leaved
        """

        for check_box in self.check_boxes:
            check_box.leave()

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = [(name, -1, counter)]
        for check_box in self.check_boxes:
            layers_info += check_box.print_layers('checkbox', counter + 1)

        return layers_info

    def tick_on(self, index: int) -> None:
        """
        ticks on a specific checkbox
        """

        if self.clicked_i < len(self.check_boxes):
            self.check_boxes[self.clicked_i].ticked_on = False
        self.clicked_i = index
        self.check_boxes[self.clicked_i].ticked_on = True

    def insert(
            self, insert_i: int, info: tuple[pg.SurfaceType, str],
            win_ratio_w: float, win_ratio_h: float
    ) -> None:
        """
        inserts a checkbox at an index
        takes insert index (appends if -1), check box info, window size ratio
        """

        if insert_i != -1:
            self.check_boxes[insert_i].set_info((info[0], add_border(info[0], WHITE)), info[1])
            self.check_boxes[insert_i].handle_resize(win_ratio_w, win_ratio_h)
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
            self, drop_down_i: int, fallback: tuple[pg.SurfaceType, str],
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
            self.tick_on(self.clicked_i - 1)
        elif self.clicked_i == drop_down_i:
            self.clicked_i = min(self.clicked_i, len(self.check_boxes) - 1)
            self.check_boxes[self.clicked_i].ticked_on = True

    def upt(self, mouse_info: MouseInfo, keys: list[int]) -> int:
        """
        makes the grid interactable and allows only one check_box to be pressed at a time
        takes mouse info and keys
        returns the index of the active checkbox
        """

        rects: tuple[pg.FRect, ...] = tuple(check_box.rect for check_box in self.check_boxes)
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
                self.tick_on(clicked_i)

        for i, check_box in enumerate(self.check_boxes):
            if check_box.upt(mouse_info):
                self.tick_on(i)

        return self.clicked_i
