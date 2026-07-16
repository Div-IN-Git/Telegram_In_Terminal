from __future__ import annotations

import fnmatch
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

from bitscore.archive.hashing import sha256_file


@dataclass(frozen=True)
class ZipResult:
    path: Path
    size_bytes: int
    sha256_hash: str
    files_added: int
    ignored: list[str]


def should_ignore(path: Path, patterns: list[str]) -> bool:
    parts = path.parts
    name = path.name
    for pattern in patterns:
        if name == pattern or fnmatch.fnmatch(name, pattern):
            return True
        if pattern in parts:
            return True
    return False


def estimate_size(path: Path, patterns: list[str] | None = None) -> int:
    patterns = patterns or []
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, dirs, files in os.walk(path):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if not should_ignore(root_path / d, patterns)]
        for file in files:
            file_path = root_path / file
            if not should_ignore(file_path, patterns):
                total += file_path.stat().st_size
    return total


def create_zip(items: list[Path], destination: Path, ignore_patterns: list[str]) -> ZipResult:
    destination.parent.mkdir(parents=True, exist_ok=True)
    ignored: list[str] = []
    files_added = 0
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for item in items:
            item = item.resolve()
            if item.is_file():
                if should_ignore(item, ignore_patterns):
                    ignored.append(str(item))
                    continue
                zf.write(item, arcname=item.name)
                files_added += 1
                continue
            for root, dirs, files in os.walk(item):
                root_path = Path(root)
                dirs[:] = [d for d in dirs if not should_ignore(root_path / d, ignore_patterns)]
                for dirname in set(os.listdir(root_path)) - set(dirs) - set(files):
                    candidate = root_path / dirname
                    if should_ignore(candidate, ignore_patterns):
                        ignored.append(str(candidate))
                for file in sorted(files):
                    file_path = root_path / file
                    if should_ignore(file_path, ignore_patterns):
                        ignored.append(str(file_path))
                        continue
                    arcname = Path(item.name) / file_path.relative_to(item)
                    zf.write(file_path, arcname=str(arcname))
                    files_added += 1
    return ZipResult(destination, destination.stat().st_size, sha256_file(destination), files_added, ignored)
