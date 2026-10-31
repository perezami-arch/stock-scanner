"""Hebrew unified report (08.10.2026 v2). Markdown + PDF (headless Chrome, RTL HTML).
Every technical number printed comes from <run_dir>/levels/<T>.json (single source of truth) via the candidate dicts
(scanner_levelsfile.apply_trade) and facts_for_prompt(); platform outputs are opinions (weight 0). Reconciliation result
(report / tracker / chart index vs levels JSON) is summarised at the top; 'לא תואם' setups are excluded from the recommendations."""
import os, json, subprocess, html, math, datetime as dt
import pandas as pd

VERD = {'approve': '✅ אישור', 'flag': '⚠️ דגל', 'veto': '⛔ וטו', None: '—'}
DIRH = {'LONG': 'לונג', 'SHORT': 'שורט'}
DVIEW = {'supports': 'תומך', 'neutral': 'ניטרלי', 'opposes': 'מתנגד'}
CPA = {'hold': 'להחזיק', 'tighten': 'להדק', 'exit': 'לצאת'}

def _n(x, d=2):
    try:
        v = float(x)
        return '—' if math.isnan(v) else ('\u200e' if v < 0 else '') + f'{v:,.{d}f}'
    except Exception:
        return '—' if x is None or str(x) in ('nan', 'None', '') else str(x)

def _t(x):
    if x is None or (isinstance(x, float) and math.isnan(x)) or str(x) in ('nan', 'None'): return '—'
    return str(x).replace('|', '/').replace('\n', ' ').strip()

def _vd(r, k):
    return VERD.get(r.get(k)) if r.get(k) else ('חסר קרדיט' if str(r.get(k.replace('_verdict', '_error')) or '').startswith('חסר קרדיט') else ('שגיאה' if r.get(k.replace('_verdict', '_error')) else '—'))

def _nd(x):   # price with enough decimals for crypto
    try: v = float(x)
    except Exception: return '—'
    return _n(v, 2 if abs(v) >= 10 else 4 if abs(v) >= 0.1 else 6)

def write_report(run_dir, res):
    import scanner_levelsfile as LF
    d = pd.read_csv(f'{run_dir}/scan_raw.csv')
    meta = json.load(open(f'{run_dir}/run_meta.json')) if os.path.exists(f'{run_dir}/run_meta.json') else {}
    R = res['regime']; cands, rows = res['cands'], res['rows']; M = res['models']
    rec = res.get('recon') or {}; eg = res.get('earnings') or {}
    trial = res.get('run_kind') == 'trial'
    L_ = []; w = L_.append
    asof = meta.get('scan_asof_local', '')[:16]
    w('# דוח סורק מאוחד – ' + ('ריצת ניסיון (TRIAL)' if trial else 'סריקה שבועית (יום שני)'))
    w(f'**זמן הסריקה:** {asof} (שעון ישראל) · **תיקייה:** `{run_dir}` · **הופק:** {dt.datetime.now():%d.%m.%Y %H:%M} (שעון ישראל)\n')
    # ---- reconciliation line (top)
    bad = {k: v for k, v in rec.items() if v}
    if rec:
        w(f"> **בדיקת התאמה (קובץ הרמות מול הדוח, שורות הטראקר ואינדקס הגרפים, סבולת 1e-6 יחסית):** {len(rec) - len(bad)} מתוך {len(rec)} תואמים"
          + (f" · **לא תואם: {', '.join(f'{k[0]} {DIRH.get(k[1], k[1])}' for k in bad)}** (הוצאו מההמלצות, פירוט בסעיף 7)" if bad else ' · אין אי-התאמות.') + '\n')
    cr = res.get('credit_errors') or sorted({x for r in rows for x in str(r.get('credit_status') or '').split(' ; ') if x})
    if cr:
        w('> ## 🔴 חסר קרדיט')
        for x in cr: w(f"> - **{x if str(x).startswith('חסר קרדיט') else 'חסר קרדיט - ' + str(x)}**: העמודות של הפלטפורמה הזו ריקות בדוח. צריך לטעון קרדיט ולהריץ שוב.")
        w('')
    w('> **חשוב:** עמודות המודלים (Jev, ‏Grok, ‏Perplexity, ‏Claude אנליסט, ‏GPT פרקליט השטן) נכנסות לציון לפי critic_score v4 (מ-29.10.2026): **Grok, ‏Perplexity, ‏Claude, ‏GPT במשקל 1.0, Jev במשקל 0**, וציון כל מודל נשמר בעמודה נפרדת. הכניסה, הסטופ והיעד מגיעים רק מכללי הבוט, '
      'דרך קובץ הרמות של הריצה, ואף מודל לא שינה אותם. פסקי הדין נמדדים **רק קדימה, מ-12.10.2026**, בלי בקטסט היסטורי. '
      'כלל הדוחות (אין כניסה חדשה בתוך 5 ימי מסחר לפני דוח) הוא **כלל פעיל**. זה לא ייעוץ השקעות.\n')
    # ---- partition
    def key(c): return (c['t'], c['direction'])
    rec_ok = lambda c: not rec.get(key(c))
    blocked = [(c, r) for c, r in zip(cands, rows) if (c.get('_eg') or {}).get('blocked')]
    exc = [(c, r) for c, r in zip(cands, rows) if (c.get('_eg') or {}).get('exception')]
    recs = [(c, r) for c, r in zip(cands, rows) if not (c.get('_eg') or {}).get('blocked') and rec_ok(c) and (c.get('_selected') or (c.get('_eg') or {}).get('exception'))]
    stock_recs = [x for x in recs if x[0].get('asset') != 'crypto']; crypto_recs = [x for x in recs if x[0].get('asset') == 'crypto']
    # ---- 1 regime
    w('## 1. מצב השוק')
    idx = d[d['t'].isin(['SPY', 'QQQ', 'IWM', 'SMH', '^VIX'])].set_index('t')
    w(f"- **נקודת חיתוך לנתונים (PIT):** {_t(res.get('cutoff') or R.get('pit_cutoff_utc'))} UTC")
    w(f"- **תשואת 10 שנים:** {_n(R.get('US10Y'), 3)}% (שינוי 20 יום: {_n(R.get('US10Y_chg_20d_bp'), 1)} נ\"ב) · **30 שנים:** {_n(R.get('US30Y'), 3)}% · **מרווח 2-10:** {_n(R.get('us2y10y_spread'))}")
    w(f"- **VIX:** {_n(R.get('VIX'))} · **AAII שוורים פחות דובים:** {_n(R.get('aaii_bull_bear'), 1)} (סקר מ-{_t(R.get('aaii_date'))})")
    if len(idx):
        w('\n| מדד | סגירה | 5 ימים % | 15 ימים % | 60 ימים % | RSI | מבנה ממוצעים | שיפוע SMA50 |'); w('|---|---|---|---|---|---|---|---|')
        for t in ['SPY', 'QQQ', 'IWM', 'SMH', '^VIX']:
            if t in idx.index:
                r = idx.loc[t]; w(f"| {t} | {_n(r['px'])} | {_n(r['r5'])} | {_n(r['r15'])} | {_n(r['r60'])} | {_n(r['rsi'], 1)} | {_t(r['stack'])} | {_t(r['slope50'])} |")
    w('')
    # ---- 2 method
    cap = res.get('sector_cap', 2)
    w('## 2. איך נבחרו המועמדים')
    w(f"- **{res.get('n_full', '—')} שמות עברו את הכללים** (הרשימה המלאה ב-`candidates_full.csv`, עם ציוני הכללים, הרמות מקובץ הרמות, כניסה/סטופ/יעד ודגל הדוח). "
      f"מתוכם נבחרו עד **{res.get('candidates_n', 20)}** לדוח.")
    w('- **מניות לונג:** סגירה מעל SMA50 ו-SMA200, שיפוע SMA50 עולה, עד 3 ATR מעל SMA20, שווי ≥ $1.5B, מחזור > $14M, מחיר ≥ $5.')
    w('- **מניות שורט:** רק מי שעובר את כלל השורט המאושר (ck_score≥3 וסגירה מתחת ל-SMA200).')
    w('- **קריפטו (לונג בלבד):** BTC, ‏ETH, ‏SOL ומטבעות גדולים, נרות יומיים של Alpaca. אותו מסנן מגמה, סטופ קבוע 3×ATR14 על סגירה יומית, בלי יעד. שורט קריפטו מוקפא. Grok הוא פלטפורמת הסנטימנט הראשית.')
    w(f"- **דירוג אחד לכולם (אין חלוקה קבועה לונג/שורט):** ציון אחיד 0–100 = אחוזון המומנטום 12-1 בתוך קבוצת הנכס, "
      f"ובשורט הפוך (100 פחות האחוזון). ככל שהציון גבוה יותר המומנטום מצביע לכיוון העסקה, ושורט מדורג מעל לונג רק כשהמומנטום שלו חזק יותר. "
      f"נבחרים עד {res.get('candidates_n', 20)} בעלי הציון הגבוה ביותר - יכולים להיות 20 לונג ו-0 שורט. "
      f"**סף כניסה: {res.get('min_score', 60):g}** (דגל `--min-score`); מתחתיו שם לא נכנס גם אם נשארו פחות מ-{res.get('candidates_n', 20)} מקומות. "
      f"ברירת המחדל 60 נקבעה לפי מדגם מאומת (139 סטאפי מניות עם תוצאה ליום 20, 15 ימי כניסה שונים): מציון 60 ומעלה שיעור הפגיעה בתשואה מכוונת ליום 20 היה 58.9% מול 51.8% מתחת, בלי יתרון בממוצע. מדגם קטן - הסף עצמו נמדד קדימה.")
    w(f"- **גיוון:** " + (f"לכל היותר {cap} שמות מאותו סקטור בכל צד (דגל `--sector-cap`, 0 מבטל)." if cap else 'מגבלת הסקטור כבויה בריצה הזו.'))
    w('- **כלל הדוחות (פעיל):** אין כניסה חדשה במניה אם הדוח הבא בתוך 5 ימי מסחר מיום הכניסה. מקורות התאריך: לוח Yahoo, ‏OpenBB/Nasdaq ו-Perplexity (רק כשהוא מאשר עם מקור). '
      'אם יש מחלוקת, לוקחים את התאריך **המוקדם**. אין תאריך מאומת: מסומן "תאריך דוח לא מאומת". חריגה רק בקטליזטור חזק מאוד: Perplexity מדרג "חזק" עם מקור מתוארך, '
      'Claude בביטחון 70 ומעלה בעד, ו-GPT לא הטיל וטו. מניה שנחסמה מוחלפת בשם הבא בדירוג, והיא עדיין נרשמת ביומן למדידה.')
    w('- **מקור אמת יחיד:** לכל שם נבנה קובץ `levels/<TICKER>.json` (נרות מהמטמון של הסריקה, hash של הנרות, פיבוטים, ספירת אליוט v1 ו-v2, פיבו, VP120, תמיכה/התנגדות, גלי נפח, RSI/CCI, כניסה/סטופ/יעד, סטטוס דוח). '
      'הגרף, הדוח, שורות הטראקר והמודלים קוראים רק ממנו.')
    w('- **המודלים רואים את הגרף:** Claude, ‏GPT, ‏Grok ו-Perplexity מקבלים את תמונת הגרף (1280 פיקסלים) כקלט הראשי לקריאה הטכנית, וכל מספר בטקסט מגיע מקובץ הרמות. '
      'כל מודל אומר אם הוא חולק על ספירת האליוט, הפיבו או התמיכה/התנגדות שצוירו (עמודה ניסיונית `chart_count_disagree`).\n')
    # ---- 3 summary table
    def table(items, title):
        w(title)
        hdr = ['#', 'טיקר', 'כיוון', 'כניסה (ייחוס)', 'סטופ', 'יעד', 'דירוג', 'דוח', 'Jev', 'Grok', 'Perplexity', 'Claude', 'GPT', 'חולקים על הגרף']
        w('| ' + ' | '.join(hdr) + ' |'); w('|---' * len(hdr) + '|')
        for i, (c, r) in enumerate(items, 1):
            tgt = _nd(c['target']) if c['target'] else ('100% שנדלייר' if c['direction'] == 'LONG' and c.get('asset') != 'crypto' else 'אין')
            gs = f"{VERD[r['grok_verdict']]} (\u200e{r['grok_sentiment']:+d})" if r.get('grok_verdict') else _vd(r, 'grok_verdict')
            cl = f"{r['claude_conviction']} ({DVIEW.get(r.get('claude_direction_view'), '')})" if r.get('claude_conviction') is not None else _vd(r, 'claude_verdict')
            jv = f"{_t(r.get('jev_news_sentiment'))}" if r.get('jev_n_headlines') is not None else '—'
            rk = _n(c.get('rank_score'), 1)
            g = c.get('_eg') or {}
            es = ('⚡ ' + g['status']) if g.get('exception') else (f"{g.get('next_earnings')} ({g.get('td_to_earnings')} י\"מ)" if g.get('next_earnings') else _t(g.get('status')))
            dis = sum(str(r.get(f'{p}_chart_disagree') or '').startswith('yes') for p in ('grok', 'pplx', 'claude', 'gpt'))
            w('| ' + ' | '.join([str(i), f"**{c['t']}**", DIRH[c['direction']], _nd(c['entry']), _nd(c['stop']), tgt, rk, es, jv, gs,
                                 _vd(r, 'pplx_verdict'), cl, _vd(r, 'gpt_verdict'), f'{dis}/4' if r.get('image_inputs') else '—']) + ' |')
        w('')
    table(stock_recs, f'## 3. המלצות – מניות ({len(stock_recs)})')
    w('_דירוג: הציון האחיד 0–100 (אחוזון מומנטום 12-1, הפוך בשורט). Grok בסוגריים: סנטימנט 2- עד 2+. Claude: ביטחון 0–100 ועמדה. "חולקים על הגרף": כמה מודלים אמרו שספירת האליוט/פיבו/תמיכה שצוירו לא נראית נכונה. הכל במשקל 0._\n')
    # ---- 4 crypto
    w(f'## 4. קריפטו – לונג בלבד ({len(crypto_recs)})')
    if crypto_recs:
        w('_Grok הוא פלטפורמת הסנטימנט הראשית לקריפטו. סטופ קבוע 3×ATR14 על סגירה יומית UTC, בלי יעד._\n')
        table(crypto_recs, '')
    else: w('אין שם קריפטו שעבר את מסנן המגמה בריצה הזו.\n')
    # ---- 5 exceptions
    w(f'## 5. חריגה: קטליזטור חזק ({len(exc)})')
    if exc:
        for c, r in exc: w(f"- **{c['t']}** ({DIRH[c['direction']]}): דוח ב-{c['_eg'].get('next_earnings')} ({c['_eg'].get('td_to_earnings')} ימי מסחר). {c['_eg'].get('exception_reason')}")
    else: w('אין.')
    w('')
    # ---- 6 blocked
    w(f'## 6. נחסם - דוח בתוך 5 ימי מסחר ({len(blocked)})')
    if blocked:
        w('| טיקר | כיוון | דוח הבא | ימי מסחר עד הדוח | מקורות | Perplexity קטליזטור | Claude | GPT |'); w('|---|---|---|---|---|---|---|---|')
        for c, r in blocked:
            g = c['_eg']
            w(f"| {c['t']} | {DIRH[c['direction']]} | {g.get('next_earnings')} | {g.get('td_to_earnings')} | {_t('; '.join(g.get('sources') or []))} | "
              f"{_t(r.get('pplx_catalyst_strength'))} | {_t(r.get('claude_conviction'))} | {_vd(r, 'gpt_verdict')} |")
        w('\n_השמות האלה לא בהמלצות, אבל פסקי הדין שלהם נרשמו ביומן למדידה._\n')
    else: w('אין.\n')
    # ---- 7 mismatches
    w(f'## 7. לא תואם ({len(bad)})')
    if bad:
        for k, v in bad.items(): w(f"- **{k[0]} {DIRH.get(k[1], k[1])}:** " + '; '.join(_t(x) for x in v[:6]))
    else: w('אין. כל המספרים בדוח, בשורות הטראקר ובאינדקס הגרפים זהים לקובץ הרמות.')
    w('')
    # ---- 8 per candidate
    w('## 8. פירוט לכל מועמד')
    for i, (c, r) in enumerate(zip(cands, rows), 1):
        x = res['raw'].get(c['t'], {}); L = c.get('_levels') or LF.load(run_dir, c) or {}; f = LF.facts_for_prompt(L) if L else {}
        tag = '' if not (c.get('_eg') or {}).get('blocked') else ' · ⛔ נחסם (דוח)'
        if rec.get(key(c)): tag += ' · ❗ לא תואם'
        w(f"### {i}. {c['t']} – {DIRH[c['direction']]}{' (קריפטו)' if c.get('asset') == 'crypto' else ''} · דירוג {_n(c.get('rank_score'), 1)}{tag}")
        if r.get('credit_status'): w(f"- **🔴 {r['credit_status']}**")
        T = f.get('trade') or {}; te = f.get('technical') or {}
        w(f"- **רמות (קובץ הרמות, נר אחרון {_t((f.get('levels_file') or {}).get('last_bar'))}, hash {_t((f.get('levels_file') or {}).get('bar_hash'))}):** "
          f"כניסה {_nd(c['entry'])} · סטופ {_nd(c['stop'])} ({_t(T.get('stop_rule'))}, ATR14={_nd(te.get('atr14_wilder'))}) · יעד: {_nd(c['target']) if c['target'] else 'אין'} – {_t(T.get('target_note') or T.get('target_rule'))}")
        w(f"- **טכני:** SMA20 {_nd(te.get('sma20'))} · SMA50 {_nd(te.get('sma50'))} · SMA200 {_nd(te.get('sma200'))} · מומנטום 12-1 {_n(te.get('mom_12_1'), 3)} · "
          f"RSI14 {_n((f.get('waves') or {}).get('rsi14'), 1)} · CCI20 {_n((f.get('waves') or {}).get('cci20'), 0)}")
        e1, e2 = f.get('elliott_v1') or {}, f.get('elliott_v2') or {}
        f1, f2 = f.get('fib_v1') or {}, f.get('fib_v2') or {}
        vp, sr = f.get('vp120') or {}, f.get('sr_nearest') or {}
        w(f"- **ניסיוני (משקל 0):** אליוט v2: {_t(e2.get('label'))} · אליוט v1: {_t(e1.get('label'))} · פיבו v2 {_nd(f2.get('origin'))}→{_nd(f2.get('end'))} (1.618={_nd((f2.get('levels') or {}).get('1.618'))}) · "
          f"VP120 POC {_nd(vp.get('poc'))} (VAH {_nd(vp.get('vah'))}, VAL {_nd(vp.get('val'))}) · תמיכה {_nd(sr.get('sr_support'))} · התנגדות {_nd(sr.get('sr_resistance'))} · "
          f"סוף גל: {_t((f.get('waves') or {}).get('wave_end_n'))} משפחות ({_t((f.get('waves') or {}).get('wave_end_families'))}) · "
          f"תחילת גל: {_t((f.get('waves') or {}).get('wave_start_n'))} ({_t((f.get('waves') or {}).get('wave_start_families'))})")
        g = c.get('_eg') or {}
        w(f"- **דוח:** {_t(g.get('status'))}" + (f" · מקורות: {_t('; '.join(g.get('sources') or []))}" if g.get('sources') else ''))
        ref = ((c.get('_levels') or {}).get('reference')) or {}
        ls_, fs_ = ref.get('liq_sweep') or {}, ref.get('fib_spiral') or {}
        if ls_:   # reference only, weight 0; never changes entry / stop / target
            flag = ('כן' if ls_.get('ls_sweep') else 'לא') if not ls_.get('error') else 'שגיאה'
            side = ' / '.join(n for k, n in (('ls_long_sweep', 'לונג'), ('ls_short_sweep', 'שורט')) if ls_.get(k))
            w(f"- **סוויפ נזילות (ייחוס בלבד, משקל 0):** {flag}" + (f" ({side}, רמה {_nd(ls_.get('ls_level'))} {_t(ls_.get('ls_level_kind'))})" if ls_.get('ls_sweep') else '')
              + (' · **עבר בדיקה, שביר, משקל 0**' if ls_.get('validated_variant') else ''))
        if c['direction'] == 'SHORT' and fs_ and not fs_.get('error'):
            w(f"- **ספירלת פיבו – יעדי ייחוס בלבד (משקל 0, לא משנה סטופ/יעד; השורט נשאר עם סטופ נגרר 4×ATR בלי יעד):** "
              f"T1 {_nd(fs_.get('fs_target_t1'))} ({_t(fs_.get('fs_t1_src'))}) · T2 {_nd(fs_.get('fs_target_t2'))} ({_t(fs_.get('fs_t2_src'))}) · מצב: {_t(fs_.get('fs_state'))}")
        if c.get('_chart_png'): w(f"\n![גרף {c['t']}]({os.path.relpath(c['_chart_png'], run_dir)})\n")
        if not res['enabled']: w('- **פלטפורמות:** לא הורצו.\n'); continue
        order = (['grok', 'jev', 'pplx'] if c.get('asset') == 'crypto' else ['jev', 'grok', 'pplx']) + ['claude', 'gpt']
        for p in order:
            if p == 'jev' and x.get('jev'):
                jv = x['jev']
                w(f"- **Jev ({M.get('jev')}):** {_t(r.get('jev_n_headlines'))} כותרות · {_t(r.get('jev_n_trusted'))} בביטחון ≥0.8 (סומכים על Jev) · {_t(r.get('jev_n_to_claude'))} הועברו ל-Claude לשיפוט "
                  f"(ביטחון נמוך או חשד למניפולציה; {_t(r.get('jev_n_dropped_injection'))} חשודות, {_t(r.get('jev_n_press_release'))} הודעות חברה) · סנטימנט {_t(r.get('jev_news_sentiment'))} · "
                  f"קטליזטור {_t(r.get('jev_top_catalyst'))}" + (f" · הסכמה עם Claude {_t(r.get('jev_claude_agreement'))}" if r.get('jev_claude_agreement') else ''))
            if p == 'grok':
                if r.get('grok_verdict'):
                    src = 'פוסטים שנשלפו בחינם (X)' if r.get('grok_source') == 'free_x_cache' else 'חיפוש X של Grok'
                    w(f"- **Grok{' (סנטימנט ראשי לקריפטו)' if c.get('asset') == 'crypto' else ''} ({M['grok']}, {src}):** {VERD[r['grok_verdict']]} · סנטימנט \u200e{r['grok_sentiment']:+d} · "
                      f"ביטחון {_t(r.get('grok_confidence'))} · {_t(r.get('grok_n_posts'))} פוסטים · {_t(r.get('grok_reason'))} · חשבונות מאומתים: {_t(r.get('grok_accounts'))}")
                else: w(f"- **Grok:** לא התקבל ({_t(r.get('grok_error'))[:160]})")
            if p == 'pplx':
                if r.get('pplx_verdict'):
                    w(f"- **Perplexity ({M['pplx']}):** {VERD[r['pplx_verdict']]} · {_t(r.get('pplx_reason'))} · קטליזטור: {_t(r.get('pplx_catalyst_strength'))}"
                      + (f" ({_t(r.get('pplx_catalyst_source'))})" if r.get('pplx_catalyst_source') else ''))
                    w(f"  - {_t(r.get('pplx_catalyst_summary'))} · דוח הבא: {_t(r.get('pplx_next_earnings'))} · דגלים: {_t(r.get('pplx_red_flags'))}")
                else: w(f"- **Perplexity:** לא התקבל ({_t(r.get('pplx_error'))[:160]})")
            if p == 'claude':
                if r.get('claude_conviction') is not None:
                    w(f"- **Claude, אנליסט ({M['claude']}):** ביטחון **{r['claude_conviction']}/100** · {DVIEW.get(r.get('claude_direction_view'), '—')} · סיכון: {_t(r.get('claude_key_risk'))}")
                    w(f"  - תזה: {_t(r.get('claude_thesis'))} · טכני (מהגרף): {_t(r.get('claude_technical_read'))}")
                else: w(f"- **Claude:** לא התקבל ({_t(r.get('claude_error'))[:160]})")
            if p == 'gpt':
                if r.get('gpt_verdict'):
                    w(f"- **GPT, פרקליט השטן ({M.get('gpt')}):** {VERD[r['gpt_verdict']]} · הסיכון הגדול: {_t(r.get('gpt_main_risk'))} · {_t(r.get('gpt_reason'))}")
                    if r.get('gpt_rebuttal_of_analyst'): w(f"  - נגד התזה של Claude: {_t(r['gpt_rebuttal_of_analyst'])}")
                elif M.get('gpt'): w(f"- **GPT:** לא התקבל ({_t(r.get('gpt_error'))[:160]})")
        dl = [f"{nm}: {_t(r.get(f'{p}_chart_disagree'))}" for p, nm in (('grok', 'Grok'), ('pplx', 'Perplexity'), ('claude', 'Claude'), ('gpt', 'GPT')) if r.get(f'{p}_chart_disagree')]
        if dl: w(f"- **האם הגרף נראה נכון? (ניסיוני):** {' · '.join(dl)} · קלט: {_t(r.get('image_inputs'))}")
        if r.get('cross_challenge'): w(f"- **אתגור הדדי:** {_t(r['cross_challenge'])}")
        w('')
    # ---- 9 tool stats
    w('## 9. סטטיסטיקת כלים (tool_stats, משקל 0)')
    w(res['tool_stats_md'] if res.get('tool_stats_md') else f"לא הופק: {_t(res.get('tool_stats_err'))}")
    w('')
    # ---- 10 costs
    st = res['stats']; est = res.get('estimate') or {}
    w('## 10. עלויות ותקינות')
    w(f"- **עלות המודלים בריצה:** ${res['spent']:.3f} מתוך תקרה ${res['budget']:.2f}. פירוט ב-`platform_costs.json`.")
    if est:
        pc = est.get('per_call_avg_usd', {})
        w(f"- **ממוצע למועמד:** כ-${est.get('per_candidate_usd', 0):.3f} (Grok {_n(pc.get('grok'), 3)}, Perplexity {_n(pc.get('pplx'), 3)}, Jev {_n(pc.get('jev_per_ticker'), 4)}, "
          f"Claude {_n(pc.get('claude_analyst'), 3)}, GPT {_n(pc.get('gpt_advocate'), 3)}) · הערכה שבועית: כ-${_n(est.get('weekly_estimate_usd'))}.")
    for k, lab in [('grok', 'Grok'), ('pplx', 'Perplexity'), ('claude', 'Claude'), ('gpt', 'GPT')]:
        if k in st: w(f"- **{lab}:** {st[k]['ok']} מתוך {st[k]['of']} הצליחו")
    w(f"- **עמודות מחקר (research_columns):** {_t(json.dumps(res.get('research_status'), ensure_ascii=False)[:200]) if res.get('research_status') else 'לא רצו'}")
    w('- **קבצים:** `candidates_full.csv`, ‏`levels/`, ‏`charts/` + `chart_index.json`, ‏`tracker_rows.csv`, ‏`reconciliation.json`, ‏`platform_enrichment.csv`, ‏`platform_raw.json`, ‏`research_columns.csv`.')
    md = '\n'.join(L_) + '\n'
    mdp = f'{run_dir}/unified_report_he.md'
    open(mdp, 'w', encoding='utf-8').write(md)
    pdfp = _pdf(md, f'{run_dir}/unified_report_he.pdf', base=run_dir)
    return {'md': mdp, 'pdf': pdfp}

def _pdf(md, out, base=None):
    try:
        import markdown
        body = markdown.markdown(md, extensions=['tables'])
        css = ("body{font-family:'IBM Plex Sans Hebrew','Rubik','DejaVu Sans',sans-serif;direction:rtl;font-size:10.5px;line-height:1.45;margin:18px}"
               "table{border-collapse:collapse;width:100%;font-size:9.5px;margin:6px 0}th,td{border:1px solid #bbb;padding:3px 5px;text-align:right}"
               "th{background:#eef2f7}h1{font-size:19px}h2{font-size:15px;border-bottom:2px solid #335;padding-bottom:2px;margin-top:16px}h3{font-size:12.5px;margin:12px 0 4px;color:#123}"
               "blockquote{background:#fff6e0;border-right:4px solid #e0a000;margin:6px 0;padding:6px 10px}code{font-size:9px;direction:ltr;unicode-bidi:embed}"
               "img{max-width:100%;page-break-inside:avoid}a{color:#1a4fa0;word-break:break-all;font-size:9px}li{margin:2px 0}@page{size:A4 landscape;margin:10mm}")
        h = f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'
        hp = out.replace('.pdf', '.html'); open(hp, 'w', encoding='utf-8').write(h)
        prof = f'/tmp/chrome-pdf-{os.getpid()}'
        subprocess.run(['google-chrome', '--headless=new', '--no-sandbox', '--disable-gpu', '--no-first-run', f'--user-data-dir={prof}', '--allow-file-access-from-files',
                        '--no-proxy-server', '--no-pdf-header-footer', f'--print-to-pdf={out}', 'file://' + hp],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300, check=True)
        return out if os.path.exists(out) else None
    except Exception as e:
        print('[report] PDF skipped:', e); return None
