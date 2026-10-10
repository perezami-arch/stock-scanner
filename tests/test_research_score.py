"""Offline contracts and ranking tests; fixtures do not measure investment returns."""
import copy
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'modules'))
sys.path.insert(0, str(ROOT / 'scanner'))
import scanner_research_score as R
import scanner_lunar_calendar as LC
import run_unified_scan as RUN
import scanner_levelsfile as LF

DATA = ROOT / 'research/jewish-lunar/data/jerusalem-lunar-daily-2026-10.csv'


def fixture(direction='LONG', ticker='TEST', base=75):
    sgn = 1 if direction == 'LONG' else -1
    point = lambda label, price, date: dict(label=label, price=price, date=date, confirmed_at='2026-10-05', provisional=False)
    pivots = [point('0', 90 if sgn == 1 else 110, '2026-09-25'),
              point('1', 110 if sgn == 1 else 90, '2026-10-01'), point('2', 100, '2026-10-02')]
    c = dict(t=ticker, asset='stock', direction=direction, unified_score=base, rank_score=base,
             momentum_score=base if sgn == 1 else 100-base, momentum_score_short=base,
             rank_basis='momentum_score percentile', sector_etf='TEST', entry=100, stop=100-8*sgn, target=100+15*sgn,
             _eg={'blocked': False})
    L = dict(schema_version='levels-1.0', symbol=ticker, asset='stock', direction=direction, run_id='fixture-only',
             data=dict(cutoff_utc='2026-10-08T12:15:00Z', last_bar='2026-10-07', source='synthetic_fixture'),
             score=dict(value=base, basis=c['rank_basis']), context={},
             technical=dict(last_close=100, atr14_wilder=2),
             trade=dict(entry=c['entry'], stop=c['stop'], target=c['target']),
             pivots={'confirmed': pivots},
             elliott={'v2': {'views': {direction: dict(kind='impulse', state='impulse_confirmed', provisional=False, pivots=pivots)}}},
             fib={'v2': dict(view=direction, stale=False, origin=pivots[0], end=pivots[1],
                             levels={'0.382': 100, '0.5': 100, '0.618': 100, '0.786': 100})},
             waves={'signals': dict(wave_start_n=3, wave_start_families='volume_exhaustion,effort_result,elliott_context',
                                    wave_end_n=0, wave_end_families=None, rsi14=55, cci20=100)})
    geo = dict(geo_direction_view=direction, geo_last_bar='2026-10-07',
               candle_bias_last='bullish' if sgn == 1 else 'bearish', candle_patterns_last='engulfing',
               candle_context='uptrend' if sgn == 1 else 'downtrend', candle_vol_ratio20=1.5, candle_vol_ratio20_median=1.5,
               exp_spiral_arc_above=100, exp_spiral_arc_below=100,
               exp_gann_level_above=100, exp_gann_level_below=100, exp_gann_angle_above=100, exp_gann_angle_below=100,
               exp_gann_next_time_bars=1, exp_gann_box_bars=4, exp_gann_origin_age_bars=8, exp_gann_end_age_bars=4,
               exp_anchor_origin_date='2026-09-25', exp_anchor_origin_confirmed_at='2026-10-05',
               exp_anchor_end_date='2026-10-01', exp_anchor_end_confirmed_at='2026-10-05')
    return c, L, geo


class ScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scorer = R.ResearchScorer([DATA])

    def test_requested_weight_and_budget(self):
        self.assertEqual(self.scorer.weight, 0.30)
        self.assertAlmostEqual(sum(R.WEIGHTS.values()), 1)
        b = {k: R.component(90, 'fixture') for k in R.WEIGHTS}
        r = R.blend(70, b)
        self.assertAlmostEqual(r['score'], 76)
        self.assertAlmostEqual(r['effective_baseline_weight'], .7)

    def test_missing_all_keeps_base(self):
        r = R.blend(73, {})
        self.assertEqual(r['score'], 73)
        self.assertEqual(r['effective_research_weight'], 0)
        self.assertIsNone(r['research_score'])

    def test_partial_coverage_returns_weight_to_base(self):
        r = R.blend(70, {'candles': R.component(100, 'fixture')})
        self.assertAlmostEqual(r['score'], 70.9)
        self.assertAlmostEqual(r['effective_research_weight'], .03)
        self.assertAlmostEqual(r['effective_baseline_weight'], .97)

    def test_contributions_reconcile(self):
        r = self.scorer.evaluate(*fixture()[:2], geometry=fixture()[2])
        self.assertAlmostEqual(sum(b['contribution_points'] for b in r['components'].values()), r['delta_points'])
        self.assertAlmostEqual(r['baseline_score'] + r['delta_points'], r['score'], places=4)
        self.assertEqual(r['status'], 'complete')

    def test_zero_weight_restores_base_exactly(self):
        c, L, geo = fixture(base=74.3)
        original = copy.deepcopy(L['trade'])
        r = R.ResearchScorer([DATA], weight=0).apply(c, L, geometry=geo)
        self.assertEqual(c['unified_score'], 74.3)
        self.assertEqual(r['status'], 'disabled')
        self.assertEqual(c['rank_basis'], 'momentum_score percentile')
        self.assertEqual(L['trade'], original)

    def test_long_short_mirror(self):
        results = []
        for direction in ('LONG', 'SHORT'):
            c, L, geo = fixture(direction)
            results.append(self.scorer.evaluate(c, L, geometry=geo))
        self.assertEqual(results[0]['score'], results[1]['score'])
        for key in R.WEIGHTS:
            self.assertEqual(results[0]['components'][key]['score'], results[1]['components'][key]['score'])

    def test_wrong_geometry_side_not_reused(self):
        c, L, geo = fixture('SHORT')
        geo['geo_direction_view'] = 'LONG'
        r = self.scorer.evaluate(c, L, geometry=geo)
        for key in ('candles', 'volume', 'gann', 'fibonacci', 'lunar_calendar', 'confluence'):
            self.assertIsNone(r['components'][key]['score'])
        self.assertIsNotNone(r['components']['elliott']['score'])

    def test_volume_does_not_double_count_elliott(self):
        _, L, geo = fixture()
        signals = L['waves']['signals']
        signals.update(wave_start_n=1, wave_start_families='elliott_context')
        self.assertEqual(R._volume(L, geo)['score'], 50)

    def test_missing_wave_names_not_zero_evidence(self):
        _, L, geo = fixture()
        L['waves']['signals']['wave_start_families'] = None
        self.assertIsNone(R._volume(L, geo)['score'])

    def test_opposing_candle_penalizes_direction(self):
        c, L, geo = fixture()
        geo['candle_bias_last'] = 'bearish'
        r = self.scorer.evaluate(c, L, geometry=geo)
        self.assertEqual(r['components']['candles']['score'], 0)
        self.assertLess(r['components']['candles']['contribution_points'], 0)

    def test_provisional_elliott_discount(self):
        _, L, _ = fixture()
        view = L['elliott']['v2']['views']['LONG']
        view.update(provisional=True, state='impulse_provisional')
        self.assertEqual(R._elliott(L, 'LONG')['score'], 75)

    def test_future_pivot_is_not_scored(self):
        _, L, _ = fixture()
        L['elliott']['v2']['views']['LONG']['pivots'][-1]['confirmed_at'] = '2026-10-08'
        self.assertIsNone(R._elliott(L, 'LONG')['score'])

    def test_fib_requires_confirmed_anchors(self):
        _, L, geo = fixture()
        L['pivots']['confirmed'][0]['confirmed_at'] = '2026-10-09'
        self.assertIsNone(R._fibonacci(L, geo, 'LONG', 100, 2)['score'])

    def test_stale_fib_excluded(self):
        _, L, geo = fixture()
        L['fib']['v2']['stale'] = True
        self.assertIsNone(R._fibonacci(L, geo, 'LONG', 100, 2)['score'])

    def test_gann_does_not_use_known_bad_future_dates(self):
        _, _, geo = fixture()
        first = R._gann(geo, 'LONG', 100, 2)
        geo['exp_gann_next_time_date'] = '2099-01-01'
        self.assertEqual(first, R._gann(geo, 'LONG', 100, 2))

    def test_no_calendar_only_disables_calendar_dependent_blocks(self):
        c, L, geo = fixture()
        r = R.ResearchScorer([]).evaluate(c, L, geometry=geo)
        self.assertIsNone(r['components']['lunar_calendar']['score'])
        self.assertIsNone(r['components']['confluence']['score'])
        self.assertAlmostEqual(r['coverage'], .65)
        self.assertAlmostEqual(r['effective_research_weight'], .195)

    def test_scores_bounded(self):
        for base in (0, 50, 100):
            for score in (0, 50, 100):
                for weight in (0, .3, 1):
                    r = R.blend(base, {k: R.component(score, 'fixture') for k in R.WEIGHTS}, weight)
                    self.assertTrue(0 <= r['score'] <= 100)

    def test_invalid_config_and_numbers(self):
        for value in (-.1, 1.1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                R.validate_weight(value)
        self.assertIsNone(R.blend(float('nan'), {})['score'])
        self.assertEqual(R.blend(101, {})['status'], 'invalid_baseline')
        with self.assertRaises(ValueError):
            R.blend(50, {'gann': R.component(101, 'fixture')})

    def test_raw_crypto_momentum_is_not_percentile(self):
        c, L, geo = fixture()
        c['rank_basis'] = 'momentum_12_1 (crypto LONG, raw fallback)'
        r = self.scorer.evaluate(c, L, geometry=geo)
        self.assertEqual(r['score'], 75)
        self.assertEqual(r['coverage'], 0)

    def test_apply_idempotent_and_trade_fields_untouched(self):
        c, L, geo = fixture()
        original = copy.deepcopy((L['trade'], c['entry'], c['stop'], c['target'], c['_eg']))
        first = self.scorer.apply(c, L, geometry=geo)
        second = self.scorer.apply(c, L, geometry=geo)
        self.assertEqual(first, second)
        self.assertEqual(original, (L['trade'], c['entry'], c['stop'], c['target'], c['_eg']))
        self.assertEqual(c['rank_score'], L['score']['value'])
        self.assertEqual(c['rank_score'], L['context']['rank_score'])
        json.dumps(L, allow_nan=False)

    def test_evaluate_is_pure(self):
        c, L, geo = fixture()
        before = copy.deepcopy((c, L, geo))
        self.scorer.evaluate(c, L, geometry=geo)
        self.assertEqual(before, (c, L, geo))

    def test_rank_can_change_and_earnings_gate_still_applies(self):
        a, La, ga = fixture(ticker='A', base=75)
        b, Lb, gb = fixture(ticker='B', base=74)
        ga['candle_bias_last'] = 'bearish'
        La['waves']['signals'].update(wave_start_n=0, wave_start_families=None,
                                     wave_end_n=2, wave_end_families='climax,volume_exhaustion')
        baseline, _ = RUN.select([copy.deepcopy(a), copy.deepcopy(b)], 1, 0, 0)
        self.scorer.apply(a, La, geometry=ga)
        self.scorer.apply(b, Lb, geometry=gb)
        ranked, _ = RUN.select([a, b], 1, 0, 0)
        self.assertEqual(baseline[0]['t'], 'A')
        self.assertEqual(ranked[0]['t'], 'B')
        b['_eg']['blocked'] = True
        selected, blocked = RUN.select([a, b], 1, 0, 0)
        self.assertEqual(selected[0]['t'], 'A')
        self.assertEqual(blocked[0]['t'], 'B')

    def test_error_falls_back_without_excluding_candidate(self):
        c, L, _ = fixture()
        fake = types.SimpleNamespace(weight=.3, config_sha256='fixture', apply=lambda *a: (_ for _ in ()).throw(ValueError('fixture failure')))
        result = RUN.apply_research(c, L, None, fake)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(c['unified_score'], 75)
        self.assertEqual(L['score']['value'], 75)

    def test_decision_identity_and_naive_time_rejected(self):
        c, L, geo = fixture()
        L['data']['cutoff_utc'] = '2026-10-08T12:15:00'
        with self.assertRaises(ValueError):
            self.scorer.evaluate(c, L, geometry=geo)
        L['data']['cutoff_utc'] = '2026-10-08T12:15:00Z'
        L['direction'] = 'SHORT'
        with self.assertRaises(ValueError):
            self.scorer.evaluate(c, L, geometry=geo)

    def test_geometry_failure_retains_other_available_evidence(self):
        c, L, _ = fixture()
        with patch.object(R, 'geometry_at_cutoff', side_effect=RuntimeError('fixture geometry')):
            r = self.scorer.evaluate(c, L, bars=object())
        self.assertEqual(r['status'], 'partial')
        self.assertAlmostEqual(r['coverage'], .15)
        self.assertTrue(r['errors'])

    def test_real_geometry_is_invariant_to_later_bars(self):
        import numpy as np
        import pandas as pd
        dates = pd.bdate_range('2026-01-01', '2026-10-20')
        j = np.arange(len(dates))
        close = 100 + j * .04 + 7 * np.sin(j * .19)
        bars = pd.DataFrame(dict(Open=close-.3, High=close+1, Low=close-1, Close=close,
                                 Volume=1000000 + 10000*(j % 20)), index=dates)
        for direction in ('LONG', 'SHORT'):
            for date in ('2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07'):
                c, L, _ = fixture(direction)
                L['data'].update(last_bar=date, cutoff_utc=date+'T23:00:00Z')
                before = bars.loc[:date].copy()
                changed = bars.copy()
                changed.loc[changed.index > date, ['Open', 'High', 'Low', 'Close', 'Volume']] *= 10
                prefix = self.scorer.evaluate(c, L, bars=before)
                future = self.scorer.evaluate(c, L, bars=changed)
                self.assertEqual(prefix, future)
                self.assertEqual(prefix['errors'], [])

    def test_etf_uses_stock_bar_clock(self):
        fake_geo = types.SimpleNamespace(geometry_columns=lambda *args, **kw: {'clock_asset': args[2]})
        with patch.dict(sys.modules, scanner_geometry=fake_geo):
            out = R.geometry_at_cutoff(object(), '2026-10-08T12:15Z', 'etf', 'LONG')
        self.assertEqual(out['clock_asset'], 'stock')

    def test_hebrew_day_is_context_not_a_directional_bonus(self):
        _, _, geo = fixture()
        a = dict(lunar_status='ok', lunar_phase_deg=90, lunar_hebrew_day=7)
        b = dict(a, lunar_hebrew_day=23)
        self.assertEqual(R._clock_pair(a, geo), R._clock_pair(b, geo))

    def test_same_two_clock_relation_has_no_waxing_waning_preference(self):
        _, _, geo = fixture()
        geo.update(exp_gann_box_bars=8, exp_gann_origin_age_bars=10, exp_gann_end_age_bars=2)
        first = R._clock_pair(dict(lunar_status='ok', lunar_phase_deg=90), geo)
        geo.update(exp_gann_origin_age_bars=14, exp_gann_end_age_bars=6)
        second = R._clock_pair(dict(lunar_status='ok', lunar_phase_deg=270), geo)
        self.assertEqual(first['relation_strength'], second['relation_strength'])
        self.assertEqual(first['relation_strength'], 1)

    def test_clock_relation_depends_on_asset_age_and_records_confirmations(self):
        _, _, geo = fixture()
        a = R._clock_pair(dict(lunar_status='ok', lunar_phase_deg=0), geo)
        geo.update(exp_gann_origin_age_bars=10, exp_gann_end_age_bars=6)
        b = R._clock_pair(dict(lunar_status='ok', lunar_phase_deg=0), geo)
        self.assertEqual(a['relation_strength'], 1)
        self.assertEqual(b['relation_strength'], 0)
        self.assertEqual(a['anchors']['origin']['confirmed_at'], '2026-10-05')

    def test_missing_or_future_asset_clock_has_no_weight(self):
        c, L, geo = fixture()
        for changes in ({'exp_gann_box_bars': 0}, {'exp_gann_origin_age_bars': None},
                        {'exp_anchor_end_confirmed_at': '2026-10-08'}, {'exp_gann_end_age_bars': 999}):
            r = self.scorer.evaluate(c, L, geometry=dict(geo, **changes))
            self.assertIsNone(r['components']['lunar_calendar']['score'])
            self.assertIsNone(r['components']['confluence']['score'])
            self.assertEqual(r['clocks']['status'], 'missing')

    def test_clock_alignment_cannot_supply_trade_direction(self):
        clocks = dict(status='ok', relation_strength=1.0)
        blocks = {k: R.component(50, 'neutral fixture') for k in ('candles', 'volume')}
        self.assertEqual(R._lunar(clocks, blocks)['score'], 50)
        blocks = {k: R.component(0, 'opposing fixture') for k in ('candles', 'volume')}
        self.assertEqual(R._lunar(clocks, blocks)['score'], 0)

    def test_gann_score_invariant_to_price_currency_units(self):
        _, _, geo = fixture()
        a = R._gann(geo, 'LONG', 100, 2)
        cents = {k: v * 100 if k in ('exp_gann_level_above', 'exp_gann_level_below',
                                    'exp_gann_angle_above', 'exp_gann_angle_below') else v for k, v in geo.items()}
        self.assertEqual(a, R._gann(cents, 'LONG', 10000, 200))

    def test_volume_median_excludes_current_bar_and_handles_outlier(self):
        import numpy as np
        import pandas as pd
        import scanner_geometry as GEO
        close = 100 + np.arange(35) * .1
        volumes = np.full(35, 100.0)
        volumes[-2] = 10000
        volumes[-1] = 200
        bars = pd.DataFrame(dict(Open=close-.1, High=close+1, Low=close-1, Close=close, Volume=volumes),
                            index=pd.bdate_range('2026-08-01', periods=35))
        columns = GEO.candle_columns(bars)
        self.assertEqual(columns['candle_vol_ratio20_median'], 2)
        self.assertNotEqual(columns['candle_vol_ratio20_median'], columns['candle_vol_ratio20'])


class CalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calendar = LC.JerusalemCalendar([DATA])

    def test_exact_sunset_and_one_second_later(self):
        day = self.calendar.days[7]
        previous = self.calendar.features(LC.iso(day.start))
        after = self.calendar.features(LC.iso(day.start + timedelta(seconds=1)))
        self.assertNotEqual(previous['lunar_hebrew_day'], after['lunar_hebrew_day'])
        self.assertEqual(after['lunar_hebrew_day'], 27)
        self.assertEqual(self.calendar.features(LC.iso(day.start + timedelta(microseconds=500000)))['lunar_status'], 'sample_not_yet_available')

    def test_timezone_equivalent_decision_and_daily_sample(self):
        utc = self.calendar.features('2026-10-08T12:15:00Z')
        israel = self.calendar.features('2026-10-08T15:15:00+03:00')
        self.assertEqual(utc, israel)
        self.assertEqual(utc['lunar_sample_utc'], '2026-10-07T15:16:47Z')
        self.assertEqual(utc['lunar_hebrew_day'], 27)

    def test_outside_coverage_no_phase_zero(self):
        r = self.calendar.features('2026-11-10T12:00:00Z')
        self.assertEqual(r['lunar_status'], 'out_of_calendar_coverage')
        self.assertIsNone(r['lunar_phase_deg'])


class PipelineFixtureTest(unittest.TestCase):
    def test_unified_universe_not_cut_by_legacy_environment_top_n(self):
        import os
        import pandas as pd
        # Candidate filtering is pure; forbid the unrelated network client in this offline test.
        network = types.SimpleNamespace(post=lambda *a, **kw: (_ for _ in ()).throw(AssertionError('network forbidden')))
        with patch.dict(sys.modules, requests=network):
            import scanner_platforms as SP
        common = dict(mcap_ok=True, mcap_b=10, dolvol_m=20, px=100, sma50=90, sma200=80,
                      slope50='up', ext20atr=1, initial_stop=92, r60=10, short_rule_pass=False,
                      short_initial_stop=None, short_ck_score=0, momentum_score_short=20,
                      sector_etf='TEST', tp_half_1618=115, tp_half_fallback=False)
        frame = pd.DataFrame([dict(common, t='AA', momentum_score=80), dict(common, t='BB', momentum_score=79)])
        with patch.dict(os.environ, PLATFORM_TOP_LONG='1', PLATFORM_TOP_SHORT='1'), \
             patch.object(SP, 'MAX_PER_SECTOR', 0), patch.object(SP.pd, 'read_csv', return_value=frame):
            self.assertEqual(len(SP.select_candidates('fixture', 100000, 100000)), 1)
            self.assertEqual(len(SP.select_candidates('fixture', 100000, 100000, respect_env=False)), 2)

    def test_report_and_tracker_show_weighted_result(self):
        import unified_report as UR
        c, L, geo = fixture()
        R.ResearchScorer([DATA]).apply(c, L, geometry=geo)
        c['_levels'] = L
        c['_selected'] = True
        res = dict(regime={}, cands=[c], rows=[{}], models={}, raw={}, enabled=False,
                   stats={}, spent=0, budget=0, research_weight=.3)
        temp_parent = ROOT / 'tests' / '.tmp'
        temp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_parent) as directory:
            (Path(directory) / 'scan_raw.csv').write_text('t\nTEST\n', encoding='utf-8')
            with patch.object(UR, '_pdf', return_value=None):
                paths = UR.write_report(directory, res)
            report = Path(paths['md']).read_text(encoding='utf-8')
            self.assertIn('30%', report)
            self.assertIn('שקלול מחקר ניסיוני', report)
            self.assertIn('תרומה בנקודות', report)
            self.assertNotIn('**ניסיוני (משקל 0):** אליוט', report)
        row = LF.tracker_row(L, 'fixture|TEST|LONG', '2026-10-08')
        self.assertEqual(row['unified_score'], c['unified_score'])
        self.assertEqual(row['research_effective_weight'], .3)
        self.assertEqual(LF.facts_for_prompt(L)['research_score'], L['research_score'])

    def test_main_paper_pipeline_serializes_score_before_selection(self):
        import pandas as pd
        c, L, geo = fixture()
        temp_parent = ROOT / 'tests' / '.tmp'
        temp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_parent) as directory:
            fake_sp = types.SimpleNamespace(MAX_PER_SECTOR=0, regime_summary=lambda _: {}, select_candidates=lambda *a, **kw: [c])
            fake_lf = types.SimpleNamespace(build=lambda *a: (copy.deepcopy(L), object()),
                                           earnings_gate=lambda *a: {'status': 'ok', 'blocked': False},
                                           save=LF.save, apply_trade=LF.apply_trade, path=LF.path,
                                           facts_for_prompt=lambda _: {}, entry_session=LF.entry_session)
            args = ['scan', '--run-dir', directory, '--paper', '--no-models', '--no-crypto', '--no-hooks',
                    '--no-research-columns', '--no-tool-stats', '--research-calendar', str(DATA)]
            with patch.dict(sys.modules, scanner_platforms=fake_sp, scanner_levelsfile=fake_lf), \
                 patch.object(sys, 'argv', args), patch.object(RUN, 'cutoff_of', return_value=pd.Timestamp('2026-10-08T12:15Z')), \
                 patch.object(R, 'geometry_at_cutoff', return_value=geo), patch.object(RUN, 'append_paper', return_value=0):
                RUN.main()
            saved = json.loads((Path(directory) / 'levels/TEST.json').read_text(encoding='utf-8'))
            audit = json.loads((Path(directory) / 'research_scores.json').read_text(encoding='utf-8'))
            table = pd.read_csv(Path(directory) / 'candidates_full.csv')
            self.assertAlmostEqual(saved['score']['value'], audit[0]['score'])
            self.assertAlmostEqual(table.iloc[0]['unified_score'], audit[0]['score'])
            self.assertNotEqual(table.iloc[0]['unified_score'], table.iloc[0]['baseline_score'])
            self.assertIn('baseline_would_select', table)
            self.assertEqual(saved['trade'], L['trade'])
            self.assertIn('content_hash', saved)


if __name__ == '__main__':
    unittest.main()
