"""Tests for the text_label file."""

from unittest import TestCase, mock
from unittest.mock import Mock

import pygame as pg

from src.classes.text_label import TextLabel, _RENDERERS_CACHE

from src.utils import RectPos, resize_obj
from src.type_utils import XY, WH, BlitInfo
from src.consts import WHITE, TEXT_LAYER

from tests.utils import cmp_imgs


class TestTextLabel(TestCase):
    """Tests for the TextLabel class."""

    def _make_text_label(self) -> TextLabel:
        """
        Creates a text label.

        Returns:
            text label
        """

        text_label: TextLabel = TextLabel(RectPos(1, 2, "center"), "hello\n!", 1, 20, WHITE)
        text_label.resize(2, 3)

        return text_label

    @mock.patch.object(TextLabel, "_refresh_rects", autospec=True)
    def test_init(self, mock_refresh_rects: Mock) -> None:
        """Tests the init method, mocks TextLabel.refresh_rects."""

        img: pg.Surface
        line: str

        text_label: TextLabel = TextLabel(RectPos(1, 2, "center"), "hello\n!", 1, 20, WHITE)
        expected_renderer: pg.Font = _RENDERERS_CACHE[text_label._init_h]

        self.assertEqual(text_label.init_pos, RectPos(1, 2, "center"))

        self.assertEqual(text_label._init_h, 20)
        self.assertIs(expected_renderer, text_label._renderer)

        self.assertEqual(text_label.text, "hello\n!")
        self.assertEqual(text_label._bg_color, WHITE)

        self.assertEqual(text_label.layer, 1 + TEXT_LAYER)

        lines: list[str] = text_label.text.split("\n")
        for img, line in zip(text_label.imgs, lines, strict=True):
            expected_img: pg.Surface = expected_renderer.render(
                line, True, WHITE, WHITE
            ).convert_alpha()
            self.assertTrue(cmp_imgs(img, expected_img))

        mock_refresh_rects.assert_called_once_with(
            text_label, (text_label.init_pos.x, text_label.init_pos.y)
        )

        transparent_bg_text_label: TextLabel = TextLabel(RectPos(0, 0, "topleft"), "hello")
        self.assertIsNone(transparent_bg_text_label._bg_color)

    def test_blit_sequence(self) -> None:
        """Tests the blit_sequence property."""

        text_label: TextLabel = self._make_text_label()

        expected_sequence: list[BlitInfo] = [
            (img, rect, text_label.layer)
            for img, rect in zip(text_label.imgs, text_label._rects, strict=True)
        ]

        self.assertListEqual(text_label.blit_sequence, expected_sequence)

    @mock.patch.object(TextLabel, "_refresh_rects", autospec=True, wraps=TextLabel._refresh_rects)
    def test_resize(self, mock_refresh_rects: Mock) -> None:
        """Tests the resize method, mocks TextLabel.refresh_rects."""

        expected_xy: XY
        _expected_w: int
        expected_h: int
        img: pg.Surface
        line: str

        text_label: TextLabel = TextLabel(RectPos(1, 2, "center"), "hello\n!", 1, 20, WHITE)
        init_num_get_rects_calls: int = mock_refresh_rects.call_count

        text_label.resize(2, 3)

        expected_xy, (_expected_w, expected_h) = resize_obj(
            text_label.init_pos, 0, text_label._init_h, 2, 3, True
        )

        expected_renderer: pg.Font = _RENDERERS_CACHE[expected_h]
        self.assertIs(text_label._renderer, expected_renderer)

        lines: list[str] = text_label.text.split("\n")
        for img, line in zip(text_label.imgs, lines, strict=True):
            expected_img: pg.Surface = expected_renderer.render(
                line, True, WHITE, WHITE
            ).convert_alpha()
            self.assertTrue(cmp_imgs(img, expected_img))

        self.assertEqual(mock_refresh_rects.call_count, init_num_get_rects_calls + 1)
        mock_refresh_rects.assert_called_with(text_label, expected_xy)

    def test_refresh_rects(self) -> None:
        """Tests the refresh_rects method."""

        expected_line_rect_x: int
        expected_line_rect_y: int
        img: pg.Surface

        text_label: TextLabel = self._make_text_label()
        text_label._refresh_rects((2, 3))

        expected_rect: pg.Rect = pg.Rect()
        expected_rect.size = (
            max([img.get_width() for img in text_label.imgs]),
            sum([img.get_height() for img in text_label.imgs])
        )
        expected_rect.center = (2, 3)

        expected_rects: list[pg.Rect] = []
        expected_line_rect_x, expected_line_rect_y = expected_rect.topleft
        for img in text_label.imgs:
            expected_line_rect: pg.Rect = pg.Rect(
                expected_line_rect_x, expected_line_rect_y, expected_rect.w, img.get_height()
            )
            expected_line_center: XY = expected_line_rect.center

            expected_line_rect.w = img.get_width()
            expected_line_rect.center = expected_line_center
            expected_rects.append(expected_line_rect)

            expected_line_rect_y += expected_line_rect.h

        self.assertEqual(text_label.rect, expected_rect)
        self.assertListEqual(text_label._rects, expected_rects)

    def test_move_rect(self) -> None:
        """Tests the move_rect method."""

        expected_xy: XY
        _expected_wh: WH
        rect: pg.Rect

        text_label: TextLabel = self._make_text_label()
        text_label.move_rect(3, 4, 2, 3)

        expected_line_init_pos: RectPos = RectPos(3, 4, "center")
        self.assertEqual(text_label.init_pos, expected_line_init_pos)

        expected_xy, _expected_wh = resize_obj(expected_line_init_pos, 0, 0, 2, 3)
        self.assertTupleEqual(text_label.rect.center, expected_xy)
        for rect in text_label._rects:
            expected_xy, _expected_wh = resize_obj(expected_line_init_pos, 0, 0, 2, 3)
            self.assertTupleEqual(rect.center, expected_xy)
            expected_line_init_pos.y += rect.h

    @mock.patch.object(TextLabel, "_refresh_rects", autospec=True, wraps=TextLabel._refresh_rects)
    def test_set_text(self, mock_refresh_rects: Mock) -> None:
        """Tests the set_text method, mocks TextLabel.refresh_rects."""

        img: pg.Surface
        line: str

        text_label: TextLabel = self._make_text_label()
        init_num_get_rects_calls: int = mock_refresh_rects.call_count

        text_label.set_text("hello\n?")
        self.assertEqual(text_label.text, "hello\n?")
        self.assertEqual(mock_refresh_rects.call_count, init_num_get_rects_calls + 1)

        lines: list[str] = text_label.text.split("\n")
        expected_renderer: pg.Font = pg.font.SysFont("helvetica", 60)
        for img, line in zip(text_label.imgs, lines, strict=True):
            expected_img: pg.Surface = expected_renderer.render(
                line, True, WHITE, WHITE
            ).convert_alpha()
            self.assertTrue(cmp_imgs(img, expected_img))

        mock_refresh_rects.assert_called_with(text_label, text_label.rect.center)

    def test_get_pos_at(self) -> None:
        """Tests the get_pos_at method."""

        x_2: int
        x_5: int

        text_label: TextLabel = self._make_text_label()
        expected_renderer: pg.Font = pg.font.SysFont("helvetica", 60)

        # See if the render with antialiasing has the same width as the one without (font specific)
        x_2 = text_label.rect.x + expected_renderer.render("he", True, WHITE, WHITE).get_width()
        x_5 = text_label.rect.x + expected_renderer.render("hello", True, WHITE, WHITE).get_width()

        self.assertEqual(text_label.get_x_at(0), text_label.rect.x)
        self.assertEqual(text_label.get_x_at(2), x_2)
        self.assertEqual(text_label.get_x_at(5), x_5)

    def test_get_closest_to(self) -> None:
        """Tests the get_closest_to method."""

        rect_left: int
        rect_right: int

        text_label: TextLabel = self._make_text_label()
        expected_renderer: pg.Font = pg.font.SysFont("helvetica", 60)

        rect_left, rect_right = text_label.rect.x, text_label.rect.right
        pos_2: int = rect_left + expected_renderer.render("he", True, WHITE, WHITE).get_width()
        turning_x: int = pos_2 + expected_renderer.render("l", True, WHITE, WHITE).get_width() // 2
        first_line: str = text_label.text.split("\n")[0]

        self.assertEqual(text_label.get_closest_to(rect_left - 1), 0)
        self.assertEqual(text_label.get_closest_to(rect_left), 0)
        self.assertEqual(text_label.get_closest_to(pos_2 - 1), 2)
        self.assertEqual(text_label.get_closest_to(pos_2 + 1), 2)
        self.assertEqual(text_label.get_closest_to(turning_x), 2)
        self.assertEqual(text_label.get_closest_to(turning_x + 1), 3)
        self.assertEqual(text_label.get_closest_to(rect_right), len(first_line))
        self.assertEqual(text_label.get_closest_to(rect_right + 1), len(first_line))
