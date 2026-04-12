# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cdkdiff is a Python CLI wrapper around `cdk diff` that adds risk scoring, colorized terminal output, JSON export, and GitHub PR comment posting. Built with Click, Rich, and requests.

## Setup

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Common Commands

```
# Run CDK diff with risk scoring (requires cdk CLI and a CDK app in current directory)
.venv/bin/cdkdiff
.venv/bin/cdkdiff MyStack
.venv/bin/cdkdiff --output json
.venv/bin/cdkdiff --output pr-comment --post-github
.venv/bin/cdkdiff --fail-on high

# Run tests
.venv/bin/pytest

# Lint
.venv/bin/ruff check .

# Type check
.venv/bin/mypy src/
```

## Directory Structure

```
src/cdkdiff/
  cli.py              # Click CLI entry point
  runner.py            # Executes `cdk diff` subprocess and captures output
  parser.py            # Parses raw cdk diff output into structured models
  scorer.py            # Assigns risk levels (low/medium/high) to changes
  models.py            # Data models (RiskLevel, StackDiff, DiffSummary)
  github_client.py     # Posts PR comments via GitHub API
  formatters/
    terminal.py        # Rich colorized terminal output
    json_fmt.py        # JSON output formatter
    github_fmt.py      # Markdown formatter for PR comments
tests/
  fixtures/            # Sample cdk diff output files for testing
  test_parser.py       # Parser tests
  test_scorer.py       # Risk scoring tests
  test_cli.py          # CLI integration tests
  test_formatters.py   # Output formatter tests
  test_runner.py       # Runner tests
  test_github_client.py # GitHub client tests
```

## Architecture

Single-command Click CLI (`cdkdiff.cli:main`, installed as `cdkdiff`). The pipeline is: run `cdk diff` subprocess -> parse output -> score risks -> format and display. Source code lives under `src/cdkdiff/` (src layout).

For GitHub PR comments, set `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, and either `GITHUB_PR_NUMBER` or `GITHUB_REF` environment variables.

## Testing

```
.venv/bin/pytest                     # Run all tests
.venv/bin/pytest tests/test_parser.py # Run specific test file
.venv/bin/pytest -x                  # Stop on first failure
```

Test fixtures in `tests/fixtures/` contain sample `cdk diff` outputs (simple_add, replacement_changes, multi_stack, etc.).

## Code Style

Ruff is configured with line-length 100.
