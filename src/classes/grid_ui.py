"""Interface to modify the grid."""

from typing import TypeAlias, Final

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.classes.num_input_box import NumInputBox
from src.classes.ui import UI, CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON
from src.classes.clickable import Checkbox
from src.classes.text_label import TextLabel

from src.utils import RectPos, Size, Ratio, ObjInfo, Mouse, Keyboard, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import MOUSE_LEFT, EMPTY_TILE_ARR, NUM_TILE_ROWS, NUM_TILE_COLS, UI_LAYER

SelectionType: TypeAlias = "NumSlider"

MOVEMENT_THRESHOLD: Final[int] = 10
SPEED_SCALING_FACTOR: Final[int] = MOVEMENT_THRESHOLD * 15
MAX_DIM: Final[int] = 256


class NumSlider:
    """Class that allows picking a number in a predefined range either by sliding or typing."""

    __slots__ = (
        "value", "input_box", "_prev_mouse_x", "_traveled_x", "_speeds", "_is_sliding", "objs_info"
    )

    def __init__(self, pos: RectPos, extra_text: str, base_layer: int = UI_LAYER) -> None:
        """
        Creates the slider and extra text.

        Args:
            position, extra text, base layer (default = UI_LAYER)
        """

        self.value: int
        self.input_box: NumInputBox = NumInputBox(pos, base_layer)

        self._prev_mouse_x: int
        self._traveled_x: int = 0
        self._speeds: list[int] = []
        self._is_sliding: bool = False

        extra_text_label_x: int = self.input_box.rect.x - 10
        extra_text_label: TextLabel = TextLabel(
            RectPos(extra_text_label_x, self.input_box.rect.centery, "midright"), extra_text,
            base_layer
        )

        self.objs_info: list[ObjInfo] = [ObjInfo(self.input_box), ObjInfo(extra_text_label)]

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._prev_mouse_x = pg.mouse.get_pos()[0]

    def leave(self) -> None:
        """Clears all the relevant data when the object state is leaved."""

        self._traveled_x = 0
        self._speeds.clear()
        self._is_sliding = False
        self.input_box.cursor_type = pg.SYSTEM_CURSOR_IBEAM

    def set_value(self, value: int) -> None:
        """
        Sets the slider on a specific value.

        Args:
            value
        """

        self.value = value
        self.input_box.text_label.set_text(str(self.value))
        self.input_box.bounded_set_cursor_i(0)

    def _slide(self, mouse_x: int, input_box_text: str, max_value: int) -> str:
        """
        Changes the value with the mouse, it's faster when moving the mouse faster.

        Args:
            mouse x, input box text, maximum value
        """

        speed: int = mouse_x - self._prev_mouse_x
        if speed:
            self._speeds.append(speed)
        self._traveled_x += speed

        copy_input_box_text: str = input_box_text
        if abs(self._traveled_x) >= MOVEMENT_THRESHOLD:
            units_traveled: float = self._traveled_x / MOVEMENT_THRESHOLD
            avg_speed: float = sum(self._speeds) / len(self._speeds)
            scaled_avg_speed: float = max(avg_speed / SPEED_SCALING_FACTOR, 1)
            scaled_units: int = int(units_traveled * scaled_avg_speed)
            value: int = max(min(self.value + scaled_units, max_value), 1)

            copy_input_box_text = str(value)
            self._speeds.clear()
            self._traveled_x -= int(units_traveled) * MOVEMENT_THRESHOLD

        return copy_input_box_text

    def upt(
            self, mouse: Mouse, keyboard: Keyboard, max_value: int, selected_obj: SelectionType
    ) -> bool:
        """
        Allows to select a color either by sliding or typing.

        Args:
            mouse, keyboard, maximum value, selected object
        Returns:
            clicked flag
        """

        if not mouse.pressed[MOUSE_LEFT]:
            self._traveled_x = 0
            self._speeds.clear()
            self._is_sliding = False
            self.input_box.cursor_type = pg.SYSTEM_CURSOR_IBEAM
        elif self.input_box == mouse.hovered_obj:
            self._is_sliding = True
            self.input_box.cursor_type = pg.SYSTEM_CURSOR_SIZEWE

        is_input_box_clicked: bool
        copy_input_box_text: str
        is_input_box_clicked, copy_input_box_text = self.input_box.upt(
            mouse, keyboard, (1, max_value), selected_obj == self
        )
        if self._is_sliding:
            copy_input_box_text = self._slide(mouse.x, copy_input_box_text, max_value)

        if copy_input_box_text != self.input_box.text_label.text:
            self.value = int(copy_input_box_text or 1)
            self.input_box.text_label.set_text(copy_input_box_text)
            self.input_box.bounded_set_cursor_i(None)

        self._prev_mouse_x = mouse.x

        return is_input_box_clicked


class GridUI(UI):
    """Class to create an interface that allows modifying the grid, has a preview."""

    __slots__ = (
        "_preview_init_pos", "_preview_img", "_preview_rect", "_preview_size_cap",
        "_h_slider", "_w_slider", "values_ratio", "_preview_tiles", "checkbox",
        "_selection_i", "_win_ratio"
    )

    def __init__(self, pos: RectPos) -> None:
        """
        Initializes the interface.

        Args:
            position
        """

        # Tiles dimension is a float to represent the full size more accurately when resizing

        super().__init__(pos, "MODIFY GRID")

        preview_init_y: int = self._rect.centery + 40
        self._preview_init_pos: RectPos = RectPos(self._rect.centerx, preview_init_y, "center")

        self._preview_img: pg.Surface
        self._preview_rect: pg.Rect = pg.Rect(0, 0, 300, 300)
        setattr(self._preview_rect, self._preview_init_pos.coord_type, self._preview_init_pos.xy)

        self._preview_size_cap: Size = Size(*self._preview_rect.size)

        slider_x: int = self._preview_rect.x + 20
        self._h_slider: NumSlider = NumSlider(
            RectPos(slider_x, self._preview_rect.y - 25, "bottomleft"), "height"
        )
        self._w_slider: NumSlider = NumSlider(
            RectPos(slider_x, self._h_slider.input_box.rect.y - 25, "bottomleft"), "width"
        )
        self.values_ratio: Ratio = Ratio(1, 1)

        self._preview_tiles: NDArray[np.uint8]

        checkbox_y: int = self._h_slider.input_box.rect.centery
        self.checkbox: Checkbox = Checkbox(
            RectPos(self._preview_rect.right - 20, checkbox_y, "midright"),
            [CHECKBOX_IMG_OFF, CHECKBOX_IMG_ON], "keep ratio", "(CTRL+K)", UI_LAYER
        )

        self._selection_i: int
        self._win_ratio: Ratio = Ratio(1, 1)

        self.objs_info.extend(
            [ObjInfo(self._w_slider), ObjInfo(self._h_slider), ObjInfo(self.checkbox)]
        )

    def get_blit_sequence(self) -> list[LayeredBlitInfo]:
        """
        Gets the blit sequence.

        Returns:
            sequence to add in the main blit sequence
        """

        sequence: list[LayeredBlitInfo] = super().get_blit_sequence()
        sequence.append((self._preview_img, self._preview_rect.topleft, UI_LAYER))

        return sequence

    def enter(self) -> None:
        """Initializes all the relevant data when the object state is entered."""

        self._selection_i = 0

    def resize(self, win_ratio: Ratio) -> None:
        """
        Resizes the object.

        Args:
            window size ratio
        """

        self._win_ratio = win_ratio

        super().resize(self._win_ratio)
        self._get_preview()

    def set_info(self, area: Size, tiles: NDArray[np.uint8]) -> None:
        """
        Sets the size and tiles.

        Args:
            area, tiles
        """

        self._w_slider.set_value(area.w)
        self._h_slider.set_value(area.h)
        self._preview_tiles = tiles
        self.values_ratio.wh = (area.h / area.w, area.w / area.h)

        self._get_preview()

    def _fit_tiles(self) -> NDArray[np.uint8]:
        """
        Adjusts the tiles to fit the area.

        Returns:
            tiles
        """

        copy_tiles: NDArray[np.uint8] = self._preview_tiles
        pad_width: tuple[SizePair, SizePair, SizePair]

        num_extra_rows: int = self._h_slider.value - copy_tiles.shape[0]
        if num_extra_rows < 0:
            copy_tiles = copy_tiles[:self._h_slider.value, ...]
        elif num_extra_rows > 0:
            pad_width = ((0, num_extra_rows), (0, 0), (0, 0))
            copy_tiles = np.pad(copy_tiles, pad_width, constant_values=0)

        num_extra_cols: int = self._w_slider.value - copy_tiles.shape[1]
        if num_extra_cols < 0:
            copy_tiles = copy_tiles[:, :self._w_slider.value, ...]
        elif num_extra_cols > 0:
            pad_width = ((0, 0), (0, num_extra_cols), (0, 0))
            copy_tiles = np.pad(copy_tiles, pad_width, constant_values=0)

        return copy_tiles

    def _resize_preview(self, small_preview_img: pg.Surface) -> None:
        """
        Resizes the preview.

        Args:
            small preview image
        """

        cap_w: int = self._preview_size_cap.w
        cap_h: int = self._preview_size_cap.h
        init_tile_dim: float = min(cap_w / self._w_slider.value, cap_h / self._h_slider.value)
        init_w: float = self._w_slider.value * init_tile_dim
        init_h: float = self._h_slider.value * init_tile_dim

        xy: PosPair
        wh: SizePair
        xy, wh = resize_obj(self._preview_init_pos, init_w, init_h, self._win_ratio, True)
        preview_coord_type: str = self._preview_init_pos.coord_type
        self._preview_img = pg.transform.scale(small_preview_img, wh)
        self._preview_rect = self._preview_img.get_rect(**{preview_coord_type: xy})

    def _get_preview(self) -> None:
        """Gets a preview of the grid."""

        tiles: NDArray[np.uint8] = self._fit_tiles()

        # Repeat tiles so an empty tile image takes 1 normal-sized tile
        tiles = np.repeat(np.repeat(tiles, NUM_TILE_ROWS, 0), NUM_TILE_COLS, 1)
        empty_tiles_mask: NDArray[np.bool_] = tiles[..., 3:4] == 0
        tiles = tiles[..., :3]

        ver_reps: int = self._h_slider.value
        hor_reps: int = self._w_slider.value
        empty_tiles: NDArray[np.uint8] = np.tile(EMPTY_TILE_ARR, (ver_reps, hor_reps, 1))
        # Swaps columns and rows, because pygame uses it like this
        tiles = np.where(empty_tiles_mask, empty_tiles, tiles).transpose((1, 0, 2))

        # Having a version where 1 tile = 1 pixel is better for scaling
        small_preview_img: pg.Surface = pg.surfarray.make_surface(tiles)
        self._resize_preview(small_preview_img)

    def _move_with_keys(self, timed_keys: list[int]) -> None:
        """
        Moves the selected object with keys.

        Args:
            timed keys
        """

        cursor_x: int
        closest_char_i: int
        if pg.K_UP in timed_keys:
            self._selection_i = 0
            cursor_x = self._h_slider.input_box.cursor_rect.x
            closest_char_i = self._w_slider.input_box.text_label.get_closest_to(cursor_x)
            self._w_slider.input_box.bounded_set_cursor_i(closest_char_i)
        if pg.K_DOWN in timed_keys:
            self._selection_i = 1
            cursor_x = self._w_slider.input_box.cursor_rect.x
            closest_char_i = self._h_slider.input_box.text_label.get_closest_to(cursor_x)
            self._h_slider.input_box.bounded_set_cursor_i(closest_char_i)

    def _upt_sliders(self, mouse: Mouse, keyboard: Keyboard) -> None:
        """
        Updates sliders and selection.

        Args:
            mouse, keyboard
        """

        selected_obj: SelectionType = (self._w_slider, self._h_slider)[self._selection_i]

        is_w_slider_clicked: bool = self._w_slider.upt(mouse, keyboard, MAX_DIM, selected_obj)
        if is_w_slider_clicked:
            self._selection_i = 0

        is_h_slider_clicked: bool = self._h_slider.upt(mouse, keyboard, MAX_DIM, selected_obj)
        if is_h_slider_clicked:
            self._selection_i = 1

    def _adjust_opp_slider(self, has_grid_w_changed: bool) -> None:
        """
        Adjusts the opposite slider when keeping their ratio.

        Args:
            grid width changed flag
        """

        ptr_opp_slider: NumSlider
        uncapped_value: int
        slider_text: str
        if has_grid_w_changed:
            ptr_opp_slider = self._h_slider
            uncapped_value = round(self._w_slider.value * self.values_ratio.w)
            slider_text = self._w_slider.input_box.text_label.text
        else:
            ptr_opp_slider = self._w_slider
            uncapped_value = round(self._h_slider.value * self.values_ratio.h)
            slider_text = self._h_slider.input_box.text_label.text
        ptr_opp_slider.value = max(min(uncapped_value, 256), 1)

        opp_slider_text: str = str(ptr_opp_slider.value)
        if not slider_text and ptr_opp_slider.value == 1:
            opp_slider_text = ""

        ptr_opp_slider.input_box.text_label.set_text(opp_slider_text)
        ptr_opp_slider.input_box.bounded_set_cursor_i(None)

    def upt(self, mouse: Mouse, keyboard: Keyboard) -> tuple[bool, bool, Size]:
        """
        Allows selecting a grid area with 2 sliders and view its preview.

        Args:
            mouse, keyboard
        Returns:
            exiting flag, confirming flag, size (can be None)
        """

        if keyboard.timed:
            self._move_with_keys(keyboard.timed)

        prev_w_slider_text: str = self._w_slider.input_box.text_label.text
        prev_h_slider_text: str = self._h_slider.input_box.text_label.text
        self._upt_sliders(mouse, keyboard)

        has_grid_w_changed: bool = self._w_slider.input_box.text_label.text != prev_w_slider_text
        has_grid_h_changed: bool = self._h_slider.input_box.text_label.text != prev_h_slider_text
        if has_grid_w_changed or has_grid_h_changed:
            if self.checkbox.is_checked:
                self._adjust_opp_slider(has_grid_w_changed)
            self._get_preview()

        is_shortcutting: bool = keyboard.is_ctrl_on and pg.K_k in keyboard.timed
        should_get_size_ratio: bool = self.checkbox.upt(mouse, is_shortcutting)
        if should_get_size_ratio:
            self.values_ratio.w = self._h_slider.value / self._w_slider.value
            self.values_ratio.h = self._w_slider.value / self._h_slider.value

        is_exiting: bool
        is_confirming: bool
        is_exiting, is_confirming = self._base_upt(mouse, keyboard.pressed)

        return is_exiting, is_confirming, Size(self._w_slider.value, self._h_slider.value)
