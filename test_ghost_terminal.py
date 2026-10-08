import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).parent / "6_messaging" / "65"))
import ghost_runner


class GhostTerminalTests(unittest.TestCase):
    def test_session_picker_returns_an_absolute_root_session_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sessions = root / "sessions"
            sessions.mkdir()
            (sessions / "operator.session").touch()
            with patch.object(ghost_runner, "PROJECT_ROOT", root), patch("builtins.input", return_value="1"):
                self.assertEqual(ghost_runner.select_session(), str(sessions / "operator"))


if __name__ == "__main__":
    unittest.main()
