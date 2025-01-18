"""Classes to create a locked checkbox or a grid of connected checkboxes."""

from math import ceil
from typing import Optional

import pygame as pg

from src.classes.clickable import Clickable

from src.utils import Point, RectPos, Ratio, ObjInfo, Mouse, add_border, rec_move_rect, rec_resize
from src.type_utils import PosPair, CheckboxInfo
from src.consts import MOUSE_LEFT, WHITE, VISIBLE_CHECKBOX_GRID_ROWS, BG_LAYER


class LockedCheckbox(Clickable):
    """Class to create a checkbox that can't be unchecked."""

    __slots__ = (
        "_is_checked",
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

        self._is_checked: bool = False

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        super().leave()
        self.img_i = int(self._is_checked)

    def upt(self, mouse: Mouse) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and checks it if clicked.

        Args:
            mouse
        Returns:
            True if the checkbox has been checked else False
        """

        self._is_hovering = mouse.hovered_obj == self

        checked: bool = mouse.released[MOUSE_LEFT] and self._is_hovering
        if checked:
            self._is_checked = True
        self.img_i = 1 if self._is_checked else int(self._is_hovering)

        return checked


class CheckboxGrid:
    """Class to create a grid of checkboxes (images must be of the same size)."""

    __slots__ = (
        "_init_pos", "_unresized_last_point", "cols", "_increment", "_layer", "checkboxes",
        "_hovered_checkbox", "visible_checkboxes", "clicked_i", "offset_y", "rect", "_win_ratio",
        "objs_info"
    )

    def __init__(
            self, pos: RectPos, checkboxes_info: list[CheckboxInfo], cols: int,
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
        checkbox_img_w: int = checkboxes_info[0][0].get_width()
        checkbox_img_h: int = checkboxes_info[0][0].get_height()

        increment_x: int = -(checkbox_img_w + 10) if inverted_axes[0] else checkbox_img_w + 10
        increment_y: int = -(checkbox_img_h + 10) if inverted_axes[1] else checkbox_img_h + 10
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
            mouse position
        Returns:
            True if the object is being hovered else False, hovered object layer
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

    def set_offset_y(self, offset_y: int) -> None:
        """
        Sets the row offset from the start.

        Args:
            y offset
        """

        self.offset_y = offset_y

        visible_start: int = self.offset_y * self.cols
        visible_end: int = visible_start + (VISIBLE_CHECKBOX_GRID_ROWS * self.cols)
        self.visible_checkboxes = self.checkboxes[visible_start:visible_end]

        ptr_init_point: Point = self._unresized_last_point
        ptr_init_point.x = self._init_pos.x
        ptr_init_point.y = self._init_pos.y
        for i, checkbox in enumerate(self.visible_checkboxes):
            rec_move_rect(checkbox, ptr_init_point.x, ptr_init_point.y, self._win_ratio)
            rec_resize([checkbox], self._win_ratio)

            ptr_init_point.x += self._increment.x
            if not (i + 1) % self.cols:
                ptr_init_point.x = self._init_pos.x
                ptr_init_point.y += self._increment.y

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
        self.checkboxes[self.clicked_i]._is_checked = False

        self.clicked_i = clicked_i
        self.checkboxes[self.clicked_i].img_i = 1
        self.checkboxes[self.clicked_i]._is_checked = True

        clicked_row: int = self.clicked_i // self.cols
        if clicked_row < self.offset_y:
            self.set_offset_y(clicked_row)
        elif clicked_row >= self.offset_y + VISIBLE_CHECKBOX_GRID_ROWS:
            self.set_offset_y(clicked_row - VISIBLE_CHECKBOX_GRID_ROWS + 1)

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

    def replace(self, replace_i: int, img: pg.Surface, hovering_text: str) -> None:
        """
        Replaces a checkbox.

        Args:
            index, image, hovering text
        """

        checkbox: LockedCheckbox = self.checkboxes[replace_i]
        checkbox.init_imgs = checkbox.imgs = [img, add_border(img, WHITE)]
        if checkbox.hovering_text_label:
            checkbox.hovering_text_label.set_text(hovering_text)

        if checkbox in self.visible_checkboxes:
            rec_resize([checkbox], self._win_ratio)

    def append(self, img: pg.Surface, hovering_text: str) -> None:
        """
        Appends a checkbox.

        Args:
            index, checkbox image, checkbox text
        """

        ptr_init_point: Point = self._unresized_last_point

        pos: RectPos = RectPos(ptr_init_point.x, ptr_init_point.y, self._init_pos.coord_type)
        imgs: list[pg.Surface] = [img, add_border(img, WHITE)]
        checkbox: LockedCheckbox = LockedCheckbox(pos, imgs, hovering_text, self._layer)
        self.checkboxes.append(checkbox)

        visible_start: int = self.offset_y * self.cols
        visible_end: int = visible_start + (VISIBLE_CHECKBOX_GRID_ROWS * self.cols)
        self.visible_checkboxes = self.checkboxes[visible_start:visible_end]

        if checkbox in self.visible_checkboxes:
            rec_move_rect(checkbox, ptr_init_point.x, ptr_init_point.y, self._win_ratio)
            rec_resize([checkbox], self._win_ratio)

            ptr_init_point.x += self._increment.x
            if not len(self.checkboxes) % self.cols:
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

        removed_checkbox: LockedCheckbox = self.checkboxes.pop(remove_i)
        if not self.checkboxes:
            self.set_grid([fallback_info], 0, 0)

            return

        num_visible_rows: int = ceil(len(self.checkboxes) / self.cols) - self.offset_y
        should_decrease_offset: bool = bool(
            self.offset_y and num_visible_rows < VISIBLE_CHECKBOX_GRID_ROWS
        )

        if should_decrease_offset:
            self.offset_y -= 1
        visible_start: int = self.offset_y * self.cols
        visible_end: int = visible_start + (VISIBLE_CHECKBOX_GRID_ROWS * self.cols)
        self.visible_checkboxes = self.checkboxes[visible_start:visible_end]

        ptr_init_point: Point = self._unresized_last_point
        ptr_init_point.x = removed_checkbox.init_pos.x
        ptr_init_point.y = removed_checkbox.init_pos.y
        remove_start_i: int = remove_i
        if should_decrease_offset or remove_i < visible_start:
            ptr_init_point.x = self._init_pos.x
            ptr_init_point.y = self._init_pos.y
            remove_start_i = visible_start

        for i in range(remove_start_i, visible_start + len(self.visible_checkboxes)):
            rec_move_rect(self.checkboxes[i], ptr_init_point.x, ptr_init_point.y, self._win_ratio)

            ptr_init_point.x += self._increment.x
            if not (i + 1) % self.cols:
                ptr_init_point.x = self._init_pos.x
                ptr_init_point.y += self._increment.y

        if self.clicked_i > remove_i:
            self.clicked_i -= 1
        elif self.clicked_i == remove_i:
            self.clicked_i = min(self.clicked_i, len(self.checkboxes) - 1)
            self.checkboxes[self.clicked_i].img_i = 1
            self.checkboxes[self.clicked_i]._is_checked = True

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        left: int = min([rect.left for rect in rects])
        top: int = min([rect.top for rect in rects])
        w: int = max([rect.right for rect in rects]) - left
        h: int = max([rect.bottom for rect in rects]) - top
        self.rect = pg.Rect(left, top, w, h)
        self.objs_info = [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def _move_with_keys(self, timed_keys: list[int]) -> None:
        """
        Moves the selected checkbox with keys.

        Args:
            timed keys
        """

        local_clicked_i: int = self.clicked_i

        k_sub_1: int
        k_add_1: int
        k_sub_cols: int
        k_add_cols: int
        if self._increment.x > 0:
            k_sub_1, k_add_1 = pg.K_LEFT, pg.K_RIGHT
        else:
            k_sub_1, k_add_1 = pg.K_RIGHT, pg.K_LEFT
        if self._increment.y > 0:
            k_sub_cols, k_add_cols = pg.K_UP, pg.K_DOWN
        else:
            k_sub_cols, k_add_cols = pg.K_DOWN, pg.K_UP

        if k_sub_1 in timed_keys:
            local_clicked_i = max(local_clicked_i - 1, 0)
        if k_add_1 in timed_keys:
            local_clicked_i = min(local_clicked_i + 1, len(self.checkboxes) - 1)
        can_sub_cols: bool = local_clicked_i - self.cols >= 0
        if k_sub_cols in timed_keys and can_sub_cols:
            local_clicked_i -= self.cols
        can_add_cols: bool = local_clicked_i + self.cols <= len(self.checkboxes) - 1
        if k_add_cols in timed_keys and can_add_cols:
            local_clicked_i += self.cols
        if pg.K_HOME in timed_keys:
            local_clicked_i = 0
        if pg.K_END in timed_keys:
            local_clicked_i = len(self.checkboxes) - 1

        if self.clicked_i != local_clicked_i:
            self.check(local_clicked_i)

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
                visible_start: int = self.offset_y * self.cols
                visible_checkbox_i: int = self.visible_checkboxes.index(self._hovered_checkbox)
                self.check(visible_start + visible_checkbox_i)

    def upt(self, mouse: Mouse, timed_keys: list[int]) -> int:
        """
        Allows checking only one checkbox at a time.

        Args:
            mouse, timed keys
        Returns
            index of the active checkbox
        """

        self.upt_checkboxes(mouse)
        if mouse.hovered_obj == self or self._hovered_checkbox and timed_keys:
            self._move_with_keys(timed_keys)

        return self.clicked_i
