'''
class to simplify text rendering
'''

import pygame as pg
from typing import Tuple, Final

from const import S_INIT_WIN, ColorType, BlitPair

FONT_RATIO: Final[int] = S_INIT_WIN.h // 32
WHITE: Final[ColorType] = (255, 255, 255)

class Text:
    '''
    class to simplify text rendering
    '''

    __slots__ = (
        '_text', '_renderer', '_img', '_pos'
    )

    def __init__(self, text: str, pos: Tuple[int, int]) -> None:
        '''
        creates text image
        takes text and position
        '''

        self._text: str = text
        self._renderer: pg.Font = pg.font.Font(None, S_INIT_WIN.h // FONT_RATIO)
        self._img: pg.SurfaceType = self._renderer.render(self._text, True, WHITE)

        self._pos: Tuple[int, int] = pos

    def blit(self) -> BlitPair:
        '''
        return a pair to add in the blit sequence
        '''

        return self._img, self._pos

    def handle_resize(self, new_h: int):
        '''
        resizes objects
        '''

        self._renderer = pg.font.Font(None, new_h // FONT_RATIO)
        self.modify_text(self._text)

    def modify_text(self, text: str) -> None:
        '''
        modifies rendered text
        takes new text
        '''

        self._img = self._renderer.render(text, True, WHITE)
