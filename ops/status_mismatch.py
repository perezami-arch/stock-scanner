"""Daily check: flag positions whose status differs between the tracker (positions_registry.csv) and the
hypothetical/paper account ledger. Read-only; prints mismatches and exits 1 if any (for the daily job to alert).
Usage: python ops/status_mismatch.py TRACKER_CSV ACCOUNT_CSV
Both files need ticker, entry_session, status; optional exit_date, exit_price. 'closed'/'stopped' are treated as closed."""
import sys, pandas as pd
CLOSED = {"closed", "stopped", "stop", "סטופ", "סגור"}
def norm(df):
    df = df.copy(); df["is_closed"] = df["status"].astype(str).str.strip().str.lower().isin(CLOSED)
    for c in ("exit_date", "exit_price"):
        if c not in df: df[c] = None
    return df[["ticker", "entry_session", "is_closed", "exit_date", "exit_price"]]
def main(a, b):
    t = norm(pd.read_csv(a, dtype=object)); p = norm(pd.read_csv(b, dtype=object))
    m = t.merge(p, on=["ticker", "entry_session"], how="outer", suffixes=("_tracker", "_account"), indicator=True)
    bad = m[(m._merge != "both") | (m.is_closed_tracker != m.is_closed_account)
            | (m.is_closed_tracker.fillna(False) & (m.exit_date_tracker.astype(str) != m.exit_date_account.astype(str)))]
    if len(bad):
        print(f"STATUS MISMATCH: {len(bad)} position(s)"); print(bad.to_string(index=False)); return 1
    print("status OK: tracker and account agree"); return 0
if __name__ == "__main__": sys.exit(main(sys.argv[1], sys.argv[2]))
