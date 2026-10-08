import json
import tempfile
import unittest
from pathlib import Path

from ghost_runner import ConfigManager, DatabaseManager


class ConfigSeedTests(unittest.TestCase):
    def test_seed_does_not_overwrite_existing_dashboard_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db = DatabaseManager(temp_path / "ghost.db")
            db.execute(
                "INSERT INTO chats (chat_id, title, backup_chat_id, monitored) VALUES (?, ?, ?, ?)",
                (1, "Dashboard title", 999, 0),
            )
            mirrors_path = temp_path / "mirrors.json"
            mirrors_path.write_text(json.dumps([{
                "chat_id": 1,
                "title": "Seed title",
                "backup_chat_id": 123,
            }]), encoding="utf-8")

            ConfigManager(db, str(mirrors_path)).load_initial_config()
            row = db.execute(
                "SELECT title, backup_chat_id, monitored FROM chats WHERE chat_id = ?", (1,),
            ).fetchone()
            db.close()

            self.assertEqual(dict(row), {
                "title": "Dashboard title", "backup_chat_id": 999, "monitored": 0,
            })


if __name__ == "__main__":
    unittest.main()
