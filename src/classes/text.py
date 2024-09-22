"""
Class to simplify text rendering, renderers are cached
"""

import pygame as pg

from src.utils import RectPos
from src.type_utils import LayeredBlitSequence, LayerSequence
from src.consts import WHITE, BG_LAYER, TEXT_LAYER

renderers_cache: dict[int, pg.Font] = {}


class Text:
    """
    Class to simplify text rendering
    """

    __slots__ = (
        '_init_pos', '_x', '_y', '_init_h', '_renderer', 'text', '_lines',
        '_imgs', 'rects', 'rect', '_layer'
    )

    def __init__(
        self, pos: RectPos, text: str, base_layer: int = BG_LAYER, h: int = 24
    ) -> None:
        """
        Creates the text images
        Args:
            position, text, base_layer (default = BG_LAYER), height (default = 24)
        """

        self._init_pos: RectPos = pos
        self._x: float = self._init_pos.x
        self._y: float = self._init_pos.y

        self._init_h: int = h
        if self._init_h not in renderers_cache:
            renderers_cache[self._init_h] = pg.font.SysFont('helvetica', self._init_h)
        self._renderer: pg.Font = renderers_cache[self._init_h]

        self.text: str = text
        self._lines: tuple[str, ...] = tuple(self.text.split('\n'))

        self._imgs: tuple[pg.Surface, ...] = tuple(
            self._renderer.render(line, True, WHITE) for line in self._lines
        )
        self.rects: list[pg.FRect] = []
        self.rect: pg.FRect = pg.FRect(0.0, 0.0, 0.0, 0.0)

        self._layer: int = base_layer + TEXT_LAYER

        self._get_rects()

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return [(img, rect.topleft, self._layer) for img, rect in zip(self._imgs, self.rects)]

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
        Args:
            window width ratio, window height ratio
        """

        h: int = int(self._init_h * win_ratio_h)
        self._x, self._y = self._init_pos.x * win_ratio_w, self._init_pos.y * win_ratio_h

        if h not in renderers_cache:
            renderers_cache[h] = pg.font.SysFont('helvetica', h)
        self._renderer = renderers_cache[h]

        self._imgs = tuple(self._renderer.render(line, True, WHITE) for line in self._lines)
        self._get_rects()

    def print_layer(self, name: str, counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, self._layer, counter)]

    def _get_rects(self) -> None:
        """
        Calculates the rects and rect depending on the position's coordinate
        """

        self.rects = []

        current_y: float = self._y
        tot_h: float = sum(img.get_height() for img in self._imgs)
        if 'bottom' in self._init_pos.coord_type:
            current_y -= tot_h - self._imgs[-1].get_height()
        elif self._init_pos.coord_type in ('midright', 'center', 'midleft'):
            current_y -= (tot_h - self._imgs[-1].get_height()) / 2.0

        for img in self._imgs:
            self.rects.append(img.get_frect(**{self._init_pos.coord_type: (self._x, current_y)}))
            current_y += self.rects[-1].h

        x: float = min(rect.x for rect in self.rects)
        y: float = min(rect.y for rect in self.rects)
        max_w: float = max(rect.w for rect in self.rects)
        self.rect = pg.FRect(x, y, max_w, tot_h)

    def move_rect(self, x: float, y: float, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Moves the rects and rect to a specific coordinate
        Args:
            x, y, window width ratio, window height ratio
        """

        self._init_pos.x, self._init_pos.y = x / win_ratio_w, y / win_ratio_h
        self._x, self._y = x, y
        self._get_rects()

    def set_text(self, text: str) -> None:
        """
        Sets the text and adjusts its position
        Args:
            text
        """

        self.text = text
        self._lines = tuple(self.text.split('\n'))

        self._imgs = tuple(self._renderer.render(line, True, WHITE) for line in self._lines)
        self._get_rects()

    def get_pos_at(self, char_i: int) -> float:
        """
        Gets the x position of the character at a given index (only for single line text)
        Args:
            index
        Returns:
            x
        """

        w: int = self._renderer.render(self._lines[0][:char_i], False, WHITE).get_width()

        return self.rects[0].x + w

    def get_closest_to(self, x: int) -> int:
        """
        Calculates the index of the closest character to a given x (only for single line text)
        Args:
            x
        Returns:
            index (0 - len(text))
        """

        current_x: int = int(self.rects[0].x)
        for i, char in enumerate(self._lines[0]):
            next_x: int = current_x + self._renderer.render(char, False, WHITE).get_width()
            if x < next_x:
                return i if abs(x - current_x) < abs(x - next_x) else i + 1

            current_x = next_x

        return len(self._lines[0])
