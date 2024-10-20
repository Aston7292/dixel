"""
Tests for the clickable file
"""

import pygame as pg
import unittest
from unittest import mock
from itertools import zip_longest
from collections.abc import Iterator
from typing import Final, Optional, Any

from src.classes.clickable import Clickable, Checkbox, Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, ObjInfo, MouseInfo
from src.type_utils import LayeredBlitInfo, LayeredBlitSequence
from src.consts import ELEMENT_LAYER, TOP_LAYER

from tests.utils import cmp_imgs

IMG_1: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_2: Final[pg.Surface] = IMG_1.copy()
IMG_2.fill((0, 0, 1, 0))


def cmp_hovering_text(
        expected_hovering_text_h: int, expected_hovering_text: str,
        hovering_text_imgs: tuple[pg.Surface, ...]
) -> bool:
    """
    Compares hovering texts
    Args:
        expected hovering text height, expected hovering text, hovering text images
    Returns:
        True if the surfaces are the same ele False
    """

    expected_hovering_text_label: TextLabel = TextLabel(
        RectPos(0, 0, 'topleft'), expected_hovering_text, h=expected_hovering_text_h
    )
    expected_hovering_text_imgs: tuple[pg.Surface, ...] = tuple(
        pg.Surface(rect.size) for rect in expected_hovering_text_label.rects
    )

    expected_hovering_text_info: Iterator[tuple[pg.Surface, LayeredBlitInfo]] = zip_longest(
        expected_hovering_text_imgs, expected_hovering_text_label.blit()
    )
    for target_img, (text_img, _, _) in expected_hovering_text_info:
        target_img.blit(text_img)

    hovering_text_label_comparison: Iterator[tuple[pg.Surface, pg.Surface]] = zip_longest(
        hovering_text_imgs, expected_hovering_text_imgs
    )

    return all(
        cmp_imgs(img, expected_img, False) for img, expected_img in hovering_text_label_comparison
    )


class TestCheckbox(unittest.TestCase):
    """
    Tests for the checkbox class
    """

    checkbox: Checkbox

    @classmethod
    def setUpClass(cls: type["TestCheckbox"]) -> None:
        """
        Creates the checkbox
        """

        cls.checkbox = Checkbox(RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", "world\n!", 1)

    @mock.patch.object(TextLabel, '__init__', autospec=True, wraps=TextLabel.__init__)
    def test_init(self, mock_text_label_init: mock.Mock) -> None:
        """
        Tests the init method (mocks the TextLabel.__init__ method)
        """

        test_checkbox: Checkbox = Checkbox(
            RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", "world\n!", 1
        )
        text_label_init_args: tuple[Any, ...] = mock_text_label_init.call_args[0]

        # Also tests the Clickable abstract class
        self.assertEqual(test_checkbox.init_pos, RectPos(1, 2, 'center'))
        self.assertTupleEqual(test_checkbox._init_imgs, (IMG_1, IMG_2))

        self.assertTupleEqual(test_checkbox._imgs, (IMG_1, IMG_2))
        expected_rect: pg.Rect = IMG_1.get_rect(**{self.checkbox.init_pos.coord_type: (1, 2)})
        self.assertEqual(test_checkbox.rect, expected_rect)

        self.assertFalse(test_checkbox._is_hovering)

        self.assertEqual(test_checkbox._layer, 1 + ELEMENT_LAYER)
        self.assertEqual(test_checkbox._hovering_layer, 1 + TOP_LAYER)

        self.assertTrue(cmp_hovering_text(12, "world\n!", test_checkbox._hovering_text_imgs))

        no_hovering_text_checkbox: Checkbox = Checkbox(
            RectPos(0, 0, 'topleft'), (IMG_1, IMG_2), "hello", ''
        )
        self.assertIsNone(no_hovering_text_checkbox._hovering_text_label)
        self.assertTupleEqual(no_hovering_text_checkbox._hovering_text_imgs, ())

        self.assertFalse(test_checkbox.is_checked)

        text_label_used_args: tuple[Any, ...] = text_label_init_args[1:]
        expected_text_label_used_args: tuple[Any, ...] = (
            RectPos(test_checkbox.rect.centerx, test_checkbox.rect.y - 5, 'midbottom'), "hello",
            1, 16
        )
        self.assertTupleEqual(text_label_used_args, expected_text_label_used_args)

        text_label: TextLabel = text_label_init_args[0]
        self.assertListEqual(test_checkbox.objs_info, [ObjInfo(text_label)])

    def test_base_blit(self) -> None:
        """
        Tests the base_blit method
        """

        expected_sequence_0: LayeredBlitSequence = [
            (self.checkbox._imgs[0], self.checkbox.rect.topleft, self.checkbox._layer)
        ]

        self.assertListEqual(self.checkbox._base_blit(0), expected_sequence_0)

        expected_sequence_1: LayeredBlitSequence = [
            (self.checkbox._imgs[1], self.checkbox.rect.topleft, self.checkbox._layer)
        ]

        expected_hovering_text_line_x: int = pg.mouse.get_pos()[0] + 15
        expected_hovering_text_line_y: int = pg.mouse.get_pos()[1]

        self.checkbox._is_hovering = True
        for img in self.checkbox._hovering_text_imgs:
            expected_sequence_1.append((
                img, (expected_hovering_text_line_x, expected_hovering_text_line_y),
                self.checkbox._hovering_layer
            ))
            expected_hovering_text_line_y += img.get_height()
        self.assertListEqual(self.checkbox._base_blit(1), expected_sequence_1)
        self.checkbox._is_hovering = False

    def test_check_hovering(self) -> None:
        """
        Tests the check_hovering method
        """

        hovered_obj: Optional[Checkbox]
        layer: int
        hovered_obj, layer = self.checkbox.check_hovering(self.checkbox.rect.topleft)
        self.assertIs(hovered_obj, self.checkbox)
        self.assertEqual(layer, 1 + ELEMENT_LAYER)

        hovered_obj, layer = self.checkbox.check_hovering((self.checkbox.rect.x - 1, 0))
        self.assertIsNone(hovered_obj)

    def test_leave(self) -> None:
        """
        Tests the leave method
        """

        self.checkbox._is_hovering = True
        self.checkbox.leave()
        self.assertFalse(self.checkbox._is_hovering)

    def test_a_resize(self) -> None:
        """
        Tests the resize method as first
        """

        expected_imgs: tuple[pg.Surface, ...] = tuple(
            pg.transform.scale(img, (30, 22)) for img in self.checkbox._init_imgs
        )
        expected_rect: pg.Rect = expected_imgs[0].get_rect(
            **{self.checkbox.init_pos.coord_type: (3, 4)}
        )

        self.checkbox.resize((3.0, 2.0))
        for img, expected_img in zip_longest(self.checkbox._imgs, expected_imgs):
            self.assertTrue(cmp_imgs(img, expected_img))
        self.assertEqual(self.checkbox.rect, expected_rect)

        self.assertTrue(cmp_hovering_text(24, "world\n!", self.checkbox._hovering_text_imgs))

    def test_move_rect(self) -> None:
        """
        Tests the move_rect method
        """

        self.checkbox.move_rect(2, 3, 2.0, 3.0)
        self.assertTupleEqual(self.checkbox.init_pos.xy, (2, 3))
        pos: tuple[int, int] = getattr(self.checkbox.rect, self.checkbox.init_pos.coord_type)
        self.assertTupleEqual(pos, (4, 9))

    @mock.patch.object(Clickable, "_base_blit", autospec=True, wraps=Clickable._base_blit)
    def test_blit(self, mock_base_blit: mock.Mock) -> None:
        """
        Tests the blit method (mocks the Clickable._base_blit method)
        """

        self.checkbox.blit()
        mock_base_blit.assert_called_with(self.checkbox, 0)

        self.checkbox.is_checked = True
        self.checkbox.blit()
        mock_base_blit.assert_called_with(self.checkbox, 1)
        self.checkbox.is_checked = False

    @mock.patch.object(pg.mouse, 'set_cursor')
    def test_upt(self, mock_set_cursor: mock.Mock) -> None:
        """
        Tests the upt method (mocks the pygame.mouse.set_cursor method)
        """

        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)

        # Check twice with shortcut
        self.assertTrue(self.checkbox.upt(None, mouse_info, True))
        self.assertTrue(self.checkbox.is_checked)
        self.assertFalse(self.checkbox.upt(None, mouse_info, True))
        self.assertFalse(self.checkbox.is_checked)

        # Leave hover
        self.checkbox._is_hovering = True
        self.assertFalse(self.checkbox.upt(None, mouse_info))
        self.assertFalse(self.checkbox._is_hovering)
        mock_set_cursor.assert_called_once_with(pg.SYSTEM_CURSOR_ARROW)

        # Enter hover and check twice
        self.assertTrue(self.checkbox.upt(self.checkbox, mouse_info))
        self.assertTrue(self.checkbox.is_checked)
        self.assertFalse(self.checkbox.upt(self.checkbox, mouse_info))
        self.assertFalse(self.checkbox.is_checked)
        self.assertTrue(self.checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_HAND)

        # Hover and don't click
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)
        self.assertFalse(self.checkbox.upt(self.checkbox, blank_mouse_info))


class TestButton(unittest.TestCase):
    """
    Tests for the button class
    """

    button: Button

    @classmethod
    def setUpClass(cls: type["TestButton"]) -> None:
        """
        Creates the button
        """

        cls.button = Button(RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", "world\n!", 1, 10)

    @mock.patch.object(TextLabel, '__init__', autospec=True, wraps=TextLabel.__init__)
    @mock.patch.object(Clickable, '__init__', autospec=True, wraps=Clickable.__init__)
    def test_init(self, mock_clickable_init: mock.Mock, mock_text_label_init: mock.Mock) -> None:
        """
        Tests the init method (mocks the Clickable.__init__ and TextLabel.__init__ methods)
        """

        test_button: Button = Button(
            RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", "world\n!", 1, 10
        )
        mock_clickable_init.assert_called_once_with(
            test_button, RectPos(1, 2, 'center'), (IMG_1, IMG_2), "world\n!", 1
        )

        self.assertEqual(mock_text_label_init.call_count, 2)
        text_label_init_args: tuple[Any, ...] = mock_text_label_init.call_args[0]

        text_label_used_args: tuple[Any, ...] = text_label_init_args[1:]
        expected_text_label_used_args: tuple[Any, ...] = (
            RectPos(*test_button.rect.center, 'center'), "hello", 1, 10
        )
        self.assertTupleEqual(text_label_used_args, expected_text_label_used_args)

        text_label: TextLabel = text_label_init_args[0]
        self.assertEqual(test_button.objs_info, [ObjInfo(text_label)])

        no_text_button: Button = Button(RectPos(0, 0, 'topleft'), (IMG_1, IMG_2), '', '')
        self.assertListEqual(no_text_button.objs_info, [])

    @mock.patch.object(Clickable, "_base_blit", autospec=True, wraps=Clickable._base_blit)
    def test_blit(self, mock_base_blit: mock.Mock) -> None:
        """
        Tests the blit method (mocks the Clickable._base_blit method)
        """

        self.button.blit()
        mock_base_blit.assert_called_with(self.button, 0)

        self.button._is_hovering = True
        self.button.blit()
        mock_base_blit.assert_called_with(self.button, 1)
        self.button._is_hovering = False

    @mock.patch.object(pg.mouse, 'set_cursor')
    def test_upt(self, mock_set_cursor: mock.Mock) -> None:
        """
        Tests the upt method (mocks the pygame.mouse.set_cursor method)
        """

        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)

        # Leave hover
        self.button._is_hovering = True
        self.assertFalse(self.button.upt(None, mouse_info))
        self.assertFalse(self.button._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_ARROW)

        # Enter hover and click
        self.button._is_hovering = False
        self.assertTrue(self.button.upt(self.button, mouse_info))
        self.assertTrue(self.button._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_HAND)

        # Hover and don't click
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)
        self.assertFalse(self.button.upt(self.button, blank_mouse_info))
