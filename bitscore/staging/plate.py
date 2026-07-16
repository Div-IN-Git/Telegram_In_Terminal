from __future__ import annotations

from pathlib import Path

from bitscore.archive.zipper import estimate_size
from bitscore.db.models import PlateItem
from bitscore.db.repository import Repository
from bitscore.exceptions import NotFoundError


class PlateManager:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def stage(self, path: Path) -> PlateItem:
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            raise NotFoundError(f"Path does not exist: {resolved}")
        kind = "folder" if resolved.is_dir() else "file"
        estimated = estimate_size(resolved, self.repo.get_ignore_patterns())
        return self.repo.add_plate_item(resolved, kind, estimated)

    def unstage(self, item: str) -> None:
        if self.repo.remove_plate_item(item) == 0:
            raise NotFoundError(f"No staged item matched: {item}")

    def list(self) -> list[PlateItem]:
        return self.repo.list_plate()

    def clear(self) -> None:
        self.repo.clear_plate()
