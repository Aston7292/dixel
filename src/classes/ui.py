"""Abstract class to create a default UI with a title, confirm and exit buttons."""

from abc import abstractmethod
from typing import Self, Final, Any

from pygame import Surface, Rect, K_ESCAPE, K_RETURN

from src.classes.clickable import Button
from src.classes.text_label import TextLabel
from src.classes.devices import KEYBOARD

import src.obj_utils as objs
from src.obj_utils import UIElement, resize_obj
from src.type_utils import XY, RectPos
from src.consts import DARKER_GRAY, UI_LAYER
from src.win import WIN_INIT_W, WIN_INIT_H
from src.imgs import CLOSE_OFF_IMG, CLOSE_ON_IMG, BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG

INTERFACE_INIT_W: Final[int] = 500
INTERFACE_INIT_H: Final[int] = 700


class UI(UIElement):
    """Abstract class to create a default UI with a title, confirm and exit buttons."""

    __slots__ = (
        "_init_pos", "_rect",
        "_title_text_label", "_exit", "_confirm",
    )

    def __init__(self: Self, title: str, should_have_confirm: bool) -> None:
        """
        Creates the title, exit and confirm buttons.

        Args:
            title, have confirm flag
        """

        super().__init__()

        self._init_pos: RectPos = RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center")

        img: Surface = Surface((INTERFACE_INIT_W, INTERFACE_INIT_H))
        img.fill(DARKER_GRAY)
        self._rect: Rect = Rect(0, 0, *img.get_size())
        setattr(self._rect, self._init_pos.coord_type, (self._init_pos.x, self._init_pos.y))

        self._title_text_label: TextLabel = TextLabel(
            RectPos(self._rect.centerx, self._rect.y + 16, "midtop"),
            title, UI_LAYER, h=35
        )

        self._exit: Button = Button(
            RectPos(self._rect.right - 10, self._rect.y + 10, "topright"),
            (CLOSE_OFF_IMG, CLOSE_ON_IMG), None, "Escape", UI_LAYER
        )

        self._confirm: Button | None = None
        if should_have_confirm:
            self._confirm = Button(
                RectPos(self._rect.right - 10, self._rect.bottom - 10, "bottomright"),
                (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "Confirm", "Enter", UI_LAYER
            )

        self.layer = UI_LAYER
        self.blit_sequence = [(img, self._rect, self.layer)]
        self.sub_objs = (self._title_text_label, self._exit)
        if self._confirm is not None:
            self.sub_objs += (self._confirm,)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        objs_list: list[UIElement] = list(self.sub_objs)
        while objs_list != []:
            obj: UIElement = objs_list.pop()
            if obj in objs.animating_objs:
                obj.reset_animation()
                objs.animating_objs.remove(obj)

            objs_list.extend(obj.sub_objs)

    def resize(self: Self) -> None:
        """Resizes the object."""

        xy: XY

        xy, self._rect.size = resize_obj(self._init_pos, INTERFACE_INIT_W, INTERFACE_INIT_H)
        img: Surface = Surface(self._rect.size)
        img.fill(DARKER_GRAY)
        setattr(self._rect, self._init_pos.coord_type, xy)

        self.blit_sequence[0] = (img, self._rect, self.layer)

    def _base_upt(self: Self) -> tuple[bool, bool]:
        """
        Checks if the exit or confirm button are pressed.

        Returns:
            exiting flag, confirming flag
        """

        is_exit_pressed: bool = self._exit.upt()
        is_exiting: bool = is_exit_pressed or K_ESCAPE in KEYBOARD.released

        is_confirming: bool = False
        if self._confirm is not None:
            is_confirm_pressed: bool = self._confirm.upt()
            is_confirming = is_confirm_pressed or K_RETURN in KEYBOARD.released

        return is_exiting, is_confirming

    @abstractmethod
    def upt(self: Self) -> tuple[bool, bool, *tuple[Any, ...]]:
        """
        Should implement a way to make the object interactable.

        Returns:
            exiting flag, confirming flag, extra info
        """
