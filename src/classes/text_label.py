"""Class to simplify text rendering, renderers are cached."""

from typing import Final, Optional

import pygame as pg

from src.utils import RectPos, resize_obj
from src.type_utils import XY, WH, LayeredBlitInfo
from src.consts import WHITE, BG_LAYER, TEXT_LAYER

RENDERERS_CACHE: Final[dict[int, pg.Font]] = {}


class TextLabel:
    """Class to simplify text rendering."""

    __slots__ = (
        "init_pos", "_init_h", "_renderer", "text", "_bg_color", "_imgs", "rect", "_rects", "layer"
    )

    def __init__(
            self, pos: RectPos, text: str, base_layer: int = BG_LAYER, h: int = 25,
            bg_color: Optional[pg.Color] = None
    ) -> None:
        """
        Creates the text images.

        Args:
            position, text, base_layer (default = BG_LAYER), height (default = 25),
            background color (default = None)
        """

        self.init_pos: RectPos = pos
        self._init_h: int = h

        if self._init_h not in RENDERERS_CACHE:
            RENDERERS_CACHE[self._init_h] = pg.font.SysFont("helvetica", self._init_h)
        self._renderer: pg.Font = RENDERERS_CACHE[self._init_h]

        self.text: str = text
        self._bg_color: Optional[pg.Color] = bg_color

        lines: list[str] = self.text.split("\n")

        self._imgs: list[pg.Surface] = [
            self._renderer.render(line, True, WHITE, self._bg_color) for line in lines
        ]
        self.rect: pg.Rect = pg.Rect()
        self._rects: list[pg.Rect] = []

        self.layer: int = base_layer + TEXT_LAYER

        self._refresh_rects((self.init_pos.x, self.init_pos.y))

    @property
    def blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        return [(img, rect, self.layer) for img, rect in zip(self._imgs, self._rects)]

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY
        _w: int
        h: int

        xy, (_w, h) = resize_obj(self.init_pos, 0, self._init_h, win_w_ratio, win_h_ratio, True)
        if h not in RENDERERS_CACHE:
            RENDERERS_CACHE[h] = pg.font.SysFont("helvetica", h)
        self._renderer = RENDERERS_CACHE[h]

        lines: list[str] = self.text.split("\n")
        self._imgs = [self._renderer.render(line, True, WHITE, self._bg_color) for line in lines]
        self._refresh_rects(xy)

    def _refresh_rects(self, xy: XY) -> None:
        """
        Refreshes the rects and rect depending on the position coordinate.

        Args:
            xy
        """

        img_width: int
        img_height: int

        img_sizes: list[XY] = [img.get_size() for img in self._imgs]
        imgs_widths: list[int] = [img_width for img_width, _img_height in img_sizes]
        imgs_heights: list[int] = [img_height for _img_width, img_height in img_sizes]

        self.rect.size = (max(imgs_widths), sum(imgs_heights))
        setattr(self.rect, self.init_pos.coord_type, xy)

        self._rects = []
        line_rect_y: int = self.rect.y
        for img_width, img_height in img_sizes:
            # Create full line rect to get the position at coord_type
            # Shrink it to the line width and move it there

            line_rect: pg.Rect = pg.Rect(self.rect.x, line_rect_y, self.rect.w, img_height)
            line_xy: XY = getattr(line_rect, self.init_pos.coord_type)

            line_rect.w = img_width
            setattr(line_rect, self.init_pos.coord_type, line_xy)
            self._rects.append(line_rect)

            line_rect_y += line_rect.h

    def move_rect(self, init_x: int, init_y: int, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Moves the rects and rect to a specific coordinate.

        Args:
            initial x, initial y, window width ratio, window height ratio
        """

        line_init_pos: RectPos
        xy: XY
        _wh: WH
        rect: pg.Rect

        self.init_pos.x, self.init_pos.y = init_x, init_y  # Modifying init_pos is more accurate
        line_init_pos = RectPos(self.init_pos.x, self.init_pos.y, self.init_pos.coord_type)

        xy, _wh = resize_obj(line_init_pos, 0, 0, win_w_ratio, win_h_ratio)
        setattr(self.rect, line_init_pos.coord_type, xy)
        for rect in self._rects:
            xy, _wh = resize_obj(line_init_pos, 0, 0, win_w_ratio, win_h_ratio)
            setattr(rect, line_init_pos.coord_type, xy)
            line_init_pos.y += rect.h

    def set_text(self, text: str) -> None:
        """
        Sets the text and adjusts its position.

        Args:
            text
        """

        self.text = text

        lines: list[str] = self.text.split("\n")
        self._imgs = [self._renderer.render(line, True, WHITE, self._bg_color) for line in lines]
        xy: XY = getattr(self.rect, self.init_pos.coord_type)
        self._refresh_rects(xy)

    def get_x_at(self, i: int) -> int:
        """
        Gets the x coordinate of the character at a given index (only for single line text).

        Args:
            index
        Returns:
            character x
        """

        return self.rect.x + self._renderer.render(self.text[:i], False, WHITE, WHITE).get_width()

    def get_closest_to(self, x: int) -> int:
        """
        Calculates the index of the closest character to a given x (only for single line text).

        Args:
            x coordinate
        Returns:
            index (0 - len(text))
        """

        i: int
        char: str

        prev_x: int = self.rect.x
        for i, char in enumerate(self.text):
            current_x: int = prev_x + self._renderer.render(char, False, WHITE, WHITE).get_width()
            if x < current_x:
                return i if abs(x - prev_x) < abs(x - current_x) else i + 1

            prev_x = current_x

        return len(self.text)
