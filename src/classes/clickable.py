"""Class to create various clickable objects."""

from abc import ABC, abstractmethod
from typing import Final, Optional, Any

import pygame as pg

from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio, ObjInfo, Mouse, resize_obj, rec_move_rect, rec_resize
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import MOUSE_LEFT, BLACK, BG_LAYER, ELEMENT_LAYER, TEXT_LAYER, TOP_LAYER

DEFAULT_RATIO: Final[Ratio] = Ratio(1, 1)
INIT_CLICK_INTERVAL: Final[int] = 100


class Clickable(ABC):
    """
    Abstract class to create a clickable object with two images (with same size) and hovering text.

    Includes:
        get_blit_sequence() -> layered blit sequence
        get_hovering_info(mouse_xy) -> tuple[is hovering, layer]
        leave() -> None
        resize(window size ratio) -> None
        move_rect(xy, window size ratio) -> None

    Children should include:
        upt(mouse) -> bool
    """

    __slots__ = (
        "init_pos", "init_imgs", "imgs", "rect", "img_i", "_is_hovering", "_layer", "cursor_type",
        "hovering_text_label"
    )

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], hovering_text: Optional[str],
            base_layer: int
    ) -> None:
        """
        Creates the object.

        Args:
            position, two images, hovering text (can be None), base layer
        """

        self.init_pos: RectPos = pos
        self.init_imgs: list[pg.Surface] = imgs

        self.imgs: list[pg.Surface] = self.init_imgs
        self.rect: pg.Rect = self.imgs[0].get_rect(**{self.init_pos.coord_type: self.init_pos.xy})

        self.img_i: int = 0
        self._is_hovering: bool = False

        self._layer: int = base_layer + ELEMENT_LAYER
        self.cursor_type: int = pg.SYSTEM_CURSOR_HAND

        # Better if it's not in objs_info
        self.hovering_text_label: Optional[TextLabel]
        if hovering_text is None:
            self.hovering_text_label = None
        else:
            hovering_text_layer: int = base_layer + TOP_LAYER - TEXT_LAYER
            self.hovering_text_label = TextLabel(
                RectPos(0, 0, "topleft"), hovering_text, hovering_text_layer, 12, BLACK
            )

    def get_blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        img: pg.Surface = self.imgs[self.img_i]
        sequence: list[LayeredBlitInfo] = [(img, self.rect.topleft, self._layer)]

        if self._is_hovering and self.hovering_text_label:
            mouse_x: int
            mouse_y: int
            mouse_x, mouse_y = pg.mouse.get_pos()
            rec_move_rect(self.hovering_text_label, mouse_x + 15, mouse_y, DEFAULT_RATIO)

            hovering_text_label_objs: list[Any] = [self.hovering_text_label]
            while hovering_text_label_objs:
                obj: Any = hovering_text_label_objs.pop()
                if hasattr(obj, "get_blit_sequence"):
                    sequence.extend(obj.get_blit_sequence())
                if hasattr(obj, "objs_info"):
                    hovering_text_label_objs.extend([info.obj for info in obj.objs_info])

        return sequence

    def get_hovering_info(self, mouse_xy: PosPair) -> tuple[bool, int]:
        """
        Gets the hovering info.

        Args:
            mouse xy
        Returns:
            hovered flag, hovered object layer
        """

        return self.rect.collidepoint(mouse_xy), self._layer

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self._is_hovering = False

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        xy: PosPair
        wh: SizePair
        xy, wh = resize_obj(self.init_pos, *self.init_imgs[0].get_size(), win_ratio)

        self.imgs = [pg.transform.scale(img, wh) for img in self.init_imgs]
        self.rect = self.imgs[0].get_rect(**{self.init_pos.coord_type: xy})

        if self.hovering_text_label:
            rec_resize([self.hovering_text_label], win_ratio)

    def move_rect(self, init_xy: PosPair, win_ratio: Ratio) -> None:
        """
        Moves the rect to a specific coordinate.

        Args:
            initial xy, window size ratio
        """

        self.init_pos.xy = init_xy  # Modifying init_pos is more accurate

        xy: PosPair
        xy, _ = resize_obj(self.init_pos, 0, 0, win_ratio)
        setattr(self.rect, self.init_pos.coord_type, xy)

    @abstractmethod
    def upt(self, mouse: Mouse) -> bool:
        """
        Should implement a way to make the object interactable.

        Args:
            mouse
        Returns:
            boolean related to clicking
        """


class Checkbox(Clickable):
    """Class to create a checkbox with text on top."""

    __slots__ = (
        "is_checked", "objs_info"
    )

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], text: str, hovering_text: Optional[str],
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox and text.

        Args:
            position, two images, text, hovering text (can be None),
            base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

        text_label_pos: RectPos = RectPos(self.rect.centerx, self.rect.y - 5, "midbottom")
        text_label: TextLabel = TextLabel(text_label_pos, text, base_layer, 16)

        self.objs_info: list[ObjInfo] = [ObjInfo(text_label)]

    def upt(self, mouse: Mouse, is_shortcutting: bool = False) -> bool:
        """
        Changes the checkbox image when checked.

        Args:
            mouse, shortcutting flag (default = False)
        Returns:
            has been checked flag
        """

        self._is_hovering = mouse.hovered_obj == self

        has_toggled: bool = (mouse.released[MOUSE_LEFT] and self._is_hovering) or is_shortcutting
        if has_toggled:
            self.is_checked = not self.is_checked
            self.img_i = int(self.is_checked)

        return has_toggled and self.is_checked


class Button(Clickable):
    """Class to create a button, when hovered changes image."""

    __slots__ = (
        "objs_info",
    )

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], text: Optional[str],
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
            text_label_pos: RectPos = RectPos(*self.rect.center, "center")
            text_label: TextLabel = TextLabel(text_label_pos, text, base_layer, text_h)
            self.objs_info = [ObjInfo(text_label)]

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        super().leave()
        self.img_i = 0

    def upt(self, mouse: Mouse) -> bool:
        """
        Changes the button image if the mouse is hovering it.

        Args:
            mouse
        Returns:
            clicked flag
        """

        self._is_hovering = mouse.hovered_obj == self
        self.img_i = int(self._is_hovering)

        return mouse.released[MOUSE_LEFT] and self._is_hovering


class SpammableButton(Clickable):
    """Class to create a spammable button, when hovered changes image."""

    __slots__ = (
        "_click_interval", "_last_click_time", "_is_first_click"
    )

    def __init__(self, pos: RectPos, imgs: list[pg.Surface], base_layer: int = BG_LAYER) -> None:
        """
        Creates the button and text.

        Args:
            position, two images, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, "", base_layer)

        self._click_interval: int = INIT_CLICK_INTERVAL
        self._last_click_time: int = -INIT_CLICK_INTERVAL
        self._is_first_click: bool = True

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        super().leave()
        self.img_i = 0

        self._click_interval = INIT_CLICK_INTERVAL
        self._last_click_time = -INIT_CLICK_INTERVAL
        self._is_first_click = True

    def upt(self, mouse: Mouse) -> bool:
        """
        Changes the button image if the mouse is hovering it.

        Args:
            mouse
        Returns:
            clicked flag
        """

        self._is_hovering = mouse.hovered_obj == self
        self.img_i = int(self._is_hovering)

        is_clicked: bool = False
        if not mouse.pressed[MOUSE_LEFT]:
            self._is_first_click = True
        elif self._is_hovering:
            time: int = pg.time.get_ticks()
            if self._is_first_click:
                self._click_interval = INIT_CLICK_INTERVAL
                self._last_click_time = time + 150  # Takes longer for second click
                self._is_first_click = False
                is_clicked = True
            elif time - self._last_click_time >= self._click_interval:
                self._click_interval = max(self._click_interval - 10, 10)
                self._last_click_time = time
                is_clicked = True

        return is_clicked
