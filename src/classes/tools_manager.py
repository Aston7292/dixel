"""
Class to manage drawing tools
"""

import pygame as pg
from typing import Final, Any

from src.classes.ui import CHECKBOX_1_IMG, CHECKBOX_2_IMG
from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Checkbox

from src.utils import RectPos, ObjInfo, MouseInfo, load_img
from src.type_utils import LayerSequence
from src.consts import SPECIAL_LAYER

PENCIL_IMG: Final[pg.Surface] = load_img("sprites", "pencil_tool.png")
BUCKET_IMG: Final[pg.Surface] = PENCIL_IMG

'''
All tools have:
- name
- base info (image and text)
- info for extra UI elements with:
    - type
    - arguments to create it (excluding position)
    - arguments to pass in the upt method
    - format to send it to the grid

Extra UI elements need:
    - a position argument as first in the constructor
    - a base_layer argument in the constructor
    - an upt method
    - a rect attribute
'''

TOOLS_INFO: Final[dict[str, dict[str, Any]]] = {
    "brush": {
        "base_info": (PENCIL_IMG, "edit pixels"),
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [(CHECKBOX_1_IMG, CHECKBOX_2_IMG), "x mirror", ''],
                "upt_args": ["hovered_obj", "mouse_info"],
                "output_format": {"x_mirror": "is_checked"}
            },
            {
                "type": Checkbox,
                "init_args": [(CHECKBOX_1_IMG, CHECKBOX_2_IMG), "y mirror", ''],
                "upt_args": ["hovered_obj", "mouse_info"],
                "output_format": {"y_mirror": "is_checked"}
            }
        )
    },
    "fill": {
        "base_info": (BUCKET_IMG, "fill"),
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [
                    (CHECKBOX_1_IMG, CHECKBOX_2_IMG), "edit pixels of\nthe same color", ''
                ],
                "upt_args": ["hovered_obj", "mouse_info"],
                "output_format": {"same_color": "is_checked"}
            },
        )
    }
}


def check_extra_info() -> None:  # Could go unnoticed
    """
    Makes sure extra UI elements have every required attributes and methods
    Raises:
        ValueError if a missing required attribute/method is found
    """

    extra_info: tuple[tuple[dict[str, Any], ...], ...] = tuple(
        info["extra_info"] for info in TOOLS_INFO.values()
    )

    missing_attrs: set[tuple[str, str]] = set()
    for tool_info in extra_info:
        for info in tool_info:
            obj: Any = info["type"](RectPos(0, 0, 'topleft'), *info["init_args"])

            required_attrs: list[str] = ["rect", "upt"] + list(info["output_format"].values())
            for attr in required_attrs:
                if not hasattr(obj, attr):
                    missing_attrs.add((obj.__class__.__name__, attr))

    if missing_attrs:
        for name, attr in missing_attrs:
            print(f"Class {name} is missing required attribute/method {attr}.")
        print()

        raise ValueError("Missing required attribute/method.")


class ToolsManager:
    """
    Class to manage drawing tools
    """

    __slots__ = (
        '_names', '_tools', '_extra_info', 'objs_info', '_dynamic_info_ranges'
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of options and sub options
        Args:
            position
        Raises:
            ValueError if an extra UI element is missing a required attribute
        """

        check_extra_info()

        self._names: tuple[str, ...] = tuple(TOOLS_INFO.keys())
        base_info: tuple[tuple[pg.Surface, str], ...] = tuple(
            info["base_info"] for info in TOOLS_INFO.values()
        )
        self._tools: CheckboxGrid = CheckboxGrid(pos, base_info, 5, (False, True))

        # Adds object and removes type and init arguments
        extra_info: tuple[tuple[dict[str, Any], ...], ...] = tuple(
            info["extra_info"] for info in TOOLS_INFO.values()
        )
        self._extra_info: list[list[dict[str, Any]]] = []
        for tool_info in extra_info:
            obj_x: int = self._tools.rect.x + 20
            obj_y: int = self._tools.rect.y - 20

            objs_info: list[dict[str, Any]] = []
            for info in tool_info:
                obj: Any = info["type"](
                    RectPos(obj_x, obj_y, 'bottomleft'), *info["init_args"],
                    base_layer=SPECIAL_LAYER
                )
                info["obj"] = obj
                del info["type"], info["init_args"]

                obj_x += obj.rect.w + 20

                objs_info.append(info)
            self._extra_info.append(objs_info)

        self.objs_info: list[ObjInfo] = [ObjInfo("tools", self._tools)]

        self._dynamic_info_ranges: list[tuple[int, int]] = []
        for i, obj_info in enumerate(self._extra_info):
            range_start: int = len(self.objs_info)
            self.objs_info.extend(
                ObjInfo(f"{self._names[i]} tool {j}", info["obj"])
                for j, info in enumerate(obj_info)
            )
            range_end: int = len(self.objs_info)

            self._dynamic_info_ranges.append((range_start, range_end))

        active_range: tuple[int, int] = self._dynamic_info_ranges[self._tools.clicked_i]
        for i in range(self._dynamic_info_ranges[0][0], self._dynamic_info_ranges[-1][1]):
            if i < active_range[0] or i >= active_range[1]:
                self.objs_info[i].set_active(False)

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...]
    ) -> tuple[str, dict[str, Any]]:
        """
        Allows selecting a tool and it's extra options
        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            tool name, sub options state
        """

        prev_clicked_i: int = self._tools.clicked_i
        self._tools.upt(hovered_obj, mouse_info, keys)

        if self._tools.clicked_i != prev_clicked_i:
            prev_active_range: tuple[int, int] = self._dynamic_info_ranges[prev_clicked_i]
            prev_objs_info: list[ObjInfo] = self.objs_info[
                prev_active_range[0]:prev_active_range[1]
            ]
            for prev_info in prev_objs_info:
                prev_info.set_active(False)

            prev_objs: list[Any] = [prev_info.obj for prev_info in prev_objs_info]
            while prev_objs:
                obj: Any = prev_objs.pop()

                if hasattr(obj, "leave"):
                    obj.leave()
                if hasattr(obj, "objs_info"):
                    prev_objs.extend(obj.objs_info)

            active_range: tuple[int, int] = self._dynamic_info_ranges[self._tools.clicked_i]
            for i in range(active_range[0], active_range[1]):
                self.objs_info[i].set_active(True)

        local_vars: dict[str, Any] = locals()
        output_dict: dict[str, Any] = {}
        for info in self._extra_info[self._tools.clicked_i]:
            upt_args: tuple[Any, ...] = tuple(
                local_vars.get(str(arg), arg) for arg in info["upt_args"]
            )
            info["obj"].upt(*upt_args)

            obj_output_dict: dict[str, Any] = info["output_format"].copy()
            for key in obj_output_dict:
                obj_output_dict[key] = getattr(info["obj"], obj_output_dict[key])
            output_dict.update(obj_output_dict)

        return self._names[self._tools.clicked_i], output_dict
