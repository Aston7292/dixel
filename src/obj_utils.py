"""Functions/Classes shared between files to manage objects."""

from abc import ABC
from math import ceil
from typing import Self

from pygame import Rect, SYSTEM_CURSOR_ARROW

import src.vars as my_vars
from src.type_utils import XY, WH, BlitInfo, RectPos
from src.consts import BG_LAYER

state_i: int = 0
states_objs: tuple[tuple[UIElement, ...], ...] = ((),)
state_active_objs: tuple[UIElement, ...] = ()
animating_objs: set[UIElement] = set()


class UIElement(ABC):
    """Base class for UI elements."""

    __slots__ = (
        "init_pos",
        "hover_rects", "layer", "cursor_type", "blit_sequence", "sub_objs",
        "is_active", "should_follow_parent",
    )

    def __init__(self: Self) -> None:
        """Initializes all the default attributes of UI elements."""

        self.init_pos: RectPos = RectPos(0, 0, "topleft")

        self.hover_rects: tuple[Rect, ...] = ()
        self.layer: int = BG_LAYER
        self.cursor_type: int = SYSTEM_CURSOR_ARROW
        self.blit_sequence: list[BlitInfo] = []
        self.sub_objs: tuple[UIElement , ...] = ()

        self.is_active: bool = True
        self.should_follow_parent: bool = True

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self: Self) -> None:
        """Resizes the object."""

    def move_to(self: Self, _init_x: int, _init_y: int, _should_scale: bool) -> None:
        """
        Moves the object to a specific coordinate.

        Args:
            initial x, initial y, scale flag
        """

    def set_layer(self: Self, _layer: int) -> None:
        """
        Sets the object layer.

        Args:
            layer
        """

    def animate(self: Self, _dt: float) -> None:
        """
        Plays a frame of the active animation.

        Args:
            delta time
        """

    def reset_animation(self: Self) -> None:
        """Resets the animation."""

    def rec_resize(self: Self) -> None:
        """Resizes an object and its sub objects."""

        objs_list: list[UIElement] = [self]
        while objs_list != []:
            obj: UIElement = objs_list.pop()
            obj.resize()
            objs_list.extend([obj for obj in obj.sub_objs])

    def rec_move_to(self: Self, init_x: int, init_y: int, should_scale: bool = True) -> None:
        """
        Moves an object and its sub objects to a specific coordinate.

        Args:
            object, initial x, initial y, scale flag (default = True)
        """

        objs_list: list[UIElement] = [self]
        change_x: int = 0
        change_y: int = 0
        while objs_list != []:
            obj: UIElement = objs_list.pop()
            if obj.should_follow_parent or obj == self:
                if obj == self:
                    change_x, change_y = init_x - obj.init_pos.x, init_y - obj.init_pos.y
                    obj.move_to(init_x, init_y, should_scale)
                else:
                    obj.move_to(obj.init_pos.x + change_x, obj.init_pos.y + change_y, should_scale)

                objs_list.extend(obj.sub_objs)

    def rec_set_layer(self: Self, layer: int) -> None:
        """
        Sets the layer for an object and its sub objects.

        Args:
            object, layer
        """

        objs_list: list[UIElement] = [self]
        layer_offset: int = layer - self.layer
        while objs_list != []:
            obj: UIElement = objs_list.pop()
            obj.set_layer(obj.layer + layer_offset)
            objs_list.extend(obj.sub_objs)

    def rec_set_active(self: Self, should_activate: bool) -> None:
        """
        Sets the active flag for the object and sub objects then calls their enter/leave method.

        Args:
            activate flag
        """

        if self.is_active == should_activate:
            return

        objs_list: list[UIElement] = [self]
        while objs_list != []:
            obj: UIElement = objs_list.pop()
            if obj.should_follow_parent or obj == self:
                obj.is_active = should_activate
                if should_activate:
                    obj.enter()
                else:
                    obj.leave()

                objs_list.extend(obj.sub_objs)

        global state_active_objs
        state_active_objs = tuple([
            obj
            for obj in states_objs[state_i] if obj.is_active
        ])


def resize_obj(
        init_pos: RectPos, init_w: float, init_h: float,
        should_keep_wh_ratio: bool = False
) -> tuple[XY, WH]:
    """
    Scales position and size of an object without creating gaps between attached objects.

    Args:
        initial position, initial width, initial height,
        keep size ratio flag (default = False)
    Returns:
        position, size
    """

    resized_wh: WH

    resized_xy: XY = (
        round(init_pos.x * my_vars.win_w_ratio),
        round(init_pos.y * my_vars.win_h_ratio),
    )

    if should_keep_wh_ratio:
        resized_wh = (ceil(init_w * my_vars.min_win_ratio), ceil(init_h * my_vars.min_win_ratio))
    else:
        resized_wh = (ceil(init_w * my_vars.win_w_ratio  ), ceil(init_h * my_vars.win_h_ratio))

    return resized_xy, resized_wh
