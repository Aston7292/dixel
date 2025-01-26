"""Tests for the file_utils file."""

from unittest import TestCase, mock
from tkinter import filedialog
from os import path
from pathlib import Path

from src.file_utils import (
    try_create_file_argv, try_create_dir_argv, handle_cmd_args, ask_save_to_file, ask_open_file
)
from src.consts import IMG_STATE_OK, IMG_STATE_MISSING


class TestFileUtils(TestCase):
    """Tests for the file_utils file."""

    # How to test get_img_state (problems with mocking portalocker)

    @mock.patch.object(Path, "touch", autospec=True)
    @mock.patch("builtins.print", autospec=True)
    def test_try_create_file_argv(self, mock_print: mock.Mock, mock_path_touch: mock.Mock) -> None:
        """Tests the try_create_file_argv function, mocks print and the Path.touch."""

        img_file_obj: Path = Path("a.png")

        self.assertTrue(try_create_file_argv(img_file_obj, ""))
        mock_print.assert_called_once()

        self.assertFalse(try_create_file_argv(img_file_obj, "--mk-file"))
        mock_path_touch.assert_called_once_with(img_file_obj)

        mock_path_touch.side_effect = PermissionError
        self.assertTrue(try_create_file_argv(img_file_obj, "--mk-file"))
        self.assertEqual(mock_print.call_count, 2)

    @mock.patch.object(Path, "mkdir", autospec=True)
    @mock.patch("builtins.print", autospec=True)
    def test_try_create_dir_argv(self, mock_print: mock.Mock, mock_path_mkdir: mock.Mock) -> None:
        """Tests the try_create_dir_argv function, mocks print and the Path.mkdir."""

        img_file_obj: Path = Path("a", "a.png")

        self.assertTrue(try_create_dir_argv(img_file_obj, ""))
        mock_print.assert_called_once()

        self.assertFalse(try_create_dir_argv(img_file_obj, "--mk-dir"))
        mock_path_mkdir.assert_called_once_with(img_file_obj.parent, parents=True)

        mock_path_mkdir.side_effect = PermissionError
        self.assertTrue(try_create_dir_argv(img_file_obj, "--mk-dir"))
        self.assertEqual(mock_print.call_count, 2)

    @mock.patch.object(path, "isreserved", autospec=True, return_value=False)
    @mock.patch("builtins.print", autospec=True)
    def test_handle_argv(self, mock_print: mock.Mock, mock_isreserved: mock.Mock) -> None:
        """Tests the handle_cmd_args function, mocks print and os.path.isreserved."""

        with self.assertRaises(SystemExit):
            handle_cmd_args(["", "help"])
        with self.assertRaises(SystemExit):
            handle_cmd_args(["", "", "a"])
        self.assertEqual(mock_print.call_count, 2)

        self.assertTupleEqual(handle_cmd_args(["", "a.jpeg"]), ("a.png", ""))
        mock_isreserved.assert_called_once_with(Path("a.png"))
        self.assertTupleEqual(handle_cmd_args(["", "a.jpeg", "--mk-file"]), ("a.png", "--mk-file"))

        mock_isreserved.return_value = True
        with self.assertRaises(SystemExit):
            handle_cmd_args(["", "a"])
        mock_print.assert_called_with("Invalid name.")

        mock_isreserved.side_effect = ValueError
        with self.assertRaises(SystemExit):
            handle_cmd_args(["", "a"])
        mock_print.assert_called_with("Invalid path.")

    @mock.patch("src.file_utils.get_img_state", autospec=True)
    @mock.patch.object(filedialog, "asksaveasfilename", autospec=True)
    def test_ask_save_to_file(
            self, mock_ask_save_as_file_name: mock.Mock, mock_get_img_state: mock.Mock
    ) -> None:
        """Test the ask_save_to_file function, mocks asksaveasfilename and get_img_state."""

        mock_ask_save_as_file_name.return_value = "a.txt"
        mock_get_img_state.return_value = IMG_STATE_OK

        self.assertEqual(ask_save_to_file(), "a.png")
        mock_ask_save_as_file_name.assert_called_once_with(
            defaultextension=".png", filetypes=[("png Files", "*.png")], title="Save As",
        )
        mock_get_img_state.assert_called_once_with("a.png", True)

        mock_ask_save_as_file_name.return_value = ""
        mock_get_img_state.return_value = IMG_STATE_MISSING
        self.assertEqual(ask_save_to_file(), "")

        mock_ask_save_as_file_name.side_effect = ("a.txt", "")
        self.assertEqual(ask_save_to_file(), "")

    @mock.patch("src.file_utils.get_img_state", autospec=True)
    @mock.patch.object(filedialog, "askopenfilename", autospec=True)
    def test_ask_open_file(
            self, mock_ask_open_file_name: mock.Mock, mock_get_img_state: mock.Mock
    ) -> None:
        """Test the ask_open_file function, mocks filedialog.askopenfilename and get_img_state."""

        mock_ask_open_file_name.return_value = "a.png"
        mock_get_img_state.return_value = IMG_STATE_OK

        self.assertEqual(ask_open_file(), "a.png")
        mock_ask_open_file_name.assert_called_once_with(
            defaultextension=".png", filetypes=[("png Files", "*.png")], title="Open",
        )
        mock_get_img_state.assert_called_once_with("a.png", False)

        mock_ask_open_file_name.return_value = ""
        mock_get_img_state.return_value = IMG_STATE_MISSING
        self.assertEqual(ask_open_file(), "")

        mock_ask_open_file_name.side_effect = ("a.txt", "")
        self.assertEqual(ask_open_file(), "")
