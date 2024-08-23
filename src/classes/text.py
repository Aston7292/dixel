"""
class to simplify text rendering
renderers are cached
"""

import pygame as pg
from typing import Tuple, Dict, Final

from src.utils import RectPos, BlitSequence
from src.const import WHITE

RENDERERS_CACHE: Final[Dict[int, pg.Font]] = {}


class Text:
    """
    class to simplify text rendering
    """

    __slots__ = (
        '_init_pos', '_pos', '_init_h', '_renderer', 'text', '_surf', 'rect'
    )

    def __init__(self, pos: RectPos, text: str, h: int = 32) -> None:
        """
        creates text surface and rect
        takes position, text and optional height
        """

        self._init_pos: RectPos = pos
        self._pos: Tuple[float, float] = self._init_pos.xy

        self._init_h: int = h
        if self._init_h not in RENDERERS_CACHE:
            RENDERERS_CACHE[self._init_h] = pg.font.Font(size=self._init_h)
        self._renderer: pg.Font = RENDERERS_CACHE[self._init_h]

        self.text: str = text
        self._surf: pg.SurfaceType = self._renderer.render(self.text, True, WHITE)
        self.rect: pg.FRect = self._surf.get_frect(**{self._init_pos.coord: self._init_pos.xy})

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        return [(self._surf, self.rect.topleft)]

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

        self._surf = self._renderer.render(self.text, True, WHITE)
        self.rect = self._surf.get_frect(**{self._init_pos.coord: self._pos})

    def move_rect(self, x: float, y: float, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        moves the rect to a specific coordinate
        takes x, y and window size ratio
        """

        self._init_pos.x, self._init_pos.y = x / win_ratio_w, y / win_ratio_h
        self._pos = (x, y)
        self.rect = self._surf.get_frect(**{self._init_pos.coord: self._pos})

    def modify_text(self, text: str) -> None:
        """
        modifies text image and adjusts position
        takes new text
        """

        self.text = text

        self._surf = self._renderer.render(self.text, True, WHITE)
        self.rect = self._surf.get_frect(**{self._init_pos.coord: self._pos})

    def get_pos_at(self, i: int) -> float:
        """
        get x pos of the character at a given index
        returns the x pos of the char at i
        """

        sub_string: str = self.text[:i]

        return self.rect.x + self._renderer.render(sub_string, False, WHITE).get_width()

    def get_closest(self, x: int) -> int:
        """
        get the index of the closest character to a given x
        takes x position
        returns index of closest character (0 - len(text))
        """

        current_x: int = int(self.rect.x)
        for i, char in enumerate(self.text):
            next_x: int = current_x + self._renderer.render(char, False, WHITE).get_width()
            if x < next_x:
                if x - current_x < next_x - x:
                    return i
                return i + 1

            current_x = next_x

        return len(self.text)
