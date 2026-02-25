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
