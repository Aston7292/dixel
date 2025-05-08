"""Class to indicate an unsaved file."""

import pygame as pg
from typing import Optional

from src.utils import RectPos, resize_obj
from src.type_utils import XY, BlitInfo
from src.consts import WHITE, ELEMENT_LAYER, ANIMATION_I_GROW, ANIMATION_I_SHRINK


class UnsavedIcon:
    """Class to indicate an unsaved file."""

    __slots__ = (
        "_init_radius", "_radius", "_min_radius", "_max_radius", "rect", "frame_rect", "_color",
        "_animation_i", "_normal_radius", "blit_sequence", "_min_win_ratio"
    )

    def __init__(self) -> None:
        """Creates image and rect."""

        self._init_radius: int = 8
        self._normal_radius: float = self._init_radius
        self._radius: float = self._normal_radius
        self._min_radius: float = self._normal_radius
        self._max_radius: float = self._normal_radius * 1.5

        # Prevents cutoffs
        dim: int = self._radius * 2 + 1
        max_dim: int = round(self._max_radius * 2 + 1)

        img: pg.Surface = pg.Surface((dim, dim)).convert()
        self.rect: pg.Rect = pg.Rect(0, 0, max_dim, max_dim)
        self.frame_rect: pg.Rect = pg.Rect(0, 0, *img.get_size())
        self.frame_rect.center = self.rect.center

        self._color: pg.Color = WHITE
        self._animation_i: Optional[int] = None

        self.blit_sequence: list[BlitInfo] = [(img, self.frame_rect, ELEMENT_LAYER)]
        self._min_win_ratio: float = 1

        self.set_radius(self._radius)

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY

        self._min_win_ratio = min(win_w_ratio, win_h_ratio)

        radius_ratio: float = self._radius / self._normal_radius
        min_radius_ratio: float = self._min_radius / self._normal_radius
        max_radius_ratio: float = self._max_radius / self._normal_radius
        xy, (self._normal_radius, self._normal_radius) = resize_obj(
            RectPos(0, 0, ""), self._init_radius, self._init_radius, win_w_ratio, win_h_ratio, True
        )

        self._min_radius = self._normal_radius * min_radius_ratio
        self._max_radius = self._normal_radius * max_radius_ratio

        max_dim: int = round(self._max_radius * 2 + 1)
        self.rect.size = (max_dim, max_dim)
        self.set_radius(self._normal_radius * radius_ratio)

    def set_radius(self, radius: float) -> None:
        """
        Sets the radius and refreshes image and rect, position should be reset manually.

        Args:
            radius
        """

        self._radius = radius

        dim: int = round(self._radius * 2 + 1)  # Prevent cutoffs
        img: pg.Surface = pg.Surface((dim, dim)).convert()
        self.frame_rect.size = (dim, dim)
        self.frame_rect.center = self.rect.center

        center: tuple[float, float] = (self.frame_rect.w / 2, self.frame_rect.h / 2)
        pg.draw.aacircle(img, self._color, center, self._radius)

        self.blit_sequence[0] = (img, self.frame_rect, ELEMENT_LAYER)

    def set_animation(self, i: int, color: pg.Color, shrink_to_0: bool) -> None:
        """
        Sets the animation info.

        Args:
            index, color, shrink to 0 flag
        """

        self._animation_i = i
        self._color = color
        self._min_radius = 0 if shrink_to_0 else self._normal_radius

    def animate(self, dt: float) -> None:
        """
        Plays the animation.

        Args:
            delta time
        """

        progress: float

        prev_radius: float = self._radius

        # The animation is fast at the start and slow at the end
        if self._animation_i == ANIMATION_I_GROW:
            progress = (self._max_radius - self._radius) / self._max_radius
            self._radius += (0.25 + progress) * dt

            if self._radius >= self._max_radius:
                self._radius = self._max_radius
                self._animation_i = ANIMATION_I_SHRINK
        elif self._animation_i == ANIMATION_I_SHRINK:
            progress = (self._radius - self._min_radius) / self._max_radius
            self._radius -= (0.25 + progress) * dt

            if self._radius <= self._min_radius:
                self._radius = self._min_radius
                self._color = WHITE
                self._animation_i = None

        if self._radius != prev_radius:
            self.set_radius(self._radius)
