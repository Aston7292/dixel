"""
Class to manage the drawing tools.

Tools must have:
- name
- base info (image and text)
- shortcut key
- info for extra UI elements with:
    - type
    - arguments to create it (excluding position)
    - arguments to pass in the upt method
    - dict format to send it to the grid

Extra UI elements need:
    - a position argument as first in the constructor
    - a base_layer argument in the constructor
    - an upt method
    - a rect attribute
"""

from typing import TypeAlias, Final, Any

import pygame as pg
from pygame.locals import *

from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Checkbox
from src.classes.devices import Mouse, Keyboard

from src.utils import RectPos, ObjInfo
from src.type_utils import CheckboxInfo, ToolInfo, BlitInfo
from src.consts import SPECIAL_LAYER
from src.imgs import CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG, BRUSH_IMG, BUCKET_IMG, EYE_DROPPER_IMG

_ToolsInfo: TypeAlias = dict[str, dict[str, Any]]
_ToolExtraInfo: TypeAlias = list[dict[str, Any]]
_ToolsExtraInfo: TypeAlias = list[tuple[dict[str, Any], ...]]

_CHECKBOX_IMGS: Final[list[pg.Surface]] = [CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG]
_TOOLS_INFO: Final[_ToolsInfo] = {
    "brush": {
        "base_info": (BRUSH_IMG, "Pencil\n(SHIFT+P)"),
        "shortcut_k": K_p,
        "extra_info": ()
    },
    "bucket": {
        "base_info": (BUCKET_IMG, "Bucket\n(SHIFT+B)"),
        "shortcut_k": K_b,
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [_CHECKBOX_IMGS, "Color Fill", "Fill pixels with\nthe same color"],
                "upt_args": ["mouse"],
                "out_format": {"color_fill": "is_checked"}
            },
        )
    },
    "eye_dropper": {
        "base_info": (EYE_DROPPER_IMG, "Eye Dropper\n(SHIFT+E)"),
        "shortcut_k": K_e,
        "extra_info": ()
    }
}

_EYE_DROPPER_I: Final[int] = 2

class ToolsManager:
    """Class to manage drawing tools."""

    __slots__ = (
        "tools_grid", "_tool_name", "_tools_extra_info", "_saved_clicked_i", "blit_sequence",
        "objs_info", "_tools_objs_info_ranges"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of tools and sub options.

        Args:
            position
        """

        tool_extra_info: _ToolExtraInfo
        tool_range_start_i: int
        tool_range_end_i: int
        i: int

        tools_grid_info: list[CheckboxInfo] = [info["base_info"] for info in _TOOLS_INFO.values()]
        self.tools_grid: CheckboxGrid = CheckboxGrid(pos, tools_grid_info, 5, False, True)
        self._tool_name: str = tuple(_TOOLS_INFO.keys())[0]

        tools_raw_extra_info: _ToolsExtraInfo = [
            info["extra_info"] for info in _TOOLS_INFO.values()
        ]
        # Added keys: obj | removed keys: type, init_args
        self._tools_extra_info: list[_ToolExtraInfo] = [
            self._get_extra_info(raw_extra_info) for raw_extra_info in tools_raw_extra_info
        ]

        self._saved_clicked_i: int | None = None

        self.blit_sequence: list[BlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.tools_grid)]
        objs_info: list[ObjInfo] = self.objs_info

        self._tools_objs_info_ranges: list[tuple[int, int]] = []
        for tool_extra_info in self._tools_extra_info:
            range_start: int = len(objs_info)
            objs_info.extend(
                [ObjInfo(sub_tool_extra_info["obj"]) for sub_tool_extra_info in tool_extra_info]
            )

            self._tools_objs_info_ranges.append((range_start, len(objs_info)))

        tool_i: int = self.tools_grid.clicked_i
        tool_range_start_i, tool_range_end_i = self._tools_objs_info_ranges[tool_i]
        for i in range(self._tools_objs_info_ranges[0][0], self._tools_objs_info_ranges[-1][1]):
            if i < tool_range_start_i or i >= tool_range_end_i:
                objs_info[i].rec_set_active(False)

    def _get_extra_info(self, raw_extra_info: tuple[dict[str, Any], ...]) -> _ToolExtraInfo:
        """
        Creates the sub options of a tool.

        Args:
            raw extra info
        Returns:
            extra info
        """

        obj_x: int
        obj_y: int
        raw_sub_tool_extra_info: dict[str, Any]

        obj_x, obj_y = self.tools_grid.rect.x + 10, self.tools_grid.rect.y - 20
        extra_info: _ToolExtraInfo = []
        for raw_sub_tool_extra_info in raw_extra_info:
            obj_class: Any = raw_sub_tool_extra_info["type"]
            pos: RectPos = RectPos(obj_x, obj_y, "bottomleft")
            init_args: list[Any] = raw_sub_tool_extra_info["init_args"]
            obj: Any = obj_class(pos, *init_args, base_layer=SPECIAL_LAYER)

            raw_sub_tool_extra_info["obj"] = obj
            del raw_sub_tool_extra_info["type"], raw_sub_tool_extra_info["init_args"]

            obj_x += obj.rect.w + 20
            extra_info.append(raw_sub_tool_extra_info)

        return extra_info

    def refresh_tools(self, prev_tool_i: int) -> None:
        """
        Sets the previous tool inactive and activates the new one.

        Args:
            index of the previous tool
        """

        prev_active_range_start_i: int
        prev_active_range_end_i: int
        active_range_start_i: int
        active_range_end_i: int
        obj_info: ObjInfo

        self._tool_name = tuple(_TOOLS_INFO.keys())[self.tools_grid.clicked_i]
        objs_info_ranges: list[tuple[int, int]] = self._tools_objs_info_ranges
        prev_active_range_start_i, prev_active_range_end_i = objs_info_ranges[prev_tool_i]
        active_range_start_i, active_range_end_i = objs_info_ranges[self.tools_grid.clicked_i]

        for obj_info in self.objs_info[prev_active_range_start_i:prev_active_range_end_i]:
            obj_info.rec_set_active(False)
        for obj_info in self.objs_info[active_range_start_i:active_range_end_i]:
            obj_info.rec_set_active(True)

    def _handle_shortcuts(self, keyboard: Keyboard) -> None:
        """
        Handles changing the selection with the keyboard.

        Args:
            keyboard
        """

        i: int
        info: dict[str, Any]

        for i, info in enumerate(_TOOLS_INFO.values()):
            if info["shortcut_k"] in keyboard.pressed:
                self.tools_grid.clicked_i = i

    def _upt_sub_objs(self, local_vars: dict[str, Any]) -> dict[str, Any]:
        """
        Updates the sub options and returns the needed attribute as a dictionary.

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
        Allows selecting a tool and its extra options.

        Args:
            mouse, keyboard
        Returns:
            tool name, sub objects states
        """

        if keyboard.is_shift_on:
            self._handle_shortcuts(keyboard)
        self.tools_grid.upt(mouse, keyboard)

        if keyboard.is_alt_on:
            if self.tools_grid.clicked_i != _EYE_DROPPER_I:
                self._saved_clicked_i = self.tools_grid.clicked_i
                self.tools_grid.clicked_i = _EYE_DROPPER_I
        elif self._saved_clicked_i is not None:
            self.tools_grid.clicked_i = self._saved_clicked_i
            self._saved_clicked_i = None

        if self.tools_grid.clicked_i != self.tools_grid.prev_clicked_i:
            self.refresh_tools(self.tools_grid.prev_clicked_i)
        self.tools_grid.refresh()

        out_dict: dict[str, Any] = self._upt_sub_objs(locals())

        return self._tool_name, out_dict
