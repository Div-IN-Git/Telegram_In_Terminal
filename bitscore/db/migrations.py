from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from bitscore.config import Settings


def schema_sql() -> str:
    return (files("bitscore.db") / "schema.sql").read_text(encoding="utf-8")


def init_database(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    import sqlite3

    with sqlite3.connect(settings.db_path) as conn:
        conn.executescript(schema_sql())
        conn.commit()
