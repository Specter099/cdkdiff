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
