"""
Paintable pixel grid with minimap
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
from typing import Final, Optional, Any

from src.utils import Point, Size, RectPos, ObjInfo, MouseInfo, load_img, get_pixels
from src.type_utils import ColorType, BlitSequence, LayeredBlitSequence, LayerSequence
from src.consts import WHITE, EMPTY_PIXEL_SURF, BG_LAYER

TRANSPARENT_GREY: Final[ColorType] = (120, 120, 120, 125)


class Grid:
    """
    Class to create a grid of pixels and it's minimap
    """

    __slots__ = (
        '_grid_init_pos', 'area', '_init_visible_area', 'visible_area', 'grid_pixel_dim',
        '_grid_img', 'grid_rect', '_grid_init_size', 'pixels', 'transparent_pixel_img',
        '_minimap_init_pos', '_minimap_img', '_minimap_rect', '_minimap_init_size',
        '_min_win_ratio', '_small_minimap_img_1', '_small_minimap_img_2', '_small_grid_img',
        '_layer'
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the grid and minimap
        Args:
            grid position, minimap position
        """

        #  Pixels dimensions are floats to represent the full size more accurately when resizing

        self._grid_init_pos: RectPos = grid_pos

        self.area: Size = Size(64, 64)
        self._init_visible_area: Size = Size(32, 32)
        self.visible_area: Size = Size(*self._init_visible_area.wh)

        self.grid_pixel_dim: float = 18.0

        self._grid_img: pg.Surface = pg.Surface((
            round(self.visible_area.w * self.grid_pixel_dim),
            round(self.visible_area.h * self.grid_pixel_dim)
        ))
        self.grid_rect: pg.Rect = self._grid_img.get_rect(
            **{self._grid_init_pos.coord_type: self._grid_init_pos.xy}
        )

        self._grid_init_size: Size = Size(*self.grid_rect.size)

        self.pixels: NDArray[np.uint8] = np.zeros((self.area.h, self.area.w, 4), np.uint8)
        self.transparent_pixel_img: pg.Surface = pg.Surface((2, 2), pg.SRCALPHA)
        self.transparent_pixel_img.fill(TRANSPARENT_GREY)

        self._minimap_init_pos: RectPos = minimap_pos

        self._minimap_img: pg.Surface = pg.Surface((256, 256))
        self._minimap_rect: pg.Rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: self._minimap_init_pos.xy}
        )

        self._minimap_init_size: Size = Size(*self._minimap_rect.size)

        self._min_win_ratio: float = 1.0  # Keeps the pixels as squares

        # Having a version where 1 grid pixel = 1 pixel is better for scaling
        self._small_minimap_img_1: pg.Surface = pg.Surface((self.area.w * 2, self.area.h * 2))
        # Adds the section indicator
        self._small_minimap_img_2: pg.Surface = self._small_minimap_img_1.copy()
        self._small_grid_img: pg.Surface = self._small_minimap_img_1.subsurface(
            (0, 0, self.visible_area.w * 2, self.visible_area.h * 2)
        ).copy()

        self._layer: int = BG_LAYER

        self.update_full(Point(0, 0), [])

    def blit(self) -> LayeredBlitSequence:
        """
        Returns:
            sequence to add in the main blit sequence
        """

        return [
            (self._grid_img, self.grid_rect.topleft, self._layer),
            (self._minimap_img, self._minimap_rect.topleft, self._layer)
        ]

    def check_hovering(self, mouse_pos: tuple[int, int]) -> tuple[Optional["Grid"], int]:
        """
        Checks if the mouse is hovering any interactable part of the object
        Args:
            mouse position
        Returns:
            hovered object (can be None), hovered object's layer
        """

        return self if self.grid_rect.collidepoint(mouse_pos) else None, self._layer

    def handle_resize(self, win_ratio_w: float, win_ratio_h: float) -> None:
        """
        Resizes the object
        Args:
            window width ratio, window height ratio
        """

        # Grid and minimap are resized normally for more consistency
        self._min_win_ratio = min(win_ratio_w, win_ratio_h)

        self.grid_pixel_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

        grid_pos: tuple[int, int] = (
            round(self._grid_init_pos.x * win_ratio_w), round(self._grid_init_pos.y * win_ratio_h)
        )
        grid_size: tuple[int, int] = (
            round(self.visible_area.w * self.grid_pixel_dim),
            round(self.visible_area.h * self.grid_pixel_dim)
        )

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_size)
        self.grid_rect = self._grid_img.get_rect(**{self._grid_init_pos.coord_type: grid_pos})

        minimap_pixel_dim: float = min(
            self._minimap_init_size.w / self.area.w, self._minimap_init_size.h / self.area.h
        ) * self._min_win_ratio

        minimap_pos: tuple[int, int] = (
            round(self._minimap_init_pos.x * win_ratio_w),
            round(self._minimap_init_pos.y * win_ratio_h)
        )
        minimap_size: tuple[int, int] = (
            round(self.area.w * minimap_pixel_dim), round(self.area.h * minimap_pixel_dim)
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_size)
        self._minimap_rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: minimap_pos}
        )

    def get_section_indicator(self, offset: Point) -> None:
        """
        Indicates the visible area on the minimap with a white rectangle
        Args:
            offset
        """

        self._small_minimap_img_2 = self._small_minimap_img_1.copy()

        visible_area_rect: pg.Rect = pg.Rect(
            offset.x * 2, offset.y * 2, self.visible_area.w * 2, self.visible_area.h * 2
        )
        pg.draw.rect(self._small_minimap_img_2, WHITE, visible_area_rect, 2)

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, self._minimap_rect.size)

    def get_grid(self, offset: Point, selected_pixels: list[Point]) -> None:
        """
        Gets the grid image from the minimap
        Args:
            offset, selected pixels
        """

        w: int
        h: int
        w, h = self.visible_area.wh
        if offset.x + w > self.area.w:
            w -= offset.x + w - self.area.w
        if offset.y + h > self.area.h:
            h -= offset.y + h - self.area.h

        w *= 2
        h *= 2

        small_grid_rect: pg.Rect = pg.Rect(offset.x * 2, offset.y * 2, w, h)
        self._small_grid_img = self._small_minimap_img_1.subsurface(small_grid_rect).copy()

        pixel_size: tuple[int, int] = self.transparent_pixel_img.get_size()
        blit_sequence: BlitSequence = [
            (self.transparent_pixel_img, (pixel.x - offset.x * 2, pixel.y - offset.y * 2))
            for pixel in selected_pixels
            if small_grid_rect.colliderect((pixel.xy, pixel_size))
        ]
        self._small_grid_img.fblits(blit_sequence)

        grid_size: tuple[int, int] = (
            round(self.visible_area.w * self.grid_pixel_dim),
            round(self.visible_area.h * self.grid_pixel_dim)
        )
        grid_pos: tuple[int, int] = getattr(self.grid_rect, self._grid_init_pos.coord_type)

        self._grid_img = pg.transform.scale(self._small_grid_img, grid_size)
        self.grid_rect = self._grid_img.get_rect(**{self._grid_init_pos.coord_type: grid_pos})

    def update_full(self, offset: Point, selected_pixels: list[Point]) -> None:
        """
        Updates all the pixels on the minimap and retrieves the grid
        Args:
            offset and selected pixels
        """

        blit_sequence: BlitSequence = []

        w: int
        h: int
        w, h = self.area.wh
        pixels: NDArray[np.uint8] = self.pixels

        empty_pixel_surf: pg.Surface = EMPTY_PIXEL_SURF
        pixel_surf: pg.Surface = pg.Surface((2, 2))
        for y in range(h):
            row: NDArray[np.uint8] = pixels[y]
            for x in range(w):
                if not row[x, -1]:
                    blit_sequence.append((empty_pixel_surf, (x * 2, y * 2)))
                else:
                    pixel_surf.fill(row[x])
                    blit_sequence.append((pixel_surf.copy(), (x * 2, y * 2)))
        self._small_minimap_img_1.fblits(blit_sequence)

        self._small_minimap_img_2 = self._small_minimap_img_1.copy()

        visible_area_rect: pg.Rect = pg.Rect(
            offset.x * 2, offset.y * 2, self.visible_area.w * 2, self.visible_area.h * 2
        )
        pg.draw.rect(self._small_minimap_img_2, WHITE, visible_area_rect, 2)

        minimap_pixel_dim: float = min(
            self._minimap_init_size.w / w, self._minimap_init_size.h / h
        ) * self._min_win_ratio

        minimap_size: tuple[int, int] = (
            round(w * minimap_pixel_dim), round(h * minimap_pixel_dim)
        )
        minimap_pos: tuple[int, int] = getattr(
            self._minimap_rect, self._minimap_init_pos.coord_type
        )

        self._minimap_img = pg.transform.scale(self._small_minimap_img_2, minimap_size)
        self._minimap_rect = self._minimap_img.get_rect(
            **{self._minimap_init_pos.coord_type: minimap_pos}
        )

        self.get_grid(offset, selected_pixels)

    def update_section(
            self, offset: Point, selected_pixels: list[Point],
            changed_pixels: list[tuple[int, int]]
    ) -> None:
        """
        Updates specific pixels on the minimap and retrieves the grid
        Args:
            offset, selected pixels, changed pixels
        """

        blit_sequence: BlitSequence = []

        pixels: NDArray[np.uint8] = self.pixels
        empty_pixel_surf: pg.Surface = EMPTY_PIXEL_SURF
        pixel_surf: pg.Surface = pg.Surface((2, 2))
        for x, y in changed_pixels:
            if not pixels[y, x, -1]:
                blit_sequence.append((empty_pixel_surf, (x * 2, y * 2)))
            else:
                pixel_surf.fill(pixels[y, x])
                blit_sequence.append((pixel_surf.copy(), (x * 2, y * 2)))
        self._small_minimap_img_1.fblits(blit_sequence)

        self.get_section_indicator(offset)
        self.get_grid(offset, selected_pixels)

    def load_from_img(
            self, img: Optional[pg.Surface], offset: Point, selected_pixels: list[Point]
    ) -> None:
        """
        Loads a surface's rgba values into a 3D array and blits it on the grid
        Args:
            image (if it's None it creates an empty grid), offset, selected pixels
        """

        if not img:
            self.pixels = np.zeros((self.area.h, self.area.w, 4), np.uint8)
        else:
            self.pixels = get_pixels(img)

            extra_rows: int = self.area.h - self.pixels.shape[0]
            extra_cols: int = self.area.w - self.pixels.shape[1]

            if extra_rows < 0:
                self.pixels = self.pixels[:self.area.h, :, :]
            elif extra_rows > 0:
                self.pixels = np.pad(
                    self.pixels, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0
                )
            if extra_cols < 0:
                self.pixels = self.pixels[:, :self.area.w, :]
            elif extra_cols > 0:
                self.pixels = np.pad(
                    self.pixels, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0
                )

        self.update_full(offset, selected_pixels)

    def resize(self, area: Size) -> None:
        """
        Resizes the grid
        Args:
            area
        """

        self.area = area

        extra_rows: int = self.area.h - self.pixels.shape[0]
        extra_cols: int = self.area.w - self.pixels.shape[1]

        if extra_rows < 0:
            self.pixels = self.pixels[:self.area.h, :, :]
        elif extra_rows > 0:
            self.pixels = np.pad(self.pixels, ((0, extra_rows), (0, 0), (0, 0)), constant_values=0)
        if extra_cols < 0:
            self.pixels = self.pixels[:, :self.area.w, :]
        elif extra_cols > 0:
            self.pixels = np.pad(self.pixels, ((0, 0), (0, extra_cols), (0, 0)), constant_values=0)

        self.visible_area.w = min(self.visible_area.w, self.area.w)
        self.visible_area.h = min(self.visible_area.h, self.area.h)
        self.grid_pixel_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

        self._small_minimap_img_1 = pg.Surface((self.area.w * 2, self.area.h * 2))

    def zoom(self, amount: int, reach_limit: list[bool]) -> None:
        """
        Changes pixels dimension and visible area
        Args:
            amount, reach limit flags
        """

        visible_area: Size = self.visible_area
        if any(reach_limit):
            if reach_limit[0]:
                visible_area.w = visible_area.h = 1
            elif reach_limit[1]:
                visible_area.w, visible_area.h = self.area.wh
        else:
            if visible_area.w == visible_area.h:
                visible_area.w = max(min(visible_area.w - amount, self.area.w), 1)
                visible_area.h = max(min(visible_area.h - amount, self.area.h), 1)
            else:
                if amount > 0:
                    #  Zooming in decreases the largest side
                    if visible_area.w > visible_area.h:
                        visible_area.w = max(visible_area.w - amount, 1)
                        visible_area.h = min(visible_area.wh)
                    else:
                        visible_area.h = max(visible_area.h - amount, 1)
                        visible_area.w = min(visible_area.wh)
                else:
                    #  Zooming out increases the smallest side if it can be increased
                    should_increase_w: bool = (
                        (visible_area.w < visible_area.h or visible_area.h == self.area.h) and
                        visible_area.w != self.area.w
                    )
                    if should_increase_w:
                        visible_area.w = min(visible_area.w - amount, self.area.w)
                        visible_area.h = max(min(visible_area.w, self.area.h), visible_area.h)
                    else:
                        visible_area.h = min(visible_area.h - amount, self.area.h)
                        visible_area.w = max(min(visible_area.h, self.area.w), visible_area.w)

        self.grid_pixel_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

    def reset(self, selected_pixels: list[Point]) -> None:
        """
        Resets the visible area and offset
        Args:
            selected pixels
        """

        self.visible_area.w, self.visible_area.h = self._init_visible_area.wh
        self.grid_pixel_dim = min(
            self._grid_init_size.w / self.visible_area.w,
            self._grid_init_size.h / self.visible_area.h
        ) * self._min_win_ratio

        self.get_grid(Point(0, 0), selected_pixels)
        self.get_section_indicator(Point(0, 0))


class GridManager:
    """
    Class to create and edit a grid of pixels
    """

    __slots__ = (
        'grid', '_selected_pixels', '_is_hovering', '_prev_mouse_x', '_prev_mouse_y',
        '_prev_hovered_obj', '_offset', '_traveled_dist', 'objs_info'
    )

    def __init__(self, grid_pos: RectPos, minimap_pos: RectPos) -> None:
        """
        Creates the Grid object
        Args:
            grid position, minimap position
        """

        self.grid: Grid = Grid(grid_pos, minimap_pos)

        self._selected_pixels: list[Point] = []  # Absolute coordinates
        self._is_hovering: bool = False

        self._prev_mouse_x: int
        self._prev_mouse_y: int
        self._prev_mouse_x, self._prev_mouse_y = pg.mouse.get_pos()
        self._prev_hovered_obj: Optional[Grid] = None

        self._offset: Point = Point(0, 0)
        self._traveled_dist: Size = Size(0, 0)

        self.objs_info: list[ObjInfo] = [ObjInfo("grid", self.grid)]

    def leave(self) -> None:
        """
        Clears all the relevant data when a state is leaved
        """

        self._selected_pixels = []
        self._is_hovering = False
        self._traveled_dist.w = self._traveled_dist.h = 0

        self.grid.get_grid(self._offset, self._selected_pixels)

    def load_from_path(self, file_path: str, area: Optional[Size]) -> None:
        """
        Loads an image from a path and renders it into the grid
        Args:
            path (if it's empty it creates an empty grid), area
        """

        self._offset.x = self._offset.y = 0

        if area:
            self.grid.resize(area)
        img: Optional[pg.Surface] = load_img(file_path) if file_path else None
        self.grid.load_from_img(img, self._offset, self._selected_pixels)

    def _handle_keys(self, keys: tuple[int, ...], mouse_pixel: Point, brush_size: int) -> None:
        """
        Handles grid movement with arrows
        Args:
            keys, mouse pixel, brush size
        """

        if not any(key in keys for key in (pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN)):
            return

        new_mouse_pixel: Point = Point(*mouse_pixel.xy)

        k_mods: int = pg.key.get_mods()
        kmod_ctrl: int = k_mods & pg.KMOD_CTRL

        cols: int
        rows: int
        cols, rows = self.grid.area.wh
        visible_area: Size = self.grid.visible_area
        pixel_dim: float = self.grid.grid_pixel_dim

        movement_value: int = 1
        if k_mods & pg.KMOD_ALT:
            movement_value = brush_size
        if k_mods & pg.KMOD_SHIFT:
            movement_value = max(visible_area.wh)

        extra_offset: int
        if pg.K_LEFT in keys:
            if kmod_ctrl:
                new_mouse_pixel.x = 0
                self._offset.x = 0
            else:
                new_mouse_pixel.x -= movement_value
                if new_mouse_pixel.x < 0:
                    extra_offset = new_mouse_pixel.x
                    self._offset.x = max(self._offset.x + extra_offset, 0)
                    new_mouse_pixel.x = 0
        if pg.K_RIGHT in keys:
            if kmod_ctrl:
                new_mouse_pixel.x = visible_area.w - 1
                self._offset.x = cols - visible_area.w
            else:
                new_mouse_pixel.x += movement_value
                if new_mouse_pixel.x + 1 > visible_area.w:
                    extra_offset = new_mouse_pixel.x + 1 - visible_area.w
                    self._offset.x = min(self._offset.x + extra_offset, cols - visible_area.w)
                    new_mouse_pixel.x = visible_area.w - 1
        if pg.K_UP in keys:
            if kmod_ctrl:
                new_mouse_pixel.y = 0
                self._offset.y = 0
            else:
                new_mouse_pixel.y -= movement_value
                if new_mouse_pixel.y < 0:
                    extra_offset = new_mouse_pixel.y
                    self._offset.y = max(self._offset.y + extra_offset, 0)
                    new_mouse_pixel.y = 0
        if pg.K_DOWN in keys:
            if kmod_ctrl:
                new_mouse_pixel.y = visible_area.h - 1
                self._offset.y = rows - visible_area.h
            else:
                new_mouse_pixel.y += movement_value
                if new_mouse_pixel.y + 1 > visible_area.h:
                    extra_offset = new_mouse_pixel.y + 1 - visible_area.h
                    self._offset.y = min(self._offset.y + extra_offset, rows - visible_area.h)
                    new_mouse_pixel.y = visible_area.h - 1

        self.grid.get_section_indicator(self._offset)

        half_pixel_dim: float = pixel_dim / 2.0
        pg.mouse.set_pos((
            round(self.grid.grid_rect.x + new_mouse_pixel.x * pixel_dim + half_pixel_dim),
            round(self.grid.grid_rect.y + new_mouse_pixel.y * pixel_dim + half_pixel_dim)
        ))

    def _get_pixel_info(
            self, mouse_info: MouseInfo, keys: tuple[int, ...], brush_size: int
    ) -> tuple[Point, Point]:
        """
        Calculates previous and current mouse pixel and handles arrow movement
        Args:
            mouse info, keys, brush size
        Returns:
            start and end
        """

        prev_mouse_pixel: Point = Point(
            int((self._prev_mouse_x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int((self._prev_mouse_y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )
        mouse_pixel: Point = Point(
            int((mouse_info.x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim),
            int((mouse_info.y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim)
        )

        prev_offset_x: int = self._offset.x
        prev_offset_y: int = self._offset.y
        # Can change offset so it can't be in the move method
        self._handle_keys(keys, mouse_pixel, brush_size)

        prev_mouse_pixel.x += prev_offset_x - brush_size // 2
        prev_mouse_pixel.y += prev_offset_y - brush_size // 2
        mouse_pixel.x += self._offset.x - brush_size // 2
        mouse_pixel.y += self._offset.y - brush_size // 2

        return prev_mouse_pixel, mouse_pixel

    def _handle_brush(
            self, start: Point, end: Point, is_drawing: bool, brush_size: int,
            extra_info: dict[str, Any]
    ) -> list[tuple[int, int]]:
        """
        Handles brush tool
        Args:
            start, end, drawing bool, brush size, extra info
        Returns:
            changed pixels
        """

        changed_pixels: list[tuple[int, int]] = []
        area: Size = self.grid.area

        self._selected_pixels.append(Point(end.x * 2, end.y * 2))
        if extra_info["x_mirror"]:
            self._selected_pixels.extend(
                Point((area.w - brush_size) * 2 - pixel.x, pixel.y)
                for pixel in self._selected_pixels.copy()
            )
        if extra_info["y_mirror"]:
            self._selected_pixels.extend(
                Point(pixel.x, (area.h - brush_size) * 2 - pixel.y)
                for pixel in self._selected_pixels.copy()
            )

        if not is_drawing:
            return changed_pixels

        '''
        Get the coordinates of the grid pixels the mouse touched between frames using
        Bresenham's Line Algorithm
        '''

        x_1: int = max(min(start.x, area.w - 1), -brush_size + 1)
        y_1: int = max(min(start.y, area.h - 1), -brush_size + 1)
        x_2: int = max(min(end.x, area.w - 1), -brush_size + 1)
        y_2: int = max(min(end.y, area.h - 1), -brush_size + 1)

        delta_x: int = abs(x_2 - x_1)
        delta_y: int = abs(y_2 - y_1)
        step_x: int = 1 if x_1 < x_2 else -1
        step_y: int = 1 if y_1 < y_2 else -1
        err: int = delta_x - delta_y
        while True:
            changed_pixels.append((x_1, y_1))
            if x_1 == x_2 and y_1 == y_2:
                break

            err_2: int = err * 2
            if err_2 > -delta_y:
                err -= delta_y
                x_1 += step_x
            if err_2 < delta_x:
                err += delta_x
                y_1 += step_y

        if extra_info["x_mirror"]:
            changed_pixels.extend((area.w - brush_size - x, y) for x, y in changed_pixels.copy())
        if extra_info["y_mirror"]:
            changed_pixels.extend((x, area.h - brush_size - y) for x, y in changed_pixels.copy())

        # Resizes the pixels to the brush size
        return [
            (x, y)
            for original_x, original_y in changed_pixels
            for x in range(max(original_x, 0), min(original_x + brush_size, area.w))
            for y in range(max(original_y, 0), min(original_y + brush_size, area.h))
        ]

    def _draw(
            self, mouse_info: MouseInfo, keys: tuple[int, ...], color: ColorType, brush_size: int,
            tool_info: tuple[str, dict[str, Any]]
    ) -> None:
        """
        Handles grid drawing
        Args:
            mouse_info, keys, color, brush size, tool info
        """

        prev_mouse_pixel: Point  # Absolute coordinates
        mouse_pixel: Point  # Absolute coordinates
        prev_mouse_pixel, mouse_pixel = self._get_pixel_info(mouse_info, keys, brush_size)

        if self.grid.transparent_pixel_img.get_width() != brush_size * 2:
            self.grid.transparent_pixel_img = pg.transform.scale(
                self.grid.transparent_pixel_img, (brush_size * 2, brush_size * 2)
            )
            self.grid.get_grid(self._offset, self._selected_pixels)

        prev_selected_pixels: list[Point] = self._selected_pixels
        self._selected_pixels = []

        is_drawing: bool = (
            (mouse_info.pressed[0] or pg.K_RETURN in keys) or
            (mouse_info.pressed[2] or pg.K_BACKSPACE in keys)
        )

        changed_pixels: list[tuple[int, int]] = []
        extra_tool_info: dict[str, Any] = tool_info[1]
        match tool_info[0]:
            case "brush":
                changed_pixels = self._handle_brush(
                    prev_mouse_pixel, mouse_pixel, is_drawing, brush_size, extra_tool_info
                )

        prev_pixels: NDArray[np.uint8] = np.copy(self.grid.pixels)
        if changed_pixels:
            rgba_color: list[int] = [0, 0, 0, 0]
            if mouse_info.pressed[0] or pg.K_RETURN in keys:
                rgba_color = list(color) + [255]

            changed_pixels = list(set(changed_pixels))
            for x, y in changed_pixels:
                self.grid.pixels[y, x] = rgba_color

        if not np.array_equal(self.grid.pixels, prev_pixels):
            self.grid.update_section(self._offset, self._selected_pixels, changed_pixels)
        elif self._selected_pixels != prev_selected_pixels:
            self.grid.get_grid(self._offset, self._selected_pixels)

    def _move(self, mouse_info: MouseInfo) -> None:
        """
        Allows changing the section of the grid that is drawn
        Args:
            mouse info
        """

        if not mouse_info.pressed[1]:
            self._traveled_dist.w = self._traveled_dist.h = 0

            return

        pixels_traveled: int

        self._traveled_dist.w += self._prev_mouse_x - mouse_info.x
        if abs(self._traveled_dist.w) >= self.grid.grid_pixel_dim:
            pixels_traveled = int(abs(self._traveled_dist.w) / self.grid.grid_pixel_dim)
            if self._traveled_dist.w < 0:
                pixels_traveled = -pixels_traveled
            self._traveled_dist.w -= int(pixels_traveled * self.grid.grid_pixel_dim)

            self._offset.x = max(
                min(self._offset.x + pixels_traveled, self.grid.area.w - self.grid.visible_area.w),
                0
            )
            self.grid.get_section_indicator(self._offset)
            self.grid.get_grid(self._offset, self._selected_pixels)

        self._traveled_dist.h += self._prev_mouse_y - mouse_info.y
        if abs(self._traveled_dist.h) >= self.grid.grid_pixel_dim:
            pixels_traveled = int(abs(self._traveled_dist.h) / self.grid.grid_pixel_dim)
            if self._traveled_dist.h < 0:
                pixels_traveled = -pixels_traveled
            self._traveled_dist.h -= int(pixels_traveled * self.grid.grid_pixel_dim)

            self._offset.y = max(
                min(self._offset.y + pixels_traveled, self.grid.area.h - self.grid.visible_area.h),
                0
            )
            self.grid.get_section_indicator(self._offset)
            self.grid.get_grid(self._offset, self._selected_pixels)

    def resize(self, area: Optional[Size]) -> None:
        """
        Resizes the grid
        Args:
            area
        """

        if not area:
            return

        self._traveled_dist.w = self._traveled_dist.h = 0

        self.grid.resize(area)
        self._offset.x = min(self._offset.x, self.grid.area.w - self.grid.visible_area.w)
        self._offset.y = min(self._offset.y, self.grid.area.h - self.grid.visible_area.h)

        self.grid.update_full(self._offset, self._selected_pixels)

    def zoom(self, amount: int, brush_size: int, reach_limit: list[bool]) -> None:
        """
        Zooms in/out
        Args:
            amount, brush size, reach limit flags
        """

        if not self._is_hovering:
            return

        mouse_x: int
        mouse_y: int
        mouse_x, mouse_y = pg.mouse.get_pos()

        prev_mouse_pixel_x: int = (
            int((mouse_x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim) - brush_size // 2
        )
        prev_mouse_pixel_y: int = (
            int((mouse_y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim) - brush_size // 2
        )

        self.grid.zoom(amount, reach_limit)

        mouse_pixel_x: int = (
            int((mouse_x - self.grid.grid_rect.x) / self.grid.grid_pixel_dim) - brush_size // 2
        )
        mouse_pixel_y: int = (
            int((mouse_y - self.grid.grid_rect.y) / self.grid.grid_pixel_dim) - brush_size // 2
        )

        self._offset.x = max(
            min(
                self._offset.x + prev_mouse_pixel_x - mouse_pixel_x,
                self.grid.area.w - self.grid.visible_area.w
            ), 0
        )
        self._offset.y = max(
            min(
                self._offset.y + prev_mouse_pixel_y - mouse_pixel_y,
                self.grid.area.h - self.grid.visible_area.h
            ), 0
        )

        for pixel in self._selected_pixels:
            pixel.x, pixel.y = mouse_pixel_x * 2, mouse_pixel_y * 2

        self.grid.get_grid(self._offset, self._selected_pixels)
        self.grid.get_section_indicator(self._offset)

    def upt(
            self, hovered_obj: Any, mouse_info: MouseInfo, keys: tuple[int, ...], color: ColorType,
            brush_size: int, tool_info: tuple[str, dict[str, Any]]
    ) -> None:
        """
        Allows drawing, moving and zooming
        Args:
            hovered object (can be None), mouse info, keys, color, brush size, tool info
        """

        if self.grid != hovered_obj:
            if self._is_hovering:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)
                self._is_hovering = False
        elif not self._is_hovering:
            pg.mouse.set_cursor(pg.SYSTEM_CURSOR_CROSSHAIR)
            self._is_hovering = True

        # Makes drawing possible even 1 frame after the grid was left
        if self.grid in (hovered_obj, self._prev_hovered_obj):
            self._draw(mouse_info, keys, color, brush_size, tool_info)
        elif self._selected_pixels:
            self._selected_pixels = []
            self.grid.get_grid(self._offset, self._selected_pixels)

        self._move(mouse_info)

        k_mods: int = pg.key.get_mods()
        if k_mods & pg.KMOD_CTRL and pg.K_r in keys:
            self._offset.x = self._offset.y = 0
            self._traveled_dist.w = self._traveled_dist.h = 0
            self.grid.reset(self._selected_pixels)

        self._prev_mouse_x, self._prev_mouse_y = mouse_info.xy
        self._prev_hovered_obj = hovered_obj
