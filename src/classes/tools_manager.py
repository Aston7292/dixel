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

from pygame import Surface

from src.classes.ui import CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON
from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Checkbox

from src.utils import RectPos, ObjInfo, MouseInfo, get_img
from src.type_utils import ToolInfo
from src.consts import SPECIAL_LAYER

ToolsInfo = dict[str, dict[str, Any]]
ToolsExtraInfo = tuple[tuple[dict[str, Any], ...], ...]
ToolsExtraInfoList = list[list[dict[str, Any]]]

PENCIL_IMG: Final[Surface] = get_img("sprites", "pencil_tool.png")
BUCKET_IMG: Final[Surface] = PENCIL_IMG

TOOLS_INFO: Final[ToolsInfo] = {
    "brush": {
        "base_info": (PENCIL_IMG, "edit pixels"),
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [(CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON), "x mirror", None],
                "upt_args": ["hovered_obj", "mouse_info"],
                "out_format": {"mirror_x": "is_checked"}
            },
            {
                "type": Checkbox,
                "init_args": [(CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON), "y mirror", None],
                "upt_args": ["hovered_obj", "mouse_info"],
                "out_format": {"mirror_y": "is_checked"}
            }
        )
    },
    "fill": {
        "base_info": (BUCKET_IMG, "fill"),
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [
                    (CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON), "fill pixels of\nthe same color", None
                ],
                "upt_args": ["hovered_obj", "mouse_info"],
                "out_format": {"same_color": "is_checked"}
            },
        )
    }
}


class ToolsManager:
    """Class to manage drawing tools."""

    __slots__ = (
        "_names", "tools_grid", "_tools_extra_info", "objs_info", "_dynamic_info_ranges"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of options and sub options.

        Args:
            position
        """

        self._names: tuple[str, ...] = tuple(TOOLS_INFO.keys())
        base_tools_info: tuple[tuple[Surface, str], ...] = tuple(
            info["base_info"] for info in TOOLS_INFO.values()
        )
        self.tools_grid: CheckboxGrid = CheckboxGrid(pos, base_tools_info, 5, (False, True))

        tools_raw_extra_info: ToolsExtraInfo = tuple(
            info["extra_info"] for info in TOOLS_INFO.values()
        )
        # Added keys: obj, removed keys: type, init_args
        self._tools_extra_info = [
            self._get_extra_info(tool_raw_extra_info)
            for tool_raw_extra_info in tools_raw_extra_info
        ]

        self.objs_info: list[ObjInfo] = [ObjInfo(self.tools_grid)]

        self._dynamic_info_ranges: list[tuple[int, int]] = []
        for tool_extra_info in self._tools_extra_info:
            range_start: int = len(self.objs_info)
            self.objs_info.extend(
                ObjInfo(sub_tool_extra_info["obj"]) for sub_tool_extra_info in tool_extra_info
            )
            range_end: int = len(self.objs_info)

            self._dynamic_info_ranges.append((range_start, range_end))

        active_range: tuple[int, int] = self._dynamic_info_ranges[self.tools_grid.clicked_i]
        for i in range(self._dynamic_info_ranges[0][0], self._dynamic_info_ranges[-1][1]):
            if i < active_range[0] or i >= active_range[1]:
                self.objs_info[i].set_active(False)

    def _get_extra_info(self, raw_extra_info: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
        """
        Creates the sub objects of a tool.

        Args:
            raw extra info
        Returns:
            extra info
        """

        extra_info: list[dict[str, Any]] = []

        obj_x: int = self.tools_grid.rect.x + 20
        obj_y: int = self.tools_grid.rect.y - 20
        for raw_sub_tool_extra_info in raw_extra_info:
            obj: Any = raw_sub_tool_extra_info["type"](
                RectPos(obj_x, obj_y, "bottomleft"), *raw_sub_tool_extra_info["init_args"],
                base_layer=SPECIAL_LAYER
            )

            raw_sub_tool_extra_info["obj"] = obj
            del raw_sub_tool_extra_info["type"], raw_sub_tool_extra_info["init_args"]

            obj_x += obj.rect.w + 20
            extra_info.append(raw_sub_tool_extra_info)

        return extra_info

    def refresh_tools(self, prev_tool_i: int) -> None:
        """
        Clears all the relevant data of the previous tool and activated a new one.

        Args:
            index of the previous tool
        """

        prev_active_range: tuple[int, int] = self._dynamic_info_ranges[prev_tool_i]
        prev_objs_info: list[ObjInfo] = self.objs_info[prev_active_range[0]:prev_active_range[1]]
        for prev_info in prev_objs_info:
            prev_info.set_active(False)

        prev_tool_objs: list[Any] = [prev_info.obj for prev_info in prev_objs_info]
        while prev_tool_objs:
            obj: Any = prev_tool_objs.pop()

            if hasattr(obj, "leave"):
                obj.leave()
            if hasattr(obj, "objs_info"):
                prev_tool_objs.extend(obj_info.obj for obj_info in obj.objs_info)

        active_range: tuple[int, int] = self._dynamic_info_ranges[self.tools_grid.clicked_i]
        for i in range(active_range[0], active_range[1]):
            self.objs_info[i].set_active(True)

    def _upt_sub_objs(self, local_vars: dict[str, Any]) -> dict[str, Any]:
        """
        Updates the sub objects and returns the needed attribute as a dictionary.

        Args:
            local variables
        Returns:
            output dictionary
        """

        out_dict: dict[str, Any] = {}
        for extra_info in self._tools_extra_info[self.tools_grid.clicked_i]:
            upt_args: tuple[Any, ...] = tuple(
                local_vars.get(str(arg), arg) for arg in extra_info["upt_args"]
            )
            extra_info["obj"].upt(*upt_args)

            obj_out_dict: dict[str, Any] = {}
            for key, value in extra_info["out_format"].items():
                obj_out_dict[key] = getattr(extra_info["obj"], value)
            out_dict.update(obj_out_dict)

        return out_dict

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]) -> ToolInfo:
        """
        Allows selecting a tool and it's extra options.

        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            tool name, sub options state
        """

        prev_clicked_i: int = self.tools_grid.clicked_i
        self.tools_grid.upt(hovered_obj, mouse_info, keys)

        if self.tools_grid.clicked_i != prev_clicked_i:
            self.refresh_tools(prev_clicked_i)
        out_dict: dict[str, Any] = self._upt_sub_objs(locals())

        return self._names[self.tools_grid.clicked_i], out_dict
