"""
class to manage drawing tools
"""

import pygame as pg
from os import path
from typing import Tuple, List, Dict, Final, Any

from src.classes.ui import CHECK_BOX_1, CHECK_BOX_2
from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import CheckBox
from src.utils import RectPos, MouseInfo, BlitSequence

PENCIL: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'pencil_tool.png')
).convert_alpha()
BUCKET: Final[pg.SurfaceType] = PENCIL.copy()

'''
each tool has:
- name
- base info (image and text)
- info for extra ui elements with:
    - type
    - arguments to create it (excluding position)
    - arguments to pass in the upt method
    - format to send it to the grid

extra ui element need:
    blit(), handle_resize(window size ratio), upt()
    rect
'''

TOOLS_INFO: Dict[str, Dict[str, Any]] = {
    'brush': {
        'base_info': (PENCIL, 'edit pixels'),
        'extra_info': [
            {
                'type': CheckBox, 'init_args': [(CHECK_BOX_1, CHECK_BOX_2), 'x mirror'],
                'upt_args': ['mouse_info'], 'output_format': {'x_mirror': 'ticked_on'}
            },
            {
                'type': CheckBox, 'init_args': [(CHECK_BOX_1, CHECK_BOX_2), 'y mirror'],
                'upt_args': ['mouse_info'], 'output_format': {'y_mirror': 'ticked_on'}
            },
        ],
    },
    'fill': {
        'base_info': (BUCKET, 'fill'),
        'extra_info': [
            {
                'type': CheckBox,
                'init_args': [(CHECK_BOX_1, CHECK_BOX_2), 'edit pixels of\nthe same color'],
                'upt_args': ['mouse_info'], 'output_format': {'same_color': 'ticked_on'}
            }
        ]
    }
}


class ToolsManager:
    """
    class to manage drawing tools
    """

    __slots__ = (
        '_names', '_tools', '_extra_info'
    )

    def __init__(self, pos: RectPos) -> None:
        """
        creates a grid of options and sub options
        takes position
        """

        self._names: Tuple[str, ...] = tuple(TOOLS_INFO.keys())
        base_info: List[Tuple[pg.SurfaceType, str]] = [
            info['base_info'] for info in TOOLS_INFO.values()
        ]
        extra_info: Tuple[List[Dict[str, Any]], ...] = tuple(
            info['extra_info'] for info in TOOLS_INFO.values()
        )

        self._tools: CheckBoxGrid = CheckBoxGrid(pos, base_info, 5, (False, True))

        self._extra_info: List[List[Dict[str, Any]]] = []
        for tool_info in extra_info:
            objs_info: List[Dict[str, Any]] = []

            check_box_rect: Tuple[pg.FRect, ...] = tuple(
                check_box.rect for check_box in self._tools.check_boxes
            )
            current_x: float = min(rect.x for rect in check_box_rect) + 20.0
            current_y: float = min(rect.y for rect in check_box_rect) - 20.0

            for i in range(len(tool_info)):
                obj_info: Dict[str, Any] = tool_info[i]

                obj: Any = obj_info['type'](
                    RectPos(current_x, current_y, 'bottomleft'), *obj_info['init_args']
                )
                current_x += obj.rect.w + 20.0
                obj_info['obj'] = obj

                del obj_info['type'], obj_info['init_args']
                objs_info.append(obj_info)
            self._extra_info.append(objs_info)

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = self._tools.blit()
        for info in self._extra_info[self._tools.clicked_i]:
            sequence += info['obj'].blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self._tools.handle_resize(win_ratio_w, win_ratio_h)
        for tool_info in self._extra_info:
            for info in tool_info:
                info['obj'].handle_resize(win_ratio_w, win_ratio_h)

    def upt(self, mouse_info: MouseInfo, keys: List[int]) -> Tuple[str, Dict[str, Any]]:
        """
        makes the object interactable
        takes mouse info and keys
        returns the tool name and sub options state
        """

        self._tools.upt(mouse_info, keys)

        local_vars: Dict[str, Any] = locals()
        output_dict: Dict[str, Any] = {}
        for info in self._extra_info[self._tools.clicked_i]:
            args: Tuple[Any, ...] = tuple(local_vars[arg] for arg in info['upt_args'])
            info['obj'].upt(*args)

            obj_output_dict: Dict[str, Any] = info['output_format'].copy()
            for key in obj_output_dict:
                obj_output_dict[key] = getattr(info['obj'], obj_output_dict[key])
            output_dict.update(obj_output_dict)

        return self._names[self._tools.clicked_i], output_dict
