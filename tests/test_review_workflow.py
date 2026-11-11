"""Regression checks for client review, protocol compatibility and computed metrics."""
import csv
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from feedback import FIELDS, read_feedback, save_feedback
from pipeline import run_pipeline
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def response(**changes):
    return dict(reviewer='it01', event='EVT-0903', round=1, version='baseline-v1',
                severity='High', template='Combined anomaly', clarity=4, completeness=4,
                severity_fit=4, trust=4, interpretation_correct='', shap_clarity=4,
                comment='Clear enough', **changes)


def widget(elements, label):
    return next(element for element in elements if element.label == label)


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_pipeline()

    def test_metrics_recomputed_from_exported_predictions(self):
        items = self.result['test_predictions']
        tp = sum(x['actual'] == 1 and x['predicted'] == 1 for x in items)
        tn = sum(x['actual'] == 0 and x['predicted'] == 0 for x in items)
        fp = sum(x['actual'] == 0 and x['predicted'] == 1 for x in items)
        fn = sum(x['actual'] == 1 and x['predicted'] == 0 for x in items)
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        f1 = 2 * precision * recall / (precision + recall)
        positives = [x['raw_score'] for x in items if x['actual']]
        negatives = [x['raw_score'] for x in items if not x['actual']]
        auc = sum((p > n) + .5 * (p == n) for p in positives for n in negatives) / (len(positives) * len(negatives))
        self.assertEqual(self.result['cm'], [[tn, fp], [fn, tp]])
        for expected, actual in zip([precision, recall, f1, (tn + tp) / len(items), auc], self.result['metrics']):
            self.assertAlmostEqual(expected, actual)
        self.assertEqual(len(items), 250)
        self.assertEqual(sum(x['actual'] for x in items), 25)
        self.assertAlmostEqual(tn / (tn + fp + fn + tp), .9)

    def test_original_client_benchmark_is_preserved(self):
        self.assertEqual(self.result['cm'], [[225, 0], [3, 22]])
        self.assertEqual(sum(x['flagged'] for x in self.result['rows']), 91)
        self.assertFalse(self.result['metadata']['labels_used_for_fit'])
        self.assertEqual(len(self.result['metadata']['dataset_sha256']), 64)


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'feedback.csv'

    def test_direct_feedback_blank_quiz_and_resubmission(self):
        save_feedback(self.path, response())
        save_feedback(self.path, {**response(), 'clarity': 5})
        records = read_feedback(self.path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['interpretation_correct'], '')
        self.assertEqual(records[0]['survey_protocol'], 'direct-review-v2')
        self.assertEqual(records[0]['clarity'], '5')

    def test_legacy_feedback_remains_readable_and_identified(self):
        old_fields = [f for f in FIELDS if f not in {'survey_protocol', 'shap_clarity'}]
        old = {**response(), 'interpretation_correct': '1', 'utc': '2026-11-10T00:00:00+00:00'}
        with self.path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=old_fields)
            writer.writeheader()
            writer.writerow({f: old[f] for f in old_fields})
        self.assertEqual(read_feedback(self.path)[0]['survey_protocol'], 'quiz-v1')
        save_feedback(self.path, {**response(), 'reviewer': 'it02'})
        self.assertEqual({x['survey_protocol'] for x in read_feedback(self.path)}, {'quiz-v1', 'direct-review-v2'})

    def test_invalid_write_does_not_replace_valid_file(self):
        save_feedback(self.path, response())
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            save_feedback(self.path, {**response(), 'clarity': 99})
        self.assertEqual(self.path.read_bytes(), original)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for source in [*ROOT.glob('*.py'), ROOT / 'interface.css']:
            shutil.copy2(source, self.root / source.name)
        self.app = AppTest.from_file(str(self.root / 'app.py'), default_timeout=60).run()
        self.assertFalse(self.app.exception)

    def submit(self, code='IT01', rating=4):
        app = self.app
        widget(app.text_input, 'Reviewer code').set_value(code)
        for label in ['Was this alert clear?', 'Was the evidence complete?', 'Was the severity appropriate?',
                      'Would you trust this alert to guide a review?',
                      'Was the plain-English alert clearer than the raw SHAP values?']:
            widget(app.selectbox, label).set_value(rating)
        widget(app.button, 'Save reviewer feedback').click().run()
        self.assertFalse(app.exception)

    def test_participant_can_submit_immediately_and_search_by_role(self):
        app = self.app
        widget(app.radio, 'Data workspace').set_value('Reviewer study').run()
        self.assertEqual(widget(app.radio, 'Study view').value, 'Participant')
        self.assertNotIn('How many records were accessed?', [x.label for x in app.text_input])
        self.assertTrue(any(x.label == 'Save reviewer feedback' for x in app.button))
        self.submit()
        records = read_feedback(self.root / 'data/study/feedback.csv')
        self.assertEqual(records[0]['event'], 'EVT-0903')
        self.assertEqual(records[0]['survey_protocol'], 'direct-review-v2')
        self.assertEqual(records[0]['interpretation_correct'], '')
        self.assertFalse((self.root / 'data/rehearsal/feedback.csv').exists())
        widget(app.text_input, 'Search alerts').set_value('Nurse').run()
        table = app.dataframe[0].value
        self.assertGreater(len(table), 0)
        # Search can match wording as well as role. Every result must contain the search term.
        self.assertTrue(all('nurse' in ' '.join(map(str, row)).lower() for row in table.values))
        self.assertNotIn('Receptionist', app.subheader[-1].value)
        widget(app.text_input, 'Search alerts').set_value('does-not-exist').run()
        self.assertTrue(any('No alerts match' in x.value for x in app.info))
        self.assertFalse(app.exception)

    def test_two_round_feedback_pairs_and_locks_revision(self):
        app = self.app
        self.submit()
        revised = widget(app.text_area, 'Revised alert').value + '\nVerify the access with the department lead.'
        widget(app.text_area, 'Revised alert').set_value(revised)
        widget(app.text_area, 'Reason for revision or control designation').set_value('Make the recommended action clearer.')
        widget(app.checkbox, 'I checked the wording and severity against the source evidence.').check()
        widget(app.button, 'Save approved Round 2 version').click().run()
        self.assertFalse(app.exception)
        widget(app.radio, 'Study round').set_value('Round 2').run()
        self.submit(rating=5)
        records = read_feedback(self.root / 'data/rehearsal/feedback.csv')
        self.assertEqual(len(records), 2)
        self.assertEqual({x['round'] for x in records}, {'1', '2'})
        self.assertNotEqual(records[0]['version'], records[1]['version'])
        self.assertTrue(any(m.label == 'Matched reviewer / alert pairs' and m.value == '1' for m in app.metric))
        before = (self.root / 'data/rehearsal/revisions.json').read_bytes()
        widget(app.text_area, 'Revised alert').set_value(revised + ' Another change.')
        widget(app.checkbox, 'I checked the wording and severity against the source evidence.').check()
        widget(app.button, 'Save approved Round 2 version').click().run()
        self.assertTrue(any('evaluated version is locked' in x.value for x in app.error))
        self.assertEqual((self.root / 'data/rehearsal/revisions.json').read_bytes(), before)

    def test_round_two_without_approval_cannot_save(self):
        widget(self.app.radio, 'Study round').set_value('Round 2').run()
        self.assertFalse(any(x.label == 'Save reviewer feedback' for x in self.app.button))
        self.assertTrue(any('approved revision' in x.value for x in self.app.info))

    def test_table_selection_opens_matching_case_and_filter_resets_safely(self):
        app = self.app
        table = app.dataframe[0]
        target = table.value.iloc[5]['Event']
        app.session_state[table.key] = {'selection': {'rows': [5], 'columns': [], 'cells': []}}
        app.run()
        self.assertTrue(any(x.value.startswith(target + ' ·') for x in app.subheader))
        widget(app.text_input, 'Search alerts').set_value('Nurse').run()
        self.assertFalse(app.exception)
        new_table = app.dataframe[0].value
        current = app.session_state['selected_event']
        self.assertIn(current, new_table['Event'].tolist())
        self.assertTrue(any(x.value.startswith(current + ' ·') for x in app.subheader))

    def test_legacy_and_direct_protocol_pairs_are_not_pooled(self):
        path = self.root / 'data/rehearsal/feedback.csv'
        for protocol, code, rating in [('direct-review-v2', 'it01', 5), ('quiz-v1', 'it02', 2)]:
            for round_number in (1, 2):
                save_feedback(path, {**response(), 'reviewer': code, 'round': round_number,
                    'survey_protocol': protocol, 'clarity': rating,
                    'interpretation_correct': '1' if protocol == 'quiz-v1' else ''})
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any(m.label == 'Matched reviewer / alert pairs' and m.value == '1' for m in self.app.metric))
        paired = next(d.value for d in self.app.dataframe if 'Measure' in d.value)
        self.assertEqual(paired.iloc[0]['Round 1'], 5)
        widget(self.app.selectbox, 'Survey protocol').set_value('quiz-v1').run()
        paired = next(d.value for d in self.app.dataframe if 'Measure' in d.value)
        self.assertEqual(paired.iloc[0]['Round 1'], 2)


if __name__ == '__main__':
    unittest.main()
