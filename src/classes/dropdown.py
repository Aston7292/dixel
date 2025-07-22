"""Class to crate a drop-down menu with various options."""

from typing import Any

import pygame as pg
from pygame.locals import SYSTEM_CURSOR_ARROW

from src.classes.clickable import Button
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE

from src.utils import RectPos, ObjInfo, rec_move_rect
from src.type_utils import BlitInfo
from src.consts import MOUSE_LEFT, BG_LAYER
from src.imgs import BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG

class Dropdown:
    """Class to crate a drop-down menu with various options."""

    __slots__ = (
        "_init_x", "_init_y",
        "_options", "values", "option_i", "_is_fully_visible",
        "hover_rects", "layer", "blit_sequence", "_win_ratio_w", "_win_ratio_h", "objs_info",
        "_options_objs_info_start_i", "_options_objs_info_end_i",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(
            self, pos: RectPos, info: list[tuple[str, str, Any]], text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates all the buttons.

        Args:
            position, options texts hovering texts and values, text,
            base layer (default = BG_LAYER)
        """

        self._init_x: int = pos.x
        self._init_y: int = pos.y

        info = [("", "", None)] + info  # For placeholder button
        self._options: list[Button] = [
            # Changed to copy selected option when fully visible
            Button(
                RectPos(self._init_x, self._init_y, pos.coord_type),
                [BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG], option_text, option_hovering_text,
                base_layer
            )
            for option_text, option_hovering_text, _option_value in info
        ]

        self.values: list[Any] = [
            option_value for _option_text, _option_hovering_text, option_value in info
        ]
        self.option_i: int = 1
        self._is_fully_visible: bool = False

        text_label: TextLabel = TextLabel(
            RectPos(self._options[0].rect.centerx, self._options[0].rect.y - 8, "midbottom"),
            text, base_layer
        )

        self.hover_rects: list[pg.Rect] = []
        self.layer: int = base_layer
        self.blit_sequence: list[BlitInfo] = []
        self._win_ratio_w: float = 1
        self._win_ratio_h: float = 1
        self.objs_info: list[ObjInfo] = [ObjInfo(text_label)]

        self._options_objs_info_start_i: int = len(self.objs_info)
        self.objs_info.extend([ObjInfo(option) for option in self._options])
        self._options_objs_info_end_i: int   = len(self.objs_info)

        self.set_option_i(self.option_i)


    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._set_full_visibility(False)

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        self._win_ratio_w, self._win_ratio_h = win_w_ratio, win_h_ratio

    def set_option_i(self, option_i: int) -> None:
        """
        Selects an option, moves it to the top, activates it and inactivates all others.

        Args:
            option index
        """

        obj_info: ObjInfo

        self.option_i = option_i

        dropdown_objs_info: list[ObjInfo] = self.objs_info[
            self._options_objs_info_start_i:self._options_objs_info_end_i
        ]
        selected_obj_info: ObjInfo = dropdown_objs_info[self.option_i]
        for obj_info in dropdown_objs_info:
            obj_info.rec_set_active(obj_info == selected_obj_info)

        option_obj_info_i: int = self._options_objs_info_start_i + self.option_i
        rec_move_rect(
            self.objs_info[option_obj_info_i].obj, self._init_x, self._init_y,
            self._win_ratio_w, self._win_ratio_h
        )

    def _set_full_visibility(self, is_fully_visible: bool) -> None:
        """
        Sets the visibility of the full options list.

        Args:
            fully visible flag
        """

        option: Button
        obj_info: ObjInfo

        self._is_fully_visible = is_fully_visible

        if self._is_fully_visible:
            self._options[0].text_label.set_text(  self._options[self.option_i].text_label.text)
            self._options[0].hovering_text_label = self._options[self.option_i].hovering_text_label

            init_y: int = self._init_y
            for option in self._options:
                rec_move_rect(
                    option, self._init_x, init_y,
                    self._win_ratio_w, self._win_ratio_h
                )
                init_y += option.init_imgs[0].get_height()
        else:
            option_obj_info_i: int = self._options_objs_info_start_i + self.option_i
            rec_move_rect(
                self.objs_info[option_obj_info_i].obj, self._init_x, self._init_y,
                self._win_ratio_w, self._win_ratio_h
            )

        dropdown_objs_info: list[ObjInfo] = self.objs_info[
            self._options_objs_info_start_i:self._options_objs_info_end_i
        ]
        selected_obj_info: ObjInfo = dropdown_objs_info[self.option_i]
        for obj_info in dropdown_objs_info:
            if obj_info != selected_obj_info:
                obj_info.rec_set_active(self._is_fully_visible)

    def _upt_all(self) -> None:
        """Updates all options, if one is clicked it selects it and hides all others."""

        i: int
        option: Button

        clicked_option: Button | None = None
        for i, option in enumerate(self._options):
            is_clicked: bool = option.upt()
            if is_clicked:
                if i != 0:
                    self.option_i = i
                clicked_option = option

                self._set_full_visibility(False)
                break

        if clicked_option == self._options[0]:
            # Placeholder option was clicked, the selected one is now in its place and hovered
            MOUSE.hovered_obj = self._options[self.option_i]
            self._options[self.option_i].img_i = 1
            self._options[self.option_i]._is_hovering = True
        elif clicked_option is not None:
            # An option was clicked and it moved to the top, MOUSE is no longer hovering it
            MOUSE.hovered_obj = None
            clicked_option.img_i = 0
            clicked_option._is_hovering = False

    def _upt_selected(self) -> None:
        """Updates the selected option, if one is clicked it activates all others."""

        is_clicked: bool = self._options[self.option_i].upt()
        if is_clicked:
            self._set_full_visibility(not self._is_fully_visible)
            if self._is_fully_visible:
                # Selected option was moved to its index, mouse is now hovering the placeholder one
                self._options[self.option_i].img_i = 0
                self._options[self.option_i]._is_hovering = False
                MOUSE.hovered_obj = self._options[0]
                self._options[0            ].img_i = 1
                self._options[0            ]._is_hovering = True

    def upt(self) -> None:
        """Shows all the options if the drop-down menu is clicked and allows selecting one."""

        is_hovering_option: bool = MOUSE.hovered_obj in self._options
        if (MOUSE.released[MOUSE_LEFT] and not is_hovering_option) and self._is_fully_visible:
            self._set_full_visibility(False)

        if self._is_fully_visible:
            self._upt_all()
        else:
            self._upt_selected()
