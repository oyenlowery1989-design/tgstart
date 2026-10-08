import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard import ghost_process


class GhostProcessTests(unittest.TestCase):
    def test_start_passes_the_selected_absolute_session_to_the_worker(self):
        session_path = Path("/tmp/sessions/operator")
        with patch("dashboard.ghost_process.subprocess.Popen") as popen:
            popen.return_value.poll.return_value = None
            ghost_process.start_ghost_bot(session_path, "operator")

        _, kwargs = popen.call_args
        self.assertEqual(kwargs["env"]["SESSION_NAME"], str(session_path))
        self.assertEqual(ghost_process.status(), {"running": True, "session_name": "operator"})


if __name__ == "__main__":
    unittest.main()
