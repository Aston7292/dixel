"""Runs every test in the tests directory (a test file must start with test)."""

from unittest import TestLoader, TestSuite, TextTestRunner
from typing import Final

import pygame as pg

pg.init()
pg.Window(hidden=True).get_surface()

_TEST_SUITE: Final[TestSuite] = TestLoader().discover("tests")
TextTestRunner().run(_TEST_SUITE)
