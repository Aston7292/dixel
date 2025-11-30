"""Functions/Classes shared between files to manage objects."""

from dataclasses import dataclass, field
from math import ceil
from typing import Self, Protocol

from pygame import Rect

import src.vars as my_vars
from src.type_utils import XY, WH, BlitInfo, RectPos

state_i: int = 0
states_info: tuple[tuple[ObjInfo, ...], ...] = ((),)
state_active_objs: tuple[UIElement, ...] = ()
animating_objs: set[AnimatableElement] = set()


class UIElement(Protocol):
    """Class to reinforce type hinting of UIElements."""

    hover_rects: tuple[Rect, ...]
    layer: int
    cursor_type: int
    blit_sequence: list[BlitInfo]

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self: Self) -> None:
        """Resizes the object."""

    @property
    def objs_info(self: Self) -> tuple[ObjInfo, ...]:
        """
        Gets the sub objects info.

        Returns:
            objects info
        """


class AnimatableElement(Protocol):
    """Class to reinforce type hinting of animatable elements."""

    def animate(self: Self, dt: float) -> None:
        """
        Plays a frame of the active animation.

        Args:
            delta time
        """


@dataclass(slots=True)
class ObjInfo:
    """
    Dataclass for storing an object and its active flag.

    Args:
        object, follow parent flag (changes activeness when parent does) (default = True)
    """

    obj: UIElement
    is_active: bool = field(default=True, init=False)
    should_follow_parent: bool = True

    def rec_set_active(self: Self, should_activate: bool) -> None:
        """
        Sets the active flag for the object and sub objects then calls their enter/leave method.

        Args:
            activate flag
        """

        if self.is_active == should_activate:
            return

        objs_info: list[ObjInfo] = [self]
        while objs_info != []:
            info: ObjInfo = objs_info.pop()
            if info.should_follow_parent or info == self:
                info.is_active = should_activate
                if should_activate:
                    info.obj.enter()
                else:
                    info.obj.leave()

                objs_info.extend(info.obj.objs_info)

        global state_active_objs
        state_active_objs = tuple([
            info.obj
            for info in states_info[state_i] if info.is_active
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


def rec_move_rect(
        main_obj: UIElement, init_x: int, init_y: int,
        should_scale: bool = True
) -> None:
    """
    Moves an object and its sub objects to a specific coordinate.

    Args:
        object, initial x, initial y, scale flag (default = True)
    """

    objs_list: list[UIElement] = [main_obj]
    change_x: int = 0
    change_y: int = 0
    while objs_list != []:
        obj: UIElement = objs_list.pop()
        class_name: str = obj.__class__.__name__
        assert hasattr(obj, "init_pos") and isinstance(obj.init_pos, RectPos), class_name
        assert hasattr(obj, "move_rect") and callable(obj.move_rect)         , class_name

        if obj == main_obj:
            change_x, change_y = init_x - obj.init_pos.x, init_y - obj.init_pos.y
            obj.move_rect(init_x, init_y, should_scale)
        else:
            obj.move_rect(obj.init_pos.x + change_x, obj.init_pos.y + change_y, should_scale)

        objs_list.extend([info.obj for info in obj.objs_info])
