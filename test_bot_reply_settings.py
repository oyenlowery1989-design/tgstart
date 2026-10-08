import unittest

from fastapi import HTTPException

from dashboard.routes.bot_reply import validate_settings


class BotReplySettingsTests(unittest.TestCase):
    def test_rejects_a_session_path_outside_the_saved_sessions(self):
        with self.assertRaises(HTTPException):
            validate_settings({"session_name": "/tmp/other"}, {"main"})

    def test_rejects_unknown_provider_before_any_setting_is_written(self):
        with self.assertRaises(HTTPException):
            validate_settings({"provider": "anything-goes"}, {"main"})

    def test_normalizes_and_bounds_valid_numeric_settings(self):
        settings = validate_settings({
            "session_name": "main", "history_depth": "50", "draft_ttl_hours": "6.5",
        }, {"main"})
        self.assertEqual(settings, {
            "session_name": "main", "history_depth": "50", "draft_ttl_hours": "6.5",
        })


if __name__ == "__main__":
    unittest.main()
