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
    def __init__(self, output_console: Console | None = None):
        self.console = output_console or console

    """Renders SearchResult to the terminal using Rich."""

    def format(self, result: SearchResult) -> str:
        kind = result.scenario.kind
        if kind == "command":
            self._print_command(result)
            self._print_explanation(result)
        elif kind == "tip" or kind == "reference":
            self._print_tip(result)
        elif kind == "troubleshooting":
            self._print_troubleshooting(result)

        if result.has_warning:
            self._print_warning(result)

        return ""

    def format_error_hint(self, error_message: str, result: SearchResult) -> str:
        hint = result.hint_for_error(error_message)

        if hint:
            self._print_hint(hint)
        else:
            self.console.print(
                "\n[bold yellow]! Erreur non reconnue.[/bold yellow]"
                " Vérifie la commande et réessaie."
            )

        return ""

    # ── Private helpers ───────────────────────────────────────────────────────

    def _print_command(self, result: SearchResult) -> None:
        namespace = result.scenario.namespace or (result.scenario.tags[0] if result.scenario.tags else "everycli")
        score_pct = int(result.score * 100)
        title = Text(f" {namespace} | {result.scenario.id} ", style="bold #5eead4")
        command = Text()
        command.append("> ", style="bold #5eead4")
        command.append(result.resolved_command, style="bold #5eead4")

        panel = Panel(
            command,
            title=title,
            title_align="left",
            box=box.ROUNDED,
            border_style="#2c7a70",
            padding=(0, 2),
        )
        self.console.print()
        self.console.print(panel)

    def _print_explanation(self, result: SearchResult) -> None:
        self.console.print(
            f"  [dim](i)[/dim] {result.scenario.explanation}",
        )
        self.console.print(f"  [dim]score {result.score:.2f} | {int(result.score * 100)}% relevant | namespace: {result.scenario.namespace or 'n/a'}[/dim]")

    def _print_warning(self, result: SearchResult) -> None:
        self.console.print(
            f"  [bold yellow]![/bold yellow] {result.scenario.warning}",
        )

    def _print_hint(self, hint) -> None:
        self.console.print("\n[bold red][x] Erreur détectée[/bold red]")
        self.console.print(f"  [dim]Cause  :[/dim] {hint.cause}")
        self.console.print(f"  [dim]Solution :[/dim] [cyan]{hint.fix}[/cyan]")

    def _print_tip(self, result: SearchResult) -> None:
        title = Text(f" 💡 Astuce | {result.scenario.id} ", style="bold #f59e0b")
        content = Text(result.scenario.content.strip())
        
        panel = Panel(
            content,
            title=title,
            title_align="left",
            box=box.ROUNDED,
            border_style="#d97706",
            padding=(0, 2),
        )
        self.console.print()
        self.console.print(panel)
        self.console.print(f"  [dim]score {result.score:.2f} | {int(result.score * 100)}% relevant | namespace: {result.scenario.namespace or 'n/a'}[/dim]")

    def _print_troubleshooting(self, result: SearchResult) -> None:
        title = Text(f" 🔧 Dépannage | {result.scenario.id} ", style="bold #ef4444")
        
        content = Text()
        content.append(f"{result.scenario.description}\n\n", style="bold")
        content.append("Causes probables :\n", style="bold #fca5a5")
        for cause in result.scenario.causes:
            content.append(f"  • {cause}\n")
            
        content.append("\nSolutions :\n", style="bold #86efac")
        for solution in result.scenario.solutions:
            content.append(f"  ✓ {solution}\n")
            
        panel = Panel(
            content,
            title=title,
            title_align="left",
            box=box.ROUNDED,
            border_style="#b91c1c",
            padding=(0, 2),
        )
        self.console.print()
        self.console.print(panel)
        self.console.print(f"  [dim]score {result.score:.2f} | {int(result.score * 100)}% relevant | namespace: {result.scenario.namespace or 'n/a'}[/dim]")


assert isinstance(RichFormatter(), ResultFormatterProtocol), \
    "RichFormatter must implement ResultFormatterProtocol"