"""Class to simplify multi-line text rendering, renderers are cached."""

from tkinter import messagebox
from pathlib import Path
from io import BytesIO
from typing import Self, Final

import pygame as pg
from pygame import SYSTEM_CURSOR_ARROW

import src.obj_utils as objs
import src.vars as my_vars
from src.obj_utils import ObjInfo, resize_obj
from src.file_utils import FileError, handle_file_os_error, try_read_file
from src.lock_utils import LockError, try_lock_file
from src.type_utils import XY, WH, BlitInfo, RectPos
from src.consts import WHITE, FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I, BG_LAYER, TEXT_LAYER

_RENDERERS_CACHE: Final[dict[int, pg.Font]] = {}
_is_first_font_load_error: bool = True


def _try_add_renderer(h: int) -> None:
    """
    Adds a render to the cache with retries.

    Args:
        height
    """

    global _is_first_font_load_error
    attempt_i: int
    should_retry: bool

    font_path: Path = Path("assets", "fonts", "fredoka.ttf")
    renderer: pg.Font | None = None
    error_str: str = ""
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            with font_path.open("rb") as f:
                try_lock_file(f, should_be_shared=True)
                font_bytes_io: BytesIO = BytesIO(try_read_file(f))
                renderer = pg.font.Font(font_bytes_io, h)
            break
        except (FileNotFoundError, PermissionError, LockError, FileError, pg.error) as e:
            error_str = {
                FileNotFoundError: "File missing.",
                PermissionError: "Permission denied.",
                LockError: "File locked.",
                FileError: e.error_str if isinstance(e, FileError) else "",
                pg.error: str(e),
            }[type(e)]

            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and _is_first_font_load_error and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            break

    if renderer is None:
        if _is_first_font_load_error:
            messagebox.showerror("Font Load Failed", f"{font_path.name}: {error_str}")
            _is_first_font_load_error = False
        renderer = pg.font.Font(size=round(h * 1.3))
    _RENDERERS_CACHE[h] = renderer


class TextLabel:
    """Class to simplify multi-line text rendering."""

    __slots__ = (
        "init_pos", "init_h", "_renderer",
        "text", "_bg_color",
        "_imgs", "rect", "_rects",
        "hover_rects", "layer", "blit_sequence",
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW
    objs_info: tuple[ObjInfo, ...] = ()

    def __init__(
            self: Self, pos: RectPos, text: str,
            base_layer: int = BG_LAYER,
            h: int = 25, bg_color: pg.Color | None = None
    ) -> None:
        """
        Creates the text images, rects and full rect.

        Args:
            position, text,
            base_layer (default = BG_LAYER),
            height (default = 25), background color (default = None)
        """

        self.init_pos: RectPos = pos
        self.init_h: int = h

        if self.init_h not in _RENDERERS_CACHE:
            _try_add_renderer(self.init_h)
        self._renderer: pg.Font = _RENDERERS_CACHE[self.init_h]

        self.text: str = text
        self._bg_color: pg.Color | None = bg_color

        self._imgs: tuple[pg.Surface, ...] = tuple([
            self._renderer.render(
                line,
                antialias=True, color=WHITE, bgcolor=self._bg_color
            ).convert_alpha()
            for line in self.text.split("\n")
        ])

        self.rect: pg.Rect = pg.Rect()
        self._rects: tuple[pg.Rect, ...] = ()

        self.hover_rects: tuple[pg.Rect, ...] = ()
        self.layer: int = base_layer + TEXT_LAYER
        self.blit_sequence: list[BlitInfo] = []

        self.refresh_rects((self.init_pos.x, self.init_pos.y))

    def enter(self: Self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self: Self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self: Self) -> None:
        """Resizes the object."""

        xy: XY
        _w: int
        h: int

        xy, (_w, h) = resize_obj(
            self.init_pos, init_w=0, init_h=self.init_h,
            should_keep_wh_ratio=True
        )
        if h not in _RENDERERS_CACHE:
            _try_add_renderer(h)
        self._renderer = _RENDERERS_CACHE[h]

        self._imgs = tuple([
            self._renderer.render(
                line,
                antialias=True, color=WHITE, bgcolor=self._bg_color
            ).convert_alpha()
            for line in self.text.split("\n")
        ])
        self.refresh_rects(xy)

    def move_rect(self: Self, init_x: int, init_y: int, should_scale: bool) -> None:
        """
        Moves the rects and rect to a specific coordinate.

        Args:
            initial x, initial y, scale flag
        """

        xy: XY
        rect: pg.Rect

        prev_rect_x: int = self.rect.x
        prev_rect_y: int = self.rect.y
        self.init_pos.x, self.init_pos.y = init_x, init_y  # More accurate

        if should_scale:
            xy = (
                round(self.init_pos.x * my_vars.win_w_ratio),
                round(self.init_pos.y * my_vars.win_h_ratio),
            )
        else:
            xy = (self.init_pos.x, self.init_pos.y)
        setattr(self.rect, self.init_pos.coord_type, xy)

        change_x: int = self.rect.x - prev_rect_x
        change_y: int = self.rect.y - prev_rect_y
        for rect in self._rects:
            rect.x += change_x
            rect.y += change_y

    def refresh_rects(self: Self, xy: XY) -> None:
        """
        Refreshes the rects and full rect depending on coord_type.

        Args:
            xy
        """

        img_w: int
        img_h: int

        imgs_whs: list[WH] = [img.get_size() for img in self._imgs]

        self.rect.size = (
            max([img_w for img_w , _img_h in imgs_whs]),
            sum([img_h for _img_w, img_h  in imgs_whs]),
        )
        setattr(self.rect, self.init_pos.coord_type, xy)

        self._rects = ()
        line_rect_y: int = self.rect.y
        for img_w, img_h in imgs_whs:
            # Creates the full line rect to get the position at coord_type
            # Shrinks it to the line width and moves it there

            line_rect: pg.Rect = pg.Rect(self.rect.x, line_rect_y, self.rect.w, img_h)
            line_xy: XY = getattr(line_rect, self.init_pos.coord_type)

            line_rect.w = img_w

            setattr(line_rect, self.init_pos.coord_type, line_xy)
            self._rects += (line_rect,)
            line_rect_y += line_rect.h

        self.blit_sequence = [(img, rect, self.layer) for img, rect in zip(self._imgs, self._rects)]

    def set_text(self: Self, text: str) -> None:
        """
        Sets the text and adjusts its position.

        Args:
            text
        """

        self.text = text
        self._imgs = tuple([
            self._renderer.render(
                line,
                antialias=True, color=WHITE, bgcolor=self._bg_color
            ).convert_alpha()
            for line in self.text.split("\n")
        ])

        xy: XY = getattr(self.rect, self.init_pos.coord_type)
        self.refresh_rects(xy)

    def get_x_at(self: Self, char_i: int) -> int:
        """
        Gets the x coordinate of the character at a given index (only for single line text).

        Args:
            character index
        Returns:
            character x coordinate
        """

        return self.rect.x + self._renderer.size(self.text[:char_i])[0]

    def get_closest_to(self: Self, x: int) -> int:
        """
        Gets the index of the closest character to a given x (only for single line text).

        Args:
            x coordinate
        Returns:
            index (0 - len(text))
        """

        char: str

        i: int = 0
        prev_x: int = self.rect.x
        current_x: int = prev_x
        for i, char in enumerate(self.text):
            current_x = prev_x + self._renderer.size(char)[0]
            if x < current_x:
                break

            prev_x = current_x

        return i if abs(x - prev_x) < abs(x - current_x) else i + 1

    def start_animation(self: Self) -> None:
        """Resets the alpha value and starts the fade-in animation."""

        self._imgs[0].set_alpha(0)
        objs.animating_objs.add(self)

    def animate(self: Self, dt: float) -> None:
        """
        Plays a frame of the active animation.

        Args:
            delta time
        """

        img: pg.Surface

        a: int | None = self._imgs[0].get_alpha()
        if a is None:
            a = 0

        a = round(a + (8 * dt))
        if a >= 255:
            a = 255
            objs.animating_objs.remove(self)

        for img in self._imgs:
            img.set_alpha(a)
