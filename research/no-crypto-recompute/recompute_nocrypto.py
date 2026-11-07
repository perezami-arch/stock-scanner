#!/usr/bin/env python3
"""Recompute the simulated account WITHOUT crypto (Ilan 01.11.2026), 16.10.2026 -> latest close.

Rules (same as the box ledger account_balance.csv): $120,000 buying power split into equal slots over the open
positions; duplicates by ticker+direction counted once (earliest kept); stock long half at the Fib 1.618 target ->
weighted return 0.5*close + 0.5*half; stop = the tracked level known BEFORE the session (a newly computed trailing
level — long 5xATR14, short 4xATR14, via stop_policy — applies only to later sessions, never to today's high/low);
a stop counts when the day's low (long) / high (short) crosses that level, exit at the worse of the stop and the open;
new entries at the entry-session open; slot size changes at the open of an entry day (gap from the previous close on the old slots).
Baseline: 16.10.2026 close = $27,460 (official, set by Ilan). Crypto P&L before 16.10 is inside that baseline and
cannot be separated (the ledger did not split it).
Needs ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY in env (never printed).
"""
import os, sys, csv, requests
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(_HERE, '..', '..', 'modules'), os.environ.get('SCANNER_ROOT', '/workspace')):
    if _p and os.path.isdir(_p) and _p not in sys.path: sys.path.insert(0, _p)
import stop_policy as SPOL
BP = 120000.0; BASE = ('2026-10-16', 27460.0)
# stop check: closes after STOPS_CHECKED_THROUGH only, using the tracked level as of that date (trailing stops change over time,
# so applying today's level to earlier days would be wrong).
# (sym, dir, entry, entry_date or None=before baseline, group, half=(date, price) or None, exit=(date, price) or None, stop)
P = [
 ('MU',1,933.9230520539426,None,'real',None,None,794.5852), ('MRVL',1,253.52999877929688,None,'real',None,None,207.5153),
 ('ORCL',-1,135.91000366210938,None,'real',None,None,151.0962), ('XOM',1,173.4499969482422,None,'real',('2026-10-16',178.98),None,169.2325),
 ('GOOGL',1,356.2300109863281,None,'real',None,('2026-10-23',320.21),None), ('KO',1,90.55999755859376,None,'real',('2026-10-15',92.00),None,89.3979),
 ('AMGN',1,420.3399963378906,None,'real',('2026-10-29',460.73),None,415.859), ('T',-1,22.270000457763672,None,'real',None,None,23.6147),
 ('MRK',1,141.9,None,'trial',None,None,129.2226), ('DE',1,648.76,None,'trial',None,None,582.3857), ('COP',1,132.76,None,'trial',None,None,117.1327),
 ('SBUX',-1,93.0,None,'trial',None,('2026-10-23',102.0982),None), ('CMCSA',-1,20.91,None,'trial',None,None,23.3170),
 ('NKE',-1,34.125,None,'trial',None,None,38.8654), ('UBER',-1,68.175,None,'trial',None,None,75.4068), ('HON',-1,206.49,None,'trial',None,None,225.3832),
 ('ADI',1,404.8699951171875,'2026-10-19','real',None,None,380.1249), ('OXY',1,62.0,'2026-10-19','real',None,None,57.9999),
 ('LLY',1,1243.3900146484375,'2026-10-19','real',('2026-10-29',1373.70),None,1203.621), ('AAPL',1,340.7799987792969,'2026-10-19','real',None,None,323.8409),
 ('ABNB',1,174.5399932861328,'2026-10-19','real',None,None,159.2836), ('AVGO',-1,338.75,'2026-10-19','real',None,None,366.4719),
 ('PFE',1,29.309999465942383,'2026-10-19','real',('2026-10-22',30.42),None,28.2331),
 ('NFLX',-1,65.16000366210938,'2026-10-26','real',None,None,69.9719), ('CRWD',1,259.0599975585937,'2026-10-26','real',None,None,218.8417),
 ('TXN',1,288.9200134277344,'2026-10-26','real',None,None,276.1914), ('TMO',1,675.8599853515625,'2026-10-26','real',None,None,630.5504),
]
CRYPTO_REMOVED = ['UNI long (13.10)', 'LINK long (13.10)', 'AAVE long (20.10)']
STOPS_CHECKED_THROUGH = '2026-10-29'   # the ledger already checked stock stops through 29.10 (only GOOGL/SBUX hit); the stop column = levels as of 29.10

def wret(p, px, day):
    s, d, e, ed, g, half, ex, st = p
    x = d * (px - e) / e
    return 0.5 * x + 0.5 * d * (half[1] - e) / e if half and half[0] <= day else x

def active(p, day):  # position counts a slot on `day` (entered by then, not exited before)
    return (p[3] is None or p[3] <= day) and not (p[6] and p[6][0] < day)

def positions():
    """Tracked book, one row per ticker+direction (earliest entry)."""
    raw = [list(p) for p in P]
    return [r['raw'] for r in SPOL.dedup_earliest(
        [{'ticker': p[0], 'direction': 'LONG' if p[1] == 1 else 'SHORT', 'entry_date': p[3], 'raw': p} for p in raw])]

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    H = {'APCA-API-KEY-ID': os.environ['ALPACA_API_KEY_ID'], 'APCA-API-SECRET-KEY': os.environ['ALPACA_API_SECRET_KEY']}
    END = argv[0] if argv else '2026-10-31'
    r = requests.get('https://data.alpaca.markets/v2/stocks/bars', headers=H, params={'symbols': ','.join(sorted({p[0] for p in P})), 'timeframe': '1Day',
        'start': BASE[0], 'end': END + 'T00:00:00Z', 'feed': 'sip', 'adjustment': 'raw', 'limit': 10000}).json()
    B = {s: {b['t'][:10]: b for b in v} for s, v in r['bars'].items()}
    days = sorted({d for v in B.values() for d in v if d > BASE[0]})
    rows, bal, prev_day, stop_events = [], BASE[1], BASE[0], []
    book = positions()
    for day in days:
        n_old = sum(active(p, prev_day) for p in book); n_new = sum(active(p, day) for p in book)
        S_old, S_new = BP / n_old, BP / n_new
        pl = {'real': 0.0, 'trial': 0.0}
        for p in book:
            if not active(p, day) or day not in B[p[0]]: continue
            b = B[p[0]][day]; s, d, e, ed, g, half, ex, st = p
            # Stop known before this session. Do not rebuild it from today's close and then test today's high/low.
            # Fill is the worse of the stop and the open (a gap through the stop does not fill at the stop).
            if ex is None and st is not None and day > STOPS_CHECKED_THROUGH:
                hit = SPOL.touch_fill('LONG' if d == 1 else 'SHORT', b['o'], b['h'], b['l'], st)
                if hit is not None:
                    p[6] = ex = (day, hit); stop_events.append((day, s, g, hit))
            close = ex[1] if ex and ex[0] == day else b['c']
            if ed == day:   # new entry at the open
                pl[g] += S_new * wret(p, close, day)
            else:
                pc = B[s][prev_day]['c'] if prev_day in B[s] else None
                if pc is None: continue
                # gap prev close -> open on old slot, open -> close on new slot (ledger convention)
                pl[g] += S_old * (wret(p, b['o'], day) - wret(p, pc, prev_day)) + S_new * (wret(p, close, day) - wret(p, b['o'], day))
        ch = pl['real'] + pl['trial']; bal += ch
        rows.append({'close_date': day, 'balance': round(bal, 2), 'change_usd': round(ch, 2), 'real_usd': round(pl['real'], 2), 'trial_usd': round(pl['trial'], 2),
                     'slots': n_new, 'slot_usd': round(S_new, 2), 'pct_vs_30000': round((bal / 30000 - 1) * 100, 2)})
        prev_day = day
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'account_nocrypto.csv')
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for x in rows: print(x)
    print('stops hit in replay:', stop_events)
    print('real total', round(sum(x['real_usd'] for x in rows), 2), 'trial total', round(sum(x['trial_usd'] for x in rows), 2))
    open_ = [p for p in book if not p[6]]
    print('open at end:', len(open_), 'real', sum(p[4] == 'real' for p in open_), 'trial', sum(p[4] == 'trial' for p in open_))
    for p in book:
        last = max(B[p[0]]) if not p[6] else p[6][0]; px = B[p[0]][last]['c'] if not p[6] else p[6][1]
        print(p[4], p[0], 'S' if p[1] < 0 else 'L', 'closed' if p[6] else 'open', last, round(wret(p, px, last) * 100, 2))

if __name__ == '__main__':
    main()
