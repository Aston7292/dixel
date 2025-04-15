"""Functions shared between tests."""

import pygame as pg
import numpy as np
from numpy.typing import NDArray


def cmp_imgs(img: pg.Surface, expected_img: pg.Surface, should_cmp_alpha: bool = True) -> bool:
    """
    Compares two images.

    Args:
        image, expected image, compare alpha flag (default = True)
    Returns:
        equal flag
    """

    pixels: NDArray[np.uint8] = pg.surfarray.pixels3d(img)
    if should_cmp_alpha:
        alpha_values: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img)
        pixels = np.dstack((pixels, alpha_values))

    expected_pixels: NDArray[np.uint8] = pg.surfarray.pixels3d(expected_img)
    if should_cmp_alpha:
        expected_alpha_values: NDArray[np.uint8] = pg.surfarray.pixels_alpha(expected_img)
        expected_pixels = np.dstack((expected_pixels, expected_alpha_values))

    if pixels.shape != expected_pixels.shape:
        print(f"Size differs: {pixels.shape} {expected_pixels.shape}", end="")
    return np.array_equal(pixels, expected_pixels)
