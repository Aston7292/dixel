"""Tests for the devices file."""

from unittest import TestCase, mock
from unittest.mock import Mock
from typing import Self

from pygame import Rect, K_1, K_END, K_KP1, KMOD_NONE, KMOD_ALT, KMOD_NUM, key

from src.classes.devices import _Mouse, _Keyboard

import src.obj_utils as objs
from src.consts import BG_LAYER, ELEMENT_LAYER

from tests.utils import DummyUIElement


class TestDevices(TestCase):
    """Tests for the devices file."""

    def test_refresh_hovered_obj(self: Self) -> None:
        """Tests the Mouse.refresh_hovered_obj method."""

        obj_1: DummyUIElement = DummyUIElement((
            Rect(0, 0, 5, 5),
            Rect(5, 5, 5, 5)
        ))
        obj_2: DummyUIElement = DummyUIElement((
            Rect(5, 5, 5, 5),
            Rect(10, 10, 5, 5)
        ))

        mouse: _Mouse = _Mouse()

        mouse.x = mouse.y = -1
        mouse.hovered_obj = obj_1
        objs.state_active_objs = [obj_1, obj_2]
        mouse.refresh_hovered_obj()
        self.assertIsNone(mouse.hovered_obj)

        mouse.x = mouse.y = 0
        mouse.hovered_obj = None
        objs.state_active_objs = [obj_1, obj_2]
        mouse.refresh_hovered_obj()
        self.assertEqual(mouse.hovered_obj, obj_1)

        mouse.x = mouse.y = 5
        mouse.hovered_obj = None
        obj_1.layer, obj_2.layer = ELEMENT_LAYER, BG_LAYER
        objs.state_active_objs = [obj_1, obj_2]
        mouse.refresh_hovered_obj()
        self.assertEqual(mouse.hovered_obj, obj_1)

        mouse.x = mouse.y = 5
        mouse.hovered_obj = None
        obj_1.layer, obj_2.layer = BG_LAYER, ELEMENT_LAYER
        objs.state_active_objs = [obj_1, obj_2]
        mouse.refresh_hovered_obj()
        self.assertEqual(mouse.hovered_obj, obj_2)

    def test_refresh_timed(self: Self) -> None:
        """Tests the Keyboard.refresh_timed method."""

        keyboard: _Keyboard = _Keyboard()

        keyboard.pressed = [K_1]
        keyboard.timed = []
        keyboard._prev_timed_refresh = -1_000
        keyboard._alt_k = ""
        keyboard.refresh_timed()
        self.assertListEqual(keyboard.timed, [K_1])

        keyboard.pressed = [K_1]
        keyboard.timed = []
        keyboard._alt_k = "1"
        keyboard.is_alt_on = False
        keyboard.refresh_timed()
        self.assertListEqual(keyboard.timed, [1])
        self.assertEqual(keyboard._alt_k, "")

    @mock.patch.object(key, "get_mods", autospec=True)
    def test_add(self: Self, mock_get_mods: Mock) -> None:
        """Tests the Keyboard.add method (mocks the pygame.key.get_mods() method)."""

        keyboard: _Keyboard = _Keyboard()

        mock_get_mods.return_value = KMOD_NONE
        keyboard._raws = keyboard.pressed = []
        keyboard.add(K_KP1)
        self.assertListEqual(keyboard._raws, [K_KP1])
        self.assertListEqual(keyboard.pressed, [K_END])

        mock_get_mods.return_value = KMOD_NUM
        keyboard._raws = keyboard.pressed = []
        keyboard.is_numpad_on = False
        keyboard.add(K_KP1)
        self.assertTrue(keyboard.is_numpad_on)
        self.assertListEqual(keyboard.pressed, [K_1])

        mock_get_mods.return_value = KMOD_ALT
        keyboard._raws = keyboard.pressed = []
        keyboard.is_alt_on = False
        keyboard._alt_k = ""
        keyboard.add(K_1)
        self.assertListEqual(keyboard._raws, [])
        self.assertEqual(keyboard._alt_k, "1")

        mock_get_mods.return_value = KMOD_ALT
        keyboard._raws = keyboard.pressed = []
        keyboard.is_alt_on = False
        keyboard._alt_k = "1114111"
        keyboard.add(K_1)
        self.assertEqual(keyboard._alt_k, "1")

    @mock.patch.object(key, "get_mods", autospec=True)
    def test_remove(self: Self, mock_get_mods: Mock) -> None:
        """Tests the Keyboard.remove method (mocks the pygame.key.get_mods() method)."""

        keyboard: _Keyboard = _Keyboard()

        mock_get_mods.return_value = KMOD_NONE
        keyboard._raws    = [K_KP1, K_KP1]
        keyboard.pressed = [K_KP1, K_KP1]
        keyboard.released = []
        keyboard.remove(K_KP1)
        self.assertListEqual(keyboard._raws, [K_KP1])
        self.assertListEqual(keyboard.pressed , [K_END])
        self.assertListEqual(keyboard.released, [K_END])

        mock_get_mods.return_value = KMOD_NUM
        keyboard._raws    = [K_KP1, K_KP1]
        keyboard.pressed = [K_KP1, K_KP1]
        keyboard.released = []
        keyboard.is_numpad_on = False
        keyboard.remove(K_KP1)
        self.assertTrue(keyboard.is_numpad_on)
        self.assertListEqual(keyboard.pressed , [K_1])
        self.assertListEqual(keyboard.released, [K_1])

        mock_get_mods.return_value = KMOD_NONE
        keyboard._raws    = [K_1]
        keyboard.pressed = [K_1]
        keyboard.released = []
        keyboard.remove(K_1)
        self.assertListEqual(keyboard.released, [K_1])
