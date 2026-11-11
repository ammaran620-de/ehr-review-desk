"""Synthetic EHR detection, explanation and alert generation."""
import json
import hashlib
import importlib.metadata

from translation import translate

import numpy as np
import shap
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_auc_score, roc_curve


def run_pipeline():
    rng = np.random.default_rng(42)
    baselines = [
        ('Doctor', 7, 19, 20, 45, ['Medicine', 'Surgery']),
        ('Nurse', 6, 20, 15, 35, ['Medicine', 'Emergency']),
        ('Receptionist', 8, 17, 6, 18, ['Admissions', 'Outpatient']),
        ('Lab Technician', 7, 18, 10, 28, ['Laboratory', 'Pathology']),
        ('IT Staff', 8, 19, 3, 12, ['IT', 'Administration']),
    ]
    types = ['Excessive access', 'Off-hours access', 'Role mismatch', 'Burst behavior', 'Unassigned access']
    features = ['Login time', 'Off-hours flag', 'Records accessed', 'Session duration', 'Access rate', 'Role mismatch', 'Unassigned department']
    rows = []
    matrix = []
    for i in range(1000):
        role, start, end, low, high, departments = baselines[i % 5]
        minute = int(rng.integers(start * 60, end * 60))
        count = int(rng.integers(low, high + 1))
        duration = int(rng.integers(15, 90))
        assigned = departments[(i % 75) // 5 % 2]
        department = assigned
        kind = 'Normal' if i < 900 else types[((i - 900) // 5 + i % 5) % 5]
        if kind == types[0]:
            count *= int(rng.integers(4, 11))
            duration = int(rng.integers(100, 190))
        elif kind == types[1]:
            minute = int(rng.integers(0, 300))
        elif kind == types[2]:
            department = 'Intensive Care'
        elif kind == types[3]:
            duration = int(rng.integers(1, 4))
        elif kind == types[4]:
            department = next(d for d in departments if d != assigned)
        if i == 902:
            minute, count, duration, department = 135, 187, 32, 'Surgery'
            kind = 'Combined scenario'
        off = not start * 60 <= minute < end * 60
        mismatch = department not in departments
        unassigned = department != assigned and not mismatch
        matrix.append([minute, off, count, duration, count / duration, mismatch, unassigned])
        rows.append(dict(id=f'EVT-{i+1:04}', user_id=f'USR_{(i % 75)+1:03}', role=role,
            date=f'2026-10-{1+i%28:02}', login_time=f'{minute//60:02}:{minute%60:02}',
            records_accessed=count, session_duration_mins=duration, department_accessed=department,
            assigned_department=assigned, off_hours_access=off, role_mismatch=mismatch,
            label=int(kind != 'Normal'), scenario=kind, hours=f'{start:02}:00–{end:02}:00'))
    x = np.array(matrix, dtype=np.float32)
    # Deterministic split by index. The injected labels are excluded from fit and score normalization.
    train = np.arange(len(rows)) % 4 != 0
    model = IsolationForest(n_estimators=120, random_state=42).fit(x[train])
    raw = -model.score_samples(x)
    lo, hi = raw[train].min(), np.quantile(raw[train], 0.95)
    scores = np.clip((raw - lo) / (hi - lo), 0, 1)
    flags = scores > 0.75
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(x[flags], check_additivity=False)
    expected = float(np.asarray(explainer.expected_value).item())
    # Invert the Isolation Forest score transform to recover its mean path length.
    from sklearn.ensemble._iforest import _average_path_length
    mean_depth = -np.log2(raw[flags]) * _average_path_length([model.max_samples_])[0]
    np.testing.assert_allclose(values.sum(axis=1) + expected, mean_depth, atol=2e-5)
    averages = {role: float(np.mean([r['records_accessed'] for j,r in enumerate(rows[:900])
        if train[j] and r['role'] == role])) for role,*_ in baselines}
    by_row = dict(zip(np.flatnonzero(flags), values))
    for i,r in enumerate(rows):
        r.update(score=float(scores[i]), raw_score=float(raw[i]), flagged=bool(flags[i]), held_out=bool(not train[i]), baseline=round(averages[r['role']], 2))
        if flags[i]:
            r['shap'] = [-round(float(v), 6) for v in by_row[i]]
            r['alert'] = translate(r, features)
    y = [r['label'] for r in rows]
    cm = confusion_matrix(np.array(y)[~train], flags[~train], labels=[0,1]).tolist()
    p, rec, f1, _ = precision_recall_fscore_support(np.array(y)[~train], flags[~train], average='binary', zero_division=0)
    assert len({(r['user_id'], r['date']) for r in rows}) == len(rows)
    assert sum(y) == 100 and len(rows) == 1000
    # ROC uses continuous scores before clipping to preserve rank.
    roc_x, roc_y, _ = roc_curve(np.array(y)[~train], raw[~train])
    held_out = [dict(event=r['id'], actual=r['label'], predicted=int(r['flagged']),
                     score=r['score'], raw_score=r['raw_score']) for r in rows if r['held_out']]
    metadata = dict(seed=42, n_estimators=120, threshold=0.75, threshold_operator='>',
        training_count=int(train.sum()), test_count=len(held_out),
        test_anomalies=sum(r['actual'] for r in held_out),
        split='Every fourth event held out; not an unseen-user split',
        score='Relative training-normalized anomaly index, not a probability',
        labels_used_for_fit=False,
        dataset_sha256=hashlib.sha256(json.dumps(matrix, separators=(',', ':')).encode()).hexdigest(),
        packages={p: importlib.metadata.version(p) for p in ('numpy', 'scikit-learn', 'shap')})
    return dict(rows=rows, features=features, cm=cm, metadata=metadata, test_predictions=held_out,
        metrics=[float(p), float(rec), float(f1), (cm[0][0]+cm[1][1])/250,
                 float(roc_auc_score(np.array(y)[~train], raw[~train]))],
        roc=[roc_x.tolist(), roc_y.tolist()], expected=expected, baselines=baselines)

if __name__ == '__main__':
    from pathlib import Path
    import pandas as pd

    result = run_pipeline()
    Path('ehr_data.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    columns = ['id', 'user_id', 'role', 'date', 'login_time', 'records_accessed',
               'department_accessed', 'assigned_department', 'session_duration_mins',
               'role_mismatch', 'off_hours_access', 'label']
    pd.DataFrame(result['rows'])[columns].to_csv('synthetic_access_logs.csv', index=False)
    print('Held-out confusion matrix:', result['cm'], '| ROC-AUC:', result['metrics'][-1])
