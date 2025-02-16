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

from src.utils import RectPos, ObjInfo, Mouse, Keyboard, get_img
from src.type_utils import CheckboxInfo, ToolInfo, LayeredBlitInfo
from src.consts import SPECIAL_LAYER

ToolsInfo = dict[str, dict[str, Any]]
ToolExtraInfo = list[dict[str, Any]]
ToolsExtraInfo = list[tuple[dict[str, Any], ...]]

PENCIL_IMG: Final[Surface] = get_img("sprites", "pencil_tool.png")
BUCKET_IMG: Final[Surface] = PENCIL_IMG
CHECKBOX_IMGS: list[Surface] = [CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON]

TOOLS_INFO: Final[ToolsInfo] = {
    "brush": {
        "base_info": (PENCIL_IMG, "edit pixels"),
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [CHECKBOX_IMGS, "x mirror", None],
                "upt_args": ["mouse"],
                "out_format": {"mirror_x": "is_checked"}
            },
            {
                "type": Checkbox,
                "init_args": [CHECKBOX_IMGS, "y mirror", None],
                "upt_args": ["mouse"],
                "out_format": {"mirror_y": "is_checked"}
            }
        )
    },
    "fill": {
        "base_info": (BUCKET_IMG, "fill"),
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [CHECKBOX_IMGS, "fill all pixels\nthat have the\nsame color", None],
                "upt_args": ["mouse"],
                "out_format": {"same_color": "is_checked"}
            },
        )
    }
}


class ToolsManager:
    """Class to manage drawing tools."""

    __slots__ = (
        "tools_grid", "_tool_name", "_tools_extra_info", "blit_sequence", "objs_info",
        "_tools_objs_info_ranges"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of options and sub options.

        Args:
            position
        """

        tool_extra_info: ToolExtraInfo
        tool_range_start_i: int
        tool_range_end_i: int
        i: int

        checkboxes_info: list[CheckboxInfo] = [info["base_info"] for info in TOOLS_INFO.values()]
        self.tools_grid: CheckboxGrid = CheckboxGrid(pos, checkboxes_info, 5, False, True)

        tools_raw_extra_info: ToolsExtraInfo = [info["extra_info"] for info in TOOLS_INFO.values()]

        self._tool_name: str = tuple(TOOLS_INFO.keys())[self.tools_grid.clicked_i]
        # Added keys: obj, removed keys: type, init_args
        self._tools_extra_info: list[ToolExtraInfo] = [
            self._get_extra_info(raw_extra_info) for raw_extra_info in tools_raw_extra_info
        ]

        self.blit_sequence: list[LayeredBlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.tools_grid)]

        self._tools_objs_info_ranges: list[tuple[int, int]] = []
        for tool_extra_info in self._tools_extra_info:
            range_start: int = len(self.objs_info)
            self.objs_info.extend(
                [ObjInfo(sub_tool_extra_info["obj"]) for sub_tool_extra_info in tool_extra_info]
            )

            self._tools_objs_info_ranges.append((range_start, len(self.objs_info)))

        tool_i: int = self.tools_grid.clicked_i
        tool_range_start_i, tool_range_end_i = self._tools_objs_info_ranges[tool_i]
        for i in range(self._tools_objs_info_ranges[0][0], self._tools_objs_info_ranges[-1][-1]):
            if i < tool_range_start_i or i >= tool_range_end_i:
                self.objs_info[i].set_active(False)

    def _get_extra_info(self, raw_extra_info: tuple[dict[str, Any], ...]) -> ToolExtraInfo:
        """
        Creates the sub objects of a tool.

        Args:
            raw extra info
        Returns:
            extra info
        """

        obj_x: int
        obj_y: int
        raw_sub_tool_extra_info: dict[str, Any]

        extra_info: ToolExtraInfo = []

        obj_x, obj_y = self.tools_grid.rect.x + 20, self.tools_grid.rect.y - 20
        for raw_sub_tool_extra_info in raw_extra_info:
            obj_type: Any = raw_sub_tool_extra_info["type"]
            pos: RectPos = RectPos(obj_x, obj_y, "bottomleft")
            init_args: list[Any] = raw_sub_tool_extra_info["init_args"]
            obj: Any = obj_type(pos, *init_args, base_layer=SPECIAL_LAYER)

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

        prev_active_range_start_i: int
        prev_active_range_end_i: int
        active_range_start_i: int
        active_range_end_i: int
        obj_info: ObjInfo

        self._tool_name = tuple(TOOLS_INFO.keys())[self.tools_grid.clicked_i]
        objs_info_ranges: list[tuple[int, int]] = self._tools_objs_info_ranges
        prev_active_range_start_i, prev_active_range_end_i = objs_info_ranges[prev_tool_i]
        active_range_start_i, active_range_end_i = objs_info_ranges[self.tools_grid.clicked_i]

        for obj_info in self.objs_info[prev_active_range_start_i:prev_active_range_end_i]:
            obj_info.set_active(False)
        for obj_info in self.objs_info[active_range_start_i:active_range_end_i]:
            obj_info.set_active(True)

    def _upt_sub_objs(self, local_vars: dict[str, Any]) -> dict[str, Any]:
        """
        Updates the sub objects and returns the needed attribute as a dictionary.

        Args:
            local variables
        Returns:
            output dictionary
        """

        extra_info: dict[str, Any]
        key: str
        value: Any

        out_dict: dict[str, Any] = {}
        for extra_info in self._tools_extra_info[self.tools_grid.clicked_i]:
            upt_vars: list[Any] = [local_vars.get(arg, arg) for arg in extra_info["upt_args"]]
            extra_info["obj"].upt(*upt_vars)

            for key, value in extra_info["out_format"].items():
                out_dict[key] = getattr(extra_info["obj"], value)

        return out_dict

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> ToolInfo:
        """
        Allows selecting a tool and it's extra options.

        Args:
            mouse, keyboard
        Returns:
            tool name, sub options state
        """

        prev_tool_i: int = self.tools_grid.clicked_i
        tool_i: int = self.tools_grid.upt(mouse, keyboard)
        if tool_i != prev_tool_i:
            self.refresh_tools(prev_tool_i)

        out_dict: dict[str, Any] = self._upt_sub_objs(locals())

        return self._tool_name, out_dict
