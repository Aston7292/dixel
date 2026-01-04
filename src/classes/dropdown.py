"""Class to crate a drop-down menu with various options."""

from typing import Self, Any

from pygame import Rect

from src.classes.clickable import Button
from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE

from src.obj_utils import UIElement
from src.type_utils import DropdownOptionsInfo, RectPos
from src.consts import MOUSE_LEFT, ELEMENT_LAYER, SPECIAL_LAYER
from src.imgs import BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG


class Dropdown(UIElement):
    """Class to crate a drop-down menu with various options."""

    __slots__ = (
        "init_pos",
        "_options", "rect", "values", "option_i", "_is_fully_visible",
    )

    def __init__(
            self: Self, pos: RectPos, info: DropdownOptionsInfo,
            text: str, base_layer: int = SPECIAL_LAYER,
            text_h: int = 25, is_text_above: bool = True
    ) -> None:
        """
        Creates all the buttons.

        Args:
            position, options texts hovering texts and values,
            text, base layer (default = SPECIAL_LAYER),
            text height (default = 25), text above flag (default = True, False = left)
        """

        super().__init__()

        self.init_pos: RectPos = pos

        # For placeholder button (changed to copy selected option when fully visible)
        info = (("", "", None),) + info

        self._options: list[Button] = [
            Button(
                RectPos(self.init_pos.x, self.init_pos.y, self.init_pos.coord_type),
                (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG), text, hovering_text,
                base_layer, should_animate=False, text_h=text_h
            )
            for text, hovering_text, _value in info
        ]
        self.rect: Rect = self._options[0].rect

        self.values: list[Any] = [value for _text, _hovering_text, value in info]
        self.option_i: int = 0
        self._is_fully_visible: bool = False

        text_label_pos: RectPos = (
            RectPos(self.rect.centerx, self.rect.y - 4, "midbottom") if is_text_above else
            RectPos(self.rect.x - 8, self.rect.centery, "midright")
        )
        text_label: TextLabel = TextLabel(
            text_label_pos,
            text, base_layer - SPECIAL_LAYER, h=20
        )

        self.layer = base_layer
        self.sub_objs = (text_label,) + tuple(self._options)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._set_full_visibility(False)

    def move_to(self: Self, init_x: int, init_y: int, should_scale: bool) -> None:
        """
        Moves the object to a specific coordinate.

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

        option: Button

        self.option_i = option_i
        self._is_fully_visible = False

        selected_option: Button = self._options[self.option_i]
        for option in self._options:
            option.rec_set_active(option == selected_option)

        selected_option.rec_move_to(self.init_pos.x, self.init_pos.y)
        selected_option.rec_set_layer(self.layer + ELEMENT_LAYER - SPECIAL_LAYER)

    def add(self: Self, text: str, hovering_text: str, value: Any) -> None:
        """
        Adds an option and makes it visible if it should be.

        Args:
            text, hovering text, value
        """

        assert self._options[0].text_label is not None

        option: Button = Button(
            RectPos(self.init_pos.x, self.init_pos.y, self.init_pos.coord_type),
            (BUTTON_S_OFF_IMG, BUTTON_S_ON_IMG), text, hovering_text,
            self.layer, should_animate=False, text_h=self._options[0].text_label.init_h
        )
        option.rec_resize()
        option.rec_set_active(False)

        self._options.append(option)
        self.values.append(value)
        self.sub_objs += (option,)

    def _set_full_visibility(self: Self, is_fully_visible: bool) -> None:
        """
        Sets the visibility of the full options list.

        Args:
            fully visible flag
        """

        i: int
        option: Button

        self._is_fully_visible = is_fully_visible
        selected_option: Button = self._options[self.option_i]

        if self._is_fully_visible:
            assert (
                self._options[0].text_label is not None and
                selected_option.text_label is not None
            )
            self._options[0].text_label.set_text(selected_option.text_label.text)
            self._options[0].hovering_text_label.set_text(selected_option.hovering_text_label.text)

            option_init_h: int = self._options[0].init_imgs[0].get_height()
            for i, option in enumerate(self._options):
                option.rec_move_to(self.init_pos.x, self.init_pos.y + (i * option_init_h))
                option.rec_set_layer(self.layer + ELEMENT_LAYER)
        else:
            selected_option.rec_move_to(self.init_pos.x, self.init_pos.y)
            selected_option.rec_set_layer(self.layer + ELEMENT_LAYER - SPECIAL_LAYER)

        for option in self._options:
            option.rec_set_active(self._is_fully_visible or option == selected_option)

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
            MOUSE.released[MOUSE_LEFT] = False  # Doesn't click objects below
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
