"""Cross-process lease for dashboard-managed Telegram workers."""
import os
from pathlib import Path


class WorkerLock:
    def __init__(self, path: Path):
        self.path = path
        self.acquired = False

    @staticmethod
    def _pid_is_running(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                try:
                    pid = int(self.path.read_text(encoding="utf-8").strip())
                except (OSError, ValueError):
                    pid = 0
                if pid and self._pid_is_running(pid):
                    return False
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
                lock_file.write(str(os.getpid()))
            self.acquired = True
            return True
        return False

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            if self.path.read_text(encoding="utf-8").strip() == str(os.getpid()):
                self.path.unlink()
        except FileNotFoundError:
            pass
        self.acquired = False
