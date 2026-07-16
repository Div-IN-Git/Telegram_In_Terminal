from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from bitscore.config import TelegramSettings
from bitscore.exceptions import ConfigError, StorageUnavailableError
from bitscore.storage.base import StoredObject


@dataclass(frozen=True)
class TelegramDocument:
    message_id: int
    chat_id: int
    filename: str
    size_bytes: int | None
    date_iso: str


class TelegramStorageAdapter:
    def __init__(self, settings: TelegramSettings) -> None:
        self.settings = settings

    def _validate(self) -> None:
        missing = []
        if not self.settings.api_id:
            missing.append("api_id")
        if not self.settings.api_hash:
            missing.append("api_hash")
        if not self.settings.chat_id:
            missing.append("chat_id")
        if missing:
            raise ConfigError("Telegram settings missing: " + ", ".join(missing))

    def _run(self, coro):
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    async def _client(self):
        self._validate()
        try:
            from telethon import TelegramClient
        except ImportError as exc:
            raise StorageUnavailableError("Telethon is not installed. Run `pip install -e .`.") from exc
        client = TelegramClient(self.settings.session_name, self.settings.api_id, self.settings.api_hash)
        await client.start()
        return client

    def upload_document(self, path: Path, stored_filename: str) -> StoredObject:
        async def inner() -> StoredObject:
            client = await self._client()
            try:
                msg = await client.send_file(self.settings.chat_id, str(path), caption=stored_filename, attributes=None, force_document=True)
                return StoredObject(msg.id, int(self.settings.chat_id), stored_filename, path.stat().st_size)
            finally:
                await client.disconnect()

        return self._run(inner())

    def download_document(self, message_id: int, destination: Path) -> Path:
        async def inner() -> Path:
            client = await self._client()
            try:
                msg = await client.get_messages(self.settings.chat_id, ids=message_id)
                if not msg:
                    raise StorageUnavailableError(f"Telegram message not found: {message_id}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                result = await msg.download_media(file=str(destination))
                return Path(result)
            finally:
                await client.disconnect()

        return self._run(inner())

    def delete_document(self, message_id: int) -> None:
        async def inner() -> None:
            client = await self._client()
            try:
                await client.delete_messages(self.settings.chat_id, [message_id])
            finally:
                await client.disconnect()

        self._run(inner())

    def iter_documents(self):
        async def inner() -> list[TelegramDocument]:
            client = await self._client()
            docs: list[TelegramDocument] = []
            try:
                async for msg in client.iter_messages(self.settings.chat_id, reverse=True):
                    if not msg.file:
                        continue
                    filename = getattr(msg.file, "name", None) or (msg.message or "").strip()
                    if not filename:
                        continue
                    docs.append(TelegramDocument(msg.id, int(self.settings.chat_id), filename, getattr(msg.file, "size", None), msg.date.isoformat()))
                return docs
            finally:
                await client.disconnect()

        return self._run(inner())

    def health(self) -> dict[str, object]:
        async def inner() -> dict[str, object]:
            client = await self._client()
            try:
                me = await client.get_me()
                return {
                    "telegram_connected": True,
                    "session_user": getattr(me, "username", None) or getattr(me, "first_name", None),
                    "chat_id": self.settings.chat_id,
                }
            finally:
                await client.disconnect()

        return self._run(inner())
