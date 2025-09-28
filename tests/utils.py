"""Functions/Classes shared between tests."""

from typing import Self

from pygame import Rect, SYSTEM_CURSOR_ARROW

from src.obj_utils import ObjInfo
from src.type_utils import BlitInfo, RectPos
from src.consts import BG_LAYER


class DummyUIElement():
    """Blank UI element for testing."""

    init_pos: RectPos = RectPos(0, 0, "topleft")

    cursor_type: int = SYSTEM_CURSOR_ARROW
    blit_sequence: list[BlitInfo] = []

    def __init__(self: Self, hover_rects: tuple[Rect, ...] = ()) -> None:
        """
        Initializes the hover rectangles, the layer and objects info.

        Args:
            hover rectangles
        """

        self.hover_rects: tuple[Rect, ...] = hover_rects
        self.layer: int = BG_LAYER

        self.objs_info: list[ObjInfo] = []

    def enter(self: Self) -> None:
        """Blank method to respect the UIElement protocol."""

    def leave(self: Self) -> None:
        """Blank method to respect the UIElement protocol."""

    def resize(self: Self, _win_w_ratio: float, _win_h_ratio: float) -> None:
        """Blank method to respect the UIElement protocol."""

    def move_rect(
            self: Self, _init_x: int, _init_y: int,
            _win_w_ratio: float, _win_h_ratio: float
    ) -> None:
        """Blank method to test the rec_move_rect method."""
