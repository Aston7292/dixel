"""
Tests for the checkbox grid file
"""

import pygame as pg
import unittest
from unittest import mock
from typing import Final

from src.classes.checkbox_grid import LockedCheckbox
from src.classes.clickable import Clickable
from src.classes.text_label import TextLabel

from src.utils import RectPos, MouseInfo

from tests.test_clickable import cmp_hovering_text

IMG_1: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_2: Final[pg.Surface] = IMG_1.copy()
IMG_2.fill((0, 0, 1, 0))


class TestLockedCheckbox(unittest.TestCase):
    """
    Tests for the locked checkbox class
    """

    locked_checkbox: LockedCheckbox
    expected_hovering_text_h: int

    @classmethod
    def setUpClass(cls: type["TestLockedCheckbox"]) -> None:
        """
        Creates the checkbox
        """

        cls.locked_checkbox = LockedCheckbox(RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", 1)
        cls.expected_hovering_text_h = 12

    @mock.patch.object(Clickable, '__init__', autospec=True, wraps=Clickable.__init__)
    def test_init(self, mock_clickable_init: mock.Mock) -> None:
        """
        Tests the init method, mocks the Clickable.__init__ method
        """

        test_locked_checkbox: LockedCheckbox = LockedCheckbox(
            RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", 1
        )
        mock_clickable_init.assert_called_once_with(
            test_locked_checkbox, RectPos(1, 2, 'center'), (IMG_1, IMG_2), "hello", 1
        )

        self.assertFalse(test_locked_checkbox.is_checked)

    @mock.patch.object(Clickable, "_base_blit", autospec=True, wraps=Clickable._base_blit)
    def test_blit(self, mock_base_blit: mock.Mock) -> None:
        """
        Tests the blit method, mocks the Clickable._base_blit method
        """

        self.locked_checkbox.blit()
        mock_base_blit.assert_called_with(self.locked_checkbox, 0)

        self.locked_checkbox._is_hovering = True
        self.locked_checkbox.blit()
        mock_base_blit.assert_called_with(self.locked_checkbox, 1)
        self.locked_checkbox._is_hovering = False

        self.locked_checkbox.is_checked = True
        self.locked_checkbox.blit()
        mock_base_blit.assert_called_with(self.locked_checkbox, 1)
        self.locked_checkbox.is_checked = False

    @mock.patch.object(TextLabel, 'set_text', autospec=True, wraps=TextLabel.set_text)
    def test_set_info(self, mock_set_text: mock.Mock) -> None:
        """
        Tests the set_info method, mocks the TextLabel.set_text method
        """

        self.locked_checkbox.set_info((IMG_2, IMG_1), "world")

        self.assertTupleEqual(self.locked_checkbox._init_imgs, (IMG_2, IMG_1))
        self.assertTupleEqual(self.locked_checkbox._imgs, (IMG_2, IMG_1))

        mock_set_text.assert_called_once_with(self.locked_checkbox._hovering_text_label, "world")
        self.assertTrue(cmp_hovering_text(
            self.expected_hovering_text_h, "world", self.locked_checkbox._hovering_text_imgs
        ))

    @mock.patch.object(pg.mouse, 'set_cursor')
    def test_upt(self, mock_set_cursor: mock.Mock) -> None:
        """
        Tests the upt method, mocks the pygame.mouse.set_cursor method
        """

        mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (True,) * 5)

        # Leave hover
        self.locked_checkbox._is_hovering = True
        self.assertFalse(self.locked_checkbox.upt(None, mouse_info))
        self.assertFalse(self.locked_checkbox._is_hovering)
        mock_set_cursor.assert_called_once_with(pg.SYSTEM_CURSOR_ARROW)

        # Enter hover and check twice
        self.assertTrue(self.locked_checkbox.upt(self.locked_checkbox, mouse_info))
        self.assertTrue(self.locked_checkbox.is_checked)
        self.assertTrue(self.locked_checkbox.upt(self.locked_checkbox, mouse_info))
        self.assertTrue(self.locked_checkbox.is_checked)
        self.assertTrue(self.locked_checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_HAND)

        # Hover and don't click
        blank_mouse_info: MouseInfo = MouseInfo(0, 0, (False,) * 3, (False,) * 5)
        self.assertFalse(self.locked_checkbox.upt(self.locked_checkbox, blank_mouse_info))
