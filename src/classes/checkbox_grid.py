"""Class to create a grid of connected checkboxes."""

from typing import Self

import pygame as pg
from pygame.locals import *

from src.classes.clickable import LockedCheckbox
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import add_border
from src.obj_utils import ObjInfo
from src.type_utils import BlitInfo, RectPos
from src.consts import WHITE, BG_LAYER


def checkbox_grid_get_rect(checkboxes: tuple[LockedCheckbox, ...], rect: pg.Rect) -> None:
    """
    Gets the rect covering all the elements in a checkbox grid.

    Args:
        checkboxes, rect
    """

    rects: list[pg.Rect] = [checkbox.rect for checkbox in checkboxes]
    rects_xs: list[int] = [rect.x for rect in rects]
    rects_ys: list[int] = [rect.y for rect in rects]

    rect.topleft = (min(rects_xs), min(rects_ys))
    rect.size = (
        (max(rects_xs) + rects[0].w) - rect.x,
        (max(rects_ys) + rects[0].h) - rect.y,
    )


def checkbox_grid_move_with_keys(
        k_left: int, k_right: int, k_down: int, k_up: int,
        num_cols: int, num_checkboxes: int, clicked_i: int
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
            clicked_i -= clicked_i % num_cols
        else:
            clicked_i = max(clicked_i - 1, 0)

    if k_right in KEYBOARD.timed:
        if KEYBOARD.is_ctrl_on:
            row_start: int = clicked_i - clicked_i % num_cols
            clicked_i = min(row_start + num_cols - 1, num_checkboxes - 1)
        else:
            clicked_i = min(clicked_i + 1           , num_checkboxes - 1)

    if k_down in KEYBOARD.timed:
        if KEYBOARD.is_ctrl_on:
            clicked_i %= num_cols
        elif clicked_i - num_cols >= 0:
            clicked_i -= num_cols

    if k_up in KEYBOARD.timed:
        if KEYBOARD.is_ctrl_on:
            col: int = clicked_i % num_cols
            clicked_i = (num_checkboxes // num_cols) * num_cols + col
            if clicked_i >= num_checkboxes:
                clicked_i -= num_cols
        elif clicked_i + num_cols < num_checkboxes:
            clicked_i += num_cols

    if K_HOME in KEYBOARD.pressed:
        clicked_i = 0
    if K_END  in KEYBOARD.pressed:
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


class CheckboxGrid:
    """Class to create a grid of connected checkboxes."""

    __slots__ = (
        "_init_pos", "_num_cols", "_increment_x", "_increment_y",
        "checkboxes", "_hovered_checkbox", "rect",
        "clicked_i", "prev_clicked_i",
        "hover_rects", "layer", "blit_sequence",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(
            self: Self, pos: RectPos, info: tuple[tuple[pg.Surface, str], ...],
            num_cols: int, should_invert_cols: bool, should_invert_rows: bool,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkboxes and finds the visible ones.

        Args:
            position, checkboxes images and hovering texts,
            number of columns, invert columns flag, invert rows flag,
            base layer (default = BG_LAYER)
        """

        i: int
        img: pg.Surface
        hovering_text: str

        self._init_pos: RectPos = pos

        self._num_cols: int = num_cols
        checkbox_w: int = info[0][0].get_width()
        checkbox_h: int = info[0][0].get_height()
        self._increment_x: int = -(checkbox_w + 10) if should_invert_cols else checkbox_w + 10
        self._increment_y: int = -(checkbox_h + 10) if should_invert_rows else checkbox_h + 10

        self.checkboxes: tuple[LockedCheckbox, ...] = ()
        self._hovered_checkbox: LockedCheckbox | None = None
        self.rect: pg.Rect = pg.Rect()

        self.clicked_i: int = 0
        self.prev_clicked_i: int = self.clicked_i

        self.hover_rects: tuple[pg.Rect, ...] = (self.rect,)
        self.layer: int = base_layer
        self.blit_sequence: list[BlitInfo] = []

        for i, (img, hovering_text) in enumerate(info):
            init_x: int = self._init_pos.x + (self._increment_x * (i %  self._num_cols))
            init_y: int = self._init_pos.y + (self._increment_y * (i // self._num_cols))

            self.checkboxes += (
                LockedCheckbox(
                    RectPos(init_x, init_y, self._init_pos.coord_type),
                    (img, add_border(img, WHITE)), hovering_text, self.layer
                )
            ,)
        checkbox_grid_get_rect(self.checkboxes, self.rect)

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._hovered_checkbox = None

    def resize(self: Self) -> None:
        """Resizes the object."""

        checkbox_grid_get_rect(self.checkboxes, self.rect)

    @property
    def objs_info(self: Self) -> tuple[ObjInfo, ...]:
        """
        Gets the sub objects info.

        Returns:
            objects info
        """

        return tuple([ObjInfo(checkbox) for checkbox in self.checkboxes])

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
            KEYBOARD.pressed != ()
        ):
            k_left: int  = pg.K_LEFT  if self._increment_x > 0 else pg.K_RIGHT
            k_right: int = pg.K_RIGHT if self._increment_x > 0 else pg.K_LEFT
            k_down: int  = pg.K_DOWN  if self._increment_y < 0 else pg.K_UP
            k_up: int    = pg.K_UP    if self._increment_y < 0 else pg.K_DOWN
            self.clicked_i = checkbox_grid_move_with_keys(
                k_left, k_right, k_down, k_up,
                self._num_cols, len(self.checkboxes), self.clicked_i
            )

        self._hovered_checkbox, did_check_hovered_checkbox = checkbox_grid_upt_checkboxes(
            self.checkboxes, self._hovered_checkbox
        )
        if did_check_hovered_checkbox:
            self.clicked_i = self.checkboxes.index(self._hovered_checkbox)
