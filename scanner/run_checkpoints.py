#!/usr/bin/env python3
"""Checkpoint runner for OPEN positions (learning loop, platforms-learning-loop-addendum-2026-10-08.txt).
Per open position in /workspace/scan-runs/positions_registry.csv (weekly-scan recommendations only; never paper / trial rows):
  1. update from real daily closes (entry = next session open; the bot's own stop rule via scanner_stops.stop_status, close-checked;
     day-20 time exit) -> closed positions get ret_dir / bench_ret / excess_dir (direction x (stock - SPY|BTC));
  2. at trading day 5 and 10: FREE technical re-run with data up to that close (levels JSON via scanner_levelsfile.build -> SMA50/200,
     Elliott v1+v2 recount, Fib, VA120, S/R, waves, ATR stop) + chart (scanner_charts.render_from_levels);
  3. Jev gate on NEW Alpaca headlines since the previous decision point (trusted text only);
  4. cost gate: Grok / Perplexity / Claude / GPT re-research FRESH only if a trigger fired (scanner_lessons.triggers), else ledger rows
     'skipped - no material change';
  5. right/wrong scoring of closed positions + per-platform scoreboard; weekly lessons (closed trades only) -> prompts/<p>_vN.txt.
Flags: --asof ISO (default now) --no-models (zero LLM calls; Jev too) --budget USD (default 1.0) --max-llm-positions N --lessons
       --sim-from-run RUN --sim-cutoff ISO  (dry-run plumbing test: builds a SIMULATED registry/ledger/prompts in --out, never the real files)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, argparse, math, shutil, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, _SCANNER_ROOT)
import scanner_lessons as SLS, scanner_levelsfile as LF, scanner_stops as ST, stop_policy as SPOL

SKIP = 'skipped - no material change'
PLATS = ('jev', 'grok', 'pplx', 'claude', 'gpt')

def log(*a): print('[checkpoints]', *a, flush=True)

def _f(v):
    try: v = float(v); return v if math.isfinite(v) else None
    except Exception: return None

def px_dir_for(asof): return f"{_SCANNER_ROOT}/scanner-momentum-cache/{pd.Timestamp(asof).tz_convert('UTC').strftime('%Y%m%dT%H%MZ')}"

def get_bars(t, asset, asof, cp_dir):
    """same sources as the scan: Yahoo cache (stocks) / Alpaca daily (crypto, saved under <cp_dir>/bars/crypto for the levels JSON)."""
    if asset == 'crypto':
        import scanner_crypto as SCR
        x = SCR.alpaca_daily(t, pd.Timestamp(asof).tz_convert('UTC'))
        if x is not None:
            os.makedirs(f'{cp_dir}/bars/crypto', exist_ok=True); x.to_csv(SCR.bars_path(cp_dir, t))
        return x
    return ST.daily_bars(t, 'stock', pd.Timestamp(asof).tz_convert('UTC'), px_dir_for(asof))

def half_exit(stp, exit_date=None):
    """(half_price, half_date) of the 1/2 take-profit if it was taken on or before the exit close, else (None, None)."""
    if not stp.get('half_taken') or not stp.get('half_date'): return None, None
    if exit_date is not None and pd.Timestamp(stp['half_date']) > pd.Timestamp(exit_date): return None, None
    return _f(stp.get('half_price')), stp['half_date']

def sessions_after(x, entry_session):
    return x[x.index >= pd.Timestamp(entry_session)]

def news_file(cp_dir, t, asset, cut, since):
    """Alpaca/Benzinga headlines created in [since, cut) -> <cp_dir>/news_checkpoint_<T>.json (load_headlines layout)."""
    import scanner_news as SN
    days = max(1, int(math.ceil((pd.Timestamp(cut) - pd.Timestamp(since)).total_seconds() / 86400)) + 1)
    sym = f'{t}-USD' if asset == 'crypto' else t
    try: arts = list(SN.fetch_news_pit(sym, pd.Timestamp(cut).to_pydatetime(), lookback_days=min(days, 14)))
    except Exception as e: arts = []; log('news failed', t, e)
    f = f'{cp_dir}/news_checkpoint_{t}.json'
    json.dump({'meta': {'cutoff_utc': str(cut), 'since_utc': str(since), 'source': 'Alpaca News API (Benzinga)'}, 'news': {t: arts}},
              open(f, 'w'), ensure_ascii=False, default=str)
    return f, len(arts)

def ledger_rows(T, dp, asof_local, cut, cp_dir, models, outs, costs, trig, skipped, prompt_version, is_sim):
    rows = []
    for p in PLATS:
        o = outs.get(p); err = outs.get(p + '_err')
        verdict = conv = risk = act = None
        if isinstance(o, dict):
            if p == 'jev':
                verdict = o.get('sentiment_label'); risk = o.get('top_catalyst')
            elif p == 'grok': verdict, conv, risk = o.get('verdict'), o.get('sentiment'), o.get('reason_he')
            elif p == 'pplx': verdict, risk = o.get('verdict'), o.get('reason_he')
            elif p == 'claude': verdict, conv, risk = o.get('direction_view'), o.get('conviction'), o.get('key_risk_he')
            elif p == 'gpt': verdict, risk = o.get('verdict'), o.get('main_risk_he')
            act = o.get('checkpoint_action')
        cd = (o or {}).get('chart_count_disagree') if isinstance(o, dict) else None
        rows.append({'trade_key': T['trade_key'], 'ticker': T['ticker'], 'asset': T['asset'], 'direction': T['direction'], 'decision_point': dp,
                     'asof_local': asof_local, 'data_cutoff_utc': str(cut), 'run_dir': cp_dir, 'platform': p, 'model': models.get(p),
                     'role': {'claude': 'analyst', 'gpt': 'devils_advocate'}.get(p, 'checker'), 'prompt_version': prompt_version(p)[0],
                     'verdict': verdict, 'conviction_or_sentiment': conv, 'main_risk_or_reason': risk, 'checkpoint_action': act,
                     'cost_usd_this_pass': round(costs.get(p, 0.0), 5), 'fresh': o is not None,
                     'skipped_reason': (SKIP if (skipped and p != 'jev') else err), 'trigger': ' ; '.join(trig) or None,
                     'chart_count_disagree': None if not cd else f"{cd.get('disagree')}: {cd.get('reason_he') or ''}",
                     'image_input': None if not isinstance(o, dict) or p == 'jev' else ('image' if o.get('_image') else 'text'),
                     'entry_ref': T.get('entry_ref'), 'stop': T.get('current_stop'), 'target': T.get('target'), 'earnings_gate': None,
                     'trial': bool(is_sim), 'is_trial': bool(is_sim), 'forward_only_from': SLS.FORWARD_FROM, 'weight': 0})
    return rows

def run(asof, registry, ledger, out_dir, budget_usd=1.0, no_models=False, max_llm=99, lessons=False, is_sim=False):
    import scanner_platforms as SP
    asof = pd.Timestamp(asof); asof = asof.tz_localize('Asia/Jerusalem') if asof.tzinfo is None else asof
    asof = asof.tz_convert('UTC')
    cp_dir = f"{out_dir}/{asof.tz_convert('Asia/Jerusalem'):%Y-%m-%d_%H%M}"; os.makedirs(cp_dir, exist_ok=True)
    reg = SLS.load_registry(registry)
    budget = SP.Budget(budget_usd, f'{cp_dir}/platform_costs.json'); budget.credit = set(); budget.save()
    models = {'jev': SP.JEV_MODEL, 'grok': SP.GROK_MODEL, 'pplx': SP.PPLX_MODEL, 'claude': SP.CLAUDE_MODEL, 'gpt': SP.GPT_MODEL}
    summary = {'asof_utc': str(asof), 'cp_dir': cp_dir, 'open_before': int((reg.status == 'open').sum()), 'checkpoints': [], 'closed': [], 'pending_entry': []}
    all_rows, n_llm = [], 0
    for i, T in reg[reg.status == 'open'].iterrows():
        T = T.to_dict(); t, asset, d = T['ticker'], T['asset'], T['direction']; sgn = 1 if d == 'LONG' else -1
        x = get_bars(t, asset, asof, cp_dir)
        if x is None or not len(x): log('no bars', t); continue
        s = sessions_after(x, T['entry_session'])
        if not len(s): summary['pending_entry'].append(t); continue
        fill = _f(s.Open.iloc[0]); reg.at[i, 'entry_fill'] = fill; reg.at[i, 'entry_price'] = fill
        tp = _f(T.get('target')) if (asset == 'stock' and d == 'LONG') else None
        done = set(filter(None, str(T.get('checkpoints_done') or '').split(',')))
        prev = json.loads(T['last_state']) if isinstance(T.get('last_state'), str) and T['last_state'].startswith('{') else {}
        last_dec = T.get('last_decision_utc') or T.get('cutoff_utc')
        # --- exit. 5x longs and intraday touch apply from 2026-11-07 only. The stored current_stop is a floor
        # (a recompute must not lower it) and a row that already has an exit is not replayed into a new one.
        floor = _f(T.get('current_stop'))
        committed = {'date': T.get('exit_date'), 'price': T.get('exit_price')} if str(T.get('exit_date') or '') not in ('', 'None', 'nan') else None
        stp = ST.stop_status(x, asset, d, T['entry_session'], fill, tp_half=tp, floor=floor, committed_exit=committed)
        exit_date = exit_px = reason = None
        if stp.get('stopped') and stp.get('stop_date'):
            k = int((s.index <= pd.Timestamp(stp['stop_date'])).sum())
            if k <= SLS.HORIZON: exit_date, exit_px, reason = stp['stop_date'], stp['stop_close'], 'סטופ'
        if exit_date is None and len(s) >= SLS.HORIZON:
            exit_date, exit_px, reason = str(s.index[SLS.HORIZON - 1].date()), _f(s.Close.iloc[SLS.HORIZON - 1]), f'יום {SLS.HORIZON}'
        # --- day 5 / 10 checkpoints (each at ITS close, point-in-time), only if still open at that day
        for day in (5, 10):
            tag = f'd{day}'
            if tag in done or len(s) < day: continue
            dday = s.index[day - 1]
            if exit_date and pd.Timestamp(exit_date) <= dday: continue
            cut = SLS.close_cut(dday, asset)
            c = {'t': t, 'asset': asset, 'direction': d, 'entry': _f(T.get('entry_ref')), 'stop': None, 'target': _f(T.get('target')), 'date': str(dday.date())}
            xs = x[x.index <= dday]
            if asset == 'crypto':
                import scanner_crypto as SCR; xs.to_csv(SCR.bars_path(cp_dir, t))
            try:
                L, xb = LF.build(c, cp_dir, cut, px_dir_for(asof)); L['earnings'] = {'status': 'checkpoint (not re-gated)'}
                st_d = ST.stop_status(xs, asset, d, T['entry_session'], fill, tp_half=tp, floor=floor)
                L['trade']['stop'] = st_d.get('next_level'); L['trade']['stop_rule'] = 'scanner_stops.stop_status (live, at this checkpoint)'
                LF.save(L, cp_dir, c); LF.apply_trade(c, L)
                try: c['_chart_png'] = LF.render(cp_dir, c, xb)['png']
                except Exception as e: log('chart failed', t, e)
            except Exception as e:
                log('technical re-run failed', t, e); continue
            cur = SLS.snapshot_state(L, st_d, d)
            close_d = _f(xs.Close.iloc[-1]); unreal = sgn * (close_d / fill - 1) if fill else None
            # Jev gate on headlines since the previous decision point
            outs, costs = {}, {}
            jv = None
            if not no_models:
                nf, n_news = news_file(cp_dir, t, asset, cut, last_dec)
                jv = SP.jev_news(c, cp_dir, budget, cut, since_utc=last_dec, news_file=nf); outs['jev'] = jv
            trig = SLS.triggers(prev, cur, {'direction': d, 'target': T.get('target')}, jv)
            call = bool(trig) and not no_models and n_llm < max_llm
            if call:
                n_llm += 1
                c['_checkpoint'] = {'decision_point': tag, 'trading_day': day, 'entry_session': T['entry_session'], 'entry_fill': fill,
                                    'close_at_checkpoint': close_d, 'unrealized_dir_pct': None if unreal is None else round(100 * unreal, 2),
                                    'current_stop_rule_level': st_d.get('next_level'), 'triggers_he': trig,
                                    'technical_snapshot_now': cur, 'technical_snapshot_previous': prev}
                facts = SP.setup_facts(c, {}); today = pd.Timestamp(cut).date()
                g, outs['grok_err'] = SP.grok(c, facts, budget, today, asof_utc=cut)
                p, outs['pplx_err'] = SP.pplx(c, facts, budget, today)
                heads = (jv or {}).get('for_claude'); trusted = (jv or {}).get('trusted_context')
                a, outs['claude_err'] = SP.analyst(c, facts, g, p, budget, heads=heads, trusted=trusted)
                v, outs['gpt_err'] = SP.advocate(c, facts, g, p, a, budget, heads=heads, trusted=trusted)
                outs.update(grok=g, pplx=p, claude=a, gpt=v)
            for xlog in budget.log:
                if xlog.get('ticker') == t and not xlog.get('_counted'):
                    pl = 'grok' if xlog['platform'] == 'grok_cache' else xlog['platform']
                    costs[pl] = costs.get(pl, 0) + (xlog.get('cost_usd') or 0); xlog['_counted'] = True
            Tn = dict(T, current_stop=st_d.get('next_level'))
            all_rows += ledger_rows(Tn, tag, str(pd.Timestamp(cut).tz_convert('Asia/Jerusalem')), cut, cp_dir, models, outs, costs, trig,
                                    skipped=not call, prompt_version=SP.prompt_version, is_sim=is_sim)
            done.add(tag); prev = cur; last_dec = str(cut)
            summary['checkpoints'].append({'ticker': t, 'direction': d, 'day': day, 'triggers': trig, 'llm_called': call,
                                           'jev': None if not jv else {k: jv.get(k) for k in ('n_headlines', 'n_material', 'sentiment_label')},
                                           'unrealized_dir_pct': None if unreal is None else round(100 * unreal, 2), 'stop': st_d.get('next_level'),
                                           'actions': {p: (outs.get(p) or {}).get('checkpoint_action') for p in ('grok', 'pplx', 'claude', 'gpt') if outs.get(p)}})
        # --- registry update
        lc = _f(x.Close.iloc[-1])
        reg.at[i, 'checkpoints_done'] = ','.join(sorted(done)); reg.at[i, 'last_state'] = json.dumps(prev, default=str)
        reg.at[i, 'last_decision_utc'] = last_dec; reg.at[i, 'last_close'] = lc; reg.at[i, 'last_close_date'] = str(x.index[-1].date())
        live = stp.get('next_level')
        if floor is not None and live is not None: live = SPOL.ratchet(d, floor, live)   # never publish a looser stop than the one already live
        reg.at[i, 'current_stop'] = live
        if _f(T.get('stop_initial_fill')) is None: reg.at[i, 'stop_initial_fill'] = stp.get('initial_stop')
        hp, hd = half_exit(stp, exit_date)
        reg.at[i, 'half_taken'] = None if 'half_taken' not in stp else bool(hd)
        reg.at[i, 'half_date'] = hd; reg.at[i, 'half_price'] = hp
        reg.at[i, 'unrealized_dir'] = None if not fill else round(sgn * (lc / fill - 1), 5)
        reg.at[i, 'unrealized_dir_weighted'] = None if not fill else round(ST.weighted_return(d, fill, lc, hp), 5)
        if exit_date:
            b = SLS.bench(asset, asof)
            bb = b[(b.index >= pd.Timestamp(T['entry_session'])) & (b.index <= pd.Timestamp(exit_date))] if b is not None else None
            br = (float(bb.Close.iloc[-1] / bb.Open.iloc[0] - 1)) if bb is not None and len(bb) else None
            rd = sgn * (exit_px / fill - 1); rw = ST.weighted_return(d, fill, exit_px, hp)
            reg.loc[i, ['status', 'exit_date', 'exit_price', 'exit_reason', 'ret_dir', 'bench_ret', 'excess_dir', 'ret_dir_weighted', 'excess_dir_weighted']] = \
                ['closed', exit_date, exit_px, reason, round(rd, 5), None if br is None else round(br, 5), None if br is None else round(rd - sgn * br, 5),
                 round(rw, 5), None if br is None else round(rw - sgn * br, 5)]
            summary['closed'].append({'ticker': t, 'direction': d, 'exit_date': exit_date, 'reason': reason, 'ret_dir': round(rd, 4),
                                      'excess_dir': None if br is None else round(rd - sgn * br, 4), 'ret_dir_weighted': round(rw, 4),
                                      'excess_dir_weighted': None if br is None else round(rw - sgn * br, 4), 'half_date': hd, 'half_price': hp})
    SLS.save_registry(reg, registry)
    if all_rows: SP.append_ledger(all_rows, ledger)
    budget.save()
    # --- scoring + scoreboard (closed positions; forward rows only for the real ledger)
    S = pd.DataFrame()
    if os.path.exists(ledger):
        lg = pd.read_csv(ledger)
        if not is_sim:
            lg = lg[~lg.get('is_trial', pd.Series(False, index=lg.index)).astype(str).str.lower().eq('true')]
            lg = lg[lg.asof_local.astype(str).str[:10] >= SLS.FORWARD_FROM]
        S = SLS.score(lg, SLS.load_registry(registry), asof)
    sb = SLS.scoreboard(S); sb.to_csv(f'{cp_dir}/scoreboard.csv', index=False)
    if len(S): S.to_csv(f'{cp_dir}/scored_rows.csv', index=False)
    summary['scoreboard'] = sb.to_dict('records'); summary['spent_usd'] = round(budget.spent, 4)
    summary['ledger_rows_written'] = len(all_rows); summary['llm_positions'] = n_llm
    summary['skipped_rows'] = sum(1 for r in all_rows if r['skipped_reason'] == SKIP)
    if lessons or asof.tz_convert('Asia/Jerusalem').weekday() == 6:      # weekly (Sunday run, before Monday's scan) or forced
        summary['lessons'] = SLS.build_weekly_lessons(S, asof)
    json.dump(summary, open(f'{cp_dir}/checkpoint_summary.json', 'w'), ensure_ascii=False, indent=1, default=str)
    return summary

def build_sim(run_dir, sim_cut, out_dir):
    """dry-run fixture: the trial run's selected names re-entered at a PAST cutoff (levels rebuilt point-in-time at sim_cut).
    Entry verdicts are COPIED from the trial ledger (look-ahead -> plumbing test only, is_sim=True, never measured)."""
    sim_cut = pd.Timestamp(sim_cut); sim_cut = sim_cut.tz_localize('UTC') if sim_cut.tzinfo is None else sim_cut.tz_convert('UTC')
    os.makedirs(out_dir, exist_ok=True)
    reg_p, led_p = f'{out_dir}/positions_registry_SIM.csv', f'{out_dir}/platform_verdicts_ledger_SIM.csv'
    for f in (reg_p, led_p):
        if os.path.exists(f): os.remove(f)
    sel = json.load(open(f'{run_dir}/selected.json')) if os.path.exists(f'{run_dir}/selected.json') else None
    full = pd.read_csv(f'{run_dir}/candidates_full.csv') if os.path.exists(f'{run_dir}/candidates_full.csv') else pd.read_csv(f'{run_dir}/platform_enrichment.csv').rename(columns={'t': 'ticker'})
    if sel: full = full[[f'{a}|{b}' in sel for a, b in zip(full.ticker, full.direction)]]
    elif 'selected' in full: full = full[full.selected.astype(str).str.lower() == 'true']
    full = full.head(12)
    sim_dir = f'{out_dir}/sim_entry'; os.makedirs(sim_dir, exist_ok=True)
    tl = pd.read_csv((_SCANNER_ROOT + '/scan-runs/platform_verdicts_ledger_trial.csv'))
    rows, led = [], []
    for _, r in full.iterrows():
        asset = r.get('asset') if isinstance(r.get('asset'), str) else 'stock'
        c = {'t': r.ticker, 'asset': asset, 'direction': r.direction, 'entry': None, 'stop': None, 'target': None}
        try:
            if asset == 'crypto':
                import scanner_crypto as SCR
                xx = SCR.alpaca_daily(r.ticker, sim_cut); os.makedirs(f'{sim_dir}/bars/crypto', exist_ok=True); xx.to_csv(SCR.bars_path(sim_dir, r.ticker))
            L, x = LF.build(c, sim_dir, sim_cut, px_dir_for(sim_cut)); LF.save(L, sim_dir, c)
        except Exception as e:
            log('sim levels failed', r.ticker, e); continue
        es = LF.entry_session(sim_cut) if asset != 'crypto' else (sim_cut.normalize() + pd.Timedelta(days=1)).tz_localize(None)
        key = f"{r.ticker}|{r.direction}|{L['data']['last_bar']}"
        rows.append({'trade_id': f'SIM|{key}', 'trade_key': key, 'ticker': r.ticker, 'asset': asset, 'direction': r.direction, 'source_run': sim_dir,
                     'cutoff_utc': str(sim_cut), 'entry_session': str(pd.Timestamp(es).date()), 'entry_ref': L['trade'].get('entry'),
                     'stop_initial': L['trade'].get('stop'), 'target': L['trade'].get('target'), 'atr14_at_cutoff': (L.get('technical') or {}).get('atr14_wilder'),
                     'levels_file': LF.path(sim_dir, c), 'status': 'open', 'checkpoints_done': '', 'last_decision_utc': str(sim_cut),
                     'last_state': json.dumps(SLS.snapshot_state(L, None, r.direction), default=str), 'is_trial': True, 'is_sim': True})
        e = tl[(tl.ticker == r.ticker) & (tl.direction == r.direction)].copy()
        if len(e):
            e = e[e.run_dir == e.run_dir.iloc[-1]].drop_duplicates('platform', keep='last')
            e['trade_key'] = key; e['decision_point'] = 'entry'; e['asof_local'] = str(sim_cut.tz_convert('Asia/Jerusalem')); led.append(e)
    reg = pd.DataFrame(rows)
    for k in SLS.REG_COLS:
        if k not in reg: reg[k] = None
    SLS.save_registry(reg, reg_p)
    if led: pd.concat(led).to_csv(led_p, index=False)
    return reg_p, led_p

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--asof', default=None); ap.add_argument('--no-models', action='store_true'); ap.add_argument('--budget', type=float, default=1.0)
    ap.add_argument('--max-llm-positions', type=int, default=99); ap.add_argument('--lessons', action='store_true')
    ap.add_argument('--registry', default=SLS.REGISTRY); ap.add_argument('--ledger', default=None)
    ap.add_argument('--out', default=(_SCANNER_ROOT + '/scan-runs/checkpoints'))
    ap.add_argument('--sim-from-run'); ap.add_argument('--sim-cutoff'); ap.add_argument('--sim-asof', nargs='*')
    a = ap.parse_args()
    if a.sim_from_run:
        out = a.out if a.out != (_SCANNER_ROOT + '/scan-runs/checkpoints') else (_SCANNER_ROOT + '/scan-runs/checkpoints_SIM')
        if os.path.exists(f'{out}/prompts'): shutil.rmtree(f'{out}/prompts')
        shutil.copytree((_SCANNER_ROOT + '/prompts'), f'{out}/prompts'); SLS.PROMPTS = f'{out}/prompts'   # never touch the real prompt versions
        reg_p, led_p = build_sim(a.sim_from_run, a.sim_cutoff, out)
        log('SIM registry', reg_p, 'ledger', led_p)
        res = []
        for k, s_asof in enumerate(a.sim_asof or [a.asof]):
            r = run(s_asof, reg_p, led_p, out, budget_usd=a.budget, no_models=a.no_models, max_llm=a.max_llm_positions,
                    lessons=(a.lessons and k == len(a.sim_asof or [1]) - 1), is_sim=True)
            res.append(r); log(s_asof, '->', json.dumps({k2: r[k2] for k2 in ('checkpoints', 'closed', 'spent_usd', 'skipped_rows', 'llm_positions')}, ensure_ascii=False, default=str)[:1500])
        json.dump(res, open(f'{out}/sim_results.json', 'w'), ensure_ascii=False, indent=1, default=str)
        return
    import scanner_platforms as SP
    r = run(a.asof or pd.Timestamp.now(tz='Asia/Jerusalem'), a.registry, a.ledger or SP.LEDGER, a.out, budget_usd=a.budget,
            no_models=a.no_models, max_llm=a.max_llm_positions, lessons=a.lessons)
    log(json.dumps({k: r[k] for k in ('open_before', 'checkpoints', 'closed', 'spent_usd', 'skipped_rows')}, ensure_ascii=False, default=str)[:3000])

if __name__ == '__main__':
    main()
