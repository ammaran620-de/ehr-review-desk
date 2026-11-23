"""A fixed review sample, independent of model evaluation and Round 2 wording."""
from itertools import zip_longest

REVIEW_QUOTAS = {'High': 7, 'Medium': 8, 'Low': 5}
REVIEW_LIMIT = sum(REVIEW_QUOTAS.values())
SEVERITY_ORDER = {severity: index for index, severity in enumerate(REVIEW_QUOTAS)}


def review_set(rows):
    """Select the top-scoring candidates within each severity, using event ID for ties."""
    by_severity = {severity: [] for severity in REVIEW_QUOTAS}
    for row in sorted((row for row in rows if row['flagged']), key=lambda row: (-row['score'], row['id'])):
        by_severity[row['alert']['severity']].append(row)

    selected = [by_severity[severity][:quota] for severity, quota in REVIEW_QUOTAS.items()]
    remaining = sorted(
        (row for severity, quota in REVIEW_QUOTAS.items() for row in by_severity[severity][quota:]),
        key=lambda row: (-row['score'], row['id']),
    )
    interleaved = [row for group in zip_longest(*selected) for row in group if row is not None]
    return (interleaved + remaining)[:REVIEW_LIMIT]
