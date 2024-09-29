"""
Tests for the utils file
"""

import pygame as pg
import unittest
from unittest import mock
import numpy as np
from numpy.typing import NDArray

from src.utils import Point, RectPos, Size, ObjInfo, MouseInfo, load_img, add_border, get_pixels


class ParentObj:
    """
    Class to test the set active method on sub objects
    """

    def __init__(self) -> None:
        """
        Creates the objects info
        """

        self.objs_info: list[ObjInfo] = [ObjInfo("obj_1", 1), ObjInfo("obj_2", 2)]


class TestUtils(unittest.TestCase):
    """
    Tests for the utils file
    """

    @mock.patch.object(pg.image, 'load')
    def test_load_img(self, mock_load: mock.Mock) -> None:
        """
        Tests the load_img method (mocks the pygame.image.load method)
        """

        mock_surf: mock.Mock = mock.Mock(spec=pg.Surface)
        mock_load.return_value = mock_surf

        load_img("test.png")
        mock_surf.convert_alpha.assert_called_once()

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

    def test_get_pixels(self) -> None:
        """
        Tests the get_pixels method
        """

        img: pg.Surface = pg.Surface((50, 51), pg.SRCALPHA)
        img.fill((255, 0, 0, 0))
        img.set_at((0, 1), (255, 0, 1))

        pixels_rgb: NDArray[np.uint8] = pg.surfarray.pixels3d(img)
        pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img)
        expected_pixels: NDArray[np.uint8] = np.dstack((pixels_rgb, pixels_alpha))
        expected_pixels = np.transpose(expected_pixels, (1, 0, 2))

        self.assertTrue(np.array_equal(get_pixels(img), expected_pixels))

    def test_point(self) -> None:
        """
        Tests the Point dataclass
        """

        point: Point = Point(0, 1)

        self.assertEqual(point.x, 0)
        self.assertEqual(point.y, 1)
        self.assertTupleEqual(point.xy, (0, 1))

    def test_rect_pos(self) -> None:
        """
        Tests the RectPos dataclass
        """

        pos: RectPos = RectPos(0.0, 1.0, 'topleft')

        self.assertEqual(pos.x, 0.0)
        self.assertEqual(pos.y, 1.0)
        self.assertEqual(pos.coord_type, 'topleft')
        self.assertTupleEqual(pos.xy, (0.0, 1.0))

    def test_size(self) -> None:
        """
        Tests the Size dataclass
        """

        size: Size = Size(0, 1)

        self.assertEqual(size.w, 0)
        self.assertEqual(size.h, 1)
        self.assertTupleEqual(size.wh, (0, 1))

    def test_obj_info(self) -> None:
        """
        Tests the ObjInfo dataclass
        """

        parent_obj: ParentObj = ParentObj()
        parent_obj_info: ObjInfo = ObjInfo("obj", parent_obj)

        self.assertEqual(parent_obj_info.name, "obj")
        self.assertIs(parent_obj_info.obj, parent_obj)
        self.assertTrue(parent_obj_info.is_active)

        parent_obj_info.set_active(False)
        objs_info: list[ObjInfo] = [parent_obj_info]
        while objs_info:
            obj_info: ObjInfo = objs_info.pop()
            self.assertFalse(obj_info.is_active)

            if hasattr(obj_info.obj, "objs_info"):
                objs_info.extend(obj_info.obj.objs_info)

    def test_mouse_info(self) -> None:
        """
        Tests the MouseInfo dataclass
        """

        mouse_info: MouseInfo = MouseInfo(0, 1, (False,) * 3, (False,) * 5)

        self.assertEqual(mouse_info.x, 0)
        self.assertEqual(mouse_info.y, 1)
        self.assertTupleEqual(mouse_info.pressed, (False,) * 3)
        self.assertTupleEqual(mouse_info.released, (False,) * 5)
        self.assertTupleEqual(mouse_info.xy, (0, 1))
