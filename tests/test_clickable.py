"""Tests for the clickable file."""

from unittest import TestCase, mock
from itertools import zip_longest
from typing import Final, Optional, Any

import pygame as pg

from src.classes.clickable import Clickable, Checkbox, Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio, ObjInfo, MouseInfo, resize_obj
from src.type_utils import LayeredBlitSequence
from src.consts import ELEMENT_LAYER, TOP_LAYER

from tests.utils import cmp_imgs, cmp_hovering_text, RESIZING_RATIO

IMG_1: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_2: Final[pg.Surface] = IMG_1.copy()
IMG_2.fill((0, 0, 1, 0))


class TestCheckbox(TestCase):
    """Tests for the Checkbox class."""

    checkbox: Checkbox

    @classmethod
    def setUpClass(cls: type["TestCheckbox"]) -> None:
        """Creates the checkbox."""

        cls.checkbox = Checkbox(RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", "world\n!", 1)

    def copy_checkbox(self) -> Checkbox:
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

        checkbox_copy: Checkbox = Checkbox(
            self.checkbox.init_pos, self.checkbox._init_imgs, text, hovering_text, layer
        )
        checkbox_copy.resize(RESIZING_RATIO)

        return checkbox_copy

    @mock.patch.object(TextLabel, '__init__', autospec=True, wraps=TextLabel.__init__)
    def test_init(self, text_label_init_mock: mock.Mock) -> None:
        """Tests the init method, mocks the TextLabel.__init__ method."""

        # Also tests the Clickable abstract class

        test_checkbox: Checkbox = Checkbox(
            RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", "world\n!", 1
        )

        self.assertEqual(test_checkbox.init_pos, RectPos(1, 2, 'center'))
        self.assertTupleEqual(test_checkbox._init_imgs, (IMG_1, IMG_2))

        self.assertTupleEqual(test_checkbox._imgs, test_checkbox._init_imgs)
        expected_rect: pg.Rect = IMG_1.get_rect(**{test_checkbox.init_pos.coord_type: (1, 2)})
        self.assertEqual(test_checkbox.rect, expected_rect)

        self.assertFalse(test_checkbox._is_hovering)

        self.assertEqual(test_checkbox._layer, 1 + ELEMENT_LAYER)
        self.assertEqual(test_checkbox._hovering_layer, 1 + TOP_LAYER)

        self.assertTrue(cmp_hovering_text(12, "world\n!", test_checkbox._hovering_text_imgs))

        no_hovering_text_checkbox: Checkbox = Checkbox(
            RectPos(0, 0, 'topleft'), (IMG_1, IMG_2), "hello", None
        )
        self.assertIsNone(no_hovering_text_checkbox._hovering_text_label)
        self.assertTupleEqual(no_hovering_text_checkbox._hovering_text_imgs, ())

        # Checkbox attrs

        self.assertFalse(test_checkbox.is_checked)

        text_label_init_args: tuple[Any, ...] = text_label_init_mock.call_args_list[1][0]
        text_label: TextLabel = text_label_init_args[0]
        expected_text_label_init_args: tuple[Any, ...] = (
            text_label, RectPos(test_checkbox.rect.centerx, test_checkbox.rect.y - 5, 'midbottom'),
            "hello", 1, 16
        )
        self.assertTupleEqual(text_label_init_args, expected_text_label_init_args)
        self.assertListEqual(test_checkbox.objs_info, [ObjInfo(text_label)])

    def test_base_blit(self) -> None:
        """Tests the base_blit method."""

        checkbox_copy: Checkbox = self.copy_checkbox()

        expected_sequence_0: LayeredBlitSequence = [
            (checkbox_copy._imgs[0], checkbox_copy.rect.topleft, checkbox_copy._layer)
        ]
        self.assertListEqual(checkbox_copy._base_blit(0), expected_sequence_0)

        expected_sequence_1: LayeredBlitSequence = [
            (checkbox_copy._imgs[1], checkbox_copy.rect.topleft, checkbox_copy._layer)
        ]

        expected_hovering_text_line_x: int = pg.mouse.get_pos()[0] + 15
        expected_hovering_text_line_y: int = pg.mouse.get_pos()[1]
        for img in checkbox_copy._hovering_text_imgs:
            expected_sequence_1.append((
                img, (expected_hovering_text_line_x, expected_hovering_text_line_y),
                checkbox_copy._hovering_layer
            ))
            expected_hovering_text_line_y += img.get_height()

        checkbox_copy._is_hovering = True
        self.assertListEqual(checkbox_copy._base_blit(1), expected_sequence_1)

    def test_check_hovering(self) -> None:
        """Tests the check_hovering method."""

        hovered_obj: Optional[Checkbox]
        layer: int
        hovered_obj, layer = self.checkbox.check_hovering(self.checkbox.rect.topleft)
        self.assertIs(hovered_obj, self.checkbox)
        self.assertEqual(layer, 1 + ELEMENT_LAYER)

        hovered_obj, layer = self.checkbox.check_hovering((self.checkbox.rect.x - 1, 0))
        self.assertIsNone(hovered_obj)

    def test_leave(self) -> None:
        """Tests the leave method."""

        checkbox_copy: Checkbox = self.copy_checkbox()
        checkbox_copy._is_hovering = True
        checkbox_copy.leave()

        self.assertFalse(checkbox_copy._is_hovering)

    def test_a_resize(self) -> None:
        """Tests the resize method as first."""

        self.checkbox.resize(RESIZING_RATIO)

        expected_pos: tuple[int, int]
        expected_size: tuple[int, int]
        expected_pos, expected_size = resize_obj(
            self.checkbox.init_pos, *self.checkbox._init_imgs[0].get_size(), RESIZING_RATIO
        )

        expected_imgs: tuple[pg.Surface, ...] = tuple(
            pg.transform.scale(img, expected_size) for img in self.checkbox._init_imgs
        )
        expected_rect: pg.Rect = expected_imgs[0].get_rect(
            **{self.checkbox.init_pos.coord_type: expected_pos}
        )

        for img, expected_img in zip_longest(self.checkbox._imgs, expected_imgs):
            self.assertTrue(cmp_imgs(img, expected_img))
        self.assertEqual(self.checkbox.rect, expected_rect)

        if self.checkbox._hovering_text_label:
            local_hovering_text_label: TextLabel = self.checkbox._hovering_text_label
            expected_hovering_text_h: int
            _, (_, expected_hovering_text_h) = resize_obj(
                local_hovering_text_label.init_pos, 0.0, local_hovering_text_label._init_h,
                RESIZING_RATIO, True
            )
            local_hovering_text_imgs: tuple[pg.Surface, ...] = self.checkbox._hovering_text_imgs

            self.assertTrue(
                cmp_hovering_text(expected_hovering_text_h, "world\n!", local_hovering_text_imgs)
            )

    def test_move_rect(self) -> None:
        """Tests the move_rect method."""

        checkbox_copy: Checkbox = self.copy_checkbox()
        checkbox_copy.move_rect(3, 4, Ratio(2.1, 3.2))

        self.assertEqual(checkbox_copy.init_pos.x, 3)
        self.assertEqual(checkbox_copy.init_pos.y, 4)
        xy: tuple[int, int] = getattr(checkbox_copy.rect, checkbox_copy.init_pos.coord_type)
        self.assertTupleEqual(
            xy, (round(checkbox_copy.init_pos.x * 2.1), round(checkbox_copy.init_pos.y * 3.2))
        )

    @mock.patch.object(Clickable, "_base_blit")
    def test_blit(self, base_blit_mock: mock.Mock) -> None:
        """Tests the blit method, mocks the Clickable._base_blit method."""

        checkbox_copy: Checkbox = self.copy_checkbox()

        checkbox_copy.blit()
        base_blit_mock.assert_called_with(0)

        checkbox_copy.is_checked = True
        checkbox_copy.blit()
        base_blit_mock.assert_called_with(1)

    @mock.patch.object(pg.mouse, 'set_cursor')
    def test_upt(self, set_cursor_mock: mock.Mock) -> None:
        """Tests the upt method, mocks the pygame.mouse.set_cursor method."""

        checkbox_copy: Checkbox = self.copy_checkbox()
        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)

        # Leave hover and click
        checkbox_copy._is_hovering = True
        self.assertFalse(checkbox_copy.upt(None, mouse_info))
        self.assertFalse(checkbox_copy._is_hovering)
        set_cursor_mock.assert_called_once_with(pg.SYSTEM_CURSOR_ARROW)

        # Enter hover and click twice
        self.assertTrue(checkbox_copy.upt(checkbox_copy, mouse_info))
        self.assertTrue(checkbox_copy.is_checked)
        self.assertFalse(checkbox_copy.upt(checkbox_copy, mouse_info))
        self.assertFalse(checkbox_copy.is_checked)
        self.assertTrue(checkbox_copy._is_hovering)
        set_cursor_mock.assert_called_with(pg.SYSTEM_CURSOR_HAND)

        # Check twice with shortcut
        self.assertTrue(checkbox_copy.upt(None, mouse_info, True))
        self.assertTrue(checkbox_copy.is_checked)
        self.assertFalse(checkbox_copy.upt(None, mouse_info, True))
        self.assertFalse(checkbox_copy.is_checked)

        # Don't hover and don't click
        self.assertFalse(checkbox_copy.upt(None, mouse_info))
        # Hover and don't click
        self.assertFalse(checkbox_copy.upt(checkbox_copy, blank_mouse_info))


class TestButton(TestCase):
    """Tests for the Button class."""

    button: Button

    @classmethod
    def setUpClass(cls: type["TestButton"]) -> None:
        """Creates the button."""

        cls.button = Button(RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", "world\n!", 1, 10)

    def copy_button(self) -> Button:
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

        button_copy: Button = Button(
            self.button.init_pos, self.button._init_imgs, text, hovering_text, layer, text_h
        )
        button_copy.resize(RESIZING_RATIO)

        return button_copy

    @mock.patch.object(TextLabel, '__init__', autospec=True, wraps=TextLabel.__init__)
    @mock.patch.object(Clickable, '__init__', autospec=True, wraps=Clickable.__init__)
    def test_init(self, clickable_init_mock: mock.Mock, text_label_init_mock: mock.Mock) -> None:
        """Tests the init method, mocks the TextLabel.__init__ and Clickable.__init__ methods."""

        test_button: Button = Button(
            RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", "world\n!", 1, 10
        )
        clickable_init_mock.assert_called_once_with(
            test_button, RectPos(1, 2, 'center'), (IMG_1, IMG_2), "world\n!", 1
        )

        text_label_init_args: tuple[Any, ...] = text_label_init_mock.call_args[0]
        text_label: TextLabel = text_label_init_args[0]
        expected_text_label_init_args: tuple[Any, ...] = (
            text_label, RectPos(*test_button.rect.center, 'center'), "hello", 1, 10
        )
        self.assertTupleEqual(text_label_init_args, expected_text_label_init_args)
        self.assertEqual(test_button.objs_info, [ObjInfo(text_label)])

        no_text_button: Button = Button(RectPos(0, 0, 'topleft'), (IMG_1, IMG_2), None, None)
        self.assertListEqual(no_text_button.objs_info, [])

    @mock.patch.object(Clickable, "_base_blit")
    def test_blit(self, base_blit_mock: mock.Mock) -> None:
        """Tests the blit method, mocks the Clickable._base_blit method."""

        button_copy: Button = self.copy_button()

        button_copy.blit()
        base_blit_mock.assert_called_with(0)

        button_copy._is_hovering = True
        button_copy.blit()
        base_blit_mock.assert_called_with(1)

    @mock.patch.object(pg.mouse, 'set_cursor')
    def test_upt(self, set_cursor_mock: mock.Mock) -> None:
        """Tests the upt method, mocks the pygame.mouse.set_cursor method."""

        button_copy: Button = self.copy_button()
        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)

        # Leave hover and click
        button_copy._is_hovering = True
        self.assertFalse(button_copy.upt(None, mouse_info))
        self.assertFalse(button_copy._is_hovering)
        set_cursor_mock.assert_called_with(pg.SYSTEM_CURSOR_ARROW)

        # Enter hover and click
        button_copy._is_hovering = False
        self.assertTrue(button_copy.upt(button_copy, mouse_info))
        self.assertTrue(button_copy._is_hovering)
        set_cursor_mock.assert_called_with(pg.SYSTEM_CURSOR_HAND)

        # Don't hover and don't click
        self.assertFalse(button_copy.upt(None, blank_mouse_info))
        # Hover and don't click
        self.assertFalse(button_copy.upt(button_copy, blank_mouse_info))
