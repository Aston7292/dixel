"""Class to simplify text rendering, renderers are cached."""

import pygame as pg

from src.utils import RectPos, Ratio, resize_obj
from src.type_utils import LayeredBlitSequence
from src.consts import WHITE, BG_LAYER, TEXT_LAYER

renderers_cache: dict[int, pg.Font] = {}


class TextLabel:
    """Class to simplify text rendering."""

    __slots__ = (
        'init_pos', '_init_h', '_renderer', 'text', '_lines', '_imgs', 'rect', 'rects', '_layer'
    )

    def __init__(
            self, pos: RectPos, text: str, base_layer: int = BG_LAYER, h: int = 24
    ) -> None:
        """
        Creates the text images.

        Args:
            position, text, base_layer (default = BG_LAYER), height (default = 24)
        """

        self.init_pos: RectPos = pos
        self._init_h: int = h

        if self._init_h not in renderers_cache:
            renderers_cache[self._init_h] = pg.font.SysFont("helvetica", self._init_h)
        self._renderer: pg.Font = renderers_cache[self._init_h]

        self.text: str = text
        self._lines: tuple[str, ...] = tuple(self.text.split('\n'))

        self._imgs: tuple[pg.Surface, ...] = tuple(
            self._renderer.render(line, True, WHITE) for line in self._lines
        )
        self.rect: pg.Rect = pg.Rect()
        self.rects: list[pg.Rect] = []

        self._layer: int = base_layer + TEXT_LAYER

        self._get_rects((self.init_pos.x, self.init_pos.y))

    def blit(self) -> LayeredBlitSequence:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        return [(img, rect.topleft, self._layer) for img, rect in zip(self._imgs, self.rects)]

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        pos, (_, h) = resize_obj(self.init_pos, 0.0, self._init_h, win_ratio, True)

        if h not in renderers_cache:
            renderers_cache[h] = pg.font.SysFont("helvetica", h)
        self._renderer = renderers_cache[h]

        self._imgs = tuple(self._renderer.render(line, True, WHITE) for line in self._lines)
        self._get_rects(pos)

    def _get_rects(self, xy: tuple[int, int]) -> None:
        """
        Calculates the rects and rect depending on the position coordinate.

        Args:
            position
        """

        self.rects = []

        rect_w: int = max(img.get_width() for img in self._imgs)
        rect_h: int = sum(img.get_height() for img in self._imgs)
        self.rect = pg.Rect(0, 0, rect_w, rect_h)
        setattr(self.rect, self.init_pos.coord_type, xy)

        line_rect_y: int = self.rect.y
        for img in self._imgs:
            line_rect: pg.Rect = img.get_rect(topleft=(self.rect.x, line_rect_y))
            leftover_w: int = self.rect.w - line_rect.w
            if self.init_pos.coord_type in ('midtop', 'center', 'midbottom'):
                line_rect.x += round(leftover_w / 2.0)
            elif 'right' in self.init_pos.coord_type:
                line_rect.x += leftover_w

            self.rects.append(line_rect)
            line_rect_y += self.rects[-1].h

    def move_rect(self, x: int, y: int, win_ratio: Ratio) -> None:
        """
        Moves the rects and rect to a specific coordinate.

        Args:
            x, y, window size ratio
        """

        self.init_pos.x, self.init_pos.y = x, y
        xy: tuple[int, int] = (round(x * win_ratio.w), round(y * win_ratio.h))
        self._get_rects(xy)

    def set_text(self, text: str) -> None:
        """
        Sets the text and adjusts its position.

        Args:
            text
        """

        self.text = text
        self._lines = tuple(self.text.split('\n'))

        self._imgs = tuple(self._renderer.render(line, True, WHITE) for line in self._lines)
        xy: tuple[int, int] = getattr(self.rect, self.init_pos.coord_type)
        self._get_rects(xy)

    def get_pos_at(self, char_i: int) -> int:
        """
        Gets the x position of the character at a given index (only for single line text).

        Args:
            index
        Returns:
            character x
        """

        w: int = self._renderer.render(self._lines[0][:char_i], False, WHITE).get_width()

        return self.rects[0].x + w

    def get_closest_to(self, x: int) -> int:
        """
        Calculates the index of the closest character to a given x (only for single line text).

        Args:
            x
        Returns:
            index (0 - len(text))
        """

        current_x: int = self.rects[0].x
        for i, char in enumerate(self._lines[0]):
            next_x: int = current_x + self._renderer.render(char, False, WHITE).get_width()
            if x < next_x:
                return i if abs(x - current_x) < abs(x - next_x) else (i + 1)

            current_x = next_x

        return len(self._lines[0])
