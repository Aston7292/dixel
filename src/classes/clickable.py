"""Classes to create various clickable objects."""

from abc import ABC, abstractmethod
from math import ceil
from typing import Self, Final

from pygame import Surface, Rect, transform, SYSTEM_CURSOR_HAND

from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE

import src.obj_utils as objs
import src.vars as my_vars
from src.obj_utils import ObjInfo, resize_obj, rec_move_rect
from src.type_utils import XY, WH, CoordType, BlitInfo, RectPos
from src.consts import (
    BLACK,
    MOUSE_LEFT,
    BG_LAYER, ELEMENT_LAYER, TEXT_LAYER, TOP_LAYER,
    ANIMATION_GROW, ANIMATION_SHRINK,
)
from src.win import WIN_SURF

_INIT_CLICK_INTERVAL: Final[int] = 128


class _Clickable(ABC):
    """Abstract class to create a clickable object with various images and hovering text."""

    __slots__ = (
        "init_pos", "_scale", "init_imgs", "_imgs", "rect", "_frame_rect",
        "_last_mouse_move_time",
        "hovering_text_label", "_hovering_text_label_obj_info",
        "hover_rects", "layer", "blit_sequence", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_HAND

    def __init__(
            self: Self, pos: RectPos, imgs: tuple[Surface, ...], hovering_text: str,
            base_layer: int
    ) -> None:
        """
        Creates the object and hovering text.

        Args:
            position, images, hovering text, base layer
        """

        self.init_pos: RectPos = pos
        self._scale: float = 1

        self.init_imgs: tuple[Surface, ...] = imgs  # Better for scaling
        self._imgs: list[Surface] = list(self.init_imgs)
        self.rect: Rect = Rect(0, 0, *self._imgs[0].get_size())
        setattr(self.rect, self.init_pos.coord_type, (self.init_pos.x, self.init_pos.y))
        self._frame_rect: Rect = self.rect.copy()
        self._frame_rect.center = self.rect.center

        self._last_mouse_move_time: int = my_vars.ticks

        # Better if it's not in objs_info, activating a drop-down menu will activate it too
        self.hovering_text_label: TextLabel = TextLabel(
            RectPos(MOUSE.x, MOUSE.y, "topleft"),
            hovering_text, base_layer + TOP_LAYER - TEXT_LAYER,
            h=12, bg_color=BLACK
        )
        self._hovering_text_label_obj_info: ObjInfo = ObjInfo(
            self.hovering_text_label, should_follow_parent=False
        )
        self._hovering_text_label_obj_info.rec_set_active(False)

        self.hover_rects: tuple[Rect, ...] = (self.rect,)
        self.layer: int = base_layer + ELEMENT_LAYER
        self.blit_sequence: list[BlitInfo] = [(self._imgs[0], self._frame_rect, self.layer)]
        self.objs_info: tuple[ObjInfo, ...] = (self._hovering_text_label_obj_info,)

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._last_mouse_move_time = my_vars.ticks

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._hovering_text_label_obj_info.rec_set_active(False)
        # blit_sequence is refreshed by subclasses

    def resize(self: Self) -> None:
        """Resizes the object."""

        xy: XY

        xy, self.rect.size = resize_obj(self.init_pos, *self.init_imgs[0].get_size())
        self._frame_rect.size = (
            ceil(self.init_imgs[0].get_width()  * self._scale * my_vars.win_w_ratio),
            ceil(self.init_imgs[0].get_height() * self._scale * my_vars.win_h_ratio),
        )
        self.set_unscaled_imgs(self.init_imgs)
        setattr(self.rect, self.init_pos.coord_type, xy)
        self._frame_rect.center = self.rect.center

    def move_rect(self: Self, init_x: int, init_y: int, should_scale: bool) -> None:
        """
        Moves the rect to a specific coordinate.

        Args:
            initial x, initial y, scale flag
        """

        xy: XY

        self.init_pos.x, self.init_pos.y = init_x, init_y  # More accurate

        if should_scale:
            xy = (
                round(self.init_pos.x * my_vars.win_w_ratio),
                round(self.init_pos.y * my_vars.win_h_ratio),
            )
        else:
            xy = (self.init_pos.x, self.init_pos.y)
        setattr(self.rect, self.init_pos.coord_type, xy)
        self._frame_rect.center = self.rect.center

    def set_unscaled_imgs(self: Self, imgs: tuple[Surface, ...]) -> None:
        """
        Modifies the images, scales them and refreshes the blit sequence.

        Args:
            images
        """

        img_i: int = self._imgs.index(self.blit_sequence[0][0])
        self._imgs = [
            transform.scale(img, self._frame_rect.size).convert()
            for img in imgs
        ]
        self.blit_sequence[0] = (self._imgs[img_i], self._frame_rect, self.layer)

    def _handle_hovering_text_label_pos(self: Self) -> XY:
        """
        Gets the position of the hovering text label and changes the coord type if it overflows.

        Returns:
            hovering text label x, hovering text label y
        """

        prev_coord_type: CoordType = self.hovering_text_label.init_pos.coord_type

        x: int = MOUSE.x + 8
        y: int = MOUSE.y
        is_overflowing_x: bool = x + self.hovering_text_label.rect.w > WIN_SURF.get_width()
        is_overflowing_y: bool = y + self.hovering_text_label.rect.h > WIN_SURF.get_height()
        if is_overflowing_x and is_overflowing_y:
            x = MOUSE.x
            self.hovering_text_label.init_pos.coord_type = "bottomright"
        elif is_overflowing_x:
            x = MOUSE.x
            self.hovering_text_label.init_pos.coord_type = "topright"
        elif is_overflowing_y:
            self.hovering_text_label.init_pos.coord_type = "bottomleft"
        else:
            self.hovering_text_label.init_pos.coord_type = "topleft"

        if self.hovering_text_label.init_pos.coord_type != prev_coord_type:
            rect_xy: XY = getattr(
                self.hovering_text_label.rect, self.hovering_text_label.init_pos.coord_type
            )
            self.hovering_text_label.refresh_rects(rect_xy)

        return x, y

    def _refresh(self: Self, img_i: int, is_hovering: bool = False) -> None:
        """
        Refreshes the last mouse move time and blit sequence.

        Args:
            image index, hovering flag
        """

        x: int
        y: int

        if not is_hovering or (MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y):
            self._last_mouse_move_time = my_vars.ticks
            self._hovering_text_label_obj_info.rec_set_active(False)

        self.blit_sequence = [(self._imgs[img_i], self._frame_rect, self.layer)]
        if is_hovering and (my_vars.ticks - self._last_mouse_move_time >= 750):
            x, y = self._handle_hovering_text_label_pos()
            rec_move_rect(self.hovering_text_label, x, y, should_scale=False)

            if not self._hovering_text_label_obj_info.is_active:
                self.hovering_text_label.start_animation()
                self._hovering_text_label_obj_info.rec_set_active(True)


    @abstractmethod
    def upt(self: Self) -> bool:
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
            self: Self, pos: RectPos, imgs: tuple[Surface, ...],
            text: str | None, hovering_text: str, base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox and text.

        Args:
            position, two images, text (can be None), hovering text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

        if text is not None:
            text_label: TextLabel = TextLabel(
                RectPos(self.rect.centerx, self.rect.y - 4, "midbottom"),
                text, base_layer, h=16
            )

            self.objs_info += (ObjInfo(text_label),)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self._refresh(int(self.is_checked))

    def set_checked(self: Self, is_checked: bool) -> None:
        """
        Sets the checked flag and refreshes the blit sequence.

        Args:
            checked flag
        """

        self.is_checked = is_checked
        self._refresh(int(self.is_checked), MOUSE.hovered_obj == self)

    def upt(self: Self, is_shortcutting: bool = False) -> bool:
        """
        Changes the checkbox image when checked.

        Args:
            shortcutting flag (default = False)
        Returns:
            toggled flag
        """

        is_hovering: bool = MOUSE.hovered_obj == self
        did_toggle: bool = (MOUSE.released[MOUSE_LEFT] and is_hovering) or is_shortcutting
        if did_toggle:
            self.is_checked = not self.is_checked

        self._refresh(int(self.is_checked), is_hovering)

        return did_toggle


class LockedCheckbox(_Clickable):
    """Class to create a checkbox that can't be unchecked."""

    __slots__ = (
        "is_checked",
    )

    def __init__(
            self: Self, pos: RectPos, imgs: tuple[Surface, ...], hovering_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox.

        Args:
            position, two images, hovering text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self._refresh(int(self.is_checked))

    def set_checked(self: Self, is_checked: bool) -> None:
        """
        Sets the checked flag and refreshes the blit sequence.

        Args:
            checked flag
        """

        self.is_checked = is_checked
        is_hovering: bool = MOUSE.hovered_obj == self
        self._refresh(int(is_hovering or self.is_checked), MOUSE.hovered_obj == self)

    def upt(self: Self) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and checks it if clicked.

        Returns:
           checked flag
        """

        is_hovering: bool = MOUSE.hovered_obj == self
        self._refresh(int(is_hovering or self.is_checked), is_hovering)

        return MOUSE.released[MOUSE_LEFT] and is_hovering


class Button(_Clickable):
    """Class to create a button, when hovered changes image."""

    __slots__ = (
        "_min_scale", "_max_scale", "_animation_i", "_should_animate",
        "text_label",
    )

    def __init__(
            self: Self, pos: RectPos, imgs: tuple[Surface, ...],
            text: str | None, hovering_text: str,
            base_layer: int = BG_LAYER,
            should_animate: bool = True, text_h: int = 25
    ) -> None:
        """
        Creates the button and text.

        Args:
            position, two images, text (can be None), hovering text,
            base layer (default = BG_LAYER),
            animate flag (default = True), text height (default = 25)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self._min_scale: float = 1
        self._max_scale: float = 1.15
        self._animation_i: int = ANIMATION_GROW
        self._should_animate: bool = should_animate

        self.text_label: TextLabel | None = None
        if text is not None:
            self.text_label = TextLabel(
                RectPos(self.rect.centerx, self.rect.centery, "center"),
                text, base_layer, text_h
            )

            self.objs_info += (ObjInfo(self.text_label),)

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self._refresh(0)

    def set_hovering(self: Self, is_hovering: bool) -> None:
        """
        Sets the hovering flag and refreshes the blit sequence.

        Args:
            hovering flag
        """

        self._refresh(int(is_hovering), is_hovering)

    def upt(self: Self) -> bool:
        """
        Changes the button image if the mouse is hovering it and checks for clicks.

        Returns:
            clicked flag
        """

        is_hovering: bool = MOUSE.hovered_obj == self
        if MOUSE.pressed[MOUSE_LEFT] and is_hovering and self._should_animate:
            self._animation_i = ANIMATION_SHRINK
            self._min_scale = 0.9
            objs.animating_objs.add(self)
        self._refresh(int(is_hovering), is_hovering)

        return MOUSE.released[MOUSE_LEFT] and is_hovering

    def animate(self: Self, dt: float) -> None:
        """
        Plays a frame of the active animation.

        Args:
            delta time
        """

        prev_scale: float = self._scale

        # The animation is fast at the start and slow at the end
        if self._animation_i == ANIMATION_GROW:
            grow_progress: float = (self._max_scale - self._scale) / self._max_scale
            self._scale += grow_progress * 0.5 * dt
            if self._max_scale - self._scale <= 0.01:
                self._scale = self._max_scale
                self._animation_i = ANIMATION_SHRINK
                self._min_scale = 1
        elif self._animation_i == ANIMATION_SHRINK:
            shrink_progress: float = (self._scale - self._min_scale) / self._max_scale
            self._scale -= shrink_progress * 0.25 * dt
            if self._scale - self._min_scale <= 0.01:
                self._scale = self._min_scale
                if self._min_scale == 1:
                    objs.animating_objs.remove(self)
                else:
                    self._animation_i = ANIMATION_GROW

        if self._scale != prev_scale:
            w: int = ceil(self.init_imgs[0].get_width()  * self._scale * my_vars.win_w_ratio)
            h: int = ceil(self.init_imgs[0].get_height() * self._scale * my_vars.win_h_ratio)

            self._frame_rect.size = (w, h)
            self._frame_rect.center = self.rect.center
            self.set_unscaled_imgs(self.init_imgs)



class SpammableButton(_Clickable):
    """Class to create a spammable button, when hovered changes image."""

    __slots__ = (
        "_click_interval", "_last_click_time", "_is_first_click",
        "_min_scale", "_max_scale", "_animation_i",
        "_hover_extra_x", "_hover_extra_y", "_hover_extra_w", "_hover_extra_h",
    )

    def __init__(
            self: Self, pos: RectPos, imgs: tuple[Surface, ...], hovering_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the button and text.

        Args:
            position, two images, hovering_text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self._click_interval: int = _INIT_CLICK_INTERVAL
        self._last_click_time: int = -_INIT_CLICK_INTERVAL
        self._is_first_click: bool = True

        self._min_scale: float = 1
        self._max_scale: float = 1.15
        self._animation_i: int = ANIMATION_GROW

        self._hover_extra_x: int = 0
        self._hover_extra_y: int = 0
        self._hover_extra_w: int = 0
        self._hover_extra_h: int = 0

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self._is_first_click = True

        self._refresh(0)

    def resize(self: Self) -> None:
        """Resizes the object."""

        super().resize()  # There's no need to restore rect

        self.rect.x -= self._hover_extra_x
        self.rect.y -= self._hover_extra_y
        self.rect.w += self._hover_extra_w
        self.rect.h += self._hover_extra_h

    def move_rect(self: Self, init_x: int, init_y: int, should_scale: bool) -> None:
        """
        Moves the rect to a specific coordinate.

        Args:
            initial x, initial y, scale flag
        """

        self.rect.x += self._hover_extra_x
        self.rect.y += self._hover_extra_y

        super().move_rect(init_x, init_y, should_scale)

        self.rect.x -= self._hover_extra_x
        self.rect.y -= self._hover_extra_y

    def set_hover_extra_size(self: Self, left: int, right: int, top: int, bottom: int) -> None:
        """
        Expands the hoverable area of the object.

        Args:
            extra left, extra right, extra top, extra bottom
        """

        self._hover_extra_x = left
        self._hover_extra_y = top
        self._hover_extra_w = self._hover_extra_x + right
        self._hover_extra_h = self._hover_extra_y + bottom

        self.rect.x -= self._hover_extra_x
        self.rect.y -= self._hover_extra_y
        self.rect.w += self._hover_extra_w
        self.rect.h += self._hover_extra_h

    def _handle_click(self: Self) -> bool:
        """
        Handles clicking, there's delay between the first and other clicks and then acceleration.

        Returns:
            clicked flag
        """

        is_clicked: bool = False
        if self._is_first_click:
            self._click_interval = _INIT_CLICK_INTERVAL
            self._last_click_time = my_vars.ticks + 128  # Takes longer for second click
            self._is_first_click = False
            is_clicked = True
        elif my_vars.ticks - self._last_click_time >= self._click_interval:
            self._click_interval = max(self._click_interval - 10, 16)
            self._last_click_time = my_vars.ticks
            is_clicked = True

        return is_clicked

    def upt(self: Self) -> bool:
        """
        Changes the button image if the mouse is hovering it and checks for timed clicks.

        Returns:
            clicked flag
        """

        is_hovering: bool = MOUSE.hovered_obj == self
        is_clicked: bool = False
        if MOUSE.pressed[MOUSE_LEFT] and is_hovering:
            is_clicked = self._handle_click()
            self._animation_i = ANIMATION_SHRINK
            self._min_scale = 0.9
            objs.animating_objs.add(self)
        else:
            self._is_first_click = True

        self._refresh(int(is_hovering), is_hovering)

        return is_clicked

    def animate(self: Self, dt: float) -> None:
        """
        Plays a frame of the active animation.

        Args:
            delta time
        """

        prev_scale: float = self._scale

        if self._animation_i == ANIMATION_GROW:
            grow_progress: float = (self._max_scale - self._scale) / self._max_scale
            self._scale += grow_progress * 0.5 * dt
            if self._max_scale - self._scale <= 0.01:
                self._scale = self._max_scale
                self._animation_i = ANIMATION_SHRINK
                self._min_scale = 1
        elif self._animation_i == ANIMATION_SHRINK:
            shrink_progress: float = (self._scale - self._min_scale) / self._min_scale
            self._scale -= shrink_progress * 0.25 * dt
            if self._scale - self._min_scale <= 0.01:
                self._scale = self._min_scale
                if self._min_scale == 1:
                    objs.animating_objs.remove(self)
                else:
                    self._animation_i = ANIMATION_GROW

        # The animation is fast at the start and slow at the end
        if self._scale != prev_scale:
            w: int = ceil(self.init_imgs[0].get_width()  * self._scale * my_vars.win_w_ratio)
            h: int = ceil(self.init_imgs[0].get_height() * self._scale * my_vars.win_h_ratio)

            self.rect.x += self._hover_extra_x
            self.rect.y += self._hover_extra_y
            self.rect.w -= self._hover_extra_w
            self.rect.h -= self._hover_extra_h

            self._frame_rect.size = (w, h)
            self._frame_rect.center = self.rect.center
            self.set_unscaled_imgs(self.init_imgs)

            self.rect.x -= self._hover_extra_x
            self.rect.y -= self._hover_extra_y
            self.rect.w += self._hover_extra_w
            self.rect.h += self._hover_extra_h