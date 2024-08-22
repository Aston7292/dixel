"""
class to choose a number in range with an input box
"""

import pygame as pg
from typing import Tuple, List

from src.classes.text import Text
from src.utils import MouseInfo, RectPos, Size
from src.const import WHITE, BlitSequence


class NumInputBox:
    """
    class to choose a number in range with an input box
    """

    __slots__ = (
        '_box_init_pos', '_box_img', 'box_rect', '_box_init_size', 'hovering', 'selected',
        'text', 'text_i', '_cursor_img', '_cursor_rect', '_cursor_init_size'
    )

    def __init__(self, pos: RectPos, img: pg.SurfaceType, text: str):
        """
        creates surfaces, rects and text object
        takes position, image and text
        """

        self._box_init_pos: RectPos = pos

        self._box_img: pg.SurfaceType = img
        self.box_rect: pg.FRect = self._box_img.get_frect(
            **{pos.pos: pos.xy}
        )

        self._box_init_size: Size = Size(int(self.box_rect.w), int(self.box_rect.h))

        self.hovering: bool = False
        self.selected: bool = False

        self.text = Text(RectPos(*self.box_rect.center, 'center'), text)
        self.text_i: int = 0

        self._cursor_img: pg.SurfaceType = pg.Surface((1, self.text.rect.h))
        self._cursor_img.fill(WHITE)
        self._cursor_rect: pg.FRect = self._cursor_img.get_frect(
            topleft=(self.text.get_pos_at(self.text_i), self.text.rect.y)
        )

        self._cursor_init_size: Size = Size(int(self._cursor_rect.w), int(self._cursor_rect.h))

    def blit(self) -> BlitSequence:
        """
        returns a sequence to add in the main blit sequence
        """

        sequence: BlitSequence = [(self._box_img, self.box_rect.topleft)]
        sequence += self.text.blit()
        if self.selected:
            sequence += [(self._cursor_img, self._cursor_rect.topleft)]

        return sequence

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        resizes objects
        takes window size ratio
        """

        box_size: Tuple[int, int] = (
            int(self._box_init_size.w * win_ratio_w), int(self._box_init_size.h * win_ratio_h)
        )
        box_pos: Tuple[float, float] = (
            self._box_init_pos.x * win_ratio_w, self._box_init_pos.y * win_ratio_h
        )

        self._box_img = pg.transform.scale(self._box_img, box_size)
        self.box_rect = self._box_img.get_frect(**{self._box_init_pos.pos: box_pos})

        self.text.handle_resize(win_ratio_w, win_ratio_h)

        cursor_size: Tuple[int, int] = (
            int(self._cursor_init_size.w * win_ratio_w),
            int(self._cursor_init_size.h * win_ratio_h)
        )

        self._cursor_img = pg.transform.scale(self._cursor_img, cursor_size)
        self.get_cursor_pos()

    def get_cursor_pos(self) -> None:
        """
        calculates cursor position based on text index
        """

        self._cursor_rect.x = self.text.get_pos_at(self.text_i)
        self._cursor_rect.y = self.text.rect.y

    def upt(
            self, mouse_info: MouseInfo, keys: List[int], limits: Tuple[int, int], selected: bool
    ) -> Tuple[bool, str]:
        """
        makes the object interactable
        takes mouse info, keys, limits and selected bool
        returns whatever the input box was clicked or not and the new text
        """

        new_text: str = self.text.text

        if not self.box_rect.collidepoint(mouse_info.xy):
            if self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self.hovering = False
        else:
            if not self.hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_IBEAM)
                self.hovering = True

            if mouse_info.released[0]:
                self.text_i = self.text.get_closest(mouse_info.x)
                self.get_cursor_pos()

                return True, new_text

        self.selected = selected
        if self.selected and keys:
            if pg.K_LEFT in keys:
                self.text_i = max(self.text_i - 1, 0)
            elif pg.K_RIGHT in keys:
                self.text_i = min(self.text_i + 1, len(self.text.text))
            elif pg.K_HOME in keys:
                self.text_i = 0
            elif pg.K_END in keys:
                self.text_i = len(self.text.text)
            else:
                k: int = keys[-1]
                if k == pg.K_BACKSPACE and self.text_i:
                    new_text = self.text.text[:self.text_i - 1] + self.text.text[self.text_i:]
                    self.text_i = max(self.text_i - 1, 0)
                elif k == pg.K_DELETE:
                    new_text = self.text.text[:self.text_i] + self.text.text[self.text_i + 1:]
                elif k <= 0x10ffff and chr(k).isdigit():
                    new_text = self.text.text[:self.text_i] + chr(k) + self.text.text[self.text_i:]
                    self.text_i = min(self.text_i + 1, len(new_text))

                    if len(new_text) > len(str(limits[1])):
                        new_text = new_text[:len(str(limits[1]))]

                    if int(new_text) < limits[0]:
                        new_text = str(limits[0])
                    elif int(new_text) > limits[1]:
                        new_text = str(limits[1])

                if new_text:
                    new_text = new_text.lstrip('0')
                    if not new_text:
                        new_text = '0'
            self.get_cursor_pos()

        return False, new_text
