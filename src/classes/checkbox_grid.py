"""
Classes to create a locked checkbox or a grid of connected checkboxes
"""

import pygame as pg
from collections.abc import Iterator
from typing import Optional, Any

from src.classes.clickable import Clickable

from src.utils import RectPos, Size, ObjInfo, MouseInfo, add_border
from src.type_utils import LayeredBlitInfo, LayeredBlitSequence, LayerSequence
from src.consts import WHITE, BG_LAYER


class LockedCheckbox(Clickable):
    """
    Class to create a checkbox, when hovered changes image and displays text,
    when checked it will display the hovering image, cannot be unchecked
    """

    __slots__ = (
        'is_checked',
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.Surface, pg.Surface], hovering_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox
        Args:
            position, two images, hovering text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        img_i: int = 1 if self.is_checked else int(self._is_hovering)

        return self._base_blit(img_i)

    def set_info(self, imgs: tuple[pg.Surface, pg.Surface], text: str) -> None:
        """
        Sets images and text
        Args:
            two images, text
        """

        self._imgs = imgs
        if self._hovering_text_label:
            self._hovering_text_label.set_text(text)
            self._hovering_text_imgs = tuple(
                pg.Surface((int(rect.w), int(rect.h))) for rect in self._hovering_text_label.rects
            )

            hovering_text_info: Iterator[tuple[pg.Surface, LayeredBlitInfo]] = zip(
                self._hovering_text_imgs, self._hovering_text_label.blit()
            )
            for target_img, (text_img, _, _) in hovering_text_info:
                target_img.blit(text_img)

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and checks it if clicked
        Args:
            hovered object (can be None), mouse info
        Returns:
            True if the checkbox was checked else False
        """

        if self != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False

            return False

        if not self._is_hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self._is_hovering = True

        if mouse_info.released[0]:
            self.is_checked = True

            return True

        return False


class CheckboxGrid:
    """
    Class to create a grid of checkboxes with n columns (images must be of the same size)
    """

    __slots__ = (
        '_init_pos', '_last_x', '_last_y', '_cols', '_increment', '_layer',
        'checkboxes', 'clicked_i', 'rect', 'objs_info'
    )

    def __init__(
            self, pos: RectPos, checkboxes_info: tuple[tuple[pg.Surface, str], ...], cols: int,
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
        self._last_x: float = self._init_pos.x
        self._last_y: float = self._init_pos.y

        self._cols: int = cols

        self._increment: Size = Size(
            checkboxes_info[0][0].get_width() + 10, checkboxes_info[0][0].get_height() + 10
        )
        if inverted_axes[0]:
            self._increment.w *= -1
        if inverted_axes[1]:
            self._increment.h *= -1

        self._layer: int = base_layer

        self.checkboxes: list[LockedCheckbox] = []
        self.clicked_i: int = 0
        self.rect: pg.FRect = pg.FRect(0.0, 0.0, 0.0, 0.0)

        self.objs_info: list[ObjInfo] = [
            ObjInfo(f"checkbox {i}", checkbox) for i, checkbox in enumerate(self.checkboxes)
        ]

        self.change_grid(checkboxes_info, 1.0, 1.0)

    def check_hovering(self, mouse_pos: tuple[int, int]) -> tuple[Optional["CheckboxGrid"], int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object's layer
        """

        return self if self.rect.collidepoint(mouse_pos) else None, self._layer

    def post_resize(self) -> None:
        """
        Handles post resizing behavior
        """

        rects: tuple[pg.FRect, ...] = tuple(checkbox.rect for checkbox in self.checkboxes)
        left: float = min(rect.left for rect in rects)
        top: float = min(rect.top for rect in rects)
        w: float = max(rect.right for rect in rects) - left
        h: float = max(rect.bottom for rect in rects) - top
        self.rect = pg.FRect(left, top, w, h)

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, self._layer, depth_counter)]

    def check(self, clicked_i: int) -> None:
        """
        Checks a specific checkbox
        Args:
            index
        """

        if self.clicked_i < len(self.checkboxes):
            self.checkboxes[self.clicked_i].is_checked = False
        self.clicked_i = clicked_i
        self.checkboxes[self.clicked_i].is_checked = True

    def change_grid(
            self, checkboxes_info: tuple[tuple[pg.Surface, str], ...],
            win_ratio_w: float, win_ratio_h: float
    ) -> None:
        """
        Clears the grid and creates a new one
        Args:
            checkboxes images and texts, window width ratio, window height ratio
        """

        self._last_x, self._last_y = self._init_pos.xy
        self.checkboxes = []
        for i, info in enumerate(checkboxes_info):
            imgs: tuple[pg.Surface, pg.Surface] = (info[0], add_border(info[0], WHITE))
            checkbox: LockedCheckbox = LockedCheckbox(
                RectPos(self._last_x, self._last_y, self._init_pos.coord_type), imgs,
                info[1], self._layer
            )
            checkbox.handle_resize(win_ratio_w, win_ratio_h)
            self.checkboxes.append(checkbox)

            self._last_x += self._increment.w
            if not ((i + 1) % self._cols):
                self._last_x = self._init_pos.x
                self._last_y += self._increment.h

        rects: tuple[pg.FRect, ...] = tuple(checkbox.rect for checkbox in self.checkboxes)
        left: float = min(rect.left for rect in rects)
        top: float = min(rect.top for rect in rects)
        w: float = max(rect.right for rect in rects) - left
        h: float = max(rect.bottom for rect in rects) - top
        self.rect = pg.FRect(left, top, w, h)

        self.objs_info = [
            ObjInfo(f"checkbox {i}", checkbox) for i, checkbox in enumerate(self.checkboxes)
        ]

        self.check(0)

    def insert(
            self, insert_i: Optional[int], checkbox_info: tuple[pg.Surface, str],
            win_ratio_w: float, win_ratio_h: float
    ) -> None:
        """
        Inserts a checkbox at an index
        Args:
            index (appends if None), checkbox image and text,
            window width ratio, window height ratio
        """

        imgs: tuple[pg.Surface, pg.Surface] = (
            checkbox_info[0], add_border(checkbox_info[0], WHITE)
        )

        if insert_i is not None:
            self.checkboxes[insert_i].set_info(imgs, checkbox_info[1])
            self.checkboxes[insert_i].handle_resize(win_ratio_w, win_ratio_h)
        else:
            checkbox: LockedCheckbox = LockedCheckbox(
                RectPos(self._last_x, self._last_y, self._init_pos.coord_type), imgs,
                checkbox_info[1], self._layer
            )
            checkbox.handle_resize(win_ratio_w, win_ratio_h)
            self.checkboxes.append(checkbox)

            self._last_x += self._increment.w
            if not (len(self.checkboxes) % self._cols):
                self._last_x = self._init_pos.x
                self._last_y += self._increment.h

        rects: tuple[pg.FRect, ...] = tuple(checkbox.rect for checkbox in self.checkboxes)
        left: float = min(rect.left for rect in rects)
        top: float = min(rect.top for rect in rects)
        w: float = max(rect.right for rect in rects) - left
        h: float = max(rect.bottom for rect in rects) - top
        self.rect = pg.FRect(left, top, w, h)

        self.objs_info = [
            ObjInfo(f"checkbox {i}", checkbox) for i, checkbox in enumerate(self.checkboxes)
        ]

    def remove(
            self, remove_i: int, fallback_info: tuple[pg.Surface, str],
            win_ratio_w: float, win_ratio_h: float
    ) -> None:
        """
        Removes a checkbox at an index
        Args:
            index, fallback image and text, window width ratio, window height ratio
        """

        checkbox: LockedCheckbox = self.checkboxes.pop(remove_i)
        self._last_x = getattr(checkbox.rect, self._init_pos.coord_type)[0] / win_ratio_w
        self._last_y = getattr(checkbox.rect, self._init_pos.coord_type)[1] / win_ratio_h
        for i in range(remove_i, len(self.checkboxes)):
            # TODO: make into a method?
            self.checkboxes[i].init_pos.x = self._last_x
            self.checkboxes[i].init_pos.y = self._last_y
            pos: tuple[float, float] = (self._last_x * win_ratio_w, self._last_y * win_ratio_h)
            setattr(self.checkboxes[i].rect, self._init_pos.coord_type, pos)

            self._last_x += self._increment.w
            if not ((i + 1) % self._cols):
                self._last_x = self._init_pos.x
                self._last_y += self._increment.h

        if not self.checkboxes:
            imgs: tuple[pg.Surface, pg.Surface] = (
                fallback_info[0], add_border(fallback_info[0], WHITE)
            )
            checkbox = LockedCheckbox(
                RectPos(self._last_x, self._last_y, self._init_pos.coord_type), imgs,
                fallback_info[1], self._layer
            )
            checkbox.handle_resize(win_ratio_w, win_ratio_h)
            self.checkboxes = [checkbox]

            self._last_x = self._init_pos.x + self._increment.w
            self._last_y = self._init_pos.y

        if self.clicked_i > remove_i:
            self.check(self.clicked_i - 1)
        elif self.clicked_i == remove_i:
            self.clicked_i = min(self.clicked_i, len(self.checkboxes) - 1)
            self.checkboxes[self.clicked_i].is_checked = True

        rects: tuple[pg.FRect, ...] = tuple(checkbox.rect for checkbox in self.checkboxes)
        left: float = min(rect.left for rect in rects)
        top: float = min(rect.top for rect in rects)
        w: float = max(rect.right for rect in rects) - left
        h: float = max(rect.bottom for rect in rects) - top
        self.rect = pg.FRect(left, top, w, h)

        self.objs_info = [
            ObjInfo(f"checkbox {i}", checkbox) for i, checkbox in enumerate(self.checkboxes)
        ]

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...]) -> int:
        """
        Allows checking only one checkbox at a time
        Args:
            hovered object (can be None), mouse info, keys
        Returns
            index of the active checkbox
        """

        if (self == hovered_obj or hovered_obj in self.checkboxes) and keys:
            new_clicked_i: int = self.clicked_i

            k_sub_1: int
            k_add_1: int
            k_sub_cols: int
            k_add_cols: int
            if self._increment.w > 0:
                k_sub_1, k_add_1 = pg.K_LEFT, pg.K_RIGHT
            else:
                k_sub_1, k_add_1 = pg.K_RIGHT, pg.K_LEFT
            if self._increment.h > 0:
                k_sub_cols, k_add_cols = pg.K_UP, pg.K_DOWN
            else:
                k_sub_cols, k_add_cols = pg.K_DOWN, pg.K_UP

            if k_sub_1 in keys:
                new_clicked_i = max(new_clicked_i - 1, 0)
            if k_add_1 in keys:
                new_clicked_i = min(new_clicked_i + 1, len(self.checkboxes) - 1)
            if k_sub_cols in keys and new_clicked_i - self._cols >= 0:
                new_clicked_i -= self._cols
            if k_add_cols in keys and new_clicked_i + self._cols <= len(self.checkboxes) - 1:
                new_clicked_i += self._cols

            if self.clicked_i != new_clicked_i:
                self.check(new_clicked_i)

        for i, checkbox in enumerate(self.checkboxes):
            if checkbox.upt(hovered_obj, mouse_info):
                self.check(i)

        return self.clicked_i
