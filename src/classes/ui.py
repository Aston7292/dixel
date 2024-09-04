"""
abstract class to create a default ui with a title, a confirm and exit buttons
"""

import pygame as pg
from abc import ABC, abstractmethod
from os import path
from typing import Final, Any

from src.classes.clickable import Button
from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo, LayeredBlitSequence, LayersInfo
from src.const import UI_LAYER

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
    abstract class to create a default ui with a title, a confirm and exit buttons

    - includes: blit() -> PriorityBlitSequence, handle_resize(window size ratio) -> None,
    base_upt(mouse, keys, ctrl) -> confirmed, exited
    - children should include: upt(mouse info, keys, ctrl) -> tuple[bool, Any]
    """

    __slots__ = (
        '_ui_init_pos', '_ui_img', '_ui_rect', '_ui_init_size', '_base_layer', '_title',
        '_confirm', '_exit'
    )

    def __init__(self, pos: RectPos, title: str) -> None:
        """
        initializes the interface
        takes position and title
        """

        self._ui_init_pos: RectPos = pos

        self._ui_img: pg.SurfaceType = INTERFACE
        self._ui_rect: pg.FRect = self._ui_img.get_frect(
            **{self._ui_init_pos.coord: self._ui_init_pos.xy}
        )

        self._ui_init_size: Size = Size(int(self._ui_rect.w), int(self._ui_rect.h))

        self._base_layer: int = UI_LAYER

        self._title: Text = Text(
            RectPos(self._ui_rect.centerx, self._ui_rect.top + 10.0, 'midtop'), title,
            self._base_layer, 32
        )

        self._confirm: Button = Button(
            RectPos(self._ui_rect.right - 10.0, self._ui_rect.bottom - 10.0, 'bottomright'),
            (BUTTON_M_OFF, BUTTON_M_ON), 'confirm', '(CTRL+ENTER)', self._base_layer
        )
        self._exit: Button = Button(
            RectPos(self._ui_rect.right - 10.0, self._ui_rect.y + 10.0, 'topright'),
            (CLOSE_1, CLOSE_2), '', '(CTRL+BACKSPACE)', self._base_layer
        )

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._ui_img, self._ui_rect.topleft, self._base_layer)]
        sequence += self._title.blit()
        sequence += self._confirm.blit()
        sequence += self._exit.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        size: tuple[int, int] = (
            int(self._ui_init_size.w * win_ratio_w), int(self._ui_init_size.h * win_ratio_h)
        )
        pos: tuple[float, float] = (
            self._ui_init_pos.x * win_ratio_w, self._ui_init_pos.y * win_ratio_h
        )

        self._ui_img = pg.transform.scale(self._ui_img, size)
        self._ui_rect = self._ui_img.get_frect(**{self._ui_init_pos.coord: pos})

        self._title.handle_resize(win_ratio_w, win_ratio_h)
        self._confirm.handle_resize(win_ratio_w, win_ratio_h)
        self._exit.handle_resize(win_ratio_w, win_ratio_h)

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = [(name, self._base_layer, counter)]
        layers_info += self._exit.print_layers('button exit', counter + 1)
        layers_info += self._confirm.print_layers('button confirm', counter + 1)
        layers_info += self._title.print_layers('text title', counter + 1)

        return layers_info

    def _base_upt(self, mouse_info: MouseInfo, keys: list[int], ctrl: int) -> tuple[bool, bool]:
        """
        handles the base behavior
        takes mouse info, keys and ctrl
        returns the buttons that were clicked
        """

        confirmed: bool = self._confirm.upt(mouse_info) or bool(ctrl and pg.K_RETURN in keys)
        exited: bool = self._exit.upt(mouse_info) or bool(ctrl and pg.K_BACKSPACE in keys)

        if confirmed or exited:
            self._confirm.leave()
            self._exit.leave()

        return confirmed, exited

    @abstractmethod
    def upt(self, mouse_info: MouseInfo, keys: list[int], ctrl: int) -> tuple[bool, Any]:
        """
        should implement a way to make the object interactable
        takes mouse info, keys and ctrl
        returns whatever the interface was closed or not and the extra info
        """
