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
from src.classes.devices import KEYBOARD

from src.utils import RectPos, ObjInfo
from src.type_utils import BlitInfo
from src.consts import BG_LAYER, SPECIAL_LAYER
from src.imgs import CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG, PENCIL_IMG, BUCKET_IMG, EYE_DROPPER_IMG


ToolInfo: TypeAlias = tuple[str, dict[str, Any]]
_ToolsInfo: TypeAlias = dict[str, dict[str, Any]]
_ToolExtraInfo: TypeAlias = list[dict[str, Any]]
_ToolsExtraInfo: TypeAlias = list[tuple[dict[str, Any], ...]]

_CHECKBOX_IMGS: Final[list[pg.Surface]] = [CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG]
_TOOLS_INFO: Final[_ToolsInfo] = {
    "pencil": {
        "base_info": (PENCIL_IMG, "Pencil\n(SHIFT+P)"),
        "shortcut_k": K_p,
        "extra_info": (),
    },

    "bucket": {
        "base_info": (BUCKET_IMG, "Bucket\n(SHIFT+B)"),
        "shortcut_k": K_b,
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": [_CHECKBOX_IMGS, "Color Fill", "Fill pixels with\nthe same color"],
                "upt_args": [],
                "out_format": {"color_fill": "is_checked"},
            },
        ),
    },

    "eye_dropper": {
        "base_info": (EYE_DROPPER_IMG, "Eye Dropper\n(SHIFT+E)"),
        "shortcut_k": K_e,
        "extra_info": (),
    },
}

_EYE_DROPPER_I: Final[int] = 2

class ToolsManager:
    """Class to manage drawing tools."""

    __slots__ = (
        "tools_grid", "_tool_name", "_tools_extra_info",
        "saved_clicked_i",
        "hover_rects", "layer", "blit_sequence", "objs_info",
        "_sub_tools_ranges",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of tools and sub options.

        Args:
            position
        """

        tool_extra_info: _ToolExtraInfo
        i: int

        self.tools_grid: CheckboxGrid = CheckboxGrid(
            pos,
            [info["base_info"] for info in _TOOLS_INFO.values()], 5, False, True
        )
        self._tool_name: str = tuple(_TOOLS_INFO.keys())[0]

        tools_raw_extra_info: _ToolsExtraInfo = [
            info["extra_info"] for info in _TOOLS_INFO.values()
        ]
        # Added keys: obj | removed keys: type, init_args
        self._tools_extra_info: list[_ToolExtraInfo] = [
            self._get_extra_info(raw_extra_info) for raw_extra_info in tools_raw_extra_info
        ]

        self.saved_clicked_i: int | None = None

        self.hover_rects: list[pg.Rect] = []
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.tools_grid)]

        self._sub_tools_ranges: list[tuple[int, int]] = []
        for tool_extra_info in self._tools_extra_info:
            range_start: int = len(self.objs_info)
            self.objs_info.extend(
                [ObjInfo(sub_tool_extra_info["obj"]) for sub_tool_extra_info in tool_extra_info]
            )
            range_end: int   = len(self.objs_info)

            self._sub_tools_ranges.append((range_start, range_end))

        sub_tools_range_start_i: int = self._sub_tools_ranges[self.tools_grid.clicked_i][0]
        sub_tools_range_end_i: int   = self._sub_tools_ranges[self.tools_grid.clicked_i][1]

        for i in range(self._sub_tools_ranges[0][0], self._sub_tools_ranges[-1][1]):
            if i < sub_tools_range_start_i or i >= sub_tools_range_end_i:
                self.objs_info[i].rec_set_active(False)

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        if self.saved_clicked_i is not None:
            self.tools_grid.clicked_i = self.saved_clicked_i
            self.saved_clicked_i = None
            self.refresh_tools(self.tools_grid.prev_clicked_i)
            self.tools_grid.refresh()

    def resize(self, _win_w_ratio: float, _win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

    def _get_extra_info(self, raw_extra_info: tuple[dict[str, Any], ...]) -> _ToolExtraInfo:
        """
        Creates the sub options of a tool.

        Args:
            raw extra info
        Returns:
            extra info
        """

        raw_sub_tool_extra_info: dict[str, Any]

        obj_x: int = self.tools_grid.rect.x + 20
        extra_info: _ToolExtraInfo = []
        for raw_sub_tool_extra_info in raw_extra_info:
            obj: Any = raw_sub_tool_extra_info["type"](
                RectPos(obj_x, self.tools_grid.rect.y - 20, "bottomleft"),
                *raw_sub_tool_extra_info["init_args"], base_layer=SPECIAL_LAYER
            )
            obj_x += obj.rect.w + 20

            assert hasattr(obj, "rect") and isinstance(obj.rect, pg.Rect), obj.__class__.__name__
            assert hasattr(obj, "upt" ) and callable(  obj.upt          ), obj.__class__.__name__

            raw_sub_tool_extra_info["obj"] = obj
            del raw_sub_tool_extra_info["type"], raw_sub_tool_extra_info["init_args"]
            extra_info.append(raw_sub_tool_extra_info)

        return extra_info

    def refresh_tools(self, prev_tool_i: int) -> None:
        """
        Sets the previous tool inactive and activates the new one.

        Args:
            index of the previous tool
        """

        obj_info: ObjInfo

        tool_i: int = self.tools_grid.clicked_i
        self._tool_name = tuple(_TOOLS_INFO.keys())[tool_i]

        prev_sub_tools_range_start_i: int = self._sub_tools_ranges[prev_tool_i]              [0]
        prev_sub_tools_range_end_i: int   = self._sub_tools_ranges[prev_tool_i]              [1]
        sub_tools_range_start_i: int      = self._sub_tools_ranges[self.tools_grid.clicked_i][0]
        sub_tools_range_end_i: int        = self._sub_tools_ranges[self.tools_grid.clicked_i][1]

        for obj_info in self.objs_info[prev_sub_tools_range_start_i:prev_sub_tools_range_end_i]:
            obj_info.rec_set_active(False)
        for obj_info in self.objs_info[     sub_tools_range_start_i:     sub_tools_range_end_i]:
            obj_info.rec_set_active(True )

    def _handle_shortcuts(self) -> None:
        """Handles changing the selection with the keyboard."""

        i: int
        info: dict[str, Any]

        for i, info in enumerate(_TOOLS_INFO.values()):
            if info["shortcut_k"] in KEYBOARD.pressed:
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
        value: str

        out_dict: dict[str, Any] = {}
        for extra_info in self._tools_extra_info[self.tools_grid.clicked_i]:
            upt_vars: list[Any] = [local_vars.get(arg, arg) for arg in extra_info["upt_args"]]
            extra_info["obj"].upt(*upt_vars)

            for key, value in extra_info["out_format"].items():
                out_dict[key] = getattr(extra_info["obj"], value)

        return out_dict

    def upt(self) -> ToolInfo:
        """
        Allows selecting a tool and its extra options.

        Returns:
            tool name, sub objects states
        """

        if KEYBOARD.is_shift_on:
            self._handle_shortcuts()
        self.tools_grid.upt()

        if KEYBOARD.is_alt_on:
            if self.tools_grid.clicked_i != _EYE_DROPPER_I:
                self.saved_clicked_i = self.tools_grid.clicked_i
                self.tools_grid.clicked_i = _EYE_DROPPER_I
        elif self.saved_clicked_i is not None:
                self.tools_grid.clicked_i = self.saved_clicked_i
                self.saved_clicked_i = None

        if self.tools_grid.clicked_i != self.tools_grid.prev_clicked_i:
            self.refresh_tools(self.tools_grid.prev_clicked_i)
        self.tools_grid.refresh()

        out_dict: dict[str, Any] = self._upt_sub_objs(locals())
        return self._tool_name, out_dict
