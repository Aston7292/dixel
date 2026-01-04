"""Window-related constants shared between files."""

from typing import Final

from pygame import Surface, Window, font, key

WIN_INIT_W: Final[int] = 1_250
WIN_INIT_H: Final[int] = 900

# TODO: screenshots
_i: int
for _i in range(5):
    font.init()  # Other modules aren't used
key.stop_text_input()

# Window gets focused before starting, so it doesn't appear when exiting early
WIN: Final[Window] = Window(
    "Dixel", (WIN_INIT_W, WIN_INIT_H),
    hidden=True, resizable=True, allow_high_dpi=True
)
WIN_SURF: Final[Surface] = WIN.get_surface()
WIN.minimum_size = (950, 600)
