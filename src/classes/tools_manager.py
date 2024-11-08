"""
Class to manage drawing tools.

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
"""

from typing import Final, Any

import pygame as pg

from src.classes.ui import CHECKBOX_1_IMG, CHECKBOX_2_IMG
from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Checkbox

from src.utils import RectPos, ObjInfo, MouseInfo, get_img
from src.type_utils import ToolInfo
from src.consts import SPECIAL_LAYER

PENCIL_IMG: Final[pg.Surface] = get_img("sprites", "pencil_tool.png")
BUCKET_IMG: Final[pg.Surface] = PENCIL_IMG

ToolsInfo = dict[str, dict[str, Any]]
ExtraInfos = tuple[tuple[dict[str, Any], ...], ...]
ExtraInfosList = list[list[dict[str, Any]]]

TOOLS_INFO: Final[ToolsInfo] = {
    "brush": {
        "base_info": (PENCIL_IMG, "edit pixels"),
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [(CHECKBOX_1_IMG, CHECKBOX_2_IMG), "x mirror", ''],
                "upt_args": ["hovered_obj", "mouse_info"],
                "output_format": {"mirror_x": "is_checked"}
            },
            {
                "type": Checkbox,
                "init_args": [(CHECKBOX_1_IMG, CHECKBOX_2_IMG), "y mirror", ''],
                "upt_args": ["hovered_obj", "mouse_info"],
                "output_format": {"mirror_y": "is_checked"}
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


class ToolsManager:
    """Class to manage drawing tools."""

    __slots__ = (
        '_names', '_tools', '_extra_infos', 'objs_info', '_dynamic_info_ranges'
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of options and sub options.

        Args:
            position
        """

        self._names: tuple[str, ...] = tuple(TOOLS_INFO.keys())
        base_infos: tuple[tuple[pg.Surface, str], ...] = tuple(
            info["base_info"] for info in TOOLS_INFO.values()
        )
        self._tools: CheckboxGrid = CheckboxGrid(pos, base_infos, 5, (False, True))

        self._extra_infos: ExtraInfosList = []  # Added keys: obj, removed keys: type, init_args
        extra_infos: ExtraInfos = tuple(info["extra_info"] for info in TOOLS_INFO.values())
        for extra_info in extra_infos:
            tool_info: list[dict[str, Any]] = self._get_tool_infos(extra_info)
            self._extra_infos.append(tool_info)

        self.objs_info: list[ObjInfo] = [ObjInfo(self._tools)]

        self._dynamic_info_ranges: list[tuple[int, int]] = []
        for obj_info in self._extra_infos:
            range_start: int = len(self.objs_info)
            self.objs_info.extend(ObjInfo(info["obj"]) for info in obj_info)
            range_end: int = len(self.objs_info)

            self._dynamic_info_ranges.append((range_start, range_end))

        active_range: tuple[int, int] = self._dynamic_info_ranges[self._tools.clicked_i]
        for i in range(self._dynamic_info_ranges[0][0], self._dynamic_info_ranges[-1][1]):
            if i < active_range[0] or i >= active_range[1]:
                self.objs_info[i].set_active(False)

    def _get_tool_infos(self, extra_info: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
        """
        Creates the sub objects of a tool.

        Args:
            extra info
        Returns:
            tool info
        """

        tool_info: list[dict[str, Any]] = []

        obj_x: int = self._tools.rect.x + 20
        obj_y: int = self._tools.rect.y - 20
        for info in extra_info:
            obj: Any = info["type"](
                RectPos(obj_x, obj_y, 'bottomleft'), *info["init_args"],
                base_layer=SPECIAL_LAYER
            )

            info["obj"] = obj
            del info["type"], info["init_args"]

            obj_x += obj.rect.w + 20
            tool_info.append(info)

        return tool_info

    def _leave_tool(self, tool_i: int) -> None:
        """
        Clears all the relevant data of the previous tool.

        Args:
            index of the tool
        """

        active_range: tuple[int, int] = self._dynamic_info_ranges[tool_i]
        objs_info: list[ObjInfo] = self.objs_info[active_range[0]:active_range[1]]
        for prev_info in objs_info:
            prev_info.set_active(False)

        tool_objs: list[Any] = [prev_info.obj for prev_info in objs_info]
        while tool_objs:
            obj: Any = tool_objs.pop()

            if hasattr(obj, "leave"):
                obj.leave()
            if hasattr(obj, "objs_info"):
                tool_objs.extend(info.obj for info in obj.objs_info)

    def _upt_sub_objs(self, local_vars: dict[str, Any]) -> dict[str, Any]:
        """
        Updates the sub objects and returns the needed attribute as a dictionary.

        Args:
            local variables
        Returns:
            output dictionary
        """

        output_dict: dict[str, Any] = {}
        for info in self._extra_infos[self._tools.clicked_i]:
            upt_args: tuple[Any, ...] = tuple(
                local_vars.get(str(arg), arg) for arg in info["upt_args"]
            )
            info["obj"].upt(*upt_args)

            obj_output_dict: dict[str, Any] = info["output_format"].copy()
            for key in obj_output_dict:
                obj_output_dict[key] = getattr(info["obj"], obj_output_dict[key])
            output_dict.update(obj_output_dict)

        return output_dict

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]) -> ToolInfo:
        """
        Allows selecting a tool and it's extra options.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            tool name, sub options state
        """

        prev_clicked_i: int = self._tools.clicked_i
        self._tools.upt(hovered_obj, mouse_info, keys)

        if self._tools.clicked_i != prev_clicked_i:
            self._leave_tool(prev_clicked_i)
            active_range: tuple[int, int] = self._dynamic_info_ranges[self._tools.clicked_i]
            for i in range(active_range[0], active_range[1]):
                self.objs_info[i].set_active(True)
        output_dict: dict[str, Any] = self._upt_sub_objs(locals())

        return self._names[self._tools.clicked_i], output_dict
