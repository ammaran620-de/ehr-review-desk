"""Versioned synthetic benchmarks; reported metrics always come from predictions."""
import json
from pathlib import Path
from reference_pipeline import run_pipeline as run_reference


def run_pipeline(benchmark='reference-v1', *, seed=42, explain=True):
    if benchmark == 'reference-v1':
        if seed != 42:
            raise ValueError('The original benchmark is pinned to seed 42.')
        result = run_reference()
        result['metadata'].update(benchmark_id='reference-v1', benchmark_name='Original demonstration',
                                  test_normal=225, majority_accuracy=.9, user_overlap=True)
        return result
    if benchmark == 'realistic-v1':
        from realistic_pipeline import run_realistic_pipeline
        return run_realistic_pipeline(seed=seed, explain=explain)
    raise ValueError(f'Unknown benchmark: {benchmark}')


if __name__ == '__main__':
    import argparse
    import pandas as pd
    parser = argparse.ArgumentParser()
    parser.add_argument('--benchmark', choices=['realistic-v1', 'reference-v1'], default='realistic-v1')
    args = parser.parse_args()
    result = run_pipeline(args.benchmark)
    Path('ehr_data.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    columns = ['id', 'user_id', 'role', 'date', 'login_time', 'records_accessed',
               'department_accessed', 'assigned_department', 'session_duration_mins',
               'role_mismatch', 'off_hours_access', 'label']
    pd.DataFrame(result['rows'])[columns].to_csv('synthetic_access_logs.csv', index=False)
    print('Benchmark:', args.benchmark, '| Metrics:', result['metrics'], '| Confusion matrix:', result['cm'])
