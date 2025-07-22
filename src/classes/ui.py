"""Abstract class to create a default UI with a title, confirm and exit buttons."""

from abc import ABC, abstractmethod
from typing import Final, Any

import pygame as pg
from pygame import K_ESCAPE, K_RETURN, SYSTEM_CURSOR_ARROW

from src.classes.clickable import Button
from src.classes.text_label import TextLabel
from src.classes.devices import KEYBOARD

from src.utils import RectPos, ObjInfo, resize_obj
from src.type_utils import XY, BlitInfo
from src.consts import DARKER_GRAY, WIN_INIT_W, WIN_INIT_H, UI_LAYER
from src.imgs import CLOSE_OFF_IMG, CLOSE_ON_IMG, BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG

_INTERFACE_IMG: Final[pg.Surface] = pg.Surface((512, 700))
_INTERFACE_IMG.fill(DARKER_GRAY)


class UI(ABC):
    """
    Abstract class to create a default UI with a title, confirm and exit buttons.

    Includes:
        hover_rects
        layer
        blit_sequence
        cursor_type
        objs_info

        enter() -> None
        leave() -> None
        resize(window width ratio, window height ratio) -> None,
        base_upt() -> tuple[exited, confirmed]

    Children should include:
        upt() -> tuple[exited, confirmed, extra info]
    """

    __slots__ = (
        "_init_pos", "_rect",
        "hover_rects", "layer", "blit_sequence", "objs_info",
        "_exit", "_confirm",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(self, title: str, has_confirm: bool) -> None:
        """
        Creates the title, exit and confirm buttons.

        Args:
            title, has confirm flag
        """

        self._init_pos: RectPos = RectPos(round(WIN_INIT_W / 2), round(WIN_INIT_H / 2), "center")

        self._rect: pg.Rect = pg.Rect(0, 0, *_INTERFACE_IMG.get_size())
        setattr(self._rect, self._init_pos.coord_type, (self._init_pos.x, self._init_pos.y))

        self.hover_rects: list[pg.Rect] = []
        self.layer: int = UI_LAYER
        self.blit_sequence: list[BlitInfo] = [(_INTERFACE_IMG, self._rect, self.layer)]
        self.objs_info: list[ObjInfo] = []

        title_text_label: TextLabel = TextLabel(
            RectPos(self._rect.centerx, self._rect.y + 20, "midtop"),
            title, self.layer, 35
        )

        self._exit: Button = Button(
            RectPos(self._rect.right - 10, self._rect.y      + 10, "topright"),
            [CLOSE_OFF_IMG, CLOSE_ON_IMG], "", "Escape", self.layer
        )

        self._confirm: Button | None = None
        if has_confirm:
            self._confirm = Button(
                RectPos(self._rect.right - 10, self._rect.bottom - 10, "bottomright"),
                [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Confirm", "Enter", self.layer
            )

        self.objs_info.extend((ObjInfo(title_text_label), ObjInfo(self._exit)))
        if self._confirm is not None:
            self.objs_info.append(ObjInfo(self._confirm))

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY

        xy, self._rect.size = resize_obj(
            self._init_pos, *_INTERFACE_IMG.get_size(),
            win_w_ratio, win_h_ratio
        )

        img: pg.Surface = pg.transform.scale(_INTERFACE_IMG, self._rect.size).convert()
        setattr(self._rect, self._init_pos.coord_type, xy)

        self.blit_sequence[0] = (img, self._rect, self.layer)

    def _base_upt(self) -> tuple[bool, bool]:
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
    def upt(self) -> tuple[bool, bool, Any]:
        """
        Should implement a way to make the object interactable.

        Returns:
            exiting flag, confirming flag, extra info
        """
