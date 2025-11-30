"""Class to create a grid of connected checkboxes for unique colors."""

from math import ceil
from typing import Self, Final

import pygame as pg
from pygame.locals import *

from src.classes.checkbox_grid import (
    checkbox_grid_get_rect, checkbox_grid_move_with_keys, checkbox_grid_upt_checkboxes
)
from src.classes.clickable import LockedCheckbox
from src.classes.devices import MOUSE, KEYBOARD

from src.utils import add_border
from src.obj_utils import UIElement, ObjInfo, rec_move_rect
from src.type_utils import HexColor, BlitInfo, RectPos
from src.consts import WHITE, DARKER_GRAY, HEX_BLACK, BG_LAYER


_COLOR_IMG: Final[pg.Surface] = pg.Surface((32, 32))
NUM_COLS: Final[int] = 5
NUM_VISIBLE_ROWS: Final[int] = 10


def _get_color_checkbox_info(hex_color: HexColor) -> tuple[tuple[pg.Surface, ...], str]:
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

    return (
        (add_border(_COLOR_IMG, DARKER_GRAY), add_border(_COLOR_IMG, WHITE)),
        f"{color[:3]}\n{hex_color}"
    )


class ColorsGrid:
    """Class to create a grid of connected checkboxes for unique colors."""

    __slots__ = (
        "_init_pos",
        "colors", "visible_checkboxes", "_hovered_checkbox", "rect",
        "clicked_i", "offset_y", "prev_clicked_i",
        "hover_rects", "layer", "blit_sequence",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(self: Self, pos: RectPos, base_layer: int = BG_LAYER) -> None:
        """
        Creates the checkboxes for the visible colors.

        Args:
            position, base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos

        self.colors: list[HexColor] = []
        self.visible_checkboxes: tuple[LockedCheckbox, ...] = ()
        self._hovered_checkbox: LockedCheckbox | None = None
        self.rect: pg.Rect = pg.Rect(self._init_pos.x, self._init_pos.y, 0, 0)

        self.clicked_i: int = 0
        self.offset_y: int = 0
        self.prev_clicked_i: int = self.clicked_i

        self.hover_rects: tuple[pg.Rect, ...] = (self.rect,)
        self.layer: int = base_layer
        self.blit_sequence: list[BlitInfo] = []

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._hovered_checkbox = None

    def resize(self: Self) -> None:
        """Resizes the object."""

        checkbox_grid_get_rect(self.visible_checkboxes, self.rect)

    @property
    def objs_info(self: Self) -> tuple[ObjInfo, ...]:
        """
        Gets the sub objects info.

        Returns:
            objects info
        """

        return tuple([ObjInfo(checkbox) for checkbox in self.visible_checkboxes])

    def _move_section_to_last(self: Self, start_i: int) -> None:
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

            rec_move_rect(self.visible_checkboxes[i], init_x, init_y)
            checkbox_objs: list[UIElement] = [self.visible_checkboxes[i]]
            while checkbox_objs != []:
                obj: UIElement = checkbox_objs.pop()
                obj.resize()
                checkbox_objs.extend([info.obj for info in obj.objs_info])

    def set_offset_y(self: Self, offset_y: int) -> None:
        """
        Sets the row offset, and refreshes the visible checkboxes.

        Args:
            y offset
        """

        self.offset_y = offset_y

        visible_start_i: int =  self.offset_y                     * NUM_COLS
        visible_end_i: int   = (self.offset_y + NUM_VISIBLE_ROWS) * NUM_COLS
        self.visible_checkboxes = tuple([
            LockedCheckbox(
                RectPos(0, 0, self._init_pos.coord_type),
                *_get_color_checkbox_info(color)
            )
            for color in self.colors[visible_start_i:visible_end_i]
        ])

        visible_end_i = visible_start_i + len(self.visible_checkboxes)
        if visible_start_i <= self.clicked_i < visible_end_i:
            rel_clicked_i: int = self.clicked_i - visible_start_i
            self.visible_checkboxes[rel_clicked_i].set_checked(True)

        self._move_section_to_last(start_i=0)

    def set_info(self: Self, hex_colors: list[HexColor], clicked_i: int, offset_y: int) -> None:
        """
        Modifies the grid, sets clicked checkbox index and row offset.

        Args:
            hexadecimal colors, clicked index, y offset
        """

        self.colors = hex_colors
        self.clicked_i = clicked_i
        self.set_offset_y(offset_y)
        checkbox_grid_get_rect(self.visible_checkboxes, self.rect)

    def check(self: Self, clicked_i: int) -> None:
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
            if visible_start_i <= self.prev_clicked_i < visible_end_i:
                rel_prev_clicked_i: int = self.prev_clicked_i - visible_start_i
                self.visible_checkboxes[rel_prev_clicked_i].set_checked(False)

            rel_clicked_i: int = self.clicked_i - visible_start_i
            self.visible_checkboxes[rel_clicked_i].set_checked(True)

        self.prev_clicked_i = self.clicked_i

    def try_add(self: Self, hex_color: HexColor) -> None:
        """
        Adds a color if it's not present.

        Args:
            hexadecimal color
        """

        if hex_color not in self.colors:
            self.colors.append(hex_color)

            visible_start_i: int =  self.offset_y                     * NUM_COLS
            visible_end_i: int   = (self.offset_y + NUM_VISIBLE_ROWS) * NUM_COLS
            if visible_start_i <= (len(self.colors) - 1) < visible_end_i:
                self.visible_checkboxes += (
                    LockedCheckbox(
                        RectPos(0, 0, self._init_pos.coord_type),
                        *_get_color_checkbox_info(hex_color)
                    )
                ,)
                self._move_section_to_last(start_i=len(self.visible_checkboxes) - 1)
                checkbox_grid_get_rect(self.visible_checkboxes, self.rect)

    def edit(self: Self, edit_i: int, hex_color: HexColor) -> None:
        """
        Edits a checkbox images and hovering text.

        Args:
            index, hexadecimal color
        """

        imgs: tuple[pg.Surface, ...]
        hovering_text: str

        if hex_color not in self.colors:
            self.colors[edit_i] = hex_color

            visible_start_i: int = self.offset_y * NUM_COLS
            visible_end_i: int = visible_start_i + len(self.visible_checkboxes)
            if visible_start_i <= edit_i < visible_end_i:
                imgs, hovering_text = _get_color_checkbox_info(hex_color)

                rel_edit_i: int = edit_i - visible_start_i
                self.visible_checkboxes[rel_edit_i].init_imgs = imgs
                self.visible_checkboxes[rel_edit_i].set_unscaled_imgs(imgs)
                self.visible_checkboxes[rel_edit_i].hovering_text_label.set_text(hovering_text)
                self.visible_checkboxes[rel_edit_i].hovering_text_label.resize()

    def remove(self: Self, remove_i: int) -> None:
        """
        Removes at an index, if there's only one checkbox it will be edited to black.

        Args:
            index
        """

        if len(self.colors) == 1:
            self.edit(0, HEX_BLACK)
        else:
            self.colors.pop(remove_i)
            if self.clicked_i > remove_i:
                self.clicked_i = self.prev_clicked_i = self.clicked_i - 1
            elif self.clicked_i == remove_i:
                self.clicked_i = self.prev_clicked_i = min(self.clicked_i, len(self.colors) - 1)

            num_above_rows: int = ceil(len(self.colors) / NUM_COLS) - self.offset_y
            if self.offset_y != 0 and num_above_rows < NUM_VISIBLE_ROWS:
                self.offset_y -= 1

            self.set_offset_y(self.offset_y)
            checkbox_grid_get_rect(self.visible_checkboxes, self.rect)

    def _handle_shortcuts(self: Self) -> None:
        """Selects a color if the user presses ctrl+c+dimension."""

        k: int

        num_shortcuts: int = min(len(self.colors), 9)
        for k in range(K_1, K_1 + num_shortcuts):
            if k in KEYBOARD.pressed:
                self.clicked_i = k - K_1

    def upt_checkboxes(self: Self) -> None:
        """Updates the checkboxes and sets the absolute clicked index."""

        did_check_hovered_checkbox: bool

        self._hovered_checkbox, did_check_hovered_checkbox = checkbox_grid_upt_checkboxes(
            self.visible_checkboxes, self._hovered_checkbox
        )

        if did_check_hovered_checkbox:
            visible_start_i: int = self.offset_y * NUM_COLS
            rel_hovered_checkbox_i: int = self.visible_checkboxes.index(self._hovered_checkbox)
            self.clicked_i = visible_start_i + rel_hovered_checkbox_i

    def upt(self: Self) -> None:
        """Allows checking only one checkbox at a time."""

        if KEYBOARD.is_ctrl_on and K_c in KEYBOARD.pressed:
            self._handle_shortcuts()

        if (
            (MOUSE.hovered_obj == self or self._hovered_checkbox is not None) and
            KEYBOARD.pressed != ()
        ):
            self.clicked_i = checkbox_grid_move_with_keys(
                K_RIGHT, K_LEFT, K_DOWN, K_UP,
                NUM_COLS, len(self.colors), self.clicked_i
            )

        self.upt_checkboxes()

        if self.clicked_i != self.prev_clicked_i:
            visible_start_i: int = self.offset_y * NUM_COLS
            visible_end_i: int = visible_start_i + len(self.visible_checkboxes)
            if   self.clicked_i <  visible_start_i:
                self.offset_y = self.clicked_i // NUM_COLS
            elif self.clicked_i >= visible_end_i:
                clicked_row: int = self.clicked_i // NUM_COLS
                self.offset_y = clicked_row - NUM_VISIBLE_ROWS + 1
