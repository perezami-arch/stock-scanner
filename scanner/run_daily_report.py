#!/usr/bin/env python3
"""Daily report (8:24 weekday routine, AFTER the --paper --no-models scan). Hebrew markdown + PDF -> /workspace/scan-runs/daily/<YYYY-MM-DD>/.
  0. OpenBB snapshot (idempotent): /workspace/venv-openbb/bin/python /workspace/openbb_snapshot.py -> /workspace/openbb-snapshots/<last NYSE session>/
  1. open positions (positions_registry.csv = weekly-scan recommendations only) updated from REAL closes; stop rule / day-20 exits;
  2. day-5 / day-10 checkpoints via run_checkpoints.run(): free technical re-run + chart, Jev gate FIRST, paid models only if triggered;
  3. closures today with each platform's right / wrong (entry + checkpoint verdicts, direction-adjusted excess vs SPY/BTC);
  4. tool_stats Hebrew section + per-platform scoreboard;
  5. paper trades: ONE line (count only) - they are never positions and never listed.
Flags: --asof ISO  --no-models (zero LLM calls incl. Jev)  --budget USD (default 1.0)  --no-openbb  --no-tool-stats  --tracker XLSX"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, argparse, subprocess, glob
import pandas as pd
sys.path.insert(0, _SCANNER_ROOT)
import scanner_lessons as SLS, run_checkpoints as RC

VERD_HE = {'approve': 'אישר', 'flag': 'דגל', 'veto': 'וטו', 'supports': 'תומך', 'opposes': 'מתנגד', 'neutral': 'ניטרלי'}
PL_HE = {'jev': 'Jev', 'grok': 'Grok', 'pplx': 'Perplexity', 'claude': 'Claude', 'gpt': 'GPT'}
DIRH = {'LONG': 'לונג', 'SHORT': 'שורט'}

def openbb():
    try:
        r = subprocess.run([(_SCANNER_ROOT + '/venv-openbb/bin/python'), (_SCANNER_ROOT + '/openbb_snapshot.py')], capture_output=True, text=True, timeout=1200)
        tail = (r.stdout or r.stderr or '').strip().splitlines()[-1:] or ['']
        return r.returncode, tail[0][:200]
    except Exception as e:
        return -1, f'{e.__class__.__name__}: {e}'[:200]

def update_paper(asof, path=None):
    """paper_trades_ledger.csv from real closes: entry = open of entry_session, stop = the same rule as positions (scanner_stops.stop_status:
    stock 4xATR chandelier on closes, crypto fixed 3xATR), half at the stock-long target, exit at the stop close or day 20; cum_d1..20 =
    direction-adjusted close return vs the fill. Paper rows never become positions and never enter the reports beyond one line."""
    import scanner_stops as ST
    path = path or os.environ.get('PAPER_LEDGER', (_SCANNER_ROOT + '/scan-runs/paper_trades_ledger.csv'))
    if not os.path.exists(path): return 0
    d = pd.read_csv(path, dtype=object); n = 0; cache = {}
    for i, r in d[d.status.isin(['pending_entry', 'open'])].iterrows():
        key = (r.ticker, r.asset)
        if key not in cache:
            try: cache[key] = RC.get_bars(r.ticker, r.asset, asof, '/tmp/paper_bars')
            except Exception: cache[key] = None
        x = cache[key]
        if x is None or not len(x): continue
        s = x[x.index >= pd.Timestamp(r.entry_session)]
        if not len(s): continue
        fill = float(s.Open.iloc[0]); sgn = 1 if r.direction == 'LONG' else -1
        tp = float(r.target_level) if (r.asset == 'stock' and r.direction == 'LONG' and pd.notna(r.target_level) and str(r.target_level) not in ('', 'nan')) else None
        st = ST.stop_status(x, r.asset, r.direction, r.entry_session, fill, tp_half=tp)
        if st.get('next_level') is None: d.loc[i, 'status'] = 'no active rule'; continue
        k0 = x.index.searchsorted(pd.Timestamp(r.entry_session)); A = ST.atr14(x.High.values, x.Low.values, x.Close.values)
        init = fill - sgn * float(r.stop_atr_mult) * float(A[k0 - 1] if k0 > 0 else A[-1])
        d.loc[i, ['entry_price', 'stop', 'status']] = [round(fill, 6), round(init, 6), 'open']
        for j in range(min(20, len(s))): d.loc[i, f'cum_d{j + 1}'] = round(sgn * (float(s.Close.iloc[j]) / fill - 1), 6)
        ex = None
        if st.get('stopped') and (s.index <= pd.Timestamp(st['stop_date'])).sum() <= 20: ex = (st['stop_date'], st['stop_close'], 'stop')
        elif len(s) >= 20: ex = (str(s.index[19].date()), float(s.Close.iloc[19]), 'day20')
        if ex: d.loc[i, ['status', 'exit_date', 'exit_price', 'exit_reason']] = ['closed', ex[0], ex[1], ex[2]]
        n += 1
    d.to_csv(path, index=False)
    return n

def paper_line():
    f = os.environ.get('PAPER_LEDGER', (_SCANNER_ROOT + '/scan-runs/paper_trades_ledger.csv'))
    if not os.path.exists(f): return 'עסקאות נייר: אין עדיין.'
    d = pd.read_csv(f)
    return (f"עסקאות נייר (לא פוזיציות, למדידת העמודות הניסיוניות בלבד): {len(d)} שורות, {d.alert_date.nunique()} ימי כניסה שונים, "
            f"{int((d.status.astype(str) == 'open').sum()) if 'status' in d else '—'} פתוחות.")

def half_cell(r):
    """'—' when the position has no half target (shorts, crypto, fallback), 'לא' before it is hit, else 'date @ price'."""
    hp = pd.to_numeric(pd.Series([r.get('half_price')]), errors='coerce').iloc[0]
    if pd.notna(hp) and str(r.get('half_date') or '') not in ('', 'nan', 'None'): return f"{r.half_date} @ {hp:.2f}"
    return 'לא' if str(r.get('half_taken')) in ('False', 'false', '0', '0.0') else '—'

def pct(v):
    try:
        v = float(v)
        return f"\u200e{100 * v:+.2f}%" if v == v else '—'
    except Exception: return '—'

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--asof', default=None); ap.add_argument('--no-models', action='store_true'); ap.add_argument('--budget', type=float, default=1.0)
    ap.add_argument('--no-openbb', action='store_true'); ap.add_argument('--no-tool-stats', action='store_true'); ap.add_argument('--tracker', default=None)
    ap.add_argument('--registry', default=SLS.REGISTRY); ap.add_argument('--ledger', default=None); ap.add_argument('--out', default=(_SCANNER_ROOT + '/scan-runs/daily'))
    a = ap.parse_args()
    import scanner_platforms as SP, run_unified_scan as RU, unified_report as UR
    asof = pd.Timestamp(a.asof) if a.asof else pd.Timestamp.now(tz='Asia/Jerusalem')
    if asof.tzinfo is None: asof = asof.tz_localize('Asia/Jerusalem')
    out = f"{a.out}/{asof.tz_convert('Asia/Jerusalem'):%Y-%m-%d}"; os.makedirs(out, exist_ok=True)
    ob = (None, 'דולג (--no-openbb)') if a.no_openbb else openbb()
    ledger = a.ledger or SP.LEDGER
    s = RC.run(asof, a.registry, ledger, f'{out}/checkpoints', budget_usd=a.budget, no_models=a.no_models)
    reg = SLS.load_registry(a.registry)
    L = []; w = L.append
    w(f"# דוח יומי – {asof.tz_convert('Asia/Jerusalem'):%d.%m.%Y %H:%M} (שעון ישראל)\n")
    w(f"- **OpenBB:** {'עודכן' if ob[0] == 0 else 'נכשל' if ob[0] not in (None, 0) else ''} {ob[1]}")
    w(f"- **עלות המודלים בריצה:** \u200e${s['spent_usd']:.3f} · שורות ביומן: {s['ledger_rows_written']} (מתוכן {s['skipped_rows']} 'אין שינוי מהותי') · "
      f"פוזיציות שהפעילו מודלים בתשלום: {s['llm_positions']}")
    w('- משקלי המודלים (critic_score v4, פעיל מ-29.10.2026): Grok, ‏Perplexity, ‏Claude, ‏GPT במשקל 1.0 · Jev במשקל 0. עמודות מחקר ניסיוניות נשארות במשקל 0.\n')
    # 1. open positions
    op = reg[reg.status == 'open']
    w(f'## 1. פוזיציות פתוחות ({len(op)})')
    if len(op):
        w('| טיקר | כיוון | כניסה | סגירה אחרונה | תשואה מכוונת | חצי ביעד | תשואה משוקללת | סטופ נוכחי | נקודות ביקורת |'); w('|---|---|---|---|---|---|---|---|---|')
        for _, r in op.iterrows():
            w(f"| {r.ticker} | {DIRH.get(r.direction, r.direction)} | {r.entry_fill or r.entry_ref} ({r.entry_session}) | {r.last_close or '—'} ({r.last_close_date or '—'}) | "
              f"{pct(r.unrealized_dir)} | {half_cell(r)} | {pct(r.unrealized_dir_weighted)} | {r.current_stop or '—'} | {r.checkpoints_done or '—'} |")
    else: w('אין פוזיציות פתוחות (הרישום מתחיל מהסריקה השבועית של 12.10).')
    if s['pending_entry']: w(f"\nממתינות לפתיחת המסחר (כניסה בפתיחה הבאה): {', '.join(s['pending_entry'])}")
    # 2. checkpoints
    w(f"\n## 2. נקודות ביקורת היום ({len(s['checkpoints'])})")
    for c in s['checkpoints']:
        j = c.get('jev') or {}
        w(f"- **{c['ticker']} {DIRH.get(c['direction'])} – יום {c['day']}:** תשואה מכוונת {pct((c.get('unrealized_dir_pct') or 0) / 100)} · סטופ {c.get('stop')} · "
          f"Jev: {j.get('n_headlines', '—')} כותרות, {j.get('n_material', '—')} מהותיות ({j.get('sentiment_label') or '—'}) · "
          + (f"טריגרים: {'; '.join(c['triggers'])} → מחקר מחדש: " + ', '.join(f"{PL_HE[p]}={v}" for p, v in c['actions'].items())
             if c['llm_called'] else ('אין שינוי מהותי – המודלים בתשלום לא נקראו' if not c['triggers'] else f"טריגרים: {'; '.join(c['triggers'])} (מעבר לתקרה, לא נקראו)")))
    # 3. closures
    w(f"\n## 3. סגירות ({len(s['closed'])})")
    sc = pd.read_csv(f"{s['cp_dir']}/scored_rows.csv") if os.path.exists(f"{s['cp_dir']}/scored_rows.csv") else pd.DataFrame()
    for c in s['closed']:
        hh = f" · חצי מומש {c['half_date']} ב-{c['half_price']:.2f}, תשואה משוקללת {pct(c.get('ret_dir_weighted'))} (מול המדד {pct(c.get('excess_dir_weighted'))})" if c.get('half_date') else ''
        w(f"- **{c['ticker']} {DIRH.get(c['direction'])}** נסגר {c['exit_date']} ({c['reason']}): תשואה מכוונת {pct(c['ret_dir'])}, מול המדד {pct(c['excess_dir'])}{hh}")
        g = sc[sc.ticker == c['ticker']] if len(sc) else sc
        for _, r in g.iterrows():
            res = 'צדק' if r.right is True or str(r.right) == 'True' else 'טעה' if str(r.right) == 'False' else 'ללא הכרעה'
            w(f"  - {PL_HE.get(r.platform, r.platform)} ({r.decision_point}): {VERD_HE.get(str(r.verdict), r.verdict)} → {res}")
    # 4. scoreboard + tool_stats
    w('\n## 4. לוח תוצאות לפי פלטפורמה (פוזיציות סגורות בלבד)')
    sb = pd.DataFrame(s['scoreboard'])
    if len(sb):
        w('| פלטפורמה | נקודת החלטה | הכרעות | צדק | טעה | שיעור פגיעה | ימי כניסה שונים |'); w('|---|---|---|---|---|---|---|')
        for _, r in sb.iterrows():
            w(f"| {PL_HE.get(r.platform, r.platform)} | {r.decision_point} | {r.n_calls} | {r.right} | {r.wrong} | {r.hit_rate if pd.notna(r.hit_rate) else '—'} | {r.distinct_entry_days} |")
    else: w('אין עדיין פוזיציות סגורות.')
    if not a.no_tool_stats:
        md, err = RU.tool_stats(a.tracker or RU.latest_tracker())
        w('\n## 5. סטטיסטיקת כלים (tool_stats)\n'); w(md if md else f'_לא זמין: {err}_')
    try: update_paper(asof)
    except Exception as e: print('paper update failed:', e)
    w(f'\n## 6. עסקאות נייר\n{paper_line()}')
    mdp = f'{out}/daily_report_he.md'; open(mdp, 'w').write('\n'.join(L) + '\n')
    try: UR._pdf(open(mdp).read(), f'{out}/daily_report_he.pdf', base=out)
    except Exception as e: print('pdf failed:', e)
    print(json.dumps({'md': mdp, 'pdf': f'{out}/daily_report_he.pdf', 'spent_usd': s['spent_usd']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
