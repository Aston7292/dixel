"""
Abstract class to create a default ui with a title, confirm and exit buttons
"""

import pygame as pg
from abc import ABC, abstractmethod
from os import path
from typing import Final, Any

from src.classes.clickable import Button
from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo
from src.type_utils import ObjsInfo, LayeredBlitSequence, LayerSequence
from src.consts import UI_LAYER

INTERFACE: Final[pg.SurfaceType] = pg.Surface((500, 700))
INTERFACE.fill((60, 60, 60))

BUTTON_M_OFF: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'button_m_off.png')
).convert_alpha()
BUTTON_M_ON: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'button_m_on.png')
).convert_alpha()

CLOSE_1: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'close_button_off.png')
).convert_alpha()
CLOSE_2: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'close_button_on.png')
).convert_alpha()

CHECK_BOX_1: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'check_box_off.png')
).convert_alpha()
CHECK_BOX_2: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'check_box_on.png')
).convert_alpha()
INPUT_BOX: Final[pg.Surface] = pg.Surface((60, 40))


class UI(ABC):
    """
    Abstract class to create a default ui with a title, confirm and exit buttons

    Includes:
        blit() -> PriorityBlitSequence
        handle_resize(window width ratio, window height ratio) -> None,
        base_upt(mouse, keys, ctrl) -> tuple[confirmed, exited]

    Children should include:
        upt(hovered object, mouse info, keys, ctrl) -> tuple[closed, extra info]
    """

    __slots__ = (
        '_init_pos', '_img', '_rect', '_init_size', '_base_layer', '_title', '_exit', '_confirm',
        'sub_objs'
    )

    def __init__(self, pos: RectPos, title: str) -> None:
        """
        Initializes the interface
        Args:
            position and title
        """

        self._init_pos: RectPos = pos

        self._img: pg.SurfaceType = INTERFACE
        self._rect: pg.FRect = self._img.get_frect(
            **{self._init_pos.coord: self._init_pos.xy}
        )

        self._init_size: Size = Size(int(self._rect.w), int(self._rect.h))

        self._base_layer: int = UI_LAYER

        self._title: Text = Text(
            RectPos(self._rect.centerx, self._rect.top + 10.0, 'midtop'), title,
            self._base_layer, 32
        )

        self._exit: Button = Button(
            RectPos(self._rect.right - 10.0, self._rect.y + 10.0, 'topright'),
            (CLOSE_1, CLOSE_2), '', '(CTRL+BACKSPACE)', self._base_layer
        )
        self._confirm: Button = Button(
            RectPos(self._rect.right - 10.0, self._rect.bottom - 10.0, 'bottomright'),
            (BUTTON_M_OFF, BUTTON_M_ON), 'confirm', '(CTRL+ENTER)', self._base_layer
        )

        self.sub_objs: ObjsInfo = [
            ('title', self._title),
            ('exit', self._exit),
            ('confirm', self._confirm)
        ]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return [(self._img, self._rect.topleft, self._base_layer)]

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes objects
        Args:
            window width ratio, window height ratio
        """

        size: tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: tuple[float, float] = (
            self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h
        )

        self._img = pg.transform.scale(self._img, size)
        self._rect = self._img.get_frect(**{self._init_pos.coord: pos})

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, self._base_layer, depth_counter)]

    def _base_upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: list[int], ctrl: int
    ) -> tuple[bool, bool]:
        """
        Handles the base behavior
        Args:
            hovered object, mouse info, keys, ctrl
        Returns:
            buttons states
        """

        ctrl_backspace: bool = bool(ctrl and pg.K_BACKSPACE in keys)
        exited: bool = self._exit.upt(hover_obj, mouse_info) or ctrl_backspace

        ctrl_enter: bool = bool(ctrl and pg.K_RETURN in keys)
        confirmed: bool = self._confirm.upt(hover_obj, mouse_info) or ctrl_enter

        return confirmed, exited

    @abstractmethod
    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: list[int], ctrl: int
    ) -> tuple[bool, Any]:
        """
        Should implement a way to make the object interactable
        Args:
            hovered object (can be None), mouse info, keys, ctrl
        Returns:
            True if the interface was closed else False, extra info
        """
