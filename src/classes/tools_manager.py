"""
Class to manage the drawing tools.

Tools must have:
- name
- info (image and text)
- shortcut key
- sub tools info:
    - type
    - constructor args (excluding position)
    - upt method args
    - dict format to send it to the grid

Sub tools need:
    - to be a subclass of UIElement
    - a position argument as first in the constructor
    - a base_layer argument in the constructor
    - a rect attribute
    - an upt method
    - (optional) importState/exportState methods for loading/saving
"""

from typing import Self, Literal, TypeAlias, Final, Any

from pygame import Surface, Rect, K_b, K_e, K_l, K_i, K_p, K_r

from src.classes.checkbox_grid import CheckboxGrid
from src.classes.clickable import Checkbox
from src.classes.devices import KEYBOARD

from src.obj_utils import UIElement
from src.type_utils import RectPos
from src.consts import SPECIAL_LAYER
from src.imgs import (
    CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG,
    PENCIL_IMG, ERASER_IMG, BUCKET_IMG, EYE_DROPPER_IMG, LINE_IMG, RECT_IMG,
)


ToolName: TypeAlias = Literal["pencil", "eraser", "bucket", "eye_dropper", "line", "rect"]
ToolInfo: TypeAlias = tuple[ToolName, dict[str, Any]]
_ToolsInfo: TypeAlias = dict[ToolName, dict[str, Any]]
_SubToolsInfo: TypeAlias = tuple[dict[str, Any], ...]

_CHECKBOX_IMGS: Final[tuple[Surface, ...]] = (CHECKBOX_OFF_IMG, CHECKBOX_ON_IMG)
_TOOLS_INFO: Final[_ToolsInfo] = {
    "pencil": {
        "info": (PENCIL_IMG, "Pencil\n(SHIFT+P)"),
        "shortcut_k": K_p,
        "sub_info": (),
    },

    "eraser": {
        "info": (ERASER_IMG, "Eraser\n(SHIFT+E)"),
        "shortcut_k": K_e,
        "sub_info": (),
    },

    "bucket": {
        "info": (BUCKET_IMG, "Bucket\n(SHIFT+B)"),
        "shortcut_k": K_b,
        "sub_info": (
            {
                "type": Checkbox,
                "init_args": (_CHECKBOX_IMGS, "Color Fill", "Fill pixels with\nthe same color"),
                "upt_args": (),
                "out_format": {"color_fill": "is_checked"},
            },
        ),
    },

    "eye_dropper": {
        "info": (EYE_DROPPER_IMG, "Eye Dropper\n(SHIFT+I)"),
        "shortcut_k": K_i,
        "sub_info": (),
    },

    "line": {
        "info": (LINE_IMG, "Line\n(SHIFT+L)"),
        "shortcut_k": K_l,
        "sub_info": (),
    },

    "rect": {
        "info": (RECT_IMG, "Rectangle\n(SHIFT+R)"),
        "shortcut_k": K_r,
        "sub_info": (
            {
                "type": Checkbox,
                "init_args": (_CHECKBOX_IMGS, "Fill", "Autofill\nthe rectangle"),
                "upt_args": (),
                "out_format": {"fill": "is_checked"},
            },
        ),
    },
}
del _CHECKBOX_IMGS

_EYE_DROPPER_I: Final[int] = 3


class ToolsManager(UIElement):
    """Class to manage drawing tools."""

    __slots__ = (
        "tools_grid", "_tool_name", "_all_sub_tools_info",
        "saved_clicked_i",
    )

    def __init__(self: Self, pos: RectPos) -> None:
        """
        Creates the grid of tools and sub tools.

        Args:
            position
        """

        super().__init__()

        sub_tools_info: _SubToolsInfo
        sub_tool_info: dict[str, Any]

        self.tools_grid: CheckboxGrid = CheckboxGrid(
            pos,
            tuple([info["info"] for info in _TOOLS_INFO.values()]),
            cols=5, should_invert_cols=False, should_invert_rows=True
        )
        self._tool_name: ToolName = tuple(_TOOLS_INFO.keys())[0]

        def _refine_sub_tools_info(raw_sub_tools_info: _SubToolsInfo) -> _SubToolsInfo:
            """
            Creates the sub tools of a tool from their info.
            (Added keys: obj | removed keys: type, init_args)

            Args:
                raw info
            Returns:
                info
            """

            raw_info: dict[str, Any]

            sub_tools_info: _SubToolsInfo = ()
            sub_tool_x: int = self.tools_grid.rect.x + 8
            for raw_info in raw_sub_tools_info:
                sub_tool: UIElement = raw_info["type"](
                    RectPos(sub_tool_x, self.tools_grid.rect.y - 16, "bottomleft"),
                    *raw_info["init_args"], base_layer=SPECIAL_LAYER
                )
                assert (
                    hasattr(sub_tool, "rect") and isinstance(sub_tool.rect, Rect) and
                    hasattr(sub_tool, "import_state") and callable(sub_tool.import_state) and
                    hasattr(sub_tool, "export_state") and callable(sub_tool.export_state) and
                    hasattr(sub_tool, "upt")  and callable(sub_tool.upt)
                ), sub_tool.__class__.__name__

                rect: Rect = sub_tool.rect
                sub_tool_x += rect.w + 16

                raw_info["obj"] = sub_tool
                del raw_info["type"], raw_info["init_args"]
                sub_tools_info += (raw_info,)

            return sub_tools_info
        self._all_sub_tools_info: tuple[_SubToolsInfo, ...] = tuple([
            _refine_sub_tools_info(info["sub_info"])
            for info in _TOOLS_INFO.values()
        ])

        self.saved_clicked_i: int | None = None

        self.sub_objs = (self.tools_grid,)
        for sub_tools_info in self._all_sub_tools_info:
            for sub_tool_info in sub_tools_info:
                sub_tool: UIElement = sub_tool_info["obj"]
                self.sub_objs += (sub_tool,)
                sub_tool.rec_set_active(False)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        if self.saved_clicked_i is not None:
            self.check(self.saved_clicked_i)
            self.saved_clicked_i = None

    def check(self: Self, tool_i: int) -> None:
        """
        Sets the previous tool inactive and activates the new one.

        Args:
            tool index
        """

        sub_tool_info: dict[str, Any]
        sub_tool: UIElement

        for sub_tool_info in self._all_sub_tools_info[self.tools_grid.prev_clicked_i]:
            sub_tool = sub_tool_info["obj"]
            sub_tool.rec_set_active(False)

        self.tools_grid.check(tool_i)
        self._tool_name = tuple(_TOOLS_INFO.keys())[self.tools_grid.clicked_i]

        for sub_tool_info in self._all_sub_tools_info[self.tools_grid.clicked_i]:
            sub_tool = sub_tool_info["obj"]
            sub_tool.rec_set_active(True)

    def import_sub_tools_states(self: Self, all_info: list[Any]) -> None:
        """
        Sets all the relevant sub tools info.

        Args:
            info
        """

        sub_tools_info: _SubToolsInfo
        sub_tool_info: dict[str, Any]

        i: int = 0
        for sub_tools_info in self._all_sub_tools_info:
            for sub_tool_info in sub_tools_info:
                sub_tool: UIElement = sub_tool_info["obj"]
                assert hasattr(sub_tool, "import_state") and callable(sub_tool.import_state)
                sub_tool.import_state(all_info[i])
                i += 1

    def export_sub_tools_states(self: Self) -> list[Any]:
        """
        Gets all the relevant sub tools info.

        Returns:
            info
        """

        sub_tools_info: _SubToolsInfo
        sub_tool_info: dict[str, Any]

        all_info: list[Any] = []
        for sub_tools_info in self._all_sub_tools_info:
            for sub_tool_info in sub_tools_info:
                sub_tool: UIElement = sub_tool_info["obj"]
                assert hasattr(sub_tool, "export_state") and callable(sub_tool.export_state)
                all_info.append(sub_tool.export_state())

        return all_info

    def _handle_shortcuts(self: Self) -> None:
        """Handles changing the selection with the keyboard if shift is on."""

        i: int
        info: dict[str, Any]

        for i, info in enumerate(_TOOLS_INFO.values()):
            if info["shortcut_k"] in KEYBOARD.pressed:
                self.tools_grid.clicked_i = i

    def _upt_sub_tools(self: Self, local_vars: dict[str, Any]) -> dict[str, Any]:
        """
        Updates the sub tools and returns the needed attribute as a dictionary.

        Args:
            local variables
        Returns:
            output dictionary
        """

        info: dict[str, Any]
        out_format_k: str
        out_format_v: str

        out_dict: dict[str, Any] = {}
        for info in self._all_sub_tools_info[self.tools_grid.clicked_i]:
            upt_args: tuple[str, ...] = info["upt_args"]
            info["obj"].upt(*[
                local_vars.get(arg, arg)  # If it doesn't exist use it as a string
                for arg in upt_args
            ])

            out_format: dict[str, str] = info["out_format"]
            for out_format_k, out_format_v in out_format.items():
                out_dict[out_format_k] = getattr(info["obj"], out_format_v)

        return out_dict

    def upt(self: Self) -> ToolInfo:
        """
        Allows selecting a tool and handles its sub tools.

        Returns:
            tool name, sub tools out dict
        """

        if KEYBOARD.is_shift_on and not KEYBOARD.is_ctrl_on:  # CTRL+SHIFT+P is for palettes
            self._handle_shortcuts()
        self.tools_grid.upt()

        if KEYBOARD.is_alt_on:
            if self.saved_clicked_i is None:
                self.saved_clicked_i = self.tools_grid.clicked_i
                self.tools_grid.clicked_i = _EYE_DROPPER_I
        elif self.saved_clicked_i is not None:
            self.tools_grid.clicked_i = self.saved_clicked_i
            self.saved_clicked_i = None

        out_dict: dict[str, Any] = self._upt_sub_tools(locals())
        return self._tool_name, out_dict
