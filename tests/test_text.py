"""Tests for the text_label file."""

from unittest import TestCase, mock

import pygame as pg

from src.classes.text_label import TextLabel, renderers_cache

from src.utils import RectPos, resize_obj
from src.type_utils import PosPair, LayeredBlitInfo
from src.consts import WHITE, TEXT_LAYER

from tests.utils import cmp_imgs, RESIZING_RATIO


class TestTextLabel(TestCase):
    """Tests for the TextLabel class."""

    text_label: TextLabel
    renderer: pg.Font

    @classmethod
    def setUpClass(cls: type["TestTextLabel"]) -> None:
        """Creates the text and a model renderer."""

        cls.text_label = TextLabel(RectPos(1, 2, "center"), "hello\n!", 1, 30, WHITE)
        cls.renderer = pg.font.SysFont("helvetica", 30)

    def _copy_text_label(self) -> TextLabel:
        """
        Creates a copy of the text label.

        Returns:
            copy
        """

        ptr_pos: RectPos = self.text_label.init_pos
        text: str = self.text_label.text
        layer: int = self.text_label._layer - TEXT_LAYER
        h: int = self.text_label._init_h

        copy_text_label: TextLabel = TextLabel(ptr_pos, text, layer, h, self.text_label._bg_color)
        copy_text_label.resize(RESIZING_RATIO)

        return copy_text_label

    @mock.patch.object(TextLabel, "_get_rects", autospec=True)
    def test_init(self, mock_get_rects: mock.Mock) -> None:
        """Tests the init method, mocks TextLabel.get_rects."""

        text_label: TextLabel = TextLabel(RectPos(1, 2, "center"), "hello\n!", 1, 30, WHITE)

        self.assertEqual(text_label.init_pos, RectPos(1, 2, "center"))

        self.assertEqual(text_label._init_h, 30)
        self.assertIs(renderers_cache[text_label._init_h], text_label._renderer)

        self.assertEqual(text_label.text, "hello\n!")
        self.assertListEqual(text_label._lines, ["hello", "!"])
        self.assertEqual(text_label._bg_color, WHITE)

        self.assertEqual(text_label._layer, 1 + TEXT_LAYER)

        renderer: pg.Font = pg.font.SysFont("helvetica", 30)
        for img, line in zip(text_label._imgs, text_label._lines, strict=True):
            expected_img: pg.Surface = renderer.render(line, True, WHITE, WHITE).convert()
            self.assertTrue(cmp_imgs(img.convert(), expected_img, False))

        mock_get_rects.assert_called_once_with(text_label, text_label.init_pos.xy)

        transparent_bg_text_label: TextLabel = TextLabel(RectPos(0, 0, "topleft"), "hello")
        self.assertIsNone(transparent_bg_text_label._bg_color)

    def test_get_blit_sequence(self) -> None:
        """Tests the get_blit_sequence method."""

        expected_sequence: list[LayeredBlitInfo] = [
            (img, rect.topleft, self.text_label._layer)
            for img, rect in zip(self.text_label._imgs, self.text_label.rects, strict=True)
        ]

        self.assertListEqual(self.text_label.get_blit_sequence(), expected_sequence)

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._get_rects)
    def test_a_resize(self, mock_get_rects: mock.Mock) -> None:
        """Tests the resize method as first, mocks TextLabel.get_rects."""

        expected_xy: PosPair
        expected_h: int
        expected_xy, (_, expected_h) = resize_obj(
            self.text_label.init_pos, 0, self.text_label._init_h, RESIZING_RATIO, True
        )

        self.text_label.resize(RESIZING_RATIO)
        self.__class__.renderer = pg.font.SysFont("helvetica", 60)
        self.assertIs(renderers_cache[expected_h], self.text_label._renderer)

        for img, line in zip(self.text_label._imgs, self.text_label._lines, strict=True):
            expected_img: pg.Surface = self.renderer.render(line, True, WHITE, WHITE).convert()
            self.assertTrue(cmp_imgs(img.convert(), expected_img, False))
        mock_get_rects.assert_called_once_with(self.text_label, expected_xy)

    def test_get_rects(self) -> None:
        """Tests the get_rects method."""

        copy_text_label: TextLabel = self._copy_text_label()
        copy_text_label._get_rects((2, 3))

        expected_rects: list[pg.Rect] = []
        rect_w: int = max(img.get_width() for img in copy_text_label._imgs)
        rect_h: int = sum(img.get_height() for img in copy_text_label._imgs)
        expected_rect: pg.Rect = pg.Rect(0, 0, rect_w, rect_h)
        expected_rect.center = (2, 3)

        line_rect_y: int = expected_rect.y
        for img in copy_text_label._imgs:
            line_rect: pg.Rect = pg.Rect(expected_rect.x, line_rect_y, rect_w, img.get_height())
            expected_rects.append(img.get_rect(center=line_rect.center))

            line_rect_y += expected_rects[-1].h

        self.assertEqual(copy_text_label.rect, expected_rect)
        self.assertListEqual(copy_text_label.rects, expected_rects)

    def test_move_rect(self) -> None:
        """Tests the move_rect method."""

        copy_text_label: TextLabel = self._copy_text_label()

        copy_text_label.move_rect((3, 4), RESIZING_RATIO)

        expected_init_pos: RectPos = RectPos(3, 4, "center")
        self.assertEqual(copy_text_label.init_pos, expected_init_pos)

        expected_xy: PosPair
        expected_xy, _ = resize_obj(expected_init_pos, 0, 0, RESIZING_RATIO)
        self.assertTupleEqual(copy_text_label.rect.center, expected_xy)
        for rect in copy_text_label.rects:
            expected_xy, _ = resize_obj(expected_init_pos, 0, 0, RESIZING_RATIO)
            self.assertTupleEqual(rect.center, expected_xy)
            expected_init_pos.y += rect.h

    @mock.patch.object(TextLabel, "_get_rects", autospec=True, wraps=TextLabel._get_rects)
    def test_set_text(self, mock_get_rects: mock.Mock) -> None:
        """Tests the set_text method, mocks TextLabel.get_rects."""

        copy_text_label: TextLabel = self._copy_text_label()
        init_num_get_rects_calls: int = mock_get_rects.call_count

        copy_text_label.set_text("hello\n?")
        self.assertEqual(mock_get_rects.call_count, init_num_get_rects_calls + 1)

        self.assertEqual(copy_text_label.text, "hello\n?")
        self.assertListEqual(copy_text_label._lines, ["hello", "?"])
        for img, line in zip(copy_text_label._imgs, copy_text_label._lines, strict=True):
            expected_img: pg.Surface = self.renderer.render(line, True, WHITE, WHITE).convert()
            self.assertTrue(cmp_imgs(img.convert(), expected_img, False))

        mock_get_rects.assert_called_with(copy_text_label, copy_text_label.rect.center)

    def test_get_pos_at(self) -> None:
        """Tests the get_pos_at method."""

        start_x: int = self.text_label.rects[0].x

        # See if the render with antialiasing has the same width as the one without (font specific)
        x_2: int = start_x + self.renderer.render("he", True, WHITE, WHITE).get_width()
        x_5: int = start_x + self.renderer.render("hello", True, WHITE, WHITE).get_width()

        self.assertEqual(self.text_label.get_pos_at(0), start_x)
        self.assertEqual(self.text_label.get_pos_at(2), x_2)
        self.assertEqual(self.text_label.get_pos_at(5), x_5)

    def test_get_closest_to(self) -> None:
        """Tests the get_closest_to method."""

        line_rect_left: int = self.text_label.rects[0].left
        line_rect_right: int = self.text_label.rect.right
        pos_2: int = line_rect_left + self.renderer.render("he", True, WHITE, WHITE).get_width()
        turning_x: int = pos_2 + (self.renderer.render("l", True, WHITE, WHITE).get_width() // 2)
        first_line_len: int = len(self.text_label._lines[0])

        self.assertEqual(self.text_label.get_closest_to(line_rect_left - 1), 0)
        self.assertEqual(self.text_label.get_closest_to(line_rect_left), 0)
        self.assertEqual(self.text_label.get_closest_to(pos_2 - 1), 2)
        self.assertEqual(self.text_label.get_closest_to(pos_2 + 1), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_x), 2)
        self.assertEqual(self.text_label.get_closest_to(turning_x + 1), 3)
        self.assertEqual(self.text_label.get_closest_to(line_rect_right), first_line_len)
        self.assertEqual(self.text_label.get_closest_to(line_rect_right + 1), first_line_len)
