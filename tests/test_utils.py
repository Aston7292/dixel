"""Tests for the utils file."""

from unittest import TestCase
from typing import Self

from pygame import Surface, Color, SRCALPHA
from numpy import uint8
from numpy.typing import NDArray

from src.utils import get_pixels, add_border, prettify_path


class TestUtils(TestCase):
    """Tests for the utils file."""

    def test_get_pixels(self: Self) -> None:
        """Tests the get_pixels function."""

        x: int
        y: int

        img: Surface = Surface((4, 5), SRCALPHA)
        img.fill((255, 0, 0))
        img.set_at((0, 1), (255, 0, 0, 1))

        pixels: NDArray[uint8] = get_pixels(img)
        for x in range(img.get_width()):
            for y in range(img.get_height()):
                self.assertTupleEqual(
                    tuple(pixels[x, y]),
                    tuple(img.get_at((x, y)))
                )

    def test_add_border(self: Self) -> None:
        """Tests the add_border function."""

        img: Surface = add_border(Surface((10, 11)), Color(0, 0, 1))

        self.assertTupleEqual(
            tuple(img.get_at((0, 0))),
            (0, 0, 1, 255)
        )
        self.assertTupleEqual(
            tuple(img.get_at((9, 0))),
            (0, 0, 1, 255)
        )
        self.assertTupleEqual(
            tuple(img.get_at((0, 9))),
            (0, 0, 1, 255)
        )
        self.assertTupleEqual(
            tuple(img.get_at((9, 9))),
            (0, 0, 1, 255)
        )

        self.assertTupleEqual(
            tuple(img.get_at((2, 2))),
            (0, 0, 0, 255)
        )

    def test_prettify_path(self: Self) -> None:
        """Tests the prettify path function."""

        self.assertEqual(
            prettify_path("C:/User/user/dir1234567890abcdef/file1234567890abcdef"),
            "C:\\...\\dir1...cdef\\file...cdef"
        )

        self.assertEqual(
            prettify_path("C:/User/user/dir/file"),
            "C:\\User\\user\\dir\\file"
        )
