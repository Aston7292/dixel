"""Class to indicate an unsaved file."""

from typing import Self

from pygame import Surface, Rect, Color, draw, SYSTEM_CURSOR_ARROW

from src.obj_utils import ObjInfo, resize_obj
from src.type_utils import XY, BlitInfo, RectPos
import src.vars as my_vars
from src.consts import WHITE, BG_LAYER, ELEMENT_LAYER, ANIMATION_GROW, ANIMATION_SHRINK


class UnsavedIcon:
    """Class to indicate an unsaved file."""

    __slots__ = (
        "init_radius", "_normal_radius", "_radius", "_min_radius", "_max_radius",
        "rect", "frame_rect",
        "_color", "_animation_i",
        "hover_rects", "layer", "blit_sequence",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW
    objs_info: list[ObjInfo] = []

    def __init__(self: Self) -> None:
        """Creates image and rect."""

        self.init_radius: int = 8
        self._normal_radius: float = self.init_radius
        self._radius: float = 0
        self._min_radius: float = self._normal_radius
        self._max_radius: float = self._normal_radius * 1.5

        img: Surface = Surface((
            # Prevents cutoffs
            round((self._radius * 2) + 1),
            round((self._radius * 2) + 1),
        ))
        self.rect: Rect = Rect(
            0, 0,
            # Prevents cutoffs
            round((self._max_radius * 2) + 1),
            round((self._max_radius * 2) + 1)
        )
        self.frame_rect: Rect = Rect(0, 0, *img.get_size())
        self.frame_rect.center = self.rect.center

        self._color: Color = WHITE
        self._animation_i: int | None = None

        self.hover_rects: tuple[Rect, ...] = ()
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = [(img, self.frame_rect, ELEMENT_LAYER)]

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self: Self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        _xy: XY

        radius_ratio: float     = self._radius     / self._normal_radius
        min_radius_ratio: float = self._min_radius / self._normal_radius
        max_radius_ratio: float = self._max_radius / self._normal_radius

        # Position is set manually after resize
        _xy, (self._normal_radius, self._normal_radius) = resize_obj(
            RectPos(0, 0, "topleft"), self.init_radius, self.init_radius,
            win_w_ratio, win_h_ratio, should_keep_wh_ratio=True
        )

        self._min_radius = self._normal_radius * min_radius_ratio
        self._max_radius = self._normal_radius * max_radius_ratio

        self.rect.size = (
            # Prevents cutoffs
            round((self._max_radius * 2) + 1),
            round((self._max_radius * 2) + 1),
        )
        self.set_radius(self._normal_radius * radius_ratio)

    def set_radius(self: Self, radius: float) -> None:
        """
        Sets the radius and refreshes image and rect.

        Args:
            radius
        """

        self._radius = radius

        img: Surface = Surface((
            # Prevents cutoffs
            round((self._radius * 2) + 1),
            round((self._radius * 2) + 1),
        ))
        self.frame_rect.size = img.get_size()
        self.frame_rect.center = self.rect.center
        draw.aacircle(
            img, self._color,
            (self.frame_rect.w / 2, self.frame_rect.h / 2), self._radius
        )

        self.blit_sequence = (
            [] if self.frame_rect.w == 0 else
            [(img, self.frame_rect, ELEMENT_LAYER)]
        )

    def set_animation(self: Self, i: int, color: Color, should_go_to_0: bool) -> None:
        """
        Sets the animation info.

        Args:
            index, color, go to 0 flag
        """

        self._animation_i = i
        self._color = color
        self._min_radius = 0 if should_go_to_0 else self._normal_radius

    def animate(self: Self) -> None:
        """Plays either the grow or shrink animation."""

        prev_radius: float = self._radius

        # The animation is fast at the start and slow at the end
        if self._animation_i == ANIMATION_GROW:
            grow_progress: float   = (self._max_radius - self._radius    ) / self._max_radius
            self._radius += (0.25 + grow_progress  ) * my_vars.dt

            if self._radius >= self._max_radius:
                self._radius = self._max_radius
                self._animation_i = ANIMATION_SHRINK
        elif self._animation_i == ANIMATION_SHRINK:
            shrink_progress: float = (self._radius     - self._min_radius) / self._max_radius
            self._radius -= (0.25 + shrink_progress) * my_vars.dt

            if self._radius <= self._min_radius:
                self._radius = self._min_radius
                self._color = WHITE
                self._animation_i = None

        if self._radius != prev_radius:
            self.set_radius(self._radius)
