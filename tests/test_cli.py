from click.testing import CliRunner
from unittest.mock import patch
from cdkdiff.cli import main


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
