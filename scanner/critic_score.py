"""Critic (LLM model) weights - scoring v4-critics (26.10.2026). Activated by Ilan 26.10.2026 ("full weight per the original proposal").
SOURCE: scanner-improvement-proposal-2026-10-08.pdf, section 6.5 "כללי וטו וניקוד" (veto & scoring rules), copied verbatim below:
  final score = base score + SUM(critic_weight x verdict), confirm = +1, flag = -1, out-of-domain veto = -2.
  Initial weight 1.0 per critic. Confirmations capped at +2 in total (so "everyone agrees" does not inflate a score).
  V1 domain-owner veto backed by evidence the bot reproduces -> setup deleted (Perplexity: events/fundamentals/news; Grok: X sentiment).
  V2 veto outside the platform's domain (e.g. Claude on anything) = double flag (-2).
  V3 evidence the bot could not reproduce -> ordinary flag (-1).
  Entry threshold: total flags <= -3 -> "watch only", no entry (still measured in the tracker as a shadow row).
MAPPING to today's model outputs (no new numbers):
  grok / pplx / gpt verdict: approve|confirm -> +1, flag -> -1, veto -> V1/V2/V3 as above.
  claude (analyst, returns direction_view not a verdict): supports -> +1, opposes -> -1 (flag), neutral -> 0.
  pplx veto counts as a reproduced domain veto only when the bot's own earnings gate also blocks the setup; otherwise V3 (-1).
  grok veto: the bot cannot reproduce X sentiment -> V3 (-1).  gpt/claude have no data domain -> any veto = V2 (-2).
  jev: not a critic in the original proposal (added later as a headline pre-filter) -> weight 0, no number invented.
Weights are recalibrated only from forward results (section 6.6); as of 26.10.2026 no model has closed outcomes (0/15)."""
VERSION = 'v4-critics (2026-10-26)'
WEIGHTS = {'grok': 1.0, 'pplx': 1.0, 'claude': 1.0, 'gpt': 1.0, 'jev': 0.0}
DOMAIN = {'pplx': 'events/fundamentals/news', 'grok': 'x_sentiment'}
CONFIRM_CAP = 2.0
WATCH_ONLY_AT = -3.0

def _v(x):
    s = str(x or '').strip().lower()
    return {'confirm': 'approve', 'supports': 'approve', 'opposes': 'flag'}.get(s, s)

def score(row, earnings_blocked=False, weights=None):
    """row: platform row (grok_verdict, pplx_verdict, gpt_verdict, claude_direction_view).
    -> dict(points, confirm_pts, flag_pts, deleted, watch_only, detail)."""
    w = WEIGHTS if weights is None else weights
    raw = {'grok': row.get('grok_verdict'), 'pplx': row.get('pplx_verdict'), 'gpt': row.get('gpt_verdict'), 'claude': row.get('claude_direction_view')}
    conf = flags = 0.0; deleted = False; detail = {}
    for m, v in raw.items():
        v = _v(v); wt = float(w.get(m, 0.0))
        if not wt or v in ('', 'none', 'nan', 'neutral'): detail[m] = 0.0; continue
        if v == 'approve': conf += wt; detail[m] = wt; continue
        if v == 'flag': p = -1.0
        elif v == 'veto':
            if m == 'pplx' and earnings_blocked: deleted = True; p = 0.0; detail[m] = 'deleted (V1)'; continue
            p = -1.0 if m in DOMAIN else -2.0
        else: detail[m] = 0.0; continue
        flags += wt * p; detail[m] = wt * p
    conf = min(conf, CONFIRM_CAP)
    return dict(version=VERSION, points=round(conf + flags, 2), confirm_pts=round(conf, 2), flag_pts=round(flags, 2),
                deleted=deleted, watch_only=deleted or flags <= WATCH_ONLY_AT, detail=detail)
