"""
Tests for the text file
"""

import pygame as pg
import unittest
from unittest import mock
from itertools import zip_longest

from src.classes.text_label import TextLabel, renderers_cache

from src.utils import RectPos
from src.type_utils import LayeredBlitSequence
from src.consts import WHITE, TEXT_LAYER

from tests.utils import cmp_imgs


class TestText(unittest.TestCase):
    """
    Tests for the text class
    """

    text_label: TextLabel
    renderer: pg.Font

    @classmethod
    def setUpClass(cls: type["TestText"]) -> None:
        """
        Creates the text and a model renderer
        """

        cls.text_label = TextLabel(RectPos(1, 2, 'center'), "hello\n!", 1, 30)
        cls.renderer = pg.font.SysFont("helvetica", 30)

    @mock.patch.object(TextLabel, "_get_rects")
    def test_init(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the init method  (mocks the get_rects method)
        """

        text_label: TextLabel = TextLabel(RectPos(1, 2, 'center'), "hello\n!", 1, 30)

        self.assertEqual(text_label.init_pos, RectPos(1, 2, 'center'))

        self.assertEqual(text_label._init_h, 30)
        self.assertIs(renderers_cache[text_label._init_h], text_label._renderer)

        self.assertEqual(text_label.text, "hello\n!")
        self.assertTupleEqual(text_label._lines, tuple(text_label.text.split('\n')))

        self.assertEqual(text_label._layer, 1 + TEXT_LAYER)

        renderer: pg.Font = pg.font.SysFont("helvetica", 30)
        for img, line in zip_longest(text_label._imgs, text_label._lines):
            expected_img: pg.Surface = renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))

        mock_get_rects.assert_called_once_with((1, 2))

    def test_blit(self) -> None:
        """
        Tests the blit method
        """

        expected_sequence: LayeredBlitSequence = [
            (img, rect.topleft, self.text_label._layer)
            for img, rect in zip_longest(self.text_label._imgs, self.text_label.rects)
        ]

        self.assertListEqual(self.text_label.blit(), expected_sequence)

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._get_rects)
    def test_a_resize(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the resize method as first (mocks the get_rects method)
        """

        self.__class__.renderer = pg.font.SysFont("helvetica", 60)
        self.text_label.resize((2.0, 3.0))

        self.assertIs(renderers_cache[60], self.text_label._renderer)

        for img, line in zip_longest(self.text_label._imgs, self.text_label._lines):
            expected_img: pg.Surface = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))
        mock_get_rects.assert_called_once_with(self.text_label, (2, 6))

    def test_get_rects(self) -> None:
        """
        Tests the get_rects method
        """

        rect_w: int = max(img.get_width() for img in self.text_label._imgs)
        rect_h: int = sum(img.get_height() for img in self.text_label._imgs)
        expected_rect: pg.Rect = pg.Rect(0, 0, rect_w, rect_h)
        setattr(expected_rect, self.text_label.init_pos.coord_type, (2, 3))

        expected_rects: list[pg.Rect] = []
        line_rect_y: int = expected_rect.y
        for img in self.text_label._imgs:
            line_rect: pg.Rect = img.get_rect(topleft=(expected_rect.x, line_rect_y))
            line_rect.x += round((expected_rect.w - line_rect.w) / 2)
            expected_rects.append(line_rect)
            line_rect_y += expected_rects[-1].h

        self.text_label._get_rects((2, 3))
        self.assertEqual(self.text_label.rect, expected_rect)
        self.assertListEqual(self.text_label.rects, expected_rects)

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._get_rects)
    def test_move_rect(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the move_rect method (mocks the get_rects method)
        """

        self.text_label.move_rect(2, 3, 2.1, 3.2)

        self.assertEqual(
            self.text_label.init_pos, RectPos(2, 3, self.text_label.init_pos.coord_type)
        )
        # Also makes sure round was used
        mock_get_rects.assert_called_once_with(self.text_label, (4, 10))

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._get_rects)
    def test_set_text(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the set_text method (mocks the get_rects method)
        """

        expected_img: pg.Surface

        self.text_label.set_text("hello\n?")

        self.assertEqual(self.text_label.text, "hello\n?")
        self.assertTupleEqual(self.text_label._lines, tuple(self.text_label.text.split('\n')))
        for img, line in zip_longest(self.text_label._imgs, self.text_label._lines):
            expected_img = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))
        pos: tuple[int, int] = getattr(self.text_label.rect, self.text_label.init_pos.coord_type)
        mock_get_rects.assert_called_once_with(self.text_label, pos)

        self.text_label.set_text("hello\n!")

        self.assertEqual(self.text_label.text, "hello\n!")
        self.assertTupleEqual(self.text_label._lines, tuple(self.text_label.text.split('\n')))
        for img, line in zip_longest(self.text_label._imgs, self.text_label._lines):
            expected_img = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))

    def test_get_pos_at(self) -> None:
        """
        Tests the get_pos_at method
        """

        start_x: int = self.text_label.rects[0].x

        # Also makes sure the render with antialiasing has the same width as the one without
        x_2: int = start_x + self.renderer.render("he", True, WHITE).get_width()
        x_5: int = start_x + self.renderer.render("hello", True, WHITE).get_width()

        self.assertEqual(self.text_label.get_pos_at(0), start_x)
        self.assertEqual(self.text_label.get_pos_at(2), x_2)
        self.assertEqual(self.text_label.get_pos_at(5), x_5)

    def test_get_closest_to(self) -> None:
        """
        Tests the get_closest_to method
        """

        pos_2: int = (
            self.text_label.rects[0].x + self.renderer.render("he", True, WHITE).get_width()
        )
        turning_point: int = pos_2 + (self.renderer.render("l", True, WHITE).get_width() // 2)

        self.assertEqual(self.text_label.get_closest_to(self.text_label.rect.x), 0)
        self.assertEqual(self.text_label.get_closest_to(pos_2 - 1), 2)
        self.assertEqual(self.text_label.get_closest_to(pos_2 + 1), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_point), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_point + 1), 3)
        self.assertEqual(self.text_label.get_closest_to(1_000), 5)
