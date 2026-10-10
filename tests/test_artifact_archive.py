"""Archive/restore tests against local fixtures, no remote mutation."""
from pathlib import Path
import sys
import tempfile
import sqlite3
import unittest
import copy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'modules'))
import scanner_artifact_archive as A


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'tests/.tmp'; parent.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=parent); self.root=Path(self.temp.name)
        self.source=self.root/'source'; self.source.mkdir()
        self.out=self.root/'bundles'; self.dest=self.root/'windows'

    def tearDown(self): self.temp.cleanup()

    def build(self, previous=None): return A.build({'scan-runs':self.source},self.out,previous,bundle_limit=10)
    def fetch(self,tag,asset): return self.out/asset

    def test_round_trip_hebrew_files_and_idempotent_restore(self):
        (self.source/'דוח.md').write_text('מחקר בדיקה',encoding='utf-8')
        manifest,_,_=self.build()
        self.assertEqual(A.restore(manifest,self.dest,self.fetch)['copied'],1)
        self.assertEqual(A.restore(manifest,self.dest,self.fetch)['unchanged'],1)
        self.assertEqual((self.dest/'scan-runs/דוח.md').read_text(encoding='utf-8'),'מחקר בדיקה')

    def test_changed_files_keep_old_version_and_deleted_source_is_retained(self):
        p=self.source/'report.json'; p.write_text('old')
        first,_,_=self.build(); A.restore(first,self.dest,self.fetch)
        old=A.sha(p); p.write_text('new')
        second,_,bundles=self.build(first)
        self.assertEqual(second['parent_tag'],first['tag']); self.assertEqual(second['generation'],2)
        A.restore(second,self.dest,self.fetch)
        self.assertEqual((self.dest/'.versions/scan-runs/report.json'/old).read_text(),'old')
        p.unlink()
        third,_,bundles=self.build(second)
        self.assertIn('scan-runs/report.json',third['files']); self.assertEqual(bundles,[])

    def test_identical_content_only_stored_once_and_split_bundles_restore(self):
        (self.source/'a.txt').write_text('same content')
        (self.source/'b.txt').write_text('same content')
        (self.source/'c.txt').write_text('different data')
        m,_,bundles=self.build()
        self.assertEqual(len(m['files']),3); self.assertEqual(len(m['objects']),2); self.assertEqual(len(bundles),2)
        self.assertEqual(A.restore(m,self.dest,self.fetch)['copied'],3)

    def test_corrupt_bundle_does_not_overwrite_existing_file(self):
        (self.source/'a.txt').write_text('first')
        first,_,_=self.build(); A.restore(first,self.dest,self.fetch)
        (self.source/'a.txt').write_text('second')
        second,_,bundles=self.build(first); bundles[0].write_bytes(b'broken')
        with self.assertRaisesRegex(ValueError,'checksum'):
            A.restore(second,self.dest,self.fetch)
        self.assertEqual((self.dest/'scan-runs/a.txt').read_text(),'first')

    def test_path_traversal_and_windows_devices_rejected_before_download(self):
        (self.source/'a.txt').write_text('test')
        m,_,_=self.build()
        for name in ('../escape','/absolute','C:/outside','scan-runs/con.txt','scan-runs/a:stream','scan-runs/a\\b'):
            bad=copy.deepcopy(m); bad['files'][name]=bad['files'].pop('scan-runs/a.txt')
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                A.restore(bad,self.dest,lambda *args: self.fail('must not download'))

    def test_credentials_and_dependency_files_excluded(self):
        (self.source/'.env.json').write_text('fixture-secret')
        (self.source/'key.pem').write_text('fixture-secret')
        (self.source/'output.csv').write_text('public data')
        p=self.source/'node_modules'; p.mkdir(); (p/'test.json').write_text('{}')
        m,_,_=self.build()
        self.assertEqual(list(m['files']),['scan-runs/output.csv'])

    def test_content_reversion_has_new_generation_and_tag(self):
        p=self.source/'report.json'; p.write_text('a')
        first,_,_=self.build()
        p.write_text('b'); second,_,_=self.build(first)
        p.write_text('a'); third,_,_=self.build(second)
        self.assertEqual(len({first['tag'],second['tag'],third['tag']}),3)
        self.assertEqual(third['generation'],3)
        self.assertEqual(third['parent_tag'],second['tag'])
        same,_,bundles=self.build(third)
        self.assertEqual(same,third); self.assertEqual(bundles,[])

    def test_sqlite_wal_backup_is_consistent(self):
        db=sqlite3.connect(self.source/'research.sqlite')
        db.execute('PRAGMA journal_mode=WAL'); db.execute('CREATE TABLE results (n INTEGER)')
        db.execute('INSERT INTO results VALUES (42)'); db.commit()
        try:
            m,_,_=self.build(); A.restore(m,self.dest,self.fetch)
            restored=sqlite3.connect(self.dest/'scan-runs/research.sqlite')
            try: self.assertEqual(restored.execute('SELECT n FROM results').fetchone()[0],42)
            finally: restored.close()
        finally: db.close()


if __name__=='__main__': unittest.main()
