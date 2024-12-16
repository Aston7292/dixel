"""Tests for the checkbox_grid file."""

from unittest import TestCase, mock
from itertools import zip_longest
from typing import Final, Optional, Any

import pygame as pg

from src.classes.checkbox_grid import LockedCheckbox, CheckboxGrid
from src.classes.clickable import Clickable
from src.classes.text_label import TextLabel

from src.utils import Point, RectPos, Ratio, ObjInfo, MouseInfo, add_border
from src.type_utils import CheckboxInfo
from src.consts import WHITE, ELEMENT_LAYER

from tests.utils import cmp_imgs, RESIZING_RATIO

IMG_1: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_2: Final[pg.Surface] = IMG_1.copy()
IMG_2.fill((0, 0, 1, 0))


class TestLockedCheckbox(TestCase):
    """Tests for the LockedCheckbox class."""

    locked_checkbox: LockedCheckbox

    @classmethod
    def setUpClass(cls: type["TestLockedCheckbox"]) -> None:
        """Creates the checkbox."""

        cls.locked_checkbox = LockedCheckbox(RectPos(1, 2, "center"), (IMG_1, IMG_2), "hello", 1)

    def _copy_locked_checkbox(self) -> LockedCheckbox:
        """
        Creates a copy of the locked checkbox.

        Returns:
            copy
        """

        hovering_text: Optional[str] = None
        if self.locked_checkbox._hovering_text_label:
            hovering_text = self.locked_checkbox._hovering_text_label.text
        layer: int = self.locked_checkbox._layer - ELEMENT_LAYER

        copy_locked_checkbox: LockedCheckbox = LockedCheckbox(
            self.locked_checkbox.init_pos, self.locked_checkbox._init_imgs, hovering_text, layer
        )
        copy_locked_checkbox.resize(RESIZING_RATIO)

        return copy_locked_checkbox

    @mock.patch.object(Clickable, "__init__", autospec=True)
    def test_init(self, mock_clickable_init: mock.Mock) -> None:
        """Tests the init method, mocks the Clickable.__init__ method."""

        test_locked_checkbox: LockedCheckbox = LockedCheckbox(
            RectPos(1, 2, "center"), (IMG_1, IMG_2), "hello", 1
        )
        mock_clickable_init.assert_called_once_with(
            test_locked_checkbox, RectPos(1, 2, "center"), (IMG_1, IMG_2), "hello", 1
        )

        self.assertFalse(test_locked_checkbox.is_checked)

    @mock.patch.object(Clickable, "_blit_i", autospec=True)
    def test_blit(self, mock_blit_i: mock.Mock) -> None:
        """Tests the blit method, mocks the Clickable._blit_i method."""

        copy_locked_checkbox: LockedCheckbox = self._copy_locked_checkbox()

        copy_locked_checkbox.blit()
        mock_blit_i.assert_called_with(copy_locked_checkbox, 0)

        copy_locked_checkbox._is_hovering = True
        copy_locked_checkbox.blit()
        mock_blit_i.assert_called_with(copy_locked_checkbox, 1)
        copy_locked_checkbox._is_hovering = False

        copy_locked_checkbox.is_checked = True
        copy_locked_checkbox.blit()
        mock_blit_i.assert_called_with(copy_locked_checkbox, 1)

    @mock.patch.object(TextLabel, "set_text", autospec=True)
    def test_set_info(self, mock_set_text: mock.Mock) -> None:
        """Tests the set_info method, mocks the TextLabel.set_text method."""

        copy_locked_checkbox: LockedCheckbox = self._copy_locked_checkbox()
        copy_locked_checkbox.set_info((IMG_2, IMG_1), "world")

        self.assertTupleEqual(copy_locked_checkbox._init_imgs, (IMG_2, IMG_1))
        self.assertTupleEqual(copy_locked_checkbox._imgs, (IMG_2, IMG_1))

        mock_set_text.assert_called_once_with(copy_locked_checkbox._hovering_text_label, "world")

        copy_locked_checkbox._hovering_text_label = None
        copy_locked_checkbox.set_info((IMG_2, IMG_1), "world")  # Assert it doesn't crash

    @mock.patch.object(Clickable, "_handle_hover", autospec=True, wraps=Clickable._handle_hover)
    def test_upt(self, mock_handle_hover: mock.Mock) -> None:
        """Tests the upt method, mocks the Clickable._handle_hover method."""

        copy_locked_checkbox: LockedCheckbox = self._copy_locked_checkbox()
        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)

        # Dont' hover and click
        self.assertFalse(copy_locked_checkbox.upt(None, mouse_info))
        self.assertFalse(copy_locked_checkbox._is_hovering)
        mock_handle_hover.assert_called_once_with(copy_locked_checkbox, None)

        # Hover and click twice
        self.assertTrue(copy_locked_checkbox.upt(copy_locked_checkbox, mouse_info))
        self.assertTrue(copy_locked_checkbox.is_checked)
        self.assertTrue(copy_locked_checkbox.upt(copy_locked_checkbox, mouse_info))
        self.assertTrue(copy_locked_checkbox.is_checked)

        # Don't hover and don't click
        self.assertFalse(copy_locked_checkbox.upt(None, blank_mouse_info))
        # Hover and don't click
        self.assertFalse(copy_locked_checkbox.upt(copy_locked_checkbox, blank_mouse_info))


class TestCheckboxGrid(TestCase):
    """Tests for the CheckboxGrid class."""

    init_info: tuple[CheckboxInfo, ...]
    inverted_axes: tuple[bool, bool]
    checkbox_grid: CheckboxGrid

    @classmethod
    def setUpClass(cls: type["TestCheckboxGrid"]) -> None:
        """Creates the checkbox grid."""

        surfs: tuple[pg.Surface, ...] = (IMG_1, IMG_2, IMG_1, IMG_2, IMG_1)
        cls.init_info = tuple((surf, str(i)) for i, surf in enumerate(surfs))
        cls.inverted_axes = (True, True)
        cls.checkbox_grid = CheckboxGrid(
            RectPos(1, 2, "center"), cls.init_info, 2, cls.inverted_axes, 1
        )

    def _copy_checkbox_grid(self) -> CheckboxGrid:
        """
        Creates a copy of the checkbox grid.

        Returns:
            copy
        """

        return CheckboxGrid(
            self.checkbox_grid._init_pos, self.init_info, self.checkbox_grid._cols,
            self.inverted_axes, self.checkbox_grid._layer
        )

    def _check_info(self, checkbox_grid: CheckboxGrid) -> None:
        """
        Checks the rect and objects info.

        Args:
            checkbox grid
        """

        rects: tuple[pg.Rect, ...] = tuple(
            locked_checkbox.rect for locked_checkbox in checkbox_grid.checkboxes
        )
        expected_left: int = min(rect.left for rect in rects)
        expected_top: int = min(rect.top for rect in rects)
        expected_w: int = max(rect.right for rect in rects) - expected_left
        expected_h: int = max(rect.bottom for rect in rects) - expected_top
        expected_rect: pg.Rect = pg.Rect(expected_left, expected_top, expected_w, expected_h)
        self.assertEqual(checkbox_grid.rect, expected_rect)

        expected_objs_info: list[ObjInfo] = [
            ObjInfo(locked_checkbox) for locked_checkbox in checkbox_grid.checkboxes
        ]
        self.assertListEqual(checkbox_grid.objs_info, expected_objs_info)

    @mock.patch.object(CheckboxGrid, "set_grid", autospec=True)
    def test_init(self, mock_set_grid: mock.Mock) -> None:
        """Tests the init method, mocks the CheckboxGrid.set_grid method."""

        test_checkbox_grid: CheckboxGrid = CheckboxGrid(
            RectPos(1, 2, "center"), self.init_info, 2, self.inverted_axes, 1
        )

        self.assertEqual(test_checkbox_grid._init_pos, RectPos(1, 2, "center"))

        expected_increment: Point = Point(-IMG_1.get_width() - 10, -IMG_1.get_height() - 10)
        self.assertEqual(test_checkbox_grid._cols, 2)
        self.assertEqual(test_checkbox_grid._increment, expected_increment)

        self.assertEqual(test_checkbox_grid._layer, 1)

        mock_set_grid.assert_called_once_with(test_checkbox_grid, self.init_info, Ratio(1.0, 1.0))

    def test_get_hovering_info(self) -> None:
        """Tests the get_hovering_info method."""

        is_hovering: bool
        layer: int
        is_hovering, layer = self.checkbox_grid.get_hovering_info(self.checkbox_grid.rect.topleft)
        self.assertTrue(is_hovering)
        self.assertEqual(layer, 1)

        is_hovering, layer = self.checkbox_grid.get_hovering_info(
            (self.checkbox_grid.rect.x - 1, 0)
        )
        self.assertFalse(is_hovering)

    def test_post_resize(self) -> None:
        """Tests the post_resize method."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        copy_checkbox_grid.rect = pg.Rect()
        copy_checkbox_grid.post_resize()

        self._check_info(copy_checkbox_grid)

    def test_check(self) -> None:
        """Tests the check method."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()

        copy_checkbox_grid.checkboxes[0].is_checked = False
        copy_checkbox_grid.clicked_i = 1
        copy_checkbox_grid.checkboxes[1].is_checked = True
        copy_checkbox_grid.check(0)

        self.assertEqual(copy_checkbox_grid.clicked_i, 0)
        self.assertFalse(copy_checkbox_grid.checkboxes[1].is_checked)
        self.assertTrue(copy_checkbox_grid.checkboxes[0].is_checked)

        # clicked_i out of range
        copy_checkbox_grid.clicked_i = len(copy_checkbox_grid.checkboxes)
        copy_checkbox_grid.check(0)

    @mock.patch.object(CheckboxGrid, "check", autospec=True)
    @mock.patch.object(LockedCheckbox, "resize", autospec=True)
    @mock.patch.object(LockedCheckbox, "__init__", autospec=True, wraps=LockedCheckbox.__init__)
    def test_set_grid(
        self, mock_locked_checkbox_init: mock.Mock, mock_locked_checkbox_resize: mock.Mock,
        mock_check: mock.Mock
    ) -> None:
        """Tests the set_grid method, mocks the __init__, resize and check methods."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        init_locked_checkbox_init_n_calls: int = mock_locked_checkbox_init.call_count
        init_locked_checkbox_resize_n_calls: int = mock_locked_checkbox_resize.call_count
        init_check_n_calls: int = mock_check.call_count

        copy_checkbox_grid.set_grid(((IMG_2, None),) * 10, RESIZING_RATIO)
        self.assertEqual(
            mock_locked_checkbox_init.call_count, init_locked_checkbox_init_n_calls + 10
        )
        self.assertEqual(mock_check.call_count, init_check_n_calls + 1)

        last_x: int = copy_checkbox_grid._init_pos.x
        last_y: int = copy_checkbox_grid._init_pos.y
        for i in range(10):
            call_i: int = init_locked_checkbox_init_n_calls + i
            call: tuple[Any, ...] = mock_locked_checkbox_init.call_args_list[call_i][0]

            imgs: tuple[pg.Surface, pg.Surface] = call[2]
            expected_layer: int = copy_checkbox_grid._layer
            self.assertTupleEqual(
                call, (call[0], RectPos(last_x, last_y, "center"), imgs, None, expected_layer)
            )

            expected_imgs: tuple[pg.Surface, pg.Surface] = (IMG_2, add_border(IMG_2, WHITE))
            for img, expected_img in zip_longest(imgs, expected_imgs):
                self.assertTrue(cmp_imgs(img, expected_img))

            last_x += copy_checkbox_grid._increment.x
            if not (i + 1) % 2:
                last_x = copy_checkbox_grid._init_pos.x
                last_y += copy_checkbox_grid._increment.y

        locked_checkbox_resize_calls: list[Any] = (
            mock_locked_checkbox_resize.call_args_list[init_locked_checkbox_resize_n_calls:]
        )
        pointer_locked_checkboxes: list[LockedCheckbox] = copy_checkbox_grid.checkboxes
        for call, checkbox in zip_longest(locked_checkbox_resize_calls, pointer_locked_checkboxes):
            self.assertTupleEqual(call[0], (checkbox, RESIZING_RATIO))
        self.assertEqual(len(copy_checkbox_grid.checkboxes), 10)

        self._check_info(copy_checkbox_grid)

        mock_check.assert_called_with(copy_checkbox_grid, 0)

    @mock.patch.object(LockedCheckbox, "resize", autospec=True)
    @mock.patch.object(LockedCheckbox, "set_info", autospec=True)
    def test_replace(
        self, mock_locked_checkbox_set_info: mock.Mock, mock_locked_checkbox_resize: mock.Mock
    ) -> None:
        """Tests the replace method, mocks from LockedCheckbox: set_info and resize."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        init_locked_checkbox_resize_n_calls: int = mock_locked_checkbox_resize.call_count

        # Replace checkbox
        copy_checkbox_grid.replace(0, IMG_2, "2", RESIZING_RATIO)
        self.assertEqual(
            mock_locked_checkbox_resize.call_count, init_locked_checkbox_resize_n_calls + 1
        )

        imgs: tuple[pg.Surface, pg.Surface] = mock_locked_checkbox_set_info.call_args[0][1]
        mock_locked_checkbox_set_info.assert_called_once_with(
            copy_checkbox_grid.checkboxes[0], imgs, "2"
        )

        expected_imgs: tuple[pg.Surface, pg.Surface] = (IMG_2, add_border(IMG_2, WHITE))
        for img, expected_img in zip_longest(imgs, expected_imgs):
            self.assertTrue(cmp_imgs(img, expected_img))

        mock_locked_checkbox_resize.assert_called_with(
            copy_checkbox_grid.checkboxes[0], RESIZING_RATIO
        )

        # Add checkbox
        copy_checkbox_grid._cols = len(copy_checkbox_grid.checkboxes)
        copy_checkbox_grid.replace(None, IMG_2, "2", RESIZING_RATIO)

        expected_last_x: int = (
            self.checkbox_grid._unresized_last_point.x + copy_checkbox_grid._increment.x
        )
        mock_locked_checkbox_resize.assert_called_with(
            copy_checkbox_grid.checkboxes[-1], RESIZING_RATIO
        )
        self.assertEqual(len(copy_checkbox_grid.checkboxes), 6)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.x, expected_last_x)

        expected_last_x = copy_checkbox_grid._init_pos.x
        expected_last_y: int = (
            self.checkbox_grid._unresized_last_point.y + copy_checkbox_grid._increment.y
        )
        copy_checkbox_grid._cols = len(copy_checkbox_grid.checkboxes) + 1
        copy_checkbox_grid.replace(None, IMG_2, "2", RESIZING_RATIO)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.x, expected_last_x)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.y, expected_last_y)

        self._check_info(copy_checkbox_grid)

    @mock.patch.object(LockedCheckbox, "move_rect", autospec=True)
    def test_move_to_last(self, mock_locked_checkbox_move_rect: mock.Mock) -> None:
        """Tests the move_to_last_method, mocks the LockedCheckbox.move_rect method."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        copy_checkbox_grid._move_to_last(0, RESIZING_RATIO)

        expected_last_x: int = copy_checkbox_grid._unresized_last_point.x
        expected_last_y: int = copy_checkbox_grid._unresized_last_point.y
        mock_locked_checkbox_move_rect.assert_called_once_with(
            copy_checkbox_grid.checkboxes[0], expected_last_x, expected_last_y, RESIZING_RATIO
        )

    @mock.patch.object(LockedCheckbox, "resize", autospec=True)
    @mock.patch.object(LockedCheckbox, "__init__", autospec=True, wraps=LockedCheckbox.__init__)
    def test_get_grid_from_fallback(
        self, mock_locked_checkbox_init: mock.Mock, mock_locked_checkbox_resize: mock.Mock
    ) -> None:
        """Tests the get_grid_from_fallback method, mocks the __init__ and resize methods."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        init_locked_checkbox_init_n_calls: int = mock_locked_checkbox_init.call_count
        init_locked_checkbox_resize_n_calls: int = mock_locked_checkbox_resize.call_count

        copy_checkbox_grid._get_grid_from_fallback(IMG_1, "hello", RESIZING_RATIO)
        self.assertEqual(
            mock_locked_checkbox_init.call_count, init_locked_checkbox_init_n_calls + 1
        )
        self.assertEqual(
            mock_locked_checkbox_resize.call_count, init_locked_checkbox_resize_n_calls + 1
        )

        locked_checkbox: LockedCheckbox = mock_locked_checkbox_init.call_args[0][0]

        imgs: tuple[pg.Surface, pg.Surface] = mock_locked_checkbox_init.call_args[0][2]
        expected_init_pos: RectPos = RectPos(
            self.checkbox_grid._unresized_last_point.x, self.checkbox_grid._unresized_last_point.y,
            "center"
        )
        mock_locked_checkbox_init.assert_called_with(
            locked_checkbox, expected_init_pos, imgs, "hello", copy_checkbox_grid._layer
        )

        expected_imgs: tuple[pg.Surface, pg.Surface] = (IMG_1, add_border(IMG_1, WHITE))
        for img, expected_img in zip_longest(imgs, expected_imgs):
            self.assertTrue(cmp_imgs(img, expected_img))

        mock_locked_checkbox_resize.assert_called_with(locked_checkbox, RESIZING_RATIO)
        self.assertListEqual(copy_checkbox_grid.checkboxes, [locked_checkbox])

        expected_last_x: int = copy_checkbox_grid._init_pos.x + copy_checkbox_grid._increment.x
        expected_last_y: int = copy_checkbox_grid._init_pos.y
        self.assertEqual(copy_checkbox_grid._unresized_last_point.x, expected_last_x)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.y, expected_last_y)

        # Grid with 1 column

        copy_checkbox_grid._cols = 1
        copy_checkbox_grid._get_grid_from_fallback(IMG_1, None, RESIZING_RATIO)
        expected_last_x = copy_checkbox_grid._init_pos.x
        expected_last_y = copy_checkbox_grid._init_pos.y + copy_checkbox_grid._increment.y
        self.assertEqual(copy_checkbox_grid._unresized_last_point.x, expected_last_x)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.y, expected_last_y)

    @mock.patch.object(CheckboxGrid, "check", autospec=True)
    @mock.patch.object(
        CheckboxGrid, "_get_grid_from_fallback", autospec=True,
        wraps=CheckboxGrid._get_grid_from_fallback
    )
    @mock.patch.object(CheckboxGrid, "_move_to_last", autospec=True)
    def test_remove(
        self, mock_move_to_last: mock.Mock, mock_get_grid_from_fallback: mock.Mock,
        mock_check: mock.Mock
    ) -> None:
        """Tests the remove method, mocks _move_to_last, _get_grid_from_fallback and check."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        for locked_checkbox in copy_checkbox_grid.checkboxes:
            locked_checkbox.resize(RESIZING_RATIO)
        init_check_n_calls: int = mock_check.call_count

        fallback_info: CheckboxInfo = (IMG_1, "hello")
        expected_locked_checkboxes: list[LockedCheckbox] = copy_checkbox_grid.checkboxes.copy()
        expected_locked_checkboxes.pop(2)

        copy_checkbox_grid.remove(2, fallback_info, RESIZING_RATIO)
        self.assertEqual(mock_move_to_last.call_count, 2)

        self.assertListEqual(copy_checkbox_grid.checkboxes, expected_locked_checkboxes)
        for i, call in enumerate(mock_move_to_last.call_args_list, 2):
            self.assertTupleEqual(call[0], (copy_checkbox_grid, i, RESIZING_RATIO))

        expected_last_x: int = self.checkbox_grid.checkboxes[-1].rect.centerx
        expected_last_y: int = self.checkbox_grid.checkboxes[-1].rect.centery
        self.assertEqual(copy_checkbox_grid._unresized_last_point.x, expected_last_x)
        self.assertEqual(copy_checkbox_grid._unresized_last_point.y, expected_last_y)

        self._check_info(copy_checkbox_grid)

        # Remove last and clicked_i greater than remove_i
        copy_checkbox_grid.clicked_i = 1
        copy_checkbox_grid.checkboxes = [copy_checkbox_grid.checkboxes[0]]
        copy_checkbox_grid.remove(0, fallback_info, RESIZING_RATIO)

        mock_get_grid_from_fallback.assert_called_once_with(
            copy_checkbox_grid, *fallback_info, RESIZING_RATIO
        )
        self.assertEqual(mock_check.call_count, init_check_n_calls + 1)
        mock_check.assert_called_with(copy_checkbox_grid, 0)

        # clicked_i is equal to remove_i
        copy_checkbox_grid.replace(None, IMG_1, "hello", RESIZING_RATIO)
        copy_checkbox_grid.clicked_i = 1
        copy_checkbox_grid.checkboxes[0].is_checked = False
        copy_checkbox_grid.remove(1, fallback_info, RESIZING_RATIO)

        self.assertEqual(copy_checkbox_grid.clicked_i, 0)
        self.assertTrue(copy_checkbox_grid.checkboxes[0].is_checked)

    def test_move_with_keys(self) -> None:
        """Tests the move_with_keys method."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()

        max_i: int = len(copy_checkbox_grid.checkboxes) - 1
        cols: int = copy_checkbox_grid._cols
        future_clicked_i: int

        # Left

        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_LEFT])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i + 1)
        copy_checkbox_grid.clicked_i = max_i
        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_LEFT])
        self.assertEqual(future_clicked_i, max_i)

        # Right

        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_RIGHT])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i - 1)
        copy_checkbox_grid.clicked_i = 0
        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_RIGHT])
        self.assertEqual(future_clicked_i, 0)

        # Down

        copy_checkbox_grid.clicked_i = max_i
        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_DOWN])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i - cols)
        copy_checkbox_grid.clicked_i = cols - 1
        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_DOWN])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i)

        # Up

        copy_checkbox_grid.clicked_i = 0
        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_UP])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i + cols)
        copy_checkbox_grid.clicked_i = max_i - cols + 1
        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_UP])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i)

        # Normal axes

        copy_checkbox_grid._increment.x = -copy_checkbox_grid._increment.x
        copy_checkbox_grid._increment.y = -copy_checkbox_grid._increment.y

        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_LEFT])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i - 1)
        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_RIGHT])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i + 1)

        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_UP])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i - cols)
        copy_checkbox_grid.clicked_i = 0
        future_clicked_i = copy_checkbox_grid._move_with_keys([pg.K_DOWN])
        self.assertEqual(future_clicked_i, copy_checkbox_grid.clicked_i + cols)

    @mock.patch.object(CheckboxGrid, "check", autospec=True)
    @mock.patch.object(CheckboxGrid, "_move_with_keys", autospec=True, return_value=1)
    @mock.patch.object(LockedCheckbox, "upt", autospec=True, wraps=LockedCheckbox.upt)
    def test_upt(
        self, mock_locked_checkbox_upt: mock.Mock,
        mock_move_with_keys: mock.Mock, mock_check: mock.Mock
    ) -> None:
        """Tests the upt method, mocks the upt, move_with_keys and check methods."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        init_check_n_calls: int = mock_check.call_count
        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)

        hovered_locked_checkbox: LockedCheckbox = copy_checkbox_grid.checkboxes[0]
        expected_clicked_i: int = copy_checkbox_grid.clicked_i
        self.assertEqual(
            copy_checkbox_grid.upt(hovered_locked_checkbox, mouse_info, []), expected_clicked_i
        )

        locked_checkbox_upt_calls = mock_locked_checkbox_upt.call_args_list
        pointer_locked_checkboxes: list[LockedCheckbox] = copy_checkbox_grid.checkboxes
        for call, checkbox in zip_longest(locked_checkbox_upt_calls, pointer_locked_checkboxes):
            self.assertTupleEqual(call[0], (checkbox, hovered_locked_checkbox, mouse_info))

        self.assertEqual(mock_check.call_count, init_check_n_calls + 1)
        mock_check.assert_called_with(copy_checkbox_grid, 0)

        copy_checkbox_grid.upt(copy_checkbox_grid, mouse_info, [pg.K_RIGHT])
        mock_move_with_keys.assert_called_with(copy_checkbox_grid, [pg.K_RIGHT])
        mock_check.assert_called_with(copy_checkbox_grid, 1)

        copy_checkbox_grid.upt(hovered_locked_checkbox, mouse_info, [pg.K_RIGHT])
        mock_move_with_keys.assert_called_with(copy_checkbox_grid, [pg.K_RIGHT])
