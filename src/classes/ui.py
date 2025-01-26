"""Abstract class to create a default UI with a title, confirm and exit buttons."""

from abc import ABC, abstractmethod
from typing import Final, Any

import pygame as pg

from src.classes.clickable import Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio, ObjInfo, Mouse, Keyboard, get_img, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import UI_LAYER

INTERFACE_IMG: Final[pg.Surface] = pg.Surface((500, 700))
INTERFACE_IMG.fill((60, 60, 60))

BUTTON_M_OFF_IMG: Final[pg.Surface] = get_img("sprites", "button_m_off.png")
BUTTON_M_ON_IMG: Final[pg.Surface] = get_img("sprites", "button_m_on.png")
CLOSE_IMG_OFF: Final[pg.Surface] = get_img("sprites", "close_button_off.png")
CLOSE_IMG_ON: Final[pg.Surface] = get_img("sprites", "close_button_on.png")

CHECKBOX_IMG_OFF: Final[pg.Surface] = get_img("sprites", "checkbox_off.png")
CHECKBOX_IMG_ON: Final[pg.Surface] = get_img("sprites", "checkbox_on.png")


class UI(ABC):
    """
    Abstract class to create a default UI with a title, confirm and exit buttons.

    Includes:
        get_blit_sequence() -> layered blit sequence
        resize(window size ratio) -> None,
        base_upt(mouse, keyboard) -> tuple[confirmed, exited]

    Children should include:
        upt(mouse, keyboard) -> tuple[closed, extra info]
    """

    __slots__ = (
        "_init_pos", "_init_img", "_img", "_rect", "_exit", "_confirm", "objs_info"
    )

    def __init__(self, pos: RectPos, title: str) -> None:
        """
        Initializes the interface.

        Args:
            position and title
        """

        self._init_pos: RectPos = pos
        self._init_img: pg.Surface = INTERFACE_IMG

        self._img: pg.Surface = self._init_img
        self._rect: pg.Rect = self._img.get_rect(**{self._init_pos.coord_type: self._init_pos.xy})

        title_text_label_pos: RectPos = RectPos(self._rect.centerx, self._rect.top + 10, "midtop")
        title_text_label: TextLabel = TextLabel(title_text_label_pos, title, UI_LAYER, 32)

        self._exit: Button = Button(
            RectPos(self._rect.right - 10, self._rect.y + 10, "topright"),
            [CLOSE_IMG_OFF, CLOSE_IMG_ON], None, "(Escape)", UI_LAYER
        )
        self._confirm: Button = Button(
            RectPos(self._rect.right - 10, self._rect.bottom - 10, "bottomright"),
            [BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG], "confirm", "(Enter)", UI_LAYER
        )

        self.objs_info: list[ObjInfo] = [
            ObjInfo(title_text_label), ObjInfo(self._exit), ObjInfo(self._confirm)
        ]

    def get_blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        return [(self._img, self._rect.topleft, UI_LAYER)]

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        xy: PosPair
        wh: SizePair
        xy, wh = resize_obj(self._init_pos, *self._init_img.get_size(), win_ratio)

        self._img = pg.transform.scale(self._init_img, wh)
        self._rect = self._img.get_rect(**{self._init_pos.coord_type: xy})

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
    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[bool, bool, Any]:
        """
        Should implement a way to make the object interactable.

        Args:
            mouse, keyboard
        Returns:
            exiting flag, confirming flag, extra info
        """
