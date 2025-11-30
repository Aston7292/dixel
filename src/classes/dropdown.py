"""Class to crate a drop-down menu with various options."""

from typing import Self, Any

from pygame import Rect, SYSTEM_CURSOR_ARROW

from src.classes.clickable import Button
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE

from src.obj_utils import UIElement, ObjInfo, rec_move_rect
from src.type_utils import DropdownOptionsInfo, BlitInfo, RectPos
from src.consts import MOUSE_LEFT, BG_LAYER, ELEMENT_LAYER, TEXT_LAYER, TOP_LAYER
from src.imgs import BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG


class Dropdown:
    """Class to crate a drop-down menu with various options."""

    __slots__ = (
        "init_pos",
        "_options", "values", "option_i", "_is_fully_visible",
        "hover_rects", "layer", "blit_sequence", "objs_info",
        "_options_objs_info_start_i", "_options_objs_info_end_i",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(
            self: Self, pos: RectPos, info: DropdownOptionsInfo, text: str,
            base_layer: int = BG_LAYER,
            text_h: int = 25, is_text_above: bool = True
    ) -> None:
        """
        Creates all the buttons.

        Args:
            position, options texts hovering texts and values, text,
            base layer (default = BG_LAYER),
            text height (default = 25), text above flag (default = True, False = left)
        """

        self.init_pos: RectPos = pos

        # For placeholder button (changed to copy selected option when fully visible)
        info = (("", "", None),) + info

        option_base_layer: int = base_layer + TOP_LAYER - ELEMENT_LAYER
        self._options: list[Button] = [
            Button(
                RectPos(self.init_pos.x, self.init_pos.y, self.init_pos.coord_type),
                (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG), text, hovering_text,
                option_base_layer, should_animate=False, text_h=text_h
            )
            for text, hovering_text, _value in info
        ]

        self.values: list[Any] = [value for _text, _hovering_text, value in info]
        self.option_i: int = 0
        self._is_fully_visible: bool = False

        option_rect: Rect = self._options[0].rect
        text_label_pos: RectPos = (
            RectPos(option_rect.centerx, option_rect.y - 4, "midbottom") if is_text_above else
            RectPos(option_rect.x - 16, option_rect.centery, "midright")
        )
        text_label: TextLabel = TextLabel(
            text_label_pos,
            text, base_layer + TOP_LAYER - TEXT_LAYER
        )

        self.hover_rects: tuple[Rect, ...] = ()
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = []
        self.objs_info: tuple[ObjInfo, ...] = (ObjInfo(text_label),)

        self._options_objs_info_start_i: int = len(self.objs_info)
        self.objs_info += tuple([ObjInfo(option) for option in self._options])
        self._options_objs_info_end_i: int   = len(self.objs_info)

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._set_full_visibility(False)

    def resize(self: Self) -> None:
        """Resizes the object."""

    def move_rect(self: Self, init_x: int, init_y: int, _should_scale: bool) -> None:
        """
        Moves the rect to a specific coordinate.

        Args:
            initial x, initial y, scale flag
        """

        self.init_pos.x, self.init_pos.y = init_x, init_y  # More accurate

    def set_option_i(self: Self, option_i: int) -> None:
        """
        Selects an option, moves it to the top, activates it and inactivates all others.

        Args:
            option index
        """

        obj_info: ObjInfo

        self.option_i = option_i
        self._is_fully_visible = False

        dropdown_objs_info: tuple[ObjInfo, ...] = self.objs_info[
            self._options_objs_info_start_i:self._options_objs_info_end_i
        ]
        selected_obj_info: ObjInfo = dropdown_objs_info[self.option_i]
        for obj_info in dropdown_objs_info:
            obj_info.rec_set_active(obj_info == selected_obj_info)

        rec_move_rect(self._options[self.option_i], self.init_pos.x, self.init_pos.y)

    def add(self: Self, text: str, hovering_text: str, value: Any) -> None:
        """
        Adds an option and makes it visible if it should be.

        Args:
            text, hovering text, value
        """

        assert self._options[0].text_label is not None

        option_base_layer: int = self._options[0].layer + TOP_LAYER - ELEMENT_LAYER
        option: Button = Button(
            RectPos(self.init_pos.x, self.init_pos.y, self.init_pos.coord_type),
            (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG), text, hovering_text,
            option_base_layer, should_animate=False, text_h=self._options[0].text_label.init_h
        )

        option_objs: list[UIElement] = [option]
        while option_objs != []:
            obj: UIElement = option_objs.pop()
            obj.resize()
            option_objs.extend([info.obj for info in obj.objs_info])

        self._options.append(option)
        self.values.append(value)
        self.objs_info = (
            self.objs_info[:self._options_objs_info_end_i] +
            (ObjInfo(option),) +
            self.objs_info[self._options_objs_info_end_i:]
        )
        self.objs_info[self._options_objs_info_end_i].rec_set_active(False)
        self._options_objs_info_end_i += 1

    def _set_full_visibility(self: Self, is_fully_visible: bool) -> None:
        """
        Sets the visibility of the full options list.

        Args:
            fully visible flag
        """

        i: int
        option: Button
        obj_info: ObjInfo

        self._is_fully_visible = is_fully_visible

        if self._is_fully_visible:
            selected_option_text_label: TextLabel | None = self._options[self.option_i].text_label
            hovering_text: str = self._options[self.option_i].hovering_text_label.text
            assert self._options[0].text_label is not None
            assert selected_option_text_label is not None
            self._options[0].text_label.set_text(selected_option_text_label.text)
            self._options[0].hovering_text_label.set_text(hovering_text)

            option_h: int = self._options[0].init_imgs[0].get_height()
            for i, option in enumerate(self._options):
                rec_move_rect(option, self.init_pos.x, self.init_pos.y + (i * option_h))
        else:
            rec_move_rect(self._options[self.option_i], self.init_pos.x, self.init_pos.y)

        dropdown_objs_info: tuple[ObjInfo, ...] = self.objs_info[
            self._options_objs_info_start_i:self._options_objs_info_end_i
        ]
        selected_obj_info: ObjInfo = dropdown_objs_info[self.option_i]
        for obj_info in dropdown_objs_info:
            obj_info.rec_set_active(self._is_fully_visible or obj_info == selected_obj_info)

    def _upt_all(self: Self) -> None:
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
            # Placeholder option was clicked, the selected one is now hovered
            MOUSE.hovered_obj = self._options[self.option_i]
            self._options[self.option_i].set_hovering(True)
        elif clicked_option is not None:
            # An option was clicked and it moved to the top, MOUSE is no longer hovering it
            MOUSE.hovered_obj = None
            mouse_released_list: list[bool] = list(MOUSE.released)
            mouse_released_list[MOUSE_LEFT] = False  # Doesn't click objects below
            MOUSE.released = tuple(mouse_released_list)
            clicked_option.set_hovering(False)

    def _upt_selected(self: Self) -> None:
        """Updates the selected option, if one is clicked it activates all others."""

        is_clicked: bool = self._options[self.option_i].upt()
        if is_clicked:
            self._set_full_visibility(not self._is_fully_visible)
            if self._is_fully_visible:
                # Selected option was moved to its index, mouse is now hovering the placeholder one
                self._options[self.option_i].set_hovering(False)
                MOUSE.hovered_obj = self._options[0]
                self._options[0            ].set_hovering(True)

    def upt(self: Self) -> None:
        """Shows all the options if the drop-down menu is clicked and allows selecting one."""

        if (
            self._is_fully_visible and
            (MOUSE.released[MOUSE_LEFT] and MOUSE.hovered_obj not in self._options)
        ):
            self._set_full_visibility(False)

        if self._is_fully_visible:
            self._upt_all()
        else:
            self._upt_selected()
