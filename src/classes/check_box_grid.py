"""
Classes to create a locked checkbox or a grid of connected checkboxes
"""

import pygame as pg
from typing import Any

from src.classes.clickable import Clickable
from src.utils import RectPos, Size, ObjInfo, MouseInfo, add_border
from src.type_utils import LayeredBlitSequence, LayerSequence
from src.consts import WHITE, BG_LAYER


class LockedCheckBox(Clickable):
    """
    Class to create a checkbox, when hovered changes image and displays text,
    when ticked on it will display the hovering image, cannot be ticked off
    """

    __slots__ = (
        'ticked_on',
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.Surface, pg.Surface], hover_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox
        Args:
            position, two images, hover text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hover_text, base_layer)

        self.ticked_on: bool = False

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        img_i: int = 1 if self.ticked_on else int(self._hovering)

        return self._base_blit(img_i)

    def set_info(self, imgs: tuple[pg.Surface, pg.Surface], text: str) -> None:
        """
        Sets images and text
        Args:
            two images, text
        """

        self._imgs = imgs
        if self._hover_text:
            self._hover_text.set_text(text)
            self._hover_text_surfaces = tuple(
                pg.Surface((int(rect.w), int(rect.h))) for rect in self._hover_text.rects
            )

            for target, (surf, _, _) in zip(self._hover_text_surfaces, self._hover_text.blit()):
                target.blit(surf)

    def upt(self, hover_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and ticks it on if clicked
        Args:
            hovered object (can be None), mouse info
        Returns:
            True if the checkbox was ticked on else False
        """

        if self != hover_obj:
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False

            return False

        if not self._hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self._hovering = True

        if mouse_info.released[0]:
            self.ticked_on = True

            return True

        return False


class CheckBoxGrid:
    """
    Class to create a grid of checkboxes with n columns (images must be of the same size)
    """

    __slots__ = (
        '_init_pos', '_current_x', '_current_y', '_cols', '_increment', '_layer',
        'check_boxes', 'clicked_i', '_rect', 'objs_info'
    )

    def __init__(
            self, pos: RectPos, check_boxes_info: tuple[tuple[pg.Surface, str], ...], cols: int,
            inverted_axes: tuple[bool, bool], base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates all the checkboxes
        Args:
            position, checkboxes images and texts, columns, inverted axes,
            base layer (default = BG_LAYER)
        """

        #  Current x and y don't change during window resize
        self._init_pos: RectPos = pos
        self._current_x: float = self._init_pos.x
        self._current_y: float = self._init_pos.y

        self._cols: int = cols

        self._increment: Size = Size(
            check_boxes_info[0][0].get_width() + 10, check_boxes_info[0][0].get_height() + 10
        )
        if inverted_axes[0]:
            self._increment.w *= -1
        if inverted_axes[1]:
            self._increment.h *= -1

        self._layer: int = base_layer

        self.check_boxes: list[LockedCheckBox] = []
        self.clicked_i: int = 0
        self._rect: pg.FRect = pg.FRect(0.0, 0.0, 0.0, 0.0)

        self.objs_info: list[ObjInfo] = [
            ObjInfo(f'checkbox {i}', check_box) for i, check_box in enumerate(self.check_boxes)
        ]

        self.change_grid(check_boxes_info, 1.0, 1.0)

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object's layer
        """

        return self if self._rect.collidepoint(mouse_pos) else None, self._layer

    def post_resize(self) -> None:
        """
        Handles post resizing behavior
        """

        rects: tuple[pg.FRect, ...] = tuple(check_box.rect for check_box in self.check_boxes)
        left: float = min(rect.left for rect in rects)
        top: float = min(rect.top for rect in rects)
        w: float = max(rect.right for rect in rects) - left
        h: float = max(rect.bottom for rect in rects) - top
        self._rect = pg.FRect(left, top, w, h)

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, self._layer, depth_counter)]

    def tick_on(self, clicked_i: int) -> None:
        """
        Ticks on a specific checkbox
        Args:
            index
        """

        if self.clicked_i < len(self.check_boxes):
            self.check_boxes[self.clicked_i].ticked_on = False
        self.clicked_i = clicked_i
        self.check_boxes[self.clicked_i].ticked_on = True

    def change_grid(
            self, check_boxes_info: tuple[tuple[pg.Surface, str], ...],
            win_ratio_w: float, win_ratio_h: float
    ) -> None:
        """
        Clears the grid and creates a new one
        Args:
            checkboxes images and texts, window width ratio, window height ratio
        """

        self._current_x, self._current_y = self._init_pos.xy
        self.check_boxes = []
        for i, info in enumerate(check_boxes_info):
            imgs: tuple[pg.Surface, pg.Surface] = (info[0], add_border(info[0], WHITE))
            check_box: LockedCheckBox = LockedCheckBox(
                RectPos(self._current_x, self._current_y, self._init_pos.coord), imgs,
                info[1], self._layer
            )
            check_box.handle_resize(win_ratio_w, win_ratio_h)
            self.check_boxes.append(check_box)

            self._current_x += self._increment.w
            if (i + 1) % self._cols == 0:
                self._current_x = self._init_pos.x
                self._current_y += self._increment.h

        rects: tuple[pg.FRect, ...] = tuple(check_box.rect for check_box in self.check_boxes)
        left: float = min(rect.left for rect in rects)
        top: float = min(rect.top for rect in rects)
        w: float = max(rect.right for rect in rects) - left
        h: float = max(rect.bottom for rect in rects) - top
        self._rect = pg.FRect(left, top, w, h)

        self.objs_info = [
            ObjInfo(f'checkbox {i}', check_box) for i, check_box in enumerate(self.check_boxes)
        ]

        self.tick_on(0)

    def insert(
            self, insert_i: int, check_box_info: tuple[pg.Surface, str],
            win_ratio_w: float, win_ratio_h: float
    ) -> None:
        """
        Inserts a checkbox at an index
        Args:
            index (appends if -1), checkbox info, window width ratio, window height ratio
        """

        imgs: tuple[pg.Surface, pg.Surface] = (
            check_box_info[0], add_border(check_box_info[0], WHITE)
        )

        if insert_i != -1:
            self.check_boxes[insert_i].set_info(imgs, check_box_info[1])
            self.check_boxes[insert_i].handle_resize(win_ratio_w, win_ratio_h)
        else:
            check_box: LockedCheckBox = LockedCheckBox(
                RectPos(self._current_x, self._current_y, self._init_pos.coord), imgs,
                check_box_info[1], self._layer
            )
            check_box.handle_resize(win_ratio_w, win_ratio_h)
            self.check_boxes.append(check_box)

            self._current_x += self._increment.w
            if len(self.check_boxes) % self._cols == 0:
                self._current_x = self._init_pos.x
                self._current_y += self._increment.h

        rects: tuple[pg.FRect, ...] = tuple(check_box.rect for check_box in self.check_boxes)
        left: float = min(rect.left for rect in rects)
        top: float = min(rect.top for rect in rects)
        w: float = max(rect.right for rect in rects) - left
        h: float = max(rect.bottom for rect in rects) - top
        self._rect = pg.FRect(left, top, w, h)

        self.objs_info = [
            ObjInfo(f'checkbox {i}', check_box) for i, check_box in enumerate(self.check_boxes)
        ]

    def remove(
            self, remove_i: int, fallback: tuple[pg.Surface, str],
            win_ratio_w: float, win_ratio_h: float
    ) -> None:
        """
        Removes a checkbox at an index
        Args:
            index, fallback image and text, window width ratio, window height ratio
        """

        check_box: LockedCheckBox = self.check_boxes.pop(remove_i)
        self._current_x = getattr(check_box.rect, self._init_pos.coord)[0] / win_ratio_w
        self._current_y = getattr(check_box.rect, self._init_pos.coord)[1] / win_ratio_h
        for i in range(remove_i, len(self.check_boxes)):
            self.check_boxes[i].init_pos.x = self._current_x
            self.check_boxes[i].init_pos.y = self._current_y
            pos: tuple[float, float] = (
                self._current_x * win_ratio_w, self._current_y * win_ratio_h
            )
            setattr(self.check_boxes[i].rect, self._init_pos.coord, pos)

            self._current_x += self._increment.w
            if (i + 1) % self._cols == 0:
                self._current_x = self._init_pos.x
                self._current_y += self._increment.h

        if not self.check_boxes:
            imgs: tuple[pg.Surface, pg.Surface] = (fallback[0], add_border(fallback[0], WHITE))
            check_box = LockedCheckBox(
                RectPos(self._current_x, self._current_y, self._init_pos.coord), imgs,
                fallback[1], self._layer
            )
            check_box.handle_resize(win_ratio_w, win_ratio_h)
            self.check_boxes.append(check_box)

            self._current_x = self._init_pos.x + self._increment.w
            self._current_y = self._init_pos.y

        if self.clicked_i > remove_i:
            self.tick_on(self.clicked_i - 1)
        elif self.clicked_i == remove_i:
            self.clicked_i = min(self.clicked_i, len(self.check_boxes) - 1)
            self.check_boxes[self.clicked_i].ticked_on = True

        rects: tuple[pg.FRect, ...] = tuple(check_box.rect for check_box in self.check_boxes)
        left: float = min(rect.left for rect in rects)
        top: float = min(rect.top for rect in rects)
        w: float = max(rect.right for rect in rects) - left
        h: float = max(rect.bottom for rect in rects) - top
        self._rect = pg.FRect(left, top, w, h)

        self.objs_info = [
            ObjInfo(f'checkbox {i}', check_box) for i, check_box in enumerate(self.check_boxes)
        ]

    def upt(self, hover_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...]) -> int:
        """
        Allows ticking on only one check_box at a time
        Args:
            hovered object (can be None), mouse info, keys
        Returns
            index of the active checkbox
        """

        if (self == hover_obj or hover_obj in self.check_boxes) and keys:
            clicked_i: int = self.clicked_i

            sub_1: int
            add_1: int
            sub_cols: int
            add_cols: int
            if self._increment.w > 0:
                sub_1, add_1 = pg.K_LEFT, pg.K_RIGHT
            else:
                sub_1, add_1 = pg.K_RIGHT, pg.K_LEFT
            if self._increment.h > 0:
                sub_cols, add_cols = pg.K_UP, pg.K_DOWN
            else:
                sub_cols, add_cols = pg.K_DOWN, pg.K_UP

            if sub_1 in keys:
                clicked_i = max(clicked_i - 1, 0)
            if add_1 in keys:
                clicked_i = min(clicked_i + 1, len(self.check_boxes) - 1)
            if sub_cols in keys and clicked_i - self._cols >= 0:
                clicked_i -= self._cols
            if add_cols in keys and clicked_i + self._cols <= len(self.check_boxes) - 1:
                clicked_i += self._cols

            if self.clicked_i != clicked_i:
                self.tick_on(clicked_i)

        for i, check_box in enumerate(self.check_boxes):
            if check_box.upt(hover_obj, mouse_info):
                self.tick_on(i)

        return self.clicked_i
