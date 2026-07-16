from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectRecord:
    project_id: int
    name: str
    kind: str
    created_at: str
    updated_at: str
    is_deleted: bool = False


@dataclass(frozen=True)
class VersionRecord:
    version_id: int
    project_id: int
    project_name: str
    version_number: int
    stored_filename: str
    telegram_msg_id: int | None
    telegram_chat_id: int | None
    upload_date: str
    upload_time: str
    size_bytes: int
    sha256_hash: str
    upload_status: str
    source_path: str | None
    created_at: str


@dataclass(frozen=True)
class PlateItem:
    item_id: int
    path: str
    kind: str
    added_at: str
    estimated_size_bytes: int | None


@dataclass(frozen=True)
class InventoryStats:
    project_count: int
    version_count: int
    total_size_bytes: int
    largest_project: str | None
    newest_project: str | None
    oldest_project: str | None
