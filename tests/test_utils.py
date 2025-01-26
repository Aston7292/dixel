"""Tests for the utils file."""

from unittest import TestCase, mock
from pathlib import Path
from random import SystemRandom
from math import ceil
from typing import Final

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.utils import (
    Point, RectPos, Size, Ratio, ObjInfo, Mouse, Keyboard,
    get_img, get_pixels, add_border, resize_obj, rec_resize, rec_move_rect
)
from src.type_utils import PosPair, SizePair, Color

RNG: Final[SystemRandom] = SystemRandom()


class SubObj:
    """Class to test objects info."""

    def __init__(self) -> None:
        """Creates the initial position."""

        self.init_pos: RectPos = RectPos(0, 1, "topleft")

    def resize(self, _: Ratio) -> None:
        """Empty method to test the rec_resize function."""

    def move_rect(self, _: PosPair, __: Ratio) -> None:
        """Empty method to test the rec_move_rect function."""


class MainObj:
    """Class to test objects info."""

    def __init__(self) -> None:
        """Creates the initial position and objects info."""

        self.init_pos: RectPos = RectPos(0, 1, "topleft")
        self.objs_info: list[ObjInfo] = [ObjInfo(SubObj())]

    def resize(self, _: Ratio) -> None:
        """Empty method to test the rec_resize function."""

    def move_rect(self, init_xy: PosPair, _: Ratio) -> None:
        """Method to test the rec_move_rect function."""

        self.init_pos.xy = init_xy


class TestUtils(TestCase):
    """Tests for the utils file."""

    def test_point(self) -> None:
        """Tests the Point dataclass."""

        point: Point = Point(0, 1)
        self.assertEqual(point.x, 0)
        self.assertEqual(point.y, 1)
        self.assertTupleEqual(point.xy, (0, 1))

        point.xy = (2, 3)
        self.assertTupleEqual(point.xy, (2, 3))

    def test_size(self) -> None:
        """Tests the Size dataclass."""

        size: Size = Size(0, 1)
        self.assertEqual(size.w, 0)
        self.assertEqual(size.h, 1)
        self.assertTupleEqual(size.wh, (0, 1))

        size.wh = (2, 3)
        self.assertTupleEqual(size.wh, (2, 3))

    def test_rect_pos(self) -> None:
        """Tests the RectPos dataclass."""

        pos: RectPos = RectPos(0, 1, "topleft")
        self.assertEqual(pos.x, 0)
        self.assertEqual(pos.y, 1)
        self.assertEqual(pos.coord_type, "topleft")
        self.assertTupleEqual(pos.xy, (0, 1))

        pos.xy = (2, 3)
        self.assertTupleEqual(pos.xy, (2, 3))

    def test_ratio(self) -> None:
        """Tests the Ratio dataclass."""

        ratio: Ratio = Ratio(0, 1)
        self.assertEqual(ratio.w, 0)
        self.assertEqual(ratio.h, 1)
        self.assertTupleEqual(ratio.wh, (0, 1))

        ratio.wh = (2, 3)
        self.assertTupleEqual(ratio.wh, (2, 3))

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

        mouse: Mouse = Mouse(0, 1, (False,) * 3, (False,) * 5, 2, None)
        self.assertEqual(mouse.x, 0)
        self.assertEqual(mouse.y, 1)
        self.assertTupleEqual(mouse.pressed, (False,) * 3)
        self.assertTupleEqual(mouse.released, (False,) * 5)
        self.assertEqual(mouse.scroll_amount, 2)
        self.assertIsNone(mouse.hovered_obj)
        self.assertTupleEqual(mouse.xy, (0, 1))

        mouse.xy = (2, 3)
        self.assertTupleEqual(mouse.xy, (2, 3))

    def test_keyboard(self) -> None:
        """Tests the keyboard dataclass."""

        keyboard: Keyboard = Keyboard([1], [2], False, True, False, True)
        self.assertListEqual(keyboard.pressed, [1])
        self.assertListEqual(keyboard.timed, [2])
        self.assertFalse(keyboard.is_ctrl_on)
        self.assertTrue(keyboard.is_shift_on)
        self.assertFalse(keyboard.is_alt_on)
        self.assertTrue(keyboard.is_numpad_on)

    @mock.patch.object(pg.image, "load", autospec=True)
    def test_load_img_from_path(self, mock_load: mock.Mock) -> None:
        """Tests the load_img_from_path function, mocks pygame.image.load."""

        mock_surface: mock.Mock = mock.create_autospec(pg.Surface, spec_set=True)
        mock_load.return_value = mock_surface
        mock_convert_alpha: mock.Mock = mock_surface.convert_alpha

        get_img("test", "test.png")
        mock_load.assert_called_once_with(Path("test", "test.png"))
        mock_convert_alpha.assert_called_once_with()

    def test_get_pixels(self) -> None:
        """Tests the get_pixels function."""

        img: pg.Surface = pg.Surface((50, 51), pg.SRCALPHA)
        img.fill((255, 0, 0))
        img.set_at((0, 1), (255, 0, 1))

        pixels: NDArray[np.uint8] = get_pixels(img.copy())
        for y in range(img.get_height()):
            for x in range(img.get_width()):
                color: Color = list(pixels[y, x])
                expected_color: Color = list(img.get_at((x, y)))
                self.assertListEqual(color, expected_color)

    def test_add_border(self) -> None:
        """Tests the add_border function."""

        expected_color: Color = [0, 0, 1, 255]

        img: pg.Surface = pg.Surface((10, 11))
        img_with_border: pg.Surface = add_border(img, expected_color)

        color_topleft: Color = list(img_with_border.get_at((0, 0)))
        color_topright: Color = list(img_with_border.get_at((9, 0)))
        color_bottomleft: Color = list(img_with_border.get_at((0, 9)))
        color_bottomright: Color = list(img_with_border.get_at((9, 9)))
        self.assertListEqual(color_topleft, expected_color)
        self.assertListEqual(color_topright, expected_color)
        self.assertListEqual(color_bottomleft, expected_color)
        self.assertListEqual(color_bottomright, expected_color)

    def test_resize_obj(self) -> None:
        """Tests the resize_obj function."""

        init_pos: RectPos = RectPos(1, 2, "topleft")

        resized_xy: PosPair
        resized_wh: SizePair
        resized_xy, resized_wh = resize_obj(init_pos, 3, 4, Ratio(2.1, 3.2))
        self.assertTupleEqual(resized_xy, (round(1 * 2.1), round(2 * 3.2)))
        self.assertTupleEqual(resized_wh, (ceil(3 * 2.1), ceil(4 * 3.2)))

        resized_xy, resized_wh = resize_obj(init_pos, 3, 4, Ratio(2.6, 3.4), True)
        self.assertTupleEqual(resized_xy, (round(1 * 2.6), round(2 * 3.4)))
        self.assertTupleEqual(resized_wh, (ceil(3 * 2.6), ceil(4 * 2.6)))

        win_ratio: Ratio = Ratio(0, 0)
        for _ in range(100):
            # Check gaps

            x: int = RNG.randint(0, 500)
            y: int = RNG.randint(0, 500)
            w: float = RNG.uniform(0, 100)
            h: float = RNG.uniform(0, 100)
            win_ratio.wh = (RNG.uniform(0, 5), RNG.uniform(0, 5))

            init_pos.xy = (x, y)
            resized_xy, resized_wh = resize_obj(init_pos, w, h, win_ratio)

            expected_sum_x: int = round((x * win_ratio.w) + (w * win_ratio.w))
            expected_sum_y: int = round((y * win_ratio.h) + (h * win_ratio.h))
            self.assertGreaterEqual(resized_xy[0] + resized_wh[0], expected_sum_x)
            self.assertGreaterEqual(resized_xy[1] + resized_wh[1], expected_sum_y)

    @mock.patch.object(SubObj, "resize", autospec=True)
    @mock.patch.object(MainObj, "resize", autospec=True)
    def test_rec_resize(
            self, mock_main_obj_resize: mock.Mock, mock_sub_obj_resize: mock.Mock
    ) -> None:
        """Tests the rec_resize function, mocks MainObj.resize and SubObj.resize."""

        obj: MainObj = MainObj()
        rec_resize([obj], Ratio(0, 1))

        mock_main_obj_resize.assert_called_once_with(obj, Ratio(0, 1))
        mock_sub_obj_resize.assert_called_once_with(obj.objs_info[0].obj, Ratio(0, 1))

    @mock.patch.object(SubObj, "move_rect", autospec=True)
    @mock.patch.object(MainObj, "move_rect", autospec=True, wraps=MainObj.move_rect)
    def test_rec_move_rect(
            self, mock_main_obj_move_rect: mock.Mock, mock_sub_obj_move_rect: mock.Mock
    ) -> None:
        """Tests the rec_move_rect function, mocks MainObj.move_rect and SubObj.move_rect."""

        obj: MainObj = MainObj()
        win_ratio: Ratio = Ratio(0, 1)
        sub_obj: SubObj = obj.objs_info[0].obj
        sub_obj_x: int = sub_obj.init_pos.x + 2 - obj.init_pos.x
        sub_obj_y: int = sub_obj.init_pos.y + 3 - obj.init_pos.y
        rec_move_rect(obj, 2, 3, win_ratio)

        mock_main_obj_move_rect.assert_called_once_with(obj, (2, 3), win_ratio)
        mock_sub_obj_move_rect.assert_called_once_with(sub_obj, (sub_obj_x, sub_obj_y), win_ratio)
