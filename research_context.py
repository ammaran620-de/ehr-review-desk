"""Source-backed research context, separate from computed benchmark results."""
from datetime import date

REFERENCES = [
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
             'Data / evaluation': '250 held-out synthetic events; 25 anomalies',
             'Accuracy': f'{a:.1%}', 'Precision': f'{p:.1%}', 'Recall': f'{r:.1%}',
             'F1': f'{f:.1%}', 'ROC-AUC': f'{auc:.3f}'}]
    for ref in REFERENCES[:2]:
        rows.append({'Study': ref['citation'], 'Method': ref['method'],
                     'Data / evaluation': ref['data'], 'Accuracy': ref['accuracy'],
                     'Precision': ref['precision'], 'Recall': ref['recall'],
                     'F1': ref['f1'], 'ROC-AUC': ref['auc']})
    return rows


def evaluation_report(result):
    """Downloadable methods note; includes actual counts and limits on comparison."""
    p, r, f, a, auc = result['metrics']
    tn, fp = result['cm'][0]
    fn, tp = result['cm'][1]
    return '\n'.join([
        '# EHR Review Desk — evaluation and research context', '',
        f'Generated {date.today().isoformat()}. Literature checked 2026-11-11.', '',
        '## Research focus', '',
        'This prototype combines an existing Isolation Forest detector and Tree SHAP with a '
        'rule-based translation layer that produces plain-English alerts for IT reviewers. '
        'Its research focus is explanation clarity and feedback-guided refinement. Novelty '
        'and improved usefulness must be established through literature review and reviewer data.', '',
        '## Reproducible detection benchmark', '',
        'Seed 42; 1,000 synthetic records (900 normal, 100 injected anomalies); '
        '750 training records and 250 held-out records. Every fourth event is held out. '
        'Users can occur in both partitions; this is not an unseen-user or prospective hospital evaluation. '
        'Labels and scenario names are excluded from the seven input features, model fitting and score normalization. '
        'Isolation Forest uses 120 trees. Scores are scaled using only the training minimum and 95th percentile, '
        'then clipped to [0,1]. The fixed alert threshold is strictly greater than 0.75. '
        'The score is a relative anomaly index, not a probability. ROC-AUC uses the unclipped continuous raw scores.', '',
        f'TN={tn}, FP={fp}, FN={fn}, TP={tp}.',
        f'Precision={p:.4%}; recall={r:.4%}; F1={f:.4%}; accuracy={a:.4%}; ROC-AUC={auc:.6f}.', '',
        'Precision = TP/(TP+FP). Recall = TP/(TP+FN). Accuracy = (TP+TN)/N. '
        'F1 = 2×precision×recall/(precision+recall). '
        'The always-normal reference has 90% accuracy and 0% anomaly recall on this 90/10 test set. '
        'Accuracy alone is therefore insufficient. A 100% precision value means no false positives '
        'in this particular small test; it does not mean 100% accuracy or guaranteed future performance.', '',
        '## Published research context', '',
        '| Study | Accuracy | Precision | Recall | F1 | ROC-AUC |',
        '|---|---|---|---|---|---|',
        *[f"| {r['Study']} | {r['Accuracy']} | {r['Precision']} | {r['Recall']} | {r['F1']} | {r['ROC-AUC']} |"
          for r in comparison_rows(result)], '',
        'Published numbers are transcribed, not reproduced. These studies use different datasets, '
        'label definitions, class balances and evaluation methods. They are contextual references, '
        'not evidence that this prototype outperforms them. A fair numerical superiority claim '
        'requires shared data, labels, splits and an equivalent evaluation protocol. '
        'No results are edited, capped, or selected to fit an 80–90% band.', '',
        *[f"- **{ref['citation']}** — {ref['title']}. {ref.get('location', '')} "
          f"{ref['relevance']} {ref['url']}" for ref in REFERENCES], '',
        '## Human evaluation', '',
        'Reviewers select an alert from the table, inspect its plain-English explanation, raw SHAP '
        'and role baseline, then rate clarity, completeness, severity fit, trust, and perceived clarity '
        'relative to raw SHAP on a 1–5 scale. No comprehension quiz is required. '
        'The selected event and displayed version are attached automatically to each response. '
        'Round 2 uses approved revisions or explicit unchanged controls, with the same reviewer codes and cases. '
        'Paired rating changes are descriptive self-reports. They do not establish objective comprehension, '
        'causal improvement or changes to the detector. Repeated exposure and visible evidence can affect ratings. '
        'Legacy comprehension answers remain in CSV exports but are not summarized as a current study outcome.', '',
        '## Next evidence needed', '',
        'The client’s supervisor-approved reference papers and protocol should replace or supplement these '
        'candidate references. Actual reviewer responses are needed to assess translation usefulness. '
        'Hospital validation, noise/overlap stress tests, and unseen-user evaluation remain future work. '
        'The synthetic generator creates easily separable anomaly scenarios, which can inflate performance.', '',
    ])
