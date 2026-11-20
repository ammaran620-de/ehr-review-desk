"""Client review presentation changes must not alter benchmark evidence."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest

from streamlit.testing.v1 import AppTest

from feedback import read_feedback
from pipeline import run_pipeline
from research_context import comparison_rows
from review_presentation import alert_page, page_count
from test_review_workflow import widget

ROOT = Path(__file__).resolve().parents[1]


class PresentationTests(unittest.TestCase):
    def test_pagination_preserves_every_case_without_exceeding_twenty(self):
        items = list(range(102))
        batches = [alert_page(items, page) for page in range(1, page_count(items) + 1)]
        self.assertEqual([len(batch) for batch in batches], [20, 20, 20, 20, 20, 2])
        self.assertEqual([item for batch in batches for item in batch], items)
        self.assertEqual(alert_page([], 1), [])
        self.assertEqual(alert_page(items, 999), [100, 101])

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

    def test_reviewer_screen_and_cross_page_feedback_binding(self):
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
            widget(app.selectbox, 'Alert page').set_value(2).run()
            self.assertFalse(app.exception)
            second_ids = set(app.dataframe[0].value['Event'])
            self.assertEqual(len(second_ids), 20)
            self.assertFalse(first_ids & second_ids)
            selected = app.session_state['selected_event']
            self.assertIn(selected, second_ids)
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
            widget(app.selectbox, 'Alert page').set_value(6).run()
            self.assertEqual(len(app.dataframe[0].value), 2)
            widget(app.text_input, 'Search alerts').set_value('impossible-search-value').run()
            self.assertFalse(app.exception)
            self.assertTrue(any('No alerts match' in x.value for x in app.info))


if __name__ == '__main__':
    unittest.main()
