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


class CheckboxGrid:
    """Class to create a grid of connected checkboxes."""

    __slots__ = (
        "_init_pos", "_num_cols", "_increment_x", "_increment_y",
        "checkboxes", "_hovered_checkbox",
        "clicked_i", "prev_clicked_i", "rect",
        "hover_rects", "layer", "blit_sequence", "_win_w_ratio", "_win_h_ratio",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(
            self: Self, pos: RectPos, info: list[tuple[pg.Surface, str]],
            num_cols: int, should_invert_cols: bool, should_invert_rows: bool,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkboxes and finds the visible ones.

        Args:
            position, checkboxes images and hovering texts, columns, invert columns flag,
            invert rows flag, base layer (default = BG_LAYER)
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

        self.checkboxes: list[LockedCheckbox] = []
        self._hovered_checkbox: LockedCheckbox | None = None

        self.clicked_i: int = 0
        self.prev_clicked_i: int = self.clicked_i
        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)

        self.hover_rects: tuple[pg.Rect, ...] = (self.rect,)
        self.layer: int = base_layer
        self.blit_sequence: list[BlitInfo] = []
        self._win_w_ratio: float = 1
        self._win_h_ratio: float = 1

        for i, (img, hovering_text) in enumerate(info):
            init_x: int = self._init_pos.x + (self._increment_x * (i %  self._num_cols))
            init_y: int = self._init_pos.y + (self._increment_y * (i // self._num_cols))

            self.checkboxes.append(
                LockedCheckbox(
                    RectPos(init_x, init_y, self._init_pos.coord_type),
                    [img, add_border(img, WHITE)], hovering_text, self.layer
                )
            )

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.checkboxes]
        rects_xs: list[int] = [rect.x for rect in rects]
        rects_ys: list[int] = [rect.y for rect in rects]

        self.rect.topleft = (
            min(rects_xs),
            min(rects_ys),
        )
        self.rect.size = (
            (max(rects_xs) + rects[0].w) - self.rect.x,
            (max(rects_ys) + rects[0].h) - self.rect.y,
        )

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._hovered_checkbox = None

    def resize(self: Self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        self._win_w_ratio, self._win_h_ratio = win_w_ratio, win_h_ratio

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.checkboxes]
        rects_xs: list[int] = [rect.x for rect in rects]
        rects_ys: list[int] = [rect.y for rect in rects]

        self.rect.topleft = (
            min(rects_xs),
            min(rects_ys),
        )
        self.rect.size = (
            (max(rects_xs) + rects[0].w) - self.rect.x,
            (max(rects_ys) + rects[0].h) - self.rect.y,
        )

    @property
    def objs_info(self: Self) -> list[ObjInfo]:
        """
        Gets the sub objects info.

        Returns:
            objects info
        """

        return [ObjInfo(checkbox) for checkbox in self.checkboxes]

    def check(self: Self, clicked_i: int) -> None:
        """
        Checks a checkbox and unchecks the previous one if it exists, also sets the offset.

        Args:
            index
        """

        self.checkboxes[self.prev_clicked_i].set_checked(False)
        self.clicked_i = self.prev_clicked_i = clicked_i
        self.checkboxes[self.clicked_i     ].set_checked(True)

    def _handle_move_with_left_right(self: Self) -> None:
        """Handles moving the selected checkbox with left and right keys."""

        k_sub: int = K_LEFT
        k_add: int = K_RIGHT
        if self._increment_x < 0:
            k_sub, k_add = k_add, k_sub

        if k_sub in KEYBOARD.timed:
            if KEYBOARD.is_ctrl_on:
                self.clicked_i -= self.clicked_i % self._num_cols
            else:
                self.clicked_i = max(self.clicked_i - 1, 0)

        if k_add in KEYBOARD.timed:
            if KEYBOARD.is_ctrl_on:
                row_start: int = self.clicked_i - self.clicked_i % self._num_cols
                self.clicked_i = min(row_start + self._num_cols - 1, len(self.checkboxes) - 1)
            else:
                self.clicked_i = min(self.clicked_i + 1            , len(self.checkboxes) - 1)

    def _handle_move_with_up_down(self: Self) -> None:
        """Handles moving the selected checkbox with up and down keys."""

        k_sub: int = K_UP
        k_add: int = K_DOWN
        if self._increment_y < 0:
            k_sub, k_add = k_add, k_sub

        if k_sub in KEYBOARD.timed:
            can_sub_cols: bool = self.clicked_i - self._num_cols >= 0
            if KEYBOARD.is_ctrl_on:
                self.clicked_i %= self._num_cols
            elif can_sub_cols:
                self.clicked_i -= self._num_cols

        if k_add in KEYBOARD.timed:
            can_add_cols: bool = self.clicked_i + self._num_cols < len(self.checkboxes)
            if KEYBOARD.is_ctrl_on:
                col: int = self.clicked_i % self._num_cols
                last_col: int = len(self.checkboxes) % self._num_cols
                num_rows: int = len(self.checkboxes) // self._num_cols
                row_i: int = num_rows if col < last_col else num_rows - 1

                self.clicked_i = (row_i * self._num_cols) + col
            elif can_add_cols:
                self.clicked_i += self._num_cols

    def _upt_checkboxes(self: Self) -> None:
        """Leaves the previous hovered checkbox and updates the current one."""

        prev_hovered_checkbox: LockedCheckbox | None = self._hovered_checkbox
        self._hovered_checkbox = None
        if MOUSE.hovered_obj in self.checkboxes:
            assert isinstance(MOUSE.hovered_obj, LockedCheckbox)
            self._hovered_checkbox = MOUSE.hovered_obj

        if prev_hovered_checkbox is not None and self._hovered_checkbox != prev_hovered_checkbox:
            prev_hovered_checkbox.leave()
        if self._hovered_checkbox is not None:
            did_check: bool = self._hovered_checkbox.upt()
            if did_check:
                self.clicked_i = self.checkboxes.index(self._hovered_checkbox)

    def upt(self: Self) -> None:
        """
        Allows checking only one checkbox at a time.

        Refresh should be called when everything is updated.
        """

        if (
            (MOUSE.hovered_obj == self or self._hovered_checkbox is not None) and
            KEYBOARD.pressed != []
        ):
            self._handle_move_with_left_right()
            self._handle_move_with_up_down()
            if K_HOME in KEYBOARD.pressed:
                self.clicked_i = 0
            if K_END  in KEYBOARD.pressed:
                self.clicked_i = len(self.checkboxes) - 1

        self._upt_checkboxes()
