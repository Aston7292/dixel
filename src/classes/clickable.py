"""
Class to create various clickable objects
"""

import pygame as pg
from abc import ABC, abstractmethod
from typing import Optional, Any

from src.classes.text import Text
from src.utils import Point, RectPos, Size, MouseInfo
from src.type_utils import ObjsInfo, LayeredBlitSequence, LayerSequence
from src.consts import BG_LAYER, ELEMENT_LAYER, TOP_LAYER


class Clickable(ABC):
    """
    Abstract class to create an object that can be clicked and
    changes between two images (must be of the same size)

    Includes:
        base_blit(image index) -> PriorityBlitSequence
        check_hover(mouse_position) -> tuple[object, layer]
        leave() -> None
        handle_resize(window width ratio, window height ratio) -> None
        print_layer(name, depth counter) -> LayerSequence:

    Children should include:
        blit() -> PriorityBlitSequence
        upt(hovered object, mouse info) -> bool
    """

    __slots__ = (
        'init_pos', '_imgs', 'rect', '_init_size', '_hovering', '_layer', '_hoovering_layer',
        '_hover_text', '_hover_text_surfaces'
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType], hover_text: str,
            base_layer: int
    ) -> None:
        """
        Creates the object
        Args:
            position, two images, hover text, layer
        """

        self.init_pos: RectPos = pos

        self._imgs: tuple[pg.SurfaceType, ...] = imgs
        self.rect: pg.FRect = self._imgs[0].get_frect(**{self.init_pos.coord: self.init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self._hovering: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._hoovering_layer: int = base_layer + TOP_LAYER

        self._hover_text: Optional[Text] = None
        self._hover_text_surfaces: tuple[pg.SurfaceType, ...] = ()
        if hover_text:
            '''
            Blitting the hover text on these surfaces
            saves having to change the text x, y and init position every blit method call.
            It can't be done with other images
            because blitting something would permanently change them
            and it would be noticeable when the window is resized
            but these surfaces get recalculated every resize
            '''

            self._hover_text = Text(RectPos(0.0, 0.0, 'topleft'), hover_text, h=12)
            self._hover_text_surfaces = tuple(
                pg.Surface((int(rect.w), int(rect.h))) for rect in self._hover_text.rects
            )

            for target, (surf, _, _) in zip(self._hover_text_surfaces, self._hover_text.blit()):
                target.blit(surf)

    def _base_blit(self, img_i: int) -> LayeredBlitSequence:
        """
        Handles the base blitting behavior, draws the image at a given index
        Args:
            image index
        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._imgs[img_i], self.rect.topleft, self._layer)]
        if self._hovering:
            mouse_pos: Point = Point(*pg.mouse.get_pos())
            x: int = mouse_pos.x + 15
            y: int = mouse_pos.y
            for surf in self._hover_text_surfaces:
                sequence.append((surf, (x, y), self._hoovering_layer))
                y += surf.get_height()

        return sequence

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object's layer
        """

        return self if self.rect.collidepoint(mouse_pos) else None, self._layer

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._hovering = False

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes objects
        Args:
            window width ratio, window height ratio
        """

        size: tuple[int, int] = (
            int(self._init_size.w * win_ratio_w), int(self._init_size.h * win_ratio_h)
        )
        pos: tuple[float, float] = (self.init_pos.x * win_ratio_w, self.init_pos.y * win_ratio_h)

        self._imgs = tuple(pg.transform.scale(img, size) for img in self._imgs)
        self.rect = self._imgs[0].get_frect(**{self.init_pos.coord: pos})

        if self._hover_text:
            self._hover_text.handle_resize(win_ratio_w, win_ratio_h)
            self._hover_text_surfaces = tuple(
                pg.Surface((int(rect.w), int(rect.h))) for rect in self._hover_text.rects
            )

            for target, (surf, _, _) in zip(self._hover_text_surfaces, self._hover_text.blit()):
                target.blit(surf)

    def print_layer(self, name: str, depth_counter: int) -> LayerSequence:
        """
        Args:
            name, depth counter
        Returns:
            sequence to add in the main layer sequence
        """

        sequence: LayerSequence = [(name, self._layer, depth_counter)]
        if self._hover_text:
            sequence.append(('hover text', self._hoovering_layer, depth_counter + 1))

        return sequence

    @abstractmethod
    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

    @abstractmethod
    def upt(self, hover_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        Should implement a way to make the object interactable
        Args:
            hovered object (can be None), mouse info
        Returns:
            boolean related to clicking
        """


class CheckBox(Clickable):
    """
    Class to create a checkbox with text on top
    """

    __slots__ = (
        'ticked_on', 'sub_objs'
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType], text: str,
            hover_text: str = '', base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox and text
        Args:
            position, two images, text, hover text (default = ''), base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hover_text, base_layer)

        self.ticked_on: bool = False

        text_obj: Text = Text(
            RectPos(self.rect.centerx, self.rect.y - 5.0, 'midbottom'), text, base_layer, 16
        )
        self.sub_objs: ObjsInfo = [
            ('text', text_obj)
        ]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return self._base_blit(int(self.ticked_on))

    def upt(self, hover_obj: Any, mouse_info: MouseInfo, shortcut: bool = False) -> bool:
        """
        Changes the checkbox image when clicked
        Args:
            hovered object (can be None), mouse info, shortcut boolean (default = False)
        Returns:
            True if the checkbox was ticked on else False
        """

        if shortcut:
            self.ticked_on = not self.ticked_on

            return self.ticked_on

        if self != hover_obj:
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False

            return False

        if not self._hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self._hovering = True

        if mouse_info.released[0]:
            self.ticked_on = not self.ticked_on

            return self.ticked_on

        return False


class Button(Clickable):
    """
    Class to create a button, when hovered changes image
    """

    __slots__ = (
        'sub_objs',
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType], text: str,
            hover_text: str = '', base_layer: int = BG_LAYER, text_h: int = 24
    ) -> None:
        """
        Creates the button and text
        Args:
            position, two images, text, hover text (default = ''), base layer (default = BG_LAYER),
            text height (default = 24)
        """

        super().__init__(pos, imgs, hover_text, base_layer)

        self.sub_objs: ObjsInfo = []
        if text:
            text_obj: Text = Text(RectPos(*self.rect.center, 'center'), text, base_layer, text_h)
            self.sub_objs.append(('text', text_obj))

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return self._base_blit(int(self._hovering))

    def move_rect(self, x: float, y: float, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Moves the rect to a specific coordinate
        Args:
            x, y, window width ratio, window height ratio
        """

        self.init_pos.x, self.init_pos.y = x / win_ratio_w, y / win_ratio_h
        setattr(self.rect, self.init_pos.coord, (x, y))
        for _, obj in self.sub_objs:
            obj.move_rect(*self.rect.center, win_ratio_w, win_ratio_h)

    def upt(self, hover_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        Changes the button image if the mouse is hovering it
        Args:
            hovered object (can be None), mouse info
        Returns:
            True if the button was clicked else False
        """

        if self != hover_obj:
            if self._hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._hovering = False

            return False

        if not self._hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self._hovering = True

        return mouse_info.released[0]
