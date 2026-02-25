from cdkdiff.models import DiffSummary, RiskLevel, ChangeType

_RISK_EMOJI = {
    RiskLevel.HIGH: "🔴",
    RiskLevel.MEDIUM: "🟡",
    RiskLevel.LOW: "🟢",
}
_CHANGE_SYMBOL = {
    ChangeType.ADD: "+",
    ChangeType.REMOVE: "-",
    ChangeType.UPDATE: "~",
}
_HIDDEN_MARKER = "<!-- cdkdiff-comment -->"


def format_github(summary: DiffSummary) -> str:
    highest = summary.highest_risk
    badge = _RISK_EMOJI.get(highest, "⚪") if highest else "⚪"
    lines = [
        _HIDDEN_MARKER,
        f"## CDK Diff Summary {badge}",
        "",
        f"| Stacks | Changes | Highest Risk |",
        f"|--------|---------|--------------|",
        f"| {len(summary.stacks)} | {summary.total_changes} | "
        f"{badge} {highest.value.upper() if highest else 'NONE'} |",
        "",
    ]
    for stack in summary.stacks:
        risk = stack.risk
        stack_badge = _RISK_EMOJI.get(risk, "⚪") if risk else "⚪"
        lines.append(f"<details>")
        lines.append(f"<summary>{stack_badge} <strong>{stack.name}</strong> "
                     f"({len(stack.changes)} changes)</summary>")
        lines.append("")
        if stack.changes:
            lines.append("| Resource Type | Logical ID | Change | Risk |")
            lines.append("|---------------|------------|--------|------|")
            for c in stack.changes:
                emoji = _RISK_EMOJI[c.risk]
                symbol = _CHANGE_SYMBOL[c.change_type]
                lines.append(
                    f"| `{c.resource_type}` | `{c.logical_id}` | `{symbol}` | {emoji} {c.risk.value.upper()} |"
                )
        else:
            lines.append("_No changes_")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)
