"""Tests for the objs_utils file."""

from unittest import TestCase, mock
from unittest.mock import Mock
from typing import Self

import src.obj_utils as objs
from src.obj_utils import ObjInfo, resize_obj, rec_move_rect
from src.type_utils import XY, WH, RectPos

from tests.utils import DummyUIElement


class TestObjsUtils(TestCase):
    """Tests for the objs_utils file."""

    @mock.patch.object(DummyUIElement, "leave", autospec=True)
    @mock.patch.object(DummyUIElement, "enter", autospec=True)
    def test_rec_set_active(self: Self, mock_enter: Mock, mock_leave: Mock) -> None:
        """Tests the ObjInfo.rec_set_active_method (mocks enter and leave from DummyUIElement)."""

        parent_info: ObjInfo = ObjInfo(DummyUIElement())
        child_info: ObjInfo  = ObjInfo(DummyUIElement())
        parent_info.obj.objs_info.append(child_info)

        objs.state_active_objs = [parent_info.obj, child_info.obj]
        parent_info.rec_set_active(False)
        self.assertFalse(parent_info.is_active)
        self.assertFalse(child_info.is_active)
        mock_leave.assert_has_calls((
            mock.call(parent_info.obj),
            mock.call(child_info.obj)
        ))
        self.assertListEqual(objs.state_active_objs, [])

        objs.state_active_objs = []
        parent_info.rec_set_active(True)
        mock_enter.assert_has_calls((
            mock.call(parent_info.obj),
            mock.call(child_info.obj)
        ))
        self.assertListEqual(objs.state_active_objs, [parent_info.obj, child_info.obj])

    def test_resize_obj(self: Self) -> None:
        """Tests the resize_obj function."""

        res: tuple[XY, WH] = resize_obj(
            RectPos(1, 2, "topleft"), init_w=3, init_h=4,
            win_w_ratio=2, win_h_ratio=3
        )
        self.assertTupleEqual(
            res,
            ((2, 6), (6, 12))
        )

        res = resize_obj(
            RectPos(1, 2, "topleft"), init_w=3, init_h=4,
            win_w_ratio=2, win_h_ratio=3, should_keep_wh_ratio=True
        )
        self.assertTupleEqual(
            res,
            ((2, 6), (6, 8))
        )

    @mock.patch.object(DummyUIElement, "move_rect", autospec=True)
    def test_rec_move_rect(self: Self, mock_move_rect: Mock) -> None:
        """Tests the rec_move_rect function (mocks DummyUIElement.move_rect)."""

        parent_info: ObjInfo = ObjInfo(DummyUIElement())
        child_info: ObjInfo  = ObjInfo(DummyUIElement())
        parent_info.obj.objs_info.append(child_info)
        rec_move_rect(parent_info.obj, 1, 2, 3, 4)

        mock_move_rect.assert_has_calls((
            mock.call(parent_info.obj, 1, 2, 3, 4),
            mock.call(child_info.obj, 1, 2, 3, 4)
        ))
