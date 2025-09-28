"""
Class to manage the drawing tools.

Tools must have:
- name
- info (image and text)
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

from typing import Self, Literal, TypeAlias, Final, Any

import pygame as pg
from pygame.locals import *

from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Checkbox
from src.classes.devices import KEYBOARD

from src.obj_utils import UIElement, ObjInfo
from src.type_utils import BlitInfo, RectPos
from src.consts import BG_LAYER, SPECIAL_LAYER
from src.imgs import (
    CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG,
    PENCIL_IMG, BUCKET_IMG, EYE_DROPPER_IMG, LINE_IMG, RECT_IMG,
)


ToolName: TypeAlias = Literal["pencil", "bucket", "eye_dropper", "line", "rectangle"]
ToolInfo: TypeAlias = tuple[ToolName, dict[str, Any]]
_ToolsInfo: TypeAlias = dict[ToolName, dict[str, Any]]
_ToolExtraInfo: TypeAlias = list[dict[str, Any]]

_CHECKBOX_IMGS: Final[list[pg.Surface]] = [CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG]
_TOOLS_INFO: Final[_ToolsInfo] = {
    "pencil": {
        "info": (PENCIL_IMG, "Pencil\n(SHIFT+P)"),
        "shortcut_k": K_p,
        "extra_info": (),
    },

    "bucket": {
        "info": (BUCKET_IMG, "Bucket\n(SHIFT+B)"),
        "shortcut_k": K_b,
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": (_CHECKBOX_IMGS, "Color Fill", "Fill pixels with\nthe same color"),
                "upt_args": (),
                "out_format": {"color_fill": "is_checked"},
            },
        ),
    },

    "eye_dropper": {
        "info": (EYE_DROPPER_IMG, "Eye Dropper\n(SHIFT+E)"),
        "shortcut_k": K_e,
        "extra_info": (),
    },

    "line": {
        "info": (LINE_IMG, "Line\n(SHIFT+L)"),
        "shortcut_k": K_l,
        "extra_info": (),
    },

    "rectangle": {
        "info": (RECT_IMG, "Rectangle\n(SHIFT+R)"),
        "shortcut_k": K_r,
        "extra_info": (
            {
                "type": Checkbox,
                "init_args": (_CHECKBOX_IMGS, "Fill", "Autofill\nthe rectangle"),
                "upt_args": (),
                "out_format": {"fill": "is_checked"},
            },
        ),
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

    def __init__(self: Self, pos: RectPos) -> None:
        """
        Creates the grid of tools and sub options.

        Args:
            position
        """

        tool_extra_info: _ToolExtraInfo

        self.tools_grid: CheckboxGrid = CheckboxGrid(
            pos,
            [info["info"] for info in _TOOLS_INFO.values()],
            num_cols=5, should_invert_cols=False, should_invert_rows=True
        )
        self._tool_name: ToolName = tuple(_TOOLS_INFO.keys())[0]

        def _refine_extra_info(raw_extra_info: tuple[dict[str, Any], ...]) -> _ToolExtraInfo:
            """
            Creates the sub options of a tool from its extra info.

            Args:
                raw extra info
            Returns:
                extra info
            """

            raw_sub_tool_extra_info: dict[str, Any]

            obj_x: int = self.tools_grid.rect.x + 16
            extra_info: _ToolExtraInfo = []
            for raw_sub_tool_extra_info in raw_extra_info:
                obj: UIElement = raw_sub_tool_extra_info["type"](
                    RectPos(obj_x, self.tools_grid.rect.y - 16, "bottomleft"),
                    *raw_sub_tool_extra_info["init_args"], base_layer=SPECIAL_LAYER
                )
                assert hasattr(obj, "rect"), obj.__class__.__name__

                rect: pg.Rect = obj.rect
                obj_x += rect.w + 16

                raw_sub_tool_extra_info["obj"] = obj
                del raw_sub_tool_extra_info["type"], raw_sub_tool_extra_info["init_args"]
                extra_info.append(raw_sub_tool_extra_info)

            return extra_info
        # Added keys: obj | removed keys: type, init_args
        self._tools_extra_info: list[_ToolExtraInfo] = [
            _refine_extra_info(info["extra_info"])
            for info in _TOOLS_INFO.values()
        ]

        self.saved_clicked_i: int | None = None

        self.hover_rects: tuple[pg.Rect, ...] = ()
        self.layer: int = BG_LAYER
        self.blit_sequence: list[BlitInfo] = []
        self.objs_info: list[ObjInfo] = [ObjInfo(self.tools_grid)]

        self._sub_tools_ranges: list[tuple[int, int]] = []
        for tool_extra_info in self._tools_extra_info:
            range_start: int = len(self.objs_info)

            for sub_tool_extra_info in tool_extra_info:
                obj_info: ObjInfo = ObjInfo(sub_tool_extra_info["obj"])
                self.objs_info.append(obj_info)
                obj_info.rec_set_active(False)

            range_end: int = len(self.objs_info)
            self._sub_tools_ranges.append((range_start, range_end))

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        if self.saved_clicked_i is not None:
            self.check(self.saved_clicked_i)
            self.saved_clicked_i = None

    def resize(self: Self, _win_w_ratio: float, _win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

    def check(self: Self, tool_i: int) -> None:
        """
        Sets the previous tool inactive and activates the new one.

        Args:
            tool index
        """

        obj_info: ObjInfo

        prev_clicked_i: int = self.tools_grid.prev_clicked_i
        prev_sub_tools_range_start_i: int = self._sub_tools_ranges[prev_clicked_i]           [0]
        prev_sub_tools_range_end_i: int   = self._sub_tools_ranges[prev_clicked_i]           [1]
        for obj_info in self.objs_info[prev_sub_tools_range_start_i:prev_sub_tools_range_end_i]:
            obj_info.rec_set_active(False)

        self.tools_grid.check(tool_i)
        self._tool_name = tuple(_TOOLS_INFO.keys())[self.tools_grid.clicked_i]

        sub_tools_range_start_i: int      = self._sub_tools_ranges[self.tools_grid.clicked_i][0]
        sub_tools_range_end_i: int        = self._sub_tools_ranges[self.tools_grid.clicked_i][1]
        for obj_info in self.objs_info[sub_tools_range_start_i:sub_tools_range_end_i]:
            obj_info.rec_set_active(True)

    def _handle_shortcuts(self: Self) -> None:
        """Handles changing the selection with the keyboard if shift is on."""

        i: int
        info: dict[str, Any]

        for i, info in enumerate(_TOOLS_INFO.values()):
            if info["shortcut_k"] in KEYBOARD.pressed:
                self.tools_grid.clicked_i = i

    def _upt_sub_objs(self: Self, local_vars: dict[str, Any]) -> dict[str, Any]:
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
            upt_args: list[str] = extra_info["upt_args"]
            extra_info["obj"].upt(*[
                local_vars.get(arg, arg)  # If it doesn't exist use it as a string
                for arg in upt_args
            ])

            out_format: dict[str, str] = extra_info["out_format"]
            for key, value in out_format.items():
                out_dict[key] = getattr(extra_info["obj"], value)

        return out_dict

    def upt(self: Self) -> ToolInfo:
        """
        Allows selecting a tool and its extra options.

        Returns:
            tool name, sub objects states
        """

        if KEYBOARD.is_shift_on and not KEYBOARD.is_ctrl_on:  # CTRL+SHIFT+P is for palettes
            self._handle_shortcuts()
        self.tools_grid.upt()

        if KEYBOARD.is_alt_on:
            self.saved_clicked_i = self.tools_grid.clicked_i
            self.tools_grid.clicked_i = _EYE_DROPPER_I
        elif self.saved_clicked_i is not None:
            self.tools_grid.clicked_i = self.saved_clicked_i
            self.saved_clicked_i = None

        out_dict: dict[str, Any] = self._upt_sub_objs(locals())
        return self._tool_name, out_dict
