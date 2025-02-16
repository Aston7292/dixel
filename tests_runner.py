"""Runs every test in the tests directory (a test file must start with test)."""

from unittest import TestLoader, TestSuite, TextTestRunner

import pygame as pg

pg.init()
pg.display.set_mode(flags=pg.HIDDEN)

test_suite: TestSuite = TestLoader().discover("tests")
TextTestRunner().run(test_suite)  # The resize method is first to test methods with different sizes
