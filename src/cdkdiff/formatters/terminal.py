from rich.console import Console
from rich.table import Table
from rich import box
from cdkdiff.models import DiffSummary, RiskLevel, ChangeType

_RISK_COLOR = {
    RiskLevel.HIGH: "red",
    RiskLevel.MEDIUM: "yellow",
    RiskLevel.LOW: "green",
}
_RISK_EMOJI = {
    RiskLevel.HIGH: "🔴",
    RiskLevel.MEDIUM: "🟡",
    RiskLevel.LOW: "🟢",
}
_CHANGE_LABEL = {
    ChangeType.ADD: "[green]+[/green]",
    ChangeType.REMOVE: "[red]-[/red]",
    ChangeType.UPDATE: "[yellow]~[/yellow]",
}


def print_summary(summary: DiffSummary, console: Console | None = None) -> None:
    if console is None:
        console = Console()

    highest = summary.highest_risk
    badge = _RISK_EMOJI.get(highest, "⚪") if highest else "⚪"
    risk_label = highest.value.upper() if highest else "NONE"
    color = _RISK_COLOR.get(highest, "white") if highest else "white"

    console.print()
    console.print(
        f"  CDK Diff  |  Stacks: [bold]{len(summary.stacks)}[/bold]  "
        f"|  Changes: [bold]{summary.total_changes}[/bold]  "
        f"|  Risk: {badge} [{color}]{risk_label}[/{color}]"
    )
    console.print()

    for stack in summary.stacks:
        stack_risk = stack.risk
        stack_color = _RISK_COLOR.get(stack_risk, "white") if stack_risk else "white"
        stack_badge = _RISK_EMOJI.get(stack_risk, "⚪") if stack_risk else "⚪"

        table = Table(
            title=f"{stack_badge} [{stack_color}]{stack.name}[/{stack_color}]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold",
        )
        table.add_column("Resource Type", style="cyan")
        table.add_column("Logical ID")
        table.add_column("Change", justify="center")
        table.add_column("Risk", justify="center")

        if not stack.changes:
            table.add_row("[dim]No changes[/dim]", "", "", "")
        else:
            for c in stack.changes:
                risk_color = _RISK_COLOR[c.risk]
                table.add_row(
                    c.resource_type,
                    c.logical_id,
                    _CHANGE_LABEL[c.change_type],
                    f"{_RISK_EMOJI[c.risk]} [{risk_color}]{c.risk.value.upper()}[/{risk_color}]",
                )

        console.print(table)
        console.print()
