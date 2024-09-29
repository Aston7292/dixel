"""
Tests for the text file (first tests because of renderers cache)
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
    Tests for the text file (first tests because of renderers cache)
    """

    text_label: TextLabel
    renderer: pg.Font

    @classmethod
    def setUpClass(cls: type["TestText"]) -> None:
        """
        Creates the text and a model renderer
        """

        cls.text_label = TextLabel(RectPos(1.0, 2.0, 'topleft'), "hello\nworld", 1, 30)
        cls.renderer = pg.font.SysFont("helvetica", 30)

    @mock.patch.object(TextLabel, "_get_rects")
    def test_a_init(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the init method as first (mocks the get_rects method)
        """

        self.assertEqual(self.text_label._init_pos, RectPos(1.0, 2.0, 'topleft'))
        self.assertEqual(self.text_label._x, 1.0)
        self.assertEqual(self.text_label._y, 2.0)

        self.assertEqual(self.text_label._init_h, 30)
        self.assertDictEqual(renderers_cache, {30: self.text_label._renderer})

        self.assertEqual(self.text_label.text, "hello\nworld")
        self.assertTupleEqual(self.text_label._lines, ("hello", "world"))

        self.assertEqual(self.text_label._layer, 1 + TEXT_LAYER)

        for img, line in zip_longest(self.text_label._imgs, self.text_label._lines):
            expected_img: pg.Surface = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))

        TextLabel(RectPos(0.0, 0.0, 'topleft'), "hello")
        mock_get_rects.assert_called_once()

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
    def test_aa_handle_resize(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the handle_resize method as second (mocks the get_rects method)
        """

        self.__class__.renderer = pg.font.SysFont("helvetica", 60)
        self.text_label.handle_resize(2.0, 3.0)

        self.assertEqual(self.text_label._x, 2.0)
        self.assertEqual(self.text_label._y, 6.0)

        self.assertIs(renderers_cache[60], self.text_label._renderer)

        for img, line in zip_longest(self.text_label._imgs, self.text_label._lines):
            expected_img: pg.Surface = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))
        mock_get_rects.assert_called_once()

    def test_get_rects(self) -> None:
        """
        Tests the get_rects method
        """

        coord_types: tuple[str, ...] = (
            'topleft', 'midtop', 'topright',
            'midright', 'center', 'midleft',
            'bottomright', 'midbottom', 'bottomleft'
        )

        heights: tuple[int, ...] = tuple(
            self.renderer.render(line, True, WHITE).get_height() for line in self.text_label._lines
        )
        bottom_offset: int = sum(heights) - heights[-1]
        center_offset: float = bottom_offset / 2.0

        for coord_type in coord_types:
            text_label: TextLabel = TextLabel(RectPos(1.0, 2.0, coord_type), "hello\nworld", h=30)
            text_label.handle_resize(3.0, 2.0)
            expected_rects: list[pg.FRect] = []

            current_y: float = 4.0
            if coord_type in ('midright', 'center', 'midleft'):
                current_y -= center_offset
            elif 'bottom' in coord_type:
                current_y -= bottom_offset

            for img in text_label._imgs:
                expected_rects.append(img.get_frect(**{coord_type: (3.0, current_y)}))
                current_y += expected_rects[-1].h

            x: float = min(rect.x for rect in expected_rects)
            y: float = min(rect.y for rect in expected_rects)
            max_w: float = max(rect.w for rect in expected_rects)
            expected_rect: pg.FRect = pg.FRect(x, y, max_w, sum(heights))

            self.assertListEqual(text_label.rects, expected_rects)
            self.assertEqual(text_label.rect, expected_rect)

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._get_rects)
    def test_move_rect(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the move_rect method (mocks the get_rects method)
        """

        self.text_label.move_rect(100.0, 300.0, 2.0, 3.0)

        self.assertEqual(self.text_label._init_pos, RectPos(50.0, 100.0, 'topleft'))
        self.assertEqual(self.text_label._x, 100.0)
        self.assertEqual(self.text_label._y, 300.0)
        mock_get_rects.assert_called_once()

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._get_rects)
    def test_set_text(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the set_text method (mocks the get_rects method)
        """

        expected_img: pg.Surface

        self.text_label.set_text("hello")

        self.assertEqual(self.text_label.text, "hello")
        self.assertTupleEqual(self.text_label._lines, ("hello",))
        for img, line in zip_longest(self.text_label._imgs, self.text_label._lines):
            expected_img = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))
        mock_get_rects.assert_called_once()

        self.text_label.set_text("hello\nworld")

        self.assertEqual(self.text_label.text, "hello\nworld")
        self.assertTupleEqual(self.text_label._lines, ("hello", "world"))
        for img, line in zip_longest(self.text_label._imgs, self.text_label._lines):
            expected_img = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))

    def test_get_pos_at(self) -> None:
        """
        Tests the get_pos_at method
        """

        start_x: float = self.text_label.rects[0].x

        # Also makes sure the render with antialiasing has the same width as the one without
        x_2: float = start_x + self.renderer.render("he", True, WHITE).get_width()
        x_5: float = start_x + self.renderer.render("hello", True, WHITE).get_width()

        self.assertEqual(self.text_label.get_pos_at(0), start_x)
        self.assertEqual(self.text_label.get_pos_at(2), x_2)
        self.assertEqual(self.text_label.get_pos_at(5), x_5)

    def test_get_closest_to(self) -> None:
        """
        Tests the get_closest_to method
        """

        pos_2: int = int(
            self.text_label.rects[0].x + self.renderer.render("he", True, WHITE).get_width()
        )
        turning_point: int = pos_2 + (self.renderer.render("l", True, WHITE).get_width() // 2)

        self.assertEqual(self.text_label.get_closest_to(0), 0)
        self.assertEqual(self.text_label.get_closest_to(pos_2 - 1), 2)
        self.assertEqual(self.text_label.get_closest_to(pos_2 + 1), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_point), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_point + 1), 3)
        self.assertEqual(self.text_label.get_closest_to(1_000), 5)
