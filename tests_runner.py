"""Runs every test in the tests directory (a test file must start with test)."""

import unittest

import pygame as pg

loader: unittest.TestLoader = unittest.TestLoader()
suite: unittest.TestSuite = loader.discover("tests")

pg.init()
pg.display.set_mode(flags=pg.HIDDEN)

runner: unittest.TextTestRunner = unittest.TextTestRunner()
runner.run(suite)  # The resize method runs as first to test other methods at different sizes
