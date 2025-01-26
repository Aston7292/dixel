"""Types shared between files."""

from typing import Any

import pygame as pg

PosPair = tuple[int, int]
SizePair = tuple[int, int]
Color = list[int]

CheckboxInfo = tuple[pg.Surface, str]
ToolInfo = tuple[str, dict[str, Any]]

BlitSequence = list[tuple[pg.Surface, PosPair]]
LayeredBlitInfo = tuple[pg.Surface, PosPair, int]
