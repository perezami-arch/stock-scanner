"""Crypto is OFF in this scanner (Ilan, 01.11.2026).

Crypto is removed from the scan universe, the positions tracker, the paper ledger, the platform-verdict ledgers,
the simulated account and the reports. A separate crypto scanner with its own parameters will be built later.
Nothing is deleted: crypto rows are MOVED to scan-runs/archive/crypto/<same file name> (append, de-duplicated),
and a frozen snapshot of the 01.11.2026 state lives in archive/crypto/ in the repo.

Re-enable only by an explicit decision: env SCANNER_ENABLE_CRYPTO=1.
"""
import os
import pandas as pd

CRYPTO_TICKERS_SEEN = {'UNI', 'LINK', 'AAVE', 'BTC', 'ETH', 'SOL'}   # documentation only; the filter uses the asset column


def crypto_enabled():
    return os.environ.get('SCANNER_ENABLE_CRYPTO', '0') == '1'


def is_crypto_mask(df):
    if df is None or not len(df) or 'asset' not in df.columns:
        return pd.Series(False, index=getattr(df, 'index', None))
    return df['asset'].astype(str).str.lower().eq('crypto')


def drop_crypto(df):
    """df without crypto rows (no-op when crypto is enabled or there is no asset column)."""
    if crypto_enabled() or df is None or not len(df): return df
    return df[~is_crypto_mask(df)].copy()


def archive_path(csv_path, root=None):
    root = root or os.path.join(os.path.dirname(os.path.abspath(csv_path)), 'archive', 'crypto')
    return os.path.join(root, os.path.basename(csv_path))


def archive_crypto_rows(csv_path, archive_root=None):
    """Move crypto rows of csv_path into the archive copy. Returns the number of rows moved. Never deletes data:
    rows are written to the archive first, the source is rewritten only after the archive write succeeded."""
    if crypto_enabled() or not os.path.exists(csv_path): return 0
    d = pd.read_csv(csv_path, dtype=object)
    m = is_crypto_mask(d)
    if not m.any(): return 0
    ap = archive_path(csv_path, archive_root); os.makedirs(os.path.dirname(ap), exist_ok=True)
    moved = d[m].copy(); moved['archived_reason'] = 'crypto removed from scanner (Ilan 01.11.2026)'
    if os.path.exists(ap):
        old = pd.read_csv(ap, dtype=object)
        moved = pd.concat([old, moved], ignore_index=True).drop_duplicates(subset=[c for c in d.columns], keep='first')
    moved.to_csv(ap, index=False)
    d[~m].to_csv(csv_path, index=False)
    return int(m.sum())
