# cdkdiff — Specification

## Overview

`cdkdiff` is a pip-installable CLI tool that wraps `cdk diff`, parses the output into structured change objects, scores each change by risk level, and presents results in colorized terminal output, GitHub PR comments, or JSON.

## Goals

- Make CDK changes reviewable at a glance with risk scoring
- Gate CI/CD pipelines on risk thresholds
- Auto-post diff summaries as GitHub PR comments

## CLI Interface

```bash
cdkdiff                          # diff all stacks
cdkdiff MyStack OtherStack       # diff named stacks
cdkdiff "Api*"                   # glob pattern matching
cdkdiff --output terminal        # default: colorized terminal (rich)
cdkdiff --output json            # structured JSON to stdout
cdkdiff --output pr-comment      # GitHub-flavored markdown
cdkdiff --fail-on high           # exit 1 if any high-risk changes (default for CI)
cdkdiff --fail-on medium         # exit 1 if medium or higher
cdkdiff --post-github            # post pr-comment to GitHub PR via GITHUB_TOKEN
cdkdiff --context ./path/to/app  # path to CDK app (default: cwd)
```

## Risk Scoring

Each CloudFormation resource change is classified:

| Risk | Color | Examples |
|------|-------|---------|
| 🔴 HIGH | Red | Resource deletions, replacements, IAM policy removals, security group deletions |
| 🟡 MEDIUM | Yellow | Replacements causing downtime, security group changes, KMS key changes |
| 🟢 LOW | Green | Additions, tag changes, parameter updates, metadata changes |

Risk score for a stack = highest risk level of any single change in that stack.

## Output Formats

### Terminal (default)
- Uses `rich` for colorized tables
- One table per stack showing: Resource Type, Logical ID, Change Type, Risk Level
- Summary header: total stacks, total changes, highest risk level
- Badge-style risk indicators

### JSON
```json
{
  "summary": {
    "total_stacks": 2,
    "total_changes": 14,
    "highest_risk": "high"
  },
  "stacks": [
    {
      "name": "MyStack",
      "risk": "high",
      "changes": [
        {
          "resource_type": "AWS::DynamoDB::Table",
          "logical_id": "UsersTable",
          "change_type": "Remove",
          "risk": "high",
          "details": "Resource will be deleted"
        }
      ]
    }
  ]
}
```

### PR Comment (GitHub Markdown)
- Summary badge at top
- Collapsible `<details>` section per stack
- Table of changes with emoji risk indicators
- Posted via GitHub API if `--post-github` is set

## GitHub Actions Integration

When running in GitHub Actions, the tool auto-detects these environment variables:
- `GITHUB_TOKEN` — for posting PR comments
- `GITHUB_REPOSITORY` — `owner/repo` format
- `GITHUB_PR_NUMBER` — target PR to comment on (or derive from `GITHUB_REF`)

Example workflow step:
```yaml
- name: CDK Diff
  run: cdkdiff --output pr-comment --post-github --fail-on high
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Project Structure

```
cdkdiff/
├── pyproject.toml
├── README.md
├── SPEC.md
├── tasks/
│   ├── todo.md
│   └── lessons.md
├── src/
│   └── cdkdiff/
│       ├── __init__.py
│       ├── cli.py              # Click entrypoint
│       ├── runner.py           # cdk diff subprocess execution + stack discovery
│       ├── parser.py           # raw cdk diff output → structured Change objects
│       ├── scorer.py           # risk classification logic
│       ├── models.py           # dataclasses: Change, StackDiff, DiffSummary
│       ├── github_client.py    # GitHub API: post PR comment
│       └── formatters/
│           ├── __init__.py
│           ├── terminal.py     # rich colorized output
│           ├── json_fmt.py     # JSON serialization
│           └── github_fmt.py   # GitHub markdown generation
├── tests/
│   ├── fixtures/               # raw cdk diff output samples for parser tests
│   ├── test_parser.py
│   ├── test_scorer.py
│   └── test_formatters.py
└── .github/
    └── workflows/
        └── ci.yml
```

## Dependencies

```toml
[project]
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "requests>=2.28",
    "boto3>=1.26",       # optional: for AWS context/profile resolution
]

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "ruff", "mypy"]

[project.scripts]
cdkdiff = "cdkdiff.cli:main"
```

## Key Implementation Notes

### Parser
- `cdk diff` outputs human-readable text — parse it line by line
- Stack boundaries are marked by lines like `Stack MyStackName`
- Resource changes appear as lines with `[+]`, `[-]`, `[~]` prefixes
- IAM changes appear in a separate section labeled `IAM Statement Changes`
- Capture both resource-level and IAM-level changes

### Runner
- Execute `cdk diff <stack_names>` as a subprocess
- Capture stdout+stderr; `cdk diff` exits non-zero when there ARE changes (not an error)
- Support glob expansion of stack names by first listing all stacks via `cdk list`
- Pass through CDK context (profile, region, context vars) from env

### Scorer
- Classify by change type first: `[-]` Remove → HIGH, `[~]` Update → check field, `[+]` Add → LOW
- Escalate to HIGH if: IAM statement removed, security group rule removed, resource deleted
- Escalate to MEDIUM if: replacement required, security group modified, encryption changed

### GitHub Client
- POST to `/repos/{owner}/{repo}/issues/{pr}/comments`
- Check for existing cdkdiff comment (look for a hidden HTML marker) and update it instead of creating a new one to avoid comment spam

## Development Workflow

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/
cdkdiff --help
```

## Claude Code Instructions

Read this spec fully before starting. Then:
1. Write `tasks/todo.md` with a checklist of implementation steps
2. Check in on the plan before writing any code
3. Implement in this order: models → parser → scorer → formatters → cli → github_client → tests
4. Use fixture files (sample `cdk diff` outputs) to drive parser development — do not mock the parser in tests
5. Verify the CLI works end-to-end with `cdkdiff --help` and a dry-run before marking complete
6. Never commit directly to `main` — use a feature branch
