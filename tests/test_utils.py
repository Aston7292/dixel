"""Tests for the utils file."""

from unittest import TestCase, mock
from unittest.mock import Mock
from pathlib import Path
from random import SystemRandom
from math import ceil
from typing import Final

import pygame as pg
from pygame import SRCALPHA
import numpy as np
from numpy.typing import NDArray

from src.classes.devices import Mouse, Keyboard

from src.utils import (
    Point, RectPos, Size, ObjInfo, get_pixels, add_border, resize_obj, rec_resize, rec_move_rect
)
from src.type_utils import XY, WH, RGBAColor


class SubObj:
    """Class to test objects info."""

    def __init__(self) -> None:
        """Creates the initial position."""

        self.init_pos: RectPos = RectPos(0, 1, "")

    def resize(self, _win_ratio_w: float, _win_ratio_h: float) -> None:
        """Empty method to test the rec_resize function."""

    def move_rect(
            self, _init_x: int, _init_y: int, _win_ratio_w: float, _win_ratio_h: float
    ) -> None:
        """Empty method to test the rec_move_rect function."""


class MainObj:
    """Class to test objects info."""

    def __init__(self) -> None:
        """Creates the initial position and objects info."""

        self.init_pos: RectPos = RectPos(0, 1, "")
        self.objs_info: list[ObjInfo] = [ObjInfo(SubObj())]

    def resize(self, _win_ratio_w: float, _win_ratio_h: float) -> None:
        """Empty method to test the rec_resize function."""

    def move_rect(
            self, init_x: int, init_y: int, _win_ratio_w: float, _win_ratio_h: float
    ) -> None:
        """Method to test the rec_move_rect function."""

        self.init_pos.x, self.init_pos.y = init_x, init_y


class TestUtils(TestCase):
    """Tests for the utils file."""

    def test_point(self) -> None:
        """Tests the Point dataclass."""

        point: Point = Point(0, 1)
        self.assertEqual(point.x, 0)
        self.assertEqual(point.y, 1)

    def test_size(self) -> None:
        """Tests the Size dataclass."""

        size: Size = Size(0, 1)
        self.assertEqual(size.w, 0)
        self.assertEqual(size.h, 1)

    def test_rect_pos(self) -> None:
        """Tests the RectPos dataclass."""

        pos: RectPos = RectPos(0, 1, "")
        self.assertEqual(pos.x, 0)
        self.assertEqual(pos.y, 1)
        self.assertEqual(pos.coord_type, "")

    def test_obj_info(self) -> None:
        """Tests the ObjInfo dataclass."""

        main_obj: MainObj = MainObj()
        main_obj_info: ObjInfo = ObjInfo(main_obj)
        self.assertIs(main_obj_info.obj, main_obj)
        self.assertTrue(main_obj_info.is_active)

        main_obj_info.set_active(False)
        self.assertFalse(main_obj_info.is_active)
        sub_obj_info: ObjInfo = main_obj_info.obj.objs_info[0]
        self.assertFalse(sub_obj_info.is_active)

    def test_mouse(self) -> None:
        """Tests the Mouse dataclass."""

        mouse: Mouse = Mouse(0, 1, [False] * 3, [False] * 3, 2, None)
        self.assertEqual(mouse.x, 0)
        self.assertEqual(mouse.y, 1)
        self.assertListEqual(mouse.pressed, [False] * 3)
        self.assertListEqual(mouse.released, [False] * 3)
        self.assertEqual(mouse.scroll_amount, 2)
        self.assertIsNone(mouse.hovered_obj)

    def test_keyboard(self) -> None:
        """Tests the keyboard dataclass."""

        keyboard: Keyboard = Keyboard([1], [2], False, True, False, True)
        self.assertListEqual(keyboard.pressed, [1])
        self.assertListEqual(keyboard.timed, [2])
        self.assertFalse(keyboard.is_ctrl_on)
        self.assertTrue(keyboard.is_shift_on)
        self.assertFalse(keyboard.is_alt_on)
        self.assertTrue(keyboard.is_numpad_on)

    def test_get_pixels(self) -> None:
        """Tests the get_pixels function."""

        x: int
        y: int

        img: pg.Surface = pg.Surface((50, 51), SRCALPHA)
        img.fill((255, 0, 0))
        img.set_at((0, 1), (255, 0, 1))

        pixels: NDArray[np.uint8] = get_pixels(img.copy())
        img_h: int = img.get_height()
        for x in range(img.get_width()):
            for y in range(img_h):
                rgba_color: RGBAColor = tuple(pixels[x, y])
                expected_rgba_color: RGBAColor = tuple(img.get_at((x, y)))
                self.assertTupleEqual(rgba_color, expected_rgba_color)

    def test_add_border(self) -> None:
        """Tests the add_border function."""

        expected_rgba_color: RGBAColor = (0, 0, 1, 255)

        img: pg.Surface = pg.Surface((10, 11))
        img_with_border: pg.Surface = add_border(img, expected_rgba_color)

        rgba_color_topleft: RGBAColor = tuple(img_with_border.get_at((0, 0)))
        rgba_color_topright: RGBAColor = tuple(img_with_border.get_at((9, 0)))
        rgba_color_bottomleft: RGBAColor = tuple(img_with_border.get_at((0, 9)))
        rgba_color_bottomright: RGBAColor = tuple(img_with_border.get_at((9, 9)))
        self.assertTupleEqual(rgba_color_topleft, expected_rgba_color)
        self.assertTupleEqual(rgba_color_topright, expected_rgba_color)
        self.assertTupleEqual(rgba_color_bottomleft, expected_rgba_color)
        self.assertTupleEqual(rgba_color_bottomright, expected_rgba_color)

    def test_resize_obj(self) -> None:
        """Tests the resize_obj function."""

        resized_xy: XY
        resized_wh: WH
        _i: int
        x: int
        y: int
        w: float
        h: float
        win_w_ratio: float
        win_h_ratio: float

        init_pos: RectPos = RectPos(1, 2, "")

        resized_xy, resized_wh = resize_obj(init_pos, 3, 4, 2.1, 3.2)
        self.assertTupleEqual(resized_xy, (round(1 * 2.1), round(2 * 3.2)))
        self.assertTupleEqual(resized_wh, (ceil(3 * 2.1), ceil(4 * 3.2)))

        resized_xy, resized_wh = resize_obj(init_pos, 3, 4, 2.6, 3.4, True)
        self.assertTupleEqual(resized_xy, (round(1 * 2.6), round(2 * 3.4)))
        self.assertTupleEqual(resized_wh, (ceil(3 * 2.6), ceil(4 * 2.6)))

        rng: SystemRandom = SystemRandom()
        for _i in range(1_000):
            # Check gaps

            x, y = rng.randint(0, 500), rng.randint(0, 500)
            w, h = rng.uniform(0, 100), rng.uniform(0, 100)
            win_w_ratio, win_h_ratio = rng.uniform(0, 5), rng.uniform(0, 5)

            init_pos.x, init_pos.y = x, y
            resized_xy, resized_wh = resize_obj(init_pos, w, h, win_w_ratio, win_h_ratio)

            expected_sum_x: int = round(x * win_w_ratio + w * win_w_ratio)
            expected_sum_y: int = round(y * win_h_ratio + h * win_h_ratio)
            self.assertGreaterEqual(resized_xy[0] + resized_wh[0], expected_sum_x)
            self.assertGreaterEqual(resized_xy[1] + resized_wh[1], expected_sum_y)

    @mock.patch.object(SubObj, "resize", autospec=True)
    @mock.patch.object(MainObj, "resize", autospec=True)
    def test_rec_resize(self, mock_main_obj_resize: Mock, mock_sub_obj_resize: Mock) -> None:
        """Tests the rec_resize function, mocks MainObj.resize and SubObj.resize."""

        obj: MainObj = MainObj()
        rec_resize([obj], 0, 1)

        mock_main_obj_resize.assert_called_once_with(obj, 0, 1)
        mock_sub_obj_resize.assert_called_once_with(obj.objs_info[0].obj, 0, 1)

    @mock.patch.object(SubObj, "move_rect", autospec=True)
    @mock.patch.object(MainObj, "move_rect", autospec=True, wraps=MainObj.move_rect)
    def test_rec_move_rect(
            self, mock_main_obj_move_rect: Mock, mock_sub_obj_move_rect: Mock
    ) -> None:
        """Tests the rec_move_rect function, mocks MainObj.move_rect and SubObj.move_rect."""

        obj: MainObj = MainObj()
        sub_obj: SubObj = obj.objs_info[0].obj
        sub_obj_x: int = sub_obj.init_pos.x + 2 - obj.init_pos.x
        sub_obj_y: int = sub_obj.init_pos.y + 3 - obj.init_pos.y
        rec_move_rect(obj, 2, 3, 0, 1)

        mock_main_obj_move_rect.assert_called_once_with(obj, 2, 3, 0, 1)
        mock_sub_obj_move_rect.assert_called_once_with(sub_obj, sub_obj_x, sub_obj_y, 0, 1)
