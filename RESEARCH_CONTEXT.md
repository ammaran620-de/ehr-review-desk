# EHR Review Desk — evaluation and research context

Generated 2026-11-18. Literature checked 2026-11-18.

## Research focus

Isolation Forest detects unusual access without training on labels. Tree SHAP attributes model output. The Python translation layer produces plain-English alerts; reviewer ratings assess perceived usefulness. Recent EHR work already studies human-readable rationales, so novelty and improvement require evidence.

## Selected benchmark

Benchmark: Realistic access patterns (realistic-v1); seed 42; dataset SHA-256 4aa9da99a7ce089575e862dd5bd13c934a4db3a3d2611669d9df73e397676971.
1,000 synthetic records; 900 legitimate and 100 injected anomalies. Training records: 745; test records: 255 (228 normal, 27 anomalies). Split: GroupShuffleSplit by user; 25% of users held out.
Realistic-v1 includes 36 legitimate exceptions (authorized overtime, department cover, workload surges) and 25 subtle anomalies. All events for a test user are excluded from training. Authorization is simulation ground truth, not an observed feature; behavioral overlap can produce false alarms and misses. The policy midpoint defines each role baseline. See REALISTIC_PROTOCOL.md for fixed assumptions.

Both benchmarks use seven observed features, 120 trees, training-only normalization from the minimum to the 95th percentile, clipping to [0,1], and the fixed threshold >0.75. Labels are excluded from fitting. The relative anomaly index is not a probability; ROC-AUC uses raw unclipped scores.

TN=226, FP=2, FN=6, TP=21.
Precision=91.3043%; recall=77.7778%; F1=84.0000%; accuracy=96.8627%; ROC-AUC=0.976283.
Always-normal reference: 89.4118% accuracy and 0% anomaly recall. Accuracy alone is insufficient.

## Published research context

| Study | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| This prototype · computed now | 96.9% | 91.3% | 77.8% | 84.0% | 0.976 |
| Abengowe et al. (published May 2025; issue labelled 2024) | 92% Linear SVC; 44–98% across Table 2 models | Class-specific | Class-specific | Class-specific | Not entered |
| Chua et al. (2024) | 93% | 95% | 90% | 92% | Not entered |
| Tabassum et al. (2024) | 99.21% | 98.23% | 99.75% | 98.72% | Not entered |
| Iqbal et al. (2026) | 99% (rounded) | 92% | 94% | 93% | 0.996 |

These are author-reported figures, not reproduced experiments or a leaderboard. Differences in tasks, datasets, class balances and protocols prevent direct superiority claims. The Abengowe table/prose discrepancy is retained rather than resolved by picking the more convenient value. Higher published results remain visible. Desired percentages are not substituted for measured results.

- **Abengowe et al. (published May 2025; issue labelled 2024)** — An intelligent framework for securing patients’ electronic health records using anomaly based detection technique. Table 2, Overall Accuracy row Table 2 reports Linear SVC at 92%, while the prose reports 93%; this discrepancy is unresolved. RF/DT reach 98% in the same table. Publication is listed as 8 May 2025 in a 2024-labelled issue. This is related security context, not a matched EHR access benchmark. https://doi.org/10.4314/wojast.v16i1.123
- **Chua et al. (2024)** — Web Traffic Anomaly Detection Using Isolation Forest. Table 6, classification metric scores A method-related reference near the requested range. Web traffic, scale and labels differ from our synthetic EHR access events. F1 of 92% must not be described as accuracy; the reported accuracy is 93%. https://doi.org/10.3390/informatics11040083
- **IEEE BigData (2025 conference; indexed March 2026)** — Explainable Anomaly Detection Framework for Electronic Health Record Access Logs.  The accessible abstract describes autoencoders and Integrated Gradients producing human-readable EHR audit-log rationales. A numerical accuracy was not verified, so none is entered. This is recent, closely related explanation work; our translation layer cannot be assumed novel without comparing its design. https://doi.org/10.1109/BigData66926.2025.11400768
- **Tabassum et al. (2024)** — Anomaly-based threat detection in smart health using machine learning. Table 5, SVM row Related EHR security work. Its hybrid pipeline and labeling procedure differ from this prototype. Values are reported by the authors and have not been independently reproduced. https://doi.org/10.1186/s12911-024-02760-4
- **Iqbal et al. (2026)** — Enhancing healthcare information security through VAE-driven anomaly detection in EHR access patterns. Table 7; anomalous-class precision, recall and F1 Related synthetic EHR access study using SHAP. Different data, class prevalence and detector prevent a direct ranking against our results. https://doi.org/10.1038/s41598-026-55024-8
- **Weerts, van Ipenburg & Pechenizkiy (2019)** — A Human-Grounded Evaluation of SHAP for Alert Processing.  The authors evaluated alert processing with 159 participants and found no significant performance difference with SHAP available. This motivates evaluating explanation usefulness with people instead of assuming that SHAP alone improves understanding. This was not an EHR benchmark. https://arxiv.org/abs/1907.03324

## Human evaluation and data separation

Select an alert, inspect its wording, raw SHAP and role baseline, and submit five 1–5 ratings plus an optional comment. No recall quiz is required. The event, wording version, benchmark and dataset fingerprint are attached to feedback. Original feedback is preserved. Each realistic dataset has its own storage folder. Match reviewer/case/round only within one benchmark, dataset and survey protocol. Round 2 uses approved revisions or unchanged controls. Rating changes are descriptive self-reports, not objective comprehension, causal improvement or changes in detection accuracy.

## Sensitivity and limitations

The primary realistic run is fixed to seed 42. All configured additional seeds 43–46 are reported in the dashboard and evaluations/realistic-v1.json; no best seed is substituted for the primary run. These development simulations are not a blind external validation or hospital trial. Higher realism and separated test users do not establish clinical representativeness. Supervisor-approved papers and actual reviewer responses are still needed. No patient data is used.

## Reviewer presentation update — 20 November 2026

The reviewer list displays up to 20 cases in a fixed review set. This presentation limit does not change the detector, total flags, evaluation population or reported metrics. Cards count the displayed review cases. Case selection uses baseline severity, anomaly score and event ID before filtering, and stays the same across rounds. The benchmark controls and archived practice data are in Researcher tools, outside the reviewer flow. The main literature table groups Isolation Forest methods; the full method context and higher reported results remain available separately.
