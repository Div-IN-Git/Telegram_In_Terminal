from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from bitscore.db.migrations import init_database
from bitscore.db.models import InventoryStats, PlateItem, ProjectRecord, VersionRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Repository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @classmethod
    def open(cls, settings) -> "Repository":
        init_database(settings)
        repo = cls(settings.db_path)
        repo._seed_ignore_rules(settings.ignore_patterns)
        return repo

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _seed_ignore_rules(self, patterns: tuple[str, ...]) -> None:
        with self.connect() as conn:
            for pattern in patterns:
                conn.execute("INSERT OR IGNORE INTO ignore_rules(pattern, enabled) VALUES (?, 1)", (pattern,))

    def integrity_check(self) -> str:
        with self.connect() as conn:
            return str(conn.execute("PRAGMA integrity_check").fetchone()[0])

    def get_ignore_patterns(self) -> list[str]:
        with self.connect() as conn:
            return [r["pattern"] for r in conn.execute("SELECT pattern FROM ignore_rules WHERE enabled=1 ORDER BY pattern")]

    def add_plate_item(self, path: Path, kind: str, estimated_size: int | None) -> PlateItem:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO plate_items(path, kind, added_at, estimated_size_bytes) VALUES (?, ?, ?, ?)",
                (str(path), kind, now, estimated_size),
            )
            row = conn.execute("SELECT * FROM plate_items WHERE path=?", (str(path),)).fetchone()
        return self._plate_item(row)

    def list_plate(self) -> list[PlateItem]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM plate_items ORDER BY added_at, path").fetchall()
        return [self._plate_item(r) for r in rows]

    def remove_plate_item(self, item: str) -> int:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM plate_items WHERE path=? OR item_id=?", (item, item if item.isdigit() else -1))
            return cur.rowcount

    def clear_plate(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM plate_items")

    def get_or_create_project(self, name: str, kind: str) -> ProjectRecord:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO projects(name, kind, created_at, updated_at, is_deleted)
                VALUES (?, ?, ?, ?, 0)
                ON CONFLICT(name) DO UPDATE SET updated_at=excluded.updated_at, is_deleted=0
                """,
                (name, kind, now, now),
            )
            row = conn.execute("SELECT * FROM projects WHERE name=?", (name,)).fetchone()
        return self._project(row)

    def get_project(self, name: str) -> ProjectRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE name=? AND is_deleted=0", (name,)).fetchone()
        return self._project(row) if row else None

    def list_projects(self, query: str | None = None, limit: int = 500, offset: int = 0) -> list[ProjectRecord]:
        sql = "SELECT * FROM projects WHERE is_deleted=0"
        params: list[object] = []
        if query:
            sql += " AND name LIKE ?"
            params.append(f"%{query}%")
        sql += " ORDER BY updated_at DESC, name LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._project(r) for r in rows]

    def next_version_number(self, project_id: int) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(version_number), 0) + 1 FROM versions WHERE project_id=?", (project_id,)).fetchone()
        return int(row[0])

    def stored_filename_exists(self, name: str) -> bool:
        with self.connect() as conn:
            return conn.execute("SELECT 1 FROM versions WHERE stored_filename=?", (name,)).fetchone() is not None

    def find_hash(self, project_id: int, sha256_hash: str) -> VersionRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT v.*, p.name AS project_name FROM versions v
                JOIN projects p ON p.project_id=v.project_id
                WHERE v.project_id=? AND v.sha256_hash=? AND v.upload_status='uploaded'
                ORDER BY v.version_number DESC LIMIT 1
                """,
                (project_id, sha256_hash),
            ).fetchone()
        return self._version(row) if row else None

    def insert_pending_version(
        self,
        project_id: int,
        project_name: str,
        version_number: int,
        stored_filename: str,
        upload_date: str,
        upload_time: str,
        size_bytes: int,
        sha256_hash: str,
        source_path: str | None,
    ) -> VersionRecord:
        now = utc_now()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO versions(project_id, version_number, stored_filename, telegram_msg_id, telegram_chat_id,
                    upload_date, upload_time, size_bytes, sha256_hash, upload_status, source_path, created_at)
                VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (project_id, version_number, stored_filename, upload_date, upload_time, size_bytes, sha256_hash, source_path, now),
            )
            row = conn.execute(
                "SELECT v.*, ? AS project_name FROM versions v WHERE version_id=?",
                (project_name, cur.lastrowid),
            ).fetchone()
        return self._version(row)

    def mark_version_uploaded(self, version_id: int, msg_id: int, chat_id: int) -> VersionRecord:
        with self.connect() as conn:
            conn.execute(
                "UPDATE versions SET telegram_msg_id=?, telegram_chat_id=?, upload_status='uploaded' WHERE version_id=?",
                (msg_id, chat_id, version_id),
            )
            row = conn.execute(
                """
                SELECT v.*, p.name AS project_name FROM versions v
                JOIN projects p ON p.project_id=v.project_id
                WHERE v.version_id=?
                """,
                (version_id,),
            ).fetchone()
        return self._version(row)

    def mark_version_failed(self, version_id: int) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE versions SET upload_status='failed' WHERE version_id=?", (version_id,))

    def mark_version_deleted(self, version_id: int) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE versions SET upload_status='deleted' WHERE version_id=?", (version_id,))

    def latest_version(self, project_name: str) -> VersionRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT v.*, p.name AS project_name FROM versions v
                JOIN projects p ON p.project_id=v.project_id
                WHERE p.name=? AND v.upload_status!='deleted'
                ORDER BY v.version_number DESC LIMIT 1
                """,
                (project_name,),
            ).fetchone()
        return self._version(row) if row else None

    def get_version(self, project_name: str, version: int | None = None) -> VersionRecord | None:
        if version is None:
            return self.latest_version(project_name)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT v.*, p.name AS project_name FROM versions v
                JOIN projects p ON p.project_id=v.project_id
                WHERE p.name=? AND v.version_number=? AND v.upload_status!='deleted'
                """,
                (project_name, version),
            ).fetchone()
        return self._version(row) if row else None

    def list_versions(self, project_name: str, limit: int = 500, offset: int = 0) -> list[VersionRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT v.*, p.name AS project_name FROM versions v
                JOIN projects p ON p.project_id=v.project_id
                WHERE p.name=? AND v.upload_status!='deleted'
                ORDER BY v.version_number DESC LIMIT ? OFFSET ?
                """,
                (project_name, limit, offset),
            ).fetchall()
        return [self._version(r) for r in rows]

    def stats(self) -> InventoryStats:
        with self.connect() as conn:
            counts = conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM projects WHERE is_deleted=0) AS project_count,
                  (SELECT COUNT(*) FROM versions WHERE upload_status!='deleted') AS version_count,
                  (SELECT COALESCE(SUM(size_bytes), 0) FROM versions WHERE upload_status!='deleted') AS total_size
                """
            ).fetchone()
            largest = conn.execute(
                """
                SELECT p.name FROM projects p JOIN versions v ON v.project_id=p.project_id
                WHERE v.upload_status!='deleted' GROUP BY p.project_id ORDER BY SUM(v.size_bytes) DESC LIMIT 1
                """
            ).fetchone()
            newest = conn.execute("SELECT name FROM projects WHERE is_deleted=0 ORDER BY updated_at DESC LIMIT 1").fetchone()
            oldest = conn.execute("SELECT name FROM projects WHERE is_deleted=0 ORDER BY created_at ASC LIMIT 1").fetchone()
        return InventoryStats(
            int(counts["project_count"]),
            int(counts["version_count"]),
            int(counts["total_size"]),
            largest["name"] if largest else None,
            newest["name"] if newest else None,
            oldest["name"] if oldest else None,
        )

    def _plate_item(self, row: sqlite3.Row) -> PlateItem:
        return PlateItem(row["item_id"], row["path"], row["kind"], row["added_at"], row["estimated_size_bytes"])

    def _project(self, row: sqlite3.Row) -> ProjectRecord:
        return ProjectRecord(row["project_id"], row["name"], row["kind"], row["created_at"], row["updated_at"], bool(row["is_deleted"]))

    def _version(self, row: sqlite3.Row) -> VersionRecord:
        return VersionRecord(
            row["version_id"],
            row["project_id"],
            row["project_name"],
            row["version_number"],
            row["stored_filename"],
            row["telegram_msg_id"],
            row["telegram_chat_id"],
            row["upload_date"],
            row["upload_time"],
            row["size_bytes"],
            row["sha256_hash"],
            row["upload_status"],
            row["source_path"],
            row["created_at"],
        )
