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
    includes: blit () -> BlitSequence, handle_resize (window size ratio) -> None
    children should include: upt (mouse info) -> bool
    """

    __slots__ = (
        '_init_pos', '_imgs', 'rect', '_init_size', 'img_i', 'hovering'
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType]) -> None:
        """
        creates surfaces and rect
        takes position and two images
        """

        self._init_pos: RectPos = pos

        self._imgs: Tuple[pg.SurfaceType, ...] = imgs
        self.rect: pg.FRect = self._imgs[0].get_frect(**{self._init_pos.pos: self._init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self.img_i: int = 0
        self.hovering: bool = False

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        return [(self._imgs[self.img_i], self.rect.topleft)]

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
        '_text',
    )

    def __init__(
            self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType], text: str
        ) -> None:
        """
        creates surfaces, rect and text object
        takes position, two images and text
        """

        super().__init__(pos, imgs)

        self._text: Text = Text(RectPos(self.rect.left - 10, self.rect.centery, 'midright'), text)

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
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
        returns True if the checkbox was clicked
        """

        if not self.rect.collidepoint(mouse_info.xy):
            if self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.hovering = False

            return False

        if not self.hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self.hovering = True

        if mouse_info.released[0]:
            return True

        return False


class Button(Clickable):
    """
    class to create a button, when hovered changes image
    """

    __slots__ = (
        '_text',
    )

    def __init__(
            self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType],
            text: str, text_h: int=32
        ) -> None:
        """
        creates surfaces, rect and text object
        takes position, two images, text and optional text height
        """

        super().__init__(pos, imgs)

        self._text: Optional[Text]
        if not text:
            self._text = None
        else:
            self._text = Text(RectPos(*self.rect.center, 'center'), text, text_h)

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
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
        updates the button image if the mouse is hovering it
        takes mouse info
        returns whatever the button was clicked or not
        """

        if not self.rect.collidepoint(mouse_info.xy):
            if self.hovering:
                self.img_i = 0
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.hovering = False

            return False

        if not self.hovering:
            self.img_i = 1
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self.hovering = True

        return mouse_info.released[0]
