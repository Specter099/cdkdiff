from __future__ import annotations
import fnmatch
import subprocess

_SUBPROCESS_TIMEOUT = 300  # seconds


def run_cdk_diff(
    stack_names: list[str],
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
            timeout=_SUBPROCESS_TIMEOUT,
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"cdk not found: {e}") from e

    # cdk diff exits 1 when there are changes — not an error
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"cdk diff failed (exit {result.returncode}):\n{result.stderr}"
        )

    return result.stdout


def list_stacks(context_path: str = ".") -> list[str]:
    """Return all stack names from `cdk list`."""
    try:
        result = subprocess.run(
            ["cdk", "list"],
            cwd=context_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"cdk not found: {e}") from e
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def expand_stack_patterns(patterns: list[str], context_path: str = ".") -> list[str]:
    """Expand glob patterns against available stacks. Returns matching stack names."""
    if not any("*" in p or "?" in p for p in patterns):
        return patterns  # No globs — use as-is

    all_stacks = list_stacks(context_path)
    matched: list[str] = []
    for pattern in patterns:
        matched.extend(s for s in all_stacks if fnmatch.fnmatch(s, pattern))
    return list(dict.fromkeys(matched))  # deduplicate, preserve order
