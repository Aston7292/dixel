"""Tests for the checkbox_grid file."""

from unittest import TestCase, mock
from unittest.mock import Mock
from collections.abc import Iterator
from typing import Final

import pygame as pg
from pygame.locals import *

from src.classes.checkbox_grid import LockedCheckbox, CheckboxGrid
from src.classes.clickable import _Clickable
from src.classes.text_label import TextLabel
from src.classes.devices import _Mouse

from src.utils import RectPos, ObjInfo, add_border
from src.type_utils import CheckboxInfo
from src.consts import WHITE, ELEMENT_LAYER

from tests.utils import cmp_imgs

_OFF_IMG: Final[pg.Surface] = pg.Surface((10, 11), SRCALPHA)
_ON_IMG: Final[pg.Surface] = _OFF_IMG.copy()
_ON_IMG.fill((0, 0, 1, 0))


class TestLockedCheckbox(TestCase):
    """Tests for the LockedCheckbox class."""

    _locked_checkbox: LockedCheckbox

    @classmethod
    def setUpClass(cls: type["TestLockedCheckbox"]) -> None:
        """Creates the checkbox."""

        cls._locked_checkbox = LockedCheckbox(
            RectPos(1, 2, "center"),
            [_OFF_IMG, _ON_IMG], "hello", 1
        )

    def _copy_locked_checkbox(self) -> LockedCheckbox:
        """
        Creates a copy of the locked checkbox.

        Returns:
            copy
        """

        coord_type: str = self._locked_checkbox.init_pos.coord_type
        pos: RectPos = RectPos(
            self._locked_checkbox.init_pos.x, self._locked_checkbox.init_pos.y, coord_type
        )
        imgs: list[pg.Surface] = self._locked_checkbox.init_imgs
        hovering_text: str | None = None
        if self._locked_checkbox.hovering_text_label is not None:
            hovering_text = self._locked_checkbox.hovering_text_label.text
        layer: int = self._locked_checkbox.layer - ELEMENT_LAYER

        copy_locked_checkbox: LockedCheckbox = LockedCheckbox(pos, imgs, hovering_text, layer)
        copy_locked_checkbox.resize(2, 3)
        return copy_locked_checkbox

    @mock.patch.object(_Clickable, "__init__", autospec=True)
    def test_init(self, mock_clickable_init: Mock) -> None:
        """Tests the init method, mocks Clickable.__init__."""

        pos: RectPos = RectPos(1, 2, "center")
        imgs: list[pg.Surface] = [_OFF_IMG, _ON_IMG]
        test_locked_checkbox: LockedCheckbox = LockedCheckbox(pos, imgs, "hello", 1)
        mock_clickable_init.assert_called_once_with(test_locked_checkbox, pos, imgs, "hello", 1)

        self.assertFalse(test_locked_checkbox.is_checked)

    @mock.patch.object(TextLabel, "set_text", autospec=True)
    def test_set_info(self, mock_set_text: Mock) -> None:
        """Tests the set_info method, mocks TextLabel.set_text."""

        copy_locked_checkbox: LockedCheckbox = self._copy_locked_checkbox()
        copy_locked_checkbox.set_info([_ON_IMG, _OFF_IMG], "world")

        self.assertListEqual(copy_locked_checkbox.init_imgs, [_ON_IMG, _OFF_IMG])
        self.assertListEqual(copy_locked_checkbox._imgs, [_ON_IMG, _OFF_IMG])

        mock_set_text.assert_called_once_with(copy_locked_checkbox.hovering_text_label, "world")

        copy_locked_checkbox.hovering_text_label = None
        copy_locked_checkbox.set_info([_ON_IMG, _OFF_IMG], "world")  # Assert it doesn't crash

    @mock.patch.object(_Clickable, "_handle_hover", autospec=True, wraps=_Clickable._handle_hover)
    def test_upt(self, mock_handle_hover: Mock) -> None:
        """Tests the upt method, mocks Clickable._handle_hover."""

        copy_locked_checkbox: LockedCheckbox = self._copy_locked_checkbox()
        mouse_info: _Mouse = _Mouse(0, 0, [False] * 3, [True] * 3, 0)
        blank_mouse_info: _Mouse = _Mouse(0, 0, [False] * 3, [False] * 3, 0)

        # Dont' hover and click
        self.assertFalse(copy_locked_checkbox.upt(None, mouse_info))
        mock_handle_hover.assert_called_once_with(copy_locked_checkbox, None)
        self.assertEqual(copy_locked_checkbox.img_i, 0)

        # Hover and click twice
        self.assertTrue(copy_locked_checkbox.upt(copy_locked_checkbox, mouse_info))
        self.assertTrue(copy_locked_checkbox.is_checked)
        self.assertEqual(copy_locked_checkbox.img_i, 1)
        self.assertTrue(copy_locked_checkbox.upt(copy_locked_checkbox, mouse_info))
        self.assertTrue(copy_locked_checkbox.is_checked)
        self.assertEqual(copy_locked_checkbox.img_i, 1)

        # Don't hover and don't click
        self.assertFalse(copy_locked_checkbox.upt(None, blank_mouse_info))
        # Hover and don't click
        self.assertFalse(copy_locked_checkbox.upt(copy_locked_checkbox, blank_mouse_info))


class TestCheckboxGrid(TestCase):
    """Tests for the CheckboxGrid class."""

    _init_info: list[CheckboxInfo]
    _inverted_axes: tuple[bool, bool]
    _checkbox_grid: CheckboxGrid

    @classmethod
    def setUpClass(cls: type["TestCheckboxGrid"]) -> None:
        """Creates the checkbox grid."""

        imgs: list[pg.Surface] = [_OFF_IMG, _ON_IMG, _OFF_IMG, _ON_IMG, _OFF_IMG]
        cls._init_info = [(img, str(i)) for i, img in enumerate(imgs)]
        cls._inverted_axes = (True, True)

        cls._checkbox_grid = CheckboxGrid(
            RectPos(1, 2, "center"),
            cls._init_info, 2, cls._inverted_axes, 1
        )

    def _copy_checkbox_grid(self) -> CheckboxGrid:
        """
        Creates a copy of the checkbox grid.

        Returns:
            copy
        """

        pos: RectPos = self._checkbox_grid._init_pos
        num_cols: int = self._checkbox_grid._num_cols
        layer: int = self._checkbox_grid.layer
        return CheckboxGrid(pos, self._init_info, num_cols, self._inverted_axes, layer)

    def _control_info(self, checkbox_grid: CheckboxGrid) -> None:
        """
        Controls the rect and objects info.

        Args:
            checkbox grid
        """

        expected_x: int
        expected_y: int

        locked_checkboxes: list[LockedCheckbox] = checkbox_grid.checkboxes
        rects: list[pg.Rect] = [locked_checkbox.rect for locked_checkbox in locked_checkboxes]

        expected_x, expected_y = min([rect.x for rect in rects]), min([rect.y for rect in rects])
        expected_w: int = max([rect.right  for rect in rects]) - expected_x
        expected_h: int = max([rect.bottom for rect in rects]) - expected_y
        expected_rect: pg.Rect = pg.Rect(expected_x, expected_y, expected_w, expected_h)
        self.assertEqual(checkbox_grid.rect, expected_rect)

        expected_objs_info: list[ObjInfo] = [
            ObjInfo(locked_checkbox) for locked_checkbox in locked_checkboxes
        ]
        self.assertListEqual(checkbox_grid.objs_info, expected_objs_info)

    @mock.patch.object(CheckboxGrid, "set_grid", autospec=True)
    def test_init(self, mock_set_grid: Mock) -> None:
        """Tests the init method, mocks CheckboxGrid.set_grid."""

        test_checkbox_grid: CheckboxGrid = CheckboxGrid(
            RectPos(1, 2, "center"),
            self._init_info, 2, self._inverted_axes, 1
        )

        self.assertEqual(test_checkbox_grid._init_pos, RectPos(1, 2, "center"))

        expected_increment_x: int = -_OFF_IMG.get_width()  - 10
        expected_increment_y: int = -_OFF_IMG.get_height() - 10
        self.assertEqual(test_checkbox_grid._num_cols, 2)
        self.assertEqual(test_checkbox_grid._increment_x, expected_increment_x)
        self.assertEqual(test_checkbox_grid._increment_y, expected_increment_y)

        self.assertEqual(test_checkbox_grid.layer, 1)

        mock_set_grid.assert_called_once_with(test_checkbox_grid, self._init_info, 1, 1)

    def test_get_hovering_info(self) -> None:
        """Tests the get_hovering_info method."""

        is_hovering: bool
        layer: int

        is_hovering, layer = self._checkbox_grid.get_hovering(self._checkbox_grid.rect.topleft)
        self.assertTrue(is_hovering)
        self.assertEqual(layer, 1)

        is_hovering, layer = self._checkbox_grid.get_hovering_info((0, 0))
        self.assertFalse(is_hovering)

    def test_check(self) -> None:
        """Tests the check method."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()

        copy_checkbox_grid.checkboxes[0].is_checked = False
        copy_checkbox_grid.clicked_i = 1
        copy_checkbox_grid.checkboxes[1].is_checked = True
        copy_checkbox_grid.check(0)

        self.assertEqual(copy_checkbox_grid.clicked_i, 0)
        self.assertEqual(copy_checkbox_grid.checkboxes[1].img_i, 0)
        self.assertFalse(copy_checkbox_grid.checkboxes[1].is_checked)
        self.assertEqual(copy_checkbox_grid.checkboxes[0].img_i, 1)
        self.assertTrue(copy_checkbox_grid.checkboxes[0].is_checked)

        # clicked_i out of range
        copy_checkbox_grid.clicked_i = len(copy_checkbox_grid.checkboxes)
        copy_checkbox_grid.check(0)

    @mock.patch.object(CheckboxGrid, "check", autospec=True)
    @mock.patch.object(LockedCheckbox, "resize", autospec=True)
    @mock.patch.object(LockedCheckbox, "__init__", autospec=True, wraps=LockedCheckbox.__init__)
    def test_set_grid(
            self, mock_locked_checkbox_init: Mock, mock_locked_checkbox_resize: Mock,
            mock_check: Mock
    ) -> None:
        """Tests the set_grid method, mocks __init__, resize and check."""

        init_x: int
        init_y: int
        i: int
        call: mock._Call
        img: pg.Surface
        expected_img: pg.Surface
        locked_checkbox: LockedCheckbox

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        init_num_locked_checkbox_init_calls: int = mock_locked_checkbox_init.call_count
        init_num_locked_checkbox_resize_calls: int = mock_locked_checkbox_resize.call_count
        init_num_check_calls: int = mock_check.call_count

        copy_checkbox_grid.set_grid([(_ON_IMG, None)] * 10, 2, 3)
        num_locked_checkbox_init_calls: int = mock_locked_checkbox_init.call_count
        expected_num_locked_checkbox_init_calls: int = init_num_locked_checkbox_init_calls + 10
        self.assertEqual(num_locked_checkbox_init_calls, expected_num_locked_checkbox_init_calls)
        self.assertEqual(mock_check.call_count, init_num_check_calls + 1)

        locked_checkbox_init_calls: list[mock._Call] = (
            mock_locked_checkbox_init.call_args_list[init_num_locked_checkbox_init_calls:]
        )

        init_x, init_y = copy_checkbox_grid._init_pos.x, copy_checkbox_grid._init_pos.y
        expected_pos: RectPos = RectPos(init_x, init_y, "center")
        for i, call in enumerate(locked_checkbox_init_calls):
            locked_checkbox: LockedCheckbox = copy_checkbox_grid.checkboxes[i]
            imgs: list[pg.Surface] = call[0][2]
            expected_layer: int = copy_checkbox_grid.layer
            self.assertTupleEqual(
                call[0], (locked_checkbox, expected_pos, imgs, None, expected_layer)
            )

            expected_imgs: list[pg.Surface] = [_ON_IMG, add_border(_ON_IMG, WHITE)]
            for img, expected_img in zip(expected_imgs, expected_imgs, strict=True):
                self.assertTrue(cmp_imgs(img, expected_img))

            if (i + 1) % 2 == 0:
                expected_pos.x = copy_checkbox_grid._init_pos.x
                expected_pos.y += copy_checkbox_grid._increment.y
            else:
                expected_pos.x += copy_checkbox_grid._increment.x

        locked_checkbox_resize_calls: list[mock._Call] = (
            mock_locked_checkbox_resize.call_args_list[init_num_locked_checkbox_resize_calls:]
        )
        zip_resize_calls_checkboxes: Iterator[tuple[mock._Call, LockedCheckbox]] = zip(
            locked_checkbox_resize_calls, copy_checkbox_grid.checkboxes, strict=True
        )
        for call, locked_checkbox in zip_resize_calls_checkboxes:
            self.assertTupleEqual(call[0], (locked_checkbox, 2, 3))
        self.assertEqual(len(copy_checkbox_grid.checkboxes), 10)

        self._control_info(copy_checkbox_grid)

        mock_check.assert_called_with(copy_checkbox_grid, 0)

    @mock.patch.object(LockedCheckbox, "resize", autospec=True)
    @mock.patch.object(LockedCheckbox, "set_info", autospec=True)
    def test_edit(self, mock_set_info: Mock, mock_locked_checkbox_resize: Mock) -> None:
        """Tests the edit method, mocks LockedCheckbox.set_info and LockedCheckbox.resize."""

        img: pg.Surface
        expected_img: pg.Surface
        increment_x: int
        increment_y: int

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        init_num_locked_checkbox_resize_calls: int = mock_locked_checkbox_resize.call_count

        # Replace checkbox
        copy_checkbox_grid.edit(0, _ON_IMG, "2", 2, 3)
        num_locked_checkbox_resize_calls: int = mock_locked_checkbox_resize.call_count
        expected_num_locked_checkbox_resize_calls: int = init_num_locked_checkbox_resize_calls + 1
        self.assertEqual(
            num_locked_checkbox_resize_calls, expected_num_locked_checkbox_resize_calls
        )

        imgs: list[pg.Surface] = mock_set_info.call_args[0][1]
        mock_set_info.assert_called_once_with(copy_checkbox_grid.checkboxes[0], imgs, "2")

        expected_imgs: list[pg.Surface] = [_ON_IMG, add_border(_ON_IMG, WHITE)]
        for img, expected_img in zip(imgs, expected_imgs, strict=True):
            self.assertTrue(cmp_imgs(img, expected_img))

        locked_checkbox: LockedCheckbox = copy_checkbox_grid.checkboxes[0]
        mock_locked_checkbox_resize.assert_called_with(locked_checkbox, 2, 3)

        # Add checkbox
        copy_checkbox_grid._num_cols = len(copy_checkbox_grid.checkboxes)
        copy_checkbox_grid.edit(None, _ON_IMG, "2", 2, 3)

        increment_x, increment_y = copy_checkbox_grid._increment_x, copy_checkbox_grid._increment_y

        locked_checkbox = copy_checkbox_grid.checkboxes[1]
        expected_last_x: int = self._checkbox_grid._unresized_last_point.x + increment_x
        mock_locked_checkbox_resize.assert_called_with(locked_checkbox, 2, 3)
        self.assertEqual(len(copy_checkbox_grid.checkboxes), 6)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.x, expected_last_x)

        expected_last_x = copy_checkbox_grid._init_pos.x
        expected_last_y: int = self._checkbox_grid._unresized_last_point.y + increment_y
        copy_checkbox_grid._num_cols = len(copy_checkbox_grid.checkboxes) + 1
        copy_checkbox_grid.edit(None, _ON_IMG, "2", 2, 3)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.x, expected_last_x)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.y, expected_last_y)

        self._control_info(copy_checkbox_grid)

    @mock.patch.object(CheckboxGrid, "check", autospec=True)
    @mock.patch.object(
        CheckboxGrid, "_get_grid_from_fallback", autospec=True,
        wraps=CheckboxGrid._get_grid_from_fallback
    )
    def test_remove(self, mock_get_grid_from_fallback: Mock, mock_check: Mock) -> None:
        """Tests the remove method, mocks from CheckboxGrid: _get_grid_from_fallback and check."""

        locked_checkbox: LockedCheckbox
        expected_last_x: int
        expected_last_y: int

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        for locked_checkbox in copy_checkbox_grid.checkboxes:
            locked_checkbox.resize(2, 3)
        init_num_check_calls: int = mock_check.call_count

        expected_locked_checkboxes: list[LockedCheckbox] = copy_checkbox_grid.checkboxes.copy()
        expected_locked_checkboxes.pop(2)

        copy_checkbox_grid.remove(2, _OFF_IMG, "hello", 2, 3)
        self.assertListEqual(copy_checkbox_grid.checkboxes, expected_locked_checkboxes)

        expected_last_x, expected_last_y = self._checkbox_grid.checkboxes[-1].rect.center
        self.assertEqual(copy_checkbox_grid._unresized_last_point.x, expected_last_x)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.y, expected_last_y)

        self._control_info(copy_checkbox_grid)

        # Remove last and clicked_i greater than remove_i
        copy_checkbox_grid.clicked_i = 1
        copy_checkbox_grid.checkboxes = [copy_checkbox_grid.checkboxes[0]]
        copy_checkbox_grid.remove(0, _OFF_IMG, "hello", 2, 3)

        mock_get_grid_from_fallback.assert_called_once_with(
            copy_checkbox_grid, _OFF_IMG, "hello", 2, 3
        )
        self.assertEqual(mock_check.call_count, init_num_check_calls + 1)
        mock_check.assert_called_with(copy_checkbox_grid, 0)

        # clicked_i is equal to remove_i
        copy_checkbox_grid.edit(None, _OFF_IMG, "hello", 2, 3)
        copy_checkbox_grid.clicked_i = 1
        copy_checkbox_grid.checkboxes[0].is_checked = False
        copy_checkbox_grid.remove(1, _OFF_IMG, "hello", 2, 3)

        self.assertEqual(copy_checkbox_grid.clicked_i, 0)
        self.assertEqual(copy_checkbox_grid.checkboxes[0].img_i, 1)
        self.assertTrue(copy_checkbox_grid.checkboxes[0].is_checked)

    def test_move_with_keys(self) -> None:
        """Tests the move_with_keys method."""

        clicked_i: int

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()

        max_i: int = len(copy_checkbox_grid.checkboxes) - 1
        num_cols: int = copy_checkbox_grid._num_cols

        # Left

        clicked_i = copy_checkbox_grid._move_with_keys([K_LEFT])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i + 1)
        copy_checkbox_grid.clicked_i = max_i
        clicked_i = copy_checkbox_grid._move_with_keys([K_LEFT])
        self.assertEqual(clicked_i, max_i)

        # Right

        clicked_i = copy_checkbox_grid._move_with_keys([K_RIGHT])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i - 1)
        copy_checkbox_grid.clicked_i = 0
        clicked_i = copy_checkbox_grid._move_with_keys([K_RIGHT])
        self.assertEqual(clicked_i, 0)

        # Down

        copy_checkbox_grid.clicked_i = max_i
        clicked_i = copy_checkbox_grid._move_with_keys([K_DOWN])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i - num_cols)
        copy_checkbox_grid.clicked_i = num_cols - 1
        clicked_i = copy_checkbox_grid._move_with_keys([K_DOWN])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i)

        # Up

        copy_checkbox_grid.clicked_i = 0
        clicked_i = copy_checkbox_grid._move_with_keys([K_UP])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i + num_cols)
        copy_checkbox_grid.clicked_i = max_i - num_cols + 1
        clicked_i = copy_checkbox_grid._move_with_keys([K_UP])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i)

        # Normal axes

        copy_checkbox_grid._increment.x = -copy_checkbox_grid._increment.x
        copy_checkbox_grid._increment.y = -copy_checkbox_grid._increment.y

        clicked_i = copy_checkbox_grid._move_with_keys([K_LEFT])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i - 1)
        clicked_i = copy_checkbox_grid._move_with_keys([K_RIGHT])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i + 1)

        clicked_i = copy_checkbox_grid._move_with_keys([K_UP])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i - num_cols)
        copy_checkbox_grid.clicked_i = 0
        clicked_i = copy_checkbox_grid._move_with_keys([K_DOWN])
        self.assertEqual(clicked_i, copy_checkbox_grid.clicked_i + num_cols)

    @mock.patch.object(CheckboxGrid, "check", autospec=True)
    @mock.patch.object(CheckboxGrid, "_move_with_keys", autospec=True, return_value=1)
    @mock.patch.object(LockedCheckbox, "upt", autospec=True, wraps=LockedCheckbox.upt)
    def test_upt(
            self, mock_locked_checkbox_upt: Mock, mock_move_with_keys: Mock,
            mock_check: Mock
    ) -> None:
        """Tests the upt method, mocks upt, move_with_keys and check."""

        call: mock._Call
        locked_checkbox: LockedCheckbox

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        init_num_check_calls: int = mock_check.call_count
        mouse_info: _Mouse = _Mouse(0, 0, [False] * 3, [True] * 3, 0)

        hovered_locked_checkbox: LockedCheckbox = copy_checkbox_grid.checkboxes[0]
        expected_clicked_i: int = copy_checkbox_grid.clicked_i
        clicked_i: int = copy_checkbox_grid.upt(hovered_locked_checkbox, mouse_info, [])
        self.assertEqual(clicked_i, expected_clicked_i)

        locked_checkbox_upt_calls: list[mock._Call] = mock_locked_checkbox_upt.call_args_list
        zip_upt_calls_locked_checkboxes: Iterator[tuple[mock._Call, LockedCheckbox]] = zip(
            locked_checkbox_upt_calls, copy_checkbox_grid.checkboxes, strict=True
        )
        for call, locked_checkbox in zip_upt_calls_locked_checkboxes:
            self.assertTupleEqual(call[0], (locked_checkbox, hovered_locked_checkbox, mouse_info))

        self.assertEqual(mock_check.call_count, init_num_check_calls + 1)
        mock_check.assert_called_with(copy_checkbox_grid, 0)

        copy_checkbox_grid.upt(copy_checkbox_grid, mouse_info, [K_RIGHT])
        mock_move_with_keys.assert_called_with(copy_checkbox_grid, [K_RIGHT])
        mock_check.assert_called_with(copy_checkbox_grid, 1)

        copy_checkbox_grid.upt(hovered_locked_checkbox, mouse_info, [K_RIGHT])
        mock_move_with_keys.assert_called_with(copy_checkbox_grid, [K_RIGHT])
