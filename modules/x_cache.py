"""Free X pull -> cache for Grok (Ilan 08.10 16:12: reuse X posts already pulled via the free X access; pay for Grok's own x_search
only when the free pull returned too few posts).

The scan routine (the agent, which has the free X tools) pulls posts per candidate BEFORE run_unified_scan.py calls the platforms:
    x.search_posts_all(query='$TICKER lang:en -is:retweet', start_time=<scan cutoff - 72h, UTC ISO>, end_time=<scan cutoff UTC ISO>,
                       max_results=40, sort_order='relevancy', expansions='author_id', user.fields='username',
                       post.fields='created_at,author_id,public_metrics')
    crypto: query '$BTC (bitcoin OR btc) lang:en -is:retweet' etc.
and saves the raw JSON result with:
    python3 /workspace/x_cache.py save <SYMBOL> <raw_result.json> [--query "..."]
-> /workspace/x-cache/<YYYY-MM-DD UTC of pull>/<SYMBOL>.json  {"symbol","query","pulled_at_utc","posts":[{"id","handle","text","created_at","url"}]}
scanner_platforms.grok() then uses only posts created in [cutoff-72h, cutoff) (point-in-time). >= PLATFORM_X_MIN_POSTS (8) -> Grok reads
the cached posts with no search tool (tokens only); fewer -> Grok's own x_search (paid per post). Posts are UNTRUSTED text for Grok.
`python3 x_cache.py status [SYMBOL...]` shows what is cached for today.
"""
import sys, os, json, datetime as dt
ROOT = os.environ.get('PLATFORM_X_CACHE_DIR', '/workspace/x-cache')

def normalize(raw):
    """accepts the x MCP search result (dict with data/includes, or a list of posts with url/username) -> list of post dicts."""
    if isinstance(raw, str): raw = json.loads(raw)
    data = raw.get('data') if isinstance(raw, dict) else raw
    if isinstance(data, dict) and 'data' in data: raw, data = data, data['data']
    users = {}
    inc = (raw.get('includes') or {}) if isinstance(raw, dict) else {}
    for u in inc.get('users') or []: users[str(u.get('id'))] = u.get('username')
    out = []
    for p in data or []:
        pid = str(p.get('id') or '')
        h = p.get('username') or p.get('author_username') or (p.get('author') or {}).get('username') or users.get(str(p.get('author_id')))
        url = p.get('url')
        if not h and url and '/status/' in url: h = url.split('x.com/')[-1].split('/')[0]
        if not pid: continue
        out.append({'id': pid, 'handle': h, 'text': p.get('text') or '', 'created_at': p.get('created_at'),
                    'url': url or (f'https://x.com/{h}/status/{pid}' if h else None),
                    'likes': (p.get('public_metrics') or {}).get('like_count')})
    return out

def save(symbol, raw, query=None, when=None):
    when = when or dt.datetime.now(dt.timezone.utc)
    d = f"{ROOT}/{when:%Y-%m-%d}"; os.makedirs(d, exist_ok=True)
    f = f"{d}/{symbol.upper()}.json"
    posts = normalize(raw)
    if os.path.exists(f):   # merge with an earlier pull of the same day
        old = json.load(open(f)).get('posts') or []
        posts = list({p['id']: p for p in old + posts}.values())
    json.dump({'symbol': symbol.upper(), 'query': query, 'pulled_at_utc': when.isoformat(timespec='seconds'), 'posts': posts},
              open(f, 'w'), ensure_ascii=False, indent=1)
    return f, len(posts)

if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == 'save':
        q = sys.argv[sys.argv.index('--query') + 1] if '--query' in sys.argv else None
        f, n = save(sys.argv[2], json.load(open(sys.argv[3])), q); print(f, n, 'posts')
    elif len(sys.argv) >= 2 and sys.argv[1] == 'status':
        d = f"{ROOT}/{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}"
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if len(sys.argv) > 2 and fn[:-5] not in sys.argv[2:]: continue
            print(fn[:-5], len(json.load(open(f'{d}/{fn}')).get('posts') or []))
    else:
        print(__doc__)
