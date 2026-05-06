"""
Terminal display using Rich.
Implements ResultFormatter protocol.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from everycli.core.models import SearchResult
from everycli.core.interfaces import ResultFormatter as ResultFormatterProtocol

console = Console()


class RichFormatter:
    """Renders SearchResult to the terminal using Rich."""

    def format(self, result: SearchResult) -> str:
        self._print_command(result)
        self._print_explanation(result)

        if result.has_warning:
            self._print_warning(result)

        return ""

    def format_error_hint(self, error_message: str, result: SearchResult) -> str:
        hint = result.hint_for_error(error_message)

        if hint:
            self._print_hint(hint)
        else:
            console.print(
                "\n[bold yellow]! Erreur non reconnue.[/bold yellow]"
                " Vérifie la commande et réessaie."
            )

        return ""

    # ── Private helpers ───────────────────────────────────────────────────────

    def _print_command(self, result: SearchResult) -> None:
        score_pct = int(result.score * 100)
        score_color = "green" if score_pct >= 70 else "yellow"

        title = Text()
        title.append(" Commande ", style="bold white")
        title.append(f"({score_pct}% pertinent)", style=score_color)

        panel = Panel(
            Text(result.resolved_command, style="bold cyan"),
            title=title,
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 2),
        )
        console.print()
        console.print(panel)

    def _print_explanation(self, result: SearchResult) -> None:
        console.print(
            f"  [dim](i)[/dim] {result.scenario.explanation}",
        )

    def _print_warning(self, result: SearchResult) -> None:
        console.print(
            f"  [bold yellow]![/bold yellow] {result.scenario.warning}",
        )

    def _print_hint(self, hint) -> None:
        console.print("\n[bold red][x] Erreur détectée[/bold red]")
        console.print(f"  [dim]Cause  :[/dim] {hint.cause}")
        console.print(f"  [dim]Solution :[/dim] [cyan]{hint.fix}[/cyan]")


assert isinstance(RichFormatter(), ResultFormatterProtocol), \
    "RichFormatter must implement ResultFormatterProtocol"