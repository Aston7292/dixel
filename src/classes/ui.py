"""Abstract class to create a default UI with a title, confirm and exit buttons."""

from abc import ABC, abstractmethod
from typing import Final, Any

import pygame as pg

from src.classes.clickable import Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, ObjInfo, Mouse, Keyboard, resize_obj
from src.file_utils import try_get_img
from src.type_utils import XY, WH, LayeredBlitInfo
from src.consts import DARKER_GRAY, UI_LAYER

INTERFACE_IMG: Final[pg.Surface] = pg.Surface((500, 700))
INTERFACE_IMG.fill(DARKER_GRAY)

BUTTON_M_OFF_IMG: Final[pg.Surface] = try_get_img(
    "sprites", "button_m_off.png", missing_img_wh=(128, 64)
)
BUTTON_M_ON_IMG: Final[pg.Surface] = try_get_img(
    "sprites", "button_m_on.png", missing_img_wh=(128, 64)
)
CLOSE_BUTTON_OFF_IMG: Final[pg.Surface] = try_get_img(
    "sprites", "close_button_off.png", missing_img_wh=(48, 48)
)
CLOSE_BUTTON_ON_IMG: Final[pg.Surface] = try_get_img(
    "sprites", "close_button_on.png", missing_img_wh=(48, 48)
)
CHECKBOX_IMG_OFF: Final[pg.Surface] = try_get_img(
    "sprites", "checkbox_off.png", missing_img_wh=(48, 48)
)
CHECKBOX_IMG_ON: Final[pg.Surface] = try_get_img(
    "sprites", "checkbox_on.png", missing_img_wh=(48, 48)
)


class UI(ABC):
    """
    Abstract class to create a default UI with a title, confirm and exit buttons.

    Includes:
        blit_sequence() -> layered blit sequence
        resize(window width ratio, window height ratio) -> None,
        base_upt(mouse, keyboard) -> tuple[confirmed, exited]

    Children should include:
        upt(mouse, keyboard) -> tuple[closed, extra info]
    """

    __slots__ = (
        "_init_pos", "_rect", "_exit", "_confirm", "blit_sequence", "objs_info"
    )

    def __init__(self, pos: RectPos, title: str) -> None:
        """
        Initializes the interface.

        Args:
            position and title
        """

        self._init_pos: RectPos = pos

        self._rect: pg.Rect = pg.Rect(0, 0, *INTERFACE_IMG.get_size())
        setattr(self._rect, self._init_pos.coord_type, (self._init_pos.x, self._init_pos.y))

        title_text_label: TextLabel = TextLabel(
            RectPos(self._rect.centerx, self._rect.y + 20, "midtop"),
            title, UI_LAYER, 32
        )

        self._exit: Button = Button(
            RectPos(self._rect.right - 10, self._rect.y + 10, "topright"),
            [CLOSE_BUTTON_OFF_IMG, CLOSE_BUTTON_ON_IMG], None, "(Escape)", UI_LAYER
        )
        self._confirm: Button = Button(
            RectPos(self._exit.rect.right, self._rect.bottom - 10, "bottomright"),
            [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "Confirm", "(Enter)", UI_LAYER
        )

        self.blit_sequence: list[LayeredBlitInfo] = [(INTERFACE_IMG, self._rect, UI_LAYER)]
        self.objs_info: list[ObjInfo] = [
            ObjInfo(title_text_label), ObjInfo(self._exit), ObjInfo(self._confirm)
        ]

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY
        wh: WH

        xy, wh = resize_obj(self._init_pos, *INTERFACE_IMG.get_size(), win_w_ratio, win_h_ratio)
        img: pg.Surface = pg.transform.scale(INTERFACE_IMG, wh)
        self._rect.size = wh
        setattr(self._rect, self._init_pos.coord_type, xy)

        self.blit_sequence[0] = (img, self._rect, UI_LAYER)

    def _base_upt(self, mouse: Mouse, keys: list[int]) -> tuple[bool, bool]:
        """
        Checks if the exit or confirm button were pressed.

        Args:
            mouse, keys
        Returns:
            exiting flag, confirming flag
        """

        is_exit_pressed: bool = self._exit.upt(mouse)
        is_exiting: bool = is_exit_pressed or pg.K_ESCAPE in keys

        is_confirm_pressed: bool = self._confirm.upt(mouse)
        is_confirming: bool = is_confirm_pressed or pg.K_RETURN in keys

        return is_exiting, is_confirming

    @abstractmethod
    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[Any, ...]:
        """
        Should implement a way to make the object interactable.

        Args:
            mouse, keyboard
        Returns:
            exiting flag, confirming flag, extra info
        """
