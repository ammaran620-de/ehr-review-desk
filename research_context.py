"""Source-backed research context, separate from computed benchmark results."""
from datetime import date

REFERENCES = [
    {
        'citation': 'Abengowe et al. (published May 2025; issue labelled 2024)',
        'title': 'An intelligent framework for securing patients’ electronic health records using anomaly based detection technique',
        'url': 'https://doi.org/10.4314/wojast.v16i1.123',
        'method': 'Linear SVC and other supervised baselines',
        'data': 'NSL-KDD network intrusion data, not EHR employee access logs',
        'accuracy': '92% Linear SVC; 44–98% across Table 2 models',
        'precision': 'Class-specific', 'recall': 'Class-specific', 'f1': 'Class-specific', 'auc': 'Not entered',
        'location': 'Table 2, Overall Accuracy row',
        'relevance': 'Table 2 reports Linear SVC at 92%, while the prose reports 93%; this discrepancy is unresolved. RF/DT reach 98% in the same table. Publication is listed as 8 May 2025 in a 2024-labelled issue. This is related security context, not a matched EHR access benchmark.',
    },
    {
        'citation': 'Chua et al. (2024)',
        'title': 'Web Traffic Anomaly Detection Using Isolation Forest',
        'url': 'https://doi.org/10.3390/informatics11040083',
        'method': 'Isolation Forest (unsupervised)',
        'data': 'E-commerce web logs; reported test records 1,035,020; not EHR logs',
        'accuracy': '93%', 'precision': '95%', 'recall': '90%', 'f1': '92%', 'auc': 'Not entered',
        'location': 'Table 6, classification metric scores',
        'relevance': 'A method-related reference near the requested range. Web traffic, scale and labels differ from our synthetic EHR access events. F1 of 92% must not be described as accuracy; the reported accuracy is 93%.',
    },
    {
        'citation': 'IEEE BigData (2025 conference; indexed March 2026)',
        'title': 'Explainable Anomaly Detection Framework for Electronic Health Record Access Logs',
        'url': 'https://doi.org/10.1109/BigData66926.2025.11400768',
        'relevance': 'The accessible abstract describes autoencoders and Integrated Gradients producing human-readable EHR audit-log rationales. A numerical accuracy was not verified, so none is entered. This is recent, closely related explanation work; our translation layer cannot be assumed novel without comparing its design.',
    },
    {
        'citation': 'Tabassum et al. (2024)',
        'title': 'Anomaly-based threat detection in smart health using machine learning',
        'url': 'https://doi.org/10.1186/s12911-024-02760-4',
        'method': 'Isolation Forest + SVM',
        'data': 'Hospital EHR data; pseudo-labeling followed by supervised classification',
        'accuracy': '99.21%', 'precision': '98.23%', 'recall': '99.75%',
        'f1': '98.72%', 'auc': 'Not entered',
        'location': 'Table 5, SVM row',
        'relevance': 'Related EHR security work. Its hybrid pipeline and labeling procedure differ from this prototype. Values are reported by the authors and have not been independently reproduced.',
    },
    {
        'citation': 'Iqbal et al. (2026)',
        'title': 'Enhancing healthcare information security through VAE-driven anomaly detection in EHR access patterns',
        'url': 'https://doi.org/10.1038/s41598-026-55024-8',
        'method': 'Variational autoencoder',
        'data': 'Synthetic EHR access logs; test support 2,000 with 113 anomalies',
        'accuracy': '99% (rounded)', 'precision': '92%', 'recall': '94%',
        'f1': '93%', 'auc': '0.996',
        'location': 'Table 7; anomalous-class precision, recall and F1',
        'relevance': 'Related synthetic EHR access study using SHAP. Different data, class prevalence and detector prevent a direct ranking against our results.',
    },
    {
        'citation': 'Weerts, van Ipenburg & Pechenizkiy (2019)',
        'title': 'A Human-Grounded Evaluation of SHAP for Alert Processing',
        'url': 'https://arxiv.org/abs/1907.03324',
        'relevance': 'The authors evaluated alert processing with 159 participants and found no significant performance difference with SHAP available. This motivates evaluating explanation usefulness with people instead of assuming that SHAP alone improves understanding. This was not an EHR benchmark.',
    },
]


def comparison_rows(result):
    """Published values retain their own dataset and method, without a leaderboard."""
    p, r, f, a, auc = result['metrics']
    rows = [{'Study': 'This prototype · computed now', 'Method': 'Isolation Forest (unsupervised)',
             'Data / evaluation': f"{result['metadata']['test_count']} synthetic test events; {result['metadata']['test_anomalies']} anomalies",
             'Accuracy': f'{a:.1%}', 'Precision': f'{p:.1%}', 'Recall': f'{r:.1%}',
             'F1': f'{f:.1%}', 'ROC-AUC': f'{auc:.3f}'}]
    for ref in REFERENCES:
        if 'accuracy' not in ref:
            continue
        rows.append({'Study': ref['citation'], 'Method': ref['method'],
                     'Data / evaluation': ref['data'], 'Accuracy': ref['accuracy'],
                     'Precision': ref['precision'], 'Recall': ref['recall'],
                     'F1': ref['f1'], 'ROC-AUC': ref['auc']})
    return rows


def evaluation_report(result):
    """Export the selected dataset, actual metrics and traceable literature context."""
    p, r, f, a, auc = result['metrics']
    m = result['metadata']
    tn, fp = result['cm'][0]
    fn, tp = result['cm'][1]
    realistic = m['benchmark_id'] == 'realistic-v1'
    return '\n'.join([
        '# EHR Review Desk — evaluation and research context', '',
        f'Generated {date.today().isoformat()}. Literature checked 2026-11-18.', '',
        '## Research focus', '',
        'Isolation Forest detects unusual access without training on labels. Tree SHAP attributes model output. '
        'The Python translation layer produces plain-English alerts; reviewer ratings assess perceived usefulness. '
        'Recent EHR work already studies human-readable rationales, so novelty and improvement require evidence.', '',
        '## Selected benchmark', '',
        f"Benchmark: {m['benchmark_name']} ({m['benchmark_id']}); seed {m['seed']}; dataset SHA-256 {m['dataset_sha256']}.",
        f"1,000 synthetic records; 900 legitimate and 100 injected anomalies. Training records: {m['training_count']}; "
        f"test records: {m['test_count']} ({m['test_normal']} normal, {m['test_anomalies']} anomalies). Split: {m['split']}.",
        ('Realistic-v1 includes 36 legitimate exceptions (authorized overtime, department cover, workload surges) '
         'and 25 subtle anomalies. All events for a test user are excluded from training. Authorization is simulation '
         'ground truth, not an observed feature; behavioral overlap can produce false alarms and misses. '
         'The policy midpoint defines each role baseline. See REALISTIC_PROTOCOL.md for fixed assumptions.'
         if realistic else 'Original demonstration preserves earlier events and reviews. Users can occur in both partitions; '
         'its scenarios are easily separable. Do not compare it to realistic-v1 as though the data were unchanged.'), '',
        'Both benchmarks use seven observed features, 120 trees, training-only normalization from the minimum to '
        'the 95th percentile, clipping to [0,1], and the fixed threshold >0.75. Labels are excluded from fitting. '
        'The relative anomaly index is not a probability; ROC-AUC uses raw unclipped scores.', '',
        f'TN={tn}, FP={fp}, FN={fn}, TP={tp}.',
        f'Precision={p:.4%}; recall={r:.4%}; F1={f:.4%}; accuracy={a:.4%}; ROC-AUC={auc:.6f}.',
        f"Always-normal reference: {m['majority_accuracy']:.4%} accuracy and 0% anomaly recall. Accuracy alone is insufficient.", '',
        '## Published research context', '',
        '| Study | Accuracy | Precision | Recall | F1 | ROC-AUC |',
        '|---|---|---|---|---|---|',
        *[f"| {row['Study']} | {row['Accuracy']} | {row['Precision']} | {row['Recall']} | {row['F1']} | {row['ROC-AUC']} |"
          for row in comparison_rows(result)], '',
        'These are author-reported figures, not reproduced experiments or a leaderboard. Differences in tasks, '
        'datasets, class balances and protocols prevent direct superiority claims. The Abengowe table/prose '
        'discrepancy is retained rather than resolved by picking the more convenient value. Higher published '
        'results remain visible. Desired percentages are not substituted for measured results.', '',
        *[f"- **{ref['citation']}** — {ref['title']}. {ref.get('location', '')} "
          f"{ref['relevance']} {ref['url']}" for ref in REFERENCES], '',
        '## Human evaluation and data separation', '',
        'Select an alert, inspect its wording, raw SHAP and role baseline, and submit five 1–5 ratings plus '
        'an optional comment. No recall quiz is required. The event, wording version, benchmark and dataset '
        'fingerprint are attached to feedback. Original feedback is preserved. Each realistic dataset has its '
        'own storage folder. Match reviewer/case/round only within one benchmark, dataset and survey protocol. '
        'Round 2 uses approved revisions or unchanged controls. Rating changes are descriptive self-reports, '
        'not objective comprehension, causal improvement or changes in detection accuracy.', '',
        '## Sensitivity and limitations', '',
        'The primary realistic run is fixed to seed 42. All configured additional seeds 43–46 are reported in '
        'the dashboard and evaluations/realistic-v1.json; no best seed is substituted for the primary run. '
        'These development simulations are not a blind external validation or hospital trial. Higher realism '
        'and separated test users do not establish clinical representativeness. Supervisor-approved papers '
        'and actual reviewer responses are still needed. No patient data is used.', '',
    ])
