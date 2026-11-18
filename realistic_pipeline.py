"""Fixed realistic-v1 simulation: legitimate exceptions, subtle anomalies, unseen users."""
import hashlib
import importlib.metadata
import json

import numpy as np
import shap
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_auc_score, roc_curve
from sklearn.model_selection import GroupShuffleSplit

from translation import translate

BASELINES = [
    ('Doctor', 7, 19, 20, 45, ['Medicine', 'Surgery']),
    ('Nurse', 6, 20, 15, 35, ['Medicine', 'Emergency']),
    ('Receptionist', 8, 17, 6, 18, ['Admissions', 'Outpatient']),
    ('Lab Technician', 7, 18, 10, 28, ['Laboratory', 'Pathology']),
    ('IT Staff', 8, 19, 3, 12, ['IT', 'Administration']),
]
FEATURES = ['Login time', 'Off-hours flag', 'Records accessed', 'Session duration',
            'Access rate', 'Role mismatch', 'Unassigned department']
SCENARIOS = ['Excessive access', 'Off-hours access', 'Role mismatch', 'Burst behavior', 'Unassigned access']
SENSITIVITY_SEEDS = (42, 43, 44, 45, 46)


def generate_events(seed=42):
    rng = np.random.default_rng(seed)
    exception_ids = {int(i): j % 3 for j, i in enumerate(rng.choice(900, 36, replace=False))}
    subtle_ids = set(map(int, rng.choice([i for i in range(900, 1000) if i != 902], 25, replace=False)))
    rows, matrix = [], []
    for i in range(1000):
        role, start, end, low, high, departments = BASELINES[i % 5]
        minute = int(rng.integers(start * 60, end * 60))
        count = int(np.clip(round(rng.lognormal(np.log((low + high) / 2), .23)), low, high))
        duration = int(rng.integers(15, 90))
        assigned = departments[((i % 75) // 5) % 2]
        other = next(d for d in departments if d != assigned)
        department = assigned
        kind = 'Normal' if i < 900 else SCENARIOS[((i - 900) // 5 + i % 5) % 5]
        subtle = i in subtle_ids
        legitimate_context = 'Routine workflow'
        if i in exception_ids:
            exception = exception_ids[i]
            if exception == 0:
                minute = max(0, start * 60 - int(rng.integers(30, 181)))
                legitimate_context = 'Authorized overtime'
            elif exception == 1:
                department = other
                legitimate_context = 'Authorized department cover'
            else:
                count = int(round(count * rng.uniform(1.5, 2.5)))
                duration = int(rng.integers(60, 121))
                legitimate_context = 'Legitimate workload surge'
        if kind == 'Excessive access':
            count = int(round(count * rng.uniform(1.2, 1.8) if subtle else count * rng.uniform(2, 5)))
            duration = int(rng.integers(45, 91) if subtle else rng.integers(60, 151))
        elif kind == 'Off-hours access':
            minute = max(0, start * 60 - int(rng.integers(1, 46))) if subtle else int(rng.integers(0, 300))
        elif kind == 'Role mismatch':
            department = other if subtle else 'Intensive Care'
        elif kind == 'Burst behavior':
            duration = int(rng.integers(8, 15) if subtle else rng.integers(1, 5))
        elif kind == 'Unassigned access':
            department = other
        if i == 902:
            minute, count, duration, department = 135, 187, 32, 'Surgery'
            kind = 'Combined scenario'
        off = not start * 60 <= minute < end * 60
        mismatch = department not in departments
        unassigned = department != assigned and not mismatch
        matrix.append([minute, int(off), count, duration, count / duration, int(mismatch), int(unassigned)])
        rows.append(dict(id=f'EVT-{i+1:04}', user_id=f'USR_{(i % 75)+1:03}', role=role,
            date=f'2026-10-{1+i%28:02}', login_time=f'{minute//60:02}:{minute%60:02}',
            records_accessed=count, session_duration_mins=duration, department_accessed=department,
            assigned_department=assigned, off_hours_access=off, role_mismatch=mismatch,
            label=int(i >= 900), scenario=('Subtle ' if subtle and i != 902 else '') + kind,
            simulation_context=legitimate_context if i < 900 else 'Injected unauthorized access',
            hours=f'{start:02}:00–{end:02}:00', baseline=(low + high) / 2))
    return rows, np.asarray(matrix, dtype=np.float32)


def run_realistic_pipeline(seed=42, explain=True):
    rows, x = generate_events(seed)
    users = np.array([r['user_id'] for r in rows])
    train_ids, test_ids = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=seed).split(x, groups=users))
    train = np.zeros(len(rows), dtype=bool)
    train[train_ids] = True
    model = IsolationForest(n_estimators=120, random_state=seed).fit(x[train])
    raw = -model.score_samples(x)
    low, high = float(raw[train].min()), float(np.quantile(raw[train], .95))
    if high <= low:
        raise ValueError('Training score range is degenerate.')
    scores = np.clip((raw - low) / (high - low), 0, 1)
    flags = scores > .75
    by_row, expected = {}, None
    if explain and flags.any():
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(x[flags], check_additivity=False)
        expected = float(np.asarray(explainer.expected_value).item())
        from sklearn.ensemble._iforest import _average_path_length
        mean_depth = -np.log2(raw[flags]) * _average_path_length([model.max_samples_])[0]
        np.testing.assert_allclose(values.sum(axis=1) + expected, mean_depth, atol=2e-5)
        by_row = dict(zip(np.flatnonzero(flags), values))
    for i, row in enumerate(rows):
        row.update(score=float(scores[i]), raw_score=float(raw[i]), flagged=bool(flags[i]), held_out=bool(not train[i]))
        if flags[i] and explain:
            row['shap'] = [-round(float(v), 6) for v in by_row[i]]
            row['alert'] = translate(row, FEATURES)
    y = np.array([r['label'] for r in rows])
    cm = confusion_matrix(y[~train], flags[~train], labels=[0, 1]).tolist()
    p, recall, f1, _ = precision_recall_fscore_support(y[~train], flags[~train], average='binary', zero_division=0)
    roc_x, roc_y, _ = roc_curve(y[~train], raw[~train])
    train_users, test_users = sorted(set(users[train])), sorted(set(users[~train]))
    assert not set(train_users) & set(test_users)
    assert len({(r['user_id'], r['date']) for r in rows}) == 1000
    assert int(y.sum()) == 100
    digest_payload = dict(features=x.tolist(), users=users.tolist(), labels=y.tolist(), benchmark='realistic-v1')
    metadata = dict(benchmark_id='realistic-v1', benchmark_name='Realistic access patterns', seed=seed,
        n_estimators=120, threshold=.75, threshold_operator='>', training_count=len(train_ids),
        test_count=len(test_ids), test_anomalies=int(y[~train].sum()), test_normal=int((y[~train] == 0).sum()),
        majority_accuracy=float(np.mean(y[~train] == 0)),
        legitimate_exception_count=36, subtle_anomaly_count=25,
        split='GroupShuffleSplit by user; 25% of users held out', train_users=train_users, test_users=test_users,
        user_overlap=False, score='Training-normalized anomaly index; not a probability',
        normalization_min=low, normalization_p95=high,
        labels_used_for_fit=False, labels_used_for_split=False,
        dataset_sha256=hashlib.sha256(json.dumps(digest_payload, sort_keys=True).encode()).hexdigest(),
        packages={name: importlib.metadata.version(name) for name in ('numpy', 'scikit-learn', 'shap')})
    predictions = [dict(event=r['id'], user=r['user_id'], actual=r['label'], predicted=int(r['flagged']),
                        score=r['score'], raw_score=r['raw_score']) for r in rows if r['held_out']]
    return dict(rows=rows, features=FEATURES, cm=cm, metadata=metadata, test_predictions=predictions,
        metrics=[float(p), float(recall), float(f1), (cm[0][0] + cm[1][1]) / len(test_ids),
                 float(roc_auc_score(y[~train], raw[~train]))],
        roc=[roc_x.tolist(), roc_y.tolist()], expected=expected, baselines=BASELINES)


def sensitivity_runs():
    return [dict(seed=seed, **dict(zip(('precision', 'recall', 'f1', 'accuracy', 'roc_auc'),
                run_realistic_pipeline(seed, explain=False)['metrics']))) for seed in SENSITIVITY_SEEDS]
