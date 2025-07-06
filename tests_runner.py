"""Runs every test in the tests directory (a test file must start with test)."""

from unittest import TestLoader, TestSuite, TextTestRunner
from typing import Final

import pygame as pg

pg.init()
pg.Window("", (1, 1), hidden=True).get_surface()

_TEST_SUITE: Final[TestSuite] = TestLoader().discover("tests")
TextTestRunner().run(_TEST_SUITE)
