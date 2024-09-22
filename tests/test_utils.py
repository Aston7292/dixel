"""
Tests for the utils file
"""

import pygame as pg
import unittest

from src.utils import Point, RectPos, Size, ObjInfo, MouseInfo, load_img, add_border


class ParentObj:
    """
    Class to test the set active method on sub objects
    """

    def __init__(self) -> None:
        """
        Creates the objects info
        """

        self.objs_info: list[ObjInfo] = [ObjInfo('obj1', 1), ObjInfo('obj2', 2)]


class TestUtils(unittest.TestCase):
    """
    Tests for the utils file
    """

    def test_load_img(self) -> None:
        """
        Tests the load image method
        """

        img: pg.Surface = load_img('test.png')

        self.assertTrue(bool(img.get_flags() & pg.SRCALPHA))

    def test_add_border(self) -> None:
        """
        Tests the add border method
        """

        img: pg.Surface = pg.Surface((10, 10))
        img_with_border: pg.Surface = add_border(img, (0, 0, 1))

        self.assertEqual(img_with_border.get_at((0, 0)), (0, 0, 1))
        self.assertEqual(img_with_border.get_at((0, 9)), (0, 0, 1))
        self.assertEqual(img_with_border.get_at((9, 0)), (0, 0, 1))
        self.assertEqual(img_with_border.get_at((9, 9)), (0, 0, 1))

    def test_point(self) -> None:
        """
        Tests the point dataclass
        """

        point: Point = Point(0, 1)

        self.assertEqual(point.x, 0)
        self.assertEqual(point.y, 1)
        self.assertEqual(point.xy, (0, 1))

    def test_rect_pos(self) -> None:
        """
        Tests the rect position dataclass
        """

        pos: RectPos = RectPos(0, 1, 'topleft')

        self.assertEqual(pos.x, 0)
        self.assertEqual(pos.y, 1)
        self.assertEqual(pos.coord_type, 'topleft')
        self.assertEqual(pos.xy, (0, 1))

    def test_size(self) -> None:
        """
        Tests the size dataclass
        """

        size: Size = Size(0, 1)

        self.assertEqual(size.w, 0)
        self.assertEqual(size.h, 1)
        self.assertEqual(size.wh, (0, 1))

    def test_obj_info(self) -> None:
        """
        Tests the object info dataclass
        """

        parent_obj: ParentObj = ParentObj()
        parent_obj_info: ObjInfo = ObjInfo('obj', parent_obj)

        self.assertEqual(parent_obj_info.name, 'obj')
        self.assertEqual(parent_obj_info.obj, parent_obj)
        self.assertEqual(parent_obj_info.is_active, True)

        parent_obj_info.set_active(False)
        objs_info: list[ObjInfo] = [parent_obj_info]
        while objs_info:
            obj_info: ObjInfo = objs_info.pop()
            self.assertEqual(obj_info.is_active, False)

            if hasattr(obj_info.obj, 'objs_info'):
                objs_info.extend(obj_info.obj.objs_info)

    def test_mouse_info(self) -> None:
        """
        Tests the mouse info dataclass
        """

        mouse_info: MouseInfo = MouseInfo(0, 1, (False,) * 3, (False,) * 5)

        self.assertEqual(mouse_info.x, 0)
        self.assertEqual(mouse_info.y, 1)
        self.assertEqual(mouse_info.pressed, (False,) * 3)
        self.assertEqual(mouse_info.released, (False,) * 5)
        self.assertEqual(mouse_info.xy, (0, 1))


if __name__ == '__main__':
    unittest.main()
