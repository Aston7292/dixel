"""Tests for the clickable file."""

from unittest import TestCase, mock
from itertools import zip_longest
from typing import Final, Optional, Any

import pygame as pg

from src.classes.clickable import Clickable, Checkbox, Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio, ObjInfo, MouseInfo, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import BLACK, ELEMENT_LAYER

from tests.utils import cmp_imgs, RESIZING_RATIO

IMG_OFF: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_ON: Final[pg.Surface] = IMG_OFF.copy()
IMG_ON.fill((0, 0, 1, 0))


class TestCheckbox(TestCase):
    """Tests for the Checkbox class."""

    checkbox: Checkbox

    @classmethod
    def setUpClass(cls: type["TestCheckbox"]) -> None:
        """Creates the checkbox."""

        cls.checkbox = Checkbox(RectPos(1, 2, "center"), (IMG_OFF, IMG_ON), "hello", "world\n!", 1)

    def _copy_checkbox(self) -> Checkbox:
        """
        Creates a copy of the checkbox.

        Returns:
            copy
        """

        text: str = self.checkbox.objs_info[0].obj.text
        hovering_text: Optional[str] = None
        if self.checkbox._hovering_text_label:
            hovering_text = self.checkbox._hovering_text_label.text
        layer: int = self.checkbox._layer - ELEMENT_LAYER

        copy_checkbox: Checkbox = Checkbox(
            self.checkbox.init_pos, self.checkbox._init_imgs, text, hovering_text, layer
        )
        copy_checkbox.resize(RESIZING_RATIO)

        return copy_checkbox

    @mock.patch.object(TextLabel, "__init__", autospec=True, return_value=None)
    def test_init(self, mock_text_label_init: mock.Mock) -> None:
        """Tests the init method, mocks the TextLabel.__init__ method."""

        # Also tests the Clickable abstract class

        test_checkbox: Checkbox = Checkbox(
            RectPos(1, 2, "center"), (IMG_OFF, IMG_ON), "hello", "world\n!", 1
        )
        self.assertEqual(mock_text_label_init.call_count, 2)

        self.assertEqual(test_checkbox.init_pos, RectPos(1, 2, "center"))
        self.assertTupleEqual(test_checkbox._init_imgs, (IMG_OFF, IMG_ON))

        self.assertTupleEqual(test_checkbox._imgs, (IMG_OFF, IMG_ON))
        self.assertEqual(test_checkbox.rect, IMG_OFF.get_rect(center=(1, 2)))

        self.assertEqual(test_checkbox.img_i, 0)

        self.assertFalse(test_checkbox._is_hovering)

        self.assertEqual(test_checkbox._layer, 1 + ELEMENT_LAYER)

        hovering_text_label_init_args: tuple[Any, ...] = mock_text_label_init.call_args_list[0][0]
        expected_hovering_text_label_init_args: tuple[Any, ...] = (
            test_checkbox._hovering_text_label, RectPos(0, 0, "topleft"), "world\n!", 2, 12, BLACK
        )
        self.assertTupleEqual(
            hovering_text_label_init_args, expected_hovering_text_label_init_args
        )

        # Checkbox attrs before extra TextLabel.__init__ calls

        self.assertFalse(test_checkbox.is_checked)

        text_label_init_args: tuple[Any, ...] = mock_text_label_init.call_args_list[1][0]
        text_label: TextLabel = text_label_init_args[0]
        expected_text_label_init_args: tuple[Any, ...] = (
            text_label, RectPos(test_checkbox.rect.centerx, test_checkbox.rect.y - 5, "midbottom"),
            "hello", 1, 16
        )
        self.assertTupleEqual(text_label_init_args, expected_text_label_init_args)

        self.assertListEqual(test_checkbox.objs_info, [ObjInfo(text_label)])

        # Edge cases

        no_hovering_text_checkbox: Checkbox = Checkbox(
            RectPos(0, 0, "topleft"), (IMG_OFF, IMG_ON), "hello", None
        )
        self.assertIsNone(no_hovering_text_checkbox._hovering_text_label)

    def test_blit(self) -> None:
        """Tests the blit method."""

        copy_checkbox: Checkbox = self._copy_checkbox()

        expected_sequence_0: list[LayeredBlitInfo] = [
            (copy_checkbox._imgs[0], copy_checkbox.rect.topleft, copy_checkbox._layer)
        ]
        self.assertListEqual(copy_checkbox.blit(), expected_sequence_0)

        copy_checkbox.img_i = 1
        copy_checkbox._is_hovering = True
        sequence_1: list[LayeredBlitInfo] = copy_checkbox.blit()

        expected_sequence_1: list[LayeredBlitInfo] = [
            (copy_checkbox._imgs[1], copy_checkbox.rect.topleft, copy_checkbox._layer)
        ]
        if copy_checkbox._hovering_text_label:
            mouse_x: int
            mouse_y: int
            mouse_x, mouse_y = pg.mouse.get_pos()
            copy_checkbox._hovering_text_label.move_rect(mouse_x + 15, mouse_y, Ratio(1, 1))
            expected_sequence_1.extend(copy_checkbox._hovering_text_label.blit())

        self.assertListEqual(sequence_1, expected_sequence_1)

        # Hovering without hovering text

        copy_checkbox._hovering_text_label = None
        expected_sequence_1 = [
            (copy_checkbox._imgs[1], copy_checkbox.rect.topleft, copy_checkbox._layer)
        ]
        self.assertListEqual(copy_checkbox.blit(), expected_sequence_1)

    def test_get_hovering_info(self) -> None:
        """Tests the get_hovering_info method."""

        is_hovering: bool
        layer: int
        is_hovering, layer = self.checkbox.get_hovering_info(self.checkbox.rect.topleft)
        self.assertTrue(is_hovering)
        self.assertEqual(layer, 1 + ELEMENT_LAYER)

        is_hovering, layer = self.checkbox.get_hovering_info((self.checkbox.rect.x - 1, 0))
        self.assertFalse(is_hovering)

    def test_leave(self) -> None:
        """Tests the leave method."""

        copy_checkbox: Checkbox = self._copy_checkbox()
        copy_checkbox._is_hovering = True
        copy_checkbox.leave()

        self.assertFalse(copy_checkbox._is_hovering)

    @mock.patch.object(TextLabel, "resize", autospec=True, wraps=TextLabel.resize)
    def test_a_resize(self, mock_text_label_resize: mock.Mock) -> None:
        """Tests the resize method as first, mocks the TextLabel.resize method."""

        self.checkbox.resize(RESIZING_RATIO)

        expected_xy: PosPair
        expected_wh: SizePair
        expected_xy, expected_wh = resize_obj(
            self.checkbox.init_pos, *IMG_OFF.get_size(), RESIZING_RATIO
        )

        expected_imgs: tuple[pg.Surface, ...] = tuple(
            pg.transform.scale(img, expected_wh) for img in self.checkbox._init_imgs
        )
        expected_rect: pg.Rect = expected_imgs[0].get_rect(center=expected_xy)

        for img, expected_img in zip_longest(self.checkbox._imgs, expected_imgs):
            self.assertTrue(cmp_imgs(img, expected_img))
        self.assertEqual(self.checkbox.rect, expected_rect)

        mock_text_label_resize.assert_called_once_with(
            self.checkbox._hovering_text_label, RESIZING_RATIO
        )

        copy_checkbox: Checkbox = self._copy_checkbox()
        copy_checkbox._hovering_text_label = None
        copy_checkbox.resize(RESIZING_RATIO)  # Assert it doesn't crash

    def test_move_rect(self) -> None:
        """Tests the move_rect method."""

        copy_checkbox: Checkbox = self._copy_checkbox()
        copy_checkbox.move_rect(3, 4, Ratio(2.1, 3.2))

        expected_xy: PosPair
        expected_xy, _ = resize_obj(copy_checkbox.init_pos, 0, 0, Ratio(2.1, 3.2))

        self.assertEqual(copy_checkbox.init_pos.x, 3)
        self.assertEqual(copy_checkbox.init_pos.y, 4)
        self.assertTupleEqual(copy_checkbox.rect.center, expected_xy)

    @mock.patch.object(pg.mouse, "set_cursor", autospec=True)
    def test_handle_hover(self, mock_set_cursor: mock.Mock) -> None:
        """Tests the Clickable._handle_hover method, mocks the pygame.set_cursor function."""

        copy_checkbox: Checkbox = self._copy_checkbox()

        copy_checkbox._is_hovering = True
        copy_checkbox._handle_hover(None)
        self.assertFalse(copy_checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_ARROW)

        copy_checkbox._handle_hover(copy_checkbox)
        self.assertTrue(copy_checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_HAND)

    @mock.patch.object(Clickable, "_handle_hover", autospec=True, wraps=Clickable._handle_hover)
    def test_upt(self, mock_handle_hover: mock.Mock) -> None:
        """Tests the upt method, mocks the Clickable._check_hover method."""

        copy_checkbox: Checkbox = self._copy_checkbox()
        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5, 0)
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5, 0)

        # Don't hover and click
        self.assertFalse(copy_checkbox.upt(None, mouse_info))
        mock_handle_hover.assert_called_once_with(copy_checkbox, None)

        # Hover and click twice
        self.assertTrue(copy_checkbox.upt(copy_checkbox, mouse_info))
        self.assertTrue(copy_checkbox.is_checked)
        self.assertEqual(copy_checkbox.img_i, 1)
        self.assertFalse(copy_checkbox.upt(copy_checkbox, mouse_info))
        self.assertFalse(copy_checkbox.is_checked)
        self.assertEqual(copy_checkbox.img_i, 0)

        # Check twice with shortcut
        self.assertTrue(copy_checkbox.upt(None, mouse_info, True))
        self.assertTrue(copy_checkbox.is_checked)
        self.assertFalse(copy_checkbox.upt(None, mouse_info, True))
        self.assertFalse(copy_checkbox.is_checked)

        # Don't hover and don't click
        self.assertFalse(copy_checkbox.upt(None, mouse_info))
        # Hover and don't click
        self.assertFalse(copy_checkbox.upt(copy_checkbox, blank_mouse_info))


class TestButton(TestCase):
    """Tests for the Button class."""

    button: Button

    @classmethod
    def setUpClass(cls: type["TestButton"]) -> None:
        """Creates the button."""

        cls.button = Button(RectPos(1, 2, "center"), (IMG_OFF, IMG_ON), "hello", "world\n!", 1, 10)

    def _copy_button(self) -> Button:
        """
        Creates a copy of the button.

        Returns:
            copy
        """

        text: str = self.button.objs_info[0].obj.text
        hovering_text: Optional[str] = None
        if self.button._hovering_text_label:
            hovering_text = self.button._hovering_text_label.text
        layer: int = self.button._layer - ELEMENT_LAYER
        text_h: int = self.button.objs_info[0].obj._init_h

        copy_button: Button = Button(
            self.button.init_pos, self.button._init_imgs, text, hovering_text, layer, text_h
        )
        copy_button.resize(RESIZING_RATIO)

        return copy_button

    @mock.patch.object(TextLabel, "__init__", autospec=True, return_value=None)
    @mock.patch.object(Clickable, "__init__", autospec=True, wraps=Clickable.__init__)
    def test_init(self, mock_clickable_init: mock.Mock, mock_text_label_init: mock.Mock) -> None:
        """Tests the init method, mocks the Clickable.__init__ and TextLabel.__init__ methods."""

        test_button: Button = Button(
            RectPos(1, 2, "center"), (IMG_OFF, IMG_ON), "hello", "world\n!", 1, 10
        )
        mock_clickable_init.assert_called_once_with(
            test_button, RectPos(1, 2, "center"), (IMG_OFF, IMG_ON), "world\n!", 1
        )
        self.assertEqual(mock_text_label_init.call_count, 2)

        text_label: TextLabel = mock_text_label_init.call_args[0][0]
        mock_text_label_init.assert_called_with(
            text_label, RectPos(*test_button.rect.center, "center"), "hello", 1, 10
        )
        self.assertListEqual(test_button.objs_info, [ObjInfo(text_label)])

        no_text_button: Button = Button(RectPos(0, 0, "topleft"), (IMG_OFF, IMG_ON), None, None)
        self.assertListEqual(no_text_button.objs_info, [])

    @mock.patch.object(Clickable, "_handle_hover", autospec=True, wraps=Clickable._handle_hover)
    def test_upt(self, mock_handle_hover: mock.Mock) -> None:
        """Tests the upt method, mocks the Clickable._check_hover method."""

        copy_button: Button = self._copy_button()
        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5, 0)
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5, 0)

        # Don't hover and click
        self.assertFalse(copy_button.upt(None, mouse_info))
        mock_handle_hover.assert_called_once_with(copy_button, None)
        self.assertEqual(copy_button.img_i, 0)

        # Hover and click
        copy_button._is_hovering = False
        self.assertTrue(copy_button.upt(copy_button, mouse_info))
        self.assertEqual(copy_button.img_i, 1)

        # Don't hover and don't click
        self.assertFalse(copy_button.upt(None, blank_mouse_info))
        # Hover and don't click
        self.assertFalse(copy_button.upt(copy_button, blank_mouse_info))
