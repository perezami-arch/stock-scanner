"""Daily factual review and post-exit 5/10/20-session audits.

No orders, stop modifications, automatic rule fitting, or headline sentiment
guessing. News remains untrusted source text and never becomes an instruction.
"""
from datetime import timedelta
import json
import math
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import scanner_research_ledger as RL


def number(v):
    try:
        v = float(v)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def trade_review(trade, bars, benchmark, technical=None):
    """Descriptive evidence, not a probability that a trade will succeed."""
    sgn = 1 if trade['direction'] == 'LONG' else -1
    technical = technical or {}
    entry = RL._price(trade.get('entry_fill'))
    if entry is None or bars is None or not len(bars):
        return {'status': 'pending_entry_or_prices', 'supports': [], 'weakens': []}
    close = RL._price(bars.Close.iloc[-1]); atr = RL._price(technical.get('atr14_wilder'))
    if close is None:
        return {'status': 'missing_close', 'supports': [], 'weakens': []}
    stop, target = number(trade.get('current_stop')), number(trade.get('target'))
    ret = sgn*(close/entry-1)
    supports, weakens = [], []
    (supports if ret > 0 else weakens if ret < 0 else []).append('תשואה מאז הכניסה בכיוון העסקה' if ret > 0 else 'המחיר נע נגד העסקה מאז הכניסה')
    for label, key in (('SMA50', 'sma50'), ('SMA200', 'sma200')):
        ma = RL._price(technical.get(key))
        if ma:
            aligned = sgn*(close-ma) > 0
            (supports if aligned else weakens).append(f'{label}: המחיר בצד התומך בעסקה' if aligned else f'{label}: המחיר בצד הנגדי לעסקה')
    distance = sgn*(close-stop)/atr if stop is not None and atr else None
    if distance is not None and distance <= 1:
        weakens.append('המחיר עד ATR אחד מהסטופ או עבר אותו')
    excess = None
    if benchmark is not None and len(benchmark):
        es = trade['entry_session']; last = str(bars.index[-1].date())
        lookup = {str(i.date()): row for i, row in benchmark.iterrows()}
        if es in lookup and last in lookup and RL._price(lookup[es].Open):
            excess = ret - sgn*(float(lookup[last].Close)/float(lookup[es].Open)-1)
            (supports if excess > 0 else weakens if excess < 0 else []).append('ביצוע עודף מול מדד הייחוס' if excess > 0 else 'פיגור מול מדד הייחוס')
    status = 'supporting' if supports and not weakens else 'weakening' if weakens and not supports else 'mixed'
    return dict(status=status, last_bar=str(bars.index[-1].date()), close=close, entry_fill=entry,
                direction_return=ret, excess_direction_return=excess, stop=stop, target=target,
                distance_to_stop_atr=distance, distance_to_target_pct=sgn*(target/close-1) if target else None,
                supports=supports, weakens=weakens, technical_available=bool(technical))


def post_exit_labels(trade, bars, benchmark):
    """Sessions strictly AFTER actual exit; entry-age checkpoints are unrelated.

    Exit day close anchors an adjusted-price-consistent path. If it differs from
    the registry's recorded exit, defer instead of silently changing the trade.
    """
    if bars is None or not len(bars) or benchmark is None or not len(benchmark):
        return []
    exit_day = str(trade['exit_date'])[:10]
    dates = bars.index.strftime('%Y-%m-%d')
    bd = benchmark.index.strftime('%Y-%m-%d')
    at_exit, b_exit = bars[dates == exit_day], benchmark[bd == exit_day]
    if not len(at_exit) or not len(b_exit):
        raise ValueError('Exit close missing; cannot anchor post-exit audit')
    exit_price = RL._price(trade.get('exit_price')); anchor = RL._price(at_exit.Close.iloc[0])
    bench_anchor = RL._price(b_exit.Close.iloc[0])
    if exit_price is None or anchor is None or bench_anchor is None:
        raise ValueError('Invalid exit/reference price')
    if not math.isclose(anchor, exit_price, rel_tol=1e-4, abs_tol=1e-6):
        raise ValueError('Exit price differs from stored trade; review corporate action/data correction')
    after = bars[dates > exit_day]; ref = benchmark[bd > exit_day]
    n = min(len(after), 20)
    if len(ref) < n or not after.index[:n].equals(ref.index[:n]):
        raise ValueError('Post-exit session gap; audit deferred')
    sgn = 1 if trade['direction'] == 'LONG' else -1
    labels = []
    for horizon in (5, 10, 20):
        if len(after) < horizon:
            continue
        close = RL._price(after.Close.iloc[horizon-1]); bclose = RL._price(ref.Close.iloc[horizon-1])
        if close is None or bclose is None:
            raise ValueError('Invalid post-exit close')
        ret = sgn*(close/anchor-1)
        path = after.iloc[:horizon]
        excursions = [sgn*(float(v)/anchor-1) for col in ('High', 'Low') if col in path for v in path[col] if RL._price(v)]
        labels.append(dict(horizon=horizon, exit_date=exit_day, measured_date=str(after.index[horizon-1].date()),
                           exit_price=exit_price, close=close, direction_return=ret,
                           excess_direction_return=ret-sgn*(bclose/bench_anchor-1),
                           max_favorable=max([0]+excursions) if excursions else None,
                           max_adverse=min([0]+excursions) if excursions else None,
                           interpretation='המחיר המשיך בכיוון העסקה לאחר היציאה' if ret > 0 else 'המחיר נע נגד כיוון העסקה לאחר היציאה' if ret < 0 else 'ללא שינוי',
                           limitation='בדיעבד בלבד; המשך בכיוון אינו מוכיח שהיציאה הייתה שגויה'))
    return labels


def clean_news(articles, since, asof):
    """Preserve provider coverage flags; no news is different from unavailable."""
    found, seen = [], set()
    for a in articles:
        try:
            timestamp = RL.utc(a['created_at_utc'])
        except (KeyError, ValueError, TypeError):
            continue
        ident = str(a.get('id') or RL.digest(a))
        if not since <= timestamp < asof or ident in seen:
            continue
        seen.add(ident)
        item = {k: a.get(k) for k in ('headline', 'source', 'created_at_utc', 'url')}
        item['id'] = ident
        if urlparse(str(item['url'])).scheme not in ('http', 'https'):
            item['url'] = None
        found.append(item)
    found.sort(key=lambda a: a['created_at_utc'], reverse=True)
    return dict(status=getattr(articles, 'flag', None) or 'ok', count=len(found), articles=found,
                since_utc=since.isoformat(), asof_utc=asof.isoformat(),
                interpretation='כותרות מקור לתחקור; לא הוסקה מהן השפעה על הכיוון')


def run(registry, db_path, asof, fetch_bars, fetch_news, build_levels, out):
    cut = RL.utc(asof); day = cut.astimezone(ZoneInfo('Asia/Jerusalem')).date().isoformat()
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    con = RL.connect(db_path)
    con.executescript('''
        CREATE TABLE IF NOT EXISTS trade_reviews (
            trade_id TEXT NOT NULL, asof_utc TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(trade_id, asof_utc));
        CREATE TABLE IF NOT EXISTS post_exit (
            trade_id TEXT NOT NULL, horizon INTEGER NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(trade_id, horizon));
        CREATE TABLE IF NOT EXISTS news_watermarks (symbol TEXT PRIMARY KEY, asof_utc TEXT NOT NULL);
    ''')
    price_cache, news_cache = {}, {}
    result = dict(asof_utc=cut.isoformat(), open=[], post_exit_new=[], post_exit_history=[], errors=[])

    def price(t, asset):
        key = (t, asset)
        if key not in price_cache:
            price_cache[key] = RL._completed(fetch_bars(t, asset, cut), cut, asset)
        return price_cache[key]

    def news(t, asset):
        key = f'{asset}|{t}'
        if key not in news_cache:
            row = con.execute('SELECT asof_utc FROM news_watermarks WHERE symbol=?', (key,)).fetchone()
            prior = RL.utc(row[0]) if row else cut-timedelta(days=3)
            since = max(prior, cut-timedelta(days=14))
            days = max(1, math.ceil((cut-since).total_seconds()/86400))
            try:
                arts = fetch_news(t, asset, cut, days)
                item = clean_news(arts, since, cut)
            except Exception as exc:
                item = dict(status=f'unavailable: {type(exc).__name__}', count=0, articles=[])
            item['coverage_gap'] = prior < since
            news_cache[key] = item
        return news_cache[key]

    try:
        for trade in registry:
            if str(trade.get('is_trial')).lower() == 'true' or str(trade.get('is_sim')).lower() == 'true':
                continue
            tid = str(trade['trade_id']); t = trade['ticker']; asset = trade['asset']
            try:
                if trade.get('status') == 'closed':
                    done = {r[0] for r in con.execute('SELECT horizon FROM post_exit WHERE trade_id=?', (tid,))}
                    if set(RL.HORIZONS) <= done:
                        continue
                    xx = price(t, asset); bench = price('BTC' if asset == 'crypto' else 'SPY', asset)
                    for label in post_exit_labels(trade, xx, bench):
                        if label['horizon'] in done:
                            continue
                        label.update(trade_id=tid, ticker=t, direction=trade['direction'], exit_reason=trade.get('exit_reason'),
                                     observed_at_utc=cut.isoformat(), news=news(t, asset))
                        with con:
                            con.execute('INSERT INTO post_exit VALUES (?,?,?)', (tid, label['horizon'], RL.canonical(label)))
                        result['post_exit_new'].append(label)
                    continue
                if trade.get('status') != 'open':
                    continue
                existing = con.execute('SELECT payload FROM trade_reviews WHERE trade_id=? AND asof_utc=?', (tid, cut.isoformat())).fetchone()
                if existing:
                    result['open'].append(json.loads(existing[0])); continue
                # Fetch news even when the price provider or technical rebuild fails.
                item = dict(trade_id=tid, ticker=t, direction=trade['direction'], news=news(t, asset))
                try:
                    xx = price(t, asset); bench = price('BTC' if asset == 'crypto' else 'SPY', asset)
                    try:
                        lv = build_levels(trade, cut, out)
                        item['technical'] = lv.get('technical') or {}
                        item['elliott'] = lv.get('elliott')
                        item['waves'] = lv.get('waves')
                        item['earnings'] = lv.get('earnings')
                        item['research_now'] = lv.get('research_score')
                    except Exception as exc:
                        item['technical_error'] = f'{type(exc).__name__}: {exc}'
                    item['review'] = trade_review(trade, xx, bench, item.get('technical'))
                except Exception as exc:
                    item['review'] = dict(status='unavailable', supports=[], weakens=[])
                    item['price_error'] = f'{type(exc).__name__}: {exc}'
                with con:
                    con.execute('INSERT OR IGNORE INTO trade_reviews VALUES (?,?,?)', (tid, cut.isoformat(), RL.canonical(item)))
                result['open'].append(item)
            except Exception as exc:
                result['errors'].append(dict(trade_id=tid, ticker=t, error=f'{type(exc).__name__}: {exc}'))
        with con:
            for key, item in news_cache.items():
                if item['status'] == 'ok':
                    con.execute('INSERT OR REPLACE INTO news_watermarks VALUES (?,?)', (key, cut.isoformat()))
        result['post_exit_history'] = [json.loads(r[0]) for r in con.execute('SELECT payload FROM post_exit ORDER BY trade_id,horizon')]
        result = RL.clean(result)
        (out/'trade_followup.json').write_text(RL.canonical(result)+'\n', encoding='utf-8')
        md = render(result)
        (out/'trade_followup_he.md').write_text(md, encoding='utf-8')
        return result, md
    finally:
        con.close()


def safe(value):
    # Prevent source headlines from becoming HTML or Markdown links in the PDF.
    import html
    return html.escape(str(value or '—')).replace('|', '/').replace('\n', ' ').replace('[', '&#91;').replace(']', '&#93;')


def pct(value):
    return '—' if number(value) is None else f'{float(value):+.2%}'


def render(result):
    lines = ['## מעקב יומי: כיוון העסקה וחדשות', 'הבדיקה מתבססת על נרות שהושלמו ועל החדשות הזמינות. כותרת כשלעצמה אינה קובעת כיוון.']
    status_he = dict(supporting='סימנים תומכים', weakening='סימנים מחלישים', mixed='תמונה מעורבת',
                     pending_entry_or_prices='ממתין לכניסה/נתונים', unavailable='חסרים נתונים')
    for item in result['open']:
        r = item['review']; n = item['news']
        lines.extend(['', f"### {safe(item['ticker'])} · {safe(item['direction'])} · {status_he.get(r['status'], safe(r['status']))}",
                      f"נר אחרון: {safe(r.get('last_bar'))} · תשואה בכיוון: {pct(r.get('direction_return'))} · עודף מול המדד: {pct(r.get('excess_direction_return'))}",
                      f"סטופ: {safe(r.get('stop'))} · מרחק ב־ATR: {safe(r.get('distance_to_stop_atr'))} · יעד: {safe(r.get('target'))}",
                      'תומך: '+(' ; '.join(r.get('supports', [])) or 'אין אישור זמין'),
                      'מחליש: '+(' ; '.join(r.get('weakens', [])) or 'אין סימן זמין'),
                      f"חדשות: {n['count']} חדשות מאז הבדיקה הקודמת · כיסוי: {safe(n['status'])}"])
        if item.get('technical_error') or item.get('price_error'):
            lines.append('חסר מידע בחישוב הטכני/מחירים; פירוט בקובץ המעקב.')
        if item.get('earnings'):
            lines.append('אירוע דוחות קרוב: '+safe(item['earnings'].get('status'))+' · '+safe(item['earnings'].get('next_earnings')))
        research = item.get('research_now') or {}
        components = research.get('components') or {}
        for key, title in (('elliott', 'אליוט'), ('candles', 'נרות'), ('volume', 'נפח'), ('gann', 'גאן')):
            block = components.get(key) or {}
            evidence = block.get('evidence') or {}
            lines.append(f"{title}: ציון רכיב {safe(block.get('score'))} · {safe(block.get('reason'))}")
        lunar = research.get('lunar') or {}
        if lunar:
            lines.append('יום המחקר בירושלים: '+safe(lunar.get('lunar_hebrew_date'))+' · מופע ירח '+safe(lunar.get('lunar_phase_deg'))+'°')
        if n.get('coverage_gap'):
            lines.append('קיים פער בכיסוי חדשות: ניתן היה להשלים עד 14 ימים בלבד.')
        for a in n['articles'][:8]:
            url = a.get('url')
            link = f" ([מקור](<{url}>))" if url and not any(c in url for c in '<>\n\r') else ''
            lines.append(f"- {safe(a['created_at_utc'])} · {safe(a['source'])}: {safe(a['headline'])}{link}")
        if n['count'] > 8:
            lines.append('יתר הכותרות שמורות בקובץ המעקב של היום.')
    lines.extend(['', '## תחקור לאחר סגירת העסקה — 5, 10 ו־20 ימי מסחר',
                  'הספירה מתחילה ביום המסחר שאחרי היציאה. תוצאה בדיעבד אינה מוכיחה שהיה נכון להישאר בעסקה.',
                  '| טיקר | כיוון | יציאה | ימים אחרי יציאה | תאריך מדידה | שינוי בכיוון | עודף מול מדד |',
                  '|---|---|---|---|---|---|---|'])
    for p in result['post_exit_history']:
        lines.append(f"| {safe(p['ticker'])} | {safe(p['direction'])} | {p['exit_date']} | {p['horizon']} | {p['measured_date']} | {pct(p['direction_return'])} | {pct(p['excess_direction_return'])} |")
    if not result['post_exit_history']:
        lines.append('\nטרם הבשילו בדיקות אחרי יציאה; הן יופיעו רק כשיגיעו נתונים בפועל.')
    if result['errors']:
        lines.append(f"\n{len(result['errors'])} בדיקות לא הושלמו; פירוט ב־trade_followup.json.")
    return '\n'.join(lines)+'\n'
