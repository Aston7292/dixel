"""Tests for the text_label file."""

from unittest import TestCase, mock

import pygame as pg

from src.classes.text_label import TextLabel, renderers_cache

from src.utils import RectPos, resize_obj
from src.type_utils import PosPair, SizePair, LayeredBlitInfo
from src.consts import WHITE, TEXT_LAYER

from tests.utils import cmp_imgs


class TestTextLabel(TestCase):
    """Tests for the TextLabel class."""

    _text_label: TextLabel
    _renderer: pg.Font

    @classmethod
    def setUpClass(cls: type["TestTextLabel"]) -> None:
        """Creates the text and a model renderer."""

        cls._text_label = TextLabel(RectPos(1, 2, "center"), "hello\n!", 1, 30, WHITE)
        cls._renderer = pg.font.SysFont("helvetica", 30)

    def _copy_text_label(self) -> TextLabel:
        """
        Creates a copy of the text label.

        Returns:
            copy
        """

        pos: RectPos = RectPos(
            self._text_label.init_pos.x, self._text_label.init_pos.y,
            self._text_label.init_pos.coord_type
        )
        text: str = self._text_label.text
        layer: int = self._text_label.layer - TEXT_LAYER
        h: int = self._text_label._init_h

        copy_text_label: TextLabel = TextLabel(pos, text, layer, h, self._text_label._bg_color)
        copy_text_label.resize(2, 3)

        return copy_text_label

    @mock.patch.object(TextLabel, "_get_rects", autospec=True)
    def test_init(self, mock_get_rects: mock.Mock) -> None:
        """Tests the init method, mocks TextLabel.get_rects."""

        img: pg.Surface
        line: str

        text_label: TextLabel = TextLabel(RectPos(1, 2, "center"), "hello\n!", 1, 30, WHITE)

        self.assertEqual(text_label.init_pos, RectPos(1, 2, "center"))

        self.assertEqual(text_label._init_h, 30)
        self.assertIs(renderers_cache[text_label._init_h], text_label._renderer)

        self.assertEqual(text_label.text, "hello\n!")
        self.assertListEqual(text_label._lines, ["hello", "!"])
        self.assertEqual(text_label._bg_color, WHITE)

        self.assertEqual(text_label.layer, 1 + TEXT_LAYER)

        renderer: pg.Font = pg.font.SysFont("helvetica", 30)
        for img, line in zip(text_label._imgs, text_label._lines, strict=True):
            expected_img: pg.Surface = renderer.render(line, True, WHITE, WHITE).convert()
            self.assertTrue(cmp_imgs(img.convert(), expected_img, False))

        mock_get_rects.assert_called_once_with(
            text_label, (text_label.init_pos.x, text_label.init_pos.y)
        )

        transparent_bg_text_label: TextLabel = TextLabel(RectPos(0, 0, "topleft"), "hello")
        self.assertIsNone(transparent_bg_text_label._bg_color)

    def test_get_blit_sequence(self) -> None:
        """Tests the get_blit_sequence method."""

        expected_sequence: list[LayeredBlitInfo] = [
            (img, rect.topleft, self._text_label.layer)
            for img, rect in zip(self._text_label._imgs, self._text_label._rects, strict=True)
        ]

        self.assertListEqual(self._text_label.get_blit_sequence(), expected_sequence)

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._refresh_rects)
    def test_a_resize(self, mock_get_rects: mock.Mock) -> None:
        """Tests the resize method as first, mocks TextLabel.get_rects."""

        expected_xy: PosPair
        _: int
        expected_h: int
        img: pg.Surface
        line: str

        expected_xy, (_, expected_h) = resize_obj(
            self._text_label.init_pos, 0, self._text_label._init_h, 2, 3, True
        )

        self._text_label.resize(2, 3)
        self.__class__._renderer = pg.font.SysFont("helvetica", 60)
        self.assertIs(renderers_cache[expected_h], self._text_label._renderer)

        for img, line in zip(self._text_label._imgs, self._text_label._lines, strict=True):
            expected_img: pg.Surface = self._renderer.render(line, True, WHITE, WHITE).convert()
            self.assertTrue(cmp_imgs(img.convert(), expected_img, False))
        mock_get_rects.assert_called_once_with(self._text_label, expected_xy)

    def test_get_rects(self) -> None:
        """Tests the get_rects method."""

        line_rect_x: int
        line_rect_y: int
        img: pg.Surface

        copy_text_label: TextLabel = self._copy_text_label()
        copy_text_label._refresh_rects((2, 3))

        expected_rect: pg.Rect = pg.Rect()
        expected_rects: list[pg.Rect] = []
        expected_rect.center = (2, 3)
        expected_rect.w = max([img.get_width() for img in copy_text_label._imgs])
        expected_rect.h = sum([img.get_height() for img in copy_text_label._imgs])

        line_rect_x, line_rect_y = expected_rect.topleft
        for img in copy_text_label._imgs:
            line_rect_h: int = img.get_height()
            line_rect: pg.Rect = pg.Rect(line_rect_x, line_rect_y, expected_rect.w, line_rect_h)
            line_center: PosPair = line_rect.center

            line_rect.w = img.get_width()
            line_rect.center = line_center
            expected_rects.append(line_rect)

            line_rect_y += line_rect.h

        self.assertEqual(copy_text_label.rect, expected_rect)
        self.assertListEqual(copy_text_label._rects, expected_rects)

    def test_move_rect(self) -> None:
        """Tests the move_rect method."""

        expected_xy: PosPair
        _: SizePair
        rect: pg.Rect

        copy_text_label: TextLabel = self._copy_text_label()
        copy_text_label.move_rect(3, 4, 2, 3)

        expected_init_pos: RectPos = RectPos(3, 4, "center")
        self.assertEqual(copy_text_label.init_pos, expected_init_pos)

        expected_xy, _ = resize_obj(expected_init_pos, 0, 0, 2, 3)
        self.assertTupleEqual(copy_text_label.rect.center, expected_xy)
        for rect in copy_text_label._rects:
            expected_xy, _ = resize_obj(expected_init_pos, 0, 0, 2, 3)
            self.assertTupleEqual(rect.center, expected_xy)
            expected_init_pos.y += rect.h

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._refresh_rects)
    def test_set_text(self, mock_get_rects: mock.Mock) -> None:
        """Tests the set_text method, mocks TextLabel.get_rects."""

        img: pg.Surface
        line: str

        copy_text_label: TextLabel = self._copy_text_label()
        init_num_get_rects_calls: int = mock_get_rects.call_count

        copy_text_label.set_text("hello\n?")
        self.assertEqual(mock_get_rects.call_count, init_num_get_rects_calls + 1)

        self.assertEqual(copy_text_label.text, "hello\n?")
        self.assertListEqual(copy_text_label._lines, ["hello", "?"])
        for img, line in zip(copy_text_label._imgs, copy_text_label._lines, strict=True):
            expected_img: pg.Surface = self._renderer.render(line, True, WHITE, WHITE).convert()
            self.assertTrue(cmp_imgs(img.convert(), expected_img, False))

        mock_get_rects.assert_called_with(copy_text_label, copy_text_label.rect.center)

    def test_get_pos_at(self) -> None:
        """Tests the get_pos_at method."""

        start_x: int = self._text_label.rect.x

        # See if the render with antialiasing has the same width as the one without (font specific)
        x_2: int = start_x + self._renderer.render("he", True, WHITE, WHITE).get_width()
        x_5: int = start_x + self._renderer.render("hello", True, WHITE, WHITE).get_width()

        self.assertEqual(self._text_label.get_x_at(0), start_x)
        self.assertEqual(self._text_label.get_x_at(2), x_2)
        self.assertEqual(self._text_label.get_x_at(5), x_5)

    def test_get_closest_to(self) -> None:
        """Tests the get_closest_to method."""

        line_rect_left: int = self._text_label.rect.left
        line_rect_right: int = self._text_label.rect.right
        pos_2: int = line_rect_left + self._renderer.render("he", True, WHITE, WHITE).get_width()
        turning_x: int = pos_2 + (self._renderer.render("l", True, WHITE, WHITE).get_width() // 2)
        text_len: int = len(self._text_label.text)

        self.assertEqual(self._text_label.get_closest_to(line_rect_left - 1), 0)
        self.assertEqual(self._text_label.get_closest_to(line_rect_left), 0)
        self.assertEqual(self._text_label.get_closest_to(pos_2 - 1), 2)
        self.assertEqual(self._text_label.get_closest_to(pos_2 + 1), 2)
        self.assertEqual(self._text_label.get_closest_to(turning_x), 2)
        self.assertEqual(self._text_label.get_closest_to(turning_x + 1), 3)
        self.assertEqual(self._text_label.get_closest_to(line_rect_right), text_len)
        self.assertEqual(self._text_label.get_closest_to(line_rect_right + 1), text_len)
