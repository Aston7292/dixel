"""
Runs every test in the tests directory (a test file must start with test)
"""

import pygame as pg
import unittest

loader: unittest.TestLoader = unittest.TestLoader()
suite: unittest.TestSuite = loader.discover("tests")

pg.init()
pg.display.set_mode(flags=pg.HIDDEN)

'''
In the tests the handle_resize method runs as second
to make sure other methods work at different sizes
and the init method runs as first to check initialization before resizing
'''

runner: unittest.TextTestRunner = unittest.TextTestRunner()
runner.run(suite)
