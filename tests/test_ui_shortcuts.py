import io
import unittest
from unittest.mock import patch


class TestUiShortcuts(unittest.TestCase):
    def test_read_line_with_shortcuts_non_tty_reads_line(self):
        from cores.v1 import core_loop as core_loop_mod

        fake_in = io.StringIO("hello\n")
        # Non-TTY path should fall back to readline() and strip trailing newline.
        with patch.object(core_loop_mod.sys, "stdin", fake_in):
            with patch.object(core_loop_mod.sys.stdin, "isatty", return_value=False):
                out = core_loop_mod._read_line_with_shortcuts("you> ")
                self.assertEqual(out, "hello")

    def test_quick_help_contains_shortcuts(self):
        from cores.v1 import core_dispatch as dispatch_mod

        qh = dispatch_mod.QUICK_HELP
        self.assertIn("Ctrl+A", qh)
        self.assertIn("Ctrl+T", qh)
        self.assertIn("Ctrl+\\", qh)


if __name__ == "__main__":
    unittest.main()
