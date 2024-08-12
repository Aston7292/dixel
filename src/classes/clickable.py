"""
class to create a button, when hovered changes image and text appears on top of it
"""

import pygame as pg
from abc import ABC, abstractmethod
from typing import Tuple, Optional

from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo
from src.const import BlitSequence


class Clickable(ABC):
    """
    abstract class to create and object that changes between two images
    includes: blit, handle_resize (window size ratio)
    children should include: upt (mouse info)
    """

    __slots__ = (
        '_init_pos', '_imgs', 'rect', '_init_size', '_img_i', '_hovering'
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, ...]) -> None:
        """
        creates surfaces and rect
        takes position and two images
        """

        self._init_pos: RectPos = pos

        self._imgs: Tuple[pg.SurfaceType, ...] = imgs
        self.rect: pg.FRect = self._imgs[0].get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self._img_i: int = 0
        self._hovering: bool = False

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return [(self._imgs[self._img_i], self.rect.topleft)]

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        size: Tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: Tuple[float, float] = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        self._imgs = tuple(pg.transform.scale(img, size) for img in self._imgs)
        self.rect = self._imgs[0].get_frect(**{self._init_pos.pos: pos})

    @abstractmethod
    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        method to interact with the object, should change mouse sprite and
        implement a way to change image index
        takes mouse info
        returns a boolean
        """


class CheckBox(Clickable):
    """
    class to create a checkbox with text on the left
    """

    __slots__ = (
        'ticked', '_text'
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, ...], text: str) -> None:
        """
        creates surfaces, rect and text object
        takes position, two images and text
        """

        super().__init__(pos, imgs)

        self.ticked: bool = False

        self._text: Text = Text(
            RectPos(self.rect.left - 10, self.rect.centery, 'midright'), 28, text
        )

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = super().blit()
        if self._text:
            sequence += self._text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        super().handle_resize(win_ratio_w, win_ratio_h)
        if self._text:
            self._text.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo) -> bool:
        """
        changes the checkbox image when clicked
        takes mouse info
        returns True if the checkbox was ticked on
        """

        if not self.rect.collidepoint(mouse_info.xy):
            if self._hovering:
                self._hovering = False
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

            return False

        if not self._hovering:
            self._hovering = True
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)

        if mouse_info.released[0]:
            self.ticked = not self.ticked
            self._img_i = int(self.ticked)

            return self.ticked

        return False


class Button(Clickable):
    """
    class to create a button, when hovered changes image and text appears on top of it
    """

    __slots__ = (
        '_text',
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, ...], text: str) -> None:
        """
        creates surfaces, rect and text object
        takes position, two images and text
        """

        super().__init__(pos, imgs)

        self._text: Optional[Text]
        if not text:
            self._text = None
        else:
            self._text = Text(RectPos(*self.rect.center, 'center'), 28, text)

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = super().blit()
        if self._text:
            sequence += self._text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        super().handle_resize(win_ratio_w, win_ratio_h)
        if self._text:
            self._text.handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo, toggle_on_press: bool = False) -> bool:
        """
        updates the button image if the mouse is hovering it
        takes mouse info and the toggle_on_press flag
        returns whatever the button was clicked or not
        """

        if not self.rect.collidepoint(mouse_info.xy):
            if self._hovering:
                self._img_i = 0
                self._hovering = False
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

            return False

        if not self._hovering:
            self._img_i = 1
            self._hovering = True
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)

        if toggle_on_press and mouse_info.released[0]:
            self._img_i = 0
            self._hovering = False
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

        return mouse_info.released[0]
