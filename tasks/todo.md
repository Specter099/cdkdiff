# cdkdiff Implementation Tasks

## Status: PENDING

- [ ] **Task 1:** Feature branch + project scaffolding (pyproject.toml, src/, tests/, .venv)
- [ ] **Task 2:** Models (RiskLevel, ChangeType, Change, StackDiff, DiffSummary)
- [ ] **Task 3:** Fixture files (5 sample cdk diff outputs for parser tests)
- [ ] **Task 4:** Parser (parse raw cdk diff text → DiffSummary)
- [ ] **Task 5:** Scorer (classify each Change as LOW/MEDIUM/HIGH risk)
- [ ] **Task 6:** JSON + GitHub markdown formatters
- [ ] **Task 7:** Terminal formatter (rich colorized tables)
- [ ] **Task 8:** Runner (subprocess cdk diff + glob expansion)
- [ ] **Task 9:** GitHub client (post/update PR comments)
- [ ] **Task 10:** CLI (Click entrypoint wiring everything)
- [ ] **Task 11:** CI workflow (.github/workflows/ci.yml)
- [ ] **Task 12:** End-to-end verification (all tests pass, cdkdiff --help works)

## Full Plan
See: `docs/plans/2026-02-25-cdkdiff-initial.md`

## Review
_TBD after implementation_
