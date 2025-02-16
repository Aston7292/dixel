"""Tests for the clickable file."""

from unittest import TestCase, mock
from typing import Final, Optional, Any

import pygame as pg

from src.classes.clickable import Clickable, Checkbox, Button
from src.classes.text_label import TextLabel

from src.utils import RectPos, ObjInfo, Mouse, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import BLACK, ELEMENT_LAYER

from tests.utils import cmp_imgs

IMG_OFF: Final[pg.Surface] = pg.Surface((10, 11), pg.SRCALPHA)
IMG_ON: Final[pg.Surface] = IMG_OFF.copy()
IMG_ON.fill((0, 0, 1, 0))


class TestCheckbox(TestCase):
    """Tests for the Checkbox class."""

    _checkbox: Checkbox

    @classmethod
    def setUpClass(cls: type["TestCheckbox"]) -> None:
        """Creates the checkbox."""

        cls._checkbox = Checkbox(
            RectPos(1, 2, "center"), [IMG_OFF, IMG_ON], "hello", "world\n!", 1
        )

    def _copy_checkbox(self) -> Checkbox:
        """
        Creates a copy of the checkbox.

        Returns:
            copy
        """

        hovering_text: Optional[str]

        coord_type: str = self._checkbox.init_pos.coord_type
        pos: RectPos = RectPos(self._checkbox.init_pos.x, self._checkbox.init_pos.y, coord_type)
        imgs: list[pg.Surface] = self._checkbox.init_imgs
        text: str = self._checkbox.objs_info[0].obj.text
        if self._checkbox.hovering_text_label:
            hovering_text = self._checkbox.hovering_text_label.text
        else:
            hovering_text = None
        layer: int = self._checkbox.layer - ELEMENT_LAYER

        copy_checkbox: Checkbox = Checkbox(pos, imgs, text, hovering_text, layer)
        copy_checkbox.resize(2, 3)

        return copy_checkbox

    @mock.patch.object(TextLabel, "__init__", autospec=True, return_value=None)
    def test_init(self, mock_text_label_init: mock.Mock) -> None:
        """Tests the init method, mocks TextLabel.__init__."""

        # Also tests the Clickable abstract class

        pos: RectPos = RectPos(1, 2, "center")
        test_checkbox: Checkbox = Checkbox(pos, [IMG_OFF, IMG_ON], "hello", "world\n!", 1)
        self.assertEqual(mock_text_label_init.call_count, 2)

        self.assertEqual(test_checkbox.init_pos, pos)
        self.assertListEqual(test_checkbox.init_imgs, [IMG_OFF, IMG_ON])

        self.assertListEqual(test_checkbox.imgs, [IMG_OFF, IMG_ON])
        self.assertEqual(test_checkbox.rect, IMG_OFF.get_rect(center=(1, 2)))

        self.assertEqual(test_checkbox.img_i, 0)

        self.assertFalse(test_checkbox._is_hovering)

        self.assertEqual(test_checkbox.layer, 1 + ELEMENT_LAYER)

        hovering_text_label_init_call: mock._Call = mock_text_label_init.call_args_list[0]
        expected_hovering_text_label_init_args: tuple[Any, ...] = (
            test_checkbox.hovering_text_label, RectPos(0, 0, "topleft"), "world\n!", 2, 12, BLACK
        )
        self.assertTupleEqual(
            hovering_text_label_init_call[0], expected_hovering_text_label_init_args
        )

        # Checkbox attrs before extra TextLabel.__init__ calls

        self.assertFalse(test_checkbox.is_checked)

        text_label_init_args: mock._Call = mock_text_label_init.call_args_list[1]
        text_label: TextLabel = text_label_init_args[0]
        expected_text_label_init_args: tuple[Any, ...] = (
            text_label, RectPos(test_checkbox.rect.centerx, test_checkbox.rect.y - 5, "midbottom"),
            "hello", 1, 16
        )
        self.assertTupleEqual(text_label_init_args[0], expected_text_label_init_args)

        self.assertListEqual(test_checkbox.objs_info, [ObjInfo(text_label)])

        # Edge cases

        no_hovering_text_checkbox: Checkbox = Checkbox(pos, [IMG_OFF, IMG_ON], "hello", None)
        self.assertIsNone(no_hovering_text_checkbox.hovering_text_label)

    def test_get_blit_sequence(self) -> None:
        """Tests the get_blit_sequence method."""

        mouse_x: int
        mouse_y: int

        copy_checkbox: Checkbox = self._copy_checkbox()

        expected_sequence_0: list[LayeredBlitInfo] = [
            (copy_checkbox.imgs[0], copy_checkbox.rect.topleft, copy_checkbox.layer)
        ]
        self.assertListEqual(copy_checkbox.get_blit_sequence(), expected_sequence_0)

        expected_sequence_1: list[LayeredBlitInfo] = [
            (copy_checkbox.imgs[1], copy_checkbox.rect.topleft, copy_checkbox.layer)
        ]
        if copy_checkbox.hovering_text_label:
            mouse_x, mouse_y = pg.mouse.get_pos()
            copy_checkbox.hovering_text_label.move_rect(mouse_x + 15, mouse_y, 1, 1)
            expected_sequence_1.extend(copy_checkbox.hovering_text_label.get_blit_sequence())

        copy_checkbox.img_i = 1
        copy_checkbox._is_hovering = True
        self.assertListEqual(copy_checkbox.get_blit_sequence(), expected_sequence_1)

        # Hovering without hovering text

        copy_checkbox.hovering_text_label = None
        expected_sequence_1 = [
            (copy_checkbox.imgs[1], copy_checkbox.rect.topleft, copy_checkbox.layer)
        ]
        self.assertListEqual(copy_checkbox.get_blit_sequence(), expected_sequence_1)

    def test_get_hovering_info(self) -> None:
        """Tests the get_hovering_info method."""

        is_hovering: bool
        layer: int

        is_hovering, layer = self._checkbox.get_hovering_info(self._checkbox.rect.topleft)
        self.assertTrue(is_hovering)
        self.assertEqual(layer, 1 + ELEMENT_LAYER)

        is_hovering, layer = self._checkbox.get_hovering_info((self._checkbox.rect.x - 1, 0))
        self.assertFalse(is_hovering)

    def test_leave(self) -> None:
        """Tests the leave method."""

        copy_checkbox: Checkbox = self._copy_checkbox()
        copy_checkbox._is_hovering = True
        copy_checkbox.leave()

        self.assertFalse(copy_checkbox._is_hovering)

    @mock.patch.object(TextLabel, "resize", autospec=True, wraps=TextLabel.resize)
    def test_a_resize(self, mock_text_label_resize: mock.Mock) -> None:
        """Tests the resize method as first, mocks TextLabel.resize."""

        init_w: int
        init_h: int
        expected_xy: PosPair
        expected_wh: SizePair
        img: pg.Surface
        expected_img: pg.Surface

        self._checkbox.resize(2, 3)

        init_w, init_h = IMG_OFF.get_size()

        expected_xy, expected_wh = resize_obj(
            self._checkbox.init_pos, init_w, init_h, 2, 3
        )
        expected_imgs: list[pg.Surface] = [
            pg.transform.scale(img, expected_wh) for img in self._checkbox.init_imgs
        ]
        expected_rect: pg.Rect = expected_imgs[0].get_rect(center=expected_xy)

        for img, expected_img in zip(self._checkbox.imgs, expected_imgs, strict=True):
            self.assertTrue(cmp_imgs(img, expected_img))
        self.assertEqual(self._checkbox.rect, expected_rect)

        text_label: Optional[TextLabel] = self._checkbox.hovering_text_label
        mock_text_label_resize.assert_called_once_with(text_label, 2, 3)

        copy_checkbox: Checkbox = self._copy_checkbox()
        copy_checkbox.hovering_text_label = None
        copy_checkbox.resize(2, 3)  # Assert it doesn't crash

    def test_move_rect(self) -> None:
        """Tests the move_rect method."""

        expected_xy: PosPair
        _: SizePair

        copy_checkbox: Checkbox = self._copy_checkbox()
        copy_checkbox.move_rect(3, 4, 2, 3)

        expected_xy, _ = resize_obj(copy_checkbox.init_pos, 0, 0, 2, 3)
        self.assertEqual(copy_checkbox.init_pos.x, 3)
        self.assertEqual(copy_checkbox.init_pos.y, 4)
        self.assertTupleEqual(copy_checkbox.rect.center, expected_xy)

    @mock.patch.object(pg.mouse, "set_cursor", autospec=True)
    def test_handle_hover(self, mock_set_cursor: mock.Mock) -> None:
        """Tests the Clickable._handle_hover method, mocks pygame.set_cursor."""

        copy_checkbox: Checkbox = self._copy_checkbox()

        copy_checkbox._is_hovering = True
        copy_checkbox._handle_hover(None)
        self.assertFalse(copy_checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_ARROW)

        copy_checkbox._handle_hover(copy_checkbox)
        self.assertTrue(copy_checkbox._is_hovering)
        mock_set_cursor.assert_called_with(pg.SYSTEM_CURSOR_HAND)

    @mock.patch.object(Clickable, "_handle_hover", autospec=True, wraps=Clickable._handle_hover)
    def test_upt(self, mock_handle_hover: mock.Mock) -> None:
        """Tests the upt method, mocks Clickable._check_hover."""

        copy_checkbox: Checkbox = self._copy_checkbox()
        mouse_info: Mouse = Mouse(0, 0, [False] * 3, [True] * 3, 0)
        blank_mouse_info: Mouse = Mouse(0, 0, [False] * 3, [False] * 3, 0)

        # Don't hover and click
        self.assertFalse(copy_checkbox.upt(None, mouse_info))
        mock_handle_hover.assert_called_once_with(copy_checkbox, None)

        # Hover and click twice
        self.assertTrue(copy_checkbox.upt(copy_checkbox, mouse_info))
        self.assertTrue(copy_checkbox.is_checked)
        self.assertEqual(copy_checkbox.img_i, 1)
        self.assertFalse(copy_checkbox.upt(copy_checkbox, mouse_info))
        self.assertFalse(copy_checkbox.is_checked)
        self.assertEqual(copy_checkbox.img_i, 0)

        # Check twice with shortcut
        self.assertTrue(copy_checkbox.upt(None, mouse_info, True))
        self.assertTrue(copy_checkbox.is_checked)
        self.assertFalse(copy_checkbox.upt(None, mouse_info, True))
        self.assertFalse(copy_checkbox.is_checked)

        # Don't hover and don't click
        self.assertFalse(copy_checkbox.upt(None, mouse_info))
        # Hover and don't click
        self.assertFalse(copy_checkbox.upt(copy_checkbox, blank_mouse_info))


class TestButton(TestCase):
    """Tests for the Button class."""

    _button: Button

    @classmethod
    def setUpClass(cls: type["TestButton"]) -> None:
        """Creates the button."""

        cls._button = Button(
            RectPos(1, 2, "center"), [IMG_OFF, IMG_ON], "hello", "world\n!", 1, 10
        )

    def _copy_button(self) -> Button:
        """
        Creates a copy of the button.

        Returns:
            copy
        """

        hovering_text: Optional[str]

        coord_type: str = self._button.init_pos.coord_type
        pos: RectPos = RectPos(self._button.init_pos.x, self._button.init_pos.y, coord_type)
        imgs: list[pg.Surface] = self._button.init_imgs
        text: str = self._button.objs_info[0].obj.text
        if self._button.hovering_text_label:
            hovering_text = self._button.hovering_text_label.text
        else:
            hovering_text = None
        layer: int = self._button.layer - ELEMENT_LAYER
        text_h: int = self._button.objs_info[0].obj._init_h

        copy_button: Button = Button(pos, imgs, text, hovering_text, layer, text_h)
        copy_button.resize(2, 3)

        return copy_button

    @mock.patch.object(TextLabel, "__init__", autospec=True, return_value=None)
    @mock.patch.object(Clickable, "__init__", autospec=True, wraps=Clickable.__init__)
    def test_init(self, mock_clickable_init: mock.Mock, mock_text_label_init: mock.Mock) -> None:
        """Tests the init method, mocks Clickable.__init__ and TextLabel.__init__."""

        pos: RectPos = RectPos(1, 2, "center")
        imgs: list[pg.Surface] = [IMG_OFF, IMG_ON]
        test_button: Button = Button(pos, imgs, "hello", "world\n!", 1, 10)
        mock_clickable_init.assert_called_once_with(test_button, pos, imgs, "world\n!", 1)
        self.assertEqual(mock_text_label_init.call_count, 2)

        text_label: TextLabel = mock_text_label_init.call_args[0][0]
        expected_pos: RectPos = RectPos(*test_button.rect.center, "center")
        mock_text_label_init.assert_called_with(text_label, expected_pos, "hello", 1, 10)
        self.assertListEqual(test_button.objs_info, [ObjInfo(text_label)])

        no_text_button: Button = Button(pos, imgs, None, None)
        self.assertListEqual(no_text_button.objs_info, [])

    @mock.patch.object(Clickable, "_handle_hover", autospec=True, wraps=Clickable._handle_hover)
    def test_upt(self, mock_handle_hover: mock.Mock) -> None:
        """Tests the upt method, mocks Clickable._check_hover."""

        copy_button: Button = self._copy_button()
        mouse_info: Mouse = Mouse(0, 0, [False] * 3, [True] * 3, 0)
        blank_mouse_info: Mouse = Mouse(0, 0, [False] * 3, [False] * 3, 0)

        # Don't hover and click
        self.assertFalse(copy_button.upt(None, mouse_info))
        mock_handle_hover.assert_called_once_with(copy_button, None)
        self.assertEqual(copy_button.img_i, 0)

        # Hover and click
        copy_button._is_hovering = False
        self.assertTrue(copy_button.upt(copy_button, mouse_info))
        self.assertEqual(copy_button.img_i, 1)

        # Don't hover and don't click
        self.assertFalse(copy_button.upt(None, blank_mouse_info))
        # Hover and don't click
        self.assertFalse(copy_button.upt(copy_button, blank_mouse_info))
