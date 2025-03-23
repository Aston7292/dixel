"""Functions shared between tests."""

from pygame import Surface
from pygame.surfarray import pixels3d, pixels_alpha
from numpy import array_equal, dstack as dstack_arr, uint8
from numpy.typing import NDArray


def cmp_imgs(img: Surface, expected_img: Surface, should_cmp_alpha: bool = True) -> bool:
    """
    Compares two images.

    Args:
        image, expected image, compare alpha flag (default = True)
    Returns:
        equal flag
    """

    pixels: NDArray[uint8] = pixels3d(img)
    if should_cmp_alpha:
        alpha_values: NDArray[uint8] = pixels_alpha(img)
        pixels = dstack_arr((pixels, alpha_values))

    expected_pixels: NDArray[uint8] = pixels3d(expected_img)
    if should_cmp_alpha:
        expected_alpha_values: NDArray[uint8] = pixels_alpha(expected_img)
        expected_pixels = dstack_arr((expected_pixels, expected_alpha_values))

    if pixels.shape != expected_pixels.shape:
        print(f"Size differs: {pixels.shape} {expected_pixels.shape}", end="")
    return array_equal(pixels, expected_pixels)
