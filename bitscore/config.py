from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from bitscore.constants import DEFAULT_IGNORE_PATTERNS

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


def app_data_dir() -> Path:
    override = os.getenv("BITS_HOME")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "bits"
    return Path.home() / ".bits"


@dataclass(frozen=True)
class TelegramSettings:
    api_id: int | None
    api_hash: str
    bot_token: str
    chat_id: int | None
    session_name: str


@dataclass(frozen=True)
class StorageSettings:
    download_dir: Path
    temp_dir: Path


@dataclass(frozen=True)
class SyncSettings:
    background_interval_seconds: int = 60
    auto_recall_on_drift: bool = False


@dataclass(frozen=True)
class UISettings:
    theme: str = "dark"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    config_path: Path
    db_path: Path
    telegram: TelegramSettings
    storage: StorageSettings
    ignore_patterns: tuple[str, ...]
    sync: SyncSettings
    ui: UISettings


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser()


def load_settings(config_path: Path | None = None) -> Settings:
    data_dir = app_data_dir()
    config_file = config_path or Path(os.getenv("BITS_CONFIG", data_dir / "config.toml")).expanduser()
    raw: dict = {}
    if config_file.exists():
        raw = tomllib.loads(config_file.read_text(encoding="utf-8"))

    telegram_raw = raw.get("telegram", {})
    storage_raw = raw.get("storage", {})
    ignore_raw = raw.get("ignore", {})
    sync_raw = raw.get("sync", {})
    ui_raw = raw.get("ui", {})

    def getenv(name: str, default: str = "") -> str:
        return os.getenv(name, default)

    api_id_text = getenv("BITS_API_ID") or str(telegram_raw.get("api_id") or os.getenv("API_ID") or "")
    api_id = int(api_id_text) if api_id_text.strip() else None
    chat_id_text = getenv("BITS_CHAT_ID") or str(telegram_raw.get("chat_id") or os.getenv("CHAT_ID") or "")
    chat_id = int(chat_id_text) if chat_id_text.strip() and chat_id_text.strip() != "0" else None

    download_dir = _expand(storage_raw.get("download_dir", "~/Downloads"))
    temp_dir = _expand(storage_raw.get("temp_dir", data_dir / "tmp"))

    return Settings(
        data_dir=data_dir,
        config_path=config_file,
        db_path=data_dir / "inventory.db",
        telegram=TelegramSettings(
            api_id=api_id,
            api_hash=getenv("BITS_API_HASH") or str(telegram_raw.get("api_hash") or os.getenv("API_HASH") or ""),
            bot_token=getenv("BITS_BOT_TOKEN") or str(telegram_raw.get("bot_token") or os.getenv("BOT_TOKEN") or ""),
            chat_id=chat_id,
            session_name=str(telegram_raw.get("session_name") or os.getenv("SESSION_NAME") or "bits"),
        ),
        storage=StorageSettings(download_dir=download_dir, temp_dir=temp_dir),
        ignore_patterns=tuple(ignore_raw.get("patterns", DEFAULT_IGNORE_PATTERNS)),
        sync=SyncSettings(
            background_interval_seconds=int(sync_raw.get("background_interval_seconds", 60)),
            auto_recall_on_drift=bool(sync_raw.get("auto_recall_on_drift", False)),
        ),
        ui=UISettings(theme=str(ui_raw.get("theme", "dark"))),
    )


def ensure_user_dirs(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.storage.temp_dir.mkdir(parents=True, exist_ok=True)
    settings.storage.download_dir.mkdir(parents=True, exist_ok=True)
