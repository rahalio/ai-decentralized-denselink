"""
Structured logging with Rich for beautiful terminal output
"""

from typing import Optional
import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from .config import LogLevel


class Logger:
    """Structured logger with Rich formatting"""

    def __init__(self, level: LogLevel = LogLevel.INFO, verbose: bool = False):
        self.verbose = verbose
        self.console = Console()
        self.logger = logging.getLogger("zero-codegen-merged")
        level_value = level.value.upper() if isinstance(level, LogLevel) else str(level).upper()
        self.logger.setLevel(getattr(logging, level_value))

        self.logger.handlers.clear()

        handler = RichHandler(
            console=self.console,
            show_time=verbose,
            show_path=verbose,
            rich_tracebacks=True,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
        self.logger.addHandler(handler)

    def debug(self, message: str) -> None:
        """Log debug message"""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message"""
        self.logger.info(message)

    def warn(self, message: str) -> None:
        """Log warning message"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message"""
        self.logger.error(message)

    def success(self, message: str) -> None:
        """Log success message"""
        self.console.print(f"[green]✓[/green] {message}")

    def step(self, message: str) -> None:
        """Log step message"""
        self.console.print(f"[blue]→[/blue] {message}")

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Print header panel"""
        content = f"[bold cyan]{title}[/bold cyan]"
        if subtitle:
            content += f"\n[dim]{subtitle}[/dim]"
        panel = Panel(content, border_style="cyan", padding=(1, 2))
        self.console.print(panel)

    def table(self, title: str, rows: list[dict[str, str]]) -> None:
        """Print data table"""
        if not rows:
            return
        table = Table(title=title)
        for key in rows[0].keys():
            table.add_column(key)
        for row in rows:
            table.add_row(*[str(v) for v in row.values()])
        self.console.print(table)


def create_logger(level: LogLevel = LogLevel.INFO, verbose: bool = False) -> Logger:
    """Create logger instance"""
    return Logger(level=level, verbose=verbose)
