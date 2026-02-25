from cdkdiff.models import Change, ChangeType, DiffSummary, RiskLevel

_MEDIUM_RISK_TYPES = {
    "AWS::EC2::SecurityGroup",
    "AWS::KMS::Key",
    "AWS::ElastiCache::ReplicationGroup",
    "AWS::RDS::DBInstance",
    "AWS::ElasticLoadBalancingV2::LoadBalancer",
}


def score_change(change: Change) -> RiskLevel:
    """Return the risk level for a single change."""
    if change.change_type == ChangeType.REMOVE:
        return RiskLevel.HIGH

    if change.change_type == ChangeType.ADD:
        return RiskLevel.LOW

    # UPDATE
    if change.requires_replacement:
        return RiskLevel.HIGH

    if change.resource_type in _MEDIUM_RISK_TYPES:
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


def score_summary(summary: DiffSummary) -> DiffSummary:
    """Mutate risk levels on all changes in-place and return the summary."""
    for stack in summary.stacks:
        for change in stack.changes:
            change.risk = score_change(change)
    return summary
