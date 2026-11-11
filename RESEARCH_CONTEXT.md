# EHR Review Desk — evaluation and research context

Generated 2026-11-11. Literature checked 2026-11-11.

## Research focus

This prototype combines an existing Isolation Forest detector and Tree SHAP with a rule-based translation layer that produces plain-English alerts for IT reviewers. Its research focus is explanation clarity and feedback-guided refinement. Novelty and improved usefulness must be established through literature review and reviewer data.

## Reproducible detection benchmark

Seed 42; 1,000 synthetic records (900 normal, 100 injected anomalies); 750 training records and 250 held-out records. Every fourth event is held out. Users can occur in both partitions; this is not an unseen-user or prospective hospital evaluation. Labels and scenario names are excluded from the seven input features, model fitting and score normalization. Isolation Forest uses 120 trees. Scores are scaled using only the training minimum and 95th percentile, then clipped to [0,1]. The fixed alert threshold is strictly greater than 0.75. The score is a relative anomaly index, not a probability. ROC-AUC uses the unclipped continuous raw scores.

TN=225, FP=0, FN=3, TP=22.
Precision=100.0000%; recall=88.0000%; F1=93.6170%; accuracy=98.8000%; ROC-AUC=1.000000.

Precision = TP/(TP+FP). Recall = TP/(TP+FN). Accuracy = (TP+TN)/N. F1 = 2×precision×recall/(precision+recall). The always-normal reference has 90% accuracy and 0% anomaly recall on this 90/10 test set. Accuracy alone is therefore insufficient. A 100% precision value means no false positives in this particular small test; it does not mean 100% accuracy or guaranteed future performance.

## Published research context

| Study | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| This prototype · computed now | 98.8% | 100.0% | 88.0% | 93.6% | 1.000 |
| Tabassum et al. (2024) | 99.21% | 98.23% | 99.75% | 98.72% | Not entered |
| Iqbal et al. (2026) | 99% (rounded) | 92% | 94% | 93% | 0.996 |

Published numbers are transcribed, not reproduced. These studies use different datasets, label definitions, class balances and evaluation methods. They are contextual references, not evidence that this prototype outperforms them. A fair numerical superiority claim requires shared data, labels, splits and an equivalent evaluation protocol. No results are edited, capped, or selected to fit an 80–90% band.

- **Tabassum et al. (2024)** — Anomaly-based threat detection in smart health using machine learning. Table 5, SVM row Related EHR security work. Its hybrid pipeline and labeling procedure differ from this prototype. Values are reported by the authors and have not been independently reproduced. https://doi.org/10.1186/s12911-024-02760-4
- **Iqbal et al. (2026)** — Enhancing healthcare information security through VAE-driven anomaly detection in EHR access patterns. Table 7; anomalous-class precision, recall and F1 Related synthetic EHR access study using SHAP. Different data, class prevalence and detector prevent a direct ranking against our results. https://doi.org/10.1038/s41598-026-55024-8
- **Weerts, van Ipenburg & Pechenizkiy (2019)** — A Human-Grounded Evaluation of SHAP for Alert Processing.  The authors evaluated alert processing with 159 participants and found no significant performance difference with SHAP available. This motivates evaluating explanation usefulness with people instead of assuming that SHAP alone improves understanding. This was not an EHR benchmark. https://arxiv.org/abs/1907.03324

## Human evaluation

Reviewers select an alert from the table, inspect its plain-English explanation, raw SHAP and role baseline, then rate clarity, completeness, severity fit, trust, and perceived clarity relative to raw SHAP on a 1–5 scale. No comprehension quiz is required. The selected event and displayed version are attached automatically to each response. Round 2 uses approved revisions or explicit unchanged controls, with the same reviewer codes and cases. Paired rating changes are descriptive self-reports. They do not establish objective comprehension, causal improvement or changes to the detector. Repeated exposure and visible evidence can affect ratings. Legacy comprehension answers remain in CSV exports but are not summarized as a current study outcome.

## Next evidence needed

The client’s supervisor-approved reference papers and protocol should replace or supplement these candidate references. Actual reviewer responses are needed to assess translation usefulness. Hospital validation, noise/overlap stress tests, and unseen-user evaluation remain future work. The synthetic generator creates easily separable anomaly scenarios, which can inflate performance.
