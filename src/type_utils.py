"""Types shared between files."""

from typing import Optional, Any

import pygame as pg

OptColor = Optional[list[int]]
CheckboxInfo = tuple[pg.Surface, Optional[str]]
ToolInfo = tuple[str, dict[str, Any]]

BlitSequence = list[tuple[pg.Surface, tuple[int, int]]]
LayeredBlitInfo = tuple[pg.Surface, tuple[int, int], int]
LayeredBlitSequence = list[LayeredBlitInfo]
