"""
Tests for the text file
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
import unittest
from unittest import mock

from src.classes.text import (
    TextLabel, renderers_cache, RectPos, LayeredBlitSequence, WHITE, TEXT_LAYER
)


def cmp_surfs(surf_1: pg.Surface, surf_2: pg.Surface) -> bool:
    """
    Compares two surfaces
    Args:
        surface 1, surface 2
    Returns:
        True if the surfaces have the same pixels else False
    """

    pixels_rgb_1: NDArray[np.uint8] = pg.surfarray.pixels3d(surf_1)
    pixels_alpha_1: NDArray[np.uint8] = pg.surfarray.pixels_alpha(surf_1)
    pixels_1 = np.dstack((pixels_rgb_1, pixels_alpha_1))

    pixels_rgb_2: NDArray[np.uint8] = pg.surfarray.pixels3d(surf_2)
    pixels_alpha_2: NDArray[np.uint8] = pg.surfarray.pixels_alpha(surf_2)
    pixels_2 = np.dstack((pixels_rgb_2, pixels_alpha_2))

    return np.array_equal(pixels_1, pixels_2)


class TestText(unittest.TestCase):
    """
    Tests for the text file
    """

    text_label: TextLabel
    renderer: pg.Font

    @classmethod
    def setUpClass(cls: type['TestText']) -> None:
        """
        Creates the text and a model renderer
        """

        cls.text_label = TextLabel(RectPos(1, 2, 'topleft'), "hello\nworld", 1, 30)
        cls.renderer = pg.font.SysFont("helvetica", 30)

    @mock.patch.object(TextLabel, '_get_rects')
    def test_a_init(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the init method as first (mocks the get_rects method)
        """

        self.assertEqual(self.text_label._init_pos, RectPos(1.0, 2.0, 'topleft'))
        self.assertEqual(self.text_label._x, 1.0)
        self.assertEqual(self.text_label._y, 2.0)

        self.assertEqual(self.text_label._init_h, 30)
        self.assertEqual(renderers_cache, {30: self.text_label._renderer})

        self.assertEqual(self.text_label.text, "hello\nworld")
        self.assertEqual(self.text_label._lines, ("hello", "world"))

        self.assertEqual(self.text_label._layer, 1 + TEXT_LAYER)

        for surf_1, line in zip(self.text_label._imgs, self.text_label._lines):
            surf_2: pg.Surface = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_surfs(surf_1, surf_2))

        TextLabel(RectPos(0, 0, 'topleft'), "hello")
        mock_get_rects.assert_called_once()

    def test_blit(self) -> None:
        """
        Tests the blit method
        """

        expected_sequence: LayeredBlitSequence = [
            (img, rect.topleft, self.text_label._layer)
            for img, rect in zip(self.text_label._imgs, self.text_label.rects)
        ]

        self.assertEqual(self.text_label.blit(), expected_sequence)

    @mock.patch.object(TextLabel, '_get_rects', autospec=True, wraps=TextLabel._get_rects)
    def test_aa_handle_resize(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the handle_resize method as second (mocks the get_rects method)
        """

        self.text_label.handle_resize(3.0, 2.0)
        self.__class__.renderer = pg.font.SysFont("helvetica", 60)

        self.assertEqual(self.text_label._x, 3.0)
        self.assertEqual(self.text_label._y, 4.0)

        self.assertEqual(renderers_cache[60], self.text_label._renderer)

        for surf_1, line in zip(self.text_label._imgs, self.text_label._lines):
            surf_2: pg.Surface = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_surfs(surf_1, surf_2))
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
            text_label: TextLabel = TextLabel(RectPos(1.0, 2.0, coord_type), 'hello\nworld', h=30)
            text_label.handle_resize(3.0, 2.0)
            rects: list[pg.FRect] = []

            current_y: float = 4.0
            if coord_type in ('midright', 'center', 'midleft'):
                current_y -= center_offset
            elif 'bottom' in coord_type:
                current_y -= bottom_offset

            for img in text_label._imgs:
                rects.append(img.get_frect(**{coord_type: (3.0, current_y)}))
                current_y += rects[-1].h

            x: float = min(rect.x for rect in rects)
            y: float = min(rect.y for rect in rects)
            max_w: float = max(rect.w for rect in rects)
            rect: pg.FRect = pg.FRect(x, y, max_w, sum(heights))

            self.assertEqual(text_label.rects, rects)
            self.assertEqual(text_label.rect, rect)

    @mock.patch.object(TextLabel, '_get_rects', autospec=True, wraps=TextLabel._get_rects)
    def test_move_rect(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the move_rect method (mocks the get_rects method)
        """

        self.text_label.move_rect(100.0, 300.0, 2.0, 3.0)

        self.assertEqual(self.text_label._init_pos.x, 50.0)
        self.assertEqual(self.text_label._init_pos.y, 100.0)
        self.assertEqual(self.text_label._x, 100.0)
        self.assertEqual(self.text_label._y, 300.0)
        mock_get_rects.assert_called_once()

    @mock.patch.object(TextLabel, '_get_rects', autospec=True, wraps=TextLabel._get_rects)
    def test_set_text(self, mock_get_rects: mock.Mock) -> None:
        """
        Tests the set_text method (mocks the get_rects method)
        """

        surf_2: pg.Surface

        self.text_label.set_text('hello')

        self.assertEqual(self.text_label.text, 'hello')
        self.assertEqual(self.text_label._lines, ('hello',))
        for surf_1, line in zip(self.text_label._imgs, self.text_label._lines):
            surf_2 = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_surfs(surf_1, surf_2))
        mock_get_rects.assert_called_once()

        self.text_label.set_text('hello\nworld')

        self.assertEqual(self.text_label.text, 'hello\nworld')
        self.assertEqual(self.text_label._lines, ('hello', 'world'))
        for surf_1, line in zip(self.text_label._imgs, self.text_label._lines):
            surf_2 = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_surfs(surf_1, surf_2))

    def test_get_pos_at(self) -> None:
        """
        Tests the get_pos_at method
        """

        start_x: float = self.text_label.rects[0].x

        # Also makes sure the render with antialiasing has the same width as the one without
        x_2: float = start_x + self.renderer.render('he', True, WHITE).get_width()
        x_5: float = start_x + self.renderer.render('hello', True, WHITE).get_width()

        self.assertEqual(self.text_label.get_pos_at(0), start_x)
        self.assertEqual(self.text_label.get_pos_at(2), x_2)
        self.assertEqual(self.text_label.get_pos_at(5), x_5)

    def test_get_closest_to(self) -> None:
        """
        Tests the get_closest_to method
        """

        pos_2: int = int(
            self.text_label.rects[0].x + self.renderer.render('he', True, WHITE).get_width()
        )
        turning_point: int = pos_2 + (self.renderer.render('l', True, WHITE).get_width() // 2)

        self.assertEqual(self.text_label.get_closest_to(0), 0)
        self.assertEqual(self.text_label.get_closest_to(pos_2 - 1), 2)
        self.assertEqual(self.text_label.get_closest_to(pos_2 + 1), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_point), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_point + 1), 3)
        self.assertEqual(self.text_label.get_closest_to(1_000), 5)
