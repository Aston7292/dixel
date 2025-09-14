"""Tests for the clickable file."""

from unittest import TestCase, mock
from unittest.mock import Mock
from typing import Final, Any

import pygame as pg
from pygame import SRCALPHA

from src.classes.clickable import _Clickable, Checkbox, Button
from src.classes.text_label import TextLabel
from src.classes.devices import _Mouse

from src.utils import RectPos, ObjInfo, resize_obj
from src.type_utils import XY, WH, BlitInfo
from src.consts import BLACK, ELEMENT_LAYER

from tests.utils import cmp_imgs

_OFF_IMG: Final[pg.Surface] = pg.Surface((10, 11), SRCALPHA)
_ON_IMG: Final[pg.Surface] = _OFF_IMG.copy()
_ON_IMG.fill((0, 0, 1, 0))


class TestCheckbox(TestCase):
    """Tests for the Checkbox class."""

    def _make_checkbox(self) -> Checkbox:
        """
        Creates a checkbox.

        Returns:
            checkbox
        """

        checkbox: Checkbox

        checkbox = Checkbox(RectPos(1, 2, "center"), [_OFF_IMG, _ON_IMG], "hello", "world\n!", 1)
        checkbox.resize(2, 3)
        return checkbox

    @mock.patch.object(TextLabel, "__init__", autospec=True, return_value=None)
    def test_init(self, mock_text_label_init: Mock) -> None:
        """Tests the init method, mocks TextLabel.__init__."""

        # Also tests the Clickable abstract class

        pos: RectPos = RectPos(1, 2, "center")
        checkbox: Checkbox = Checkbox(pos, [_OFF_IMG, _ON_IMG], "hello", "world\n!", 1)
        self.assertEqual(mock_text_label_init.call_count, 2)

        self.assertEqual(checkbox.init_pos, pos)
        self.assertListEqual(checkbox.init_imgs, [_OFF_IMG, _ON_IMG])

        self.assertListEqual(checkbox._imgs, [_OFF_IMG, _ON_IMG])
        self.assertEqual(checkbox.rect, _OFF_IMG.get_rect(center=(1, 2)))

        self.assertEqual(checkbox.img_i, 0)

        self.assertFalse(checkbox._is_hovering)

        self.assertEqual(checkbox.layer, 1 + ELEMENT_LAYER)

        hovering_text_label_init_call: mock._Call = mock_text_label_init.call_args_list[0]
        expected_hovering_text_label_init_args: tuple[Any, ...] = (
            checkbox.hovering_text_label, RectPos(0, 0, "topleft"),
            "world\n!", 2, 12, BLACK
        )
        self.assertTupleEqual(
            hovering_text_label_init_call[0], expected_hovering_text_label_init_args
        )

        # Checkbox attrs before extra TextLabel.__init__ calls

        self.assertFalse(checkbox.is_checked)

        text_label_init_args: mock._Call = mock_text_label_init.call_args_list[1]
        text_label: TextLabel = text_label_init_args[0]
        expected_text_label_init_args: tuple[Any, ...] = (
            text_label, RectPos(checkbox.rect.centerx, checkbox.rect.y - 5, "midbottom"),
            "hello", 1, 16
        )
        self.assertTupleEqual(text_label_init_args[0], expected_text_label_init_args)

        self.assertListEqual(checkbox.objs_info, [ObjInfo(text_label)])

        # Edge cases

        no_hovering_text_checkbox: Checkbox = Checkbox(pos, [_OFF_IMG, _ON_IMG], "hello", None)
        self.assertIsNone(no_hovering_text_checkbox.hovering_text_label)

    def test_blit_sequence(self) -> None:
        """Tests the blit_sequence attribute."""

        mouse_x: int
        mouse_y: int

        checkbox: Checkbox = self._make_checkbox()

        expected_sequence_0: list[BlitInfo] = [
            (checkbox._imgs[0], checkbox.rect, checkbox.layer)
        ]
        self.assertListEqual(checkbox.blit_sequence, expected_sequence_0)

        expected_sequence_1: list[BlitInfo] = [
            (checkbox._imgs[1], checkbox.rect, checkbox.layer)
        ]
        if checkbox.hovering_text_label is not None:
            mouse_x, mouse_y = pg.mouse.get_pos()
            checkbox.hovering_text_label.move_rect(mouse_x + 10, mouse_y, 1, 1)
            expected_sequence_1.extend(checkbox.hovering_text_label.get_blit_sequence())

        checkbox.img_i = 1
        checkbox._is_hovering = True
        self.assertListEqual(checkbox.blit_sequence, expected_sequence_1)

        # Hovering without hovering text

        checkbox.hovering_text_label = None
        expected_sequence_1 = [
            (checkbox._imgs[1], checkbox.rect, checkbox.layer)
        ]
        self.assertListEqual(checkbox.get_blit_sequence(), expected_sequence_1)

    def test_get_hovering(self) -> None:
        """Tests the get_hovering method."""

        is_hovering: bool
        layer: int

        checkbox: Checkbox = self._make_checkbox()

        is_hovering, layer = checkbox.get_hovering(checkbox.rect.topleft)
        self.assertTrue(is_hovering)
        self.assertEqual(layer, 1 + ELEMENT_LAYER)

        is_hovering, layer = checkbox.get_hovering((checkbox.rect.x - 1, 0))
        self.assertFalse(is_hovering)

    def test_leave(self) -> None:
        """Tests the leave method."""

        checkbox: Checkbox = self._make_checkbox()
        checkbox._is_hovering = True
        checkbox.leave()

        self.assertFalse(checkbox._is_hovering)

    @mock.patch.object(TextLabel, "resize", autospec=True, wraps=TextLabel.resize)
    def test_resize(self, mock_text_label_resize: Mock) -> None:
        """Tests the resize method, mocks TextLabel.resize."""

        init_w: int
        init_h: int
        expected_xy: XY
        expected_wh: WH
        img: pg.Surface
        expected_img: pg.Surface

        checkbox: Checkbox = Checkbox(
            RectPos(1, 2, "center"),
            [_OFF_IMG, _ON_IMG], "hello", "world\n!", 1
        )
        checkbox.resize(2, 3)

        init_w, init_h = _OFF_IMG.get_size()

        expected_xy, expected_wh = resize_obj(checkbox.init_pos, init_w, init_h, 2, 3)
        expected_imgs: list[pg.Surface] = [
            pg.transform.scale(img, expected_wh).convert() for img in checkbox.init_imgs
        ]
        expected_rect: pg.Rect = expected_imgs[0].get_rect(center=expected_xy)

        for img, expected_img in zip(checkbox._imgs, expected_imgs, strict=True):
            self.assertTrue(cmp_imgs(img, expected_img))
        self.assertEqual(checkbox.rect, expected_rect)

        text_label: TextLabel | None = checkbox.hovering_text_label
        mock_text_label_resize.assert_called_once_with(text_label, 2, 3)

        checkbox.hovering_text_label = None
        checkbox.resize(2, 3)  # Assert it doesn't crash

    def test_move_rect(self) -> None:
        """Tests the move_rect method."""

        expected_xy: XY
        _expected_wh: WH

        checkbox: Checkbox = self._make_checkbox()
        checkbox.move_rect(3, 4, 2, 3)

        expected_xy, _expected_wh = resize_obj(checkbox.init_pos, 0, 0, 2, 3)
        self.assertEqual(checkbox.init_pos.x, 3)
        self.assertEqual(checkbox.init_pos.y, 4)
        self.assertTupleEqual(checkbox.rect.center, expected_xy)

    def test_upt(self) -> None:
        """Tests the upt method."""

        checkbox: Checkbox = self._make_checkbox()
        mouse_info: _Mouse = _Mouse(0, 0, [False] * 3, [True] * 3, 0)
        blank_mouse_info: _Mouse = _Mouse(0, 0, [False] * 3, [False] * 3, 0)

        # Don't hover and click
        self.assertFalse(checkbox.upt(None, mouse_info))

        # Hover and click twice
        self.assertTrue(checkbox.upt(checkbox, mouse_info))
        self.assertTrue(checkbox.is_checked)
        self.assertEqual(checkbox.img_i, 1)
        self.assertFalse(checkbox.upt(checkbox, mouse_info))
        self.assertFalse(checkbox.is_checked)
        self.assertEqual(checkbox.img_i, 0)

        # Check twice with shortcut
        self.assertTrue(checkbox.upt(None, mouse_info, True))
        self.assertTrue(checkbox.is_checked)
        self.assertFalse(checkbox.upt(None, mouse_info, True))
        self.assertFalse(checkbox.is_checked)

        # Don't hover and don't click
        self.assertFalse(checkbox.upt(None, mouse_info))
        # Hover and don't click
        self.assertFalse(checkbox.upt(checkbox, blank_mouse_info))


class TestButton(TestCase):
    """Tests for the Button class."""

    def _make_button(self) -> Button:
        """
        Creates a button.

        Returns:
            button
        """

        btn: Button

        btn = Button(RectPos(1, 2, "center"), [_OFF_IMG, _ON_IMG], "hello", "world\n!", 1, 10)
        btn.resize(2, 3)
        return btn

    @mock.patch.object(TextLabel, "__init__", autospec=True, return_value=None)
    @mock.patch.object(_Clickable, "__init__", autospec=True, wraps=_Clickable.__init__)
    def test_init(self, mock_clickable_init: Mock, mock_text_label_init: Mock) -> None:
        """Tests the init method, mocks Clickable.__init__ and TextLabel.__init__."""

        pos: RectPos = RectPos(1, 2, "center")
        imgs: list[pg.Surface] = [_OFF_IMG, _ON_IMG]

        btn: Button = Button(pos, imgs, "hello", "world\n!", 1, 10)
        mock_clickable_init.assert_called_once_with(btn, pos, imgs, "world\n!", 1)
        self.assertEqual(mock_text_label_init.call_count, 2)

        text_label: TextLabel = mock_text_label_init.call_args[0][0]
        mock_text_label_init.assert_called_with(
            text_label, RectPos(btn.rect.centerx, btn.rect.centery, "center"),
            "hello", 1, 10
        )
        self.assertListEqual(btn.objs_info, [ObjInfo(text_label)])

        no_text_btn: Button = Button(pos, imgs, None, None)
        self.assertListEqual(no_text_btn.objs_info, [])

    def test_upt(self) -> None:
        """Tests the upt method."""

        btn: Button = self._make_button()
        mouse_info: _Mouse = _Mouse(0, 0, [False] * 3, [True] * 3, 0)
        blank_mouse_info: _Mouse = _Mouse(0, 0, [False] * 3, [False] * 3, 0)

        # Don't hover and click
        self.assertFalse(btn.upt(None, mouse_info))
        self.assertEqual(btn.img_i, 0)

        # Hover and click
        btn._is_hovering = False
        self.assertTrue(btn.upt(btn, mouse_info))
        self.assertEqual(btn.img_i, 1)

        # Don't hover and don't click
        self.assertFalse(btn.upt(None, blank_mouse_info))
        # Hover and don't click
        self.assertFalse(btn.upt(btn, blank_mouse_info))
