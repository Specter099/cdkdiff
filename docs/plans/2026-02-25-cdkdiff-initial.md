# cdkdiff Initial Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a pip-installable CLI that wraps `cdk diff`, parses output into structured Change objects, scores risk, and outputs to terminal/JSON/GitHub PR comments.

**Architecture:** Parse raw `cdk diff` text line-by-line into Change dataclasses, score each change by risk level (LOW/MEDIUM/HIGH), then render via pluggable formatters. A Click CLI wires everything together with subprocess execution of `cdk diff`.

**Tech Stack:** Python 3.9+, Click 8, Rich 13, requests 2.28, pytest

---

### Task 1: Feature Branch + Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/cdkdiff/__init__.py`
- Create: `src/cdkdiff/cli.py` (stub)
- Create: `src/cdkdiff/formatters/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/` (directory)

**Step 1: Create feature branch**

```bash
git checkout -b feature/initial-implementation
```

Expected: switched to new branch.

**Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cdkdiff"
version = "0.1.0"
description = "CDK diff with risk scoring"
requires-python = ">=3.9"
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "requests>=2.28",
]

[project.optional-dependencies]
dev = ["pytest>=7", "pytest-cov", "ruff", "mypy"]

[project.scripts]
cdkdiff = "cdkdiff.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
```

**Step 3: Create directory structure**

```bash
mkdir -p src/cdkdiff/formatters tests/fixtures
touch src/cdkdiff/__init__.py
touch src/cdkdiff/formatters/__init__.py
touch tests/__init__.py
```

**Step 4: Stub CLI so install works**

`src/cdkdiff/cli.py`:
```python
import click

@click.command()
def main():
    """CDK diff with risk scoring."""
    pass
```

**Step 5: Create venv and install**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cdkdiff --help
```

Expected output: `Usage: cdkdiff [OPTIONS]`

**Step 6: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: project scaffolding and install stub"
```

---

### Task 2: Models

**Files:**
- Create: `src/cdkdiff/models.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing tests**

`tests/test_models.py`:
```python
from cdkdiff.models import RiskLevel, ChangeType, Change, StackDiff, DiffSummary


def test_risk_level_ordering():
    assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH


def test_change_defaults():
    c = Change(
        resource_type="AWS::S3::Bucket",
        logical_id="MyBucket",
        change_type=ChangeType.ADD,
        risk=RiskLevel.LOW,
    )
    assert c.details == ""
    assert c.requires_replacement is False


def test_stack_diff_risk_empty():
    sd = StackDiff(name="MyStack")
    assert sd.risk is None


def test_stack_diff_risk_max():
    sd = StackDiff(name="MyStack", changes=[
        Change("AWS::S3::Bucket", "B", ChangeType.ADD, RiskLevel.LOW),
        Change("AWS::DynamoDB::Table", "T", ChangeType.REMOVE, RiskLevel.HIGH),
    ])
    assert sd.risk == RiskLevel.HIGH


def test_diff_summary_totals():
    summary = DiffSummary(stacks=[
        StackDiff("A", changes=[
            Change("AWS::S3::Bucket", "B", ChangeType.ADD, RiskLevel.LOW),
            Change("AWS::Lambda::Function", "F", ChangeType.UPDATE, RiskLevel.MEDIUM),
        ]),
        StackDiff("B", changes=[
            Change("AWS::DynamoDB::Table", "T", ChangeType.REMOVE, RiskLevel.HIGH),
        ]),
    ])
    assert summary.total_changes == 3
    assert summary.highest_risk == RiskLevel.HIGH
    assert len(summary.stacks) == 2
```

**Step 2: Run to verify it fails**

```bash
pytest tests/test_models.py -v
```

Expected: ImportError (models.py doesn't exist yet).

**Step 3: Implement models.py**

`src/cdkdiff/models.py`:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __lt__(self, other: RiskLevel) -> bool:
        return _RISK_ORDER.index(self) < _RISK_ORDER.index(other)

    def __le__(self, other: RiskLevel) -> bool:
        return _RISK_ORDER.index(self) <= _RISK_ORDER.index(other)

    def __gt__(self, other: RiskLevel) -> bool:
        return _RISK_ORDER.index(self) > _RISK_ORDER.index(other)

    def __ge__(self, other: RiskLevel) -> bool:
        return _RISK_ORDER.index(self) >= _RISK_ORDER.index(other)


_RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]


class ChangeType(Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


@dataclass
class Change:
    resource_type: str
    logical_id: str
    change_type: ChangeType
    risk: RiskLevel
    details: str = ""
    requires_replacement: bool = False


@dataclass
class StackDiff:
    name: str
    changes: List[Change] = field(default_factory=list)

    @property
    def risk(self) -> Optional[RiskLevel]:
        if not self.changes:
            return None
        return max((c.risk for c in self.changes), key=lambda r: _RISK_ORDER.index(r))


@dataclass
class DiffSummary:
    stacks: List[StackDiff] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return sum(len(s.changes) for s in self.stacks)

    @property
    def highest_risk(self) -> Optional[RiskLevel]:
        risks = [s.risk for s in self.stacks if s.risk is not None]
        if not risks:
            return None
        return max(risks, key=lambda r: _RISK_ORDER.index(r))
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```

Expected: 5 tests PASSED.

**Step 5: Commit**

```bash
git add src/cdkdiff/models.py tests/test_models.py
git commit -m "feat: add models (RiskLevel, ChangeType, Change, StackDiff, DiffSummary)"
```

---

### Task 3: Fixture Files

**Files:**
- Create: `tests/fixtures/no_changes.txt`
- Create: `tests/fixtures/simple_add.txt`
- Create: `tests/fixtures/mixed_changes.txt`
- Create: `tests/fixtures/replacement_changes.txt`
- Create: `tests/fixtures/multi_stack.txt`

**Step 1: Create no_changes.txt**

```
Stack MyStack
There were no differences
```

**Step 2: Create simple_add.txt**

```
Stack MyStack

Resources
[+] AWS::S3::Bucket MyBucket
[+] AWS::Lambda::Function MyFunction

✨  Number of stacks with differences: 1
```

**Step 3: Create mixed_changes.txt**

```
Stack ApiStack

IAM Statement Changes
┌───┬──────────────────────────────┬────────┬──────────────────────────────┬────────────────────────────────┬───────────────┐
│   │ Resource                     │ Effect │ Action                       │ Principal                      │ Condition     │
├───┼──────────────────────────────┼────────┼──────────────────────────────┼────────────────────────────────┼───────────────┤
│ - │ ${UsersTable/Resource}       │ Allow  │ dynamodb:DeleteItem           │ AWS:${LambdaRole}              │               │
│   │                              │        │ dynamodb:GetItem              │                                │               │
├───┼──────────────────────────────┼────────┼──────────────────────────────┼────────────────────────────────┼───────────────┤
│ + │ ${NewBucket/Resource}        │ Allow  │ s3:GetObject                 │ AWS:${LambdaRole}              │               │
└───┴──────────────────────────────┴────────┴──────────────────────────────┴────────────────────────────────┴───────────────┘

Resources
[-] AWS::DynamoDB::Table UsersTable destroy
[+] AWS::S3::Bucket NewBucket
[~] AWS::Lambda::Function ApiFunction
 └─ [~] Properties
     └─ [~] Environment
         └─ [~] Variables
             └─ [+] NEW_VAR: new-value

✨  Number of stacks with differences: 1
```

**Step 4: Create replacement_changes.txt**

```
Stack DataStack

Resources
[~] AWS::RDS::DBInstance Database replace
 ├─ [~] DBInstanceClass
 │   ├─ [-] db.t3.micro
 │   └─ [+] db.m5.large
[~] AWS::EC2::SecurityGroup WebSecurityGroup
 └─ [~] SecurityGroupIngress
     ├─ [-] {"CidrIp":"0.0.0.0/0","FromPort":443,"IpProtocol":"tcp","ToPort":443}
     └─ [+] {"CidrIp":"10.0.0.0/8","FromPort":443,"IpProtocol":"tcp","ToPort":443}

✨  Number of stacks with differences: 1
```

**Step 5: Create multi_stack.txt**

```
Stack StackOne

Resources
[+] AWS::S3::Bucket DataBucket

Stack StackTwo

Resources
[-] AWS::DynamoDB::Table OldTable destroy
[~] AWS::Lambda::Function ProcessorFn

✨  Number of stacks with differences: 2
```

**Step 6: Commit**

```bash
git add tests/fixtures/
git commit -m "test: add cdk diff output fixtures for parser tests"
```

---

### Task 4: Parser Tests + Implementation

**Files:**
- Create: `tests/test_parser.py`
- Create: `src/cdkdiff/parser.py`

**Step 1: Write the failing tests**

`tests/test_parser.py`:
```python
from pathlib import Path
import pytest
from cdkdiff.parser import parse
from cdkdiff.models import ChangeType, RiskLevel

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_parse_no_changes():
    result = parse(_fixture("no_changes.txt"))
    assert len(result.stacks) == 1
    assert result.stacks[0].name == "MyStack"
    assert result.stacks[0].changes == []


def test_parse_simple_add():
    result = parse(_fixture("simple_add.txt"))
    assert len(result.stacks) == 1
    stack = result.stacks[0]
    assert stack.name == "MyStack"
    assert len(stack.changes) == 2
    types = {c.resource_type for c in stack.changes}
    assert "AWS::S3::Bucket" in types
    assert "AWS::Lambda::Function" in types
    assert all(c.change_type == ChangeType.ADD for c in stack.changes)


def test_parse_mixed_changes():
    result = parse(_fixture("mixed_changes.txt"))
    assert len(result.stacks) == 1
    stack = result.stacks[0]
    assert stack.name == "ApiStack"

    resource_types = {c.resource_type for c in stack.changes}
    assert "AWS::DynamoDB::Table" in resource_types
    assert "AWS::S3::Bucket" in resource_types
    assert "AWS::Lambda::Function" in resource_types

    dynamo = next(c for c in stack.changes if c.resource_type == "AWS::DynamoDB::Table")
    assert dynamo.change_type == ChangeType.REMOVE

    s3 = next(c for c in stack.changes if c.resource_type == "AWS::S3::Bucket")
    assert s3.change_type == ChangeType.ADD

    lam = next(c for c in stack.changes if c.resource_type == "AWS::Lambda::Function")
    assert lam.change_type == ChangeType.UPDATE


def test_parse_iam_removals():
    result = parse(_fixture("mixed_changes.txt"))
    stack = result.stacks[0]
    iam_changes = [c for c in stack.changes if c.resource_type == "AWS::IAM::Statement"]
    assert len(iam_changes) >= 1
    removals = [c for c in iam_changes if c.change_type == ChangeType.REMOVE]
    assert len(removals) >= 1
    additions = [c for c in iam_changes if c.change_type == ChangeType.ADD]
    assert len(additions) >= 1


def test_parse_replacement():
    result = parse(_fixture("replacement_changes.txt"))
    stack = result.stacks[0]
    rds = next(c for c in stack.changes if c.resource_type == "AWS::RDS::DBInstance")
    assert rds.requires_replacement is True
    assert rds.change_type == ChangeType.UPDATE


def test_parse_security_group_update():
    result = parse(_fixture("replacement_changes.txt"))
    stack = result.stacks[0]
    sg = next(c for c in stack.changes if c.resource_type == "AWS::EC2::SecurityGroup")
    assert sg.change_type == ChangeType.UPDATE


def test_parse_multi_stack():
    result = parse(_fixture("multi_stack.txt"))
    assert len(result.stacks) == 2
    names = {s.name for s in result.stacks}
    assert names == {"StackOne", "StackTwo"}

    stack_two = next(s for s in result.stacks if s.name == "StackTwo")
    removal = next(c for c in stack_two.changes if c.change_type == ChangeType.REMOVE)
    assert removal.resource_type == "AWS::DynamoDB::Table"
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_parser.py -v
```

Expected: ImportError (parser.py doesn't exist).

**Step 3: Implement parser.py**

`src/cdkdiff/parser.py`:
```python
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
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_parser.py -v
```

Expected: 8 tests PASSED.

**Step 5: Commit**

```bash
git add src/cdkdiff/parser.py tests/test_parser.py
git commit -m "feat: add cdk diff output parser"
```

---

### Task 5: Scorer Tests + Implementation

**Files:**
- Create: `tests/test_scorer.py`
- Create: `src/cdkdiff/scorer.py`

**Step 1: Write the failing tests**

`tests/test_scorer.py`:
```python
import pytest
from cdkdiff.models import Change, ChangeType, DiffSummary, RiskLevel, StackDiff
from cdkdiff.scorer import score_change, score_summary


def _change(resource_type: str, change_type: ChangeType, requires_replacement: bool = False) -> Change:
    return Change(
        resource_type=resource_type,
        logical_id="TestResource",
        change_type=change_type,
        risk=RiskLevel.LOW,
        requires_replacement=requires_replacement,
    )


def test_removal_is_high():
    assert score_change(_change("AWS::DynamoDB::Table", ChangeType.REMOVE)) == RiskLevel.HIGH


def test_iam_statement_removal_is_high():
    assert score_change(_change("AWS::IAM::Statement", ChangeType.REMOVE)) == RiskLevel.HIGH


def test_addition_is_low():
    assert score_change(_change("AWS::S3::Bucket", ChangeType.ADD)) == RiskLevel.LOW


def test_iam_statement_addition_is_low():
    assert score_change(_change("AWS::IAM::Statement", ChangeType.ADD)) == RiskLevel.LOW


def test_replacement_is_high():
    c = _change("AWS::RDS::DBInstance", ChangeType.UPDATE, requires_replacement=True)
    assert score_change(c) == RiskLevel.HIGH


def test_security_group_update_is_medium():
    assert score_change(_change("AWS::EC2::SecurityGroup", ChangeType.UPDATE)) == RiskLevel.MEDIUM


def test_kms_key_update_is_medium():
    assert score_change(_change("AWS::KMS::Key", ChangeType.UPDATE)) == RiskLevel.MEDIUM


def test_lambda_update_is_low():
    assert score_change(_change("AWS::Lambda::Function", ChangeType.UPDATE)) == RiskLevel.LOW


def test_score_summary_sets_risk_on_changes():
    summary = DiffSummary(stacks=[
        StackDiff("MyStack", changes=[
            Change("AWS::DynamoDB::Table", "T", ChangeType.REMOVE, RiskLevel.LOW),
            Change("AWS::S3::Bucket", "B", ChangeType.ADD, RiskLevel.LOW),
        ])
    ])
    scored = score_summary(summary)
    dynamo = next(c for c in scored.stacks[0].changes if c.resource_type == "AWS::DynamoDB::Table")
    assert dynamo.risk == RiskLevel.HIGH
    s3 = next(c for c in scored.stacks[0].changes if c.resource_type == "AWS::S3::Bucket")
    assert s3.risk == RiskLevel.LOW
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_scorer.py -v
```

Expected: ImportError.

**Step 3: Implement scorer.py**

`src/cdkdiff/scorer.py`:
```python
from cdkdiff.models import Change, ChangeType, DiffSummary, RiskLevel

_MEDIUM_RISK_TYPES = {
    "AWS::EC2::SecurityGroup",
    "AWS::KMS::Key",
    "AWS::ElastiCache::ReplicationGroup",
    "AWS::RDS::DBInstance",
    "AWS::ElasticLoadBalancingV2::LoadBalancer",
}


def score_change(change: Change) -> RiskLevel:
    """Return the risk level for a single change."""
    if change.change_type == ChangeType.REMOVE:
        return RiskLevel.HIGH

    if change.change_type == ChangeType.ADD:
        return RiskLevel.LOW

    # UPDATE
    if change.requires_replacement:
        return RiskLevel.HIGH

    if change.resource_type in _MEDIUM_RISK_TYPES:
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


def score_summary(summary: DiffSummary) -> DiffSummary:
    """Mutate risk levels on all changes in-place and return the summary."""
    for stack in summary.stacks:
        for change in stack.changes:
            change.risk = score_change(change)
    return summary
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scorer.py -v
```

Expected: 9 tests PASSED.

**Step 5: Commit**

```bash
git add src/cdkdiff/scorer.py tests/test_scorer.py
git commit -m "feat: add risk scorer (LOW/MEDIUM/HIGH classification)"
```

---

### Task 6: JSON Formatter Tests + Implementation

**Files:**
- Create: `tests/test_formatters.py`
- Create: `src/cdkdiff/formatters/json_fmt.py`

**Step 1: Write the failing tests**

`tests/test_formatters.py`:
```python
import json
import pytest
from cdkdiff.models import Change, ChangeType, DiffSummary, RiskLevel, StackDiff
from cdkdiff.formatters.json_fmt import format_json
from cdkdiff.formatters.github_fmt import format_github


def _sample_summary() -> DiffSummary:
    return DiffSummary(stacks=[
        StackDiff("MyStack", changes=[
            Change("AWS::DynamoDB::Table", "UsersTable", ChangeType.REMOVE, RiskLevel.HIGH,
                   details="Resource will be deleted"),
            Change("AWS::S3::Bucket", "NewBucket", ChangeType.ADD, RiskLevel.LOW),
        ]),
        StackDiff("OtherStack", changes=[
            Change("AWS::Lambda::Function", "Fn", ChangeType.UPDATE, RiskLevel.LOW),
        ]),
    ])


# --- JSON formatter ---

def test_json_format_structure():
    output = json.loads(format_json(_sample_summary()))
    assert "summary" in output
    assert "stacks" in output


def test_json_summary_fields():
    output = json.loads(format_json(_sample_summary()))
    summary = output["summary"]
    assert summary["total_stacks"] == 2
    assert summary["total_changes"] == 3
    assert summary["highest_risk"] == "high"


def test_json_stack_fields():
    output = json.loads(format_json(_sample_summary()))
    stack = output["stacks"][0]
    assert stack["name"] == "MyStack"
    assert stack["risk"] == "high"
    assert len(stack["changes"]) == 2


def test_json_change_fields():
    output = json.loads(format_json(_sample_summary()))
    change = output["stacks"][0]["changes"][0]
    assert change["resource_type"] == "AWS::DynamoDB::Table"
    assert change["logical_id"] == "UsersTable"
    assert change["change_type"] == "remove"
    assert change["risk"] == "high"
    assert "details" in change


def test_json_no_changes_stack():
    summary = DiffSummary(stacks=[StackDiff("EmptyStack")])
    output = json.loads(format_json(summary))
    assert output["summary"]["highest_risk"] is None
    assert output["stacks"][0]["risk"] is None


# --- GitHub markdown formatter ---

def test_github_contains_header():
    output = format_github(_sample_summary())
    assert "CDK Diff" in output


def test_github_contains_risk_indicator():
    output = format_github(_sample_summary())
    assert "HIGH" in output or "🔴" in output


def test_github_has_details_block():
    output = format_github(_sample_summary())
    assert "<details>" in output
    assert "</details>" in output


def test_github_has_hidden_marker():
    output = format_github(_sample_summary())
    assert "<!-- cdkdiff" in output


def test_github_lists_stacks():
    output = format_github(_sample_summary())
    assert "MyStack" in output
    assert "OtherStack" in output
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_formatters.py -v
```

Expected: ImportErrors.

**Step 3: Implement json_fmt.py**

`src/cdkdiff/formatters/json_fmt.py`:
```python
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
```

**Step 4: Implement github_fmt.py**

`src/cdkdiff/formatters/github_fmt.py`:
```python
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
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_formatters.py -v
```

Expected: all formatter tests PASSED.

**Step 6: Commit**

```bash
git add src/cdkdiff/formatters/ tests/test_formatters.py
git commit -m "feat: add JSON and GitHub markdown formatters"
```

---

### Task 7: Terminal Formatter

**Files:**
- Create: `src/cdkdiff/formatters/terminal.py`

(Terminal formatter uses Rich — hard to assert exact output. Implement + spot-check manually.)

**Step 1: Implement terminal.py**

`src/cdkdiff/formatters/terminal.py`:
```python
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text
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
```

**Step 2: Commit**

```bash
git add src/cdkdiff/formatters/terminal.py
git commit -m "feat: add rich terminal formatter"
```

---

### Task 8: Runner Tests + Implementation

**Files:**
- Create: `tests/test_runner.py`
- Create: `src/cdkdiff/runner.py`

**Step 1: Write failing tests**

`tests/test_runner.py`:
```python
from unittest.mock import patch, MagicMock
import subprocess
import pytest
from cdkdiff.runner import run_cdk_diff, list_stacks, expand_stack_patterns


def _mock_run(stdout: str, returncode: int = 0):
    """Helper to mock subprocess.run."""
    mock = MagicMock()
    mock.stdout = stdout
    mock.stderr = ""
    mock.returncode = returncode
    return mock


def test_run_cdk_diff_returns_output():
    with patch("subprocess.run", return_value=_mock_run("Stack MyStack\nResources\n", returncode=1)):
        output = run_cdk_diff(stack_names=["MyStack"])
    assert "Stack MyStack" in output


def test_run_cdk_diff_no_stacks_diffs_all():
    with patch("subprocess.run", return_value=_mock_run("Stack A\n", returncode=0)) as mock:
        run_cdk_diff(stack_names=[])
    cmd = mock.call_args[0][0]
    assert "diff" in cmd
    # No specific stack names appended
    assert "MyStack" not in cmd


def test_run_cdk_diff_passes_stack_names():
    with patch("subprocess.run", return_value=_mock_run("", returncode=0)) as mock:
        run_cdk_diff(stack_names=["StackA", "StackB"])
    cmd = mock.call_args[0][0]
    assert "StackA" in cmd
    assert "StackB" in cmd


def test_list_stacks_returns_names():
    with patch("subprocess.run", return_value=_mock_run("StackA\nStackB\nStackC\n")):
        stacks = list_stacks()
    assert stacks == ["StackA", "StackB", "StackC"]


def test_expand_patterns_glob():
    with patch("cdkdiff.runner.list_stacks", return_value=["ApiStack", "ApiWorker", "DataStack"]):
        result = expand_stack_patterns(["Api*"])
    assert set(result) == {"ApiStack", "ApiWorker"}


def test_expand_patterns_exact():
    with patch("cdkdiff.runner.list_stacks", return_value=["ApiStack", "DataStack"]):
        result = expand_stack_patterns(["DataStack"])
    assert result == ["DataStack"]


def test_run_cdk_diff_raises_on_real_error():
    with patch("subprocess.run", side_effect=FileNotFoundError("cdk not found")):
        with pytest.raises(RuntimeError, match="cdk not found"):
            run_cdk_diff(stack_names=[])
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_runner.py -v
```

Expected: ImportError.

**Step 3: Implement runner.py**

`src/cdkdiff/runner.py`:
```python
from __future__ import annotations
import fnmatch
import subprocess
from typing import List


def run_cdk_diff(
    stack_names: List[str],
    context_path: str = ".",
) -> str:
    """Run cdk diff and return stdout. cdk exits 1 when diffs exist — that's normal."""
    cmd = ["cdk", "diff"] + stack_names
    try:
        result = subprocess.run(
            cmd,
            cwd=context_path,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"cdk not found: {e}") from e

    # cdk diff exits 1 when there are changes — not an error
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"cdk diff failed (exit {result.returncode}):\n{result.stderr}"
        )

    return result.stdout


def list_stacks(context_path: str = ".") -> List[str]:
    """Return all stack names from `cdk list`."""
    try:
        result = subprocess.run(
            ["cdk", "list"],
            cwd=context_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"cdk not found: {e}") from e
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def expand_stack_patterns(patterns: List[str], context_path: str = ".") -> List[str]:
    """Expand glob patterns against available stacks. Returns matching stack names."""
    if not any("*" in p or "?" in p for p in patterns):
        return patterns  # No globs — use as-is

    all_stacks = list_stacks(context_path)
    matched: list[str] = []
    for pattern in patterns:
        matched.extend(s for s in all_stacks if fnmatch.fnmatch(s, pattern))
    return list(dict.fromkeys(matched))  # deduplicate, preserve order
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_runner.py -v
```

Expected: 7 tests PASSED.

**Step 5: Commit**

```bash
git add src/cdkdiff/runner.py tests/test_runner.py
git commit -m "feat: add runner (cdk diff subprocess + glob stack expansion)"
```

---

### Task 9: GitHub Client Tests + Implementation

**Files:**
- Create: `src/cdkdiff/github_client.py`
- Modify: `tests/test_formatters.py` (add GitHub client tests in same file or new file)
- Create: `tests/test_github_client.py`

**Step 1: Write failing tests**

`tests/test_github_client.py`:
```python
from unittest.mock import patch, MagicMock
import pytest
from cdkdiff.github_client import post_pr_comment, find_existing_comment


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


def test_post_pr_comment_creates_new():
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value = _mock_response([])  # no existing comments
        mock_post.return_value = _mock_response({"id": 123}, status_code=201)

        post_pr_comment(
            token="fake-token",
            repo="owner/repo",
            pr_number=42,
            body="## CDK Diff\n<!-- cdkdiff-comment -->",
        )

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "issues/42/comments" in call_args[0][0]


def test_post_pr_comment_updates_existing():
    existing = [{"id": 99, "body": "<!-- cdkdiff-comment -->\nold content"}]
    with patch("requests.get") as mock_get, patch("requests.patch") as mock_patch:
        mock_get.return_value = _mock_response(existing)
        mock_patch.return_value = _mock_response({"id": 99})

        post_pr_comment(
            token="fake-token",
            repo="owner/repo",
            pr_number=42,
            body="<!-- cdkdiff-comment -->\nnew content",
        )

    mock_patch.assert_called_once()
    call_args = mock_patch.call_args
    assert "comments/99" in call_args[0][0]


def test_find_existing_comment_returns_id():
    comments = [
        {"id": 1, "body": "some other comment"},
        {"id": 2, "body": "<!-- cdkdiff-comment -->\ncontent"},
    ]
    with patch("requests.get", return_value=_mock_response(comments)):
        result = find_existing_comment("fake-token", "owner/repo", 42)
    assert result == 2


def test_find_existing_comment_returns_none():
    with patch("requests.get", return_value=_mock_response([])):
        result = find_existing_comment("fake-token", "owner/repo", 42)
    assert result is None
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_github_client.py -v
```

Expected: ImportError.

**Step 3: Implement github_client.py**

`src/cdkdiff/github_client.py`:
```python
from __future__ import annotations
import requests
from cdkdiff.formatters.github_fmt import _HIDDEN_MARKER

_API_BASE = "https://api.github.com"
_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _auth_headers(token: str) -> dict:
    return {**_HEADERS, "Authorization": f"Bearer {token}"}


def find_existing_comment(token: str, repo: str, pr_number: int) -> int | None:
    """Return the comment ID of an existing cdkdiff comment, or None."""
    url = f"{_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.get(url, headers=_auth_headers(token), params={"per_page": 100})
    resp.raise_for_status()
    for comment in resp.json():
        if _HIDDEN_MARKER in comment.get("body", ""):
            return comment["id"]
    return None


def post_pr_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    """Create or update a PR comment with the diff summary."""
    existing_id = find_existing_comment(token, repo, pr_number)
    if existing_id:
        url = f"{_API_BASE}/repos/{repo}/issues/comments/{existing_id}"
        resp = requests.patch(url, headers=_auth_headers(token), json={"body": body})
    else:
        url = f"{_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
        resp = requests.post(url, headers=_auth_headers(token), json={"body": body})
    resp.raise_for_status()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_github_client.py -v
```

Expected: 4 tests PASSED.

**Step 5: Commit**

```bash
git add src/cdkdiff/github_client.py tests/test_github_client.py
git commit -m "feat: add GitHub client (post/update PR comments)"
```

---

### Task 10: CLI Implementation

**Files:**
- Modify: `src/cdkdiff/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write failing tests**

`tests/test_cli.py`:
```python
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from cdkdiff.cli import main
from cdkdiff.models import Change, ChangeType, DiffSummary, RiskLevel, StackDiff


def _sample_diff_output():
    return "Stack MyStack\n\nResources\n[+] AWS::S3::Bucket NewBucket\n\n"


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_output_json():
    with patch("cdkdiff.cli.run_cdk_diff", return_value=_sample_diff_output()):
        runner = CliRunner()
        result = runner.invoke(main, ["--output", "json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "summary" in data
    assert "stacks" in data


def test_output_pr_comment():
    with patch("cdkdiff.cli.run_cdk_diff", return_value=_sample_diff_output()):
        runner = CliRunner()
        result = runner.invoke(main, ["--output", "pr-comment"])
    assert result.exit_code == 0
    assert "CDK Diff" in result.output
    assert "<details>" in result.output


def test_fail_on_high_exits_1_when_high_risk():
    output = "Stack MyStack\n\nResources\n[-] AWS::DynamoDB::Table T destroy\n\n"
    with patch("cdkdiff.cli.run_cdk_diff", return_value=output):
        runner = CliRunner()
        result = runner.invoke(main, ["--output", "json", "--fail-on", "high"])
    assert result.exit_code == 1


def test_fail_on_high_exits_0_when_low_risk():
    with patch("cdkdiff.cli.run_cdk_diff", return_value=_sample_diff_output()):
        runner = CliRunner()
        result = runner.invoke(main, ["--output", "json", "--fail-on", "high"])
    assert result.exit_code == 0


def test_fail_on_medium_exits_1_when_medium_risk():
    output = "Stack MyStack\n\nResources\n[~] AWS::EC2::SecurityGroup MySG\n\n"
    with patch("cdkdiff.cli.run_cdk_diff", return_value=output):
        runner = CliRunner()
        result = runner.invoke(main, ["--output", "json", "--fail-on", "medium"])
    assert result.exit_code == 1


def test_stack_name_args_passed_to_runner():
    with patch("cdkdiff.cli.run_cdk_diff", return_value="") as mock_run, \
         patch("cdkdiff.cli.expand_stack_patterns", return_value=["StackA"]):
        runner = CliRunner()
        runner.invoke(main, ["StackA"])
    mock_run.assert_called_once()
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: ImportError or test failures.

**Step 3: Implement cli.py**

`src/cdkdiff/cli.py`:
```python
from __future__ import annotations
import os
import sys
import click
from rich.console import Console
from cdkdiff.parser import parse
from cdkdiff.scorer import score_summary
from cdkdiff.runner import run_cdk_diff, expand_stack_patterns
from cdkdiff.formatters.json_fmt import format_json
from cdkdiff.formatters.github_fmt import format_github
from cdkdiff.formatters.terminal import print_summary
from cdkdiff.models import RiskLevel

_RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("stacks", nargs=-1)
@click.option("--output", "-o",
              type=click.Choice(["terminal", "json", "pr-comment"]),
              default="terminal",
              show_default=True,
              help="Output format.")
@click.option("--fail-on",
              type=click.Choice(["low", "medium", "high"]),
              default=None,
              help="Exit 1 if any change meets or exceeds this risk level.")
@click.option("--post-github", is_flag=True, default=False,
              help="Post diff as a GitHub PR comment (requires GITHUB_TOKEN).")
@click.option("--context", default=".", show_default=True,
              help="Path to CDK app directory.")
def main(stacks: tuple[str, ...], output: str, fail_on: str | None,
         post_github: bool, context: str) -> None:
    """CDK diff with risk scoring.

    Optionally pass stack names or glob patterns to diff specific stacks.
    """
    stack_list = list(stacks)
    if stack_list:
        stack_list = expand_stack_patterns(stack_list, context_path=context)

    raw = run_cdk_diff(stack_names=stack_list, context_path=context)
    summary = score_summary(parse(raw))

    if output == "json":
        click.echo(format_json(summary))
    elif output == "pr-comment":
        md = format_github(summary)
        click.echo(md)
        if post_github:
            _post_to_github(md)
    else:
        print_summary(summary, console=Console())

    if fail_on:
        threshold = RiskLevel(fail_on)
        if summary.highest_risk and summary.highest_risk >= threshold:
            sys.exit(1)


def _post_to_github(body: str) -> None:
    from cdkdiff.github_client import post_pr_comment
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = _resolve_pr_number()

    if not token:
        raise click.ClickException("GITHUB_TOKEN environment variable not set.")
    if not repo:
        raise click.ClickException("GITHUB_REPOSITORY environment variable not set.")
    if not pr_number:
        raise click.ClickException("Could not determine PR number. Set GITHUB_PR_NUMBER.")

    post_pr_comment(token=token, repo=repo, pr_number=pr_number, body=body)
    click.echo(f"Posted diff to PR #{pr_number} in {repo}", err=True)


def _resolve_pr_number() -> int | None:
    if pr := os.environ.get("GITHUB_PR_NUMBER"):
        return int(pr)
    # Derive from GITHUB_REF=refs/pull/123/merge
    ref = os.environ.get("GITHUB_REF", "")
    parts = ref.split("/")
    if len(parts) >= 3 and parts[1] == "pull":
        return int(parts[2])
    return None
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: 7 tests PASSED.

**Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASSED.

**Step 6: Commit**

```bash
git add src/cdkdiff/cli.py tests/test_cli.py
git commit -m "feat: implement CLI with Click (output formats, fail-on, post-github)"
```

---

### Task 11: CI Workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest tests/ -v --tb=short

      - name: Lint
        run: ruff check src/ tests/
```

**Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow (test on Python 3.9/3.11/3.12)"
```

---

### Task 12: End-to-End Verification

**Step 1: Verify CLI help works**

```bash
source .venv/bin/activate
cdkdiff --help
```

Expected: Full usage output with all options.

**Step 2: Run full test suite with coverage**

```bash
pytest tests/ -v --tb=short --cov=cdkdiff --cov-report=term-missing
```

Expected: All tests pass, coverage reported.

**Step 3: Smoke-test JSON output with fixture**

```python
# Quick smoke test: python -c "..."
python -c "
from cdkdiff.parser import parse
from cdkdiff.scorer import score_summary
from cdkdiff.formatters.json_fmt import format_json
from pathlib import Path
output = Path('tests/fixtures/mixed_changes.txt').read_text()
summary = score_summary(parse(output))
print(format_json(summary))
"
```

Expected: Valid JSON with stacks/changes/risk fields.

**Step 4: Smoke-test terminal output**

```python
python -c "
from cdkdiff.parser import parse
from cdkdiff.scorer import score_summary
from cdkdiff.formatters.terminal import print_summary
from pathlib import Path
output = Path('tests/fixtures/mixed_changes.txt').read_text()
print_summary(score_summary(parse(output)))
"
```

Expected: Rich colorized table in terminal.

**Step 5: Write tasks/todo.md summary**

Mark all tasks complete in tasks/todo.md.

**Step 6: Final commit + push**

```bash
git add tasks/todo.md
git commit -m "chore: mark implementation complete"
git push -u origin feature/initial-implementation
```

---

## Notes for Implementer

- **Parser edge case:** `cdk diff` can print property-level `[+]`/`[-]` lines (indented) — the regex `^` anchor ensures only top-level (unindented) resource lines are parsed.
- **IAM section end detection:** The IAM table section ends when the `Resources` header appears. The `in_iam_section` flag handles this.
- **Risk ordering:** `RiskLevel` implements `__lt__`/`__gt__` so `max()` and `>=` work naturally.
- **Scorer mutates in-place:** `score_summary` mutates `Change.risk` directly on the same objects returned by the parser — no copy needed.
- **GitHub API pagination:** The `find_existing_comment` function fetches 100 comments per page; for large PRs with 100+ comments, add pagination if needed.
