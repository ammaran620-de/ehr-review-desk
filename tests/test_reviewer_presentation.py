"""Client review presentation changes must not alter benchmark evidence."""
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
        self.assertEqual([r['id'] for r in sample], [r['id'] for r in review_set(list(reversed(result['rows'])))])
        self.assertEqual(result['metrics'], before)
        self.assertEqual(sum(r['flagged'] for r in result['rows']), 102)
        self.assertEqual(review_set([]), [])

    def test_comparison_groups_by_method_and_retains_full_literature(self):
        result = run_pipeline('realistic-v1', explain=False)
        main = comparison_rows(result, same_method=True)
        full = comparison_rows(result)
        self.assertEqual(len(main), 2)
        self.assertTrue(any('Chua' in row['Study'] for row in main))
        self.assertTrue(any('Tabassum' in row['Study'] and row['Accuracy'] == '99.21%' for row in full))
        self.assertTrue(any('Iqbal' in row['Study'] for row in full))
        self.assertTrue(any('Abengowe' in row['Study'] for row in full))
        self.assertEqual(main[0], full[0])

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
            widget(app.toggle, 'Researcher tools').set_value(True).run()
            widget(app.checkbox, 'Inspect all model flags').check().run()
            self.assertEqual(len(app.dataframe[0].value), 102)
            widget(app.toggle, 'Researcher tools').set_value(False).run()
            self.assertEqual(len(app.dataframe[0].value), 20)
            widget(app.text_input, 'Search alerts').set_value('impossible-search-value').run()
            self.assertFalse(app.exception)
            self.assertTrue(any('No alerts match' in x.value for x in app.info))


if __name__ == '__main__':
    unittest.main()
