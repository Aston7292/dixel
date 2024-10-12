"""
Tests for the clickables
"""

import pygame as pg
import unittest
from unittest import mock
from itertools import zip_longest
from collections.abc import Iterator
from typing import Final, Optional

from src.classes.clickable import Checkbox
from src.classes.text_label import TextLabel

from src.utils import RectPos, MouseInfo
from src.type_utils import LayeredBlitInfo, LayeredBlitSequence
from src.consts import ELEMENT_LAYER, TEXT_LAYER, TOP_LAYER

from tests.utils import cmp_imgs

IMG_1: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_2: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_2.fill((0, 0, 0, 0))


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

        cls.checkbox = Checkbox(RectPos(1, 2, 'topleft'), (IMG_1, IMG_2), "hello", "world\n!", 1)

    def test_a_init(self) -> None:
        """
        Tests the init method as first
        """

        # Also tests the Clickable abstract class
        self.assertEqual(self.checkbox._init_pos, RectPos(1, 2, 'topleft'))

        for img, expected_img in zip_longest(self.checkbox._init_imgs, (IMG_1, IMG_2)):
            self.assertTrue(cmp_imgs(img, expected_img))
        for img, expected_img in zip_longest(self.checkbox._imgs, (IMG_1, IMG_2)):
            self.assertTrue(cmp_imgs(img, expected_img))
        expected_rect: pg.Rect = IMG_1.get_rect(topleft=(1, 2))
        self.assertEqual(self.checkbox.rect, expected_rect)

        self.assertFalse(self.checkbox._is_hovering)

        self.assertEqual(self.checkbox._layer, 1 + ELEMENT_LAYER)
        self.assertEqual(self.checkbox._hovering_layer, 1 + TOP_LAYER)

        # Compare hovering text
        expected_hovering_text_label: TextLabel = TextLabel(
            RectPos(0, 0, 'topleft'), "world\n!", h=12
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
            self.checkbox._hovering_text_imgs, expected_hovering_text_imgs
        )
        for img, expected_img in hovering_text_label_comparison:
            self.assertTrue(cmp_imgs(img, expected_img, False))

        no_hovering_text_checkbox: Checkbox = Checkbox(
            RectPos(0, 0, 'topleft'), (IMG_1, IMG_2), "hello", ''
        )

        self.assertIsNone(no_hovering_text_checkbox._hovering_text_label)
        self.assertTupleEqual(no_hovering_text_checkbox._hovering_text_imgs, ())

        self.assertFalse(self.checkbox.is_checked)

        text_label: TextLabel = self.checkbox.objs_info[0].obj

        self.assertIsInstance(text_label, TextLabel)
        self.assertTrue(self.checkbox.objs_info[0].is_active)

        self.assertEqual(text_label._init_pos, RectPos(6, -3, 'midbottom'))
        self.assertEqual(text_label.text, "hello")
        self.assertEqual(text_label._layer, 1 + TEXT_LAYER)
        self.assertEqual(text_label._init_h, 16)

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

        hovered_obj, layer = self.checkbox.check_hovering((-1, -1))
        self.assertIsNone(hovered_obj)

    def test_leave(self) -> None:
        """
        Tests the leave method
        """

        self.checkbox._is_hovering = True
        self.checkbox.leave()
        self.assertFalse(self.checkbox._is_hovering)

    def test_aa_handle_resize(self) -> None:
        """
        Tests the handle_resize method as second
        """

        size: tuple[int, int] = (IMG_1.get_width() * 3, IMG_1.get_height() * 2)

        expected_imgs: tuple[pg.Surface, ...] = tuple(
            pg.transform.scale(img, size) for img in self.checkbox._init_imgs
        )
        expected_rect: pg.Rect = expected_imgs[0].get_rect(topleft=(3, 4))

        self.checkbox.handle_resize((3.0, 2.0))
        for img, expected_img in zip_longest(self.checkbox._imgs, expected_imgs):
            self.assertTrue(cmp_imgs(img, expected_img))
        self.assertEqual(self.checkbox.rect, expected_rect)

        expected_hovering_text_label: TextLabel = TextLabel(
            RectPos(0, 0, 'topleft'), "world\n!", h=24
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
            self.checkbox._hovering_text_imgs, expected_hovering_text_imgs
        )
        for img, expected_img in hovering_text_label_comparison:
            self.assertTrue(cmp_imgs(img, expected_img, False))

    def test_blit(self) -> None:
        """
        Tests the blit method
        """

        expected_sequence: LayeredBlitSequence = self.checkbox._base_blit(0)
        self.assertEqual(self.checkbox.blit(), expected_sequence)

        self.checkbox.is_checked = True
        expected_sequence = self.checkbox._base_blit(1)
        self.assertEqual(self.checkbox.blit(), expected_sequence)
        self.checkbox.is_checked = False

    @mock.patch.object(pg.mouse, 'set_cursor')
    def test_upt(self, mock_set_cursor: mock.Mock) -> None:
        """
        Tests the upt method (mocks the pygame.mouse.set_cursor method)
        """

        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)

        self.checkbox._is_hovering = True
        self.assertFalse(self.checkbox.upt(None, mouse_info, False))
        self.assertFalse(self.checkbox._is_hovering)
        mock_set_cursor.assert_called_once_with(pg.SYSTEM_CURSOR_ARROW)

        self.assertTrue(self.checkbox.upt(self.checkbox, mouse_info, False))
        self.assertTrue(self.checkbox.is_checked)
        self.assertFalse(self.checkbox.upt(self.checkbox, mouse_info, False))
        self.assertFalse(self.checkbox.is_checked)
        self.assertTrue(self.checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_HAND)

        self.assertTrue(self.checkbox.upt(None, mouse_info, True))
        self.assertTrue(self.checkbox.is_checked)
        self.assertFalse(self.checkbox.upt(None, mouse_info, True))
        self.assertFalse(self.checkbox.is_checked)

        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)
        self.assertFalse(self.checkbox.upt(self.checkbox, blank_mouse_info, False))
