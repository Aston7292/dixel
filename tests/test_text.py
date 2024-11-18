"""Tests for the text file."""

from unittest import TestCase, mock
from itertools import zip_longest

import pygame as pg

from src.classes.text_label import TextLabel, renderers_cache

from src.utils import RectPos, Ratio, resize_obj
from src.type_utils import LayeredBlitSequence
from src.consts import WHITE, TEXT_LAYER

from tests.utils import cmp_imgs, RESIZING_RATIO


class TestTextLabel(TestCase):
    """Tests for the TextLabel class."""

    text_label: TextLabel
    renderer: pg.Font

    @classmethod
    def setUpClass(cls: type["TestTextLabel"]) -> None:
        """Creates the text and a model renderer."""

        cls.text_label = TextLabel(RectPos(1, 2, 'center'), "hello\n!", 1, 30)
        cls.renderer = pg.font.SysFont("helvetica", 30)

    def copy_text_label(self) -> TextLabel:
        """
        Creates a copy of the text label.

        Returns:
            copy
        """

        layer: int = self.text_label._layer - TEXT_LAYER

        text_label_copy: TextLabel = TextLabel(
            self.text_label.init_pos, self.text_label.text, layer, self.text_label._init_h
        )
        text_label_copy.resize(RESIZING_RATIO)

        return text_label_copy

    @mock.patch.object(TextLabel, "_get_rects")
    def test_init(self, get_rects_mock: mock.Mock) -> None:
        """Tests the init method, mocks the get_rects method."""

        text_label: TextLabel = TextLabel(RectPos(1, 2, 'center'), "hello\n!", 1, 30)

        self.assertEqual(text_label.init_pos, RectPos(1, 2, 'center'))

        self.assertEqual(text_label._init_h, 30)
        self.assertIs(renderers_cache[text_label._init_h], text_label._renderer)

        self.assertEqual(text_label.text, "hello\n!")
        self.assertTupleEqual(text_label._lines, tuple(text_label.text.split('\n')))

        self.assertEqual(text_label._layer, 1 + TEXT_LAYER)

        renderer: pg.Font = pg.font.SysFont("helvetica", 30)
        for img, line in zip_longest(text_label._imgs, text_label._lines):
            expected_img: pg.Surface = renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))

        get_rects_mock.assert_called_once_with((text_label.init_pos.x, text_label.init_pos.y))

    def test_blit(self) -> None:
        """Tests the blit method."""

        expected_sequence: LayeredBlitSequence = [
            (img, rect.topleft, self.text_label._layer)
            for img, rect in zip_longest(self.text_label._imgs, self.text_label.rects)
        ]

        self.assertListEqual(self.text_label.blit(), expected_sequence)

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._get_rects)
    def test_a_resize(self, get_rects_mock: mock.Mock) -> None:
        """Tests the resize method as first, mocks the get_rects method."""

        expected_pos: tuple[int, int]
        expected_h: int
        expected_pos, (_, expected_h) = resize_obj(
            self.text_label.init_pos, 0.0, self.text_label._init_h, RESIZING_RATIO, True
        )

        self.text_label.resize(RESIZING_RATIO)
        self.__class__.renderer = pg.font.SysFont("helvetica", 60)
        self.assertIs(renderers_cache[expected_h], self.text_label._renderer)

        for img, line in zip_longest(self.text_label._imgs, self.text_label._lines):
            expected_img: pg.Surface = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))
        get_rects_mock.assert_called_once_with(self.text_label, expected_pos)

    def test_get_rects(self) -> None:
        """Tests the get_rects method."""

        text_label_copy: TextLabel = self.copy_text_label()
        text_label_copy._get_rects((2, 3))

        expected_rects: list[pg.Rect] = []
        rect_w: int = max(img.get_width() for img in text_label_copy._imgs)
        rect_h: int = sum(img.get_height() for img in text_label_copy._imgs)
        expected_rect: pg.Rect = pg.Rect(0, 0, rect_w, rect_h)
        setattr(expected_rect, text_label_copy.init_pos.coord_type, (2, 3))

        line_rect_y: int = expected_rect.y
        for img in text_label_copy._imgs:
            line_rect: pg.Rect = img.get_rect(topleft=(expected_rect.x, line_rect_y))
            line_rect.x += round((expected_rect.w - line_rect.w) / 2.0)
            expected_rects.append(line_rect)
            line_rect_y += expected_rects[-1].h

        self.assertEqual(text_label_copy.rect, expected_rect)
        self.assertListEqual(text_label_copy.rects, expected_rects)

    @mock.patch.object(TextLabel, "_get_rects")
    def test_move_rect(self, get_rects_mock: mock.Mock) -> None:
        """Tests the move_rect method, mocks the get_rects method."""

        text_label_copy: TextLabel = self.copy_text_label()
        text_label_copy.move_rect(3, 4, Ratio(2.1, 3.2))

        self.assertEqual(
            text_label_copy.init_pos, RectPos(3, 4, text_label_copy.init_pos.coord_type)
        )
        get_rects_mock.assert_called_with(
            (round(text_label_copy.init_pos.x * 2.1), round(text_label_copy.init_pos.y * 3.2))
        )

    @mock.patch.object(TextLabel, "_get_rects")
    def test_set_text(self, get_rects_mock: mock.Mock) -> None:
        """Tests the set_text method, mocks the get_rects method."""

        text_label_copy: TextLabel = self.copy_text_label()
        text_label_copy.set_text("hello\n?")

        self.assertEqual(text_label_copy.text, "hello\n?")
        self.assertTupleEqual(text_label_copy._lines, tuple(text_label_copy.text.split('\n')))
        for img, line in zip_longest(text_label_copy._imgs, text_label_copy._lines):
            expected_img: pg.Surface = self.renderer.render(line, True, WHITE)
            self.assertTrue(cmp_imgs(img, expected_img))

        get_rects_mock.assert_called_with(
            getattr(text_label_copy.rect, text_label_copy.init_pos.coord_type)
        )

    def test_get_pos_at(self) -> None:
        """Tests the get_pos_at method."""

        start_x: int = self.text_label.rects[0].x

        # See if the render with antialiasing has the same width as the one without (font specific)
        x_2: int = start_x + self.renderer.render("he", True, WHITE).get_width()
        x_5: int = start_x + self.renderer.render("hello", True, WHITE).get_width()

        self.assertEqual(self.text_label.get_pos_at(0), start_x)
        self.assertEqual(self.text_label.get_pos_at(2), x_2)
        self.assertEqual(self.text_label.get_pos_at(5), x_5)

    def test_get_closest_to(self) -> None:
        """Tests the get_closest_to method."""

        pos_2: int = (
            self.text_label.rects[0].x + self.renderer.render("he", True, WHITE).get_width()
        )
        turning_x: int = pos_2 + (self.renderer.render("l", True, WHITE).get_width() // 2)

        self.assertEqual(self.text_label.get_closest_to(self.text_label.rect.x), 0)
        self.assertEqual(self.text_label.get_closest_to(pos_2 - 1), 2)
        self.assertEqual(self.text_label.get_closest_to(pos_2 + 1), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_x), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_x + 1), 3)
        first_line_len: int = len(self.text_label._lines[0])
        self.assertEqual(
            self.text_label.get_closest_to(self.text_label.rect.right), first_line_len
        )
