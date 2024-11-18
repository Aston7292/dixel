"""Functions shared between tests."""

from itertools import zip_longest
from collections.abc import Iterator
from typing import Final

import pygame as pg
import numpy as np
from numpy.typing import NDArray

from src.classes.text_label import TextLabel

from src.utils import RectPos, Ratio
from src.type_utils import LayeredBlitInfo

RESIZING_RATIO: Final[Ratio] = Ratio(2.0, 3.0)


def cmp_imgs(img: pg.Surface, expected_img: pg.Surface, cmp_alpha: bool = True) -> bool:
    """
    Compares two images.

    Args:
        image, expected image, compare alpha flag (default = True)
    Returns:
        True if the images have the same pixels else False
    """

    pixels: NDArray[np.uint8] = pg.surfarray.pixels3d(img)
    if cmp_alpha:
        pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(img)
        pixels = np.dstack((pixels, pixels_alpha))

    expected_pixels: NDArray[np.uint8] = pg.surfarray.pixels3d(expected_img)
    if cmp_alpha:
        expected_pixels_alpha: NDArray[np.uint8] = pg.surfarray.pixels_alpha(expected_img)
        expected_pixels = np.dstack((expected_pixels, expected_pixels_alpha))

    if pixels.shape != expected_pixels.shape:
        print(f"Size differs: {pixels.shape} {expected_pixels.shape}", end='')

    return np.array_equal(pixels, expected_pixels)


def cmp_hovering_text(
        expected_hovering_text_h: int, expected_hovering_text: str,
        hovering_text_imgs: tuple[pg.Surface, ...]
) -> bool:
    """
    Compares hovering texts.

    Args:
        expected hovering text height, expected hovering text, hovering text images
    Returns:
        True if the images are the same else False
    """

    expected_hovering_text_label: TextLabel = TextLabel(
        RectPos(0, 0, 'topleft'), expected_hovering_text, h=expected_hovering_text_h
    )
    expected_hovering_text_imgs: tuple[pg.Surface, ...] = tuple(
        pg.Surface(rect.size) for rect in expected_hovering_text_label.rects
    )

    expected_hovering_text_info: Iterator[tuple[pg.Surface, LayeredBlitInfo]] = zip_longest(
        expected_hovering_text_imgs, expected_hovering_text_label.blit()
    )
    for img, (text_img, _, _) in expected_hovering_text_info:
        img.blit(text_img)

    expected_size: tuple[int, int] = expected_hovering_text_imgs[0].get_size()
    if hovering_text_imgs[0].get_size() != expected_size:
        print(f"Size differs: {hovering_text_imgs[0].get_size()} {expected_size}", end='')

    expected_len: int = len(expected_hovering_text_imgs)
    if len(hovering_text_imgs) != expected_len:
        print(f"Length differs: {len(hovering_text_imgs)} {expected_len}", end='')

    hovering_text_label_comparison: Iterator[tuple[pg.Surface, ...]] = zip_longest(
        hovering_text_imgs, expected_hovering_text_imgs
    )

    return all(
        cmp_imgs(img, expected_img, False) for img, expected_img in hovering_text_label_comparison
    )
