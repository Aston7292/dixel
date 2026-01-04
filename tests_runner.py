"""Runs every test in the tests directory (a test file must start with test)."""

from unittest import TestLoader, TestSuite, TextTestRunner
from typing import Final

import pygame as pg
from pygame import Window

pg.init()
Window("", (1, 1), hidden=True).get_surface()

_TEST_SUITE: Final[TestSuite] = TestLoader().discover("tests", "test_devices.py")
TextTestRunner().run(_TEST_SUITE)
