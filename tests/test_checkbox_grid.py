"""Tests for the checkbox grid file."""

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

    @mock.patch.object(Clickable, "_base_blit", autospec=True)
    def test_blit(self, mock_base_blit: mock.Mock) -> None:
        """Tests the blit method, mocks the Clickable._base_blit method."""

        copy_locked_checkbox: LockedCheckbox = self._copy_locked_checkbox()

        copy_locked_checkbox.blit()
        mock_base_blit.assert_called_with(copy_locked_checkbox, 0)

        copy_locked_checkbox._is_hovering = True
        copy_locked_checkbox.blit()
        mock_base_blit.assert_called_with(copy_locked_checkbox, 1)
        copy_locked_checkbox._is_hovering = False

        copy_locked_checkbox.is_checked = True
        copy_locked_checkbox.blit()
        mock_base_blit.assert_called_with(copy_locked_checkbox, 1)

    @mock.patch.object(TextLabel, "set_text", autospec=True)
    def test_set_info(self, mock_set_text: mock.Mock) -> None:
        """Tests the set_info method, mocks the TextLabel.set_text method."""

        copy_checkbox: LockedCheckbox = self._copy_locked_checkbox()
        copy_checkbox.set_info((IMG_2, IMG_1), "world")

        self.assertTupleEqual(copy_checkbox._init_imgs, (IMG_2, IMG_1))
        self.assertTupleEqual(copy_checkbox._imgs, (IMG_2, IMG_1))

        mock_set_text.assert_called_once_with(copy_checkbox._hovering_text_label, "world")

        copy_checkbox._hovering_text_label = None
        copy_checkbox.set_info((IMG_2, IMG_1), "world")  # Assert it doesn't crash

    @mock.patch.object(pg.mouse, "set_cursor", autospec=True)
    def test_upt(self, mock_set_cursor: mock.Mock) -> None:
        """Tests the upt method, mocks the pygame.mouse.set_cursor function."""

        copy_locked_checkbox: LockedCheckbox = self._copy_locked_checkbox()
        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)

        # Leave hover and click
        copy_locked_checkbox._is_hovering = True
        self.assertFalse(copy_locked_checkbox.upt(None, mouse_info))
        self.assertFalse(copy_locked_checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_ARROW)

        # Enter hover and click twice
        self.assertTrue(copy_locked_checkbox.upt(copy_locked_checkbox, mouse_info))
        self.assertTrue(copy_locked_checkbox.is_checked)
        self.assertTrue(copy_locked_checkbox.upt(copy_locked_checkbox, mouse_info))
        self.assertTrue(copy_locked_checkbox.is_checked)
        self.assertTrue(copy_locked_checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_HAND)

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

        rects: tuple[pg.Rect, ...] = tuple(checkbox.rect for checkbox in checkbox_grid.checkboxes)
        expected_left: int = min(rect.left for rect in rects)
        expected_top: int = min(rect.top for rect in rects)
        expected_w: int = max(rect.right for rect in rects) - expected_left
        expected_h: int = max(rect.bottom for rect in rects) - expected_top
        expected_rect: pg.Rect = pg.Rect(expected_left, expected_top, expected_w, expected_h)
        self.assertEqual(checkbox_grid.rect, expected_rect)

        expected_objs_info: list[ObjInfo] = [
            ObjInfo(checkbox) for checkbox in checkbox_grid.checkboxes
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

    def test_check_hovering(self) -> None:
        """Tests the check_hovering method."""

        hovered_obj: Optional[CheckboxGrid]
        layer: int
        hovered_obj, layer = self.checkbox_grid.check_hovering(self.checkbox_grid.rect.topleft)
        self.assertIs(hovered_obj, self.checkbox_grid)
        self.assertEqual(layer, 1)

        hovered_obj, layer = self.checkbox_grid.check_hovering((self.checkbox_grid.rect.x - 1, 0))
        self.assertIsNone(hovered_obj)

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
        mock_checkbox_grid_check: mock.Mock
    ) -> None:
        """Tests the set_grid method, mocks the __init__, resize and check methods."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        init_locked_checkbox_init_n_calls: int = mock_locked_checkbox_init.call_count
        init_locked_checkbox_resize_n_calls: int = mock_locked_checkbox_resize.call_count
        init_checkbox_grid_check_n_calls: int = mock_checkbox_grid_check.call_count

        copy_checkbox_grid.set_grid(((IMG_2, None),) * 10, RESIZING_RATIO)
        self.assertEqual(
            mock_locked_checkbox_init.call_count, init_locked_checkbox_init_n_calls + 10
        )
        self.assertEqual(mock_checkbox_grid_check.call_count, init_checkbox_grid_check_n_calls + 1)

        last_x: int = copy_checkbox_grid._init_pos.x
        last_y: int = copy_checkbox_grid._init_pos.y
        for i in range(10):
            args_i: int = init_locked_checkbox_init_n_calls + i
            args: tuple[Any, ...] = mock_locked_checkbox_init.call_args_list[args_i][0]

            imgs: tuple[pg.Surface, pg.Surface] = args[2]
            expected_layer: int = copy_checkbox_grid._layer
            self.assertTupleEqual(
                args, (args[0], RectPos(last_x, last_y, "center"), imgs, None, expected_layer)
            )

            expected_imgs: tuple[pg.Surface, pg.Surface] = (IMG_2, add_border(IMG_2, WHITE))
            for img, expected_img in zip_longest(imgs, expected_imgs):
                self.assertTrue(cmp_imgs(img, expected_img))

            last_x += copy_checkbox_grid._increment.x
            if not (i + 1) % 2:
                last_x = copy_checkbox_grid._init_pos.x
                last_y += copy_checkbox_grid._increment.y

        locked_checkbox_resize_actual_calls: list[Any] = (
            mock_locked_checkbox_resize.call_args_list[init_locked_checkbox_resize_n_calls:]
        )
        for i, args in enumerate(locked_checkbox_resize_actual_calls):
            self.assertEqual(args[0], (copy_checkbox_grid.checkboxes[i], RESIZING_RATIO))
        self.assertEqual(len(copy_checkbox_grid.checkboxes), 10)

        self._check_info(copy_checkbox_grid)

        mock_checkbox_grid_check.assert_called_with(copy_checkbox_grid, 0)

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

        expected_last_x: int = self.checkbox_grid._last_point.x + copy_checkbox_grid._increment.x
        mock_locked_checkbox_resize.assert_called_with(
            copy_checkbox_grid.checkboxes[-1], RESIZING_RATIO
        )
        self.assertEqual(len(copy_checkbox_grid.checkboxes), 6)
        self.assertEqual(copy_checkbox_grid._last_point.x, expected_last_x)

        expected_last_y: int = self.checkbox_grid._last_point.y + copy_checkbox_grid._increment.y
        copy_checkbox_grid._cols = len(copy_checkbox_grid.checkboxes) + 1
        copy_checkbox_grid.replace(None, IMG_2, "2", RESIZING_RATIO)
        self.assertEqual(copy_checkbox_grid._last_point.x, copy_checkbox_grid._init_pos.x)
        self.assertEqual(copy_checkbox_grid._last_point.y, expected_last_y)

        self._check_info(copy_checkbox_grid)

    @mock.patch.object(LockedCheckbox, "move_rect", autospec=True)
    def test_move_to_last(self, mock_locked_checkbox_move_rect: mock.Mock) -> None:
        """Tests the move_to_last_method, mocks the LockedCheckbox.move_rect method."""

        copy_checkbox_grid: CheckboxGrid = self._copy_checkbox_grid()
        copy_checkbox_grid._move_to_last(0, RESIZING_RATIO)

        local_last_x: int = copy_checkbox_grid._last_point.x
        local_last_y: int = copy_checkbox_grid._last_point.y
        mock_locked_checkbox_move_rect.assert_called_once_with(
            copy_checkbox_grid.checkboxes[0], local_last_x, local_last_y, RESIZING_RATIO
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
            self.checkbox_grid._last_point.x, self.checkbox_grid._last_point.y, "center"
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
        self.assertEqual(copy_checkbox_grid._last_point.x, expected_last_x)
        self.assertEqual(copy_checkbox_grid._last_point.y, copy_checkbox_grid._init_pos.y)

        # Grid with 1 column

        copy_checkbox_grid._cols = 1
        copy_checkbox_grid._get_grid_from_fallback(IMG_1, None, RESIZING_RATIO)
        expected_last_y: int = copy_checkbox_grid._init_pos.y + copy_checkbox_grid._increment.y
        self.assertEqual(copy_checkbox_grid._last_point.x, copy_checkbox_grid._init_pos.x)
        self.assertEqual(copy_checkbox_grid._last_point.y, expected_last_y)
