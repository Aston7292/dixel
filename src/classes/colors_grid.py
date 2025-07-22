"""Class to create a grid of connected checkboxes for unique colors."""

import pygame as pg
from pygame.locals import *
from math import ceil
from typing import Final

from src.classes.clickable import LockedCheckbox
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import UIElement, RectPos, ObjInfo, add_border, rec_move_rect
from src.type_utils import HexColor, BlitInfo
from src.consts import WHITE, HEX_BLACK, DARKER_GRAY, BG_LAYER


_COLOR_IMG: Final[pg.Surface] = pg.Surface((32, 32))
NUM_COLS: Final[int] = 5
NUM_VISIBLE_ROWS: Final[int] = 10


def _get_color_checkbox_info(hex_color: HexColor) -> tuple[list[pg.Surface], str]:
    """
    Creates the checkbox info for a color.

    Args:
        hexadecimal color
    Returns:
        checkbox images and hovering text
    """

    hex_color = "#" + hex_color
    color: pg.Color = pg.Color(hex_color)

    _COLOR_IMG.fill(color)
    img_off: pg.Surface = add_border(_COLOR_IMG, DARKER_GRAY)
    img_on: pg.Surface  = add_border(_COLOR_IMG, WHITE      )

    return [img_off, img_on], f"{color[:3]}\n{hex_color}"


class ColorsGrid:
    """Class to create a grid of connected checkboxes for unique colors."""

    __slots__ = (
        "_init_pos",
        "colors", "visible_checkboxes", "_hovered_checkbox",
        "clicked_i", "offset_y","_prev_clicked_i", "rect",
        "hover_rects", "layer", "blit_sequence", "_win_w_ratio", "_win_h_ratio",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the checkboxes for the visible colors.

        Args:
            position, base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos

        self.colors: list[HexColor] = [HEX_BLACK]
        self.visible_checkboxes: list[LockedCheckbox] = []
        self._hovered_checkbox: LockedCheckbox | None = None

        self.clicked_i: int = 0
        self.offset_y: int = 0
        self._prev_clicked_i: int = self.clicked_i
        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)

        self.hover_rects: list[pg.Rect] = [self.rect]
        self.layer: int = base_layer
        self.blit_sequence: list[BlitInfo] = []
        self._win_w_ratio: float = 1
        self._win_h_ratio: float = 1

        self.set_grid(self.colors, 0, 0)

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

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
    def objs_info(self) -> list[ObjInfo]:
        """
        Gets the sub objects info.

        Returns:
            objects info
        """

        return [ObjInfo(checkbox) for checkbox in self.visible_checkboxes]

    def _rec_resize(self, i: int) -> None:
        """
        Resizes the checkbox and its sub objects.

        Args:
            checkbox index
        """

        objs: list[UIElement] = [self.visible_checkboxes[i]]
        while objs != []:
            obj: UIElement = objs.pop()
            obj.resize(self._win_w_ratio, self._win_h_ratio)
            objs.extend([info.obj for info in obj.objs_info])

    def _move_section_to_last(self, start_i: int) -> None:
        """
        Moves a section of the visible checkboxes to the last point.

        Args:
            start index
        """

        i: int

        increment_x: int = -_COLOR_IMG.get_width()  - 10
        increment_y: int = -_COLOR_IMG.get_height() - 10
        for i in range(start_i, len(self.visible_checkboxes)):
            init_x: int = self._init_pos.x + (increment_x * (i %  NUM_COLS))
            init_y: int = self._init_pos.y + (increment_y * (i // NUM_COLS))

            rec_move_rect(
                self.visible_checkboxes[i], init_x, init_y,
                self._win_w_ratio, self._win_h_ratio
            )
            self._rec_resize(i)

    def set_offset_y(self, offset_y: int) -> None:
        """
        Sets the row offset, and refreshes the visible checkboxes.

        Args:
            y offset
        """

        self.offset_y = offset_y

        visible_start_i: int =  self.offset_y * NUM_COLS
        visible_end_i: int   = (self.offset_y + NUM_VISIBLE_ROWS) * NUM_COLS
        self.visible_checkboxes = [
            LockedCheckbox(
                RectPos(0, 0, self._init_pos.coord_type),
                *_get_color_checkbox_info(color)
            )
            for color in self.colors[visible_start_i:visible_end_i]
        ]

        visible_end_i = visible_start_i + len(self.visible_checkboxes)
        if visible_start_i <= self.clicked_i < visible_end_i:
            visible_clicked_i: int = self.clicked_i - visible_start_i
            self.visible_checkboxes[visible_clicked_i].img_i = 1
            self.visible_checkboxes[visible_clicked_i].is_checked = True
        self._move_section_to_last(0)

    def set_grid(self, hex_colors: list[HexColor], clicked_i: int, offset_y: int) -> None:
        """
        Modifies the grid, sets clicked checkbox index and row offset.

        Args:
            hexadecimal colors, clicked index, y offset
        """

        self.colors = hex_colors
        self.clicked_i = self._prev_clicked_i = clicked_i
        self.set_offset_y(offset_y)  # Also refreshes visible checkboxes

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
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

    def check(self, clicked_i: int) -> None:
        """
        Checks a checkbox and unchecks the previous one, also sets the offset.

        Args:
            index
        """

        self.clicked_i = clicked_i
        visible_start_i: int = self.offset_y * NUM_COLS
        visible_end_i: int = visible_start_i + len(self.visible_checkboxes)

        if   self.clicked_i <  visible_start_i:
            self.set_offset_y(self.clicked_i // NUM_COLS)
        elif self.clicked_i >= visible_end_i:
            clicked_row: int = self.clicked_i // NUM_COLS
            self.set_offset_y(clicked_row - NUM_VISIBLE_ROWS + 1)
        elif visible_start_i <= self.clicked_i < visible_end_i:
            if visible_start_i <= self._prev_clicked_i < visible_end_i:
                visible_prev_clicked_i: int = self._prev_clicked_i - visible_start_i
                self.visible_checkboxes[visible_prev_clicked_i].img_i = 0
                self.visible_checkboxes[visible_prev_clicked_i].is_checked = False

            visible_clicked_i: int = self.clicked_i - visible_start_i
            self.visible_checkboxes[visible_clicked_i].img_i = 1
            self.visible_checkboxes[visible_clicked_i].is_checked = True

        self._prev_clicked_i = self.clicked_i

    def edit(self, edit_i: int, hex_color: HexColor) -> None:
        """
        Edits a checkbox images and hovering text.

        Args:
            index, hexadecimal color
        """

        imgs: list[pg.Surface]
        hovering_text: str

        self.colors[edit_i] = hex_color

        visible_start_i: int = self.offset_y * NUM_COLS
        visible_end_i: int = visible_start_i + len(self.visible_checkboxes)
        if visible_start_i <= edit_i < visible_end_i:
            imgs, hovering_text = _get_color_checkbox_info(hex_color)

            checkbox: LockedCheckbox = self.visible_checkboxes[edit_i - visible_start_i]
            checkbox.init_imgs = checkbox.imgs = imgs
            checkbox.hovering_text_label.set_text(hovering_text)
            self._rec_resize(edit_i)

    def add(self, hex_color: HexColor) -> bool:
        """
        Adds a checkbox.

        Args:
            hexadecimal color
        Returns:
            success flag
        """

        if hex_color in self.colors:
            return False

        self.colors.append(hex_color)

        visible_start_i: int =  self.offset_y                                   * NUM_COLS
        visible_end_i: int   = (self.offset_y + NUM_VISIBLE_ROWS) * NUM_COLS
        if visible_start_i <= (len(self.colors) - 1) < visible_end_i:
            self.visible_checkboxes.append(
                LockedCheckbox(
                    RectPos(0, 0, self._init_pos.coord_type),
                    *_get_color_checkbox_info(hex_color)
                )
            )
            self._move_section_to_last(len(self.visible_checkboxes) - 1)

            rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
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

        return True

    def remove(self, remove_i: int) -> None:
        """
        Removes at an index, if there's only one checkbox it will be edited to black.

        Args:
            index
        """

        if len(self.colors) == 1:
            self.edit(0, HEX_BLACK)
            return

        self.colors.pop(remove_i)
        self.colors = self.colors or [HEX_BLACK]
        if self.clicked_i > remove_i:
            self.check(self.clicked_i - 1)
        elif self.clicked_i == remove_i:
            clicked_i: int = min(self.clicked_i, len(self.colors) - 1)
            self.check(clicked_i)

        num_above_rows: int = ceil(len(self.colors) / NUM_COLS) - self.offset_y
        if self.offset_y != 0 and num_above_rows < NUM_VISIBLE_ROWS:
            self.offset_y -= 1
        self.set_offset_y(self.offset_y)  # Also refreshes visible checkboxes

        rects: list[pg.Rect] = [checkbox.rect for checkbox in self.visible_checkboxes]
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

    def _handle_shortcuts(self) -> None:
        """Selects a color if the user presses ctrl+c+dimension."""

        k: int

        num_shortcuts: int = min(len(self.colors), 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                self.clicked_i = k - K_1

    def _move_with_left_right(self) -> None:
        """Moves the selected checkbox with left and right keys."""

        if K_RIGHT in KEYBOARD.timed:
            if KEYBOARD.is_ctrl_on:
                self.clicked_i -= self.clicked_i % NUM_COLS
            else:
                self.clicked_i = max(self.clicked_i - 1, 0)

        if K_LEFT in KEYBOARD.timed:
            if KEYBOARD.is_ctrl_on:
                row_start: int = self.clicked_i - self.clicked_i % NUM_COLS
                self.clicked_i = min(row_start + NUM_COLS - 1, len(self.colors) - 1)
            else:
                self.clicked_i = min(self.clicked_i + 1           , len(self.colors) - 1)

    def _move_with_up_down(self) -> None:
        """Moves the selected checkbox with up and down keys."""

        if K_DOWN in KEYBOARD.timed:
            can_sub_cols: bool = self.clicked_i - NUM_COLS >= 0
            if KEYBOARD.is_ctrl_on:
                self.clicked_i %= NUM_COLS
            elif can_sub_cols:
                self.clicked_i -= NUM_COLS

        if K_UP in KEYBOARD.timed:
            can_add_cols: bool = self.clicked_i + NUM_COLS < len(self.colors)
            if KEYBOARD.is_ctrl_on:
                col: int = self.clicked_i % NUM_COLS
                last_col: int = len(self.colors) % NUM_COLS
                num_rows: int = len(self.colors) // NUM_COLS
                row_i: int = num_rows if col < last_col else num_rows - 1

                self.clicked_i = (row_i * NUM_COLS) + col
            elif can_add_cols:
                self.clicked_i += NUM_COLS

    def upt_checkboxes(self) -> None:
        """Leaves the previous hovered checkbox and updates the current one."""

        prev_hovered_checkbox: LockedCheckbox | None = self._hovered_checkbox
        self._hovered_checkbox = None
        if (
            isinstance(MOUSE.hovered_obj, LockedCheckbox) and
            MOUSE.hovered_obj in self.visible_checkboxes
        ):
            self._hovered_checkbox = MOUSE.hovered_obj

        if prev_hovered_checkbox is not None and self._hovered_checkbox != prev_hovered_checkbox:
            prev_hovered_checkbox.leave()
        if self._hovered_checkbox is not None:
            did_check: bool = self._hovered_checkbox.upt()
            if did_check:
                visible_start_i: int = self.offset_y * NUM_COLS
                visible_checkbox_i: int = self.visible_checkboxes.index(self._hovered_checkbox)
                self.clicked_i = visible_start_i + visible_checkbox_i

    def upt(self) -> None:
        """Allows checking only one checkbox at a time."""

        if KEYBOARD.is_ctrl_on and K_c in KEYBOARD.pressed:
            self._handle_shortcuts()

        self.upt_checkboxes()

        is_hovering: bool = MOUSE.hovered_obj == self or self._hovered_checkbox is not None
        if is_hovering and KEYBOARD.pressed != []:
            self._move_with_left_right()
            self._move_with_up_down()
            if K_HOME in KEYBOARD.pressed:
                self.clicked_i = 0
            if K_END  in KEYBOARD.pressed:
                self.clicked_i = len(self.colors) - 1

        if self.clicked_i != self._prev_clicked_i:
            self.check(self.clicked_i)
