"""
Functions shared between tests
"""

import pygame as pg
import numpy as np
from numpy.typing import NDArray


def cmp_imgs(img_1: pg.Surface, img_2: pg.Surface, cmp_alpha: bool = True) -> bool:
    """
    Compares two images
    Args:
        image 1, image 2, compare alpha boolean (default = True)
    Returns:
        True if the images have the same pixels else False
    """

    pixels_1: NDArray[np.uint8] = pg.surfarray.pixels3d(img_1)
    if cmp_alpha:
        pixels_alpha_1: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img_1)
        pixels_1 = np.dstack((pixels_1, pixels_alpha_1))

    pixels_2: NDArray[np.uint8] = pg.surfarray.pixels3d(img_2)
    if cmp_alpha:
        pixels_alpha_2: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img_2)
        pixels_2 = np.dstack((pixels_2, pixels_alpha_2))

    return np.array_equal(pixels_1, pixels_2)
