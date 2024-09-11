"""
Class to manage drawing tools
"""

import pygame as pg
from os import path
from typing import Final, Any

from src.classes.ui import CHECK_BOX_1, CHECK_BOX_2
from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import CheckBox
from src.utils import RectPos, MouseInfo
from src.type_utils import ObjsInfo, LayerSequence
from src.consts import SPECIAL_LAYER

PENCIL: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'pencil_tool.png')
).convert_alpha()
BUCKET: Final[pg.SurfaceType] = PENCIL.copy()

'''
All tools have:
- name
- base info (image and text)
- info for extra ui elements with:
    - type
    - arguments to create it (excluding position)
    - arguments to pass in the upt method
    - format to send it to the grid

Extra ui elements need:
    - a position argument as first in the constructor
    - a base_layer argument in the constructor
    - an upt method
    - a rect attribute
'''

TOOLS_INFO: dict[str, dict[str, Any]] = {
    'brush': {
        'base_info': (PENCIL, 'edit pixels'),
        'extra_info': [
            {
                'type': CheckBox, 'init_args': [(CHECK_BOX_1, CHECK_BOX_2), 'x mirror'],
                'upt_args': ['hover_obj', 'mouse_info'],
                'output_format': {'x_mirror': 'ticked_on'}
            },
            {
                'type': CheckBox, 'init_args': [(CHECK_BOX_1, CHECK_BOX_2), 'y mirror'],
                'upt_args': ['hover_obj', 'mouse_info'],
                'output_format': {'y_mirror': 'ticked_on'}
            },
        ],
    },
    'fill': {
        'base_info': (BUCKET, 'fill'),
        'extra_info': [
            {
                'type': CheckBox,
                'init_args': [(CHECK_BOX_1, CHECK_BOX_2), 'edit pixels of\nthe same color'],
                'upt_args': ['hover_obj', 'mouse_info'],
                'output_format': {'same_color': 'ticked_on'}
            }
        ]
    }
}


class ToolsManager:
    """
    Class to manage drawing tools
    """

    __slots__ = (
        '_names', '_tools', '_extra_info', '_init_sub_objs', 'sub_objs'
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Creates the grid of options and sub options
        Args:
            position
        """

        self._names: tuple[str, ...] = tuple(TOOLS_INFO.keys())
        base_info: list[tuple[pg.SurfaceType, str]] = [
            info['base_info'] for info in TOOLS_INFO.values()
        ]
        extra_info: tuple[list[dict[str, Any]], ...] = tuple(
            info['extra_info'] for info in TOOLS_INFO.values()
        )

        self._tools: CheckBoxGrid = CheckBoxGrid(pos, base_info, 5, (False, True))

        self._extra_info: list[list[dict[str, Any]]] = []
        for tool_info in extra_info:
            objs_info: list[dict[str, Any]] = []

            check_box_rect: tuple[pg.FRect, ...] = tuple(
                check_box.rect for check_box in self._tools.check_boxes
            )
            current_x: float = min(rect.x for rect in check_box_rect) + 20.0
            current_y: float = min(rect.y for rect in check_box_rect) - 20.0

            for i in range(len(tool_info)):
                obj_info: dict[str, Any] = tool_info[i]

                obj: Any = obj_info['type'](
                    RectPos(current_x, current_y, 'bottomleft'), *obj_info['init_args'],
                    base_layer=SPECIAL_LAYER
                )
                current_x += obj.rect.w + 20.0
                obj_info['obj'] = obj

                del obj_info['type'], obj_info['init_args']
                objs_info.append(obj_info)
            self._extra_info.append(objs_info)

        self._init_sub_objs: ObjsInfo = [
            ('tools', self._tools)
        ]
        # Sub options are only added when visible
        self.sub_objs: ObjsInfo = self._init_sub_objs.copy()

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        return [(name, -1, depth_counter)]

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: list[int]
    ) -> tuple[str, dict[str, Any]]:
        """
        Allows selecting a tool and it's extra options
        Args:
            hovered object (can be None), mouse info, keys
        Returns:
            tool name, sub options state
        """

        self._tools.upt(hover_obj, mouse_info, keys)

        local_vars: dict[str, Any] = locals()
        output_dict: dict[str, Any] = {}
        for info in self._extra_info[self._tools.clicked_i]:
            args: tuple[Any, ...] = tuple(local_vars[arg] for arg in info['upt_args'])
            info['obj'].upt(*args)

            obj_output_dict: dict[str, Any] = info['output_format'].copy()
            for key in obj_output_dict:
                obj_output_dict[key] = getattr(info['obj'], obj_output_dict[key])
            output_dict.update(obj_output_dict)

        self.sub_objs = self._init_sub_objs.copy()
        self.sub_objs += [
            (f'option {i}', info['obj'])
            for i, info in enumerate(self._extra_info[self._tools.clicked_i])
        ]

        return self._names[self._tools.clicked_i], output_dict
