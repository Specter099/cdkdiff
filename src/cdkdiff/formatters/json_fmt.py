import json
from cdkdiff.models import DiffSummary


def format_json(summary: DiffSummary) -> str:
    highest = summary.highest_risk
    data = {
        "summary": {
            "total_stacks": len(summary.stacks),
            "total_changes": summary.total_changes,
            "highest_risk": highest.value if highest else None,
        },
        "stacks": [
            {
                "name": stack.name,
                "risk": stack.risk.value if stack.risk else None,
                "changes": [
                    {
                        "resource_type": c.resource_type,
                        "logical_id": c.logical_id,
                        "change_type": c.change_type.value,
                        "risk": c.risk.value,
                        "details": c.details,
                    }
                    for c in stack.changes
                ],
            }
            for stack in summary.stacks
        ],
    }
    return json.dumps(data, indent=2)
