"""Classes to create various clickable objects."""

from abc import ABC, abstractmethod
from typing import Final

import pygame as pg
from pygame import SYSTEM_CURSOR_HAND

from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE

from src.utils import RectPos, ObjInfo, resize_obj, rec_move_rect
from src.type_utils import XY, WH, BlitInfo
import src.vars as VARS
from src.consts import MOUSE_LEFT, BLACK, BG_LAYER, ELEMENT_LAYER, TOP_LAYER

_INIT_CLICK_INTERVAL: Final[int] = 100


class _Clickable(ABC):
    """
    Abstract class to create a clickable object with various images and hovering text.

    Includes:
        hover_rects
        layer
        cursor_type
        objs_info

        blit_sequence() -> blit sequence
        enter() -> None
        leave() -> None
        resize(window width ratio, window height ratio) -> None
        move_rect(x, y, window width ratio, window height ratio) -> None

    Children should include:
        upt(extra info) -> bool
    """

    __slots__ = (
        "init_pos", "init_imgs", "imgs", "rect",
        "img_i", "_is_hovering",
        "hovering_text_label", "hovering_text_alpha", "_last_mouse_move_time",
        "hover_rects", "layer", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_HAND

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], hovering_text: str, base_layer: int
    ) -> None:
        """
        Creates the object and hovering text.

        Args:
            position, images, hovering text, base layer
        """

        img: pg.Surface

        self.init_pos: RectPos = pos

        self.init_imgs: list[pg.Surface] = imgs  # Better for scaling
        self.imgs: list[pg.Surface] = self.init_imgs
        self.rect: pg.Rect = pg.Rect(0, 0, *self.imgs[0].get_size())
        setattr(self.rect, self.init_pos.coord_type, (self.init_pos.x, self.init_pos.y))

        self.img_i: int = 0
        self._is_hovering: bool = False

        # Better if it's not in objs_info, activating a drop-down menu will activate it too
        self.hovering_text_label: TextLabel = TextLabel(
            RectPos(MOUSE.x, MOUSE.y, "topleft"),
            hovering_text, BG_LAYER, 12, BLACK
        )
        self.hovering_text_label.layer = base_layer + TOP_LAYER
        self.hovering_text_alpha: int = 0
        self._last_mouse_move_time: int = VARS.ticks

        for img in self.hovering_text_label.imgs:
            img.set_alpha(self.hovering_text_alpha)

        self.hover_rects: list[pg.Rect] = [self.rect]
        self.layer: int = base_layer + ELEMENT_LAYER
        self.objs_info: list[ObjInfo] = []

    @property
    def blit_sequence(self) -> list[BlitInfo]:
        """
        Gets the blit sequence and handles the gradual appearance of the hovering text.

        Returns:
            sequence to add in the main blit sequence
        """

        img: pg.Surface

        sequence: list[BlitInfo] = [(self.imgs[self.img_i], self.rect, self.layer)]
        if self._is_hovering and (VARS.ticks - self._last_mouse_move_time >= 750):
            if self.hovering_text_alpha != 255:
                self.hovering_text_alpha = round(self.hovering_text_alpha + (16 * VARS.dt))
                self.hovering_text_alpha = min(self.hovering_text_alpha, 255)
                for img in self.hovering_text_label.imgs:
                    img.set_alpha(self.hovering_text_alpha)

            rec_move_rect(self.hovering_text_label, MOUSE.x + 10, MOUSE.y, 1, 1)
            sequence.extend(self.hovering_text_label.blit_sequence)
        elif self.hovering_text_alpha != 0:
            self.hovering_text_alpha = 0
            for img in self.hovering_text_label.imgs:
                img.set_alpha(self.hovering_text_alpha)

        return sequence

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._last_mouse_move_time = VARS.ticks

        self.hovering_text_label.enter()

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        img: pg.Surface

        self._is_hovering = False
        self.hovering_text_alpha = 0
        for img in self.hovering_text_label.imgs:
            img.set_alpha(self.hovering_text_alpha)

        self.hovering_text_label.leave()

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY
        img: pg.Surface

        xy, self.rect.size = resize_obj(
            self.init_pos, *self.init_imgs[0].get_size(),
            win_w_ratio, win_h_ratio
        )

        self.imgs = [pg.transform.scale(img, self.rect.size).convert() for img in self.init_imgs]
        setattr(self.rect, self.init_pos.coord_type, xy)

        self.hovering_text_label.resize(win_w_ratio, win_h_ratio)
        for img in self.hovering_text_label.imgs:
            img.set_alpha(self.hovering_text_alpha)

    def move_rect(self, init_x: int, init_y: int, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Moves the rect to a specific coordinate.

        Args:
            initial x, initial y, window width ratio, window height ratio
        """

        xy: XY
        _wh: WH

        self.init_pos.x, self.init_pos.y = init_x, init_y  # Modifying init_pos is more accurate
        xy, _wh = resize_obj(self.init_pos, 0, 0, win_w_ratio, win_h_ratio)
        setattr(self.rect, self.init_pos.coord_type, xy)

    @abstractmethod
    def upt(self) -> bool:
        """
        Should implement a way to make the object interactable.

        Returns:
            flag related to clicking
        """


class Checkbox(_Clickable):
    """Class to create a checkbox with text on top."""

    __slots__ = (
        "is_checked",
    )

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], text: str | None, hovering_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox and text.

        Args:
            position, two images, text (can be None), hovering text,
            base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

        if text is not None:
            text_label: TextLabel = TextLabel(
                RectPos(self.rect.centerx, self.rect.y - 5, "midbottom"),
                text, base_layer, 16
            )

            self.objs_info.append(ObjInfo(text_label))

    def upt(self, is_shortcutting: bool = False) -> bool:
        """
        Changes the checkbox image when checked.

        Args:
            shortcutting flag (default = False)
        Returns:
            toggled flag
        """

        self._is_hovering = MOUSE.hovered_obj == self
        if MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y:
            self._last_mouse_move_time = VARS.ticks

        did_toggle: bool = (MOUSE.released[MOUSE_LEFT] and self._is_hovering) or is_shortcutting
        if did_toggle:
            self.is_checked = not self.is_checked
            self.img_i = int(self.is_checked)

        return did_toggle


class LockedCheckbox(_Clickable):
    """Class to create a checkbox that can't be unchecked."""

    __slots__ = (
        "is_checked",
    )

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], hovering_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox.

        Args:
            position, two images, hovering text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self.img_i = int(self.is_checked)

    def upt(self) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and checks it if clicked.

        Returns:
           checked flag
        """

        self._is_hovering = MOUSE.hovered_obj == self
        if MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y:
            self._last_mouse_move_time = VARS.ticks
        self.img_i = int(self._is_hovering or self.is_checked)

        return MOUSE.released[MOUSE_LEFT] and self._is_hovering


class Button(_Clickable):
    """Class to create a button, when hovered changes image."""

    __slots__ = (
        "text_label",
    )

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], text: str, hovering_text: str,
            base_layer: int = BG_LAYER, text_h: int = 25
    ) -> None:
        """
        Creates the button and text.

        Args:
            position, two images, text, hovering text,
            base layer (default = BG_LAYER), text height (default = 25)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.text_label: TextLabel = TextLabel(
            RectPos(self.rect.centerx, self.rect.centery, "center"),
            text, base_layer, text_h
        )

        self.objs_info.append(ObjInfo(self.text_label))

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self.img_i = 0

    def upt(self) -> bool:
        """
        Changes the button image if the mouse is hovering it and checks for clicks.

        Returns:
            clicked flag
        """

        self._is_hovering = MOUSE.hovered_obj == self
        if MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y:
            self._last_mouse_move_time = VARS.ticks
        self.img_i = int(self._is_hovering)

        return MOUSE.released[MOUSE_LEFT] and self._is_hovering


class SpammableButton(_Clickable):
    """Class to create a spammable button, when hovered changes image."""

    __slots__ = (
        "_hover_rect",
        "_click_interval", "_last_click_time", "_is_first_click",
    )

    def __init__(
            self, pos: RectPos, imgs: list[pg.Surface], hovering_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the button and text.

        Args:
            position, two images, hovering_text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self._hover_rect: pg.Rect = self.rect.copy()
        self.hover_rects = [self._hover_rect]

        self._click_interval: int  =  _INIT_CLICK_INTERVAL
        self._last_click_time: int = -_INIT_CLICK_INTERVAL
        self._is_first_click: bool = True

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self.img_i = 0
        self._is_first_click = True

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        hover_extra_left: int = self.rect.x - self._hover_rect.x
        hover_extra_right: int = self._hover_rect.right - self.rect.right
        hover_extra_top: int = self.rect.y - self._hover_rect.y
        hover_extra_bottom: int = self._hover_rect.bottom - self.rect.bottom
        super().resize(win_w_ratio, win_h_ratio)

        self._hover_rect.x = self.rect.x - hover_extra_left
        self._hover_rect.y = self.rect.y - hover_extra_top
        self._hover_rect.w = self.rect.w + (hover_extra_left + hover_extra_right)
        self._hover_rect.h = self.rect.h + (hover_extra_top  + hover_extra_bottom)

    def move_rect(self, init_x: int, init_y: int, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Moves the rect to a specific coordinate.

        Args:
            initial x, initial y, window width ratio, window height ratio
        """

        prev_x: int = self.rect.x
        prev_y: int = self.rect.y
        super().move_rect(init_x, init_y, win_w_ratio, win_h_ratio)

        self._hover_rect.x += self.rect.x - prev_x
        self._hover_rect.y += self.rect.y - prev_y

    def set_hover_extra_size(self, left: int, right: int, top: int, bottom: int) -> None:
        """
        Expands the hoverable area of the object.

        Args:
            extra left, extra right, extra top, extra bottom
        """

        self._hover_rect.x -= left
        self._hover_rect.y -= top
        self._hover_rect.w += left + right
        self._hover_rect.h += top  + bottom

    def _handle_click(self) -> bool:
        """
        Handles clicks, there's delay between the first and second clicks and then acceleration.

        Returns:
            clicked flag
        """

        is_clicked: bool = False
        if self._is_first_click:
            self._click_interval = _INIT_CLICK_INTERVAL
            self._last_click_time = VARS.ticks + 150  # Takes longer for second click
            self._is_first_click = False
            is_clicked = True
        elif VARS.ticks - self._last_click_time >= self._click_interval:
            self._click_interval = max(self._click_interval - 10, 10)
            self._last_click_time = VARS.ticks
            is_clicked = True

        return is_clicked

    def upt(self) -> bool:
        """
        Changes the button image if the mouse is hovering it and checks for timed clicks.

        Returns:
            clicked flag
        """

        self._is_hovering = MOUSE.hovered_obj == self
        if MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y:
            self._last_mouse_move_time = VARS.ticks
        self.img_i = int(self._is_hovering)

        is_clicked: bool = False
        if not MOUSE.pressed[MOUSE_LEFT]:
            self._is_first_click = True
        elif self._is_hovering:
            is_clicked = self._handle_click()

        return is_clicked
