import tempfile
import unittest
from pathlib import Path

from dashboard.worker_lock import WorkerLock


class WorkerLockTests(unittest.TestCase):
    def test_only_one_dashboard_can_own_the_worker_lease(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "workers.lock"
            first = WorkerLock(lock_path)
            second = WorkerLock(lock_path)

            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()
            self.assertTrue(second.acquire())
            second.release()


if __name__ == "__main__":
    unittest.main()
