"""
class to manage drawing tools
"""

import pygame as pg
from os import path
from typing import Final, Any

from src.classes.ui import CHECK_BOX_1, CHECK_BOX_2
from src.classes.check_box_grid import CheckBoxGrid
from src.classes.clickable import CheckBox
from src.utils import RectPos, MouseInfo, check_nested_hover
from src.type_utils import LayeredBlitSequence, LayerSequence

PENCIL: Final[pg.SurfaceType] = pg.image.load(
    path.join('sprites', 'pencil_tool.png')
).convert_alpha()
BUCKET: Final[pg.SurfaceType] = PENCIL.copy()

'''
all tools have:
- name
- base info (image and text)
- info for extra ui elements with:
    - type
    - arguments to create it (excluding position)
    - arguments to pass in the upt method
    - format to send it to the grid

extra ui elements need:
    blit(), check_hover(mouse info), leave(), handle_resize(window size ratio), upt(), rect
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
                    RectPos(current_x, current_y, 'bottomleft'), *obj_info['init_args']
                )
                current_x += obj.rect.w + 20.0
                obj_info['obj'] = obj

                del obj_info['type'], obj_info['init_args']
                objs_info.append(obj_info)
            self._extra_info.append(objs_info)

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = self._tools.blit()
        for info in self._extra_info[self._tools.clicked_i]:
            sequence += info['obj'].blit()

        return sequence

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
        '''
        checks if the mouse is hovering any interactable part of the object
        takes mouse position
        returns the object that's being hovered (can be None) and the layer
        '''

        hover_obj: Any
        hover_layer: int
        hover_obj, hover_layer = self._tools.check_hover(mouse_pos)

        extra_info = self._extra_info[self._tools.clicked_i]
        hover_obj, hover_layer = check_nested_hover(
            mouse_pos, (info['obj'] for info in extra_info), hover_obj, hover_layer
        )

        return hover_obj, hover_layer

    def leave(self) -> None:
        """
        clears relevant data when a state is leaved
        """

        self._tools.leave()
        for info in self._extra_info[self._tools.clicked_i]:
            info['obj'].leave()

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        self._tools.handle_resize(win_ratio_w, win_ratio_h)
        for tool_info in self._extra_info:
            for info in tool_info:
                info['obj'].handle_resize(win_ratio_w, win_ratio_h)

    def print_layers(self, name: str, counter: int) -> LayerSequence:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns a sequence to add in the main layer sequence
        """

        layer_sequence: LayerSequence = [(name, -1, counter)]
        layer_sequence += self._tools.print_layers('tools', counter + 1)
        layer_sequence += [('extra options', -1, counter + 1)]
        for tool_info in self._extra_info:
            for info in tool_info:
                layer_sequence += info['obj'].print_layers('option', counter + 2)

        return layer_sequence

    def upt(
            self, hover_obj: Any, mouse_info: MouseInfo, keys: list[int]
    ) -> tuple[str, dict[str, Any]]:
        """
        allows to select a tool and it's extra options
        takes hovered object (can be None), mouse info and keys
        returns the tool name and sub options state
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

        return self._names[self._tools.clicked_i], output_dict
