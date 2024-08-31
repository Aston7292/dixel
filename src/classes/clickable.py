"""
class to create various clickable objects
"""

import pygame as pg
from abc import ABC, abstractmethod
from typing import Tuple, Optional

from src.classes.text import Text
from src.utils import RectPos, Size, MouseInfo, BlitSequence


class Clickable(ABC):
    """
    abstract class to create and object that changes between two images
    includes: blit() -> BlitSequence, handle_resize(window size ratio) -> None
    children should include: upt(mouse info) -> bool
    """

    __slots__ = (
        'init_pos', '_imgs', 'rect', '_init_size', 'img_i', 'hovering'
    )

    def __init__(self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType]) -> None:
        """
        creates the object
        takes position and two images
        """

        self.init_pos: RectPos = pos

        self._imgs: Tuple[pg.SurfaceType, ...] = imgs
        self.rect: pg.FRect = self._imgs[0].get_frect(**{self.init_pos.coord: self.init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self.img_i: int = 0
        self.hovering: bool = False

    @abstractmethod
    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        return [(self._imgs[self.img_i], self.rect.topleft)]

    @abstractmethod
    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        size: Tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: Tuple[float, float] = (self.init_pos.x * win_ratio_w, self.init_pos.y * win_ratio_h)

        self._imgs = tuple(pg.transform.scale(img, size) for img in self._imgs)
        self.rect = self._imgs[0].get_frect(**{self.init_pos.coord: pos})

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
    class to create a checkbox with text on top
    """

    __slots__ = (
        'ticked_on', '_text',
    )

    def __init__(
            self, pos: RectPos, imgs: Tuple[pg.SurfaceType, pg.SurfaceType], text: str
    ) -> None:
        """
        creates the checkbox and text
        takes position, two images and text
        """

        super().__init__(pos, imgs)

        self.ticked_on: bool = bool(self.img_i)
        self._text: Text = Text(
            RectPos(self.rect.centerx, self.rect.y - 5.0, 'midbottom'), text, 16
        )

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

    def upt(self, mouse_info: MouseInfo, shortcut: bool = False) -> bool:
        """
        changes the checkbox image when clicked
        takes mouse info and optional shortcut bool
        returns True if the checkbox was ticked on
        """

        if shortcut:
            self.ticked_on = not self.ticked_on
            self.img_i = int(self.ticked_on)

            return self.ticked_on

        if not self.rect.collidepoint(mouse_info.xy):
            if self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.hovering = False

            return False

        if not self.hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self.hovering = True

        if mouse_info.released[0]:
            self.ticked_on = not self.ticked_on
            self.img_i = int(self.ticked_on)

            return self.ticked_on

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
            text: str, text_h: int = 24
    ) -> None:
        """
        creates the button and text
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

    def move_rect(self, x: float, y: float, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        moves the rect to a specific coordinate
        takes x, y and window size ratio
        """

        self.init_pos.x, self.init_pos.y = x / win_ratio_w, y / win_ratio_h
        setattr(self.rect, self.init_pos.coord, (x, y))
        if self._text:
            self._text.move_rect(*self.rect.center, win_ratio_w, win_ratio_h)

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
