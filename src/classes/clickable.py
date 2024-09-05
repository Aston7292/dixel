"""
class to create various clickable objects
"""

import pygame as pg
from abc import ABC, abstractmethod
from typing import Optional, Any

from src.classes.text import Text
from src.utils import Point, RectPos, Size, MouseInfo, LayeredBlitSequence, LayersInfo
from src.const import BG_LAYER, ELEMENT_LAYER, HOVERING_LAYER


class Clickable(ABC):
    """
    abstract class to create and object that changes between two images

    - includes: base_blit(image index) -> PriorityBlitSequence,
    handle_resize(window size ratio) -> None
    - children should include: blit() -> PriorityBlitSequence, upt(mouse info) -> bool
    """

    __slots__ = (
        'init_pos', '_imgs', 'rect', '_init_size', 'hovering', '_layer', '_hoovering_layer',
        '_hover_text', '_hover_text_surfaces'
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType], hover_text: str,
            base_layer: int
    ) -> None:
        """
        creates the object
        takes position, two images, hover text and layer
        """

        self.init_pos: RectPos = pos

        self._imgs: tuple[pg.SurfaceType, ...] = imgs
        self.rect: pg.FRect = self._imgs[0].get_frect(**{self.init_pos.coord: self.init_pos.xy})

        self._init_size: Size = Size(int(self.rect.w), int(self.rect.h))

        self.hovering: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._hoovering_layer: int = base_layer + HOVERING_LAYER

        self._hover_text: Optional[Text] = None
        self._hover_text_surfaces: tuple[pg.SurfaceType, ...] = ()
        if hover_text:
            '''
            blitting the hover_text on the hover_text_surfaces
            saves having to change the text x, y and init_pos every blit call,
            it can't be done with other images
            because blitting something would permanently change them
            and it would be noticeable when resized
            but these surfaces get recalculated every handle_resize
            '''

            self._hover_text = Text(RectPos(0.0, 0.0, 'topleft'), hover_text, h=12)
            self._hover_text_surfaces = tuple(
                pg.Surface((int(rect.w), int(rect.h))) for rect in self._hover_text.rects
            )

            for target, (surf, _, _) in zip(self._hover_text_surfaces, self._hover_text.blit()):
                target.blit(surf)

    def _base_blit(self, img_i: int) -> LayeredBlitSequence:
        """
        handles the base blitting behavior, draws the image at a give index
        takes image index
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._imgs[img_i], self.rect.topleft, self._layer)]
        if self.hovering:
            mouse_pos: Point = Point(*pg.mouse.get_pos())
            x: int = mouse_pos.x + 15
            y: int = mouse_pos.y
            for surf in self._hover_text_surfaces:
                sequence += [(surf, (x, y), self._hoovering_layer)]
                y += surf.get_height()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
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

    def leave(self) -> None:
        """
        clears everything that needs to be cleared when the object is leaved
        """

        self.hovering = False

    def check_hover(self, mouse_pos: tuple[int, int]) -> tuple[Any, int]:
        '''
        checks if the mouse is hovering any interactable part of the object
        takes mouse position
        returns the object that's being hovered (can be None) and the layer
        '''

        obj: Any = self if self.rect.collidepoint(mouse_pos) else None

        return obj, self._layer

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = [(name, self._layer, counter)]
        if self._hover_text:
            layers_info += [('hover_text', self._hoovering_layer, counter + 1)]

        return layers_info

    @abstractmethod
    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

    @abstractmethod
    def upt(self, hover_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        should implement a way to make the object interactable
        takes hovered object (can be None) mouse info
        returns a boolean related to clicking
        """


class CheckBox(Clickable):
    """
    class to create a checkbox with text on top
    """

    __slots__ = (
        'ticked_on', '_text',
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType], text: str,
            hover_text: str = '', base_layer: int = BG_LAYER
    ) -> None:
        """
        creates the checkbox and text
        takes position, two images, text, hover text (default = '')
        and base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hover_text, base_layer)

        self.ticked_on: bool = False
        self._text: Text = Text(
            RectPos(self.rect.centerx, self.rect.y - 5.0, 'midbottom'), text, base_layer, 16
        )

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = self._base_blit(int(self.ticked_on))
        if self._text:
            sequence += self._text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        super().handle_resize(win_ratio_w, win_ratio_h)
        if self._text:
            self._text.handle_resize(win_ratio_w, win_ratio_h)

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = super().print_layers(name, counter)
        layers_info += self._text.print_layers('text', counter + 1)

        return layers_info

    def upt(self, hover_obj: Any, mouse_info: MouseInfo, shortcut: bool = False) -> bool:
        """
        changes the checkbox image when clicked
        takes hovered object (can be None), mouse info and shortcut bool (default = False)
        returns True if the checkbox was ticked on
        """

        if shortcut:
            self.ticked_on = not self.ticked_on

            return self.ticked_on

        if self != hover_obj:
            if self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.leave()

            return False

        if not self.hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self.hovering = True

        if mouse_info.released[0]:
            self.ticked_on = not self.ticked_on

            return self.ticked_on

        return False


class Button(Clickable):
    """
    class to create a button, when hovered changes image
    """

    __slots__ = (
        '_text',
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.SurfaceType, pg.SurfaceType], text: str,
            hover_text: str = '', base_layer: int = BG_LAYER, text_h: int = 24
    ) -> None:
        """
        creates the button and text
        takes position, two images, text, hover text (default = ''),
        base layer (default = BG_LAYER) and text height (default = 24)
        """

        super().__init__(pos, imgs, hover_text, base_layer)

        self._text: Optional[Text] = None
        if text:
            self._text = Text(RectPos(*self.rect.center, 'center'), text, base_layer, text_h)

    def blit(self) -> LayeredBlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = self._base_blit(int(self.hovering))
        if self._text:
            sequence += self._text.blit()

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        super().handle_resize(win_ratio_w, win_ratio_h)
        if self._text:
            self._text.handle_resize(win_ratio_w, win_ratio_h)

    def print_layers(self, name: str, counter: int) -> LayersInfo:
        """
        prints the layers of everything the object has
        takes name and nesting counter
        returns layers info
        """

        layers_info: LayersInfo = super().print_layers(name, counter)
        if self._text:
            layers_info += self._text.print_layers('text', counter + 1)

        return layers_info

    def move_rect(self, x: float, y: float, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        moves the rect to a specific coordinate
        takes x, y and window size ratio
        """

        self.init_pos.x, self.init_pos.y = x / win_ratio_w, y / win_ratio_h
        setattr(self.rect, self.init_pos.coord, (x, y))
        if self._text:
            self._text.move_rect(*self.rect.center, win_ratio_w, win_ratio_h)

    def upt(self, hover_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        updates the button image if the mouse is hovering it
        takes hovered object (can be None) and mouse info
        returns whatever the button was clicked or not
        """

        if self != hover_obj:
            if self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.leave()

            return False

        if not self.hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self.hovering = True

        return mouse_info.released[0]
