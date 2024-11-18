"""Class to create various clickable objects."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Optional, Any

import pygame as pg

from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio, ObjInfo, MouseInfo, resize_obj
from src.type_utils import LayeredBlitInfo, LayeredBlitSequence
from src.consts import BG_LAYER, ELEMENT_LAYER, TOP_LAYER


class Clickable(ABC):
    """
    Abstract class to create a clickable object with two images (must be of the same size).

    Includes:
        base_blit(image index) -> PriorityBlitSequence
        check_hovering(mouse_position) -> tuple[object, layer]
        leave() -> None
        resize(window size ratio) -> None
        move_rect(x, y, window size ratio) -> None

    Children should include:
        blit() -> PriorityBlitSequence
        upt(hovered object, mouse info) -> bool
    """

    __slots__ = (
        'init_pos', '_init_imgs', '_imgs', 'rect', '_is_hovering', '_layer', '_hovering_layer',
        '_hovering_text_label', '_hovering_text_imgs'
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.Surface, ...], hovering_text: Optional[str],
            base_layer: int
    ) -> None:
        """
        Creates the object.

        Args:
            position, two images, hovering text (can be None), base layer
        """

        self.init_pos: RectPos = pos
        self._init_imgs: tuple[pg.Surface, ...] = imgs

        self._imgs: tuple[pg.Surface, ...] = self._init_imgs
        self.rect: pg.Rect = self._imgs[0].get_rect(
            **{self.init_pos.coord_type: (self.init_pos.x, self.init_pos.y)}
        )

        self._is_hovering: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self._hovering_layer: int = base_layer + TOP_LAYER

        self._hovering_text_label: Optional[TextLabel] = None
        self._hovering_text_imgs: tuple[pg.Surface, ...] = ()
        if hovering_text is not None:
            # By blitting the hovering text here its attributes aren't modified every blit call.
            # It can't be done with other images since blitting something would change them,
            # it would be noticeable when resized but, these images get recalculated every time

            self._hovering_text_label = TextLabel(RectPos(0, 0, 'topleft'), hovering_text, h=12)
            self._hovering_text_imgs = tuple(
                pg.Surface(rect.size) for rect in self._hovering_text_label.rects
            )

            hovering_text_info: Iterator[tuple[pg.Surface, LayeredBlitInfo]] = zip(
                self._hovering_text_imgs, self._hovering_text_label.blit()
            )
            for img, (text_img, _, _) in hovering_text_info:
                img.blit(text_img)

    def _base_blit(self, img_i: int) -> LayeredBlitSequence:
        """
        Returns a sequence with the image at a given index and the hovering text if hovering.

        Args:
            image index
        Returns:
            sequence to add in the main blit sequence
        """

        sequence: LayeredBlitSequence = [(self._imgs[img_i], self.rect.topleft, self._layer)]
        if self._is_hovering:
            hovering_text_line_x: int = pg.mouse.get_pos()[0] + 15
            hovering_text_line_y: int = pg.mouse.get_pos()[1]
            for img in self._hovering_text_imgs:
                sequence.append(
                    (img, (hovering_text_line_x, hovering_text_line_y), self._hovering_layer)
                )
                hovering_text_line_y += img.get_height()

        return sequence

    def check_hovering(self, mouse_xy: tuple[int, int]) -> tuple[Any, int]:
        """
        Checks if the mouse is hovering any interactable part of the object.

        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object layer
        """

        return self if self.rect.collidepoint(mouse_xy) else None, self._layer

    def leave(self) -> None:
        """Clears all the relevant data when a state is leaved."""

        self._is_hovering = False

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        pos: tuple[int, int]
        size: tuple[int, int]
        pos, size = resize_obj(self.init_pos, *self._init_imgs[0].get_size(), win_ratio)

        self._imgs = tuple(pg.transform.scale(img, size) for img in self._init_imgs)
        self.rect = self._imgs[0].get_rect(**{self.init_pos.coord_type: pos})

        if self._hovering_text_label:
            self._hovering_text_label.resize(win_ratio)
            self._hovering_text_imgs = tuple(
                pg.Surface(rect.size) for rect in self._hovering_text_label.rects
            )

            hovering_text_info: Iterator[tuple[pg.Surface, LayeredBlitInfo]] = zip(
                self._hovering_text_imgs, self._hovering_text_label.blit()
            )
            for img, (text_img, _, _) in hovering_text_info:
                img.blit(text_img)

    def move_rect(self, x: int, y: int, win_ratio: Ratio) -> None:
        """
        Moves the rect to a specific coordinate.

        Args:
            x, y, window size ratio
        """

        self.init_pos.x, self.init_pos.y = x, y  # Modifying the init_pos is more accurate

        xy: tuple[int, int] = (round(x * win_ratio.w), round(y * win_ratio.h))
        setattr(self.rect, self.init_pos.coord_type, xy)

    @abstractmethod
    def blit(self) -> LayeredBlitSequence:
        """
        Should return the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

    @abstractmethod
    def upt(self, hovered_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        Should implement a way to make the object interactable.

        Args:
            hovered object (can be None), mouse info
        Returns:
            boolean related to clicking
        """


class Checkbox(Clickable):
    """Class to create a checkbox with text on top."""

    __slots__ = (
        'is_checked', 'objs_info'
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.Surface, ...], text: str,
            hovering_text: Optional[str], base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox and text.

        Args:
            position, two images, text, hovering text (can be None),
            base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

        text_label: TextLabel = TextLabel(
            RectPos(self.rect.centerx, self.rect.y - 5, 'midbottom'), text, base_layer, 16
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(text_label)]

    def blit(self) -> LayeredBlitSequence:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        return self._base_blit(int(self.is_checked))

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo, did_shortcut: bool = False) -> bool:
        """
        Changes the checkbox image when checked.

        Args:
            hovered object (can be None), mouse info, shortcut flag (default = False)
        Returns:
            True if the checkbox was checked else False
        """

        if self != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False
        elif not self._is_hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self._is_hovering = True

        was_checked: bool = False
        if (mouse_info.released[0] and self._is_hovering) or did_shortcut:
            self.is_checked = was_checked = not self.is_checked

        return was_checked


class Button(Clickable):
    """Class to create a button, when hovered changes image."""

    __slots__ = (
        'objs_info',
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.Surface, ...], text: Optional[str],
            hovering_text: Optional[str], base_layer: int = BG_LAYER, text_h: int = 24
    ) -> None:
        """
        Creates the button and text.

        Args:
            position, two images, text (can be None), hovering text (can be None),
            base layer (default = BG_LAYER), text height (default = 24)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.objs_info: list[ObjInfo] = []

        if text is not None:
            text_label: TextLabel = TextLabel(
                RectPos(*self.rect.center, 'center'), text, base_layer, text_h
            )
            self.objs_info.append(ObjInfo(text_label))

    def blit(self) -> LayeredBlitSequence:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        return self._base_blit(int(self._is_hovering))

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        Changes the button image if the mouse is hovering it.

        Args:
            hovered object (can be None), mouse info
        Returns:
            True if the button was clicked else False
        """

        if self != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False
        elif not self._is_hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            self._is_hovering = True

        return mouse_info.released[0] if self._is_hovering else False
