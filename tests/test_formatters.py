import json
import pytest
from cdkdiff.models import Change, ChangeType, DiffSummary, RiskLevel, StackDiff
from cdkdiff.formatters.json_fmt import format_json
from cdkdiff.formatters.github_fmt import format_github


def _sample_summary() -> DiffSummary:
    return DiffSummary(stacks=[
        StackDiff("MyStack", changes=[
            Change("AWS::DynamoDB::Table", "UsersTable", ChangeType.REMOVE, RiskLevel.HIGH,
                   details="Resource will be deleted"),
            Change("AWS::S3::Bucket", "NewBucket", ChangeType.ADD, RiskLevel.LOW),
        ]),
        StackDiff("OtherStack", changes=[
            Change("AWS::Lambda::Function", "Fn", ChangeType.UPDATE, RiskLevel.LOW),
        ]),
    ])


# --- JSON formatter ---

def test_json_format_structure():
    output = json.loads(format_json(_sample_summary()))
    assert "summary" in output
    assert "stacks" in output


def test_json_summary_fields():
    output = json.loads(format_json(_sample_summary()))
    summary = output["summary"]
    assert summary["total_stacks"] == 2
    assert summary["total_changes"] == 3
    assert summary["highest_risk"] == "high"


def test_json_stack_fields():
    output = json.loads(format_json(_sample_summary()))
    stack = output["stacks"][0]
    assert stack["name"] == "MyStack"
    assert stack["risk"] == "high"
    assert len(stack["changes"]) == 2


def test_json_change_fields():
    output = json.loads(format_json(_sample_summary()))
    change = output["stacks"][0]["changes"][0]
    assert change["resource_type"] == "AWS::DynamoDB::Table"
    assert change["logical_id"] == "UsersTable"
    assert change["change_type"] == "remove"
    assert change["risk"] == "high"
    assert "details" in change


def test_json_no_changes_stack():
    summary = DiffSummary(stacks=[StackDiff("EmptyStack")])
    output = json.loads(format_json(summary))
    assert output["summary"]["highest_risk"] is None
    assert output["stacks"][0]["risk"] is None


# --- GitHub markdown formatter ---

def test_github_contains_header():
    output = format_github(_sample_summary())
    assert "CDK Diff" in output


def test_github_contains_risk_indicator():
    output = format_github(_sample_summary())
    assert "HIGH" in output or "🔴" in output


def test_github_has_details_block():
    output = format_github(_sample_summary())
    assert "<details>" in output
    assert "</details>" in output


def test_github_has_hidden_marker():
    output = format_github(_sample_summary())
    assert "<!-- cdkdiff" in output


def test_github_lists_stacks():
    output = format_github(_sample_summary())
    assert "MyStack" in output
    assert "OtherStack" in output
