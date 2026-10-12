"""Offline synthetic lifecycle contracts; not evidence of trading returns."""
from pathlib import Path
import sys
import json
import tempfile
import unittest
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'modules'))
import scanner_research_ledger as L
import scanner_trade_followup as F


def bars(n=25):
    idx = pd.bdate_range('2026-10-12', periods=n)
    return pd.DataFrame({'Open': 100., 'High': [102+i for i in range(n)],
                         'Low': [99+i for i in range(n)], 'Close': [101+i for i in range(n)]}, index=idx)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp = ROOT/'tests/.tmp'; tmp.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=tmp)
        self.root = Path(self.tmp.name)
        self.db = L.connect(self.root/'research.sqlite')
        self.rows = [dict(ticker='TEST', asset='stock', direction='LONG', selected=True,
                          baseline_would_select=True, unified_score=70, baseline_score=68)]

    def tearDown(self):
        self.db.close(); self.tmp.cleanup()

    def freeze(self, mode='weekly', frozen='2026-10-12T07:00:00Z', path='run'):
        rows = [dict(self.rows[0], would_select=True)]
        return L.freeze_run(self.root/path, '2026-10-12T06:00:00Z', mode, rows,
                            {('TEST', 'LONG'): {'score': 70}}, {'config_sha256': 'config'},
                            {'stock': '2026-10-12'}, {'candidates': 50}, frozen_at=frozen)

    def seed(self, **kw):
        p = self.freeze(**kw)
        L.ingest(self.db, self.root/kw.get('path', 'run')/'research_snapshot.json')
        return p

    def test_snapshot_immutable_and_ingestion_idempotent(self):
        first = self.seed()
        self.assertEqual(self.freeze(), first)
        self.assertEqual(L.ingest(self.db, self.root/'run/research_snapshot.json'), 0)
        self.rows[0]['baseline_score'] = 99
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.freeze()

    def test_missing_prices_pending_not_zero(self):
        self.seed()
        L.update(self.db, '2026-10-13T07:00:00Z', lambda *a: None)
        summary = L.summarize(self.db)
        self.assertTrue(all(g['matured'] == 0 and g['pending'] == 1 and g['mean_gross_excess'] is None for g in summary['groups']))

    def test_future_and_partial_bars_excluded(self):
        self.seed()
        r = L.update(self.db, '2026-10-16T19:00:00Z', lambda *a: bars())
        self.assertEqual(r['new_observations'], 4)
        self.assertEqual(self.db.execute('SELECT count(*) FROM outcomes').fetchone()[0], 0)
        L.update(self.db, '2026-10-16T21:00:00Z', lambda *a: bars())
        self.assertEqual(self.db.execute('SELECT horizon FROM outcomes').fetchone()[0], 5)

    def test_daily_updates_do_not_multiply_sample_size(self):
        self.seed()
        for _ in range(2):
            L.update(self.db, '2026-11-14T07:00:00Z', lambda *a: bars())
        self.assertEqual(self.db.execute('SELECT count(*) FROM outcomes').fetchone()[0], 3)
        self.assertEqual(self.db.execute('SELECT count(*) FROM observations').fetchone()[0], 20)
        self.assertTrue(all(g['matured'] == 1 and g['distinct_entry_days'] == 1 for g in L.summarize(self.db)['groups']))

    def test_missing_entry_or_middle_session_defers(self):
        self.seed()
        for frame in (bars().iloc[1:], bars().drop(bars().index[2])):
            r = L.update(self.db, '2026-11-14T07:00:00Z', lambda t, *a: frame if t == 'TEST' else bars())
            self.assertEqual(len(r['errors']), 1)
            self.assertEqual(self.db.execute('SELECT count(*) FROM outcomes').fetchone()[0], 0)

    def test_replayed_trial_and_frozen_after_open_excluded(self):
        self.seed(mode='trial', path='trial')
        self.seed(frozen='2026-10-14T07:00:00Z', path='late')
        self.seed(frozen='2026-10-12T14:00:00Z', path='after_open')
        r = L.update(self.db, '2026-11-14T07:00:00Z', lambda *a: bars())
        self.assertEqual(r['excluded_nonforward'], 3)
        self.assertEqual(L.summarize(self.db)['groups'], [])

    def test_paper_weekly_are_separate(self):
        self.seed(path='weekly')
        self.seed(mode='paper', path='paper')
        self.assertEqual({g['mode'] for g in L.summarize(self.db)['groups']}, {'weekly', 'paper'})

    def test_outcomes_not_rewritten_by_later_price_revision(self):
        self.seed()
        L.update(self.db, '2026-11-14T07:00:00Z', lambda *a: bars())
        old = [r[0] for r in self.db.execute('SELECT payload FROM outcomes')]
        L.update(self.db, '2026-11-15T07:00:00Z', lambda *a: bars()*2)
        self.assertEqual(old, [r[0] for r in self.db.execute('SELECT payload FROM outcomes')])


class FollowupTests(unittest.TestCase):
    def trade(self, direction='LONG'):
        return dict(trade_id='t1', ticker='TEST', asset='stock', direction=direction, status='closed',
                    entry_session='2026-10-12', entry_fill=100, exit_date='2026-10-12', exit_price=101,
                    exit_reason='stop', current_stop=95, target=120)

    def test_post_exit_clock_starts_after_exit_not_entry(self):
        t = self.trade(); t['entry_session'] = '2026-09-01'
        p = F.post_exit_labels(t, bars(6), bars(6))
        self.assertEqual([x['horizon'] for x in p], [5])
        self.assertEqual(p[0]['measured_date'], '2026-10-19')
        self.assertAlmostEqual(p[0]['direction_return'], 106/101-1)
        self.assertEqual(F.post_exit_labels(t, bars(5), bars(5)), [])

    def test_all_post_exit_horizons_and_direction_mirror(self):
        long = F.post_exit_labels(self.trade(), bars(), bars())
        short = F.post_exit_labels(self.trade('SHORT'), bars(), bars())
        self.assertEqual([p['horizon'] for p in long], [5,10,20])
        for a,b in zip(long, short):
            self.assertAlmostEqual(a['direction_return'], -b['direction_return'])

    def test_post_exit_missing_session_and_revised_exit_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError, 'gap'):
            F.post_exit_labels(self.trade(), bars().drop(bars().index[2]), bars())
        with self.assertRaisesRegex(ValueError, 'differs'):
            F.post_exit_labels(self.trade(), bars()*2, bars()*2)

    def test_news_future_filtered_duplicates_removed_and_coverage_retained(self):
        class News(list): flag = 'no keys'
        news = News([dict(id='1', headline='test', source='test', url='https://example.com', created_at_utc='2026-10-13T01:00Z')]*2 +
                    [dict(id='2', created_at_utc='2026-10-15T01:00Z')])
        n = F.clean_news(news, L.utc('2026-10-12T07:00Z'), L.utc('2026-10-14T07:00Z'))
        self.assertEqual(n['count'], 1)
        self.assertEqual(n['status'], 'no keys')

    def test_daily_run_news_without_new_bar_post_exit_idempotency(self):
        tmp = ROOT/'tests/.tmp'; tmp.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp) as directory:
            root = Path(directory)
            active = dict(self.trade(), trade_id='active', status='open')
            news_calls = []
            def news(*a): news_calls.append(a); return []
            for date in ('2026-11-13T07:00Z', '2026-11-14T07:00Z'):
                result, _ = F.run([active, self.trade()], root/'x.sqlite', date,
                                  lambda *a: bars(), news, lambda *a: {'technical': {'sma50': 110}}, root/'out')
            self.assertEqual(len(news_calls), 2)  # one per ticker per day, even on unchanged prices
            self.assertEqual(len(result['post_exit_new']), 0)
            self.assertEqual(len(result['post_exit_history']), 3)
            self.assertEqual(len(result['open']), 1)

    def test_daily_news_still_available_when_prices_fail(self):
        tmp = ROOT/'tests/.tmp'; tmp.mkdir(exist_ok=True)
        def fail(*a): raise RuntimeError('fixture provider unavailable')
        with tempfile.TemporaryDirectory(dir=tmp) as directory:
            root = Path(directory)
            result, _ = F.run([dict(self.trade(), status='open')], root/'db.sqlite', '2026-11-13T07:00Z',
                              fail, lambda *a: [], lambda *a: {}, root/'out')
            self.assertEqual(result['open'][0]['news']['status'], 'ok')
            self.assertEqual(result['open'][0]['review']['status'], 'unavailable')


if __name__ == '__main__': unittest.main()
