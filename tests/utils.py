"""Functions shared between tests."""

import pygame as pg
import numpy as np
from numpy import uint8
from numpy.typing import NDArray


def cmp_imgs(img: pg.Surface, expected_img: pg.Surface) -> bool:
    """
    Compares two images.

    Args:
        image, expected image
    Returns:
        equal flag
    """

    pixels_rgb: NDArray[uint8] = pg.surfarray.pixels3d(img)
    alpha_values: NDArray[uint8] = pg.surfarray.pixels_alpha(img)
    pixels: NDArray[np.uint8] = np.dstack((pixels_rgb, alpha_values))

    expected_pixels_rgb: NDArray[uint8] = pg.surfarray.pixels3d(expected_img)
    expected_alpha_values: NDArray[uint8] = pg.surfarray.pixels_alpha(expected_img)
    expected_pixels: NDArray[uint8] = np.dstack((expected_pixels_rgb, expected_alpha_values))

    if pixels.shape != expected_pixels.shape:
        print(f"Size differs: {pixels.shape} {expected_pixels.shape}", end="")
    return np.array_equal(pixels, expected_pixels)
