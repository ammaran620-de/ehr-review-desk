"""Client review presentation changes must not alter benchmark evidence."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest

from streamlit.testing.v1 import AppTest

from feedback import read_feedback
from pipeline import run_pipeline
from research_context import comparison_rows
from review_presentation import review_set
from test_review_workflow import widget

ROOT = Path(__file__).resolve().parents[1]


class PresentationTests(unittest.TestCase):
    def test_fixed_review_set_preserves_benchmark_and_round_membership(self):
        result = run_pipeline('realistic-v1')
        before = list(result['metrics'])
        sample = review_set(result['rows'])
        self.assertEqual(len(sample), 20)
        self.assertEqual(len({r['id'] for r in sample}), 20)
        self.assertTrue(all(r['flagged'] for r in sample))
        self.assertEqual(Counter(r['alert']['severity'] for r in sample),
                         {'High': 7, 'Medium': 8, 'Low': 5})
        self.assertEqual({r['alert']['severity'] for r in sample[:3]}, {'High', 'Medium', 'Low'})
        for row in sample:
            if row['alert']['severity'] == 'Low':
                self.assertEqual(row['alert']['version'], 'baseline-v2')
                self.assertEqual(row['alert']['groups'], ['Volume'])
                self.assertFalse(row['off_hours_access'] or row['role_mismatch'])
                self.assertEqual(row['assigned_department'], row['department_accessed'])
        self.assertEqual([r['id'] for r in sample], [r['id'] for r in review_set(list(reversed(result['rows'])))])
        self.assertEqual(result['metrics'], before)
        self.assertEqual(sum(r['flagged'] for r in result['rows']), 102)
        self.assertEqual(review_set([]), [])

    def test_comparison_has_exactly_the_two_selected_papers(self):
        result = run_pipeline('realistic-v1', explain=False)
        rows = comparison_rows(result)
        self.assertEqual([row['Accuracy'] for row in rows], ['96.9%', '92% (Linear SVC)', '93%'])
        self.assertIn('Abengowe', rows[1]['Study'])
        self.assertIn('Chua', rows[2]['Study'])

    def test_fixed_reviewer_set_filters_and_feedback_binding(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for source in [*ROOT.glob('*.py'), ROOT / 'interface.css']:
                shutil.copy2(source, root / source.name)
            app = AppTest.from_file(str(root / 'app.py'), default_timeout=60).run()
            self.assertFalse(app.exception)
            self.assertNotIn('Benchmark dataset', [x.label for x in app.selectbox])
            self.assertNotIn('Data workspace', [x.label for x in app.radio])
            self.assertNotIn('Study view', [x.label for x in app.radio])
            self.assertFalse(any(x.label == 'Run Python pipeline' for x in app.button))
            self.assertFalse(any(x.label == 'Save approved Round 2 version' for x in app.button))
            self.assertEqual(len(app.dataframe[0].value), 20)
            self.assertEqual(Counter(app.dataframe[0].value['Severity']), {'High': 7, 'Medium': 8, 'Low': 5})
            self.assertIn('Revision Studio', [x.label for x in app.tabs])
            self.assertNotIn('Other approaches and complete literature context', [x.label for x in app.expander])
            first_ids = set(app.dataframe[0].value['Event'])
            self.assertNotIn('Alert page', [x.label for x in app.selectbox])
            widget(app.text_input, 'Search alerts').set_value('EVT-0903').run()
            self.assertEqual(list(app.dataframe[0].value['Event']), ['EVT-0903'])
            selected = app.session_state['selected_event']
            self.assertIn(selected, first_ids)
            widget(app.text_input, 'Reviewer code').set_value('IT20')
            for label in ['Was this alert clear?', 'Was the evidence complete?', 'Was the severity appropriate?',
                          'Would you trust this alert to guide a review?',
                          'Was the plain-English alert clearer than the raw SHAP values?']:
                widget(app.selectbox, label).set_value(4)
            widget(app.button, 'Save reviewer feedback').click().run()
            self.assertFalse(app.exception)
            path = next((root / 'data').glob('realistic-v1-*/study/feedback.csv'))
            self.assertEqual(read_feedback(path)[0]['event'], selected)
            self.assertEqual(read_feedback(path)[0]['benchmark_id'], 'realistic-v1')
            self.assertTrue(any(x.label == 'Accuracy' and x.value == '96.9%' for x in app.metric))
            widget(app.text_input, 'Search alerts').set_value('').run()
            self.assertEqual(set(app.dataframe[0].value['Event']), first_ids)
            widget(app.radio, 'Study round').set_value('Round 2').run()
            self.assertEqual(set(app.dataframe[0].value['Event']), first_ids)
            widget(app.button, 'Open Revision Studio').click().run()
            self.assertTrue(widget(app.toggle, 'Researcher tools').value)
            self.assertIn('Save approved Round 2 version', [x.label for x in app.button])
            widget(app.checkbox, 'Inspect all model flags').check().run()
            self.assertEqual(len(app.dataframe[0].value), 102)
            widget(app.toggle, 'Researcher tools').set_value(False).run()
            self.assertEqual(len(app.dataframe[0].value), 20)
            widget(app.text_input, 'Search alerts').set_value('impossible-search-value').run()
            self.assertFalse(app.exception)
            self.assertTrue(any('No alerts match' in x.value for x in app.info))


if __name__ == '__main__':
    unittest.main()
