import json
from pathlib import Path
import tempfile
import unittest
import hashlib

from real_llm_comparison.real_dataset import build, groups
from real_llm_comparison.study import load_dataset


def feature(text, address='District only', category=18):
    return {'type': 'Feature', 'properties': {
        'hintContent': text, 'balloonContent': 'Раздел: Test. Адрес: '+address,
        'category_id': category, 'subcategory_id': 80, 'status': 'completed'}}


class RealDatasetTests(unittest.TestCase):
    def test_offline_unconfirmed_reuse_does_not_allow_live_or_skip_reviews(self):
        fixture = Path(__file__).resolve().parents[1]/'real_llm_comparison/data/complaints_fixture.json'
        data = json.loads(fixture.read_text())
        data['provenance']['reuse_status'] = 'unconfirmed'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'dataset.json'
            path.write_text(json.dumps(data))
            self.assertTrue(load_dataset(path, 'development', dry_run=True)[1])
            with self.assertRaises(ValueError):
                load_dataset(path, 'development')
            reviewed, _ = load_dataset(path, 'development', preliminary_reuse_acknowledgement='Researcher authorizes preliminary external processing; confirmation pending.')
            self.assertEqual(reviewed['provenance']['reuse_status'], 'unconfirmed')
            with self.assertRaises(ValueError):
                load_dataset(path, 'heldout', preliminary_reuse_acknowledgement='Authorized')
            data['records'][0]['review_status'] = 'unreviewed'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_dataset(path, 'development', dry_run=True)
            with self.assertRaises(ValueError):
                load_dataset(path, 'development', preliminary_reuse_acknowledgement='Authorized')

    def test_related_records_share_group_without_grouping_entire_city(self):
        text = ' '.join('word'+str(i) for i in range(40))
        features = [feature(text), feature(text.upper()+'!'),
                    feature(text+' extra'), feature('different issue'),
                    feature('water problem', 'City district Street Lane house 12'),
                    feature('road problem', 'City district Street Lane house 12')]
        g = groups(features)
        self.assertEqual(g[0], g[1]); self.assertEqual(g[0], g[2])
        self.assertNotEqual(g[0], g[3]); self.assertEqual(g[4], g[5])

    def test_trace_redaction_reserve_and_pending_review_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            private = 'Reported fault at apartment 71. '+('Water leak reported. '*8)
            other = 'Pedestrian crossing damaged near central market. '*4
            snapshot = p/'snapshot.json'
            snapshot.write_text(json.dumps([{'features': [feature(private), feature(private), feature(other)]}, {}]))
            annotations = p/'annotations.json'
            annotations.write_text(json.dumps({
                'snapshot_sha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                'exposed_feature_indices': [0],
                'development': [{'feature_index': 0, 'english_gloss': 'reviewer-only',
                    'redactions': [{'field': 'hintContent', 'original': 'apartment 71', 'replacement': '[redacted]'}],
                    'reference': {'constraints': [{'id': 'water', 'requirement': 'inspect'}],
                                  'deliverables': ['draft']}}]}))
            build(snapshot, annotations, p/'out', '2026-10-05', 1)
            dev = json.loads((p/'out/development.draft.json').read_text())
            reserve = json.loads((p/'out/heldout_reserve.UNREVIEWED.json').read_text())
            r = dev['records'][0]
            self.assertNotIn('71', r['source']['hintContent'])
            self.assertEqual(r['source_trace']['observed_status'], 'completed')
            self.assertIsNone(r['source_trace']['portal_complaint_id'])
            self.assertNotEqual(r['group_id'], reserve['records'][0]['group_id'])
            self.assertNotIn('reviewer-only', json.dumps(r['source']))
            with self.assertRaises(ValueError):
                load_dataset(p/'out/development.draft.json', 'development')
            with self.assertRaises(FileExistsError):
                build(snapshot, annotations, p/'out', '2026-10-05', 1)


if __name__ == '__main__':
    unittest.main()
