"""
class to simplify text rendering
renderers are cached
"""

import pygame as pg
from typing import Tuple, List, Dict, Final

from src.utils import RectPos, BlitSequence
from src.const import WHITE

RENDERERS_CACHE: Final[Dict[int, pg.Font]] = {}


class Text:
    """
    class to simplify text rendering
    """

    __slots__ = (
        '_init_pos', '_x', '_y', '_init_h', '_renderer', 'text', '_lines',
        '_imgs', '_rects', 'rect'
    )

    def __init__(self, pos: RectPos, text: str, h: int = 24) -> None:
        """
        creates the text
        takes position, text and optional height
        """

        self._init_pos: RectPos = pos
        self._x: float = self._init_pos.x
        self._y: float = self._init_pos.y

        self._init_h: int = h
        if self._init_h not in RENDERERS_CACHE:
            RENDERERS_CACHE[self._init_h] = pg.font.SysFont('helvetica', self._init_h)
        self._renderer: pg.Font = RENDERERS_CACHE[self._init_h]

        self.text: str = text
        self._lines: List[str] = self.text.split('\n')

        self._imgs: Tuple[pg.SurfaceType, ...] = tuple(
            self._renderer.render(line, True, WHITE) for line in self._lines
        )
        self._rects: list[pg.FRect] = []
        self.rect: pg.FRect = pg.FRect(0, 0, 0, 0)

        self._get_rects()

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(img, rect.topleft) for img, rect in zip(self._imgs, self._rects)]

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        h: int = int(self._init_h * win_ratio_h)
        self._x, self._y = self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h

        if h not in RENDERERS_CACHE:
            RENDERERS_CACHE[h] = pg.font.SysFont('helvetica', h)
        self._renderer = RENDERERS_CACHE[h]

        self._imgs = tuple(self._renderer.render(line, True, WHITE) for line in self._lines)
        self._get_rects()

    def _get_rects(self) -> None:
        """
        calculates rects and rect depending on the position coordinate
        """

        self._rects = []

        current_y: float = self._y
        rect_h: float = sum(img.get_height() for img in self._imgs)
        if 'bottom' in self._init_pos.coord:
            current_y -= rect_h - self._imgs[-1].get_height()
        elif self._init_pos.coord in ('midright', 'center', 'midleft'):
            current_y -= (rect_h - self._imgs[-1].get_height()) / 2

        for img in self._imgs:
            self._rects.append(img.get_frect(**{self._init_pos.coord: (self._x, current_y)}))
            current_y += self._rects[-1].h

        rect_x: float = min(rect.x for rect in self._rects)
        rect_y: float = min(rect.y for rect in self._rects)
        rect_w: float = max(rect.w for rect in self._rects)
        self.rect = pg.FRect(rect_x, rect_y, rect_w, rect_h)

    def move_rect(self, x: float, y: float, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        moves the rects and rect to a specific coordinate
        takes x, y and window size ratio
        """

        self._init_pos.x, self._init_pos.y = x / win_ratio_w, y / win_ratio_h
        self._x, self._y = x, y
        self._get_rects()

    def modify_text(self, text: str) -> None:
        """
        modifies text image and adjusts position
        takes text
        """

        self.text = text
        self._lines = self.text.split('\n')

        self._imgs = tuple(self._renderer.render(line, True, WHITE) for line in self._lines)
        self._get_rects()

    def get_pos_at(self, i: int) -> float:
        """
        gets x pos of the character at a given index
        only for single line text
        returns the x pos of the char at i
        """

        x: float = (
            self._rects[0].x + self._renderer.render(self._lines[0][:i], False, WHITE).get_width()
        )

        return x

    def get_closest(self, x: int) -> int:
        """
        calculates the index of the closest character to a given x
        only for single line text
        takes x position
        returns index of closest character (0 - len(text))
        """

        current_x: int = int(self._rects[0].x)
        for i, char in enumerate(self._lines[0]):
            next_x: int = current_x + self._renderer.render(char, False, WHITE).get_width()
            if x < next_x:
                if x - current_x < next_x - x:
                    return i
                return i + 1

            current_x = next_x

        return len(self._lines[0])
