"""Classes to create a locked checkbox or a grid of connected checkboxes."""

from math import ceil
from typing import Optional

import pygame as pg

from src.classes.clickable import LockedCheckbox

from src.utils import (
    Point, RectPos, ObjInfo, Mouse, Keyboard, add_border, rec_move_rect, rec_resize
)
from src.type_utils import XY, CheckboxInfo, LayeredBlitInfo
from src.consts import WHITE, NUM_VISIBLE_CHECKBOX_GRID_ROWS, BG_LAYER


class CheckboxGrid:
    """Class to create a grid of checkboxes (images must be of the same size)."""

    __slots__ = (
        "_init_pos", "_unresized_last_point", "num_cols", "_increment_x", "_increment_y", "layer",
        "checkboxes", "visible_checkboxes", "_hovered_checkbox", "clicked_i", "offset_y", "rect",
        "blit_sequence", "_win_w_ratio", "_win_h_ratio"
    )

    def __init__(
            self, pos: RectPos, info: list[CheckboxInfo], num_cols: int, should_invert_cols: bool,
            should_invert_rows: bool, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates all the checkboxes.

        Args:
            position, checkboxes images and hovering texts, columns, invert columns flag,
            invert rows flag, base layer (default = BG_LAYER)
        """

        checkbox_w: int
        checkbox_h: int
        self._win_w_ratio: float
        self._win_h_ratio: float

        self._init_pos: RectPos = pos
        self._unresized_last_point: Point = Point(self._init_pos.x, self._init_pos.y)

        self.num_cols: int = num_cols
        checkbox_w, checkbox_h = info[0][0].get_size()
        self._increment_x: int = -checkbox_w - 10 if should_invert_cols else checkbox_w + 10
        self._increment_y: int = -checkbox_h - 10 if should_invert_rows else checkbox_h + 10

        self.layer: int = base_layer

        self.checkboxes: list[LockedCheckbox] = []
        self.visible_checkboxes: list[LockedCheckbox] = []
        self._hovered_checkbox: Optional[LockedCheckbox] = None
        self.clicked_i: int = 0
        self.offset_y: int = 0
        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)

        self.blit_sequence: list[LayeredBlitInfo] = []
        self._win_w_ratio = self._win_h_ratio = 1

        self.set_grid(info, 0, 0)

    def get_hovering(self, mouse_xy: XY) -> bool:
        """
        Gets the hovering flag.

        Args:
            mouse xy
        Returns:
            hovering flag
        """

        return self.rect.collidepoint(mouse_xy)

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._hovered_checkbox = None

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        rects_x_coords: list[int]
        rects_y_coords: list[int]

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        rects_x_coords, rects_y_coords = [rect.x for rect in rects], [rect.y for rect in rects]
        self.rect.topleft = (min(rects_x_coords), min(rects_y_coords))
        self.rect.size = (
            max(rects_x_coords) + rects[0].w - self.rect.x,
            max(rects_y_coords) + rects[0].h - self.rect.y
        )

    @property
    def objs_info(self) -> list[ObjInfo]:
        """
        Gets the sub objects.

        Returns:
            objects info
        """

        return [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def _shift_visible_checkboxes(self, shift_i: int) -> None:
        """
        Shift all the visible checkboxes to unresized_last_point starting from an index.

        Args:
            index
        """

        unresized_x: int
        unresized_y: int
        increment_x: int
        increment_y: int
        win_w_ratio: float
        win_h_ratio: float
        i: int

        init_x: int = self._init_pos.x
        unresized_x, unresized_y = self._unresized_last_point.x, self._unresized_last_point.y
        num_cols: int = self.num_cols
        increment_x, increment_y = self._increment_x, self._increment_y
        checkboxes: list[LockedCheckbox] = self.checkboxes
        win_w_ratio, win_h_ratio = self._win_w_ratio, self._win_h_ratio

        visible_end_i: int = self.offset_y * num_cols + len(self.visible_checkboxes)
        for i in range(shift_i, visible_end_i):
            rec_move_rect(checkboxes[i], unresized_x, unresized_y, win_w_ratio, win_h_ratio)
            rec_resize([checkboxes[i]], win_w_ratio, win_h_ratio)

            if (i + 1) % num_cols == 0:
                unresized_x = init_x
                unresized_y += increment_y
            else:
                unresized_x += increment_x

        self._unresized_last_point.x, self._unresized_last_point.y = unresized_x, unresized_y

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

    def set_offset_y(self, offset_y: int) -> None:
        """
        Sets the row offset from the start.

        Args:
            y offset
        """

        rects_x_coords: list[int]
        rects_y_coords: list[int]

        self.offset_y = offset_y

        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        self._unresized_last_point.x = self._init_pos.x
        self._unresized_last_point.y = self._init_pos.y
        self._shift_visible_checkboxes(self.offset_y * self.num_cols)

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        rects_x_coords, rects_y_coords = [rect.x for rect in rects], [rect.y for rect in rects]
        self.rect.topleft = (min(rects_x_coords), min(rects_y_coords))
        self.rect.size = (
            max(rects_x_coords) + rects[0].w - self.rect.x,
            max(rects_y_coords) + rects[0].h - self.rect.y
        )

    def set_grid(self, info: list[CheckboxInfo], clicked_i: int, offset_y: int) -> None:
        """
        Clears the grid and creates a new one.

        Args:
            checkboxes images and hovering texts, clicked index, y offset
        """

        self.checkboxes = [
            LockedCheckbox(
                RectPos(0, 0, self._init_pos.coord_type),
                [img, add_border(img, WHITE)], hovering_text, self.layer
            )
            for img, hovering_text in info
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
        checkbox.hovering_text_label.set_text(hovering_text)

        if checkbox in self.visible_checkboxes:
            rec_resize([checkbox], self._win_w_ratio, self._win_h_ratio)

    def append(self, img: pg.Surface, hovering_text: str) -> None:
        """
        Appends a checkbox.

        Args:
            image, hovering text
        """

        rects_x_coords: list[int]
        rects_y_coords: list[int]

        init_point: Point = self._unresized_last_point
        checkbox: LockedCheckbox = LockedCheckbox(
            RectPos(init_point.x, init_point.y, self._init_pos.coord_type),
            [img, add_border(img, WHITE)], hovering_text, self.layer
        )
        self.checkboxes.append(checkbox)

        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        if checkbox in self.visible_checkboxes:
            rec_move_rect(
                checkbox, init_point.x, init_point.y,
                self._win_w_ratio, self._win_h_ratio
            )
            rec_resize([checkbox], self._win_w_ratio, self._win_h_ratio)

            if len(self.checkboxes) % self.num_cols == 0:
                init_point.x = self._init_pos.x
                init_point.y += self._increment_y
            else:
                init_point.x += self._increment_x

            rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
            rects_x_coords, rects_y_coords = [rect.x for rect in rects], [rect.y for rect in rects]
            self.rect.topleft = (min(rects_x_coords), min(rects_y_coords))
            self.rect.size = (
                max(rects_x_coords) + rects[0].w - self.rect.x,
                max(rects_y_coords) + rects[0].h - self.rect.y
            )

    def remove(self, remove_i: int, fallback_img: pg.Surface, fallback_text: str) -> None:
        """
        Removes a checkbox at an index.

        Args:
            index, fallback image, fallback text
        """

        rects_x_coords: list[int]
        rects_y_coords: list[int]

        if len(self.checkboxes) == 1:
            self.edit(0, fallback_img, fallback_text)

            return

        removed_checkbox: LockedCheckbox = self.checkboxes.pop(remove_i)
        num_above_rows: int = ceil(len(self.checkboxes) / self.num_cols) - self.offset_y
        should_dec_offset: bool = (
            self.offset_y != 0 and num_above_rows < NUM_VISIBLE_CHECKBOX_GRID_ROWS
        )

        if should_dec_offset:
            self.offset_y -= 1
        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        if should_dec_offset or remove_i < visible_start_i:
            self._unresized_last_point.x = self._init_pos.x
            self._unresized_last_point.y = self._init_pos.y
            self._shift_visible_checkboxes(visible_start_i)
        else:
            self._unresized_last_point.x = removed_checkbox.init_pos.x
            self._unresized_last_point.y = removed_checkbox.init_pos.y
            self._shift_visible_checkboxes(remove_i)

        if self.clicked_i > remove_i:
            self.clicked_i -= 1
        elif self.clicked_i == remove_i:
            self.clicked_i = min(self.clicked_i, len(self.checkboxes) - 1)
            self.checkboxes[self.clicked_i].img_i = 1
            self.checkboxes[self.clicked_i].is_checked = True

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        rects_x_coords, rects_y_coords = [rect.x for rect in rects], [rect.y for rect in rects]
        self.rect.topleft = (min(rects_x_coords), min(rects_y_coords))
        self.rect.size = (
            max(rects_x_coords) + rects[0].w - self.rect.x,
            max(rects_y_coords) + rects[0].h - self.rect.y
        )

    def _move_with_left_right(
            self, keyboard: Keyboard, clicked_i: int, k_sub_1: int, k_add_1: int
    ) -> int:
        """
        Moves the selected checkbox with left and right arrows.

        Args:
            keyboard, clicked index, left key, right key
        Returns:
            clicked index
        """

        if k_sub_1 in keyboard.timed:
            if keyboard.is_ctrl_on:
                clicked_i -= clicked_i % self.num_cols
            else:
                clicked_i = max(clicked_i - 1, 0)

        if k_add_1 in keyboard.timed:
            if keyboard.is_ctrl_on:
                row_start: int = clicked_i - clicked_i % self.num_cols
                clicked_i = min(row_start + self.num_cols - 1, len(self.checkboxes) - 1)
            else:
                clicked_i = min(clicked_i + 1, len(self.checkboxes) - 1)

        return clicked_i

    def _move_with_up_down(
            self, keyboard: Keyboard, clicked_i: int, k_sub_cols: int, k_add_cols: int
    ) -> int:
        """
        Moves the selected checkbox with up and down arrows.

        Args:
            keyboard, clicked index, down key, up key
        Returns:
            clicked index
        """

        if k_sub_cols in keyboard.timed:
            can_sub_cols: bool = clicked_i - self.num_cols >= 0
            if keyboard.is_ctrl_on:
                clicked_i %= self.num_cols
            elif can_sub_cols:
                clicked_i -= self.num_cols

        if k_add_cols in keyboard.timed:
            can_add_cols: bool = clicked_i + self.num_cols < len(self.checkboxes)
            if keyboard.is_ctrl_on:
                column: int = clicked_i % self.num_cols
                last_column: int = len(self.checkboxes) % self.num_cols
                num_rows: int = len(self.checkboxes) // self.num_cols
                row_i: int = num_rows if column < last_column else num_rows - 1

                clicked_i = row_i * self.num_cols + column
            elif can_add_cols:
                clicked_i += self.num_cols

        return clicked_i

    def _move_with_keys(self, keyboard: Keyboard) -> None:
        """
        Moves the selected checkbox with keys.

        Args:
            keyboard
        """

        k_sub_1: int
        k_add_1: int
        k_sub_cols: int
        k_add_cols: int

        new_clicked_i: int = self.clicked_i

        if self._increment_x > 0:
            k_sub_1, k_add_1 = pg.K_LEFT, pg.K_RIGHT
        else:
            k_sub_1, k_add_1 = pg.K_RIGHT, pg.K_LEFT

        if self._increment_y > 0:
            k_sub_cols, k_add_cols = pg.K_UP, pg.K_DOWN
        else:
            k_sub_cols, k_add_cols = pg.K_DOWN, pg.K_UP

        new_clicked_i = self._move_with_left_right(keyboard, new_clicked_i, k_sub_1, k_add_1)
        new_clicked_i = self._move_with_up_down(keyboard, new_clicked_i, k_sub_cols, k_add_cols)
        if pg.K_HOME in keyboard.timed:
            new_clicked_i = 0
        if pg.K_END in keyboard.timed:
            new_clicked_i = len(self.checkboxes) - 1

        if new_clicked_i != self.clicked_i:
            self.check(new_clicked_i)

    def upt_checkboxes(self, mouse: Mouse) -> None:
        """
        Updates the previous hovered and hovered checkboxes.

        Args:
            mouse
        """

        prev_hovered_checkbox: Optional[LockedCheckbox] = self._hovered_checkbox
        self._hovered_checkbox = (
            mouse.hovered_obj if mouse.hovered_obj in self.visible_checkboxes else None
        )

        if prev_hovered_checkbox is not None and prev_hovered_checkbox != self._hovered_checkbox:
            prev_hovered_checkbox.leave()
        if self._hovered_checkbox is not None:
            has_checked: bool = self._hovered_checkbox.upt(mouse)
            if has_checked:
                visible_start_i: int = self.offset_y * self.num_cols
                visible_checkbox_i: int = self.visible_checkboxes.index(self._hovered_checkbox)
                self.check(visible_start_i + visible_checkbox_i)

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> int:
        """
        Allows checking only one checkbox at a time.

        Args:
            mouse, keyboard
        Returns
            clicked index
        """

        self.upt_checkboxes(mouse)

        is_hovering: bool = mouse.hovered_obj == self or self._hovered_checkbox is not None
        if is_hovering and keyboard.timed != []:
            self._move_with_keys(keyboard)

        return self.clicked_i
