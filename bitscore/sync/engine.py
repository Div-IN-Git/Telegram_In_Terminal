from __future__ import annotations

import re
from dataclasses import dataclass

from bitscore.db.repository import Repository

FILENAME_RE = re.compile(r"^(?P<project>.+)_(?P<date>\d{8})_(?P<time>\d{6})(?:_\d+)?\.zip$")


@dataclass(frozen=True)
class RecallReport:
    scanned: int
    imported: int
    skipped: int


class SyncEngine:
    def __init__(self, repo: Repository, storage) -> None:
        self.repo = repo
        self.storage = storage

    def rebuild_index(self, verify: bool = False) -> RecallReport:
        # v1 rebuild imports metadata from matching Telegram zip names. It keeps
        # the existing DB and idempotently adds missing rows instead of replacing.
        scanned = imported = skipped = 0
        for doc in self.storage.iter_documents():
            scanned += 1
            match = FILENAME_RE.match(doc.filename)
            if not match:
                skipped += 1
                continue
            project = self.repo.get_or_create_project(match.group("project"), "folder")
            version_number = self.repo.next_version_number(project.project_id)
            if self.repo.stored_filename_exists(doc.filename):
                skipped += 1
                continue
            pending = self.repo.insert_pending_version(
                project.project_id,
                project.name,
                version_number,
                doc.filename,
                match.group("date"),
                match.group("time"),
                int(doc.size_bytes or 0),
                "unverified" if not verify else "",
                None,
            )
            self.repo.mark_version_uploaded(pending.version_id, doc.message_id, doc.chat_id)
            imported += 1
        return RecallReport(scanned, imported, skipped)
