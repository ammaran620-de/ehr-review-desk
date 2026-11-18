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

## Rehearse the workflow

1. Leave **Data workspace** set to **Rehearsal**. Select a row in the severity-sorted **All alerts** table. Search by role, department, user, wording or event, and filter by severity or response status. The selected alert opens below the table with its plain-English wording, facts, raw SHAP values and role baseline. Case evidence can be exported as JSON.
2. Submit the five ratings and an optional comment using a practice reviewer code. Feedback is available immediately. No comprehension questions or case-code entry are required. The event and wording version are attached automatically, and a successfully used reviewer code is remembered for the browser session.
3. Open **Revision studio** and save a shorter, evidence-checked alert for Round 2 with a rationale. Select **Round 2**, open the same case, and submit feedback using the same code.
4. Open **Study results** to inspect matched responses and download the rehearsal CSV. Open **Model evaluation** for computed metrics, metric definitions, ROC curve, confusion matrix and downloadable per-event predictions. **Research context** provides linked candidate studies and a downloadable evaluation note, with explicit limits on comparisons.

## Collect actual feedback

1. Obtain the study owner's approval of recruitment, consent, participant codes and cases. Use **Reviewer study → Researcher** to manage case revisions and see results. The software doesn't recruit reviewers or provide account-based access control.
2. Switch to **Participant** before a reviewer starts. Select the assigned alert from the table in **Round 1**. The reviewer can immediately read the wording, inspect the evidence and submit ratings for clarity, completeness, severity fit, trust and perceived clarity compared with raw SHAP, plus an optional comment. Use a study-assigned anonymous reviewer code.
3. After Round 1, use **Researcher → Revision studio** to approve revised wording or severity with a documented rationale. Explicitly designate unchanged controls if the study uses them. Round 2 feedback is unavailable for any case with neither designation.
4. Run **Round 2** in Participant view using the same reviewer codes and assigned case IDs. If the wording changes while a form is open, the form resets and asks the reviewer to read the current wording. The evaluated case version is locked once Round 2 responses exist.
5. Use **Researcher → Study results** to review paired responses, distinguish revised cases from controls, and export the research CSV. Current ratings are self-reported perceptions, not objective comprehension scores. Results are descriptive and can be affected by repeated exposure and visible evidence. The `survey_protocol` field separates new `direct-review-v2` responses from legacy `quiz-v1` responses; the dashboard matches only within the selected protocol. Legacy quiz fields remain in the CSV and are blank for new responses. Do not enter patient data or identifiable reviewer information.

## Storage and recovery

- **Original demonstration** keeps `data/rehearsal/` and `data/study/` unchanged. **Realistic access patterns** uses `data/realistic-v1-<dataset-hash>/rehearsal/` and `/study/`. Each workspace has its own feedback and revisions. A changed dataset gets a different folder. Do not combine responses across these datasets. New CSV rows carry `benchmark_id` and `dataset_sha256`; older original CSVs remain readable.
- The ZIP starts with both workspaces empty. Older releases stored data in the root folder. Keep those files as archives and do not copy them into a new research workspace. Their responses predate version and questionnaire fixes.
- CSV responses are unique per reviewer code, case and round. Resubmitting a valid response for the same combination replaces the previous one. Keep backups of both files together when moving the study.
- If a file fails validation, the app reports the file and keeps the benchmark available. Writes for the affected workspace pause. Close the app, make a copy of the original file, restore a verified backup or repair the file, and reopen the app. Rehearsal and research data remain separate during recovery.

## Benchmark scope

The dashboard defaults to **Realistic access patterns (v1)**. Its fixed primary run uses seed 42, 1,000 events (900 legitimate/100 injected anomalies), 36 legitimate workflow exceptions and 25 subtle anomalies. GroupShuffleSplit holds out 19 of 75 users: 745 training events and 255 test events, including 27 anomalies. Test users do not appear in training. Labels and simulation context are excluded from fitting and splitting.

Measured primary results: **96.86% accuracy, 91.30% precision, 77.78% recall, 84.00% F1 and 0.9763 ROC-AUC**. Confusion matrix: TN 226, FP 2, FN 6, TP 21. The always-normal reference has 89.41% accuracy and zero anomaly recall. The protocol was configured before its metrics were inspected and remains fixed even though its primary accuracy is outside a desired 93–95% range. It is a documented development simulation, not a registered or blind hospital experiment.

All configured seeds 42–46 are retained in the dashboard and [evaluation evidence](evaluations/realistic-v1.json). Their accuracy ranges from 94.05% to 97.23%. These are complete synthetic sensitivity results, not justification to select a more convenient seed. See [REALISTIC_PROTOCOL.md](REALISTIC_PROTOCOL.md) for assumptions. Rebuild the evidence with `python evaluate_benchmarks.py`.

**Original demonstration (v1)** remains selectable and preserves the original data, events, scores and feedback. Its 250-event test set has 25 anomalies and 98.8% accuracy; users overlap between training and test. The two datasets differ, so a lower or higher metric across them is not evidence of model improvement.

Both use Isolation Forest without training labels, Tree SHAP, the fixed threshold >0.75 and raw-score ROC-AUC. The displayed score is a relative anomaly index, not a calibrated probability. `python pipeline.py` exports the realistic benchmark; use `python pipeline.py --benchmark reference-v1` for the original. Calling `run_pipeline()` without arguments retains the original benchmark for existing integrations.

The research focus is understandable alerts and reviewer feedback. [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md) lists recent references including Chua (2024, 93% accuracy on web logs) and Abengowe (published 2025, Linear SVC 92% in Table 2 but 93% in prose; other models reach 98%). Their data differs from ours. Higher reported EHR results remain visible too. The IEEE BigData 2025 abstract describes human-readable EHR rationales, but no unverified accuracy is assigned to it. The older 2019 SHAP study is labelled as foundational background rather than a recent numerical comparator.

Neither numerical superiority over these papers nor real-hospital performance has been demonstrated. A same-data comparison and actual reviewer evidence are required. Patient data is not used.

## Hosted reviewer preview

Streamlit Community Cloud can run `app.py` from this repository. Local CSV/JSON storage is suitable for a preview; hosted filesystem contents can be lost on a reboot or redeployment. Export feedback before updating the app and after review sessions. Durable study collection needs an external database or another persistent storage service. Participant/Researcher mode is a presentation setting, not authentication.

## Verify the update

Using the configured Python environment, run `python -m unittest discover -s tests -v`. The checks independently recompute benchmark metrics and exercise direct survey submission, legacy CSV compatibility, round/version safeguards and protocol-separated pairing.


## Licence

The code is released under the MIT licence (`LICENSE`). The records the app analyses are synthetic and generated by the code in this repository. Dependencies (Streamlit, scikit-learn, SHAP and others) keep their own licences.
