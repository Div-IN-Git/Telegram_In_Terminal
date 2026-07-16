from rich.console import Console
from rich.theme import Theme

theme = Theme(
    {
        "ok": "bold green",
        "warn": "bold yellow",
        "err": "bold red",
        "accent": "bold cyan",
        "muted": "dim",
    }
)

console = Console(theme=theme)
