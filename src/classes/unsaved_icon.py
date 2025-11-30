"""Class to indicate an unsaved file."""

from math import ceil
from typing import Self, Final

from pygame import Surface, Rect, Color, draw, SYSTEM_CURSOR_ARROW

import src.obj_utils as objs
import src.vars as my_vars
from src.obj_utils import ObjInfo, resize_obj
from src.type_utils import XY, WH, BlitInfo, RectPos
from src.consts import (
    WHITE,
    BG_LAYER, ELEMENT_LAYER,
    ANIMATION_GROW, ANIMATION_SHRINK
)

INIT_DIM: Final[int] = 16


class UnsavedIcon:
    """Class to indicate an unsaved file."""

    __slots__ = (
        "init_pos",
        "_scale", "_min_scale", "_max_scale",
        "_rect", "_frame_rect",
        "_color", "_animation_i",
        "hover_rects", "layer", "blit_sequence",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW
    objs_info: tuple[ObjInfo, ...] = ()

    def __init__(self: Self) -> None:
        """Creates image and rect."""

        self.init_pos: RectPos = RectPos(0, 0, "midleft")

        self._scale: float = 1
        self._min_scale: float = 1
        self._max_scale: float = 1.15

        img: Surface = Surface((
            ceil(INIT_DIM * self._scale * my_vars.min_win_ratio),
            ceil(INIT_DIM * self._scale * my_vars.min_win_ratio),
        ))
        self._rect: Rect = Rect(
            0, 0,
            ceil(INIT_DIM * self._max_scale * my_vars.min_win_ratio),
            ceil(INIT_DIM * self._max_scale * my_vars.min_win_ratio),
        )
        self._frame_rect: Rect = Rect(0, 0, *img.get_size())
        self._frame_rect.center = self._rect.center

        self._color: Color = WHITE
        self._animation_i: int = ANIMATION_GROW

        self.hover_rects: tuple[Rect, ...] = ()
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = [(img, self._frame_rect, ELEMENT_LAYER)]

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self: Self) -> None:
        """Resizes the object."""

        self._rect.size = (
            ceil(INIT_DIM * self._max_scale * my_vars.min_win_ratio),
            ceil(INIT_DIM * self._max_scale * my_vars.min_win_ratio),
        )
        self.set_scale(self._scale)

    def move_rect(self: Self, init_x: int, init_y: int, should_scale: bool) -> None:
        """
        Moves the rect and frame_rect to a specific coordinate.

        Args:
            initial x, initial y, scale flag
        """

        xy: XY

        self.init_pos.x, self.init_pos.y = init_x, init_y  # More accurate

        if should_scale:
            xy = (
                round(self.init_pos.x * my_vars.win_w_ratio),
                round(self.init_pos.y * my_vars.win_h_ratio),
            )
        else:
            xy = (self.init_pos.x, self.init_pos.y)
        setattr(self._rect, self.init_pos.coord_type, xy)
        self._frame_rect.center = self._rect.center

    def set_scale(self: Self, scale: float) -> None:
        """
        Sets the scale and refreshes image and rect.

        Args:
            scale
        """

        self._scale = scale

        img: Surface = Surface((
            ceil(INIT_DIM * self._scale * my_vars.min_win_ratio),
            ceil(INIT_DIM * self._scale * my_vars.min_win_ratio),
        ))
        self._frame_rect.size = img.get_size()
        self._frame_rect.center = self._rect.center

        draw.aacircle(
            img, self._color,
            (self._frame_rect.w / 2, self._frame_rect.h / 2), (img.get_width() - 1) / 2
        )

        self.blit_sequence = (
            [] if self._frame_rect.w == 0 else
            [(img, self._frame_rect, ELEMENT_LAYER)]
        )

    def set_animation(self: Self, animation_i: int, color: Color, should_go_to_0: bool) -> None:
        """
        Sets the animation info.

        Args:
            animation index, color, go to 0 flag
        """

        self._animation_i = animation_i
        self._color = color
        self._min_scale = 0 if should_go_to_0 else 1
        objs.animating_objs.add(self)

    def animate(self: Self, dt: float) -> None:
        """
        Plays a frame of the active animation.

        Args:
            delta time
        """

        prev_scale: float = self._scale

        # The animation is fast at the start and slow at the end
        if self._animation_i == ANIMATION_GROW:
            grow_progress: float = (self._max_scale - self._scale) / self._max_scale
            self._scale += (0.02 + (grow_progress * 0.2)) * dt
            if self._scale >= self._max_scale:
                self._scale = self._max_scale
                self._animation_i = ANIMATION_SHRINK
        elif self._animation_i == ANIMATION_SHRINK:
            shrink_progress: float = (self._scale - self._min_scale) / self._max_scale
            self._scale -= (0.02 + (shrink_progress * 0.2)) * dt
            if self._scale <= self._min_scale:
                self._scale = self._min_scale
                self._color = WHITE
                objs.animating_objs.remove(self)

        if self._scale != prev_scale:
            self.set_scale(self._scale)
