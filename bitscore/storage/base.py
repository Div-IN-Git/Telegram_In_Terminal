from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    message_id: int
    chat_id: int
    filename: str
    size_bytes: int | None = None


class StorageAdapter(Protocol):
    def upload_document(self, path: Path, stored_filename: str) -> StoredObject:
        ...

    def download_document(self, message_id: int, destination: Path) -> Path:
        ...

    def delete_document(self, message_id: int) -> None:
        ...

    def iter_documents(self):
        ...

    def health(self) -> dict[str, object]:
        ...
