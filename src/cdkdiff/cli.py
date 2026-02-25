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
