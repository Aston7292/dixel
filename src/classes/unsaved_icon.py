"""Class to indicate an unsaved file."""

import pygame as pg
from typing import Optional

from src.utils import RectPos, resize_obj
from src.type_utils import XY, WH, LayeredBlitInfo
from src.consts import (
    WHITE, BG_LAYER, ANIMATION_I_GROW, ANIMATION_I_SHRINK_TO_MIN, ANIMATION_I_SHRINK_TO_0
)

class UnsavedIcon:
    """Class to indicate an unsaved file."""

    __slots__ = (
        "_radius", "_min_radius", "_max_radius", "_img", "rect", "color", "animation_i",
        "blit_sequence"
    )

    def __init__(self):
        """Creates image and rect."""

        self._radius: float = 8
        self._min_radius: int = round(self._radius)
        self._max_radius: int = round(self._radius + 5)

        # Surface is bigger to prevent cut offs
        self._img: pg.Surface = pg.Surface((self._radius * 2 + 1, self._radius * 2 + 1)).convert()
        self.rect: pg.Rect = pg.Rect(0, 0, *self._img.get_size())

        self.color: pg.Color = WHITE
        self.animation_i: Optional[int] = None

        self.blit_sequence: LayeredBlitInfo = [(self._img, self.rect, BG_LAYER)]

        self.set_radius(self._radius)

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        _xy: XY
        wh: WH

        _xy, wh = resize_obj(RectPos(0, 0, ""), 16, 16, win_w_ratio, win_h_ratio, True)
        self._img = pg.Surface(wh).convert()
        self.rect.size = wh

        self._radius = self.rect.w / 2 - 1
        self._max_radius = round(self._radius + 5)

        center: tuple[float, float] = (self.rect.w / 2, self.rect.h / 2)
        pg.draw.aacircle(self._img, self.color, center, self._radius)
        self.blit_sequence[0] = (self._img, self.rect, BG_LAYER)

    def set_radius(self, radius: float) -> None:
        """
        Sets the radius.

        Args:
            radius
        """

        self._radius = radius
        dim: int = round(self._radius * 2 + 1)  # Surface is bigger to prevent cut offs
        self._img = pg.Surface((dim, dim)).convert()
        self.rect.size = self._img.get_size()
        center: tuple[float, float] = (self.rect.w / 2, self.rect.h / 2)
        pg.draw.aacircle(self._img, self.color, center, self._radius)

        self.blit_sequence[0] = (self._img, self.rect, BG_LAYER)

    def animate(self, dt: float) -> None:
        """
        Plays the animation.

        Args:
            delta time
        """

        prev_radius: float = self._radius

        if self.animation_i == ANIMATION_I_GROW:
            self._radius += 0.15 * dt
            if self._radius >= self._max_radius:
                self._radius = self._max_radius
                self.animation_i = ANIMATION_I_SHRINK_TO_MIN
        elif self.animation_i == ANIMATION_I_SHRINK_TO_MIN:
            self._radius -= 0.15 * dt
            if self._radius <= self._min_radius:
                self._radius = self._min_radius
                self.color = WHITE
                self.animation_i = None
        elif self.animation_i == ANIMATION_I_SHRINK_TO_0:
            self._radius -= 0.15 * dt
            if self._radius <= 0:
                self._radius = 0
                self.color = WHITE
                self.animation_i = None

        if self._radius != prev_radius:
            prev_center: XY = self.rect.center
            self.set_radius(self._radius)
            self.rect.center = prev_center