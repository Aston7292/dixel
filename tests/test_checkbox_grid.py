"""Tests for the checkbox grid file."""

from unittest import TestCase, mock
from typing import Final, Optional

import pygame as pg

from src.classes.checkbox_grid import LockedCheckbox, CheckboxGrid
from src.classes.clickable import Clickable
from src.classes.text_label import TextLabel

from src.utils import RectPos, Size, Ratio, ObjInfo, MouseInfo, add_border, resize_obj
from src.type_utils import CheckboxInfo
from src.consts import WHITE, ELEMENT_LAYER

from tests.utils import cmp_imgs, cmp_hovering_text, RESIZING_RATIO

IMG_1: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_2: Final[pg.Surface] = IMG_1.copy()
IMG_2.fill((0, 0, 1, 0))


class TestLockedCheckbox(TestCase):
    """Tests for the LockedCheckbox class."""

    locked_checkbox: LockedCheckbox

    @classmethod
    def setUpClass(cls: type["TestLockedCheckbox"]) -> None:
        """Creates the checkbox."""

        cls.locked_checkbox = LockedCheckbox(RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", 1)

    def copy_locked_checkbox(self) -> LockedCheckbox:
        """
        Creates a copy of the locked checkbox.

        Returns:
            copy
        """

        hovering_text: Optional[str] = None
        if self.locked_checkbox._hovering_text_label:
            hovering_text = self.locked_checkbox._hovering_text_label.text
        layer: int = self.locked_checkbox._layer - ELEMENT_LAYER

        locked_checkbox_copy: LockedCheckbox = LockedCheckbox(
            self.locked_checkbox.init_pos, self.locked_checkbox._init_imgs, hovering_text, layer
        )
        locked_checkbox_copy.resize(RESIZING_RATIO)

        return locked_checkbox_copy

    @mock.patch.object(Clickable, '__init__', autospec=True, wraps=Clickable.__init__)
    def test_init(self, clickable_init_mock: mock.Mock) -> None:
        """Tests the init method, mocks the Clickable.__init__ method."""

        test_locked_checkbox: LockedCheckbox = LockedCheckbox(
            RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", 1
        )
        clickable_init_mock.assert_called_once_with(
            test_locked_checkbox, RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", 1
        )

        self.assertFalse(test_locked_checkbox.is_checked)

    @mock.patch.object(Clickable, "_base_blit")
    def test_blit(self, base_blit_mock: mock.Mock) -> None:
        """Tests the blit method, mocks the Clickable._base_blit method."""

        locked_checkbox_copy: LockedCheckbox = self.copy_locked_checkbox()

        locked_checkbox_copy.blit()
        base_blit_mock.assert_called_with(0)

        locked_checkbox_copy._is_hovering = True
        locked_checkbox_copy.blit()
        base_blit_mock.assert_called_with(1)
        locked_checkbox_copy._is_hovering = False

        locked_checkbox_copy.is_checked = True
        locked_checkbox_copy.blit()
        base_blit_mock.assert_called_with(1)

    @mock.patch.object(TextLabel, "set_text", autospec=True, wraps=TextLabel.set_text)
    def test_set_info(self, set_text_mock: mock.Mock) -> None:
        """Tests the set_info method, mocks the TextLabel.set_text method."""

        checkbox_copy: LockedCheckbox = self.copy_locked_checkbox()
        checkbox_copy.set_info((IMG_2, IMG_1), "world")

        self.assertTupleEqual(checkbox_copy._init_imgs, (IMG_2, IMG_1))
        self.assertTupleEqual(checkbox_copy._imgs, checkbox_copy._init_imgs)

        set_text_mock.assert_called_once_with(checkbox_copy._hovering_text_label, "world")

        if checkbox_copy._hovering_text_label:
            local_hovering_text_label: TextLabel = checkbox_copy._hovering_text_label
            expected_hovering_text_h: int
            _, (_, expected_hovering_text_h) = resize_obj(
                local_hovering_text_label.init_pos, 0.0, local_hovering_text_label._init_h,
                RESIZING_RATIO, True
            )
            local_hovering_text_imgs: tuple[pg.Surface, ...] = checkbox_copy._hovering_text_imgs

            self.assertTrue(
                cmp_hovering_text(expected_hovering_text_h, "world", local_hovering_text_imgs)
            )

    @mock.patch.object(pg.mouse, 'set_cursor')
    def test_upt(self, set_cursor_mock: mock.Mock) -> None:
        """Tests the upt method, mocks the pygame.mouse.set_cursor method."""

        locked_checkbox_copy: LockedCheckbox = self.copy_locked_checkbox()
        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)

        # Leave hover and click
        locked_checkbox_copy._is_hovering = True
        self.assertFalse(locked_checkbox_copy.upt(None, mouse_info))
        self.assertFalse(locked_checkbox_copy._is_hovering)
        set_cursor_mock.assert_called_once_with(pg.SYSTEM_CURSOR_ARROW)

        # Enter hover and click twice
        self.assertTrue(locked_checkbox_copy.upt(locked_checkbox_copy, mouse_info))
        self.assertTrue(locked_checkbox_copy.is_checked)
        self.assertTrue(locked_checkbox_copy.upt(locked_checkbox_copy, mouse_info))
        self.assertTrue(locked_checkbox_copy.is_checked)
        self.assertTrue(locked_checkbox_copy._is_hovering)
        set_cursor_mock.assert_called_with(pg.SYSTEM_CURSOR_HAND)

        # Don't hover and don't click
        self.assertFalse(locked_checkbox_copy.upt(None, blank_mouse_info))
        # Hover and don't click
        self.assertFalse(locked_checkbox_copy.upt(locked_checkbox_copy, blank_mouse_info))


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
            RectPos(1, 2, 'center'), cls.init_info, 2, cls.inverted_axes, 1
        )

    def copy_checkbox_grid(self) -> CheckboxGrid:
        """
        Creates a copy of the checkbox grid.

        Returns:
            copy
        """

        return CheckboxGrid(
            self.checkbox_grid._init_pos, self.init_info, self.checkbox_grid._cols,
            self.inverted_axes, self.checkbox_grid._layer
        )

    @mock.patch.object(CheckboxGrid, 'set_grid', autospec=True, wraps=CheckboxGrid.set_grid)
    def test_init(self, set_grid_mock: mock.Mock) -> None:
        """Tests the init method, mocks the CheckboxGrid.set_grid method."""

        test_checkbox_grid: CheckboxGrid = CheckboxGrid(
            RectPos(1, 2, 'center'), self.init_info, 2, self.inverted_axes, 1
        )

        self.assertEqual(test_checkbox_grid._init_pos, RectPos(1, 2, 'center'))

        self.assertEqual(test_checkbox_grid._cols, 2)
        self.assertEqual(
            test_checkbox_grid._increment, Size(-IMG_1.get_width() - 10, -IMG_1.get_height() - 10)
        )

        self.assertEqual(test_checkbox_grid._layer, 1)

        set_grid_mock.assert_called_once_with(test_checkbox_grid, self.init_info, Ratio(1.0, 1.0))

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

        checkbox_grid_copy: CheckboxGrid = self.copy_checkbox_grid()
        checkbox_grid_copy.rect = pg.Rect()
        checkbox_grid_copy.post_resize()

        rects: tuple[pg.Rect, ...] = tuple(
            checkbox.rect for checkbox in checkbox_grid_copy.checkboxes
        )
        expected_left: int = min(rect.left for rect in rects)
        expected_top: int = min(rect.top for rect in rects)
        expected_w: int = max(rect.right for rect in rects) - expected_left
        expected_h: int = max(rect.bottom for rect in rects) - expected_top
        expected_rect: pg.Rect = pg.Rect(expected_left, expected_top, expected_w, expected_h)
        self.assertEqual(checkbox_grid_copy.rect, expected_rect)

    def test_check(self) -> None:
        """Tests the check method."""

        grid_copy: CheckboxGrid = self.copy_checkbox_grid()

        grid_copy.checkboxes[grid_copy.clicked_i].is_checked = False
        grid_copy.clicked_i = 1
        grid_copy.checkboxes[grid_copy.clicked_i].is_checked = True
        grid_copy.check(0)

        self.assertEqual(grid_copy.clicked_i, 0)
        self.assertFalse(grid_copy.checkboxes[1].is_checked)
        self.assertTrue(grid_copy.checkboxes[grid_copy.clicked_i].is_checked)

        # clicked_i out of range
        grid_copy.clicked_i = len(grid_copy.checkboxes)
        grid_copy.check(0)

    def test_set_grid(self) -> None:
        """Tests the set_grid method."""

        checkbox_grid_copy: CheckboxGrid = self.copy_checkbox_grid()

        module_path: str = "src.classes.checkbox_grid."
        locked_checkbox_init_patch: mock._patch = mock.patch(
            module_path + "LockedCheckbox.__init__", autospec=True, wraps=LockedCheckbox.__init__
        )
        locked_checkbox_resize_patch: mock._patch = mock.patch(
            module_path + "LockedCheckbox.resize"
        )
        checkbox_grid_check_patch: mock._patch = mock.patch(module_path + "CheckboxGrid.check")

        locked_checkbox_init_mock: mock.Mock = locked_checkbox_init_patch.start()
        locked_checkbox_resize_mock: mock.Mock = locked_checkbox_resize_patch.start()
        checkbox_grid_check_mock: mock.Mock = checkbox_grid_check_patch.start()

        checkbox_grid_copy.set_grid(((IMG_2, None),) * 10, Ratio(2.0, 3.0))
        locked_checkbox_init_patch.stop()
        locked_checkbox_resize_patch.stop()
        checkbox_grid_check_patch.stop()

        self.assertEqual(locked_checkbox_init_mock.call_count, 10)
        self.assertEqual(locked_checkbox_resize_mock.call_count, 10)
        self.assertEqual(len(checkbox_grid_copy.checkboxes), 10)

        last_x: int = checkbox_grid_copy._init_pos.x
        last_y: int = checkbox_grid_copy._init_pos.y
        for i, args in enumerate(locked_checkbox_init_mock.call_args_list):
            self.assertEqual(
                args[0][1], RectPos(last_x, last_y, checkbox_grid_copy._init_pos.coord_type)
            )
            self.assertTrue(cmp_imgs(args[0][2][0], IMG_2))
            self.assertTrue(cmp_imgs(args[0][2][1], add_border(IMG_2, WHITE)))
            self.assertIsNone(args[0][3])
            self.assertEqual(args[0][4], checkbox_grid_copy._layer)

            last_x += checkbox_grid_copy._increment.w
            if not (i + 1) % checkbox_grid_copy._cols:
                last_x = checkbox_grid_copy._init_pos.x
                last_y += checkbox_grid_copy._increment.h

        rects: tuple[pg.Rect, ...] = tuple(
            checkbox.rect for checkbox in checkbox_grid_copy.checkboxes
        )
        expected_left: int = min(rect.left for rect in rects)
        expected_top: int = min(rect.top for rect in rects)
        expected_w: int = max(rect.right for rect in rects) - expected_left
        expected_h: int = max(rect.bottom for rect in rects) - expected_top
        expected_rect: pg.Rect = pg.Rect(expected_left, expected_top, expected_w, expected_h)
        self.assertEqual(checkbox_grid_copy.rect, expected_rect)

        expected_objs_info: list[ObjInfo] = [
            ObjInfo(checkbox) for checkbox in checkbox_grid_copy.checkboxes
        ]
        self.assertListEqual(checkbox_grid_copy.objs_info, expected_objs_info)

        checkbox_grid_check_mock.assert_called_once_with(0)
