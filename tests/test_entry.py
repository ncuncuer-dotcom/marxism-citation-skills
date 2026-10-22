"""Synthetic integration tests; no book text or private source locations."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'references/collections.json').read_text(encoding='utf-8'))
BY_ID = {v['id']: v for v in SPEC}


class EntryWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='citation collection # ')
        self.base = Path(self.temp.name)
        self.env = dict(os.environ)
        for v in SPEC:
            self.env[v['data_env']] = str(self.base / 'index' / v['id'])

    def tearDown(self):
        self.temp.cleanup()

    def run_entry(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/research.py'), *map(str, args)],
                           cwd=self.base, env=self.env, capture_output=True, text=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        else:
            self.assertNotEqual(r.returncode, 0)
        return r

    def build(self, key, volumes, sparse=False):
        item = BY_ID[key]
        source = self.base / 'sources' / key
        source.mkdir(parents=True)
        for v in volumes:
            with fitz.open() as doc:
                for n in range(2):
                    p = doc.new_page()
                    if not sparse or n == 0:
                        p.insert_text((50, 70), '合成检索材料调查研究证据' * 4, fontname='china-s')
                doc.save(str(source / ('第{}卷.pdf'.format(v))))
        r = subprocess.run([sys.executable, str(ROOT / 'skills' / item['skill'] / 'scripts/rebuild_index.py'),
                            '--source-dir', str(source), '--allow-partial'], env=self.env,
                           cwd=self.base, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return Path(self.env[item['data_env']])

    def test_mixed_coverage_keeps_books_separate_and_reports_gaps(self):
        self.build('xi-dangjian', [1, 2])
        self.build('deng', [1], sparse=True)
        rows = [json.loads(x) for x in self.run_entry('调查', '--limit', '1').stdout.splitlines()]
        hits = [x for x in rows if 'candidate_excerpt' in x]
        self.assertEqual({x['collection_id'] for x in hits}, {'deng', 'xi-dangjian'})
        for x in hits:
            self.assertTrue(x['local_reference'].startswith(x['collection_id'] + ':'))
            self.assertIn(str(self.base / 'sources' / x['collection_id']), x['source_pdf'])
        summary = next(x for x in rows if x.get('type') == 'summary')
        self.assertEqual(set(summary['searched']), {'deng', 'xi-dangjian'})
        self.assertEqual(len(summary['skipped']), 6)
        coverage = next(x for x in rows if x.get('type') == 'coverage' and x['collection_id'] == 'deng')
        self.assertEqual(coverage['indexed_volumes'], [1])
        self.assertEqual(coverage['missing_volumes'], [2, 3])
        self.assertEqual(coverage['low_text_pages_by_volume'], {'1': [2]})

    def test_page_render_origin_and_wrong_database_rejection(self):
        data = self.build('xi-dangjian', [1, 2])
        image = self.base / 'original #.png'
        rows = [json.loads(x) for x in self.run_entry('--page', 'xi-dangjian:2:1', '--context', '1', '--render', image).stdout.splitlines()]
        pages = [x for x in rows if 'text' in x]
        self.assertEqual([x['pdf_page'] for x in pages], [1, 2])
        self.assertTrue(all(x['collection_id'] == 'xi-dangjian' for x in rows))
        self.assertEqual(image.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        r = self.run_entry('调查', '--collection', 'mao', '--data-dir', data, ok=False)
        report = [json.loads(x) for x in r.stdout.splitlines()]
        self.assertFalse(any('candidate_excerpt' in x for x in report))
        self.assertIn('文集身份', r.stdout)
        self.run_entry('--page', 'deng:1:1', '--collection', 'mao', ok=False)

    def test_empty_install_reports_all_missing_without_inventing_results(self):
        rows = [json.loads(x) for x in self.run_entry('--status').stdout.splitlines()]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(not x['ready'] for x in rows))
        result = self.run_entry('调查', ok=False)
        summary = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(summary['searched'], [])
        self.assertEqual(len(summary['skipped']), 8)
        self.run_entry('调查', '--collection', 'mao', '--collection', 'deng', '--data-dir', self.base, ok=False)


if __name__ == '__main__':
    unittest.main()
