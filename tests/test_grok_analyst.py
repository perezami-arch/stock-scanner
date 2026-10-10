"""Offline role contracts: mocked providers, no live calls or trading-return claims."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import datetime as dt
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'modules'))
sys.path.insert(0, str(ROOT/'scanner'))
import scanner_platforms as SP
import scanner_lessons as SL
import scanner_levelsfile as LF
import unified_report as UR


def analysis(view='opposes', conviction=25):
    return dict(direction_view=view, conviction=conviction, thesis_he='מבנה המחיר אינו תומך בעסקה',
                technical_read_he='המבנה הטכני חלש', catalyst_read_he='אין קטליסט מאומת בנתונים',
                fundamental_read_he='חסרים נתונים פונדמנטליים', key_risk_he='שבירת המבנה', checkpoint_action='exit')


def grok_response():
    return dict(sentiment=2, confidence='high', n_posts_seen=8, verdict='approve', reason_he='השיח חיובי',
                key_points_he=['יש עניין בנכס'], notable_accounts=[], analyst=analysis(), checkpoint_action='hold',
                chart_count_disagree={'disagree':'no', 'reason_he':'הספירה נראית סבירה'})


class GrokAnalystTests(unittest.TestCase):
    def setUp(self):
        tmp = ROOT/'tests/.tmp'; tmp.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=tmp)
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.c = dict(t='TEST', asset='stock', direction='LONG', date='2026-10-09', entry=100., stop=92., target=115.,
                      rank_score=71., unified_score=71., baseline_score=70., target_note='fixture', rank_basis='fixture', _selected=True)
        self.facts = {'technical': {'rsi14':55, 'sma200':95}, 'trade': {'entry':100, 'stop':92, 'target':115}}
        self.posts = [dict(id=str(i), handle='fixture', text='טקסט לבדיקה', url=f'https://x.com/fixture/status/{i}') for i in range(8)]
        self.response = grok_response()
        self.requests = []
        self.env = patch.dict(os.environ, {'PLATFORM_JEV':'0', 'PLATFORM_GPT':'1', 'PLATFORM_REUSE_RAW':'', 'PLATFORM_TRIAL':'0'})
        self.env.start(); self.addCleanup(self.env.stop)
        (self.run/'run_meta.json').write_text(json.dumps({'scan_asof_local':'2026-10-12T09:00:00+03:00'}), encoding='utf-8')
        pd.DataFrame([{'t':'TEST'}]).to_csv(self.run/'scan_raw.csv', index=False)

    def provider(self, url, key, payload, timeout):
        self.requests.append(deepcopy(payload))
        if url == SP.XAI_URL:
            return {'usage':{'cost_in_usd_ticks':200000000}, 'output':[{'type':'message', 'content':[{'text':json.dumps(self.response, ensure_ascii=False)}]}]}
        if payload['model'] == SP.CLAUDE_MODEL:
            value = analysis('supports', 85)
        elif payload['model'] == SP.GPT_MODEL:
            value = dict(verdict='flag', main_risk_he='מחלוקת בניתוחים', reason_he='נדרש אישור נוסף',
                         case_against_he='יש ספק בנתונים', rebuttal_of_grok_he='גרוק חסר אישור לנימוק',
                         rebuttal_of_analyst_he='קלוד נותן משקל יתר למומנטום')
        else: raise AssertionError('Unexpected provider model')
        return {'usage':{'cost':0.03}, 'choices':[{'message':{'content':json.dumps(value, ensure_ascii=False)}}]}

    def stack(self, image=None, cache=True):
        stack = ExitStack()
        stack.enter_context(patch.object(SP, '_post', side_effect=self.provider))
        stack.enter_context(patch.object(SP, 'chart_data_url', return_value=image))
        stack.enter_context(patch.object(SP, 'load_x_cache', return_value=self.posts if cache else []))
        stack.enter_context(patch.object(SP, 'prompt_version', return_value=('v1','')))
        return stack

    def call_grok(self, c=None, image=None, cache=True, limit=1):
        budget = SP.Budget(limit, str(self.run/'costs.json')); budget.credit=set()
        with self.stack(image, cache):
            result = SP.grok(c or self.c, self.facts, budget, dt.date(2026,10,12), asof_utc='2026-10-12T06:00:00Z')
        return result, budget

    def run_platforms(self, enabled=True):
        with self.stack() as stack:
            stack.enter_context(patch.object(SP, 'setup_facts', return_value=deepcopy(self.facts)))
            stack.enter_context(patch.object(SP, 'regime_summary', return_value={'pit_cutoff_utc':'2026-10-12T06:00:00Z'}))
            stack.enter_context(patch.object(SP, 'pplx', return_value=({'verdict':'flag','reason_he':'אין קטליסט'},None)))
            stack.enter_context(patch.object(SP, 'LEDGER', str(self.run/'ledger.csv')))
            stack.enter_context(patch.object(SP, 'BUDGET_USD', 2))
            return SP.run_platforms([self.c], str(self.run), enabled=enabled)

    def test_cached_call_keeps_sentiment_and_opposing_analyst_separate(self):
        (g, error), budget = self.call_grok()
        self.assertIsNone(error)
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn('tools', self.requests[0])
        self.assertIn('sma200', self.requests[0]['input'])
        self.assertEqual(g['sentiment'], 2)
        self.assertEqual(g['verdict'], 'approve')
        self.assertEqual(SP.grok_analysis(g)['direction_view'], 'opposes')
        self.assertEqual(g['_role_version'], SP.GROK_ROLE_VERSION)
        self.assertEqual(g['chart_count_disagree']['disagree'], 'n/a')
        self.assertAlmostEqual(budget.spent, 0.02)

    def test_search_vision_path_has_both_roles_and_bot_facts(self):
        (g, error), _ = self.call_grok(image='data:image/png;base64,fixture', cache=False)
        self.assertIsNone(error)
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request['tools'][0]['type'], 'x_search')
        content = request['input'][0]['content']
        self.assertIn('sma200', content[0]['text'])
        self.assertIn('2026-10-12T06:00:00+00:00', content[0]['text'])
        self.assertEqual(content[1]['type'], 'input_image')
        self.assertTrue(SP.grok_analysis(g)['_image'])

    def test_invalid_analyst_preserves_valid_x_without_sentiment_fallback(self):
        for bad in [None, dict(analysis(), conviction=101), dict(analysis(), conviction=True), dict(analysis(), conviction=float('nan')),
                    dict(analysis(), direction_view='bullish'), dict(analysis(), thesis_he='')]:
            with self.subTest(bad=bad):
                self.response = dict(grok_response(), analyst=bad)
                (g, error), _ = self.call_grok()
                self.assertIsNone(error)
                self.assertEqual(g['sentiment'],2)
                self.assertIsNone(SP.grok_analysis(g))
                self.assertTrue(SP.grok_analyst_error(g))

    def test_checkpoint_actions_for_roles_can_disagree(self):
        c = dict(self.c, _checkpoint={'decision_point':'day5'})
        (g, error), _ = self.call_grok(c=c)
        self.assertIsNone(error)
        self.assertEqual(g['checkpoint_action'],'hold')
        self.assertEqual(SP.grok_analysis(g)['checkpoint_action'],'exit')

    def test_budget_skip_calls_no_provider(self):
        (g, error), _ = self.call_grok(limit=0)
        self.assertIsNone(g)
        self.assertIn('budget guard', error)
        self.assertEqual(self.requests, [])

    def test_full_weekly_path_reports_and_measures_both_roles_once(self):
        original = deepcopy(self.c)
        res = self.run_platforms()
        r = res['rows'][0]
        self.assertEqual(self.c, original)  # no levels, rank, or 30/70 mutation
        self.assertEqual(r['grok_analyst_conviction'],25)
        self.assertEqual(r['grok_sentiment'],2)
        self.assertIn('מחלוקת',r['analyst_comparison'])
        self.assertEqual(res['df']['platform_weight'].iloc[0],0)
        self.assertEqual(res['stats']['grok_analyst']['ok'],1)
        claude_request = next(x for x in self.requests if x['model'] == SP.CLAUDE_MODEL)
        gpt_request = next(x for x in self.requests if x['model'] == SP.GPT_MODEL)
        self.assertNotIn('grok_analyst', claude_request['messages'][-1]['content'])
        self.assertIn('grok_analyst', gpt_request['messages'][-1]['content'])
        self.assertIn('claude_analyst', gpt_request['messages'][-1]['content'])
        ledger = pd.read_csv(self.run/'ledger.csv').set_index('platform')
        self.assertEqual(ledger.loc['grok_analyst','role'],'analyst')
        self.assertEqual(ledger.loc['grok_analyst','conviction_or_sentiment'],25)
        self.assertEqual(ledger.loc['grok_analyst','cost_usd_this_pass'],0)
        self.assertAlmostEqual(ledger.cost_usd_this_pass.sum(),res['spent'])
        self.assertEqual(SL.call_of(ledger.loc['grok'].to_dict() | {'platform':'grok'}),1)
        self.assertEqual(SL.call_of(ledger.loc['grok_analyst'].to_dict() | {'platform':'grok_analyst'}),-1)
        with patch.object(UR,'_pdf',return_value=None), patch.object(LF,'load',return_value={}):
            report = UR.write_report(str(self.run),res)
        text = Path(report['md']).read_text(encoding='utf-8')
        for value in ['Grok, אנליסט נוסף',r['grok_analyst_thesis'],'נגד התזה של Grok','נגד התזה של Claude','השוואת האנליסטים']:
            self.assertIn(value,text)

    def test_legacy_reuse_requires_new_role_but_current_reuse_adds_no_xai_call(self):
        reuse = self.run/'earlier.json'
        reuse.write_text(json.dumps({'TEST':{'grok':{'sentiment':2,'verdict':'approve'}}}),encoding='utf-8')
        with patch.dict(os.environ,{'PLATFORM_REUSE_RAW':str(reuse)}):
            res = self.run_platforms()
            self.assertNotIn('grok',res['raw']['TEST']['reused_from_earlier_pass'])
            reuse.write_text(json.dumps(res['raw'],ensure_ascii=False),encoding='utf-8')
            self.requests.clear()
            res2 = self.run_platforms()
        self.assertIn('grok',res2['raw']['TEST']['reused_from_earlier_pass'])
        self.assertFalse(any(p['model'] == SP.GROK_MODEL for p in self.requests))
        ledger = pd.read_csv(self.run/'ledger.csv')
        last = ledger[ledger.platform=='grok_analyst'].iloc[-1]
        self.assertFalse(last.fresh)
        self.assertEqual(last.cost_usd_this_pass,0)

    def test_missing_grok_analysis_keeps_claude_gpt_and_x_evidence(self):
        self.response.pop('analyst')
        res = self.run_platforms()
        r = res['rows'][0]
        self.assertEqual(r['grok_sentiment'],2)
        self.assertIsNone(r['grok_analyst_conviction'])
        self.assertTrue(r['grok_analyst_error'])
        self.assertEqual(r['claude_conviction'],85)
        self.assertEqual(r['gpt_verdict'],'flag')
        self.assertIn('חסר ניתוח Grok',r['analyst_comparison'])
        request = next(x for x in self.requests if x['model'] == SP.GPT_MODEL)
        self.assertIn('"grok_analyst": null', request['messages'][-1]['content'])
        row = pd.read_csv(self.run/'ledger.csv').set_index('platform').loc['grok_analyst']
        self.assertFalse(row.fresh)
        self.assertTrue(pd.isna(row.verdict))

    def test_disabled_models_have_no_analyst_claim_or_calls(self):
        res = self.run_platforms(enabled=False)
        self.assertEqual(self.requests,[])
        self.assertIsNone(res['rows'][0]['grok_analyst_conviction'])
        self.assertFalse((self.run/'ledger.csv').exists())

    def test_checkpoint_ledger_and_scores_keep_analyst_separate(self):
        # The checkpoint runner's existing stop module depends on private Linux files.
        # Stub only that unrelated dependency; exercise the real ledger function.
        spec = importlib.util.spec_from_file_location('checkpoint_role_test',ROOT/'scanner/run_checkpoints.py')
        cp = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'scanner_stops':types.ModuleType('scanner_stops')}): spec.loader.exec_module(cp)
        (g,_),_ = self.call_grok(c=dict(self.c,_checkpoint={'decision_point':'day5'}))
        rows = cp.ledger_rows(dict(trade_key='TEST|LONG|2026-10-09',ticker='TEST',asset='stock',direction='LONG'),
                              'day5','2026-10-19','2026-10-19T20:00:00Z',str(self.run),{'grok':SP.GROK_MODEL},
                              {'grok':g,'grok_analyst':SP.grok_analysis(g)},{'grok':0.02},['fixture'],False,lambda p:('v1',''),False)
        by = {x['platform']:x for x in rows}
        self.assertEqual(by['grok_analyst']['checkpoint_action'],'exit')
        self.assertEqual(by['grok']['checkpoint_action'],'hold')
        self.assertEqual(sum(x['cost_usd_this_pass'] for x in rows),0.02)
        for direction in ['LONG','SHORT']:
            self.assertEqual(SL.call_of(dict(by['grok_analyst'],direction=direction)),-1)
        self.assertEqual(SL.call_of(dict(by['grok_analyst'],verdict='neutral',conviction_or_sentiment=95)),0)
        self.assertIsNone(SL.call_of(dict(by['grok_analyst'],conviction_or_sentiment=None)))
        self.assertIn('grok_analyst',SL.PLATFORMS)


if __name__ == '__main__': unittest.main()
