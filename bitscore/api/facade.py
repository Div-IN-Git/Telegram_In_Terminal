from __future__ import annotations

import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bitscore.archive import create_zip
from bitscore.config import Settings, ensure_user_dirs, load_settings
from bitscore.constants import DATE_FORMAT, TIME_FORMAT
from bitscore.db.models import InventoryStats, PlateItem, ProjectRecord, VersionRecord
from bitscore.db.repository import Repository
from bitscore.exceptions import DuplicateUploadError, NotFoundError, PlateEmptyError
from bitscore.logging_setup import configure_logging
from bitscore.staging import PlateManager
from bitscore.storage import TelegramStorageAdapter
from bitscore.sync import RecallReport, SyncEngine


@dataclass(frozen=True)
class PlateSummary:
    items: list[PlateItem]
    total_estimated_size: int


@dataclass(frozen=True)
class StatusSummary:
    configured: bool
    db_path: Path
    project_count: int
    version_count: int
    plate_count: int


@dataclass(frozen=True)
class HealthReport:
    python_version: str
    platform: str
    db_path: Path
    db_integrity: str
    telegram: dict[str, object]
    stats: InventoryStats
    download_dir: Path
    ignore_rules: list[str]


class BitsAPI:
    def __init__(self, settings: Settings | None = None, storage=None, verbose: bool = False) -> None:
        self.settings = settings or load_settings()
        ensure_user_dirs(self.settings)
        configure_logging(self.settings.data_dir, verbose=verbose)
        self.repo = Repository.open(self.settings)
        self.plate = PlateManager(self.repo)
        self.storage = storage or TelegramStorageAdapter(self.settings.telegram)

    def stage(self, path: Path) -> PlateItem:
        return self.plate.stage(path)

    def get_plate(self) -> PlateSummary:
        items = self.plate.list()
        return PlateSummary(items, sum(i.estimated_size_bytes or 0 for i in items))

    def unstage(self, item: str) -> None:
        self.plate.unstage(item)

    def clear_plate(self) -> None:
        self.plate.clear()

    def upload_plate(self, project_name: str | None = None, force: bool = False) -> VersionRecord:
        items = self.plate.list()
        if not items:
            raise PlateEmptyError("The plate is empty. Use `bits chew <path>` first.")

        paths = [Path(i.path) for i in items]
        if project_name:
            resolved_name = project_name
        elif len(paths) == 1:
            resolved_name = paths[0].stem if paths[0].is_file() else paths[0].name
        else:
            raise PlateEmptyError("Multiple items are staged. Pass --project-name to bundle them.")

        kind = "folder" if len(paths) > 1 or paths[0].is_dir() else "file"
        now = datetime.now()
        date_part = now.strftime(DATE_FORMAT)
        time_part = now.strftime(TIME_FORMAT)
        stored_filename = self._unique_stored_filename(resolved_name, date_part, time_part)
        tmp_zip = self.settings.storage.temp_dir / stored_filename
        zip_result = create_zip(paths, tmp_zip, self.repo.get_ignore_patterns())

        project = self.repo.get_or_create_project(resolved_name, kind)
        duplicate = self.repo.find_hash(project.project_id, zip_result.sha256_hash)
        if duplicate and not force:
            tmp_zip.unlink(missing_ok=True)
            raise DuplicateUploadError(
                f"Identical content already exists as Version {duplicate.version_number}. Re-run with --force to upload anyway."
            )

        pending = self.repo.insert_pending_version(
            project.project_id,
            project.name,
            self.repo.next_version_number(project.project_id),
            stored_filename,
            date_part,
            time_part,
            zip_result.size_bytes,
            zip_result.sha256_hash,
            "; ".join(str(p) for p in paths),
        )
        try:
            stored = self.storage.upload_document(tmp_zip, stored_filename)
            uploaded = self.repo.mark_version_uploaded(pending.version_id, stored.message_id, stored.chat_id)
            self.plate.clear()
            tmp_zip.unlink(missing_ok=True)
            return uploaded
        except Exception:
            self.repo.mark_version_failed(pending.version_id)
            raise

    def download(self, name: str, version: int | None = None, dest: Path | None = None) -> Path:
        record = self.repo.get_version(name, version)
        if not record:
            raise NotFoundError(f"No version found for project: {name}")
        if record.telegram_msg_id is None:
            raise NotFoundError(f"Version {record.version_number} has no Telegram message id.")
        target_dir = (dest or self.settings.storage.download_dir).expanduser()
        if target_dir.suffix:
            target = target_dir
        else:
            target = target_dir / record.stored_filename
        return self.storage.download_document(record.telegram_msg_id, target)

    def get_latest_metadata(self, name: str) -> VersionRecord:
        record = self.repo.latest_version(name)
        if not record:
            raise NotFoundError(f"No project named {name}")
        return record

    def list_versions(self, name: str, limit: int = 500, offset: int = 0) -> list[VersionRecord]:
        records = self.repo.list_versions(name, limit=limit, offset=offset)
        if not records:
            raise NotFoundError(f"No project named {name}")
        return records

    def list_projects(self, query: str | None = None, limit: int = 500, offset: int = 0) -> list[ProjectRecord]:
        return self.repo.list_projects(query=query, limit=limit, offset=offset)

    def delete_version(self, name: str, version: int | None = None) -> None:
        record = self.repo.get_version(name, version)
        if not record:
            raise NotFoundError(f"No version found for project: {name}")
        if record.telegram_msg_id:
            self.storage.delete_document(record.telegram_msg_id)
        self.repo.mark_version_deleted(record.version_id)

    def get_quick_status(self) -> StatusSummary:
        stats = self.repo.stats()
        return StatusSummary(
            configured=bool(self.settings.telegram.api_id and self.settings.telegram.api_hash and self.settings.telegram.chat_id),
            db_path=self.settings.db_path,
            project_count=stats.project_count,
            version_count=stats.version_count,
            plate_count=len(self.repo.list_plate()),
        )

    def run_diagnostics(self, include_telegram: bool = False) -> HealthReport:
        telegram = {
            "configured": bool(self.settings.telegram.api_id and self.settings.telegram.api_hash and self.settings.telegram.chat_id),
            "checked": False,
        }
        if include_telegram:
            try:
                telegram.update(self.storage.health())
                telegram["checked"] = True
            except Exception as exc:
                telegram.update({"telegram_connected": False, "error": str(exc), "checked": True})
        return HealthReport(
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            db_path=self.settings.db_path,
            db_integrity=self.repo.integrity_check(),
            telegram=telegram,
            stats=self.repo.stats(),
            download_dir=self.settings.storage.download_dir,
            ignore_rules=self.repo.get_ignore_patterns(),
        )

    def get_inventory_stats(self) -> InventoryStats:
        return self.repo.stats()

    def rebuild_index(self, verify: bool = False) -> RecallReport:
        return SyncEngine(self.repo, self.storage).rebuild_index(verify=verify)

    def init_config(self, overwrite: bool = False) -> Path:
        cfg = self.settings.config_path
        if cfg.exists() and not overwrite:
            return cfg
        cfg.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path.cwd() / "bits.cfg.example", cfg)
        return cfg

    def _unique_stored_filename(self, project_name: str, date_part: str, time_part: str) -> str:
        safe_project = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in project_name).strip("_") or "project"
        base = f"{safe_project}_{date_part}_{time_part}"
        candidate = f"{base}.zip"
        index = 1
        while self.repo.stored_filename_exists(candidate):
            candidate = f"{base}_{index}.zip"
            index += 1
        return candidate
