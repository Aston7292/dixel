"""Runs every test in the tests directory (a test file must start with test)."""

from unittest import TestLoader, TestSuite, TextTestRunner

import pygame as pg

loader: TestLoader = TestLoader()
suite: TestSuite = loader.discover("tests")

pg.init()
pg.display.set_mode(flags=pg.HIDDEN)

runner: TextTestRunner = TextTestRunner()
runner.run(suite)  # The resize method runs as first to test other methods at different sizes
