"""Class to create a grid of connected checkboxes."""

from typing import Self

from pygame import (
    Surface, Rect,
    K_LEFT, K_RIGHT, K_DOWN, K_UP, K_HOME, K_END,
)

from src.classes.clickable import LockedCheckbox
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import add_border
from src.obj_utils import UIElement
from src.type_utils import RectPos
from src.consts import WHITE, BG_LAYER


def checkbox_grid_get_rect(checkboxes: tuple[LockedCheckbox, ...], rect: Rect) -> None:
    """
    Gets the smallest rect covering all the elements in a checkbox grid.

    Args:
        checkboxes, rect
    """

    rects: list[Rect] = [checkbox.rect for checkbox in checkboxes]
    rects_xs: list[int] = [rect.x for rect in rects]
    rects_ys: list[int] = [rect.y for rect in rects]

    rect.topleft = (min(rects_xs), min(rects_ys))
    rect.size = (
        (max(rects_xs) + rects[0].w) - rect.x,
        (max(rects_ys) + rects[0].h) - rect.y,
    )


def checkbox_grid_move_with_keys(
        k_left: int, k_right: int, k_down: int, k_up: int,
        cols: int, num_checkboxes: int, clicked_i: int
) -> int:
    """
    Handles moving the selected checkbox with keys.

    Args:
        left key, right key, down key, up key,
        number of columns, number of checkboxes, clicked index
    Returns:
        clicked index
    """

    if k_left in KEYBOARD.timed:
        if KEYBOARD.is_ctrl_on:
            clicked_i -= clicked_i % cols
        else:
            clicked_i = max(clicked_i - 1, 0)

    if k_right in KEYBOARD.timed:
        if KEYBOARD.is_ctrl_on:
            row_start_i: int = clicked_i - clicked_i % cols
            clicked_i = min(row_start_i + cols - 1, num_checkboxes - 1)
        else:
            clicked_i = min(clicked_i + 1           , num_checkboxes - 1)

    if k_down in KEYBOARD.timed:
        if KEYBOARD.is_ctrl_on:
            clicked_i %= cols
        elif clicked_i - cols >= 0:
            clicked_i -= cols

    if k_up in KEYBOARD.timed:
        if KEYBOARD.is_ctrl_on:
            col_i: int = clicked_i % cols
            clicked_i = (num_checkboxes // cols) * cols + col_i
            if clicked_i >= num_checkboxes:
                clicked_i -= cols
        elif clicked_i + cols < num_checkboxes:
            clicked_i += cols

    if K_HOME in KEYBOARD.timed:
        clicked_i = 0
    if K_END  in KEYBOARD.timed:
        clicked_i = num_checkboxes - 1

    return clicked_i


def checkbox_grid_upt_checkboxes(
        checkboxes: tuple[LockedCheckbox, ...], hovered_checkbox: LockedCheckbox | None
) -> tuple[LockedCheckbox | None, bool]:
    """
    Leaves the previous hovered checkbox and updates the current one.

    Args:
        checkboxes, hovered checkbox
    Returns:
        hovered checkbox, checked flag
    """

    new_hovered_checkbox: LockedCheckbox | None = None
    did_check: bool = False

    if MOUSE.hovered_obj in checkboxes:
        assert isinstance(MOUSE.hovered_obj, LockedCheckbox)
        new_hovered_checkbox = MOUSE.hovered_obj

    if new_hovered_checkbox != hovered_checkbox and hovered_checkbox is not None:
        hovered_checkbox.leave()
    if new_hovered_checkbox is not None:
        did_check = new_hovered_checkbox.upt()

    return new_hovered_checkbox, did_check


class CheckboxGrid(UIElement):
    """Class to create a grid of connected checkboxes."""

    __slots__ = (
        "_init_pos", "_cols", "_increment_x", "_increment_y",
        "checkboxes", "_hovered_checkbox", "rect",
        "clicked_i", "prev_clicked_i",
    )

    def __init__(
            self: Self, pos: RectPos, info: tuple[tuple[Surface, str], ...],
            cols: int, should_invert_cols: bool, should_invert_rows: bool,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkboxes and finds the visible ones.

        Args:
            position, checkboxes images and hovering texts,
            number of columns, invert columns flag, invert rows flag,
            base layer (default = BG_LAYER)
        """

        super().__init__()

        self._init_pos: RectPos = pos

        self._cols: int = cols
        checkbox_w: int = info[0][0].get_width()
        checkbox_h: int = info[0][0].get_height()
        self._increment_x: int = -(checkbox_w + 10) if should_invert_cols else checkbox_w + 10
        self._increment_y: int = -(checkbox_h + 10) if should_invert_rows else checkbox_h + 10

        self.checkboxes: tuple[LockedCheckbox, ...] = ()
        self._hovered_checkbox: LockedCheckbox | None = None
        self.rect: Rect = Rect()

        self.clicked_i: int = 0
        self.prev_clicked_i: int = self.clicked_i

        self.hover_rects = (self.rect,)
        self.layer = base_layer

        self.checkboxes = tuple([
            LockedCheckbox(
                RectPos(
                    self._init_pos.x + (self._increment_x * (i %  self._cols)),
                    self._init_pos.y + (self._increment_y * (i // self._cols)),
                    self._init_pos.coord_type
                ),
                (img, add_border(img, WHITE)), hovering_text, self.layer
            )
            for i, (img, hovering_text) in enumerate(info)
        ])
        self.sub_objs = self.checkboxes
        checkbox_grid_get_rect(self.checkboxes, self.rect)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._hovered_checkbox = None

    def resize(self: Self) -> None:
        """Resizes the object."""

        checkbox_grid_get_rect(self.checkboxes, self.rect)

    def check(self: Self, clicked_i: int) -> None:
        """
        Checks a checkbox and unchecks the previous one if it exists, also sets the offset.

        Args:
            index
        """

        self.checkboxes[self.prev_clicked_i].set_checked(False)
        self.clicked_i = self.prev_clicked_i = clicked_i
        self.checkboxes[self.clicked_i     ].set_checked(True)

    def upt(self: Self) -> None:
        """
        Allows checking only one checkbox at a time.

        Refresh should be called when everything is updated.
        """

        did_check_hovered_checkbox: bool

        if (
            (MOUSE.hovered_obj == self or self._hovered_checkbox is not None) and
            KEYBOARD.timed != ()
        ):
            k_left: int  = K_LEFT  if self._increment_x > 0 else K_RIGHT
            k_right: int = K_RIGHT if self._increment_x > 0 else K_LEFT
            k_down: int  = K_DOWN  if self._increment_y < 0 else K_UP
            k_up: int    = K_UP    if self._increment_y < 0 else K_DOWN
            self.clicked_i = checkbox_grid_move_with_keys(
                k_left, k_right, k_down, k_up,
                self._cols, len(self.checkboxes), self.clicked_i
            )

        self._hovered_checkbox, did_check_hovered_checkbox = checkbox_grid_upt_checkboxes(
            self.checkboxes, self._hovered_checkbox
        )
        if did_check_hovered_checkbox:
            self.clicked_i = self.checkboxes.index(self._hovered_checkbox)
