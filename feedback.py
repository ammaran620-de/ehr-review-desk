"""Persist one response per reviewer, alert and round."""
import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from filelock import FileLock

FIELDS = ('utc', 'reviewer', 'event', 'round', 'version', 'severity', 'template',
          'clarity', 'completeness', 'severity_fit', 'trust', 'interpretation_correct', 'shap_clarity', 'comment', 'survey_protocol')
KEY = ('reviewer', 'event', 'round')

def read_feedback(path):
    try:
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames or []
            allowed = [set(FIELDS) - omitted for omitted in
                       (set(), {'shap_clarity'}, {'survey_protocol'}, {'shap_clarity', 'survey_protocol'})]
            if set(headers) not in allowed or len(headers) != len(set(headers)):
                raise ValueError('The CSV column headers do not match the feedback format.')
            rows = list(reader)
    except FileNotFoundError:
        return []
    except csv.Error as exc:
        raise ValueError(f'Invalid CSV syntax: {exc}') from exc

    seen = set()
    for line, row in enumerate(rows, start=2):
        row.setdefault('shap_clarity', '')
        row.setdefault('survey_protocol', 'quiz-v1' if row.get('interpretation_correct') else 'direct-review-v2')
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f'CSV row {line} has missing or extra fields.')
        if (row['round'] not in {'1', '2'}
                or not re.fullmatch(r'[a-z0-9_-]{2,32}', row['reviewer'])
                or not re.fullmatch(r'EVT-\d{4}', row['event'])
                or row['severity'] not in {'High', 'Medium', 'Low'}
                or row['interpretation_correct'] not in {'', '0', '1'}
                or row['survey_protocol'] not in {'quiz-v1', 'direct-review-v2'}
                or any(row[key] not in {'1', '2', '3', '4', '5'} for key in
                       ('clarity', 'completeness', 'severity_fit', 'trust'))
                or row['shap_clarity'] not in {'', '1', '2', '3', '4', '5'}):
            raise ValueError(f'CSV row {line} contains an invalid response.')
        key = tuple(row[field] for field in KEY)
        if key in seen:
            raise ValueError(f'CSV row {line} duplicates a reviewer, case and round.')
        seen.add(key)
    return rows

def save_feedback(path, response):
    path = Path(path)
    response = {'survey_protocol': 'direct-review-v2', **response, 'utc': datetime.now(timezone.utc).isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + '.lock', timeout=10):
        rows = read_feedback(path)
        key = tuple(str(response[k]) for k in KEY)
        rows = [row for row in rows if tuple(row[k] for k in KEY) != key]
        with NamedTemporaryFile(mode='w', newline='', encoding='utf-8', dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows([*rows, response])
        try:
            # Validate the candidate CSV before replacing an existing study file.
            read_feedback(temporary)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
