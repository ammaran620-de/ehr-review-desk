"""Verify real prediction arithmetic, unsupervised fitting and dataset isolation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import shutil
import unittest

import numpy as np
from sklearn.ensemble import IsolationForest
from streamlit.testing.v1 import AppTest

from feedback import read_feedback
from pipeline import run_pipeline
from realistic_pipeline import generate_events, sensitivity_runs, SENSITIVITY_SEEDS
from test_review_workflow import widget

ROOT = Path(__file__).resolve().parents[1]


class RealisticBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_pipeline('realistic-v1')

    def test_predictions_independently_reproduce_all_metrics(self):
        r = self.result
        items = r['test_predictions']
        tn = sum(not x['actual'] and not x['predicted'] for x in items)
        fp = sum(not x['actual'] and x['predicted'] for x in items)
        fn = sum(x['actual'] and not x['predicted'] for x in items)
        tp = sum(x['actual'] and x['predicted'] for x in items)
        p, recall = tp / (tp + fp), tp / (tp + fn)
        positives = [x['raw_score'] for x in items if x['actual']]
        negatives = [x['raw_score'] for x in items if not x['actual']]
        auc = sum((a > b) + .5 * (a == b) for a in positives for b in negatives) / (len(positives) * len(negatives))
        expected = [p, recall, 2*p*recall/(p+recall), (tn+tp)/len(items), auc]
        np.testing.assert_allclose(r['metrics'], expected)
        self.assertEqual(r['cm'], [[tn, fp], [fn, tp]])
        # Keep the measured primary result even when it is outside a requested range.
        self.assertAlmostEqual(r['metrics'][3], 247/255)

    def test_split_and_generator_protocol(self):
        r = self.result
        m = r['metadata']
        self.assertFalse(set(m['train_users']) & set(m['test_users']))
        self.assertEqual(len(r['rows']), 1000)
        self.assertEqual(sum(x['label'] for x in r['rows']), 100)
        self.assertEqual(sum(x['simulation_context'] != 'Routine workflow' for x in r['rows'] if not x['label']), 36)
        self.assertEqual(sum(x['scenario'].startswith('Subtle ') for x in r['rows']), 25)
        self.assertTrue(any(x['flagged'] and not x['label'] for x in r['rows']))
        self.assertTrue(any(not x['flagged'] and x['label'] for x in r['rows']))
        self.assertNotEqual(m['dataset_sha256'], run_pipeline('reference-v1')['metadata']['dataset_sha256'])

    def test_model_fit_receives_features_without_labels(self):
        fit = IsolationForest.fit
        received = []
        def spy(model, X, y=None, **kwargs):
            received.append((X.shape, y))
            return fit(model, X, y=y, **kwargs)
        with patch.object(IsolationForest, 'fit', spy):
            run_pipeline('realistic-v1', explain=False)
        self.assertEqual(received, [((745, 7), None)])

    def test_all_configured_seeds_are_retained(self):
        runs = sensitivity_runs()
        self.assertEqual([r['seed'] for r in runs], list(SENSITIVITY_SEEDS))
        self.assertGreater(max(r['accuracy'] for r in runs), .95)
        self.assertLess(min(r['accuracy'] for r in runs), .95)


class DatasetIsolationTests(unittest.TestCase):
    def test_review_in_new_benchmark_does_not_change_original_reviews(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for source in [*ROOT.glob('*.py'), ROOT / 'interface.css']:
                shutil.copy2(source, root / source.name)
            app = AppTest.from_file(str(root / 'app.py'), default_timeout=60).run()
            self.assertFalse(app.exception)
            self.assertNotIn('Benchmark dataset', [x.label for x in app.selectbox])
            widget(app.text_input, 'Reviewer code').set_value('IT88')
            for label in ['Was this alert clear?', 'Was the evidence complete?', 'Was the severity appropriate?',
                          'Would you trust this alert to guide a review?',
                          'Was the plain-English alert clearer than the raw SHAP values?']:
                widget(app.selectbox, label).set_value(4)
            widget(app.button, 'Save reviewer feedback').click().run()
            self.assertFalse(app.exception)
            paths = list((root / 'data').glob('realistic-v1-*/study/feedback.csv'))
            self.assertEqual(len(paths), 1)
            saved = read_feedback(paths[0])
            self.assertEqual(saved[0]['benchmark_id'], 'realistic-v1')
            self.assertEqual(len(saved[0]['dataset_sha256']), 64)
            before = paths[0].read_bytes()
            widget(app.toggle, 'Researcher tools').set_value(True).run()
            widget(app.selectbox, 'Benchmark dataset').set_value('Original demonstration (v1)').run()
            self.assertFalse(app.exception)
            self.assertFalse((root / 'data/study/feedback.csv').exists())
            self.assertEqual(paths[0].read_bytes(), before)
            self.assertTrue(any('No study responses' in x.value for x in app.info))


if __name__ == '__main__':
    unittest.main()
