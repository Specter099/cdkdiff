from cdkdiff.models import RiskLevel, ChangeType, Change, StackDiff, DiffSummary


def test_risk_level_ordering():
    assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH


def test_change_defaults():
    c = Change(
        resource_type="AWS::S3::Bucket",
        logical_id="MyBucket",
        change_type=ChangeType.ADD,
        risk=RiskLevel.LOW,
    )
    assert c.details == ""
    assert c.requires_replacement is False


def test_stack_diff_risk_empty():
    sd = StackDiff(name="MyStack")
    assert sd.risk is None


def test_stack_diff_risk_max():
    sd = StackDiff(name="MyStack", changes=[
        Change("AWS::S3::Bucket", "B", ChangeType.ADD, RiskLevel.LOW),
        Change("AWS::DynamoDB::Table", "T", ChangeType.REMOVE, RiskLevel.HIGH),
    ])
    assert sd.risk == RiskLevel.HIGH


def test_diff_summary_totals():
    summary = DiffSummary(stacks=[
        StackDiff("A", changes=[
            Change("AWS::S3::Bucket", "B", ChangeType.ADD, RiskLevel.LOW),
            Change("AWS::Lambda::Function", "F", ChangeType.UPDATE, RiskLevel.MEDIUM),
        ]),
        StackDiff("B", changes=[
            Change("AWS::DynamoDB::Table", "T", ChangeType.REMOVE, RiskLevel.HIGH),
        ]),
    ])
    assert summary.total_changes == 3
    assert summary.highest_risk == RiskLevel.HIGH
    assert len(summary.stacks) == 2
