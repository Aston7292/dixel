"""Tests for the utils file."""

from unittest import TestCase, mock
from random import SystemRandom
from math import ceil
from typing import Final

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.utils import (
    Point, RectPos, Size, Ratio, ObjInfo, MouseInfo, get_img, get_pixels, add_border, resize_obj
)
from src.type_utils import PosPair, SizePair, Color

RNG: Final[SystemRandom] = SystemRandom()


class ParentObj:
    """Class to test the set active method on objects info."""

    def __init__(self) -> None:
        """Creates the objects info."""

        self.objs_info: list[ObjInfo] = [ObjInfo(1)]


class TestUtils(TestCase):
    """Tests for the utils file."""

    @mock.patch.object(pg.image, "load", autospec=True)
    def test_load_img_from_path(self, mock_load: mock.Mock) -> None:
        """Tests the load_img_from_path function, mocks the pygame.image.load function."""

        mock_surface: mock.Mock = mock.create_autospec(pg.Surface, spec_set=True)
        mock_load.return_value = mock_surface

        get_img("test.png")
        mock_surface.convert_alpha.assert_called_once_with()

    def test_get_pixels(self) -> None:
        """Tests the get_pixels function."""

        img: pg.Surface = pg.Surface((50, 51), pg.SRCALPHA)
        img.fill((255, 0, 0))
        img.set_at((0, 1), (255, 0, 1))

        pixels: NDArray[np.uint8] = get_pixels(img.copy())
        for y in range(img.get_height()):
            for x in range(img.get_width()):
                self.assertEqual(tuple(pixels[y, x]), img.get_at((x, y)))

    def test_add_border(self) -> None:
        """Tests the add_border function."""

        color: Color = (0, 0, 1)

        img: pg.Surface = pg.Surface((10, 11))
        img_with_border: pg.Surface = add_border(img, color)

        self.assertEqual(img_with_border.get_at((0, 0)), color)
        self.assertEqual(img_with_border.get_at((0, 9)), color)
        self.assertEqual(img_with_border.get_at((9, 0)), color)
        self.assertEqual(img_with_border.get_at((9, 9)), color)

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

        for _ in range(100):
            # Check gaps

            x: int = RNG.randint(0, 500)
            y: int = RNG.randint(0, 500)
            w: float = RNG.uniform(0, 100)
            h: float = RNG.uniform(0, 100)
            win_ratio: Ratio = Ratio(RNG.uniform(0, 5), RNG.uniform(0, 5))

            resized_xy, resized_wh = resize_obj(RectPos(x, y, "topleft"), w, h, win_ratio)

            expected_sum_x: int = round((x * win_ratio.w) + (w * win_ratio.w))
            expected_sum_y: int = round((y * win_ratio.h) + (h * win_ratio.h))
            self.assertGreaterEqual(resized_xy[0] + resized_wh[0], expected_sum_x)
            self.assertGreaterEqual(resized_xy[1] + resized_wh[1], expected_sum_y)

    def test_point(self) -> None:
        """Tests the Point dataclass."""

        point: Point = Point(0, 1)

        self.assertEqual(point.x, 0)
        self.assertEqual(point.y, 1)

    def test_rect_pos(self) -> None:
        """Tests the RectPos dataclass."""

        pos: RectPos = RectPos(0, 1, "topleft")

        self.assertEqual(pos.x, 0)
        self.assertEqual(pos.y, 1)
        self.assertEqual(pos.coord_type, "topleft")

    def test_size(self) -> None:
        """Tests the Size dataclass."""

        size: Size = Size(0, 1)

        self.assertEqual(size.w, 0)
        self.assertEqual(size.h, 1)

    def test_ratio(self) -> None:
        """Tests the Ratio dataclass."""

        ratio: Ratio = Ratio(0, 1)

        self.assertEqual(ratio.w, 0)
        self.assertEqual(ratio.h, 1)

    def test_obj_info(self) -> None:
        """Tests the ObjInfo dataclass."""

        parent_obj: ParentObj = ParentObj()
        parent_obj_info: ObjInfo = ObjInfo(parent_obj)

        self.assertIs(parent_obj_info.obj, parent_obj)
        self.assertTrue(parent_obj_info.is_active)

        copy_parent_obj_info: ObjInfo = ObjInfo(ParentObj())
        copy_parent_obj_info.set_active(False)

        self.assertFalse(copy_parent_obj_info.is_active)
        sub_obj_info: ObjInfo = copy_parent_obj_info.obj.objs_info[0]
        self.assertFalse(sub_obj_info.is_active)

    def test_mouse_info(self) -> None:
        """Tests the MouseInfo dataclass."""

        mouse_info: MouseInfo = MouseInfo(0, 1, (False,) * 3, (False,) * 5, 1)

        self.assertEqual(mouse_info.x, 0)
        self.assertEqual(mouse_info.y, 1)
        self.assertTupleEqual(mouse_info.pressed, (False,) * 3)
        self.assertTupleEqual(mouse_info.released, (False,) * 5)
        self.assertEqual(mouse_info.scroll_amount, 1)
