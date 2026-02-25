from pathlib import Path
import pytest
from cdkdiff.parser import parse
from cdkdiff.models import ChangeType, RiskLevel

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_parse_no_changes():
    result = parse(_fixture("no_changes.txt"))
    assert len(result.stacks) == 1
    assert result.stacks[0].name == "MyStack"
    assert result.stacks[0].changes == []


def test_parse_simple_add():
    result = parse(_fixture("simple_add.txt"))
    assert len(result.stacks) == 1
    stack = result.stacks[0]
    assert stack.name == "MyStack"
    assert len(stack.changes) == 2
    types = {c.resource_type for c in stack.changes}
    assert "AWS::S3::Bucket" in types
    assert "AWS::Lambda::Function" in types
    assert all(c.change_type == ChangeType.ADD for c in stack.changes)


def test_parse_mixed_changes():
    result = parse(_fixture("mixed_changes.txt"))
    assert len(result.stacks) == 1
    stack = result.stacks[0]
    assert stack.name == "ApiStack"

    resource_types = {c.resource_type for c in stack.changes}
    assert "AWS::DynamoDB::Table" in resource_types
    assert "AWS::S3::Bucket" in resource_types
    assert "AWS::Lambda::Function" in resource_types

    dynamo = next(c for c in stack.changes if c.resource_type == "AWS::DynamoDB::Table")
    assert dynamo.change_type == ChangeType.REMOVE

    s3 = next(c for c in stack.changes if c.resource_type == "AWS::S3::Bucket")
    assert s3.change_type == ChangeType.ADD

    lam = next(c for c in stack.changes if c.resource_type == "AWS::Lambda::Function")
    assert lam.change_type == ChangeType.UPDATE


def test_parse_iam_removals():
    result = parse(_fixture("mixed_changes.txt"))
    stack = result.stacks[0]
    iam_changes = [c for c in stack.changes if c.resource_type == "AWS::IAM::Statement"]
    assert len(iam_changes) >= 1
    removals = [c for c in iam_changes if c.change_type == ChangeType.REMOVE]
    assert len(removals) >= 1
    additions = [c for c in iam_changes if c.change_type == ChangeType.ADD]
    assert len(additions) >= 1


def test_parse_replacement():
    result = parse(_fixture("replacement_changes.txt"))
    stack = result.stacks[0]
    rds = next(c for c in stack.changes if c.resource_type == "AWS::RDS::DBInstance")
    assert rds.requires_replacement is True
    assert rds.change_type == ChangeType.UPDATE


def test_parse_security_group_update():
    result = parse(_fixture("replacement_changes.txt"))
    stack = result.stacks[0]
    sg = next(c for c in stack.changes if c.resource_type == "AWS::EC2::SecurityGroup")
    assert sg.change_type == ChangeType.UPDATE


def test_parse_multi_stack():
    result = parse(_fixture("multi_stack.txt"))
    assert len(result.stacks) == 2
    names = {s.name for s in result.stacks}
    assert names == {"StackOne", "StackTwo"}

    stack_two = next(s for s in result.stacks if s.name == "StackTwo")
    removal = next(c for c in stack_two.changes if c.change_type == ChangeType.REMOVE)
    assert removal.resource_type == "AWS::DynamoDB::Table"
