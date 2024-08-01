'''
class to simplify text rendering
'''

import pygame as pg
from typing import Final

from src.utils import Point, RectPos, Size
from src.const import S_INIT_WIN, ColorType, BlitSequence

WHITE: Final[ColorType] = (255, 255, 255)


class Text:
    '''
    class to simplify text rendering
    '''

    __slots__ = (
        '_init_h', '_h', '_renderer', '_text', '_img', '_init_pos', '_pos', '_rect'
    )

    def __init__(self, h: int, text: str, pos: RectPos) -> None:
        '''
        creates text image and rect
        takes height, text and position
        '''

        self._init_h: int = h
        self._h: int = self._init_h
        self._renderer: pg.Font = pg.font.Font(None, self._h)

        self._text: str = text
        self._img: pg.SurfaceType = self._renderer.render(self._text, True, WHITE)

        self._init_pos: Point = Point(*pos.xy)
        self._pos: RectPos = pos
        self._rect: pg.Rect = self._img.get_rect(**{self._pos.pos: self._pos.xy})

    def blit(self) -> BlitSequence:
        '''
        return a sequence to add in the main blit sequence
        '''

        return ((self._img, self._rect.topleft),)

    def handle_resize(self, win_size: Size) -> None:
        '''
        resizes surfaces
        takes window size
        '''

        self._pos.xy = (
            round(self._init_pos.x * (win_size.w / S_INIT_WIN.w)),
            round(self._init_pos.y * (win_size.h / S_INIT_WIN.h))
        )
        self._h = round(self._init_h * (win_size.h / S_INIT_WIN.h))

        self._renderer = pg.font.Font(None, self._h)
        self.modify_text(self._text)

    def modify_text(self, text: str) -> None:
        '''
        modifies rendered text and adjusts position
        takes new text
        '''

        self._text = text
        self._img = self._renderer.render(self._text, True, WHITE)
        self._rect = self._img.get_rect(**{self._pos.pos: self._pos.xy})
