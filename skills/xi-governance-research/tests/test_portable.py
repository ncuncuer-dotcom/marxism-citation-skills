"""Synthetic fixtures only: no book text or user source paths."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]


def make_pdf(path, text='调查研究检验合成材料', title='合成测试篇目'):
    with fitz.open() as doc:
        for i in range(2):
            page = doc.new_page()
            if text:
                page.insert_text((60, 80), text * 4 + str(i + 1), fontname='china-s', fontsize=12)
        doc.set_toc([[1, title, 1]])
        doc.save(str(path))


class PortableWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xi portable # ')
        self.base = Path(self.tmp.name)
        self.source = self.base / '中文 PDFs'
        self.source.mkdir()
        self.data = self.base / '数据 & index'
        for i in range(1, 6):
            make_pdf(self.source / ('第{}卷.pdf'.format(i)))

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, script, *args, ok=True, env=None):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *map(str, args)],
                                cwd=str(self.base), capture_output=True, text=True, env=env)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def build(self, *extra, ok=True):
        return self.run_script('rebuild_index.py', '--source-dir', self.source, '--data-dir', self.data, *extra, ok=ok)

    def test_full_build_search_page_render_and_data_isolation(self):
        self.build()
        result = self.run_script('retrieve.py', '--data-dir', self.data, '--status')
        state = json.loads(result.stdout)
        self.assertTrue(state['ready'])
        self.assertEqual(state['indexed_pages'], 10)
        self.assertEqual(state['missing_volumes'], [])
        result = self.run_script('retrieve.py', '调查', '--volume', '3', '--data-dir', self.data)
        hits = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(hits)
        self.assertTrue(all(x['volume'] == 3 and '调查' in x['candidate_excerpt'] for x in hits))
        dest = self.base / '图片 & #.png'
        result = self.run_script('retrieve.py', '--data-dir', self.data, '--page', '3:1', '--context', '1', '--render', dest)
        pages = [json.loads(x) for x in result.stdout.splitlines()]
        self.assertEqual([x['pdf_page'] for x in pages[:-1]], [1, 2])
        self.assertTrue(dest.is_file())
        self.assertEqual(dest.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        self.run_script('retrieve.py', '--data-dir', self.data, '--page', '3:0', ok=False)
        self.run_script('retrieve.py', '--data-dir', self.data, '--page', '9:1', ok=False)
        self.run_script('retrieve.py', '--data-dir', self.data, '--render', dest, ok=False)
        self.run_script('retrieve.py', '--data-dir', self.data, '--catalogue', '--volume', '3')
        db = sqlite3.connect(self.data / 'corpus.sqlite')
        self.assertEqual(db.execute('pragma integrity_check').fetchone()[0], 'ok')
        self.assertEqual(db.execute('select count(*) from pages p left join search s on p.id=s.rowid where s.rowid is null').fetchone()[0], 0)
        db.close()

    def test_failed_rebuild_preserves_previous_index_and_source_changes_detected(self):
        self.build()
        original = (self.data / 'corpus.sqlite').read_bytes()
        make_pdf(self.source / '重复第1卷.pdf')
        result = self.build(ok=False)
        self.assertIn('重复卷号', result.stderr)
        self.assertEqual((self.data / 'corpus.sqlite').read_bytes(), original)
        (self.source / '重复第1卷.pdf').unlink()
        (self.source / '第5卷.pdf').unlink()
        self.build(ok=False)
        self.assertEqual((self.data / 'corpus.sqlite').read_bytes(), original)
        make_pdf(self.source / '第5卷.pdf', text='')
        self.build(ok=False)
        self.assertEqual((self.data / 'corpus.sqlite').read_bytes(), original)
        self.assertFalse(list(self.data.glob('.build-*')))
        result = self.run_script('retrieve.py', '调查', '--volume', '5', '--data-dir', self.data, ok=False)
        self.assertIn('源文件已变化', result.stderr)

    def test_manifest_partial_env_and_friendly_empty_status(self):
        weird = self.source / 'a file.pdf'
        make_pdf(weird)
        manifest = self.base / '映射.json'
        manifest.write_text(json.dumps({'volumes': [{'volume': 3, 'path': '中文 PDFs/a file.pdf'}]}, ensure_ascii=False), encoding='utf-8')
        env = dict(os.environ, XI_GOVERNANCE_DATA_DIR=str(self.data))
        empty = self.run_script('retrieve.py', '--status', env=env)
        self.assertFalse(json.loads(empty.stdout)['ready'])
        self.run_script('rebuild_index.py', '--manifest', manifest, '--allow-partial', env=env)
        state = json.loads(self.run_script('retrieve.py', '--status', env=env).stdout)
        self.assertEqual([x['volume'] for x in state['volumes']], [3])
        self.assertEqual(state['missing_volumes'], [1, 2, 4, 5])
        self.run_script('retrieve.py', '--page', '1:1', env=env, ok=False)
        self.assertIn('合成测试篇目', self.run_script('retrieve.py', '--catalogue', env=env).stdout)
        # A single Chinese character remains searchable.
        self.assertIn('candidate_excerpt', self.run_script('retrieve.py', '调', env=env).stdout)
        result = self.run_script('retrieve.py', '不存在词语甲乙丙丁', '--limit', '0', env=env, ok=False)
        self.assertIn('--limit', result.stderr)


    def test_collection_identity_is_written_and_foreign_or_legacy_index_is_rejected(self):
        self.build()
        with sqlite3.connect(self.data / 'corpus.sqlite') as db:
            identity = db.execute("SELECT value FROM metadata WHERE key='collection_skill'").fetchone()
            self.assertEqual(identity, (ROOT.name,))
        cases = [('foreign-research-skill', '文集身份不匹配'), (None, '缺少文集身份')]
        for identity, message in cases:
            with self.subTest(identity=identity):
                with sqlite3.connect(self.data / 'corpus.sqlite') as db:
                    if identity is None:
                        db.execute("DELETE FROM metadata WHERE key='collection_skill'")
                    else:
                        db.execute("UPDATE metadata SET value=? WHERE key='collection_skill'", (identity,))
                for action in [('调查',), ('--status',), ('--catalogue',), ('--page', '1:1')]:
                    result = self.run_script('retrieve.py', *action, '--data-dir', self.data, ok=False)
                    self.assertEqual(result.stdout, '')
                    self.assertIn(message, result.stderr)
                if identity is None:
                    self.assertIn('本合集', result.stderr)
                    self.assertIn('重新建立索引', result.stderr)



if __name__ == '__main__':
    unittest.main()
