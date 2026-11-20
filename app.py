"""Streamlit workbench for synthetic EHR alert review."""
from pathlib import Path
from collections import Counter
from html import escape
import hashlib
import json
import re

import altair as alt
import pandas as pd
import streamlit as st
from filelock import FileLock

from feedback import read_feedback, save_feedback
from revision_store import load_revisions, save_revision
from pipeline import run_pipeline
from research_context import REFERENCES, comparison_rows, evaluation_report
from review_presentation import PAGE_SIZE, alert_page, page_count

ROOT = Path(__file__).resolve().parent
SEVERITY = {'High': 0, 'Medium': 1, 'Low': 2}
TEMPLATES = {'Combined anomaly', 'Burst behavior', 'Excessive access',
             'Off-hours access', 'Role mismatch', 'Unassigned access', 'Fallback'}
RATINGS = {'clarity': 'Was this alert clear?', 'completeness': 'Was the evidence complete?',
           'severity_fit': 'Was the severity appropriate?', 'trust': 'Would you trust this alert to guide a review?',
           'shap_clarity': 'Was the plain-English alert clearer than the raw SHAP values?'}
COLORS = {'High': '#A7284B', 'Medium': '#915016', 'Low': '#244AA3'}
SCORE_LABELS = ['Precision', 'Recall', 'F1 score', 'Accuracy', 'ROC-AUC']

st.set_page_config(page_title='EHR Review Desk', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')
st.html(f"<style>{(ROOT / 'interface.css').read_text(encoding='utf-8')}</style>")
st.html('<div class="hero"><div class="brandline">Clinical access analytics · research workspace</div>'
        '<h1>EHR Review Desk</h1><p>Triage access alerts, inspect the supporting evidence, and record reviewer decisions.</p></div>')

@st.cache_data(show_spinner='Python is generating events, model scores and SHAP explanations…')
def baseline_run(pipeline_digest, benchmark):
    return run_pipeline(benchmark)

@st.cache_data(show_spinner='Running all five configured sensitivity seeds…')
def robustness_run(pipeline_digest):
    from realistic_pipeline import sensitivity_runs
    return sensitivity_runs()

def copy_for(row, round_number, revisions):
    alert = row['alert']
    severity = alert['severity']
    revision = revisions.get(row['id']) if round_number == 2 else None
    if revision and not revision.get('control'):
        message, severity = revision['message'], revision['severity']
        version = 'r2-' + hashlib.sha256(f'{message}|{severity}'.encode()).hexdigest()[:12]
        return message, severity, version
    return alert['message'], severity, 'baseline-v1'

benchmarks = {'Realistic access patterns (v1)': 'realistic-v1', 'Original demonstration (v1)': 'reference-v1'}
benchmark = st.session_state.get('active_benchmark', 'realistic-v1')
with st.sidebar:
    st.subheader('Study tools')
    researcher_mode = st.toggle('Researcher tools', value=False,
        help='Open dataset settings, study results and the Round 2 revision studio.')
    st.caption('Reviewers read alerts and submit feedback. Researcher tools manage the study and approved revisions. This navigation switch is not a login or access restriction.')
    archived_practice = False
    if researcher_mode:
        with st.expander('Dataset settings and archives', expanded=False):
            benchmark = benchmarks[st.selectbox('Benchmark dataset', list(benchmarks),
                index=list(benchmarks.values()).index(benchmark),
                help='Synthetic access logs used to train Isolation Forest and calculate evaluation metrics; these are not patient records.')]
            st.session_state.active_benchmark = benchmark
            st.caption('Keep one dataset for both review rounds. Changing it opens a separate feedback store.')
            archived_practice = st.checkbox('Open archived practice responses', value=False,
                help='Access earlier rehearsal files separately from the reviewer study. Practice data is excluded from the study.')
        if st.button('Run Python pipeline', type='primary'):
            baseline_run.clear()
pipeline_digest = hashlib.sha256(b''.join((ROOT / name).read_bytes()
    for name in ('pipeline.py', 'reference_pipeline.py', 'realistic_pipeline.py', 'translation.py'))).hexdigest()
result = baseline_run(pipeline_digest, benchmark)
metadata = result['metadata']
workspace = 'Rehearsal' if researcher_mode and archived_practice else 'Reviewer study'
storage_root = ROOT / 'data'
if benchmark != 'reference-v1':
    storage_root /= f"{benchmark}-{metadata['dataset_sha256'][:12]}"
workspace_key = f"{benchmark}_{metadata['dataset_sha256'][:12]}_{workspace}"
workspace_dir = storage_root / ('rehearsal' if workspace == 'Rehearsal' else 'study')
FEEDBACK, REVISIONS, STUDY_LOCK = (workspace_dir / name for name in
                                   ('feedback.csv', 'revisions.json', '.study.lock'))
storage_errors = []
try:
    revisions = load_revisions(REVISIONS)
except (ValueError, OSError) as exc:
    revisions = {}
    storage_errors.append(f'{REVISIONS.name}: {exc}')
try:
    feedback = read_feedback(FEEDBACK)
    if any(item['benchmark_id'] != benchmark or
           (item['dataset_sha256'] != metadata['dataset_sha256'] and
            (benchmark != 'reference-v1' or item['dataset_sha256'])) for item in feedback):
        raise ValueError('Feedback belongs to another benchmark or dataset. Keep its original file as an archive.')
except (ValueError, OSError) as exc:
    feedback = []
    storage_errors.append(f'{FEEDBACK.name}: {exc}')
if storage_errors:
    st.error(f'{workspace} storage requires attention. Files were preserved. '
             'Review and repair the following files or restore a verified backup before saving. '
             + ' | '.join(storage_errors))
    st.code(str(workspace_dir), language=None)
rows = result['rows']
flagged = [row for row in rows if row['flagged']]
st.caption('Synthetic research preview · alerts are candidates for investigation, not confirmed security incidents.')
if researcher_mode:
    with st.sidebar:
        st.caption(f"{len(rows):,} synthetic events · {len(flagged)} total model flags · threshold >0.75. The simulation injects 100 anomalies; its flag rate is not a hospital incident rate.")
        if archived_practice:
            st.warning('Archived practice data is open. Switch this off before collecting study responses.')
    alerts_tab, evaluation_tab, research_tab, policy_tab, study_tab, revisions_tab = st.tabs(
        ['Alert review', 'Model evaluation', 'Research context', 'Role baselines', 'Study results', 'Revision studio'])
else:
    alerts_tab, evaluation_tab, research_tab = st.tabs(['Alert review', 'Model evaluation', 'Research context'])
if 'saved_feedback' in st.session_state:
    st.success(st.session_state.pop('saved_feedback'))


with alerts_tab:
    round_name = st.radio('Study round', ['Round 1', 'Round 2'], horizontal=True)
    round_number = 1 if round_name == 'Round 1' else 2
    if round_number == 2 and not revisions:
        st.info('Approve a revision or designate an unchanged control in Revision studio before collecting Round 2 feedback.')
    with st.container(key='alert_queue'):
        st.markdown('<div class="sectiontag">01 / ALERT REGISTER</div>', unsafe_allow_html=True)
        st.subheader('Alerts for review')
        st.caption('Review up to 20 alerts per page. Select a row for its explanation, SHAP evidence, role baseline and feedback form. On a phone, swipe the table sideways for more columns.')
        filters = st.columns([1, 2, 1])
        severity_filter = filters[0].selectbox('Severity', ['All', *SEVERITY])
        query = filters[1].text_input('Search alerts', placeholder='Search role, department, user or event').strip().casefold()
        queue_status = filters[2].selectbox('Review status', ['All alerts', 'Awaiting a response', 'Has a response'])
        completed = {item['event'] for item in feedback if item['round'] == str(round_number)}
        ordered = sorted(flagged, key=lambda r: (SEVERITY[copy_for(r, round_number, revisions)[1]], -r['score'], r['id']))
        visible = [r for r in ordered if (severity_filter == 'All' or copy_for(r, round_number, revisions)[1] == severity_filter)
                   and query in ' '.join((r['id'], r['role'], r['user_id'], r['department_accessed'],
                                          copy_for(r, round_number, revisions)[0])).casefold()
                   and (queue_status == 'All alerts' or (r['id'] in completed) == (queue_status == 'Has a response'))]
        pages = page_count(visible)
        filter_signature = hashlib.sha256('|'.join(r['id'] for r in visible).encode()).hexdigest()[:12]
        current_page = st.selectbox('Alert page', list(range(1, pages + 1)),
            format_func=lambda number: f'Page {number} of {pages}',
            key=f'page_{workspace_key}_{round_number}_{filter_signature}')
        page_rows = alert_page(visible, current_page)
        page_counts = Counter(copy_for(r, round_number, revisions)[1] for r in page_rows)
        page_reviewed = len({r['id'] for r in page_rows} & completed)
        summary = [('Alerts on this page', len(page_rows)), ('High severity on page', page_counts['High']),
                   ('Reviewed on page', page_reviewed)]
        st.html('<div class="overview-strip review-summary">' + ''.join(
            f'<div><span class="queue-label">{label}</span><strong>{value:,}</strong></div>'
            for label, value in summary) + '</div>')
        st.caption(f'{len(page_rows)} alerts on this page · sorted by severity, then score. '
                   'Pagination changes the display only; model results and evaluation remain unchanged. '
                   'Response status includes any reviewer in this study round.')
        if page_rows:
            register = pd.DataFrame([{
                'Severity': copy_for(r, round_number, revisions)[1], 'Event': r['id'],
                'Role': r['role'], 'Department': r['department_accessed'],
                'Time': f'{r["date"]} {r["login_time"]}',
                'Alert summary': copy_for(r, round_number, revisions)[0].splitlines()[0],
                'Response': 'Received' if r['id'] in completed else 'Awaiting',
            } for r in page_rows])
            def severity_style(value):
                backgrounds = {'High': '#f8e0e4', 'Medium': '#faecd3', 'Low': '#e0eaf5'}
                return f'background-color: {backgrounds[value]}; color: {COLORS[value]}; font-weight: bold'
            # A changed row order gets a fresh widget, so a stale row index cannot open a different case.
            signature = hashlib.sha256(json.dumps(register.to_dict('records'), sort_keys=True).encode()).hexdigest()[:12]
            default_id = st.session_state.get('selected_event', 'EVT-0903')
            default_index = next((i for i, r in enumerate(page_rows) if r['id'] == default_id), 0)
            selection = st.dataframe(register.style.map(severity_style, subset=['Severity']),
                hide_index=True, width='stretch', height=min(425, 40 + 36 * len(page_rows)),
                row_height=36, key=f'register_{workspace_key}_{round_number}_{signature}',
                on_select='rerun', selection_mode='single-row',
                selection_default={'selection': {'rows': [default_index], 'columns': [], 'cells': []}},
                column_config={'Event': st.column_config.TextColumn(width='small'),
                    'Severity': st.column_config.TextColumn(width='small'),
                    'Alert summary': st.column_config.TextColumn(width='large')})
            if selection.selection.rows:
                st.session_state.selected_event = page_rows[selection.selection.rows[0]]['id']
    with st.container(key='alert_detail'):
        if not page_rows:
            st.info('No alerts match the current filters.')
        else:
            selected = st.session_state.get('selected_event', 'EVT-0903')
            row = next((r for r in page_rows if r['id'] == selected), page_rows[0])
            message, severity, version = copy_for(row, round_number, revisions)
            policy = next(b for b in result['baselines'] if b[0] == row['role'])
            event_id = row['id']
            case_slot = (workspace_key, event_id, round_number)
            form_identity = f'{workspace_key}_{event_id}_{round_number}_{version}'
            # Store the displayed version separately from the value loaded on this rerun.
            previous = st.session_state.setdefault('displayed_versions', {}).get(case_slot)
            if previous is not None and previous != version:
                st.warning('This alert changed while it was open. Previous answers were discarded. Review the current wording before submitting again.')
            st.session_state['displayed_versions'][case_slot] = version
            unlocked = round_number == 1 or event_id in revisions
            can_write = not storage_errors and unlocked
            if round_number == 2 and not unlocked:
                st.info('This case needs an approved revision or unchanged-control designation before Round 2 feedback can be saved.')
            st.markdown('<div class="sectiontag">02 / EVENT DETAIL</div>', unsafe_allow_html=True)
            st.subheader(f'{event_id} · {row["role"]}')
            st.caption(f'{round_name} · {version}')
            with st.container(key='alert_message'):
                st.markdown('#### Plain-English alert')
                st.html(f'<p class="alert-copy">{escape(message)}</p>')

            st.html(f'<span class="pill {severity}">{severity} severity</span>')
            st.caption(f'{row["alert"]["template"]} · {row["date"]} at {row["login_time"]} · Score {row["score"]:.3f}')
            facts = [('Records accessed', str(row['records_accessed'])),
                     ('Accessed department', row['department_accessed']),
                     ('Session duration', f'{row["session_duration_mins"]} min')]
            st.html('<div class="case-summary">' + ''.join(
                f'<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
                for label, value in facts) + '</div>')
            evidence = {key: row[key] for key in ('id', 'user_id', 'role', 'date', 'login_time',
                        'records_accessed', 'session_duration_mins', 'department_accessed', 'assigned_department', 'score')}
            evidence.update({'benchmark_id': benchmark, 'dataset_sha256': metadata['dataset_sha256'],
                             'severity': severity, 'alert_version': version, 'alert_message': message,
                             'raw_shap': dict(zip(result['features'], (-value for value in row['shap']))),
                             'role_baseline': {'shift': policy[1:3], 'daily_range': policy[3:5],
                                               'mean_daily_records': row['baseline'], 'allowed_departments': policy[5]}})
            st.download_button('Export case evidence', json.dumps(evidence, ensure_ascii=False, indent=2),
                               file_name=f'{row["id"]}-{version}.json', mime='application/json')
            st.caption(f'Alert readability check · {len(re.findall(r"\b\w+\b", message))} words · read the alert before consulting the evidence below.')
            with st.expander('Raw SHAP values and role baseline', expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    shap_frame = pd.DataFrame({'Feature': result['features'],
                       'Raw SHAP': [-value for value in row['shap']],
                       'Level': [row['alert']['levels'][f] for f in result['features']]})
                    st.dataframe(shap_frame.sort_values('Raw SHAP').style.format({'Raw SHAP': '{:+.6f}'}),
                                 hide_index=True, width='stretch')
                    st.caption('Raw SHAP explains path length. More negative values support anomaly. Levels use the opposite sign.')
                with c2:
                    _, start, end, lo, hi, depts = policy
                    st.markdown('**Expected workflow**')
                    st.write(f'{start:02}:00–{end:02}:00 · {lo}–{hi} records/day')
                    st.write(f'Mean {row["baseline"]:.2f} records/day · {", ".join(depts)}')
                    st.markdown('**Observed event**')
                    st.write(f'{row["user_id"]} · {row["records_accessed"]} records · {row["session_duration_mins"]} min')
                    st.write(f'Accessed {row["department_accessed"]} · assigned {row["assigned_department"]}')
            if can_write:
                with st.container(key='feedback_panel'):
                    st.markdown('<div class="sectiontag">03 / IT REVIEW</div>', unsafe_allow_html=True)
                    st.markdown('#### Rate this alert')
                    st.caption(f'Feedback is automatically linked to {event_id} · {round_name}. Use the same reviewer code in both rounds.')
                    with st.form(f'feedback_{form_identity}'):
                        reviewer = st.text_input('Reviewer code', max_chars=32, placeholder='e.g. IT01',
                                                 value=st.session_state.get(f'last_reviewer_{workspace_key}', ''))
                        st.caption('Scale: 1 strongly disagree · 5 strongly agree')
                        left, right = st.columns(2)
                        ratings = {key: (left if i % 2 == 0 else right).selectbox(label, [1, 2, 3, 4, 5], index=None)
                                   for i, (key, label) in enumerate(RATINGS.items())}
                        comment = st.text_area('Comments', max_chars=1000, placeholder='What was unclear or missing?')
                        if st.form_submit_button('Save reviewer feedback', type='primary'):
                            if not re.fullmatch(r'[A-Za-z0-9_-]{2,32}', reviewer.strip()) or None in ratings.values():
                                st.error('Enter a valid reviewer code and every rating.')
                            else:
                                safe_comment = "'" + comment if comment.lstrip().startswith(('=', '+', '-', '@')) else comment
                                try:
                                    workspace_dir.mkdir(parents=True, exist_ok=True)
                                    with FileLock(STUDY_LOCK, timeout=10):
                                        latest_revisions = load_revisions(REVISIONS)
                                        latest_version = copy_for(row, round_number, latest_revisions)[2]
                                        if latest_version != version or (round_number == 2 and event_id not in latest_revisions):
                                            raise ValueError('The alert changed while you were reviewing it. Reopen the case and rate the current version.')
                                        save_feedback(FEEDBACK, dict(reviewer=reviewer.strip().casefold(), event=event_id,
                                            round=round_number, version=version, severity=severity, template=row['alert']['template'],
                                            benchmark_id=benchmark, dataset_sha256=metadata['dataset_sha256'],
                                            **ratings, interpretation_correct='', comment=safe_comment))
                                except (OSError, TimeoutError, ValueError) as exc:
                                    st.error(f'Could not save feedback: {exc}')
                                else:
                                    st.session_state[f'last_reviewer_{workspace_key}'] = reviewer.strip()
                                    st.session_state['saved_feedback'] = f'Saved {round_name} feedback for {event_id} in {workspace}.'
                                    st.rerun()

with evaluation_tab:
    st.subheader('Held-out benchmark')
    st.caption(f"{metadata['test_count']} held-out synthetic events · {metadata['test_anomalies']} injected anomalies · threshold >0.75")
    for column, label, value in zip(st.columns(5), SCORE_LABELS, result['metrics']):
        column.metric(label, f'{value:.3f}' if label == 'ROC-AUC' else f'{value:.1%}')
    tn, fp = result['cm'][0]
    fn, tp = result['cm'][1]
    st.info(f'Precision and accuracy measure different things. This run has {tp} detected anomalies, '
            f'{fp} false alarms, {fn} missed anomalies and {tn} correctly cleared normal events. '
            f"An always-normal prediction would achieve {metadata['majority_accuracy']:.1%} accuracy here while missing every anomaly.")
    st.caption('These results describe the selected synthetic test set; they are not hospital validation. '
               'Labels are used for evaluation only. The anomaly score is a relative index, not a probability.')
    with st.expander('Metric definitions and reproducibility'):
        st.markdown('- **Precision** — of the events flagged, how many were injected anomalies?\n'
                    '- **Recall** — of all injected anomalies, how many were flagged?\n'
                    '- **F1** — harmonic mean of precision and recall.\n'
                    '- **Accuracy** — correct decisions across normal and anomalous events.\n'
                    '- **ROC-AUC** — ranking performance across thresholds using raw continuous scores.')
        st.json(result['metadata'])
        st.caption(metadata['split'] + '. Synthetic testing does not establish performance in a real hospital.')
    st.download_button('Download benchmark evidence',
        json.dumps({k: result[k] for k in ('metadata', 'metrics', 'cm', 'test_predictions')}, indent=2),
        f'{benchmark}_evidence.json', 'application/json')
    if benchmark == 'realistic-v1':
        with st.expander('Sensitivity across all five configured seeds', expanded=True):
            sensitivity = pd.DataFrame(robustness_run(pipeline_digest))
            st.caption('Seed 42 is the primary result above. Every configured seed is shown; none is chosen to obtain a desired percentage. Seeds vary synthetic generation, user split and forest randomness.')
            st.dataframe(sensitivity.style.format({name: '{:.1%}' for name in
                ('precision', 'recall', 'f1', 'accuracy', 'roc_auc')}), hide_index=True, width='stretch')
            st.download_button('Download all sensitivity runs', sensitivity.to_csv(index=False),
                               'realistic-v1_sensitivity.csv', 'text/csv')
    charts = st.columns(2)
    with charts[0]:
        st.markdown('**ROC curve · continuous raw scores**')
        roc = pd.DataFrame({'False positive rate': result['roc'][0], 'True positive rate': result['roc'][1]})
        st.altair_chart(alt.Chart(roc).mark_line(color='#126754', strokeWidth=3).encode(
            x='False positive rate:Q', y='True positive rate:Q', tooltip=list(roc)), width='stretch')
    with charts[1]:
        st.markdown('**Confusion matrix · thresholded decisions**')
        st.dataframe(pd.DataFrame(result['cm'], index=['Actual normal', 'Actual anomaly'],
                                  columns=['Predicted normal', 'Predicted anomaly']), width='stretch')
        st.markdown('**Missed cases by injected scenario**')
        missed = pd.DataFrame([dict(Event=r['id'], Scenario=r['scenario'], Score=r['score'])
                               for r in rows if r['held_out'] and r['label'] and not r['flagged']])
        st.dataframe(missed, hide_index=True, width='stretch')
    a, b = st.columns(2)
    with a:
        st.markdown('**Held-out score distribution**')
        distribution = pd.DataFrame({'Score': [r['score'] for r in rows if r['held_out']]})
        histogram = alt.Chart(distribution).mark_bar(color='#126754').encode(
            x=alt.X('Score:Q', bin=alt.Bin(maxbins=20)), y='count()')
        cut = alt.Chart(pd.DataFrame({'Threshold': [.75]})).mark_rule(color='#A7284B', strokeDash=[5,4], strokeWidth=2).encode(x='Threshold:Q')
        st.altair_chart(histogram + cut, width='stretch')
    with b:
        st.markdown('**SHAP contribution summary · flagged events**')
        attributions = pd.DataFrame([r['shap'] for r in flagged], columns=result['features']).abs().mean()
        factors = attributions.rename('Mean absolute SHAP').rename_axis('Feature').reset_index()
        st.altair_chart(alt.Chart(factors).mark_bar(color='#126754').encode(
            x='Mean absolute SHAP:Q', y=alt.Y('Feature:N', sort='-x'), tooltip=list(factors)), width='stretch')

with research_tab:
    st.subheader('Research context')
    st.markdown('This project focuses on translating technical anomaly explanations into understandable alerts, '
                'then refining the wording using reviewer feedback. Detection performance and explanation usefulness are evaluated separately.')
    st.warning('These published results use different data and methods. The table provides context; '
               'it cannot establish that this prototype is better or worse. A fair performance comparison needs the same dataset, labels and test protocol.')
    st.markdown('**Isolation Forest method context**')
    st.dataframe(pd.DataFrame(comparison_rows(result, same_method=True)), hide_index=True, width='stretch')
    st.caption('This main table groups the same detector family. The datasets still differ, so the numbers do not establish a performance improvement.')
    with st.expander('Other approaches and complete literature context', expanded=False):
        st.dataframe(pd.DataFrame(comparison_rows(result)), hide_index=True, width='stretch')
        st.caption('Different methods are grouped separately, regardless of whether their reported accuracy is higher or lower. '
                   'Abengowe Table 2 lists Linear SVC at 92%, its prose says 93%, and stronger models reach 98%. '
                   'The 2019 paper is foundational background, not a recent numerical comparator.')
        for ref in REFERENCES:
            st.markdown('**' + ref['citation'] + ' · ' + ref['title'] + '**')
            st.write(ref['relevance'])
            if ref.get('location'):
                st.caption('Reported values from ' + ref['location'] + '. Not independently reproduced.')
            st.link_button('Open original study', ref['url'])
    st.markdown('**What the reviewer study can show**')
    st.write('The five ratings measure perceived clarity, completeness, severity fit, trust and clarity relative to raw SHAP. '
             'Matched Round 1 and Round 2 responses can describe changes after a wording revision. '
             'Actual improvement remains unproven until reviewers submit responses. No recall questions are required.')
    st.caption('References checked 18 November 2026. Published metrics retain their original task and dataset. '
               'Metrics remain calculated from the model; no target percentage is imposed.')
    st.download_button('Download evaluation and research note', evaluation_report(result),
                       'evaluation_and_research_context.md', 'text/markdown')

if not researcher_mode:
    st.stop()

with policy_tab:
    st.subheader('Expected workflow by role')
    st.dataframe(pd.DataFrame([{'Role': role, 'Shift': f'{start:02}:00–{end:02}:00',
        'Daily records': f'{lo}–{hi}', 'Allowed departments': ', '.join(depts)}
        for role, start, end, lo, hi, depts in result['baselines']]), hide_index=True, width='stretch')

with study_tab:
    st.subheader('Two-round study')
    st.caption('A response is matched by reviewer code and event. Use the same cases and scale in both rounds.')
    if not feedback:
        st.info('No study responses have been collected yet.')
    else:
        frame = pd.DataFrame(feedback)
        protocols = {'direct-review-v2': 'Direct alert review (current)', 'quiz-v1': 'Earlier quiz-based review'}
        protocol = st.selectbox('Survey protocol', list(protocols), format_func=protocols.get,
                               help='Keep feedback collected under different review procedures separate.')
        frame = frame[frame['survey_protocol'] == protocol].copy()
        st.caption(f'{len(frame)} responses under this protocol. Matched results use this protocol in both rounds.')
        measures = list(RATINGS)
        st.caption('These are self-reported 1–5 ratings. They do not measure model accuracy or objectively prove comprehension. Legacy quiz answers remain in the CSV but are excluded from this summary.')
        frame[measures] = frame[measures].replace('', None).apply(pd.to_numeric)
        round_1 = frame[frame['round'] == '1']
        round_2 = frame[frame['round'] == '2']
        paired = round_1.merge(round_2, on=['reviewer', 'event'], suffixes=('_1', '_2'))
        st.metric('Matched reviewer / alert pairs', len(paired))
        if not round_1.empty:
            st.markdown('**Round 1 mean ratings by template**')
            st.dataframe(round_1.groupby('template')[measures].mean().round(2))
        if not paired.empty:
            st.markdown('**Matched scores before and after**')
            st.dataframe(pd.DataFrame([{'Measure': RATINGS.get(m, 'Interpretation correct (proportion)'),
                'Round 1': paired[f'{m}_1'].mean(), 'Round 2': paired[f'{m}_2'].mean(),
                'Change': paired[f'{m}_2'].mean() - paired[f'{m}_1'].mean()} for m in measures]).round(3),
                hide_index=True)
            changed = paired[paired['version_1'] != paired['version_2']]
            st.caption(f'{len(changed)} pairs used revised wording or severity. Unchanged pairs remain visible for comparison.')
            if not changed.empty:
                st.markdown('**Revised alerts only**')
                st.dataframe(pd.DataFrame([{'Measure': RATINGS.get(m, 'Interpretation correct (proportion)'),
                    'Round 1': changed[f'{m}_1'].mean(), 'Round 2': changed[f'{m}_2'].mean(),
                    'Change': changed[f'{m}_2'].mean() - changed[f'{m}_1'].mean()} for m in measures]).round(3),
                    hide_index=True)
        st.markdown('**Response register**')
        st.dataframe(frame[['reviewer', 'event', 'round', 'version', 'clarity', 'shap_clarity', 'comment']],
                     hide_index=True, width='stretch')
        st.caption('The CSV export includes every protocol. Use the survey_protocol column when analyzing it.')
        st.download_button('Download feedback CSV', FEEDBACK.read_bytes(), f'{benchmark}_{workspace.lower().replace(" ", "_")}_feedback.csv', 'text/csv')

with revisions_tab:
    st.subheader('Round 2 revision studio')
    st.caption('Review Round 1 responses and save an approved version for an individual case. Round 1 always shows the original alert.')
    case_ids = [row['id'] for row in flagged]
    event = st.selectbox('Case to revise', case_ids, index=case_ids.index('EVT-0903') if 'EVT-0903' in case_ids else 0)
    source = next(row for row in flagged if row['id'] == event)
    original = source['alert']
    existing = revisions.get(event, {})
    with st.expander('Original alert and Round 1 responses', expanded=True):
        st.html(f'<p class="alert-copy">{escape(original['message'])}</p>')
        case_feedback = [item for item in feedback if item['event'] == event and item['round'] == '1']
        if case_feedback:
            st.dataframe(pd.DataFrame(case_feedback)[['reviewer', *RATINGS, 'comment']], hide_index=True, width='stretch')
        else:
            st.caption('No Round 1 response for this case.')
    revision_identity = hashlib.sha256(json.dumps(existing, sort_keys=True).encode()).hexdigest()[:12]
    with st.form(f'revision_{workspace_key}_{event}_{revision_identity}'):
        unchanged = st.checkbox('Designate this case as an unchanged Round 2 control', value=existing.get('control', False))
        new_message = st.text_area('Revised alert', value=existing.get('message', original['message']), max_chars=2400)
        new_severity = st.selectbox('Revised severity', list(SEVERITY),
                                    index=SEVERITY[existing.get('severity', original['severity'])])
        rationale = st.text_area('Reason for revision or control designation', value=existing.get('rationale', ''), max_chars=1200)
        approved = st.checkbox('I checked the wording and severity against the source evidence.')
        if st.form_submit_button('Save approved Round 2 version', type='primary', disabled=bool(storage_errors)):
            if not approved or not rationale.strip() or (not unchanged and not new_message.strip()):
                st.error('Enter the rationale, confirm the evidence check, and include wording for a revision.')
            elif not unchanged and (new_message.strip(), new_severity) == (original['message'], original['severity']):
                st.error('Change the alert wording or severity, or designate this case as an unchanged control.')
            else:
                try:
                    workspace_dir.mkdir(parents=True, exist_ok=True)
                    with FileLock(STUDY_LOCK, timeout=10):
                        if load_revisions(REVISIONS).get(event, {}) != existing:
                            raise ValueError('Another session changed this case. Reopen it before saving.')
                        if any(item['event'] == event and item['round'] == '2' for item in read_feedback(FEEDBACK)):
                            raise ValueError('Round 2 feedback already exists. The evaluated version is locked for this case.')
                        save_revision(REVISIONS, event, {'message': original['message'] if unchanged else new_message.strip(),
                                      'severity': original['severity'] if unchanged else new_severity,
                                      'rationale': rationale.strip(), 'control': unchanged})
                except (OSError, ValueError, TimeoutError) as exc:
                    st.error(f'Could not save the revision: {exc}')
                else:
                    st.success(f'Round 2 {"control" if unchanged else "revision"} saved for {event}.')
