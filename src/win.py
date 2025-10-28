"""Window-related constants shared between files."""

from typing import Final

import pygame as pg


WIN_INIT_W: Final[int] = 1_250
WIN_INIT_H: Final[int] = 900

# TODO: screenshots
_i: int
for _i in range(5):
    pg.font.init()  # Others aren't used
pg.key.stop_text_input()

# Window gets focused before starting, so it doesn't appear when exiting early
WIN: Final[pg.Window] = pg.Window(
    "Dixel", (WIN_INIT_W, WIN_INIT_H),
    hidden=True, resizable=True, allow_high_dpi=True
)
WIN_SURF: Final[pg.Surface] = WIN.get_surface()
WIN.minimum_size = (950, 600)
