'''
class to create a button, when hovered changes image and text appears on top of it
'''

import pygame as pg
from typing import Tuple

from src.classes.text import Text
from src.utils import Point, RectPos
from src.const import BlitSequence


class Button:
    '''
    class to create a button, when hovered changes image and text appears on top of it
    '''

    __slots__ = (
        '_imgs', '_img_i', '_pos', '_rect', '_can_click', '_text'
    )

    def __init__(
        self, imgs: Tuple[pg.SurfaceType, pg.SurfaceType], pos: RectPos, text: str
    ) -> None:
        '''
        creates button rect and text object
        takes two images, position and text
        '''

        self._imgs: Tuple[pg.SurfaceType, pg.SurfaceType] = imgs
        self._img_i = 0

        self._pos: RectPos = pos
        self._rect: pg.Rect = self._imgs[0].get_rect(**{self._pos.pos: self._pos.xy})

        self._can_click: bool = True

        self._text = Text(32, text, RectPos(self._rect.midtop, 'midbottom'))

    def blit(self) -> BlitSequence:
        '''
        return a sequence to add in the main blit sequence
        '''

        sequence: BlitSequence = ((self._imgs[self._img_i], self._rect.topleft),)
        if self._img_i == 1:
            sequence += self._text.blit()

        return sequence

    def click(self, mouse_pos: Point, mouse_buttons: Tuple[bool, bool, bool]) -> bool:
        '''
        updates the button image if the mouse is hovering it
        takes mouse position and buttons state
        returns whatever the button was clicked or not
        '''

        if not self._rect.collidepoint(mouse_pos.xy):
            self._img_i = 0
            return False

        self._img_i = 1

        if not mouse_buttons[0]:
            self._can_click = True
            return False

        if not self._can_click:
            return False

        self._can_click = False

        return True
