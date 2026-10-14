"""Frozen forward research cohorts, separate from the bot's stop-based positions.

Scores never learn from their own outcomes. Daily updates add observations and
5/10/20-session open-to-close labels; reports keep versions/modes separate.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import numbers
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

VERSION = 'forward-research-1.0'
HORIZONS = (5, 10, 20)
FORWARD_FROM = '2026-10-12'


def utc(value):
    d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Research timestamps must include a timezone')
    return d.astimezone(timezone.utc)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, numbers.Real):
        return float(value) if math.isfinite(value) else None
    if hasattr(value, 'item'):
        return clean(value.item())
    raise TypeError(f'Unexpected snapshot value: {type(value).__name__}')


def immutable_json(path, payload):
    """Idempotent replay is allowed; changing an existing snapshot is an error."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as f:
            f.write(canonical(payload) + '\n')
    except FileExistsError:
        if json.loads(path.read_text(encoding='utf-8')) != payload:
            raise ValueError(f'Frozen research snapshot conflict: {path}; use a new run folder')


def freeze_run(run_dir, cutoff, mode, rows, levels, manifest, entry_sessions, selection, frozen_at=None):
    """Capture ALL eligible candidates and both rankings BEFORE future outcomes.

    entry_sessions maps asset to its next open session under the existing scanner
    convention. Replayed runs are marked late and excluded from forward summaries.
    """
    if mode not in ('weekly', 'paper', 'trial'):
        raise ValueError('Unknown research cohort mode')
    cut = utc(cutoff)
    now = utc(frozen_at) if frozen_at else datetime.now(timezone.utc)
    run_id = Path(run_dir).name
    config_id = digest({'config': manifest.get('config_sha256'), 'scorer': manifest.get('scorer_sha256'),
                        'dependencies': manifest.get('dependency_sha256'), 'selection': selection})
    cohort_id = digest({'run': run_id, 'cutoff': cut.isoformat(), 'mode': mode})
    signals = []
    for row in rows:
        key = (row['ticker'], row['direction'])
        lv = levels.get(key)
        if lv is None:
            continue
        signal = clean(dict(row))
        signal.update(signal_id=digest({'cohort': cohort_id, 'asset': row['asset'], 'key': key}),
                      entry_session=entry_sessions[row['asset']], levels=clean(lv))
        entry_zone = timezone.utc if row['asset'] == 'crypto' else ZoneInfo('America/New_York')
        entry_time = '00:00:00' if row['asset'] == 'crypto' else '09:30:00'
        entry_open = datetime.fromisoformat(signal['entry_session']+'T'+entry_time).replace(tzinfo=entry_zone)
        signal['entry_open_utc'] = entry_open.astimezone(timezone.utc).isoformat()
        signals.append(signal)
    signals.sort(key=lambda s: s['signal_id'])
    payload = dict(schema=VERSION, cohort_id=cohort_id, run_id=run_id, cutoff_utc=cut.isoformat(),
                   entry_day=cut.astimezone(ZoneInfo('Asia/Jerusalem')).date().isoformat(),
                   mode=mode, config_id=config_id, manifest=manifest, selection=selection, signals=signals)
    # On replay retain the original capture time, but compare every other field.
    path = Path(run_dir) / 'research_snapshot.json'
    if path.exists():
        old = json.loads(path.read_text(encoding='utf-8'))
        now = utc(old['frozen_at_utc'])
    payload['frozen_at_utc'] = now.isoformat()
    payload['forward_eligible'] = (mode != 'trial' and payload['entry_day'] >= FORWARD_FROM
                                  and 0 <= (now - cut).total_seconds() <= 86400)
    immutable_json(path, payload)
    return payload


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS cohorts (
            id TEXT PRIMARY KEY, payload TEXT NOT NULL, hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS signals (
            id TEXT PRIMARY KEY, cohort_id TEXT NOT NULL REFERENCES cohorts(id), payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS observations (
            signal_id TEXT NOT NULL REFERENCES signals(id), bar_date TEXT NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(signal_id, bar_date));
        CREATE TABLE IF NOT EXISTS outcomes (
            signal_id TEXT NOT NULL REFERENCES signals(id), horizon INTEGER NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(signal_id, horizon));
    ''')
    return con


def ingest(con, snapshot):
    """One transaction, no replacement of already frozen scores or selection."""
    payload = json.loads(Path(snapshot).read_text(encoding='utf-8'))
    if payload['schema'] != VERSION:
        raise ValueError('Unsupported research snapshot schema')
    sha = digest(payload)
    old = con.execute('SELECT hash FROM cohorts WHERE id=?', (payload['cohort_id'],)).fetchone()
    if old:
        if old['hash'] != sha:
            raise ValueError(f"Changed frozen cohort {payload['run_id']}")
        return 0
    with con:
        con.execute('INSERT INTO cohorts VALUES (?,?,?)', (payload['cohort_id'], canonical(payload), sha))
        for s in payload['signals']:
            con.execute('INSERT INTO signals VALUES (?,?,?)', (s['signal_id'], payload['cohort_id'], canonical(s)))
    return len(payload['signals'])


def _price(v):
    try:
        v = float(v)
        return v if math.isfinite(v) and v > 0 else None
    except (ValueError, TypeError):
        return None


def _completed(bars, asof, asset):
    """Filter even a provider accidentally returning future or unfinished bars.

    Stocks use a conservative 16:05 New York boundary (early closes become
    available later, never earlier); crypto uses the following 00:00 UTC.
    Missing sessions are not filled and prices are never forward-filled.
    """
    import pandas as pd
    if bars is None or not len(bars):
        return pd.DataFrame(columns=['Open', 'Close'])
    if bars.index.has_duplicates or not bars.index.is_monotonic_increasing:
        raise ValueError('Bar dates must be ordered and unique')
    if bars.index.tz is not None:
        raise ValueError('Expected date-labelled daily bars, not intraday timestamps')
    keep = []
    for day in bars.index:
        if asset == 'crypto':
            close = (day.normalize() + pd.Timedelta(days=1)).tz_localize('UTC')
        else:
            close = (day.normalize() + pd.Timedelta(hours=16, minutes=5)).tz_localize('America/New_York')
        keep.append(close.to_pydatetime() <= utc(asof))
    return bars.loc[keep]


def update(con, asof, fetch_bars):
    """fetch_bars(ticker, asset, UTC datetime) uses the bot's existing providers.

    Prices/outcomes are observational gross returns, not executed trades or P&L.
    Repeated daily runs don't create more trials. Mature labels remain frozen.
    """
    cut = utc(asof)
    cohorts = {r['id']: json.loads(r['payload']) for r in con.execute('SELECT * FROM cohorts')}
    cache, stats = {}, Counter()
    errors = []

    def bars(ticker, asset):
        key = (ticker, asset)
        if key not in cache:
            cache[key] = _completed(fetch_bars(ticker, asset, cut), cut, asset)
        return cache[key]

    for row in con.execute('SELECT * FROM signals').fetchall():
        s = json.loads(row['payload']); cohort = cohorts[row['cohort_id']]
        if (not cohort['forward_eligible'] or utc(cohort['cutoff_utc']) > cut
                or utc(cohort['frozen_at_utc']) >= utc(s['entry_open_utc'])):
            stats['excluded_nonforward'] += 1
            continue
        ready = {r[0] for r in con.execute('SELECT horizon FROM outcomes WHERE signal_id=?', (row['id'],))}
        if set(HORIZONS) <= ready:
            stats['already_mature'] += 1
            continue
        try:
            x = bars(s['ticker'], s['asset'])
            x = x[x.index.strftime('%Y-%m-%d') >= s['entry_session']]
            if not len(x):
                stats['pending_entry_or_data'] += 1
                continue
            if str(x.index[0].date()) != s['entry_session']:
                raise ValueError('Missing declared entry session; next available bar is not a substitute')
            entry = _price(x.Open.iloc[0])
            if entry is None:
                raise ValueError('Invalid entry price')
            sign = 1 if s['direction'] == 'LONG' else -1
            bench = bars('BTC' if s['asset'] == 'crypto' else 'SPY', s['asset'])
            # The reference instrument also supplies the expected session sequence.
            # A missing bar must not turn the sixth exchange session into day five.
            expected = bench[bench.index.strftime('%Y-%m-%d') >= s['entry_session']]
            count = min(len(x), max(HORIZONS))
            if len(expected) < count or not x.index[:count].equals(expected.index[:count]):
                raise ValueError('Asset/reference session gap; outcome deferred')
            base = _price(expected.Open.iloc[0]) if len(expected) else None
            if base is None:
                raise ValueError('Missing benchmark entry')
            additions = Counter()
            with con:
                for n in range(count):
                    close = _price(x.Close.iloc[n]); bclose = _price(expected.Close.iloc[n])
                    if close is None or bclose is None:
                        raise ValueError('Invalid close; no zero/forward-filled substitute')
                    day = str(x.index[n].date())
                    obs = dict(observed_at_utc=cut.isoformat(), bar_date=day, session=n+1,
                               entry_session=s['entry_session'], entry_open=entry, close=close,
                               direction_return=sign*(close/entry-1),
                               benchmark_return=bclose/base-1,
                               excess_direction_return=sign*((close/entry-1)-(bclose/base-1)),
                               measurement='next-session open to session close; gross, no stop/fees',
                               source='scanner_lessons.bars (existing bot price adapter)',
                               prices_sha256=digest([entry, close, base, bclose, day]))
                    cur = con.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?)',
                                      (row['id'], day, canonical(obs)))
                    additions['new_observations'] += cur.rowcount
                    if n+1 in HORIZONS and n+1 not in ready:
                        con.execute('INSERT INTO outcomes VALUES (?,?,?)', (row['id'], n+1, canonical(obs)))
                        additions['new_outcomes'] += 1
            stats.update(additions)
            stats['updated_signals'] += 1
        except Exception as exc:
            errors.append({'signal_id': row['id'], 'ticker': s['ticker'], 'error': f'{type(exc).__name__}: {exc}'})
    return {'asof_utc': cut.isoformat(), **dict(stats), 'errors': errors}


def summarize(con):
    groups = defaultdict(list)
    cohorts = {r['id']: json.loads(r['payload']) for r in con.execute('SELECT * FROM cohorts')}
    for r in con.execute('SELECT * FROM signals'):
        c = cohorts[r['cohort_id']]; s = json.loads(r['payload'])
        if not c['forward_eligible'] or utc(c['frozen_at_utc']) >= utc(s['entry_open_utc']):
            continue
        labels = {o['horizon']: json.loads(o['payload']) for o in con.execute('SELECT * FROM outcomes WHERE signal_id=?', (r['id'],))}
        # Compare pre-model rankings on exactly the same frozen eligible universe.
        # Final post-model/earnings recommendations are separately archived.
        for variant, key in (('baseline', 'baseline_would_select'), ('research30', 'would_select' if c['mode'] == 'paper' else 'selected')):
            if s.get(key):
                for h in HORIZONS:
                    groups[(c['mode'], c['config_id'], s['asset'], s['direction'], variant, h)].append((c, s, labels.get(h)))
    results = []
    for key, records in sorted(groups.items()):
        complete = [r for r in records if r[2] is not None]
        day_means = defaultdict(list)
        for c, s, label in complete:
            day_means[c['entry_day']].append(label['excess_direction_return'])
        result = dict(zip(('mode', 'config_id', 'asset', 'direction', 'variant', 'horizon'), key))
        result.update(selected=len(records), matured=len(complete), pending=len(records)-len(complete),
                      distinct_entry_days=len(day_means),
                      mean_gross_direction_return=sum(r[2]['direction_return'] for r in complete)/len(complete) if complete else None,
                      mean_gross_excess=sum(r[2]['excess_direction_return'] for r in complete)/len(complete) if complete else None,
                      mean_entry_day_excess=sum(sum(v)/len(v) for v in day_means.values())/len(day_means) if day_means else None,
                      positive_excess_rate=sum(r[2]['excess_direction_return'] > 0 for r in complete)/len(complete) if complete else None)
        results.append(result)
    return dict(schema=VERSION, groups=results, automated_weight_changes=False,
                limitations=['Descriptive only; overlapping trades and lunar days are not independent trials.',
                             'Rank comparisons are pre-model; final recommendations remain in selected.json.',
                             'Gross fixed-horizon labels do not model fees, short borrow, stops, or portfolio returns.',
                             'Repeated inspection is not a new untouched holdout. No significance/edge claim.'])


def report_markdown(summary):
    lines = ['## מחקר מצטבר — גאן, תכונה וניתוח טכני',
             'משקלי המחקר נשארים קבועים. התוצאות להלן תיאוריות, לפני עלויות, לפי גרסה וסוג סריקה.',
             'השוואת דירוגים לפני המודלים; אין כאן תשואת תיק או הוכחה למובהקות.',
             '', '| סוג | גרסה | נכס/כיוון | דירוג | ימים | הבשילו/נבחרו | ימי כניסה | עודף ממוצע |',
             '|---|---|---|---|---|---|---|---|']
    for r in summary['groups']:
        value = r['mean_gross_excess']
        text = 'ממתין' if value is None else f'{value:.2%}'
        lines.append(f"| {r['mode']} | {r['config_id'][:8]} | {r['asset']}/{r['direction']} | {r['variant']} | {r['horizon']} | {r['matured']}/{r['selected']} | {r['distinct_entry_days']} | {text} |")
    if not summary['groups']:
        lines.append('\nעדיין אין סריקות עתידיות שנשמרו למחקר. נתון חסר אינו תשואה אפס.')
    return '\n'.join(lines) + '\n'


def daily(scan_root, db_path, asof, fetch_bars, out):
    """Ingest immutable run archives and extend the persistent daily ledger."""
    con = connect(db_path)
    try:
        ingested = sum(ingest(con, p) for p in sorted(Path(scan_root).glob('*/research_snapshot.json')))
        progress = update(con, asof, fetch_bars)
        summary = summarize(con)
        summary.update(progress=progress, signals_ingested=ingested)
        out = Path(out); out.mkdir(parents=True, exist_ok=True)
        (out/'research_progress.json').write_text(canonical(summary)+'\n', encoding='utf-8')
        md = report_markdown(summary)
        (out/'research_progress_he.md').write_text(md, encoding='utf-8')
        return summary, md
    finally:
        con.close()
