"""Class to create a grid of connected checkboxes."""

from math import ceil

import pygame as pg
from pygame.locals import *

from src.classes.clickable import LockedCheckbox
from src.classes.devices import Mouse, Keyboard

from src.utils import Point, RectPos, ObjInfo, add_border, rec_move_rect, rec_resize
from src.type_utils import XY, CheckboxInfo, BlitInfo
from src.consts import WHITE, NUM_VISIBLE_CHECKBOX_GRID_ROWS, BG_LAYER


class CheckboxGrid:
    """Class to create a grid of connected checkboxes."""

    __slots__ = (
        "_init_pos", "_unresized_last_point", "num_cols", "_increment_x", "_increment_y", "layer",
        "checkboxes", "visible_checkboxes", "_hovered_checkbox", "clicked_i", "prev_clicked_i",
        "offset_y", "rect", "blit_sequence", "_win_w_ratio", "_win_h_ratio"
    )

    def __init__(
            self, pos: RectPos, info: list[CheckboxInfo], num_cols: int, should_invert_cols: bool,
            should_invert_rows: bool, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkboxes and finds the visible ones.

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
        self._increment_x: int = -(checkbox_w + 10) if should_invert_cols else checkbox_w + 10
        self._increment_y: int = -(checkbox_h + 10) if should_invert_rows else checkbox_h + 10

        self.layer: int = base_layer

        self.checkboxes: list[LockedCheckbox] = []
        self.visible_checkboxes: list[LockedCheckbox] = []
        self._hovered_checkbox: LockedCheckbox | None = None

        self.clicked_i: int = 0
        self.prev_clicked_i: int = self.clicked_i
        self.offset_y: int = 0
        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)

        self.blit_sequence: list[BlitInfo] = []
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

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._hovered_checkbox = None

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        rects_x_coords: list[int] = [rect.x for rect in rects]
        rects_y_coords: list[int] = [rect.y for rect in rects]

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
        Shift the visible checkboxes to unresized_last_point starting from an index.

        Args:
            index
        """

        i: int

        visible_end_i: int = self.offset_y * self.num_cols + len(self.visible_checkboxes)

        init_x: int = self._init_pos.x
        unresized_x: int = self._unresized_last_point.x
        unresized_y: int = self._unresized_last_point.y

        num_cols: int = self.num_cols
        increment_x: int = self._increment_x
        increment_y: int = self._increment_y

        checkboxes: list[LockedCheckbox] = self.checkboxes
        win_w_ratio: float = self._win_w_ratio
        win_h_ratio: float = self._win_h_ratio

        for i in range(shift_i, visible_end_i):
            rec_move_rect(checkboxes[i], unresized_x, unresized_y, win_w_ratio, win_h_ratio)
            rec_resize([checkboxes[i]], win_w_ratio, win_h_ratio)

            if (i + 1) % num_cols == 0:
                unresized_x = init_x
                unresized_y += increment_y
            else:
                unresized_x += increment_x

        self._unresized_last_point.x, self._unresized_last_point.y = unresized_x, unresized_y

    def set_offset_y(self, offset_y: int) -> None:
        """
        Sets the row offset.

        Args:
            y offset
        """

        self.offset_y = offset_y

        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        self._unresized_last_point.x = self._init_pos.x
        self._unresized_last_point.y = self._init_pos.y
        self._shift_visible_checkboxes(visible_start_i)

    def check(self, clicked_i: int) -> None:
        """
        Checks a checkbox and unchecks the previous one if it exists, also sets the offset.

        Args:
            index
        """

        self.checkboxes[self.clicked_i].img_i = 0
        self.checkboxes[self.clicked_i].is_checked = False
        self.clicked_i = self.prev_clicked_i = clicked_i
        self.checkboxes[self.clicked_i].img_i = 1
        self.checkboxes[self.clicked_i].is_checked = True

        clicked_row: int = self.clicked_i // self.num_cols
        if clicked_row < self.offset_y:
            self.set_offset_y(clicked_row)
        elif clicked_row >= self.offset_y + NUM_VISIBLE_CHECKBOX_GRID_ROWS:
            self.set_offset_y(clicked_row - NUM_VISIBLE_CHECKBOX_GRID_ROWS + 1)

    def set_grid(self, info: list[CheckboxInfo], clicked_i: int, offset_y: int) -> None:
        """
        Modifies the grid, sets clicked checkbox index and row offset.

        The second image of a checkbox is the first one with a white border

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

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
        rects_x_coords: list[int] = [rect.x for rect in rects]
        rects_y_coords: list[int] = [rect.y for rect in rects]

        self.rect.topleft = (min(rects_x_coords), min(rects_y_coords))
        self.rect.size = (
            max(rects_x_coords) + rects[0].w - self.rect.x,
            max(rects_y_coords) + rects[0].h - self.rect.y
        )

    def edit(self, edit_i: int, img: pg.Surface, hovering_text: str) -> None:
        """
        Edits a checkbox images and hovering text.

        Args:
            index, image, hovering text
        """

        checkbox: LockedCheckbox = self.checkboxes[edit_i]
        checkbox.init_imgs = checkbox.imgs = [img, add_border(img, WHITE)]
        checkbox.hovering_text_label.set_text(hovering_text)

        if checkbox in self.visible_checkboxes:
            rec_resize([checkbox], self._win_w_ratio, self._win_h_ratio)

    def add(self, img: pg.Surface, hovering_text: str) -> None:
        """
        Adds a checkbox.

        Args:
            image, hovering text
        """

        coord_type: str = self._init_pos.coord_type
        checkbox: LockedCheckbox = LockedCheckbox(
            RectPos(self._unresized_last_point.x, self._unresized_last_point.y, coord_type),
            [img, add_border(img, WHITE)], hovering_text, self.layer
        )
        self.checkboxes.append(checkbox)

        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        if checkbox in self.visible_checkboxes:
            rec_move_rect(
                checkbox, self._unresized_last_point.x, self._unresized_last_point.y,
                self._win_w_ratio, self._win_h_ratio
            )
            rec_resize([checkbox], self._win_w_ratio, self._win_h_ratio)

            if len(self.checkboxes) % self.num_cols == 0:
                self._unresized_last_point.x = self._init_pos.x
                self._unresized_last_point.y += self._increment_y
            else:
                self._unresized_last_point.x += self._increment_x

            rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
            rects_x_coords: list[int] = [rect.x for rect in rects]
            rects_y_coords: list[int] = [rect.y for rect in rects]

            self.rect.topleft = (min(rects_x_coords), min(rects_y_coords))
            self.rect.size = (
                max(rects_x_coords) + rects[0].w - self.rect.x,
                max(rects_y_coords) + rects[0].h - self.rect.y
            )

    def remove(self, remove_i: int, fallback_img: pg.Surface, fallback_text: str) -> None:
        """
        Removes at an index, if there's only one checkbox it will be edited with the fallback info.

        Args:
            index, fallback image, fallback text
        """

        if len(self.checkboxes) == 1:
            self.edit(0, fallback_img, fallback_text)

            return

        removed_checkbox: LockedCheckbox = self.checkboxes.pop(remove_i)
        num_above_rows: int = ceil(len(self.checkboxes) / self.num_cols) - self.offset_y
        should_dec_offset_y: bool = (
            self.offset_y != 0 and num_above_rows < NUM_VISIBLE_CHECKBOX_GRID_ROWS
        )

        if should_dec_offset_y:
            self.offset_y -= 1
        visible_start_i: int = self.offset_y * self.num_cols
        visible_end_i: int = visible_start_i + NUM_VISIBLE_CHECKBOX_GRID_ROWS * self.num_cols
        self.visible_checkboxes = self.checkboxes[visible_start_i:visible_end_i]

        if should_dec_offset_y or remove_i < visible_start_i:
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
        rects_x_coords: list[int] = [rect.x for rect in rects]
        rects_y_coords: list[int] = [rect.y for rect in rects]

        self.rect.topleft = (min(rects_x_coords), min(rects_y_coords))
        self.rect.size = (
            max(rects_x_coords) + rects[0].w - self.rect.x,
            max(rects_y_coords) + rects[0].h - self.rect.y
        )

    def _move_with_left_right(self, keyboard: Keyboard) -> None:
        """
        Moves the selected checkbox with left and right keys.

        Args:
            keyboard
        """

        k_sub: int
        k_add: int
        if self._increment_x < 0:
            k_sub, k_add = k_sub, k_add

        if k_sub in keyboard.timed:
            if keyboard.is_ctrl_on:
                self.clicked_i -= self.clicked_i % self.num_cols
            else:
                self.clicked_i = max(self.clicked_i - 1, 0)

        if k_add in keyboard.timed:
            if keyboard.is_ctrl_on:
                row_start: int = self.clicked_i - self.clicked_i % self.num_cols
                self.clicked_i = min(row_start + self.num_cols - 1, len(self.checkboxes) - 1)
            else:
                self.clicked_i = min(self.clicked_i + 1, len(self.checkboxes) - 1)

    def _move_with_up_down(self, keyboard: Keyboard) -> None:
        """
        Moves the selected checkbox with up and down keys.

        Args:
            keyboard
        """

        k_sub: int = K_UP
        k_add: int = K_DOWN
        if self._increment_y < 0:
            k_sub, k_add = k_add, k_sub

        if k_sub in keyboard.timed:
            can_sub_cols: bool = self.clicked_i - self.num_cols >= 0
            if keyboard.is_ctrl_on:
                self.clicked_i %= self.num_cols
            elif can_sub_cols:
                self.clicked_i -= self.num_cols

        if k_add in keyboard.timed:
            can_add_cols: bool = self.clicked_i + self.num_cols < len(self.checkboxes)
            if keyboard.is_ctrl_on:
                col: int = self.clicked_i % self.num_cols
                last_col: int = len(self.checkboxes) % self.num_cols
                num_rows: int = len(self.checkboxes) // self.num_cols
                row_i: int = num_rows if col < last_col else num_rows - 1

                self.clicked_i = row_i * self.num_cols + col
            elif can_add_cols:
                self.clicked_i += self.num_cols

    def _move_with_keys(self, keyboard: Keyboard) -> None:
        """
        Moves the selected checkbox with the keyboard.

        Args:
            keyboard
        """

        self._move_with_left_right(keyboard)
        self._move_with_up_down(keyboard)
        if K_HOME in keyboard.pressed:
            self.clicked_i = 0
        if K_END in keyboard.pressed:
            self.clicked_i = len(self.checkboxes) - 1

    def upt_checkboxes(self, mouse: Mouse) -> None:
        """
        Leaves the previous hovered checkbox and updates the current one.

        Args:
            mouse
        """

        prev_hovered_checkbox: LockedCheckbox | None = self._hovered_checkbox
        self._hovered_checkbox = None
        if mouse.hovered_obj in self.visible_checkboxes:
            self._hovered_checkbox = mouse.hovered_obj

        if prev_hovered_checkbox is not None and self._hovered_checkbox != prev_hovered_checkbox:
            prev_hovered_checkbox.leave()
        if self._hovered_checkbox is not None:
            did_check: bool = self._hovered_checkbox.upt(mouse)
            if did_check:
                visible_start_i: int = self.offset_y * self.num_cols
                visible_checkbox_i: int = self.visible_checkboxes.index(self._hovered_checkbox)
                self.clicked_i = visible_start_i + visible_checkbox_i

    def refresh(self) -> bool:
        """
        Refreshes the previous and current clicked checkboxes.

        Returns:
            clicked index changed flag
        """

        did_change: bool = self.clicked_i != self.prev_clicked_i
        if did_change:
            new_clicked_i: int = self.clicked_i
            self.clicked_i = min(self.prev_clicked_i, len(self.checkboxes) - 1)
            self.check(new_clicked_i)

        return did_change

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Allows checking only one checkbox at a time.

        Refresh should be called when everything is updated.

        Args:
            mouse, keyboard
        """

        self.upt_checkboxes(mouse)

        is_hovering: bool = mouse.hovered_obj == self or self._hovered_checkbox is not None
        if is_hovering and keyboard.pressed != []:
            self._move_with_keys(keyboard)
