"""Abstract class to create a default UI with a title, confirm and exit buttons."""

from abc import ABC, abstractmethod
from typing import Final, Any

import pygame as pg

from src.classes.clickable import Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio, ObjInfo, MouseInfo, get_img, resize_obj
from src.type_utils import LayeredBlitSequence
from src.consts import UI_LAYER

INTERFACE_IMG: Final[pg.Surface] = pg.Surface((500, 700))
INTERFACE_IMG.fill((60, 60, 60))

BUTTON_M_OFF_IMG: Final[pg.Surface] = get_img("sprites", "button_m_off.png")
BUTTON_M_ON_IMG: Final[pg.Surface] = get_img("sprites", "button_m_on.png")
CLOSE_1_IMG: Final[pg.Surface] = get_img("sprites", "close_button_off.png")
CLOSE_2_IMG: Final[pg.Surface] = get_img("sprites", "close_button_on.png")

CHECKBOX_1_IMG: Final[pg.Surface] = get_img("sprites", "checkbox_off.png")
CHECKBOX_2_IMG: Final[pg.Surface] = get_img("sprites", "checkbox_on.png")


class UI(ABC):
    """
    Abstract class to create a default UI with a title, confirm and exit buttons.

    Includes:
        blit() -> PriorityBlitSequence
        resize(window size ratio) -> None,
        base_upt(mouse, keys) -> tuple[confirmed, exited]

    Children should include:
        upt(hovered object, mouse info, keys) -> tuple[closed, extra info]
    """

    __slots__ = (
        '_init_pos', '_init_img', '_img', '_rect', '_base_layer', '_exit', '_confirm',
        'objs_info'
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
        self._rect: pg.Rect = self._img.get_rect(
            **{self._init_pos.coord_type: (self._init_pos.x, self._init_pos.y)}
        )

        self._base_layer: int = UI_LAYER

        title_text_label: TextLabel = TextLabel(
            RectPos(self._rect.centerx, self._rect.top + 10, 'midtop'), title,
            self._base_layer, 32
        )

        self._exit: Button = Button(
            RectPos(self._rect.right - 10, self._rect.y + 10, 'topright'),
            (CLOSE_1_IMG, CLOSE_2_IMG), None, "(CTRL+BACKSPACE)", self._base_layer
        )
        self._confirm: Button = Button(
            RectPos(self._rect.right - 10, self._rect.bottom - 10, 'bottomright'),
            (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "confirm", "(CTRL+ENTER)", self._base_layer
        )

        self.objs_info: list[ObjInfo] = [
            ObjInfo(title_text_label),
            ObjInfo(self._exit), ObjInfo(self._confirm)
        ]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        return [(self._img, self._rect.topleft, self._base_layer)]

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        xy: tuple[int, int]
        wh: tuple[int, int]
        xy, wh = resize_obj(self._init_pos, *self._init_img.get_size(), win_ratio)

        self._img = pg.transform.scale(self._init_img, wh)
        self._rect = self._img.get_rect(**{self._init_pos.coord_type: xy})

    def _base_upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]
    ) -> tuple[bool, bool]:
        """
        Checks if the exit or confirm button were pressed.

        Args:
            hovered object, mouse info, keys
        Returns:
            buttons states
        """

        kmod_ctrl: int = pg.key.get_mods() & pg.KMOD_CTRL

        ctrl_backspace: bool = bool(kmod_ctrl and pg.K_BACKSPACE in keys)
        exited: bool = self._exit.upt(hovered_obj, mouse_info) or ctrl_backspace

        ctrl_enter: bool = bool(kmod_ctrl and pg.K_RETURN in keys)
        confirmed: bool = self._confirm.upt(hovered_obj, mouse_info) or ctrl_enter

        return confirmed, exited

    @abstractmethod
    def upt(self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]) -> tuple[bool, Any]:
        """
        Should implement a way to make the object interactable.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            True if the interface was closed else False, extra info
        """
