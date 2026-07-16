from __future__ import annotations

from rich.table import Table


def human_size(size: int | None) -> str:
    if size is None:
        return "-"
    value = float(size)
    for suffix in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or suffix == "TB":
            return f"{value:.1f} {suffix}" if suffix != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def plate_table(items) -> Table:
    table = Table(title="Plate")
    table.add_column("ID", justify="right")
    table.add_column("Kind")
    table.add_column("Estimated")
    table.add_column("Path")
    for item in items:
        table.add_row(str(item.item_id), item.kind, human_size(item.estimated_size_bytes), item.path)
    return table


def versions_table(records) -> Table:
    table = Table(title="Versions")
    table.add_column("Version", justify="right")
    table.add_column("Project")
    table.add_column("Date")
    table.add_column("Time")
    table.add_column("Size")
    table.add_column("Status")
    table.add_column("Hash")
    for r in records:
        table.add_row(
            str(r.version_number),
            r.project_name,
            r.upload_date,
            r.upload_time,
            human_size(r.size_bytes),
            r.upload_status,
            r.sha256_hash[:12],
        )
    return table


def projects_table(projects) -> Table:
    table = Table(title="Projects")
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Kind")
    table.add_column("Updated")
    for p in projects:
        table.add_row(str(p.project_id), p.name, p.kind, p.updated_at)
    return table
