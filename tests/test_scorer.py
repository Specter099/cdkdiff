import pytest
from cdkdiff.models import Change, ChangeType, DiffSummary, RiskLevel, StackDiff
from cdkdiff.scorer import score_change, score_summary


def _change(resource_type: str, change_type: ChangeType, requires_replacement: bool = False) -> Change:
    return Change(
        resource_type=resource_type,
        logical_id="TestResource",
        change_type=change_type,
        risk=RiskLevel.LOW,
        requires_replacement=requires_replacement,
    )


def test_removal_is_high():
    assert score_change(_change("AWS::DynamoDB::Table", ChangeType.REMOVE)) == RiskLevel.HIGH


def test_iam_statement_removal_is_high():
    assert score_change(_change("AWS::IAM::Statement", ChangeType.REMOVE)) == RiskLevel.HIGH


def test_addition_is_low():
    assert score_change(_change("AWS::S3::Bucket", ChangeType.ADD)) == RiskLevel.LOW


def test_iam_statement_addition_is_low():
    assert score_change(_change("AWS::IAM::Statement", ChangeType.ADD)) == RiskLevel.LOW


def test_replacement_is_high():
    c = _change("AWS::RDS::DBInstance", ChangeType.UPDATE, requires_replacement=True)
    assert score_change(c) == RiskLevel.HIGH


def test_security_group_update_is_medium():
    assert score_change(_change("AWS::EC2::SecurityGroup", ChangeType.UPDATE)) == RiskLevel.MEDIUM


def test_kms_key_update_is_medium():
    assert score_change(_change("AWS::KMS::Key", ChangeType.UPDATE)) == RiskLevel.MEDIUM


def test_lambda_update_is_low():
    assert score_change(_change("AWS::Lambda::Function", ChangeType.UPDATE)) == RiskLevel.LOW


def test_score_summary_sets_risk_on_changes():
    summary = DiffSummary(stacks=[
        StackDiff("MyStack", changes=[
            Change("AWS::DynamoDB::Table", "T", ChangeType.REMOVE, RiskLevel.LOW),
            Change("AWS::S3::Bucket", "B", ChangeType.ADD, RiskLevel.LOW),
        ])
    ])
    scored = score_summary(summary)
    dynamo = next(c for c in scored.stacks[0].changes if c.resource_type == "AWS::DynamoDB::Table")
    assert dynamo.risk == RiskLevel.HIGH
    s3 = next(c for c in scored.stacks[0].changes if c.resource_type == "AWS::S3::Bucket")
    assert s3.risk == RiskLevel.LOW
