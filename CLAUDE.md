# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI tool that wraps `cdk diff`, parses the output, assigns risk scores (low/medium/high) to each resource change, and renders colorized terminal output, JSON, or GitHub PR comments. Installable via `pip install cdkdiff`.

## Setup

python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

## Common Commands

# Run tests
.venv/bin/pytest tests/ -v --tb=short

# Lint
.venv/bin/ruff check src/ tests/

# Type checking
.venv/bin/mypy src/

# Build distribution
python -m build

## Directory Structure

src/cdkdiff/
├── cli.py              # Click CLI entry point (cdkdiff command)
├── runner.py           # Shells out to `cdk diff` / `cdk list`
├── parser.py           # Regex-based parser for cdk diff output
├── scorer.py           # Risk scoring logic per change type
├── models.py           # Data classes: Change, StackDiff, DiffSummary, RiskLevel
├── github_client.py    # GitHub API — create/update PR comments
└── formatters/
    ├── terminal.py     # Rich-based colorized terminal output
    ├── json_fmt.py     # JSON output formatter
    └── github_fmt.py   # Markdown formatter for PR comments
tests/
├── fixtures/           # Sample cdk diff output files
└── test_*.py           # One test module per source module

## Architecture

Data flows linearly: `runner` (subprocess) → `parser` (regex) → `scorer` (risk assignment) → `formatter` (output).

**Risk scoring rules:**
- Removals and replacements → HIGH
- Updates to security groups, KMS keys, RDS, ElastiCache, ALBs → MEDIUM
- Additions and other updates → LOW

**GitHub PR comments** use a hidden HTML marker to find and update existing comments rather than creating duplicates.

## Environment Variables

| Variable | Purpose | Required |
|---|---|---|
| `GITHUB_TOKEN` | GitHub API token for posting PR comments | Only with `--post-github` |
| `GITHUB_REPOSITORY` | `owner/repo` format | Only with `--post-github` |
| `GITHUB_PR_NUMBER` | PR number (auto-derived from `GITHUB_REF` in Actions) | Only with `--post-github` |

## Testing

Tests use pytest with fixture files in `tests/fixtures/` containing sample `cdk diff` output. No external services or AWS credentials required.

    .venv/bin/pytest tests/ -v
    .venv/bin/pytest tests/ -v --cov=cdkdiff

## Code Style

Ruff with 100-char line length. Config in `pyproject.toml`.
