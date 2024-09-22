"""
Tests for the text file
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray
import unittest

from src.classes.text import Text, renderers_cache, RectPos, LayeredBlitSequence, WHITE, TEXT_LAYER


class TestUtils(unittest.TestCase):
    """
    Tests for the text file
    """

    def setUp(self) -> None:
        """
        Creates the text and a model renderer
        """

        self.text_label: Text = Text(RectPos(0, 1, 'topleft'), "hello\nworld", 1, 30)
        self.renderer: pg.Font = pg.font.SysFont('helvetica', 30)

    def test_init(self) -> None:
        """
        Tests the init method
        """

        self.assertEqual(self.text_label._init_pos, RectPos(0, 1, 'topleft'))
        self.assertEqual(self.text_label._x, 0)
        self.assertEqual(self.text_label._y, 1)

        self.assertEqual(self.text_label._init_h, 30)
        self.assertEqual(renderers_cache, {30: self.text_label._renderer})

        self.assertEqual(self.text_label.text, 'hello\nworld')
        self.assertEqual(self.text_label._lines, ('hello', 'world'))

        self.assertEqual(self.text_label._layer, 1 + TEXT_LAYER)

        for surf_1, line in zip(self.text_label._imgs, self.text_label._lines):
            pixels_rgb_1: NDArray[np.uint8] = pg.surfarray.pixels3d(surf_1)
            pixels_alpha_1: NDArray[np.uint8] = pg.surfarray.pixels_alpha(surf_1)
            pixels_1 = np.dstack((pixels_rgb_1, pixels_alpha_1))

            surf_2: pg.Surface = self.renderer.render(line, True, WHITE)
            pixels_rgb_2: NDArray[np.uint8] = pg.surfarray.pixels3d(surf_2)
            pixels_alpha_2: NDArray[np.uint8] = pg.surfarray.pixels_alpha(surf_2)
            pixels_2 = np.dstack((pixels_rgb_2, pixels_alpha_2))

            self.assertTrue(np.array_equal(pixels_1, pixels_2))

    def test_blit(self) -> None:
        """
        Tests the blit method
        """

        sequence: LayeredBlitSequence = self.text_label.blit()
        expected_sequence: LayeredBlitSequence = [
            (img, rect.topleft, self.text_label._layer)
            for img, rect in zip(self.text_label._imgs, self.text_label.rects)
        ]

        self.assertEqual(sequence, expected_sequence)
