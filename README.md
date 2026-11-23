# EHR Review Desk
          
Local Streamlit dashboard for reviewing unusual access patterns in synthetic electronic health record data. It generates 1,000 synthetic events, fits Isolation Forest, and displays plain-English alerts with Tree SHAP evidence and role baselines.

[![tests](https://github.com/ammaran620-de/ehr-review-desk/actions/workflows/tests.yml/badge.svg)](https://github.com/ammaran620-de/ehr-review-desk/actions/workflows/tests.yml)

**Scope.** Everything here runs on synthetic data: 1,000 generated events, no patient identifiers, and no claim about real hospitals. Alert scores come from Isolation Forest and are not calibrated probabilities. The detection numbers cover the included synthetic set only (see Benchmark scope below).

## Quick start (macOS, Linux)

Use Python 3.12.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Then open the address Streamlit prints, usually `http://127.0.0.1:8501`. Run the checks with `.venv/bin/python -m unittest discover -s tests -v`. The suite covers benchmark arithmetic, unsupervised fitting, user separation, dataset isolation and reviewer workflows. Windows users can use the launcher below.

## Start on Windows

Extract the whole ZIP into a writable folder. With 64-bit Python 3.12 installed, double-click `Start_EHR_Review_Desk.cmd`. The launcher reuses a working `.venv312` and can find Python through the Windows launcher, standard installation paths, or a Python 3.12 command on PATH. The first dependency installation requires internet access.

When the terminal prints the local URL, open it in your browser and leave the terminal running. The usual address is `http://127.0.0.1:8501`. Use Ctrl+C in the terminal to stop the server.

If the launcher cannot find a Python 3.12 installed in a custom location, open PowerShell in the extracted folder and adjust the first line to that installation's exact executable path:

```powershell
$python312 = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
& $python312 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv312\Scripts\python.exe -m streamlit run app.py --server.headless true
```

If the existing `.venv312` is damaged, rename it before rebuilding. For an installation on macOS or Linux, create a Python 3.12 virtual environment and use its `bin/python` with the same pip and Streamlit module commands. The software is designed for trusted local use and binds to loopback.

## Review alerts

1. Open the dashboard. The default reviewer screen has **Alert review**, **Model evaluation**, **Research context** and **Revision Studio**. It has no Rehearsal radio, Participant/Researcher selector or benchmark selector.
2. **Alerts for review** shows a fixed set of up to **20 flagged cases**, interleaved across High, Medium and Low priority. The default benchmark shows 7 High, 8 Medium and 5 Low cases. Isolated volume signals during the expected shift and in the assigned department can be Low priority. Search and filters apply within those same 20 cases across both rounds. Researcher tools can inspect all model flags separately; the total model flags and benchmark metrics are unchanged. These synthetic flags are investigation candidates, not confirmed hospital incidents.
3. Select a row to open its plain-English explanation, raw SHAP values, role baseline and direct feedback form. Supply your anonymous reviewer code, five ratings and an optional comment. The selected event, round, dataset and wording version attach automatically.
4. Use the same reviewer code, dataset and cases in Round 2. The case must first have an approved revision or an explicit unchanged-control designation.

## Researcher tools

Open the sidebar and turn on **Researcher tools** to see **Role baselines**, **Study results** and **Revision studio**. Reviewers submit responses; the researcher analyzes paired responses, exports CSV and approves Round 2 wording. This is a navigation setting, not authentication.

- **Dataset settings and archives** contains the benchmark selector. It chooses synthetic logs used to train and evaluate the model, not patient data. Keep the same dataset throughout both study rounds.
- Earlier practice files can be accessed with **Open archived practice responses**. They stay separate from study feedback; practice is no longer part of the reviewer-facing flow.
- **Revision Studio** is visible from the main navigation. Open its tab and click **Open Revision Studio** to enable the researcher controls. It preserves Round 1 wording, records a rationale and requires an evidence check. Cases are locked against revision after Round 2 responses exist.
- **Study results** compares the same reviewer/case within one dataset and survey protocol. Ratings measure perceived clarity, completeness, severity fit, trust and clarity relative to SHAP; they do not prove objective comprehension or causal improvement. Historical quiz responses stay separate.
- **Research context** shows three rows in one table: this prototype, Abengowe et al. (Linear SVC) and Chua et al. (Isolation Forest). Different data and protocols prevent a direct superiority claim.

## Storage and recovery

- **Original demonstration** keeps `data/rehearsal/` and `data/study/` unchanged. **Realistic access patterns** uses `data/realistic-v1-<dataset-hash>/rehearsal/` and `/study/`. Each workspace has its own feedback and revisions. A changed dataset gets a different folder. Do not combine responses across these datasets. New CSV rows carry `benchmark_id` and `dataset_sha256`; older original CSVs remain readable.
- The ZIP starts with both workspaces empty. Older releases stored data in the root folder. Keep those files as archives and do not copy them into a new research workspace. Their responses predate version and questionnaire fixes.
- CSV responses are unique per reviewer code, case and round. Resubmitting a valid response for the same combination replaces the previous one. Keep backups of both files together when moving the study.
- If a file fails validation, the app reports the file and keeps the benchmark available. Writes for the affected workspace pause. Close the app, make a copy of the original file, restore a verified backup or repair the file, and reopen the app. Rehearsal and research data remain separate during recovery.

## Benchmark scope

The dashboard defaults to **Realistic access patterns (v1)**. Its fixed primary run uses seed 42, 1,000 events (900 legitimate/100 injected anomalies), 36 legitimate workflow exceptions and 25 subtle anomalies. GroupShuffleSplit holds out 19 of 75 users: 745 training events and 255 test events, including 27 anomalies. Test users do not appear in training. Labels and simulation context are excluded from fitting and splitting.

Measured primary results: **96.86% accuracy, 91.30% precision, 77.78% recall, 84.00% F1 and 0.9763 ROC-AUC**. Confusion matrix: TN 226, FP 2, FN 6, TP 21. The always-normal reference has 89.41% accuracy and zero anomaly recall. The protocol was configured before its metrics were inspected and remains fixed even though its primary accuracy is outside a desired 93–95% range. It is a documented development simulation, not a registered or blind hospital experiment.

All configured seeds 42–46 are retained in the dashboard and [evaluation evidence](evaluations/realistic-v1.json). Their accuracy ranges from 94.05% to 97.23%. These are complete synthetic sensitivity results, not justification to select a more convenient seed. See [REALISTIC_PROTOCOL.md](REALISTIC_PROTOCOL.md) for assumptions. Rebuild the evidence with `python evaluate_benchmarks.py`.

**Original demonstration (v1)** remains selectable through Researcher tools and preserves the original data, events, scores and feedback. Its 250-event test set has 25 anomalies and 98.8% accuracy; users overlap between training and test. The two datasets differ, so a lower or higher metric across them is not evidence of model improvement.

Both use Isolation Forest without training labels, Tree SHAP, the fixed threshold >0.75 and raw-score ROC-AUC. The displayed score is a relative anomaly index, not a calibrated probability. `python pipeline.py` exports the realistic benchmark; use `python pipeline.py --benchmark reference-v1` for the original. Calling `run_pipeline()` without arguments retains the original benchmark for existing integrations.

The research focus is understandable alerts and reviewer feedback. [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md) lists recent references including Chua (2024, 93% accuracy on web logs) and Abengowe (published 2025, Linear SVC 92% in Table 2 but 93% in prose; other models reach 98%). Their data differs from ours. Higher reported EHR results remain visible too. The IEEE BigData 2025 abstract describes human-readable EHR rationales, but no unverified accuracy is assigned to it. The older 2019 SHAP study is labelled as foundational background rather than a recent numerical comparator.

Neither numerical superiority over these papers nor real-hospital performance has been demonstrated. A same-data comparison and actual reviewer evidence are required. Patient data is not used.

## Hosted reviewer preview

Streamlit Community Cloud can run `app.py` from this repository. Local CSV/JSON storage is suitable for a preview; hosted filesystem contents can be lost on a reboot or redeployment. Export feedback before updating the app and after review sessions. Durable study collection needs an external database or another persistent storage service. Researcher tools is a navigation setting, not authentication.

## Verify the update

Using the configured Python environment, run `python -m unittest discover -s tests -v`. The checks independently recompute benchmark metrics and exercise direct survey submission, legacy CSV compatibility, round/version safeguards and protocol-separated pairing.


## Licence

The code is released under the MIT licence (`LICENSE`). The records the app analyses are synthetic and generated by the code in this repository. Dependencies (Streamlit, scikit-learn, SHAP and others) keep their own licences.
