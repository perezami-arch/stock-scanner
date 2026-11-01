import os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'modules'))
import crypto_policy as CP


def _df():
    return pd.DataFrame({'ticker': ['MU', 'UNI', 'LINK', 'XOM'], 'asset': ['stock', 'crypto', 'Crypto', 'stock'], 'x': [1, 2, 3, 4]})


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SCANNER_ENABLE_CRYPTO', raising=False)
    assert not CP.crypto_enabled()
    assert list(CP.drop_crypto(_df()).ticker) == ['MU', 'XOM']


def test_enabled_keeps_rows(monkeypatch):
    monkeypatch.setenv('SCANNER_ENABLE_CRYPTO', '1')
    assert len(CP.drop_crypto(_df())) == 4


def test_archive_moves_not_deletes(tmp_path, monkeypatch):
    monkeypatch.delenv('SCANNER_ENABLE_CRYPTO', raising=False)
    src = tmp_path / 'positions_registry.csv'; _df().to_csv(src, index=False)
    assert CP.archive_crypto_rows(str(src)) == 2
    live = pd.read_csv(src); arch = pd.read_csv(tmp_path / 'archive' / 'crypto' / 'positions_registry.csv')
    assert list(live.ticker) == ['MU', 'XOM']
    assert sorted(arch.ticker) == ['LINK', 'UNI'] and 'archived_reason' in arch
    # idempotent: second call moves nothing, archive not duplicated
    assert CP.archive_crypto_rows(str(src)) == 0
    assert len(pd.read_csv(tmp_path / 'archive' / 'crypto' / 'positions_registry.csv')) == 2


def test_archive_appends_dedup(tmp_path, monkeypatch):
    monkeypatch.delenv('SCANNER_ENABLE_CRYPTO', raising=False)
    src = tmp_path / 'l.csv'; _df().to_csv(src, index=False); CP.archive_crypto_rows(str(src))
    _df().to_csv(src, index=False); CP.archive_crypto_rows(str(src))   # same rows reappear -> no duplicates
    assert len(pd.read_csv(tmp_path / 'archive' / 'crypto' / 'l.csv')) == 2


def test_no_asset_column_noop(tmp_path, monkeypatch):
    monkeypatch.delenv('SCANNER_ENABLE_CRYPTO', raising=False)
    src = tmp_path / 'n.csv'; pd.DataFrame({'ticker': ['MU']}).to_csv(src, index=False)
    assert CP.archive_crypto_rows(str(src)) == 0


def test_load_registry_archives(tmp_path, monkeypatch):
    monkeypatch.delenv('SCANNER_ENABLE_CRYPTO', raising=False)
    import scanner_lessons as SLS
    src = tmp_path / 'positions_registry.csv'
    pd.DataFrame({'ticker': ['MU', 'AAVE'], 'asset': ['stock', 'crypto'], 'status': ['open', 'open']}).to_csv(src, index=False)
    reg = SLS.load_registry(str(src))
    assert list(reg.ticker) == ['MU'] and (tmp_path / 'archive' / 'crypto' / 'positions_registry.csv').exists()
