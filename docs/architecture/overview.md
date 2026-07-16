# Architecture Overview

The app is split into three layers:

- `bitscore`: backend package, containing config, SQLite repository, staging, archive, storage, sync, security, and API facade.
- `bits_cli`: Typer/Rich presentation over `BitsAPI`.
- `bits_gui`: PySide6 presentation over `BitsAPI`.

Only `bitscore.storage.telegram_adapter.TelegramStorageAdapter` talks to Telegram. Local metadata reads use SQLite, and full Telegram history scans are restricted to explicit recall.
