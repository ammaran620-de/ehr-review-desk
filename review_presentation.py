"""A fixed review sample, independent of model evaluation and Round 2 wording."""
REVIEW_LIMIT = 20
SEVERITY_ORDER = {'High': 0, 'Medium': 1, 'Low': 2}


def review_set(rows):
    """Choose once by baseline severity, score and ID; filters must run afterwards."""
    return sorted((r for r in rows if r['flagged']),
                  key=lambda r: (SEVERITY_ORDER[r['alert']['severity']], -r['score'], r['id']))[:REVIEW_LIMIT]
