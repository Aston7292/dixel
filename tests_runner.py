"""
Runs every test in the tests directory (a test file must start with test)
"""

import pygame as pg
import unittest

loader: unittest.TestLoader = unittest.TestLoader()
suite: unittest.TestSuite = loader.discover('tests')

pg.init()
pg.display.set_mode(flags=pg.HIDDEN)

runner: unittest.TextTestRunner = unittest.TextTestRunner()
runner.run(suite)
