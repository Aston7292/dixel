"""Runs every test in the tests directory (a test file must start with test)."""

from unittest import TestLoader, TestSuite, TextTestRunner

from pygame import init as pg_init, Window

pg_init()
Window(hidden=True).get_surface()

test_suite: TestSuite = TestLoader().discover("tests")
TextTestRunner().run(test_suite)
