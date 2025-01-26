"""Classes to create a locked checkbox or a grid of connected checkboxes."""

from math import ceil
from typing import Optional

import pygame as pg

from src.classes.clickable import Clickable

from src.utils import (
    Point, RectPos, Ratio, ObjInfo, Mouse, Keyboard, add_border, rec_move_rect, rec_resize
)
from src.type_utils import PosPair, CheckboxInfo
from src.consts import MOUSE_LEFT, WHITE, NUM_VISIBLE_CHECKBOX_GRID_ROWS, BG_LAYER


class LockedCheckbox(Clickable):
    """Class to create a checkbox that can't be unchecked."""

    __slots__ = (
        "is_checked",
    )

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], hovering_text: Optional[str],
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox.

        Args:
            position, two images, hovering text (can be None), base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        super().leave()
        self.img_i = int(self.is_checked)

    def upt(self, mouse: Mouse) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and checks it if clicked.

        Args:
            mouse
        Returns:
           checked flag
        """

        self._is_hovering = mouse.hovered_obj == self

        checked: bool = mouse.released[MOUSE_LEFT] and self._is_hovering
        if checked:
            self.is_checked = True
        self.img_i = 1 if self.is_checked else int(self._is_hovering)

        return checked


class CheckboxGrid:
    """Class to create a grid of checkboxes (images must be of the same size)."""

    __slots__ = (
        "_init_pos", "_unresized_last_point", "num_cols", "_increment", "_layer", "checkboxes",
        "_hovered_checkbox", "visible_checkboxes", "clicked_i", "offset_y", "rect", "_win_ratio",
        "objs_info"
    )

    def __init__(
            self, pos: RectPos, checkboxes_info: list[CheckboxInfo], num_cols: int,
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

        self.num_cols: int = num_cols
        checkbox_img_w: int = checkboxes_info[0][0].get_width()
        checkbox_img_h: int = checkboxes_info[0][0].get_height()

        increment_x: int = -checkbox_img_w - 10 if inverted_axes[0] else checkbox_img_w + 10
        increment_y: int = -checkbox_img_h - 10 if inverted_axes[1] else checkbox_img_h + 10
        self._increment: Point = Point(increment_x, increment_y)

        self._layer: int = base_layer

        self.checkboxes: list[LockedCheckbox]
        self.visible_checkboxes: list[LockedCheckbox]
        self._hovered_checkbox: Optional[LockedCheckbox] = None
        self.clicked_i: int = 0
        self.offset_y: int = 0
        self.rect: pg.Rect

        self._win_ratio: Ratio = Ratio(1, 1)

        self.objs_info: list[ObjInfo]

        self.set_grid(checkboxes_info, 0, 0)

    def get_hovering_info(self, mouse_xy: PosPair) -> tuple[bool, int]:
        """
        Gets the hovering info.

        Args:
            mouse xy
        Returns:
            hovered flag, hovered object layer
        """

        return self.rect.collidepoint(mouse_xy), self._layer

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self._hovered_checkbox = None

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        left: int = min([rect.left for rect in rects])
        top: int = min([rect.top for rect in rects])
        w: int = max([rect.right for rect in rects]) - left
        h: int = max([rect.bottom for rect in rects]) - top
        self.rect = pg.Rect(left, top, w, h)
        self._win_ratio = win_ratio

    def _shift_visible_checkboxes(self, shift_i: int) -> None:
        """
        Shift all the visible checkboxes to unresized_last_point starting from an index.

        Args:
            index
        """

        ptr_init_point: Point = self._unresized_last_point

        visible_start_i: int = self.offset_y * self.num_cols
        for i in range(shift_i, visible_start_i + len(self.visible_checkboxes)):
            rec_move_rect(self.checkboxes[i], ptr_init_point.x, ptr_init_point.y, self._win_ratio)
            rec_resize([self.checkboxes[i]], self._win_ratio)

            if (i + 1) % self.num_cols:
                ptr_init_point.x += self._increment.x
            else:
                ptr_init_point.x = self._init_pos.x
                ptr_init_point.y += self._increment.y

    def set_offset_y(self, offset_y: int) -> None:
        """
        Sets the row offset from the start.

        Args:
            y offset
        """

        self.offset_y = offset_y

        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + (NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols)
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        self._unresized_last_point.xy = self._init_pos.xy
        self._shift_visible_checkboxes(self.offset_y * self.num_cols)

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        left: int = min([rect.left for rect in rects])
        top: int = min([rect.top for rect in rects])
        w: int = max([rect.right for rect in rects]) - left
        h: int = max([rect.bottom for rect in rects]) - top
        self.rect = pg.Rect(left, top, w, h)
        self.objs_info = [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def check(self, clicked_i: int) -> None:
        """
        Checks a specific checkbox and unchecks the previous one if it exists.

        Changes clicked_i and calculates the visible checkboxes.

        Args:
            index
        """

        self.checkboxes[self.clicked_i].img_i = 0
        self.checkboxes[self.clicked_i].is_checked = False

        self.clicked_i = clicked_i
        self.checkboxes[self.clicked_i].img_i = 1
        self.checkboxes[self.clicked_i].is_checked = True

        clicked_row: int = self.clicked_i // self.num_cols
        if clicked_row < self.offset_y:
            self.set_offset_y(clicked_row)
        elif clicked_row >= self.offset_y + NUM_VISIBLE_CHECKBOX_GRID_ROWS:
            self.set_offset_y(clicked_row - NUM_VISIBLE_CHECKBOX_GRID_ROWS + 1)

    def set_grid(self, checkboxes_info: list[CheckboxInfo], clicked_i: int, offset_y: int) -> None:
        """
        Clears the grid and creates a new one.

        Args:
            checkboxes info, clicked checkbox index, y offset
        """

        coord_type: str = self._init_pos.coord_type
        layer: int = self._layer
        self.checkboxes = [
            LockedCheckbox(
                RectPos(0, 0, coord_type), [img, add_border(img, WHITE)], hovering_text, layer
            )
            for (img, hovering_text) in checkboxes_info
        ]

        self.check(clicked_i)
        self.set_offset_y(offset_y)

    def edit(self, edit_i: int, img: pg.Surface, hovering_text: str) -> None:
        """
        Edits a checkbox.

        Args:
            index, image, hovering text
        """

        checkbox: LockedCheckbox = self.checkboxes[edit_i]
        checkbox.init_imgs = checkbox.imgs = [img, add_border(img, WHITE)]
        if checkbox.hovering_text_label:
            checkbox.hovering_text_label.set_text(hovering_text)

        if checkbox in self.visible_checkboxes:
            rec_resize([checkbox], self._win_ratio)

    def append(self, img: pg.Surface, hovering_text: str) -> None:
        """
        Appends a checkbox.

        Args:
            checkbox image, checkbox text
        """

        ptr_init_point: Point = self._unresized_last_point

        pos: RectPos = RectPos(ptr_init_point.x, ptr_init_point.y, self._init_pos.coord_type)
        imgs: list[pg.Surface] = [img, add_border(img, WHITE)]
        checkbox: LockedCheckbox = LockedCheckbox(pos, imgs, hovering_text, self._layer)
        self.checkboxes.append(checkbox)

        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + (NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols)
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        if checkbox in self.visible_checkboxes:
            rec_move_rect(checkbox, ptr_init_point.x, ptr_init_point.y, self._win_ratio)
            rec_resize([checkbox], self._win_ratio)

            if len(self.checkboxes) % self.num_cols:
                ptr_init_point.x += self._increment.x
            else:
                ptr_init_point.x = self._init_pos.x
                ptr_init_point.y += self._increment.y

            rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
            left: int = min([rect.left for rect in rects])
            top: int = min([rect.top for rect in rects])
            w: int = max([rect.right for rect in rects]) - left
            h: int = max([rect.bottom for rect in rects]) - top
            self.rect = pg.Rect(left, top, w, h)
            self.objs_info = [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def remove(self, remove_i: int, fallback_info: CheckboxInfo) -> None:
        """
        Removes a checkbox at an index.

        Args:
            index, fallback info
        """

        if len(self.checkboxes) == 1:
            self.edit(0, *fallback_info)

            return

        removed_checkbox: LockedCheckbox = self.checkboxes.pop(remove_i)
        num_above_rows: int = ceil(len(self.checkboxes) / self.num_cols) - self.offset_y
        could_see_more_rows: bool = num_above_rows < NUM_VISIBLE_CHECKBOX_GRID_ROWS
        should_dec_offset: bool = bool(self.offset_y) and could_see_more_rows

        if should_dec_offset:
            self.offset_y -= 1
        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + (NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols)
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        if should_dec_offset or remove_i < visible_start_i:
            self._unresized_last_point.xy = self._init_pos.xy
            self._shift_visible_checkboxes(visible_start_i)
        else:
            self._unresized_last_point.xy = removed_checkbox.init_pos.xy
            self._shift_visible_checkboxes(remove_i)

        if self.clicked_i > remove_i:
            self.clicked_i -= 1
        elif self.clicked_i == remove_i:
            self.clicked_i = min(self.clicked_i, len(self.checkboxes) - 1)
            self.checkboxes[self.clicked_i].img_i = 1
            self.checkboxes[self.clicked_i].is_checked = True

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        left: int = min([rect.left for rect in rects])
        top: int = min([rect.top for rect in rects])
        w: int = max([rect.right for rect in rects]) - left
        h: int = max([rect.bottom for rect in rects]) - top
        self.rect = pg.Rect(left, top, w, h)
        self.objs_info = [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def _move_with_left_right(
            self, keyboard: Keyboard, clicked_i: int, k_sub_1: int, k_add_1: int
    ) -> int:
        """
        Moves the selected checkbox with left and right arrows.

        Args:
            keyboard, clicked checkbox index, left key, right key
        Returns:
            clicked checkbox index
        """

        copy_clicked_i: int = clicked_i

        if k_sub_1 in keyboard.timed:
            if keyboard.is_ctrl_on:
                copy_clicked_i -= copy_clicked_i % self.num_cols
            else:
                copy_clicked_i = max(copy_clicked_i - 1, 0)

        if k_add_1 in keyboard.timed:
            if keyboard.is_ctrl_on:
                row_start: int = copy_clicked_i - copy_clicked_i % self.num_cols
                copy_clicked_i = min(row_start + (self.num_cols - 1), len(self.checkboxes) - 1)
            else:
                copy_clicked_i = min(copy_clicked_i + 1, len(self.checkboxes) - 1)

        return copy_clicked_i

    def _move_with_up_down(
            self, keyboard: Keyboard, clicked_i: int, k_sub_cols: int, k_add_cols: int
    ) -> int:
        """
        Moves the selected checkbox with up and down arrows.

        Args:
            keyboard, clicked checkbox index, down key, up key
        Returns:
            clicked checkbox index
        """

        copy_clicked_i: int = clicked_i

        if k_sub_cols in keyboard.timed:
            can_sub_cols: bool = copy_clicked_i - self.num_cols >= 0
            if keyboard.is_ctrl_on:
                copy_clicked_i %= self.num_cols
            elif can_sub_cols:
                copy_clicked_i -= self.num_cols

        if k_add_cols in keyboard.timed:
            can_add_cols: bool = copy_clicked_i + self.num_cols <= len(self.checkboxes) - 1
            if keyboard.is_ctrl_on:
                column: int = copy_clicked_i % self.num_cols
                last_column: int = len(self.checkboxes) % self.num_cols
                num_rows: int = len(self.checkboxes) // self.num_cols
                row_i: int = num_rows if column < last_column else num_rows - 1
                copy_clicked_i = row_i * self.num_cols + column
            elif can_add_cols:
                copy_clicked_i += self.num_cols

        return copy_clicked_i

    def _move_with_keys(self, keyboard: Keyboard) -> None:
        """
        Moves the selected checkbox with keys.

        Args:
            keyboard
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

        copy_clicked_i = self._move_with_left_right(keyboard, copy_clicked_i, k_sub_1, k_add_1)
        copy_clicked_i = self._move_with_up_down(keyboard, copy_clicked_i, k_sub_cols, k_add_cols)
        if pg.K_HOME in keyboard.timed:
            copy_clicked_i = 0
        if pg.K_END in keyboard.timed:
            copy_clicked_i = len(self.checkboxes) - 1

        if copy_clicked_i != self.clicked_i:
            self.check(copy_clicked_i)

    def upt_checkboxes(self, mouse: Mouse) -> None:
        """
        Updates the previously hovered and hovered checkboxes.

        Args:
            mouse
        """

        prev_hovered_checkbox: Optional[LockedCheckbox] = self._hovered_checkbox
        is_hovering_checkbox: bool = mouse.hovered_obj in self.visible_checkboxes
        self._hovered_checkbox = mouse.hovered_obj if is_hovering_checkbox else None

        if prev_hovered_checkbox and prev_hovered_checkbox != self._hovered_checkbox:
            prev_hovered_checkbox.leave()
        if self._hovered_checkbox:
            has_checked: bool = self._hovered_checkbox.upt(mouse)
            if has_checked:
                visible_start_i: int = self.offset_y * self.num_cols
                visible_checkbox_i: int = self.visible_checkboxes.index(self._hovered_checkbox)
                self.check(visible_start_i + visible_checkbox_i)

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> int:
        """
        Allows checking only one checkbox at a time.

        Args:
            mouse, timed keys
        Returns
            index of the active checkbox
        """

        self.upt_checkboxes(mouse)
        if mouse.hovered_obj == self or self._hovered_checkbox and keyboard.timed:
            self._move_with_keys(keyboard)

        return self.clicked_i
