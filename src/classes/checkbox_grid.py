"""Classes to create a locked checkbox or a grid of connected checkboxes."""

from math import ceil
from typing import Optional, Any

import pygame as pg

from src.classes.clickable import Clickable

from src.utils import (
    Point, RectPos, Ratio, ObjInfo, MouseInfo, add_border, rec_move_rect, rec_resize
)
from src.type_utils import PosPair, CheckboxInfo
from src.consts import MOUSE_LEFT, WHITE, VISIBLE_CHECKBOX_GRID_ROWS, BG_LAYER


class LockedCheckbox(Clickable):
    """Class to create a checkbox that can't be unchecked."""

    __slots__ = (
        "_is_checked",
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.Surface, ...], hovering_text: Optional[str],
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox.

        Args:
            position, two images, hovering text (can be None), base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self._is_checked: bool = False

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        super().leave()
        self.img_i = 1 if self._is_checked else int(self._is_hovering)

    def set_info(self, imgs: tuple[pg.Surface, ...], text: str) -> None:
        """
        Sets the images and text.

        Args:
            two images, text
        """

        self._init_imgs = self._imgs = imgs
        if self._hovering_text_label:
            self._hovering_text_label.set_text(text)

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and checks it if clicked.

        Args:
            hovered object (can be None), mouse info
        Returns:
            True if the checkbox was checked else False
        """

        self._handle_hover(hovered_obj)
        if not self._is_hovering:
            self.img_i = int(self._is_checked)

            return False

        self.img_i = 1
        if mouse_info.released[MOUSE_LEFT]:
            self._is_checked = True

        return mouse_info.released[MOUSE_LEFT]


class CheckboxGrid:
    """Class to create a grid of checkboxes (images must be of the same size)."""

    __slots__ = (
        "_init_pos", "_unresized_last_point", "cols", "_increment", "_layer", "checkboxes", "_hovered_checkbox",
        "visible_checkboxes", "clicked_i", "offset_y", "rect", "_win_ratio", "objs_info"
    )

    def __init__(
            self, pos: RectPos, checkboxes_info: tuple[CheckboxInfo, ...], cols: int,
            inverted_axes: tuple[bool, bool], base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates all the checkboxes.

        Args:
            position, checkboxes info, columns, inverted axes,
            base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos
        self._unresized_last_point: Point = Point(self._init_pos.x, self._init_pos.y)

        self.cols: int = cols
        pointer_checkbox_img: pg.Surface = checkboxes_info[0][0]
        self._increment: Point = Point(
            pointer_checkbox_img.get_width() + 10, pointer_checkbox_img.get_height() + 10
        )
        if inverted_axes[0]:
            self._increment.x = -self._increment.x
        if inverted_axes[1]:
            self._increment.y = -self._increment.y

        self._layer: int = base_layer

        self.checkboxes: list[LockedCheckbox] = []
        self.visible_checkboxes: list[LockedCheckbox] = []
        self._hovered_checkbox: Optional[LockedCheckbox] = None
        self.clicked_i: int = 0
        self.offset_y: int = 0
        self.rect: pg.Rect

        self._win_ratio: Ratio = Ratio(1, 1)

        self.objs_info: list[ObjInfo]

        self.set_grid(checkboxes_info)

    def get_hovering_info(self, mouse_xy: PosPair) -> tuple[bool, int]:
        """
        Gets the hovering info.

        Args:
            mouse position
        Returns:
            True if the object is being hovered else False, hovered object layer
        """

        return self.rect.collidepoint(mouse_xy), self._layer

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        self._win_ratio = win_ratio

    def post_resize(self) -> None:
        """Gets the rect after the checkboxes were resized."""

        rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in self.visible_checkboxes)
        left: int = min(rect.left for rect in rects)
        top: int = min(rect.top for rect in rects)
        w: int = max(rect.right for rect in rects) - left
        h: int = max(rect.bottom for rect in rects) - top
        self.rect = pg.Rect(left, top, w, h)

    def check(self, clicked_i: int) -> None:
        """
        Checks a specific checkbox and unchecks the previous one if it exists.

        Changes clicked_i and calculates the visible checkboxes.

        Args:
            index of the active checkbox
        """

        self.checkboxes[self.clicked_i].img_i = 0
        self.checkboxes[self.clicked_i]._is_checked = False

        self.clicked_i = clicked_i
        self.checkboxes[self.clicked_i].img_i = 1
        self.checkboxes[self.clicked_i]._is_checked = True

        clicked_row: int = self.clicked_i // self.cols
        prev_offset_y: int = self.offset_y
        if clicked_row < self.offset_y:
            self.offset_y = clicked_row
        elif clicked_row >= self.offset_y + VISIBLE_CHECKBOX_GRID_ROWS:
            self.offset_y = clicked_row - VISIBLE_CHECKBOX_GRID_ROWS + 1

        if self.offset_y != prev_offset_y:
            visible_start: int = self.offset_y * self.cols
            visible_end: int = visible_start + (VISIBLE_CHECKBOX_GRID_ROWS * self.cols)
            self.visible_checkboxes = self.checkboxes[visible_start:visible_end]

            self._unresized_last_point.x = self._init_pos.x
            self._unresized_last_point.y = self._init_pos.y
            for i, checkbox in enumerate(self.visible_checkboxes):
                rec_move_rect(
                    checkbox, self._unresized_last_point.x, self._unresized_last_point.y, self._win_ratio
                )
                rec_resize([checkbox], self._win_ratio)

                self._unresized_last_point.x += self._increment.x
                if not (i + 1) % self.cols:
                    self._unresized_last_point.x = self._init_pos.x
                    self._unresized_last_point.y += self._increment.y

            rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in self.visible_checkboxes)
            left: int = min(rect.left for rect in rects)
            top: int = min(rect.top for rect in rects)
            w: int = max(rect.right for rect in rects) - left
            h: int = max(rect.bottom for rect in rects) - top
            self.rect = pg.Rect(left, top, w, h)
            self.objs_info = [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def set_grid(self, checkboxes_info: tuple[CheckboxInfo, ...]) -> None:
        """
        Clears the grid and creates a new one.

        Args:
            checkboxes info
        """

        self.checkboxes = [
            LockedCheckbox(
                RectPos(0, 0, self._init_pos.coord_type), (img, add_border(img, WHITE)),
                hovering_text, self._layer
            )
            for (img, hovering_text) in checkboxes_info
        ]

        visible_start: int = self.offset_y * self.cols
        visible_end: int = visible_start + (VISIBLE_CHECKBOX_GRID_ROWS * self.cols)
        self.visible_checkboxes = self.checkboxes[visible_start:visible_end]

        self._unresized_last_point.x = self._init_pos.x
        self._unresized_last_point.y = self._init_pos.y
        for i, checkbox in enumerate(self.visible_checkboxes):
            rec_move_rect(
                checkbox, self._unresized_last_point.x, self._unresized_last_point.y, self._win_ratio
            )
            rec_resize([checkbox], self._win_ratio)

            self._unresized_last_point.x += self._increment.x
            if not (i + 1) % self.cols:
                self._unresized_last_point.x = self._init_pos.x
                self._unresized_last_point.y += self._increment.y

        rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in self.visible_checkboxes)
        left: int = min(rect.left for rect in rects)
        top: int = min(rect.top for rect in rects)
        w: int = max(rect.right for rect in rects) - left
        h: int = max(rect.bottom for rect in rects) - top
        self.rect = pg.Rect(left, top, w, h)
        self.objs_info = [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

        self.check(0)

    def replace(self, replace_i: Optional[int], img: pg.Surface, hovering_text: str) -> None:
        """
        Inserts a checkbox at an index.

        Args:
            index (appends if None), checkbox image, checkbox text
        """

        checkbox: LockedCheckbox
        if replace_i is not None:
            checkbox = self.checkboxes[replace_i]
            checkbox.set_info((img, add_border(img, WHITE)), hovering_text)
            if checkbox in self.visible_checkboxes:
                rec_resize([checkbox], self._win_ratio)
        else:
            pos: RectPos = RectPos(
                self._unresized_last_point.x, self._unresized_last_point.y,
                self._init_pos.coord_type
            )
            checkbox = LockedCheckbox(
                pos, (img, add_border(img, WHITE)), hovering_text, self._layer
            )
            self.checkboxes.append(checkbox)

            visible_start: int = self.offset_y * self.cols
            visible_end: int = visible_start + (VISIBLE_CHECKBOX_GRID_ROWS * self.cols)
            self.visible_checkboxes = self.checkboxes[visible_start:visible_end]

            if checkbox in self.visible_checkboxes:
                rec_move_rect(
                    checkbox, self._unresized_last_point.x, self._unresized_last_point.y, self._win_ratio
                )
                rec_resize([checkbox], self._win_ratio)

                self._unresized_last_point.x += self._increment.x
                if not len(self.checkboxes) % self.cols:
                    self._unresized_last_point.x = self._init_pos.x
                    self._unresized_last_point.y += self._increment.y

                rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in self.visible_checkboxes)
                left: int = min(rect.left for rect in rects)
                top: int = min(rect.top for rect in rects)
                w: int = max(rect.right for rect in rects) - left
                h: int = max(rect.bottom for rect in rects) - top
                self.rect = pg.Rect(left, top, w, h)
                self.objs_info = [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def _get_grid_from_fallback(self, img: pg.Surface, hovering_text: Optional[str]) -> None:
        """
        Makes the grid out of the fallback info if all checkboxes were removed.

        Args:
            checkbox image, checkbox text (can be None)
        """

        pos: RectPos = RectPos(self._init_pos.x, self._init_pos.y, self._init_pos.coord_type)
        checkbox = LockedCheckbox(pos, (img, add_border(img, WHITE)), hovering_text, self._layer)
        rec_resize([checkbox], self._win_ratio)

        self.checkboxes = [checkbox]
        self.visible_checkboxes = self.checkboxes.copy()

        self._unresized_last_point.x = self._init_pos.x + self._increment.x
        self._unresized_last_point.y = self._init_pos.y
        if self.cols == 1:
            self._unresized_last_point.x = self._init_pos.x
            self._unresized_last_point.y += self._increment.y

    def remove(self, remove_i: int, fallback_info: CheckboxInfo) -> None:
        """
        Removes a checkbox at an index.

        Args:
            index, fallback info
        """

        removed_checkbox: LockedCheckbox = self.checkboxes.pop(remove_i)
        num_rows: int = ceil(len(self.checkboxes) / self.cols)
        should_decrease_offset: bool = bool(
            self.offset_y and (num_rows - self.offset_y < VISIBLE_CHECKBOX_GRID_ROWS)
        )

        self._unresized_last_point.x = removed_checkbox.init_pos.x
        self._unresized_last_point.y = removed_checkbox.init_pos.y
        remove_start_i: int = remove_i

        visible_start: int = self.offset_y * self.cols
        if should_decrease_offset or remove_i < visible_start:
            self._unresized_last_point.x = self._init_pos.x
            self._unresized_last_point.y = self._init_pos.y
            remove_start_i = visible_start

        if should_decrease_offset:
            self.offset_y -= 1
        visible_start = self.offset_y * self.cols
        visible_end: int = visible_start + (VISIBLE_CHECKBOX_GRID_ROWS * self.cols)
        self.visible_checkboxes = self.checkboxes[visible_start:visible_end]
        for i in range(remove_start_i, visible_start + len(self.visible_checkboxes)):
            rec_move_rect(
                self.checkboxes[i], self._unresized_last_point.x, self._unresized_last_point.y,
                self._win_ratio
            )

            self._unresized_last_point.x += self._increment.x
            if not (i + 1) % self.cols:
                self._unresized_last_point.x = self._init_pos.x
                self._unresized_last_point.y += self._increment.y

        if not self.checkboxes:
            self._get_grid_from_fallback(*fallback_info)
            self.visible_checkboxes = self.checkboxes.copy()

        if self.clicked_i > remove_i:
            self.clicked_i -= 1
        elif self.clicked_i == remove_i:
            self.clicked_i = min(self.clicked_i, len(self.checkboxes) - 1)
            self.checkboxes[self.clicked_i].img_i = 1
            self.checkboxes[self.clicked_i]._is_checked = True

        rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in self.visible_checkboxes)
        left: int = min(rect.left for rect in rects)
        top: int = min(rect.top for rect in rects)
        w: int = max(rect.right for rect in rects) - left
        h: int = max(rect.bottom for rect in rects) - top
        self.rect = pg.Rect(left, top, w, h)
        self.objs_info = [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def _move_with_keys(self, keys: list[int]) -> int:
        """
        Moves the selected checkbox with keys.

        Args:
            keys
        Returns:
            index of the active checkbox
        """

        copy_clicked_i: int = self.clicked_i

        k_sub_1: int = pg.K_LEFT
        k_add_1: int = pg.K_RIGHT
        k_sub_cols: int = pg.K_UP
        k_add_cols: int = pg.K_DOWN
        if self._increment.x < 0:
            k_sub_1, k_add_1 = k_add_1, k_sub_1
        if self._increment.y < 0:
            k_sub_cols, k_add_cols = k_add_cols, k_sub_cols

        if k_sub_1 in keys:
            copy_clicked_i = max(copy_clicked_i - 1, 0)
        if k_add_1 in keys:
            copy_clicked_i = min(copy_clicked_i + 1, len(self.checkboxes) - 1)
        if k_sub_cols in keys and (copy_clicked_i - self.cols >= 0):
            copy_clicked_i -= self.cols
        if k_add_cols in keys and (copy_clicked_i + self.cols <= len(self.checkboxes) - 1):
            copy_clicked_i += self.cols

        return copy_clicked_i

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]) -> int:
        """
        Allows checking only one checkbox at a time.

        Args:
            hovered object (can be None), mouse info, keys
        Returns
            index of the active checkbox
        """

        prev_hovered_checkbox: Optional[LockedCheckbox] = self._hovered_checkbox
        self._hovered_checkbox = hovered_obj if hovered_obj in self.visible_checkboxes else None

        if self == hovered_obj or self._hovered_checkbox and keys:
            future_clicked_i: int = self._move_with_keys(keys)
            if self.clicked_i != future_clicked_i:
                self.check(future_clicked_i)

        if prev_hovered_checkbox and prev_hovered_checkbox != self._hovered_checkbox:
            prev_hovered_checkbox.upt(hovered_obj, mouse_info)
        if self._hovered_checkbox:
            has_been_checked: bool = self._hovered_checkbox.upt(hovered_obj, mouse_info)
            if has_been_checked:
                visible_start: int = self.offset_y * self.cols
                visible_checkbox_i: int = self.visible_checkboxes.index(self._hovered_checkbox)
                self.check(visible_start + visible_checkbox_i)

        return self.clicked_i
