"""Class to simplify multi-line text rendering, renderers are cached."""

from tkinter import messagebox
from pathlib import Path
from io import BytesIO
from typing import Final

import pygame as pg
from pygame import SYSTEM_CURSOR_ARROW

from src.utils import RectPos, ObjInfo, resize_obj, try_read_file, handle_file_os_error
from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import XY, WH, BlitInfo
from src.consts import WHITE, FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I, BG_LAYER, TEXT_LAYER

_RENDERERS_CACHE: Final[dict[int, pg.Font]] = {}
_is_first_font_load_error: bool = True


def _try_add_renderer(h: int) -> None:
    """
    Adds a render to the cache with retries.

    Args:
        height
    """

    attempt_i: int
    should_retry: bool

    font_path: Path = Path("assets", "fonts", "fredoka.ttf")
    renderer: pg.Font | None = None
    error_str: str = ""
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            with font_path.open("rb") as f:
                try_lock_file(f, True)
                font_bytes: BytesIO = BytesIO(try_read_file(f))
                renderer = pg.font.Font(font_bytes, h)
            break
        except FileNotFoundError:
            error_str = "File missing."
            break
        except PermissionError:
            error_str = "Permission denied."
            break
        except LockException:
            error_str = "File locked."
            break
        except FileException as e:
            error_str = e.error_str
            break
        except pg.error as e:
            error_str = str(e)
            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            break

    if renderer is None:
        global _is_first_font_load_error

        if _is_first_font_load_error:
            messagebox.showerror("Font Load Failed", f"{font_path.name}: {error_str}")
            _is_first_font_load_error = False
        renderer = pg.font.Font(size=round(h * 1.3))
    _RENDERERS_CACHE[h] = renderer


class TextLabel:
    """Class to simplify multi-text rendering."""

    __slots__ = (
        "init_pos", "_init_h", "_renderer", "text", "_bg_color",
        "imgs", "rect", "_rects",
        "hover_rects", "layer", "blit_sequence"
    )

    cursor_type: int = SYSTEM_CURSOR_ARROW
    objs_info: list[ObjInfo] = []

    def __init__(
            self, pos: RectPos, text: str, base_layer: int = BG_LAYER, h: int = 25,
            bg_color: pg.Color | None = None
    ) -> None:
        """
        Creates the text images, rects and full rect.

        Args:
            position, text, base_layer (default = BG_LAYER), height (default = 25),
            background color (default = transparent)
        """

        self.init_pos: RectPos = pos
        self._init_h: int = h

        if self._init_h not in _RENDERERS_CACHE:
            _try_add_renderer(self._init_h)
        self._renderer: pg.Font = _RENDERERS_CACHE[self._init_h]

        self.text: str = text
        self._bg_color: pg.Color | None = bg_color

        lines: list[str] = self.text.split("\n")

        self.imgs: list[pg.Surface] = [
            self._renderer.render(line, True, WHITE, self._bg_color).convert_alpha()
            for line in lines
        ]

        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)
        self._rects: list[pg.Rect] = []

        self.hover_rects: list[pg.Rect] = []
        self.layer: int = base_layer + TEXT_LAYER
        self.blit_sequence: list[BlitInfo] = [
            (img, rect, self.layer) for img, rect in zip(self.imgs, self._rects)
        ]

        self._refresh_rects((self.init_pos.x, self.init_pos.y))

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

    def leave(self) -> None:
        """Clears the relevant data when the object state is leaved."""

    def resize(self, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Resizes the object.

        Args:
            window width ratio, window height ratio
        """

        xy: XY
        _w: int
        h: int

        xy, (_w, h) = resize_obj(self.init_pos, 0, self._init_h, win_w_ratio, win_h_ratio, True)
        if h not in _RENDERERS_CACHE:
            _try_add_renderer(h)
        self._renderer = _RENDERERS_CACHE[h]

        lines: list[str] = self.text.split("\n")
        self.imgs = [
            self._renderer.render(line, True, WHITE, self._bg_color).convert_alpha()
            for line in lines
        ]

        self._refresh_rects(xy)

    def _refresh_rects(self, xy: XY) -> None:
        """
        Refreshes the rects and full rect depending on coord_type.

        Args:
            xy
        """

        img_w: int
        img_h: int

        imgs_whs: list[WH] = [img.get_size() for img in self.imgs]

        self.rect.size = (
            max([img_w for img_w , _img_h in imgs_whs]),
            sum([img_h for _img_w, img_h  in imgs_whs]),
        )
        setattr(self.rect, self.init_pos.coord_type, xy)

        self._rects = []
        line_rect_y: int = self.rect.y
        for img_w, img_h in imgs_whs:
            # Create full line rect to get the position at coord_type
            # Shrink it to the line width and move it there

            line_rect: pg.Rect = pg.Rect(self.rect.x, line_rect_y, self.rect.w, img_h)
            line_xy: XY = getattr(line_rect, self.init_pos.coord_type)

            line_rect.w = img_w
            setattr(line_rect, self.init_pos.coord_type, line_xy)
            self._rects.append(line_rect)

            line_rect_y += line_rect.h

        self.blit_sequence = [(img, rect, self.layer) for img, rect in zip(self.imgs, self._rects)]

    def move_rect(self, init_x: int, init_y: int, win_w_ratio: float, win_h_ratio: float) -> None:
        """
        Moves the rects and rect to a specific coordinate.

        Args:
            initial x, initial y, window width ratio, window height ratio
        """

        line_init_pos: RectPos
        xy: XY
        _wh: WH
        rect: pg.Rect

        self.init_pos.x, self.init_pos.y = init_x, init_y  # Modifying init_pos is more accurate
        line_init_pos = RectPos(self.init_pos.x, self.init_pos.y, self.init_pos.coord_type)

        xy, _wh = resize_obj(line_init_pos, 0, 0, win_w_ratio, win_h_ratio)
        setattr(self.rect, line_init_pos.coord_type, xy)
        for rect in self._rects:
            xy, _wh = resize_obj(line_init_pos, 0, 0, win_w_ratio, win_h_ratio)
            setattr(rect, line_init_pos.coord_type, xy)
            line_init_pos.y += rect.h

    def set_text(self, text: str) -> None:
        """
        Sets the text and adjusts its position.

        Args:
            text
        """

        self.text = text

        lines: list[str] = self.text.split("\n")
        self.imgs = [
            self._renderer.render(line, True, WHITE, self._bg_color).convert_alpha()
            for line in lines
        ]

        xy: XY = getattr(self.rect, self.init_pos.coord_type)
        self._refresh_rects(xy)

    def get_x_at(self, i: int) -> int:
        """
        Gets the x coordinate of the character at a given index (only for single line text).

        Args:
            index
        Returns:
            character x coordinate
        """

        return self.rect.x + self._renderer.size(self.text[:i])[0]

    def get_closest_to(self, x: int) -> int:
        """
        Calculates the index of the closest character to a given x (only for single line text).

        Args:
            x coordinate
        Returns:
            index (0 - len(text))
        """

        i: int
        char: str

        prev_right: int = self.rect.x
        renderer: pg.Font = self._renderer
        for i, char in enumerate(self.text):
            current_right: int = prev_right + renderer.size(char)[0]
            if x < current_right:
                break

            prev_right = current_right

        return i if abs(x - prev_right) < abs(x - current_right) else i + 1
