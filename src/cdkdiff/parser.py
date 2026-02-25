from __future__ import annotations
import re
from cdkdiff.models import Change, ChangeType, DiffSummary, RiskLevel, StackDiff

# Matches top-level resource change lines (not indented)
_RESOURCE_RE = re.compile(
    r"^\[([+\-~])\]\s+(AWS::[^\s]+)\s+(\S+)(.*)?$"
)
# Matches IAM table rows with change indicator
_IAM_ROW_RE = re.compile(r"^\│\s+([+\-])\s+\│\s+\$\{([^}]+)\}")


def parse(output: str) -> DiffSummary:
    stacks: list[StackDiff] = []
    current_stack: StackDiff | None = None
    in_iam_section = False

    for line in output.splitlines():
        # Stack boundary
        if line.startswith("Stack ") and not line.startswith("Stack arn:"):
            stack_name = line[len("Stack "):].strip()
            current_stack = StackDiff(name=stack_name)
            stacks.append(current_stack)
            in_iam_section = False
            continue

        if current_stack is None:
            continue

        # Detect IAM section
        if "IAM Statement Changes" in line:
            in_iam_section = True
            continue

        # Detect end of IAM section (Resources header or blank then non-table content)
        if in_iam_section and line.startswith("Resources"):
            in_iam_section = False

        # Parse IAM table rows
        if in_iam_section:
            m = _IAM_ROW_RE.match(line)
            if m:
                indicator, resource_ref = m.group(1), m.group(2)
                change_type = ChangeType.ADD if indicator == "+" else ChangeType.REMOVE
                current_stack.changes.append(Change(
                    resource_type="AWS::IAM::Statement",
                    logical_id=resource_ref,
                    change_type=change_type,
                    risk=RiskLevel.LOW,  # scorer will update
                    details=f"IAM statement {'added' if indicator == '+' else 'removed'}",
                ))
            continue

        # Parse resource change lines
        m = _RESOURCE_RE.match(line)
        if m:
            indicator = m.group(1)
            resource_type = m.group(2)
            logical_id = m.group(3)
            suffix = (m.group(4) or "").strip().lower()

            if indicator == "+":
                change_type = ChangeType.ADD
            elif indicator == "-":
                change_type = ChangeType.REMOVE
            else:
                change_type = ChangeType.UPDATE

            requires_replacement = "replace" in suffix
            details = suffix if suffix else ""

            current_stack.changes.append(Change(
                resource_type=resource_type,
                logical_id=logical_id,
                change_type=change_type,
                risk=RiskLevel.LOW,  # scorer will update
                details=details,
                requires_replacement=requires_replacement,
            ))

    return DiffSummary(stacks=stacks)
