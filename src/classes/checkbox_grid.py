"""Classes to create a locked checkbox or a grid of connected checkboxes."""

from collections.abc import Iterator
from typing import Optional, Any

import pygame as pg

from src.classes.clickable import Clickable

from src.utils import Point, RectPos, Size, Ratio, ObjInfo, MouseInfo, add_border
from src.type_utils import LayeredBlitInfo, LayeredBlitSequence
from src.consts import WHITE, BG_LAYER


class LockedCheckbox(Clickable):
    """Class to create a checkbox that can't be unchecked."""

    __slots__ = (
        'is_checked',
    )

    def __init__(
            self, pos: RectPos, imgs: tuple[pg.Surface, pg.Surface], hovering_text: str,
            base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates the checkbox.

        Args:
            position, two images, hovering text, base layer (default = BG_LAYER)
        """

        super().__init__(pos, imgs, hovering_text, base_layer)

        self.is_checked: bool = False

    def blit(self) -> LayeredBlitSequence:
        """
        Returns the objects to blit.

        Returns:
            sequence to add in the main blit sequence
        """

        img_i: int = 1 if self.is_checked else int(self._is_hovering)

        return self._base_blit(img_i)

    def set_info(self, imgs: tuple[pg.Surface, pg.Surface], text: str) -> None:
        """
        Sets the images and text.

        Args:
            two images, text
        """

        self._init_imgs = self._imgs = imgs
        if self._hovering_text_label:
            self._hovering_text_label.set_text(text)
            self._hovering_text_imgs = tuple(
                pg.Surface(rect.size) for rect in self._hovering_text_label.rects
            )

            hovering_text_info: Iterator[tuple[pg.Surface, LayeredBlitInfo]] = zip(
                self._hovering_text_imgs, self._hovering_text_label.blit()
            )
            for img, (text_img, _, _) in hovering_text_info:
                img.blit(text_img)

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo) -> bool:
        """
        Changes the checkbox image if the mouse is hovering it and checks it if clicked.

        Args:
            hovered object (can be None), mouse info
        Returns:
            True if the checkbox was checked else False
        """

        if self != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False
        else:
            if not self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
                self._is_hovering = True

            if mouse_info.released[0]:
                self.is_checked = True

        return mouse_info.released[0] if self._is_hovering else False


class CheckboxGrid:
    """Class to create a grid of checkboxes (images must be of the same size)."""

    __slots__ = (
        '_init_pos', '_last_point', '_cols', '_increment', '_layer', 'checkboxes', 'clicked_i',
        'rect', 'objs_info'
    )

    def __init__(
            self, pos: RectPos, checkboxes_info: tuple[tuple[pg.Surface, str], ...], cols: int,
            inverted_axes: tuple[bool, bool], base_layer: int = BG_LAYER
    ) -> None:
        """
        Creates all the checkboxes.

        Args:
            position, checkboxes images and texts, columns, inverted axes,
            base layer (default = BG_LAYER)
        """

        self._init_pos: RectPos = pos
        self._last_point: Point = Point(self._init_pos.x, self._init_pos.y)  # Isn't resized

        self._cols: int = cols
        self._increment: Size = Size(
            checkboxes_info[0][0].get_width() + 10, checkboxes_info[0][0].get_height() + 10
        )
        if inverted_axes[0]:
            self._increment.w = -self._increment.w
        if inverted_axes[1]:
            self._increment.h = -self._increment.h

        self._layer: int = base_layer

        self.checkboxes: list[LockedCheckbox] = []
        self.clicked_i: int = 0
        self.rect: pg.Rect = pg.Rect()

        self.objs_info: list[ObjInfo] = [ObjInfo(checkbox) for checkbox in self.checkboxes]

        self.set_grid(checkboxes_info, Ratio(1.0, 1.0))

    def check_hovering(self, mouse_xy: tuple[int, int]) -> tuple[Optional["CheckboxGrid"], int]:
        """
        Checks if the mouse is hovering any interactable part of the object.

        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object layer
        """

        return self if self.rect.collidepoint(mouse_xy) else None, self._layer

    def post_resize(self) -> None:
        """Gets the rect after the checkboxes were resized."""

        rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in self.checkboxes)
        left: int = min(rect.left for rect in rects)
        top: int = min(rect.top for rect in rects)
        w: int = max(rect.right for rect in rects) - left
        h: int = max(rect.bottom for rect in rects) - top
        self.rect = pg.Rect(left, top, w, h)

    def check(self, clicked_i: int) -> None:
        """
        Checks a specific checkbox and unchecks the previous one, changes clicked_i.

        Args:
            index of the active checkbox
        """

        if self.clicked_i < len(self.checkboxes):
            self.checkboxes[self.clicked_i].is_checked = False
        self.clicked_i = clicked_i
        self.checkboxes[self.clicked_i].is_checked = True

    def set_grid(
            self, checkboxes_info: tuple[tuple[pg.Surface, str], ...], win_ratio: Ratio
    ) -> None:
        """
        Clears the grid and creates a new one.

        Args:
            checkboxes images and texts, window size ratio
        """

        local_init_pos: RectPos = self._init_pos
        local_last_point: Point = self._last_point
        local_cols: int = self._cols
        local_increment: Size = self._increment
        local_layer: int = self._layer
        local_checkboxes: list[LockedCheckbox] = self.checkboxes

        local_last_point.x, local_last_point.y = local_init_pos.x, local_init_pos.y
        local_checkboxes.clear()
        for i, (img, hovering_text) in enumerate(checkboxes_info):
            checkbox: LockedCheckbox = LockedCheckbox(
                RectPos(local_last_point.x, local_last_point.y, local_init_pos.coord_type),
                (img, add_border(img, WHITE)), hovering_text, local_layer
            )
            checkbox.resize(win_ratio)
            local_checkboxes.append(checkbox)

            local_last_point.x += local_increment.w
            if (i + 1) % local_cols == 0:
                local_last_point.x = local_init_pos.x
                local_last_point.y += local_increment.h

        rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in local_checkboxes)
        left: int = min(rect.left for rect in rects)
        top: int = min(rect.top for rect in rects)
        w: int = max(rect.right for rect in rects) - left
        h: int = max(rect.bottom for rect in rects) - top
        self.rect = pg.Rect(left, top, w, h)

        self.objs_info = [ObjInfo(checkbox) for checkbox in local_checkboxes]

        self.check(0)

    def insert(
            self, insert_i: Optional[int], img: pg.Surface, hovering_text: str, win_ratio: Ratio
    ) -> None:
        """
        Inserts a checkbox at an index.

        Args:
            index (appends if None), checkbox image, checkbox text, window size ratio
        """

        if insert_i is not None:
            self.checkboxes[insert_i].set_info((img, add_border(img, WHITE)), hovering_text)
            self.checkboxes[insert_i].resize(win_ratio)
        else:
            checkbox: LockedCheckbox = LockedCheckbox(
                RectPos(self._last_point.x, self._last_point.y, self._init_pos.coord_type),
                (img, add_border(img, WHITE)), hovering_text, self._layer
            )
            checkbox.resize(win_ratio)
            self.checkboxes.append(checkbox)

            self._last_point.x += self._increment.w
            if len(self.checkboxes) % self._cols == 0:
                self._last_point.x = self._init_pos.x
                self._last_point.y += self._increment.h

        rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in self.checkboxes)
        left: int = min(rect.left for rect in rects)
        top: int = min(rect.top for rect in rects)
        w: int = max(rect.right for rect in rects) - left
        h: int = max(rect.bottom for rect in rects) - top
        self.rect = pg.Rect(left, top, w, h)

        self.objs_info = [ObjInfo(checkbox) for checkbox in self.checkboxes]

    def _move_to_last(self, move_i: int, win_ratio: Ratio) -> None:
        """
        Moves a checkbox to the right position after one was deleted.

        Args:
            index, window size ratio
        """

        change_x: int = 0
        change_y: int = 0
        checkbox_objs: list[Any] = [self.checkboxes[move_i]]

        is_first: bool = True
        while checkbox_objs:
            obj: Any = checkbox_objs.pop()
            if hasattr(obj, "move_rect"):
                if not is_first:
                    obj.move_rect(obj.init_pos.x + change_x, obj.init_pos.y + change_y, win_ratio)
                else:
                    prev_init_x: int = obj.init_pos.x
                    prev_init_y: int = obj.init_pos.y
                    obj.move_rect(self._last_point.x, self._last_point.y, win_ratio)

                    change_x, change_y = obj.init_pos.x - prev_init_x, obj.init_pos.y - prev_init_y
                    is_first = False

            if hasattr(obj, "objs_info"):
                checkbox_objs.extend(info.obj for info in obj.objs_info)

    def _get_grid_from_fallback(
            self, img: pg.Surface, hovering_text: str, win_ratio: Ratio
    ) -> None:
        """
        Makes the grid out of the fallback info if all checkboxes were removed.

        Args:
            checkbox image, checkbox text, window size ratio
        """

        checkbox = LockedCheckbox(
            RectPos(self._last_point.x, self._last_point.y, self._init_pos.coord_type),
            (img, add_border(img, WHITE)), hovering_text, self._layer
        )
        checkbox.resize(win_ratio)
        self.checkboxes = [checkbox]

        if self._cols == 1:
            self._last_point.x = self._init_pos.x
            self._last_point.y = self._init_pos.y + self._increment.h
        else:
            self._last_point.x = self._init_pos.x + self._increment.w
            self._last_point.y = self._init_pos.y

    def remove(
            self, remove_i: int, fallback_info: tuple[pg.Surface, str], win_ratio: Ratio
    ) -> None:
        """
        Removes a checkbox at an index.

        Args:
            index, fallback image and text, window size ratio
        """

        local_init_pos: RectPos = self._init_pos
        local_last_point: Point = self._last_point
        local_cols: int = self._cols
        local_increment: Size = self._increment

        checkbox: LockedCheckbox = self.checkboxes.pop(remove_i)
        # last_point becomes the removed checkbox position
        local_last_point.x = round(
            getattr(checkbox.rect, local_init_pos.coord_type)[0] / win_ratio.w
        )
        local_last_point.y = round(
            getattr(checkbox.rect, local_init_pos.coord_type)[1] / win_ratio.h
        )

        for i in range(remove_i, len(self.checkboxes)):
            self._move_to_last(i, win_ratio)
            local_last_point.x += local_increment.w
            if (i + 1) % local_cols == 0:
                local_last_point.x = local_init_pos.x
                local_last_point.y += local_increment.h

        if not self.checkboxes:
            self._get_grid_from_fallback(*fallback_info, win_ratio)

        if self.clicked_i > remove_i:
            self.check(self.clicked_i - 1)
        elif self.clicked_i == remove_i:
            self.clicked_i = min(self.clicked_i, len(self.checkboxes) - 1)
            self.checkboxes[self.clicked_i].is_checked = True

        rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in self.checkboxes)
        left: int = min(rect.left for rect in rects)
        top: int = min(rect.top for rect in rects)
        w: int = max(rect.right for rect in rects) - left
        h: int = max(rect.bottom for rect in rects) - top
        self.rect = pg.Rect(left, top, w, h)

        self.objs_info = [ObjInfo(checkbox) for checkbox in self.checkboxes]

    def _move_with_keys(self, keys: list[int]) -> int:
        """
        Moves the selected checkbox with keys.

        Args:
            keys
        Returns:
            index of the active checkbox
        """

        local_clicked_i: int = self.clicked_i

        k_sub_1: int = pg.K_LEFT
        k_add_1: int = pg.K_RIGHT
        k_sub_cols: int = pg.K_UP
        k_add_cols: int = pg.K_DOWN
        if self._increment.w < 0:
            k_sub_1, k_add_1 = k_add_1, k_sub_1
        if self._increment.h < 0:
            k_sub_cols, k_add_cols = k_add_cols, k_sub_cols

        if k_sub_1 in keys:
            local_clicked_i = max(local_clicked_i - 1, 0)
        if k_add_1 in keys:
            local_clicked_i = min(local_clicked_i + 1, len(self.checkboxes) - 1)
        if k_sub_cols in keys and (local_clicked_i - self._cols >= 0):
            local_clicked_i -= self._cols
        if k_add_cols in keys and (local_clicked_i + self._cols <= len(self.checkboxes) - 1):
            local_clicked_i += self._cols

        return local_clicked_i

    def upt(self, hovered_obj: Any, mouse_info: MouseInfo, keys: list[int]) -> int:
        """
        Allows checking only one checkbox at a time.

        Args:
            hovered object (can be None), mouse info, keys
        Returns
            index of the active checkbox
        """

        if (self == hovered_obj or hovered_obj in self.checkboxes) and keys:
            future_clicked_i: int = self._move_with_keys(keys)
            if self.clicked_i != future_clicked_i:
                self.check(future_clicked_i)

        for i, checkbox in enumerate(self.checkboxes):
            if checkbox.upt(hovered_obj, mouse_info):
                self.check(i)

        return self.clicked_i
