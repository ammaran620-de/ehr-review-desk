# Realistic benchmark protocol v1

Configured on 18 November 2026 before inspecting its metrics. This is a versioned development protocol, not a formally preregistered experiment.

- Generate 1,000 synthetic events: 900 legitimate and 100 injected anomalies.
- Give 36 legitimate events authorized overtime, temporary department cover, or a workload surge (12 of each). This deliberately permits behavioral overlap with anomalies. Authorization is simulation ground truth, not an input feature.
- Give 25 of the 100 anomalies milder deviations. Keep the illustrative combined event EVT-0903.
- Use the existing seven observed access features, 120 Isolation Forest trees, and the existing training-only score normalization and fixed threshold >0.75. No target accuracy is an input to fitting or evaluation.
- Hold out approximately 25% of the 75 users using GroupShuffleSplit. All events for one user stay in one partition. Labels do not determine the split or model fitting.
- Primary run: seed 42. Report all additional fixed seeds 43, 44, 45 and 46 as sensitivity checks; do not choose the best seed.
- Derive role means from the defined policy midpoint, without reading test labels.
- Report the confusion matrix, anomaly precision/recall/F1, accuracy, raw-score ROC-AUC, class prevalence, and an always-normal reference. Release per-event test predictions and partition identifiers for reproducibility.
- Treat all results as synthetic simulation evidence. Changing generator realism makes this a different benchmark, not a demonstrated improvement over the old dataset or a published paper.
- Store new reviews under a benchmark-and-dataset-specific folder. Keep original benchmark feedback under its existing paths.
