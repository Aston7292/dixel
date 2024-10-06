"""
Abstract class to create a default UI with a title, confirm and exit buttons
"""

import pygame as pg
from abc import ABC, abstractmethod
from typing import Final, Any

from src.classes.clickable import Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, ObjInfo, MouseInfo, load_img, resize_obj
from src.type_utils import LayeredBlitSequence
from src.consts import UI_LAYER

INTERFACE_IMG: Final[pg.Surface] = pg.Surface((500, 700))
INTERFACE_IMG.fill((60, 60, 60))

BUTTON_M_OFF_IMG: Final[pg.Surface] = load_img("sprites", "button_m_off.png")
BUTTON_M_ON_IMG: Final[pg.Surface] = load_img("sprites", "button_m_on.png")
CLOSE_1_IMG: Final[pg.Surface] = load_img("sprites", "close_button_off.png")
CLOSE_2_IMG: Final[pg.Surface] = load_img("sprites", "close_button_on.png")

CHECKBOX_1_IMG: Final[pg.Surface] = load_img("sprites", "checkbox_off.png")
CHECKBOX_2_IMG: Final[pg.Surface] = load_img("sprites", "checkbox_on.png")
INPUT_BOX_IMG: Final[pg.Surface] = pg.Surface((60, 40))


class UI(ABC):
    """
    Abstract class to create a default UI with a title, confirm and exit buttons

    Includes:
        blit() -> PriorityBlitSequence
        handle_resize(window width ratio, window height ratio) -> None,
        base_upt(mouse, keys, ctrl) -> tuple[confirmed, exited]

    Children should include:
        upt(hovered object, mouse info, keys, ctrl) -> tuple[closed, extra info]
    """

    __slots__ = (
        '_init_pos', '_init_img', '_img', '_rect', '_base_layer', '_exit', '_confirm', 'objs_info'
    )

    def __init__(self, pos: RectPos, title: str) -> None:
        """
        Initializes the interface
        Args:
            position and title
        """

        self._init_pos: RectPos = pos
        self._init_img: pg.Surface = INTERFACE_IMG

        self._img: pg.Surface = self._init_img
        self._rect: pg.Rect = self._img.get_rect(**{self._init_pos.coord_type: self._init_pos.xy})

        self._base_layer: int = UI_LAYER

        title_text_label: TextLabel = TextLabel(
            RectPos(self._rect.centerx, self._rect.top + 10, 'midtop'), title,
            self._base_layer, 32
        )

        self._exit: Button = Button(
            RectPos(self._rect.right - 10, self._rect.y + 10, 'topright'),
            (CLOSE_1_IMG, CLOSE_2_IMG), '', "(CTRL+BACKSPACE)", self._base_layer
        )
        self._confirm: Button = Button(
            RectPos(self._rect.right - 10, self._rect.bottom - 10, 'bottomright'),
            (BUTTON_M_OFF_IMG, BUTTON_M_ON_IMG), "confirm", "(CTRL+ENTER)", self._base_layer
        )

        self.objs_info: list[ObjInfo] = [
            ObjInfo("title", title_text_label),
            ObjInfo("exit", self._exit), ObjInfo("confirm", self._confirm)
        ]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return [(self._img, self._rect.topleft, self._base_layer)]

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
        Args:
            window width ratio, window height ratio
        """

        pos: tuple[int, int]
        size: tuple[int, int]
        pos, size = resize_obj(
            self._init_pos, *self._init_img.get_size(), win_ratio_w, win_ratio_h
        )

        self._img = pg.transform.scale(self._init_img, size)
        self._rect = self._img.get_rect(**{self._init_pos.coord_type: pos})

    def _base_upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], ctrl: int
    ) -> tuple[bool, bool]:
        """
        Handles the base behavior
        Args:
            hovered object, mouse info, keys, ctrl
        Returns:
            buttons states
        """

        ctrl_backspace: bool = bool(ctrl and pg.K_BACKSPACE in keys)
        exited: bool = self._exit.upt(hovered_obj, mouse_info) or ctrl_backspace

        ctrl_enter: bool = bool(ctrl and pg.K_RETURN in keys)
        confirmed: bool = self._confirm.upt(hovered_obj, mouse_info) or ctrl_enter

        return confirmed, exited

    @abstractmethod
    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], ctrl: int
    ) -> tuple[bool, Any]:
        """
        Should implement a way to make the object interactable
        Args:
            hovered object (can be None), mouse info, keys, ctrl
        Returns:
            True if the interface was closed else False, extra info
        """
