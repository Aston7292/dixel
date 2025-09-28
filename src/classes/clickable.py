"""Classes to create various clickable objects."""

from abc import ABC, abstractmethod
from typing import Self, Final

from pygame import Surface, Rect, transform, SYSTEM_CURSOR_HAND

from src.classes.text_label import TextLabel
from src.classes.devices import MOUSE

from src.obj_utils import ObjInfo, resize_obj, rec_move_rect
from src.type_utils import XY, WH, BlitInfo, RectPos
import src.vars as my_vars
from src.consts import MOUSE_LEFT, BLACK, BG_LAYER, ELEMENT_LAYER, TEXT_LAYER, TOP_LAYER

_INIT_CLICK_INTERVAL: Final[int] = 128


class _Clickable(ABC):
    """
    Abstract class to create a clickable object with various images and hovering text.

    Includes:
        hover_rects
        layer
        cursor_type
        blit_sequence
        objs_info

        _refresh(image index) -> None
        enter() -> None
        leave() -> None
        resize(window width ratio, window height ratio) -> None
        move_rect(x, y, window width ratio, window height ratio) -> None
        set_imgs(images) -> None

    Children should include:
        upt(extra info) -> bool
    """

    __slots__ = (
        "init_pos", "init_imgs", "_imgs", "rect",
        "_is_hovering",
        "hovering_text_label", "_hovering_text_alpha", "_last_mouse_move_time",
        "hover_rects", "layer", "blit_sequence", "objs_info",
    )

    cursor_type: int = SYSTEM_CURSOR_HAND

    def __init__(
            self: Self, pos: RectPos, imgs: list[Surface], hovering_text: str,
            base_layer: int
    ) -> None:
        """
        Creates the object and hovering text.

        Args:
            position, images, hovering text, base layer
        """

        img: Surface

        self.init_pos: RectPos = pos

        self.init_imgs: list[Surface] = imgs  # Better for scaling
        self._imgs: list[Surface] = self.init_imgs
        self.rect: Rect = Rect(0, 0, *self._imgs[0].get_size())
        setattr(self.rect, self.init_pos.coord_type, (self.init_pos.x, self.init_pos.y))

        self._is_hovering: bool = False

        # Better if it's not in objs_info, activating a drop-down menu will activate it too
        self.hovering_text_label: TextLabel = TextLabel(
            RectPos(MOUSE.x, MOUSE.y, "topleft"),
            hovering_text, base_layer + TOP_LAYER - TEXT_LAYER,
            h=12, bg_color=BLACK
        )
        self._hovering_text_alpha: int = 0
        self._last_mouse_move_time: int = my_vars.ticks

        self.hover_rects: tuple[Rect, ...] = (self.rect,)
        self.layer: int = base_layer + ELEMENT_LAYER
        self.blit_sequence: list[BlitInfo] = [(self._imgs[0], self.rect, self.layer)]
        self.objs_info: list[ObjInfo] = []

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._last_mouse_move_time = my_vars.ticks

        self.hovering_text_label.enter()

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        self._is_hovering = False
        self._hovering_text_alpha = 0
        self.hovering_text_label.leave()
        # blit_sequence is refreshed by subclasses

    def resize(self: Self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY

        xy, self.rect.size = resize_obj(
            self.init_pos, *self.init_imgs[0].get_size(),
            win_w_ratio, win_h_ratio
        )

        self.set_imgs([
            transform.scale(img, self.rect.size).convert()
            for img in self.init_imgs
        ])
        setattr(self.rect, self.init_pos.coord_type, xy)

        self.hovering_text_label.resize(win_w_ratio, win_h_ratio)

    def move_rect(
            self: Self, init_x: int, init_y: int,
            win_w_ratio: float, win_h_ratio: float
    ) -> None:
        """
        Moves the rect to a specific coordinate.

        Args:
            initial x, initial y, window width ratio, window height ratio
        """

        xy: XY
        _wh: WH

        self.init_pos.x, self.init_pos.y = init_x, init_y  # More accurate
        xy, _wh = resize_obj(
            self.init_pos, init_w=0, init_h=0,
            win_w_ratio=win_w_ratio, win_h_ratio=win_h_ratio
        )
        setattr(self.rect, self.init_pos.coord_type, xy)

    def set_imgs(self: Self, imgs: list[Surface]) -> None:
        """
        Modifies the images and refreshes the blit sequence.

        Args:
            images
        """

        img_i: int = self._imgs.index(self.blit_sequence[0][0])
        self._imgs = imgs
        self.blit_sequence[0] = (self._imgs[img_i], self.rect, self.layer)


    def _refresh(self: Self, img_i: int) -> None:
        """
        Refreshes the last mouse move time and blit sequence.

        Args:
            image index
        """

        img: Surface

        if not self._is_hovering or (MOUSE.x != MOUSE.prev_x or MOUSE.y != MOUSE.prev_y):
            self._hovering_text_alpha = 0
            self._last_mouse_move_time = my_vars.ticks

        self.blit_sequence = [(self._imgs[img_i], self.rect, self.layer)]
        if self._is_hovering and (my_vars.ticks - self._last_mouse_move_time >= 750):
            rec_move_rect(
                self.hovering_text_label, MOUSE.x + 10, MOUSE.y,
                win_w_ratio=1, win_h_ratio=1
            )

            if self._hovering_text_alpha != 255:
                self._hovering_text_alpha = round(self._hovering_text_alpha + (8 * my_vars.dt))
                self._hovering_text_alpha = min(self._hovering_text_alpha, 255)
                for img in self.hovering_text_label.imgs:
                    img.set_alpha(self._hovering_text_alpha)

            self.blit_sequence.extend(self.hovering_text_label.blit_sequence)

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
            self: Self, pos: RectPos, imgs: list[Surface], text: str | None, hovering_text: str,
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
                RectPos(self.rect.centerx, self.rect.y - 4, "midbottom"),
                text, base_layer, h=16
            )

            self.objs_info.append(ObjInfo(text_label))

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
        self._refresh(int(self.is_checked))

    def upt(self: Self, is_shortcutting: bool = False) -> bool:
        """
        Changes the checkbox image when checked.

        Args:
            shortcutting flag (default = False)
        Returns:
            toggled flag
        """

        self._is_hovering = MOUSE.hovered_obj == self
        did_toggle: bool = (MOUSE.released[MOUSE_LEFT] and self._is_hovering) or is_shortcutting
        if did_toggle:
            self.is_checked = not self.is_checked

        self._refresh(int(self.is_checked))

        return did_toggle


class LockedCheckbox(_Clickable):
    """Class to create a checkbox that can't be unchecked."""

    __slots__ = (
        "is_checked",
    )

    def __init__(
            self: Self, pos: RectPos, imgs: list[Surface], hovering_text: str,
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
        self._refresh(int(self._is_hovering or self.is_checked))

    def upt(self: Self) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and checks it if clicked.

        Returns:
           checked flag
        """

        self._is_hovering = MOUSE.hovered_obj == self
        self._refresh(int(self._is_hovering or self.is_checked))

        return MOUSE.released[MOUSE_LEFT] and self._is_hovering


class Button(_Clickable):
    """Class to create a button, when hovered changes image."""

    __slots__ = (
        "text_label",
    )

    def __init__(
            self: Self, pos: RectPos, imgs: list[Surface], text: str | None, hovering_text: str,
            base_layer: int = BG_LAYER, text_h: int = 25
    ) -> None:
        """
        Creates the button and text.

        Args:
            position, two images, text (can be None), hovering text,
            base layer (default = BG_LAYER), text height (default = 25)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.text_label: TextLabel | None = None

        if text is not None:
            self.text_label = TextLabel(
                RectPos(self.rect.centerx, self.rect.centery, "center"),
                text, base_layer, text_h
            )

            self.objs_info.append(ObjInfo(self.text_label))

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

        self._is_hovering = is_hovering
        self._refresh(int(self._is_hovering))

    def upt(self: Self) -> bool:
        """
        Changes the button image if the mouse is hovering it and checks for clicks.

        Returns:
            clicked flag
        """

        self._is_hovering = MOUSE.hovered_obj == self
        self._refresh(int(self._is_hovering))

        return MOUSE.released[MOUSE_LEFT] and self._is_hovering


class SpammableButton(_Clickable):
    """Class to create a spammable button, when hovered changes image."""

    __slots__ = (
        "_hover_rect",
        "_click_interval", "_last_click_time", "_is_first_click",
    )

    def __init__(
            self: Self, pos: RectPos, imgs: list[Surface], hovering_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the button and text.

        Args:
            position, two images, hovering_text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self._hover_rect: Rect = self.rect.copy()
        self.hover_rects = (self._hover_rect,)

        self._click_interval: int = _INIT_CLICK_INTERVAL
        self._last_click_time: int = -_INIT_CLICK_INTERVAL
        self._is_first_click: bool = True

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

        super().leave()
        self._is_first_click = True
        self._refresh(0)

    def resize(self: Self, win_w_ratio: float, win_h_ratio: float) -> None:
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

        self._hover_rect.topleft = (
            self.rect.x - hover_extra_left,
            self.rect.y - hover_extra_top,
        )
        self._hover_rect.size = (
            self.rect.w + (hover_extra_left + hover_extra_right),
            self.rect.h + (hover_extra_top  + hover_extra_bottom),
        )

    def move_rect(
            self: Self, init_x: int, init_y: int,
            win_w_ratio: float, win_h_ratio: float
    ) -> None:
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

    def set_hover_extra_size(self: Self, left: int, right: int, top: int, bottom: int) -> None:
        """
        Expands the hoverable area of the object.

        Args:
            extra left, extra right, extra top, extra bottom
        """

        self._hover_rect.x -= left
        self._hover_rect.y -= top
        self._hover_rect.w += left + right
        self._hover_rect.h += top  + bottom

    def _handle_click(self: Self) -> bool:
        """
        Handles clicks, there's delay between the first and second clicks and then acceleration.

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

        self._is_hovering = MOUSE.hovered_obj == self
        is_clicked: bool = False
        if not MOUSE.pressed[MOUSE_LEFT]:
            self._is_first_click = True
        elif self._is_hovering:
            is_clicked = self._handle_click()

        self._refresh(int(self._is_hovering))

        return is_clicked
