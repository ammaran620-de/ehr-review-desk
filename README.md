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

1. Leave **Data workspace** set to **Rehearsal**. Select a color-coded event from **Alert review**. The demo case `EVT-0903` shows why an after-hours receptionist access was flagged. Explore the facts, plain-English wording, raw SHAP values and role baseline, and export evidence as JSON.
2. Answer the two interpretation questions and submit the ratings using a practice reviewer code. Rehearsal displays the supporting evidence immediately.
3. Open **Revision studio** and save a shorter, evidence-checked alert for Round 2 with a rationale. Select **Round 2**, open the same case, and submit feedback using the same code.
4. Open **Study results** to inspect matched responses and download the rehearsal CSV. Open **Model evaluation** for the held-out metrics, ROC curve, confusion matrix, score distribution and SHAP summary.

## Collect actual feedback

1. Obtain the study owner's approval of recruitment, consent, participant codes and cases. Use **Reviewer study → Researcher** to manage case revisions and see results. The software doesn't recruit reviewers or provide account-based access control.
2. Switch to **Participant** before a reviewer starts. In the same case list, open the assigned case ID in **Round 1**. The screen presents the wording first. Both interpretation answers are locked before it reveals severity, observed values, SHAP and the role baseline. The reviewer then rates clarity, evidence, severity, trust and comparative clarity versus raw SHAP, and can leave a comment.
3. After Round 1, use **Researcher → Revision studio** to approve revised wording or severity with a documented rationale. Explicitly designate unchanged controls if the study uses them. Round 2 feedback is unavailable for any case with neither designation.
4. Run **Round 2** in Participant view using the same reviewer codes and assigned case IDs. If the wording changes while a form is open, the form resets and asks the reviewer to read the current wording. The evaluated case version is locked once Round 2 responses exist.
5. Use **Researcher → Study results** to review paired responses, distinguish revised cases from controls, and export the research CSV. Results from the two rounds are descriptive and should be interpreted in light of repeated exposure and the synthetic data. Do not enter patient data or identifiable reviewer information.

## Storage and recovery

- Rehearsal uses `data/rehearsal/`. The real study uses `data/study/`. Each workspace has its own `feedback.csv` and `revisions.json`, created as needed.
- The ZIP starts with both workspaces empty. Older releases stored data in the root folder. Keep those files as archives and do not copy them into a new research workspace. Their responses predate version and questionnaire fixes.
- CSV responses are unique per reviewer code, case and round. Resubmitting a valid response for the same combination replaces the previous one. Keep backups of both files together when moving the study.
- If a file fails validation, the app reports the file and keeps the benchmark available. Writes for the affected workspace pause. Close the app, make a copy of the original file, restore a verified backup or repair the file, and reopen the app. Rehearsal and research data remain separate during recovery.

## Benchmark scope

The data contains no patient identifiers. Evaluation is on 250 held-out synthetic events with 25 injected anomalies. ROC-AUC uses continuous raw scores and the confusion matrix uses the configured threshold of 0.75. These metrics apply to the included synthetic dataset. Run `python pipeline.py` using the configured virtual environment to export the data and benchmark output.
