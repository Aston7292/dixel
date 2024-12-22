"""Functions shared between tests."""

from typing import Final

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.utils import Ratio

RESIZING_RATIO: Final[Ratio] = Ratio(2, 3)


def cmp_imgs(img: pg.Surface, expected_img: pg.Surface, should_cmp_alpha: bool = True) -> bool:
    """
    Compares two images.

    Args:
        image, expected image, compare alpha flag (default = True)
    Returns:
        True if the images have the same pixels else False
    """

    pixels: NDArray[np.uint8] = pg.surfarray.pixels3d(img)
    if should_cmp_alpha:
        pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img)
        pixels = np.dstack((pixels, pixels_alpha))

    expected_pixels: NDArray[np.uint8] = pg.surfarray.pixels3d(expected_img)
    if should_cmp_alpha:
        expected_pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(expected_img)
        expected_pixels = np.dstack((expected_pixels, expected_pixels_alpha))

    if pixels.shape != expected_pixels.shape:
        print(f"Size differs: {pixels.shape} {expected_pixels.shape}", end="")

    return np.array_equal(pixels, expected_pixels)
