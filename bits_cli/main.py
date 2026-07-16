from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from bits_cli.personality import line
from bits_cli.ui.tables import human_size, plate_table, projects_table, versions_table
from bits_cli.ui.theme import console
from bitscore import BitsAPI
from bitscore.exceptions import BitsError

app = typer.Typer(help="bits: versioned personal storage backed by Telegram.")


def api() -> BitsAPI:
    return BitsAPI()


def handle_error(exc: Exception) -> None:
    if isinstance(exc, BitsError):
        console.print(f"[err]{exc.message}[/err]")
        raise typer.Exit(1)
    raise exc


@app.command()
def init(overwrite: bool = typer.Option(False, "--overwrite", help="Replace an existing config file.")):
    """Create the first-run config file."""
    try:
        path = api().init_config(overwrite=overwrite)
        console.print(f"[ok]Config ready:[/ok] {path}")
    except Exception as exc:
        handle_error(exc)


@app.command()
def chew(path: Path):
    """Stage a file or folder."""
    try:
        item = api().stage(path)
        console.print(f"[accent]{line('chew')}[/accent] {item.kind} staged: {item.path}")
    except Exception as exc:
        handle_error(exc)


@app.command()
def plate():
    """Show staged items."""
    try:
        summary = api().get_plate()
        if not summary.items:
            console.print(f"[warn]{line('empty')}[/warn]")
            return
        console.print(plate_table(summary.items))
        console.print(f"Total estimated size: [accent]{human_size(summary.total_estimated_size)}[/accent]")
    except Exception as exc:
        handle_error(exc)


@app.command()
def take(item: str):
    """Remove one item from the plate by ID or full path."""
    try:
        api().unstage(item)
        console.print("[ok]Removed from plate.[/ok]")
    except Exception as exc:
        handle_error(exc)


@app.command()
def cleanplate():
    """Clear staged files without uploading."""
    api().clear_plate()
    console.print("[ok]Plate cleared.[/ok]")


@app.command()
def eat(
    project_name: Optional[str] = typer.Option(None, "--project-name", "-p", help="Required when multiple items are staged."),
    force: bool = typer.Option(False, "--force", help="Upload even if identical content already exists."),
):
    """Zip, upload, version, and index staged files."""
    try:
        record = api().upload_plate(project_name=project_name, force=force)
        console.print(f"[ok]{line('eat')}[/ok] {record.project_name} Version {record.version_number} ({record.stored_filename})")
    except Exception as exc:
        handle_error(exc)


@app.command()
def sniff(name: str):
    """Show latest metadata without downloading."""
    try:
        console.print(versions_table([api().get_latest_metadata(name)]))
    except Exception as exc:
        handle_error(exc)


@app.command()
def remember(name: str, limit: int = typer.Option(500, "--limit"), offset: int = typer.Option(0, "--offset")):
    """List all versions for a project."""
    try:
        records = api().list_versions(name, limit=limit, offset=offset)
        console.print(f"[accent]{line('remember')}[/accent]")
        console.print(versions_table(records))
    except Exception as exc:
        handle_error(exc)


@app.command()
def projects(query: Optional[str] = typer.Option(None, "--query", "-q")):
    """List known projects."""
    try:
        console.print(projects_table(api().list_projects(query=query)))
    except Exception as exc:
        handle_error(exc)


@app.command()
def vomit(
    name: str,
    version: Optional[int] = typer.Option(None, "--version", "-v"),
    dest: Optional[Path] = typer.Option(None, "--dest", "-d"),
):
    """Download a version zip."""
    try:
        path = api().download(name, version=version, dest=dest)
        console.print(f"[ok]Downloaded:[/ok] {path}")
    except Exception as exc:
        handle_error(exc)


@app.command()
def digest(
    name: str,
    version: Optional[int] = typer.Option(None, "--version", "-v"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
):
    """Delete latest or selected version."""
    try:
        if not yes and not typer.confirm(f"Delete {name} version {version or 'latest'}?"):
            raise typer.Exit()
        api().delete_version(name, version=version)
        console.print(f"[warn]{line('digest')}[/warn] Deleted.")
    except Exception as exc:
        handle_error(exc)


@app.command()
def hungry():
    """Quick local status."""
    try:
        status = api().get_quick_status()
        console.print(Panel.fit(
            f"Configured: {status.configured}\n"
            f"DB: {status.db_path}\n"
            f"Projects: {status.project_count}\n"
            f"Versions: {status.version_count}\n"
            f"Plate items: {status.plate_count}",
            title="bits status",
        ))
    except Exception as exc:
        handle_error(exc)


@app.command()
def health(check_telegram: bool = typer.Option(False, "--check-telegram", help="Make a live Telegram connection.")):
    """Run diagnostics."""
    try:
        report = api().run_diagnostics(include_telegram=check_telegram)
        console.print(Panel.fit(
            f"Python: {report.python_version}\n"
            f"Platform: {report.platform}\n"
            f"DB: {report.db_path}\n"
            f"DB integrity: {report.db_integrity}\n"
            f"Telegram: {report.telegram}\n"
            f"Download dir: {report.download_dir}\n"
            f"Projects: {report.stats.project_count}\n"
            f"Versions: {report.stats.version_count}\n"
            f"Storage: {human_size(report.stats.total_size_bytes)}\n"
            f"Ignore rules: {', '.join(report.ignore_rules)}",
            title="bits health",
        ))
    except Exception as exc:
        handle_error(exc)


@app.command()
def belly():
    """Inventory-wide statistics."""
    stats = api().get_inventory_stats()
    console.print(Panel.fit(
        f"Projects: {stats.project_count}\n"
        f"Versions: {stats.version_count}\n"
        f"Storage: {human_size(stats.total_size_bytes)}\n"
        f"Largest: {stats.largest_project or '-'}\n"
        f"Newest: {stats.newest_project or '-'}\n"
        f"Oldest: {stats.oldest_project or '-'}",
        title="Inventory",
    ))


@app.command()
def recall(verify: bool = typer.Option(False, "--verify", help="Reserved for future hash verification.")):
    """Rebuild local metadata from Telegram zip messages."""
    try:
        report = api().rebuild_index(verify=verify)
        console.print(f"[ok]Recall complete.[/ok] scanned={report.scanned} imported={report.imported} skipped={report.skipped}")
    except Exception as exc:
        handle_error(exc)


if __name__ == "__main__":
    app()
