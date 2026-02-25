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
