"""Functions/Classes shared between files to manage objects."""

from dataclasses import dataclass
from collections.abc import Callable
from math import ceil
from typing import Self, Protocol

from pygame import Rect

from src.type_utils import XY, WH, BlitInfo, RectPos

states_info: tuple[tuple[ObjInfo, ...], ...] = ((),)
state_active_objs: tuple[UIElement, ...] = ()
state_i: int = 0


class UIElement(Protocol):
    """Class to reinforce type hinting."""

    hover_rects: tuple[Rect, ...]
    layer: int
    cursor_type: int
    blit_sequence: list[BlitInfo]

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

    @property
    def objs_info(self: Self) -> tuple[ObjInfo, ...]:
        """
        Gets the sub objects info.

        Returns:
            objects info
        """


@dataclass(slots=True)
class ObjInfo:
    """
    Dataclass for storing an object and its active flag.

    Args:
        object
    """

    obj: UIElement
    is_active: bool = True

    def rec_set_active(self: Self, should_activate: bool) -> None:
        """
        Sets the active flag for the object and sub objects then calls their enter/leave method.

        Args:
            activate flag
        """

        if self.is_active != should_activate:
            objs_info: list[ObjInfo] = [self]
            while objs_info != []:
                info: ObjInfo = objs_info.pop()
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
        win_w_ratio: float, win_h_ratio: float, should_keep_wh_ratio: bool = False
) -> tuple[XY, WH]:
    """
    Scales position and size of an object without creating gaps between attached objects.

    Args:
        initial position, initial width, initial height,
        window width ratio, window height ratio keep size ratio flag (default = False)
    Returns:
        position, size
    """

    resized_wh: WH

    resized_xy: XY = (round(init_pos.x * win_w_ratio), round(init_pos.y * win_h_ratio))
    if should_keep_wh_ratio:
        min_ratio: float = min(win_w_ratio, win_h_ratio)
        resized_wh = (ceil(init_w * min_ratio  ), ceil(init_h * min_ratio))
    else:
        resized_wh = (ceil(init_w * win_w_ratio), ceil(init_h * win_h_ratio))

    return resized_xy, resized_wh


def rec_move_rect(
        main_obj: UIElement, init_x: int, init_y: int,
        win_w_ratio: float, win_h_ratio: float
) -> None:
    """
    Moves an object and it's sub objects to a specific coordinate.

    Args:
        object, initial x, initial y, window width ratio, window height ratio
    """

    objs_list: list[UIElement] = [main_obj]
    change_x: int = 0
    change_y: int = 0
    while objs_list != []:
        obj: UIElement = objs_list.pop()
        assert hasattr(obj, "init_pos") , obj.__class__.__name__
        assert hasattr(obj, "move_rect"), obj.__class__.__name__

        move_rect: Callable[[int, int, float, float], None] = obj.move_rect
        init_pos: RectPos = obj.init_pos
        if obj == main_obj:
            change_x, change_y = init_x - init_pos.x, init_y - init_pos.y
            move_rect(init_x, init_y, win_w_ratio, win_h_ratio)
        else:
            move_rect(init_pos.x + change_x, init_pos.y + change_y, win_w_ratio, win_h_ratio)

        objs_list.extend([info.obj for info in obj.objs_info])
