# EHR Review Desk
          
Local Streamlit dashboard for reviewing unusual access patterns in synthetic electronic health record data. It generates 1,000 synthetic events, fits Isolation Forest, and displays plain-English alerts with Tree SHAP evidence and role baselines.

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

- Rehearsal uses `data/rehearsal/`. The real study uses `data/study/`. Each workspace has its own `feedback.csv` and `revisions.json`, created as needed.
- The ZIP starts with both workspaces empty. Older releases stored data in the root folder. Keep those files as archives and do not copy them into a new research workspace. Their responses predate version and questionnaire fixes.
- CSV responses are unique per reviewer code, case and round. Resubmitting a valid response for the same combination replaces the previous one. Keep backups of both files together when moving the study.
- If a file fails validation, the app reports the file and keeps the benchmark available. Writes for the affected workspace pause. Close the app, make a copy of the original file, restore a verified backup or repair the file, and reopen the app. Rehearsal and research data remain separate during recovery.

## Benchmark scope

The data contains no patient identifiers. Evaluation is on 250 held-out synthetic events with 25 injected anomalies. ROC-AUC uses continuous raw scores and the confusion matrix uses the configured threshold of 0.75. These metrics apply to the included synthetic dataset. Run `python pipeline.py` using the configured virtual environment to export the data and benchmark output.

The primary research focus is the translation and review of technical explanations. Published detection numbers in **Research context** are transcribed from different studies and cannot establish superiority on different datasets. Metrics are never capped or changed to meet a desired range. An always-normal reference already reaches 90% accuracy on this 90/10 test set, so anomaly precision, recall and the confusion matrix must be considered. The score is a relative anomaly index, not a probability.

The deterministic split can include the same users in training and test partitions. The synthetic anomalies are easily separable and no real-hospital generalization claim is supported. Candidate references are listed in [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md); the client's supervisor-approved papers can be added when supplied.

## Hosted reviewer preview

Streamlit Community Cloud can run `app.py` from this repository. Local CSV/JSON storage is suitable for a preview; hosted filesystem contents can be lost on a reboot or redeployment. Export feedback before updating the app and after review sessions. Durable study collection needs an external database or another persistent storage service. Participant/Researcher mode is a presentation setting, not authentication.

## Verify the update

Using the configured Python environment, run `python -m unittest discover -s tests -v`. The checks independently recompute benchmark metrics and exercise direct survey submission, legacy CSV compatibility, round/version safeguards and protocol-separated pairing.
