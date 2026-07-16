from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


SECRET_RE = re.compile(r"(\d{8,}:[A-Za-z0-9_-]{20,}|[a-f0-9]{32,}|api_hash\s*=\s*['\"][^'\"]+)", re.I)


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = SECRET_RE.sub("[REDACTED]", str(record.msg))
        if record.args:
            record.args = tuple(SECRET_RE.sub("[REDACTED]", str(arg)) for arg in record.args)
        return True


def configure_logging(data_dir: Path, verbose: bool = False) -> None:
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("bits")
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    if root.handlers:
        return
    handler = RotatingFileHandler(log_dir / "bits.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactionFilter())
    root.addHandler(handler)
