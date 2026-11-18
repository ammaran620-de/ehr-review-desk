"""Rebuild the primary realistic evidence and every configured sensitivity run."""
import json
from pathlib import Path

from pipeline import run_pipeline
from realistic_pipeline import sensitivity_runs
from research_context import evaluation_report


def main():
    result = run_pipeline('realistic-v1')
    payload = {key: result[key] for key in ('metadata', 'metrics', 'cm', 'test_predictions')}
    payload['sensitivity'] = sensitivity_runs()
    target = Path(__file__).resolve().parent
    (target / 'evaluations').mkdir(exist_ok=True)
    (target / 'evaluations/realistic-v1.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    (target / 'RESEARCH_CONTEXT.md').write_text(evaluation_report(result), encoding='utf-8')
    print('Primary metrics:', result['metrics'])
    print('Confusion matrix:', result['cm'])
    print('Every configured run:', payload['sensitivity'])


if __name__ == '__main__':
    main()
