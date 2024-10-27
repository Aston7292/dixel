"""
Tests for the utils file
"""

import pygame as pg
import unittest
from unittest import mock
import numpy as np
from numpy.typing import NDArray
from random import SystemRandom
from typing import Final

from src.utils import (
    Point, RectPos, Size, ObjInfo, MouseInfo, get_img, get_pixels, add_border, resize_obj
)
from src.type_utils import ColorType

RNG: Final[SystemRandom] = SystemRandom()


class ParentObj:
    """
    Class to test the set active method on sub objects
    """

    def __init__(self) -> None:
        """
        Creates the objects info
        """

        self.objs_info: list[ObjInfo] = [ObjInfo(1)]


class TestUtils(unittest.TestCase):
    """
    Tests for the utils file
    """

    @mock.patch.object(pg.image, 'load')
    def test_load_img_from_path(self, mock_load: mock.Mock) -> None:
        """
        Tests the load_img_from_path method, mocks the pygame.image.load method
        """

        mock_surf: mock.Mock = mock.Mock(spec=pg.Surface)
        mock_load.return_value = mock_surf

        get_img("test.png")
        mock_surf.convert_alpha.assert_called_once()

    def test_get_pixels(self) -> None:
        """
        Tests the get_pixels method
        """

        img: pg.Surface = pg.Surface((50, 51), pg.SRCALPHA)
        img.fill((255, 0, 0, 0))
        img.set_at((0, 1), (255, 0, 1))

        pixels: NDArray[np.uint8] = get_pixels(img)
        for y in range(img.get_height()):
            for x in range(img.get_width()):
                pixel: ColorType = tuple(pixels[y, x])
                self.assertEqual(pixel, img.get_at((x, y)))

    def test_add_border(self) -> None:
        """
        Tests the add_border method
        """

        img: pg.Surface = pg.Surface((10, 11))
        img_with_border: pg.Surface = add_border(img, (0, 0, 1))

        self.assertEqual(img_with_border.get_at((0, 0)), (0, 0, 1))
        self.assertEqual(img_with_border.get_at((0, 9)), (0, 0, 1))
        self.assertEqual(img_with_border.get_at((9, 0)), (0, 0, 1))
        self.assertEqual(img_with_border.get_at((9, 9)), (0, 0, 1))

    def test_resize_obj(self) -> None:
        """
        Tests the resize_obj method
        """

        init_pos: RectPos = RectPos(1, 2, 'topleft')

        resized_pos: tuple[int, int]
        resized_size: tuple[int, int]
        resized_pos, resized_size = resize_obj(init_pos, 3.0, 4.0, 2.1, 3.1)

        # Also makes round and ceil were used
        self.assertTupleEqual(resized_pos, (2, 6))
        self.assertTupleEqual(resized_size, (7, 13))

        resized_pos, resized_size = resize_obj(init_pos, 3.0, 4.0, 2.6, 3.4, True)
        self.assertTupleEqual(resized_pos, (3, 7))
        self.assertTupleEqual(resized_size, (8, 11))

        for _ in range(100):
            x: int = RNG.randint(0, 500)
            y: int = RNG.randint(0, 500)
            w: float = RNG.uniform(0.0, 100.0)
            h: float = RNG.uniform(0.0, 100.0)
            ratio_w: float = RNG.uniform(0.0, 5.0)
            ratio_h: float = RNG.uniform(0.0, 5.0)

            resized_pos, resized_size = resize_obj(
                RectPos(x, y, 'topleft'), w, h, ratio_w, ratio_h
            )

            # Check gaps
            expected_sum_x: int = round((x * ratio_w) + (w * ratio_w))
            expected_sum_y: int = round((y * ratio_h) + (h * ratio_h))
            self.assertGreaterEqual(resized_pos[0] + resized_size[0], expected_sum_x)
            self.assertGreaterEqual(resized_pos[1] + resized_size[1], expected_sum_y)

    def test_point(self) -> None:
        """
        Tests the Point dataclass
        """

        point: Point = Point(0, 1)

        self.assertEqual(point.x, 0)
        self.assertEqual(point.y, 1)
        self.assertTupleEqual(point.xy, (point.x, point.y))

    def test_rect_pos(self) -> None:
        """
        Tests the RectPos dataclass
        """

        pos: RectPos = RectPos(0, 1, 'topleft')

        self.assertEqual(pos.x, 0)
        self.assertEqual(pos.y, 1)
        self.assertEqual(pos.coord_type, 'topleft')
        self.assertTupleEqual(pos.xy, (pos.x, pos.y))

    def test_size(self) -> None:
        """
        Tests the Size dataclass
        """

        size: Size = Size(0, 1)

        self.assertEqual(size.w, 0)
        self.assertEqual(size.h, 1)
        self.assertTupleEqual(size.wh, (size.w, size.h))

    def test_obj_info(self) -> None:
        """
        Tests the ObjInfo dataclass
        """

        parent_obj: ParentObj = ParentObj()
        parent_obj_info: ObjInfo = ObjInfo(parent_obj)

        self.assertIs(parent_obj_info.obj, parent_obj)
        self.assertTrue(parent_obj_info.is_active)

        parent_obj_info.set_active(False)
        self.assertFalse(parent_obj_info.is_active)
        child_obj_info: ObjInfo = parent_obj.objs_info[0]
        self.assertFalse(child_obj_info.is_active)

    def test_mouse_info(self) -> None:
        """
        Tests the MouseInfo dataclass
        """

        mouse_info: MouseInfo = MouseInfo(0, 1, (False,) * 3, (False,) * 5)

        self.assertEqual(mouse_info.x, 0)
        self.assertEqual(mouse_info.y, 1)
        self.assertTupleEqual(mouse_info.pressed, (False,) * 3)
        self.assertTupleEqual(mouse_info.released, (False,) * 5)
        self.assertTupleEqual(mouse_info.xy, (mouse_info.x, mouse_info.y))
