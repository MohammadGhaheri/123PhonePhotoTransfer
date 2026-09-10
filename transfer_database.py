from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock


class TransferDatabase:
    def __init__(self, destination_root: str | Path) -> None:
        root = Path(destination_root)
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / ".phone_photo_transfer.sqlite3"
        self._lock = Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transfers (
                remote_path TEXT PRIMARY KEY,
                remote_size INTEGER NOT NULL,
                local_path TEXT NOT NULL,
                status TEXT NOT NULL,
                deleted_remote INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def get_completed(self, remote_path: str):
        with self._lock:
            row = self._conn.execute(
                "SELECT remote_size, local_path, deleted_remote FROM transfers WHERE remote_path=? AND status='completed'",
                (remote_path,),
            ).fetchone()
        return row

    def mark_completed(self, remote_path: str, remote_size: int, local_path: str, deleted_remote: bool) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO transfers(remote_path, remote_size, local_path, status, deleted_remote, updated_at)
                VALUES (?, ?, ?, 'completed', ?, CURRENT_TIMESTAMP)
                ON CONFLICT(remote_path) DO UPDATE SET
                    remote_size=excluded.remote_size,
                    local_path=excluded.local_path,
                    status='completed',
                    deleted_remote=excluded.deleted_remote,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (remote_path, remote_size, local_path, 1 if deleted_remote else 0),
            )
            self._conn.commit()

    def mark_error(self, remote_path: str, remote_size: int, local_path: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO transfers(remote_path, remote_size, local_path, status, deleted_remote, updated_at)
                VALUES (?, ?, ?, 'error', 0, CURRENT_TIMESTAMP)
                ON CONFLICT(remote_path) DO UPDATE SET
                    remote_size=excluded.remote_size,
                    local_path=excluded.local_path,
                    status='error',
                    updated_at=CURRENT_TIMESTAMP
                """,
                (remote_path, remote_size, local_path),
            )
            self._conn.commit()
