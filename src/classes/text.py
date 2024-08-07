"""
class to simplify text rendering
renderers are cached
"""

import pygame as pg
from typing import Tuple, Dict, Final

from src.utils import RectPos
from src.const import ColorType, BlitSequence

WHITE: Final[ColorType] = (255, 255, 255)

RENDERERS_CACHE: Dict[int, pg.Font] = {}


class Text:
    """
    class to simplify text rendering
    """

    __slots__ = (
        '_renderer', '_text', 'surf', '_init_h', '_init_pos', '_pos', '_topleft'
    )

    def __init__(self, pos: RectPos, h: int, text: str) -> None:
        """
        creates text surface and rect
        takes position, height, text
        """

        self._init_pos: RectPos = pos
        self._pos: Tuple[float, float] = self._init_pos.xy
        self._init_h: int = h

        if self._init_h not in RENDERERS_CACHE:
            RENDERERS_CACHE[self._init_h] = pg.font.Font(size=self._init_h)
        self._renderer: pg.Font = RENDERERS_CACHE[self._init_h]
        self._text: str = text

        self.surf: pg.SurfaceType = self._renderer.render(self._text, True, WHITE)
        rect: pg.FRect = self.surf.get_frect(**{self._init_pos.pos: self._init_pos.xy})
        self._topleft: Tuple[float, float] = rect.topleft

    def blit(self) -> BlitSequence:
        """
        return a sequence to add in the main blit sequence
        """

        return [(self.surf, self._topleft)]

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        h: int = int(self._init_h * win_ratio_h)
        self._pos = (self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h)

        if h not in RENDERERS_CACHE:
            RENDERERS_CACHE[h] = pg.font.Font(size=h)
        self._renderer = RENDERERS_CACHE[h]

        self.surf = self._renderer.render(self._text, True, WHITE)
        rect: pg.FRect = self.surf.get_frect(**{self._init_pos.pos: self._pos})
        self._topleft = rect.topleft

    def modify_text(self, text: str) -> None:
        """
        modifies rendered text and adjusts position
        takes new text
        """

        self._text = text

        self.surf = self._renderer.render(self._text, True, WHITE)
        rect: pg.FRect = self.surf.get_frect(**{self._init_pos.pos: self._pos})
        self._topleft = rect.topleft
